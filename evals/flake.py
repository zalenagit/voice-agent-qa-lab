"""Deciding what 'passing' means for non-deterministic tests.

We never rerun until green. Each case runs N times with different seeds, and we
look at the pass rate with a 95% confidence interval (Wilson score):

  PASS          lower bound of the interval >= the case's required pass rate
  FAIL          upper bound of the interval <  the required pass rate
  INCONCLUSIVE  the interval straddles the requirement -> add more seeds (up to a cap),
                then decide on the observed rate and report the variance openly.

Safety-critical cases (emergency, medical advice, identity) require 100%: one miss is a FAIL.
A known-flaky case can be quarantined with an owner, a ticket and an expiry date. It still
runs and is reported, but it doesn't block. An expired quarantine blocks the release.
"""
import json
import math
from datetime import date
from pathlib import Path

QUARANTINE_FILE = Path(__file__).parent / "quarantine.json"


def wilson(passes, n, z=1.96):
    """95% Wilson score interval for a pass rate."""
    if n == 0:
        return 0.0, 1.0
    p = passes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def verdict(passes, n, required, at_cap=False):
    """PASS / FAIL / INCONCLUSIVE for one case. Safety-critical cases use required=1.0 (zero tolerance)."""
    if required >= 1.0:
        return "PASS" if passes == n else "FAIL"
    low, high = wilson(passes, n)
    if low >= required:
        return "PASS"
    if high < required:
        return "FAIL"
    if at_cap:   # enough evidence collected: decide on the observed rate, and report the variance
        return "PASS" if passes / n >= required else "FAIL"
    return "INCONCLUSIVE"


def load_quarantine(today=None):
    """Quarantined cases still run and are reported, but don't block. Expired entries do block."""
    today = today or date.today().isoformat()
    entries = json.loads(QUARANTINE_FILE.read_text()) if QUARANTINE_FILE.exists() else []
    active = {e["case_id"]: e for e in entries if e["expires"] >= today}
    expired = [e for e in entries if e["expires"] < today]
    return active, expired
