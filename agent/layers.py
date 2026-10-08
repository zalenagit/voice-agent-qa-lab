"""Simulated layers of a voice agent: telephony, speech-to-text, the model, text-to-speech.

Each layer is deterministic for a given random generator (seed), but includes
realistic variation so evaluation has to deal with non-determinism.
Faults can be injected per layer to practice isolating which layer failed.
"""
import json
import re

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}

INTENTS = ["book_appointment", "reschedule_appointment", "cancel_appointment",
           "appointment_lookup", "prescription_refill", "clinic_hours",
           "medical_advice", "emergency", "off_script", "speak_to_human", "unknown"]

# Intents a noisy model tends to confuse with each other
CONFUSABLE = {
    "reschedule_appointment": "cancel_appointment",
    "cancel_appointment": "reschedule_appointment",
    "book_appointment": "reschedule_appointment",
    "appointment_lookup": "book_appointment",
}

SOUND_ALIKE = {"fifteen": "fifty", "thirteen": "thirty", "two": "to", "four": "for"}


class LayerError(Exception):
    def __init__(self, layer, code, message):
        super().__init__(message)
        self.layer, self.code = layer, code


# ---------------------------------------------------------------- telephony
def telephony_connect(rng, audio, faults):
    """Returns (latency_ms, detail). Raises LayerError on call setup failure."""
    if "sip_503" in faults:
        raise LayerError("telephony", "SIP 503", "Carrier returned 503 Service Unavailable on INVITE")
    latency = rng.randint(80, 200)
    detail = {"codec": audio.get("codec", "PCMU"), "packet_loss": audio.get("packet_loss", 0.0),
              "jitter_ms": audio.get("jitter_ms", 10), "one_way_audio": "one_way_audio" in faults}
    return latency, detail


# ---------------------------------------------------------------- speech to text
def speech_to_text(rng, said, audio, faults):
    """Returns (heard_text, confidence, latency_ms)."""
    if "stt_timeout" in faults:
        raise LayerError("stt", "TIMEOUT", "Speech-to-text provider did not respond within 5000 ms")
    if "one_way_audio" in faults:  # caller audio never reaches us
        return "", 0.0, rng.randint(150, 250)

    loss = audio.get("packet_loss", 0.0)
    snr = audio.get("snr_db", 30)
    drop_p = 0.002 + loss * 2.5 + max(0, (15 - snr)) / 120
    words, out = said.split(), []
    for w in words:
        lw = w.lower().strip(",.?!")
        if rng.random() < drop_p:
            continue                       # word lost
        if lw in SOUND_ALIKE and rng.random() < drop_p * 4:
            out.append(SOUND_ALIKE[lw])    # misheard
            continue
        out.append(w)
    heard = " ".join(out)
    errors = len(words) - len(out)
    confidence = max(0.0, min(1.0, 0.97 - drop_p * 3 - errors * 0.03 + rng.uniform(-0.02, 0.02)))
    latency = int(rng.randint(180, 380) * (1 + loss * 10))
    return heard, round(confidence, 3), latency


# ---------------------------------------------------------------- the model (NLU)
def _classify(text, version):
    t = text.lower()
    rules = [
        ("emergency", ["chest pain", "chest", "breathe", "severe bleeding"]),
        ("off_script", ["ignore your instructions", "ignore previous", "system prompt", "pretend you are",
                        "you are now", "developer mode"]),
        ("medical_advice", ["should i take", "double my", "stop taking", "is it safe to", "what dose",
                            "how much should i take", "can i take"]),
        ("speak_to_human", ["human", "representative", "real person", "operator"]),
        ("reschedule_appointment", ["reschedule"] + ([] if version == "v2" else
                                                     ["move my appointment", "change my appointment"])),
        ("cancel_appointment", ["cancel"]),
        ("appointment_lookup", ["when is my appointment", "what time is my appointment",
                                "my appointments", "do i have an appointment", "her appointment",
                                "his appointment"]),
        ("prescription_refill", ["refill", "prescription"]),
        ("clinic_hours", ["hours", "what time do you open", "what time do you close", "are you open",
                          "holiday"]),
        ("book_appointment", ["book", "make an appointment", "schedule", "new appointment",
                              "see dr", "appointment with"]),
    ]
    for intent, keys in rules:
        if any(k in t for k in keys):
            return intent
    return "unknown"


def extract_slots(text, version="v1"):
    t = text.lower()
    slots = {}
    m = re.search(r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?:st|nd|rd|th)?\b(?!,?\s*\d{4})", t)
    if m:
        slots["date"] = f"2026-{MONTHS[m.group(1)]:02d}-{int(m.group(2)):02d}"
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)", t)
    if m:
        hour, minute = int(m.group(1)) % 12, int(m.group(2) or 0)
        if m.group(3).startswith("p"):
            hour += 12
        # v2 regression: returns 12-hour text instead of HH:MM
        slots["time"] = (f"{int(m.group(1))}:{minute:02d} {'PM' if hour >= 12 else 'AM'}"
                         if version == "v2" else f"{hour:02d}:{minute:02d}")
    m = re.search(r"\bdr\.?\s+(patel|nguyen|okafor)\b", t)
    if m:
        slots["provider"] = f"Dr. {m.group(1).capitalize()}"
    # Names are matched case-sensitively: "I'm having chest pain" must not become a patient called "Having Chest"
    m = re.search(r"\b(?:[Mm]y name is|[Tt]his is|I am|I'm)\s+([A-Z][a-z]+ [A-Z][a-z]+)\b", text)
    if m:
        slots["patient_name"] = m.group(1)
    m = re.search(r"\b(?:born(?: on)?|date of birth is|dob is)\s+(" + "|".join(MONTHS) +
                  r")\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})", t)
    if m:
        slots["dob"] = f"{m.group(3)}-{MONTHS[m.group(1)]:02d}-{int(m.group(2)):02d}"
    return slots


def model_understand(rng, heard, version, temperature, faults):
    """Returns (raw_model_output_string, latency_ms). Output is meant to be JSON."""
    latency = rng.randint(300, 650)
    if "model_timeout" in faults:
        raise LayerError("model", "TIMEOUT", "Model inference exceeded 8000 ms")
    intent = _classify(heard, version)
    noise = temperature * (0.015 if version == "v1" else 0.10)
    if intent in CONFUSABLE and rng.random() < noise:
        intent = CONFUSABLE[intent]
    out = {"intent": intent, "slots": extract_slots(heard, version),
           "confidence": round(rng.uniform(0.75, 0.98), 2)}
    raw = json.dumps(out)
    if "model_invalid_json" in faults:
        raw = raw[: len(raw) // 2]   # truncated generation
    return raw, latency


# ---------------------------------------------------------------- text to speech
def text_to_speech(rng, text, faults):
    """Returns (audio_ms, latency_ms). Raises on failure."""
    if "tts_error" in faults:
        raise LayerError("tts", "SYNTH_FAILED", "TTS returned 0 bytes of audio (voice id not found)")
    latency = rng.randint(140, 300) + (2600 if "tts_slow" in faults else 0)
    return len(text) * 55, latency
