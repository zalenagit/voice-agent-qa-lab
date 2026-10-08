"""Structured output validation for the model's JSON (no external dependency)."""
import json
import re

from agent.layers import INTENTS

SLOT_RULES = {
    "date": r"\d{4}-\d{2}-\d{2}",
    "time": r"\d{2}:\d{2}",
    "dob": r"\d{4}-\d{2}-\d{2}",
    "provider": r"Dr\. [A-Z][a-z]+",
    "patient_name": r"[A-Z][a-z]+ [A-Z][a-z]+",
}


def validate(raw):
    """Return a list of schema errors for one raw model output (empty list = valid)."""
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return ["not valid JSON"]
    if not isinstance(obj, dict):
        return ["top level must be an object"]
    errors = []
    if obj.get("intent") not in INTENTS:
        errors.append(f"intent '{obj.get('intent')}' is not an allowed value")
    conf = obj.get("confidence")
    if not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
        errors.append("confidence must be a number from 0 to 1")
    slots = obj.get("slots")
    if not isinstance(slots, dict):
        return errors + ["slots must be an object"]
    for key, value in slots.items():
        if key not in SLOT_RULES:
            errors.append(f"unexpected slot '{key}'")
        elif not isinstance(value, str) or not re.fullmatch(SLOT_RULES[key], value):
            errors.append(f"slot '{key}' has invalid format: {value!r}")
    return errors
