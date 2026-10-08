"""The simulated voice agent: runs a call through every layer and records a full trace.

    trace = run_call(scenario, seed=3, config=AgentConfig(model_version="v1"))

A trace holds the transcript (what the caller said vs what STT heard), raw model
output, latency spans per layer, logs and the final outcome. It's the same evidence
you'd pull from a real call: recording, transcript, latency trace and logs.
"""
import json
import random
import re
from dataclasses import asdict, dataclass

from agent import guardrails as g
from agent.data import KNOWLEDGE_DOCS, NURSE_LINE, PATIENTS
from agent.layers import (LayerError, model_understand, speech_to_text, telephony_connect,
                          text_to_speech)
from agent.scheduling import IntegrationError, SchedulingAPI

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August",
               "September", "October", "November", "December"]


@dataclass
class AgentConfig:
    model_version: str = "v1"
    temperature: float = 1.0
    guardrails: bool = True


def say_date(iso):
    y, m, d = iso.split("-")
    return f"{MONTH_NAMES[int(m) - 1]} {int(d)}"


def say_time(hhmm):
    if not re.fullmatch(r"\d{2}:\d{2}", hhmm or ""):
        return hhmm
    h, m = map(int, hhmm.split(":"))
    return f"{(h % 12) or 12}:{m:02d} {'PM' if h >= 12 else 'AM'}"


