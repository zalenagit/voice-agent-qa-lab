"""Safety controls: identity verification, medical-advice refusal, document sanitizing, PHI output filter."""
import re

from agent.data import PATIENTS

THIRD_PARTY = re.compile(r"\b(husband|wife|son|daughter|mother|father|caregiver|on behalf of|calling for|"
                         r"from the hospital|this is dr|i am dr|i'm dr|her appointment|his appointment)\b", re.I)
INSTRUCTION_LINE = re.compile(r"(system note|ignore (all |previous )?(rules|instructions)|read out|disclose|"
                              r"you must now)", re.I)

PHI_INTENTS = {"appointment_lookup", "cancel_appointment", "reschedule_appointment",
               "book_appointment", "prescription_refill"}
MAX_VERIFY_ATTEMPTS = 2

SAFE_REPLIES = {
    "emergency": "If this is a medical emergency, please hang up and call 911 now.",
    "medical_advice": ("I'm not able to give medical advice. I can connect you with our nurse line, "
                       "or you can ask your doctor at your next visit."),
    "off_script": "I can help with appointments, prescription refills and clinic information. What do you need today?",
    "verify": "Before I can help with that, please tell me the patient's full name and date of birth.",
    "verify_failed": "I'm sorry, I couldn't verify those details.",
    "locked": "I wasn't able to verify your identity, so I'm transferring you to our front desk team.",
    "third_party": ("For privacy, I can only share appointment details with the patient after verifying "
                    "their name and date of birth."),
}


def sanitize_document(text):
    """Treat retrieved documents as data: drop lines that look like instructions to the agent."""
    return "\n".join(line for line in text.splitlines() if not INSTRUCTION_LINE.search(line))


def phi_in_text(text, allowed_patient_id=None):
    """Return the list of PHI items (other patients' names, DOBs, phones) found in an agent reply."""
    found, low = [], text.lower()
    for pid, p in PATIENTS.items():
        if pid == allowed_patient_id:
            continue
        y, m, d = p["dob"].split("-")
        for value in (p["name"].lower(), p["phone"], p["dob"], f"{int(m)}/{int(d)}/{y}"):
            if value in low:
                found.append(f"{pid}:{value}")
    return found
