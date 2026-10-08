"""Statistical pass criteria for non-deterministic tests."""
import pytest

from evals import flake


def test_wilson_interval_known_value():
    low, high = flake.wilson(8, 10)
    assert low == pytest.approx(0.490, abs=0.01) and high == pytest.approx(0.943, abs=0.01)


@pytest.mark.parametrize("passes, n, required, at_cap, expected", [
    (20, 20, 0.8, False, "PASS"),          # strong evidence
    (5, 5, 0.8, False, "INCONCLUSIVE"),    # 5/5 is not yet proof of >= 80%
    (1, 10, 0.8, False, "FAIL"),           # clearly below the bar
    (17, 20, 0.8, True, "PASS"),           # at the cap: decide on the observed rate
    (15, 20, 0.8, True, "FAIL"),
    (4, 5, 1.0, False, "FAIL"),            # safety: zero tolerance
    (5, 5, 1.0, False, "PASS"),
])
def test_verdict(passes, n, required, at_cap, expected):
    assert flake.verdict(passes, n, required, at_cap) == expected


def test_expired_quarantine_is_reported(tmp_path, monkeypatch):
    q = tmp_path / "q.json"
    q.write_text('[{"case_id": "G99", "reason": "x", "owner": "qa", "ticket": "T-1", '
                 '"created": "2026-01-01", "expires": "2026-02-01"}]')
    monkeypatch.setattr(flake, "QUARANTINE_FILE", q)
    active, expired = flake.load_quarantine(today="2026-10-08")
    assert not active and expired[0]["case_id"] == "G99"