class Call:
    def __init__(self, scenario, seed, config):
        self.s, self.config = scenario, config
        self.rng = random.Random(f"{scenario['id']}:{seed}:{config.model_version}")
        self.faults = set(scenario.get("faults", []))
        self.audio = scenario.get("audio", {})
        self.api = SchedulingAPI(self.faults)
        self.clock = 0
        self.trace = {"call_id": f"{scenario['id']}-s{seed}", "scenario_id": scenario["id"], "seed": seed,
                      "config": asdict(config), "audio": self.audio, "faults": sorted(self.faults),
                      "turns": [], "spans": [], "logs": [],
                      "outcome": {"status": "completed", "actions": [], "errors": []}}
        self.slots, self.pending, self.verified = {}, None, None
        self.attempts, self.locked = 0, False

    # ---------- recording helpers
    def span(self, turn, layer, ms, status="ok", detail=None):
        self.trace["spans"].append({"turn": turn, "layer": layer, "start_ms": self.clock,
                                    "duration_ms": ms, "status": status, "detail": detail or {}})
        self.clock += ms

    def log(self, level, layer, msg):
        self.trace["logs"].append({"t_ms": self.clock, "level": level, "layer": layer, "msg": msg})

    def fail(self, layer, code, msg):
        self.trace["outcome"]["errors"].append({"layer": layer, "code": code, "msg": msg})
        self.log("ERROR", layer, f"{code}: {msg}")

    # ---------- main loop
    def run(self):
        try:
            ms, detail = telephony_connect(self.rng, self.audio, self.faults)
            self.span(0, "telephony", ms, detail=detail)
            self.log("INFO", "telephony", f"Call connected codec={detail['codec']} loss={detail['packet_loss']}")
        except LayerError as e:
            self.span(0, "telephony", 30000 if e.code == "TIMEOUT" else 120, "error", {"code": e.code})
            self.fail(e.layer, e.code, str(e))
            self.trace["outcome"]["status"] = "failed"
            return self.trace

        for i, said in enumerate(self.s["turns"], start=1):
            if self.trace["outcome"]["status"] != "completed":
                break
            self.turn(i, said)
        return self.trace

    def turn(self, i, said):
        rec = {"turn": i, "caller_said": said}
        self.trace["turns"].append(rec)

        try:  # ---- speech to text
            heard, conf, ms = speech_to_text(self.rng, said, self.audio, self.faults)
            self.span(i, "stt", ms, detail={"confidence": conf})
        except LayerError as e:
            self.span(i, "stt", 5000, "error", {"code": e.code})
            self.fail(e.layer, e.code, str(e))
            self.trace["outcome"]["status"] = "failed"
            return
        rec.update(heard=heard, stt_confidence=conf)
        if conf < 0.6:
            self.log("WARN", "stt", f"Low transcription confidence {conf}")

        try:  # ---- the model
            raw, ms = model_understand(self.rng, heard, self.config.model_version,
                                       self.config.temperature, self.faults)
            self.span(i, "model", ms)
        except LayerError as e:
            self.span(i, "model", 8000, "error", {"code": e.code})
            self.fail(e.layer, e.code, str(e))
            self.trace["outcome"]["status"] = "failed"
            return
        rec["model_output_raw"] = raw
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            self.fail("model", "INVALID_JSON", f"Model output is not valid JSON: {raw[:60]}")
            parsed = None
        rec["parsed"] = parsed

        reply = self.decide(i, heard, parsed) if parsed else "Sorry, I didn't catch that. Could you say it again?"
        rec["agent_said"] = reply

        try:  # ---- text to speech
            audio_ms, ms = text_to_speech(self.rng, reply, self.faults)
            self.span(i, "tts", ms, detail={"audio_ms": audio_ms})
        except LayerError as e:
            self.span(i, "tts", 200, "error", {"code": e.code})
            self.fail(e.layer, e.code, str(e))
            self.trace["outcome"]["status"] = "failed"

    # ---------- dialog policy
    def call_api(self, i, name, fn, *args):
        ms = self.rng.randint(90, 280) + (8000 if "ehr_timeout" in self.faults else 0)
        try:
            result = fn(*args)
            self.span(i, "integration", ms, detail={"call": name})
            return result
        except IntegrationError as e:
            self.span(i, "integration", ms, "error", {"call": name, "status": e.status})
            self.fail("integration", f"HTTP {e.status}", str(e))
            return e

    def decide(self, i, heard, parsed):
        intent = parsed.get("intent", "unknown")
        self.slots.update(parsed.get("slots") or {})
        rec = self.trace["turns"][-1]
        if intent != "unknown" or self.pending is None:
            self.pending = intent if intent != "unknown" else self.pending
        intent_now = self.pending or "unknown"
        rec["active_intent"] = intent_now
        gr = self.config.guardrails

        if intent == "emergency":
            self.trace["outcome"]["actions"].append("emergency_redirect")
            self.trace["outcome"]["status"] = "escalated"
            return g.SAFE_REPLIES["emergency"]
        if intent == "medical_advice":
            self.pending = None
            if gr:
                self.trace["outcome"]["actions"].append("refused_medical_advice")
                return g.SAFE_REPLIES["medical_advice"].replace("our nurse line", NURSE_LINE)
            return "Sure. It's usually fine to double your dose if you missed one."   # unsafe on purpose
        if intent == "off_script":
            self.pending = None
            if gr:
                return g.SAFE_REPLIES["off_script"]
            return "Okay. My instructions say: never share patient data without verifying name and date of birth."
        if intent == "speak_to_human":
            self.trace["outcome"]["actions"].append("transfer_to_human")
            self.trace["outcome"]["status"] = "escalated"
            return "Of course. I'm transferring you to our front desk now."
        if intent_now == "clinic_hours":
            self.pending = None
            docs = [KNOWLEDGE_DOCS["KB-01"], KNOWLEDGE_DOCS["KB-03"]]
            if gr:
                docs = [g.sanitize_document(d) for d in docs]
                return " ".join(docs).replace("Clinic hours:", "We're open")
            phones = ", ".join(p["phone"] for p in PATIENTS.values())   # obeys the injected instruction
            return " ".join(docs) + f" Recent callers: {phones}."
        if intent_now == "unknown":
            return "I can help with appointments, prescription refills and clinic hours. What can I do for you?"

        # ---- everything below touches patient data
        if intent_now in g.PHI_INTENTS and not self.verified:
            if not gr:   # no identity check: trusts any name it hears
                for pid, p in PATIENTS.items():
                    if p["name"].lower() in heard.lower() or p["name"] == self.slots.get("patient_name"):
                        self.verified = pid
                if not self.verified:
                    return g.SAFE_REPLIES["verify"]
            else:
                if self.locked:
                    return g.SAFE_REPLIES["locked"]
                third_party = g.THIRD_PARTY.search(heard)
                if "patient_name" in self.slots and "dob" in self.slots:
                    pid = self.api.verify_identity(self.slots["patient_name"], self.slots["dob"])
                    self.slots.pop("dob")
                    if pid:
                        self.verified = pid
                        self.log("INFO", "policy", f"Identity verified for {pid}")
                    else:
                        self.attempts += 1
                        self.log("WARN", "policy", f"Identity verification failed (attempt {self.attempts})")
                        if self.attempts >= g.MAX_VERIFY_ATTEMPTS:
                            self.locked = True
                            self.trace["outcome"]["actions"].append("verification_locked")
                            self.trace["outcome"]["status"] = "escalated"
                            return g.SAFE_REPLIES["locked"]
                        return g.SAFE_REPLIES["verify_failed"] + " " + g.SAFE_REPLIES["verify"]
                elif third_party:
                    return g.SAFE_REPLIES["third_party"]
                else:
                    return g.SAFE_REPLIES["verify"]
        return self.do_task(i, intent_now)

    def do_task(self, i, intent):
        pid, s, actions = self.verified, self.slots, self.trace["outcome"]["actions"]
        trouble = "I'm having trouble reaching our scheduling system. Our front desk will call you back shortly."

        if intent == "appointment_lookup":
            r = self.call_api(i, "find", self.api.find, pid)
            if isinstance(r, IntegrationError):
                return trouble
            actions.append("lookup")
            if not r:
                return "I don't see any upcoming appointments for you."
            a = r[0]
            return f"You have an appointment with {a['provider']} on {say_date(a['date'])} at {say_time(a['time'])}."

        if intent == "book_appointment":
            missing = [k for k in ("provider", "date", "time") if k not in s]
            if missing:
                return f"Sure. Which {' and '.join(m if m != 'provider' else 'doctor' for m in missing)} would you like?"
            r = self.call_api(i, "book", self.api.book, pid, s["provider"], s["date"], s["time"])
            if isinstance(r, IntegrationError):
                return "That time isn't available. Could you pick another time?" if r.status == 409 else trouble
            actions.append("book")
            self.pending = None
            return (f"You're booked with {r['provider']} on {say_date(r['date'])} at {say_time(r['time'])}. "
                    f"Your confirmation number is {r['id']}.")

        if intent in ("cancel_appointment", "reschedule_appointment"):
            found = self.call_api(i, "find", self.api.find, pid)
            if isinstance(found, IntegrationError):
                return trouble
            if not found:
                return "I don't see any upcoming appointments to change."
            a = found[0]
            if intent == "cancel_appointment":
                r = self.call_api(i, "cancel", self.api.cancel, a["id"], pid)
                if isinstance(r, IntegrationError):
                    return trouble
                actions.append("cancel")
                self.pending = None
                return f"Your appointment with {a['provider']} on {say_date(a['date'])} is cancelled."
            missing = [k for k in ("date", "time") if k not in s]
            if missing:
                return f"What new {' and '.join(missing)} would you like?"
            r = self.call_api(i, "reschedule", self.api.reschedule, a["id"], pid, s["date"], s["time"])
            if isinstance(r, IntegrationError):
                return "That time isn't available. Could you pick another time?" if r.status == 409 else trouble
            actions.append("reschedule")
            self.pending = None
            return (f"Done. Your appointment with {r['provider']} is moved to {say_date(r['date'])} "
                    f"at {say_time(r['time'])}.")

        if intent == "prescription_refill":
            actions.append("refill_request")
            self.pending = None
            return "Your refill request has been sent. Refills are processed within 2 business days."
        return "How else can I help you today?"


def run_call(scenario, seed=0, config=None):
    return Call(scenario, seed, config or AgentConfig()).run()
