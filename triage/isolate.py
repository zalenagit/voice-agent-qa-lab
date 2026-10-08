"""Isolate which layer failed in a call: telephony, speech-to-text, model, integration or text-to-speech.

Order matters: we check from the bottom of the stack up, because a lower-layer
failure (e.g. packet loss) produces symptoms in every layer above it (bad
transcript -> wrong intent -> wrong action). Blaming the first symptom is the
most common triage mistake.
"""
import json
import re

from evals.schema import validate

LATENCY_BUDGET_MS = 2500    # per turn, caller-perceived
TTS_SLOW_MS = 1500


def words(text):
    return re.findall(r"[a-z0-9']+", (text or "").lower())


def wer(reference, hypothesis):
    """Word error rate via edit distance."""
    r, h = words(reference), words(hypothesis)
    if not r:
        return 0.0 if not h else 1.0
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev, d[j] = d[j], cur
    return d[len(h)] / len(r)


def isolate(trace, expected=None):
    """Return {'layer', 'summary', 'evidence': [...], 'turn', 'severity'}."""
    expected = expected or {}
    spans, turns = trace["spans"], trace["turns"]
    # 4xx from the scheduling API (slot taken, not found) are business answers, not system faults
    errors = {s["layer"]: s for s in spans if s["status"] == "error"
              and not (s["layer"] == "integration" and 400 <= s["detail"].get("status", 500) < 500)}
    tel = next((s for s in spans if s["layer"] == "telephony"), None)

    def result(layer, summary, evidence, turn=None, severity="high"):
        return {"layer": layer, "summary": summary, "evidence": evidence, "turn": turn, "severity": severity}

    # 1. Telephony: call setup, missing inbound audio, network quality
    if "telephony" in errors:
        code = errors["telephony"]["detail"].get("code")
        return result("telephony", f"Call failed at setup ({code})",
                      [f"telephony span status=error code={code}", "no turns were processed"], 0, "critical")
    spoken = [t for t in turns if t["caller_said"].strip()]
    silent = [t for t in spoken if "heard" in t and not t["heard"].strip()]
    if spoken and len(silent) == len(spoken):
        return result("telephony", "No inbound audio: caller spoke but the agent received silence on every turn",
                      [f"{len(silent)}/{len(spoken)} turns transcribed as empty",
                       f"one_way_audio flag={tel['detail'].get('one_way_audio') if tel else 'n/a'}",
                       "check RTP direction / NAT / SDP negotiation"], silent[0]["turn"], "critical")
    loss = (tel or {}).get("detail", {}).get("packet_loss", 0)
    jitter = (tel or {}).get("detail", {}).get("jitter_ms", 0)
    worst = max(((wer(t["caller_said"], t.get("heard", "")), t) for t in turns if "heard" in t),
                default=(0, None), key=lambda x: x[0])
    if (loss >= 0.03 or jitter > 60) and worst[0] > 0.1:   # >3% loss is already audible on VoIP
        return result("telephony", "Degraded network audio is corrupting the transcript",
                      [f"packet_loss={loss:.0%}, jitter={jitter} ms, codec={tel['detail'].get('codec')}",
                       f"worst turn WER={worst[0]:.0%} (turn {worst[1]['turn']})",
                       "STT symptoms are downstream of the network; fix transport before tuning STT"],
                      worst[1]["turn"])

    # 2. Speech to text
    if "stt" in errors:
        s = errors["stt"]
        return result("stt", f"Speech-to-text failed ({s['detail'].get('code')})",
                      [f"stt span error on turn {s['turn']}: {s['detail'].get('code')}", f"duration {s['duration_ms']} ms"],
                      s["turn"])
    if worst[1] is not None and (worst[0] > 0.2 or worst[1].get("stt_confidence", 1) < 0.6):
        t = worst[1]
        return result("stt", "Transcript does not match what the caller said",
                      [f"WER={worst[0]:.0%}, confidence={t.get('stt_confidence')}",
                       f"said: \"{t['caller_said']}\"", f"heard: \"{t.get('heard')}\""], t["turn"])

    # 3. Model
    if "model" in errors:
        s = errors["model"]
        return result("model", f"Model call failed ({s['detail'].get('code')})", [f"model span error on turn {s['turn']}"], s["turn"])
    for t in turns:
        if "model_output_raw" in t:
            problems = validate(t["model_output_raw"])
            if problems:
                return result("model", "Model returned output that fails the schema",
                              [f"turn {t['turn']}: {problems}", f"raw: {t['model_output_raw'][:80]}"], t["turn"])
    if expected.get("first_intent") and turns and turns[0].get("parsed"):
        got = turns[0]["parsed"].get("intent")
        if got != expected["first_intent"] and wer(turns[0]["caller_said"], turns[0].get("heard", "")) <= 0.1:
            return result("model", f"Wrong intent from a clean transcript: {got} instead of {expected['first_intent']}",
                          [f"transcript WER={wer(turns[0]['caller_said'], turns[0].get('heard', '')):.0%} (accurate)",
                           f"model output: {turns[0]['model_output_raw']}",
                           f"model version {trace['config']['model_version']}"], 1)

    # 4. Integration behind the agent
    if "integration" in errors:
        s = errors["integration"]
        return result("integration", f"Scheduling/EHR call '{s['detail'].get('call')}' failed (HTTP {s['detail'].get('status')})",
                      [f"integration span error on turn {s['turn']}, {s['duration_ms']} ms",
                       next((l["msg"] for l in trace["logs"] if l["layer"] == "integration"), "")], s["turn"])

    # 5. Text to speech
    if "tts" in errors:
        s = errors["tts"]
        return result("tts", f"Text-to-speech failed ({s['detail'].get('code')}): caller heard nothing",
                      [f"tts span error on turn {s['turn']}", "the model and policy produced a correct reply; audio was never generated"],
                      s["turn"], "critical")
    for s in spans:
        if s["layer"] == "tts" and s["duration_ms"] > TTS_SLOW_MS:
            return result("tts", f"Text-to-speech is slow ({s['duration_ms']} ms)",
                          [f"tts span {s['duration_ms']} ms on turn {s['turn']} (budget {TTS_SLOW_MS} ms)"], s["turn"], "medium")

    # 6. Latency budget
    per_turn = {}
    for s in spans:
        if s["turn"] > 0:
            per_turn.setdefault(s["turn"], []).append(s)
    for turn, ss in per_turn.items():
        total = sum(s["duration_ms"] for s in ss)
        if total > LATENCY_BUDGET_MS:
            slow = max(ss, key=lambda s: s["duration_ms"])
            return result(slow["layer"], f"Turn {turn} took {total} ms (budget {LATENCY_BUDGET_MS} ms)",
                          [f"slowest layer: {slow['layer']} {slow['duration_ms']} ms"], turn, "medium")

    return result("none", "No layer fault detected; review the dialog policy and expectations", [], None, "low")
