"""Production monitoring: drift is detected after it starts, not before, and routed to the right team."""
from functools import lru_cache

from monitoring.monitor import analyze, psi
from monitoring.simulate_production import generate


@lru_cache
def result():
    return analyze(generate(days=14, calls=150, drift_day=10), rate=0.1)


def test_no_alerts_before_drift_starts():
    assert not [a for a in result()["alerts"] if a["day"] < 10]


def test_audio_degradation_is_detected_and_routed_to_voice_infra():
    alerts = [a for a in result()["alerts"] if "Transcription" in a["title"]]
    assert alerts and alerts[0]["day"] == 10
    assert alerts[0]["owner"] == "voice-infra"
    assert all("--audio" in x["repro"] for x in alerts[0]["examples"])


def test_intent_mix_shift_is_detected():
    assert any("intent mix" in a["title"] for a in result()["alerts"])


def test_no_phi_leaks_in_production():
    assert all(d["phi_leaks"] == 0 for d in result()["daily"].values())


def test_psi_is_zero_for_identical_distributions():
    assert psi({"a": 10, "b": 5}, {"a": 20, "b": 10}) == 0.0
