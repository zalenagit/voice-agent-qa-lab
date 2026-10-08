"""Model regression detection, red-team results and the release gate."""
from functools import lru_cache

from evals.compare import compare
from evals.run_eval import run as run_eval
from redteam.run import run as run_redteam
from release.gate import evaluate


@lru_cache
def report(model):
    return run_eval(model)


def test_baseline_model_meets_every_release_gate():
    result = evaluate(report("v1"), run_redteam(), waivers=[])
    assert result["decision"] == "GO", result["blocking"]


def test_candidate_model_regression_is_caught():
    metric_rows, case_rows, regressions = compare(report("v1"), report("v2"))
    assert regressions
    assert any(r[0] == "schema_valid_rate" and r[4] == "REGRESSION" for r in metric_rows)
    assert any(r[0] == "G08" and r[5] == "REGRESSION" for r in case_rows)   # "move my appointment"


def test_candidate_model_is_blocked_from_release():
    assert evaluate(report("v2"), run_redteam(model="v2"), waivers=[])["decision"] == "NO-GO"


def test_guardrails_hold_under_red_team_attack():
    s = run_redteam()["summary"]
    assert s["critical_failures"] == 0 and s["high_failures"] == 0


def test_red_team_suite_catches_a_vulnerable_agent():
    """Test the tests: with guardrails off, the suite must fail loudly."""
    assert run_redteam(guardrails=False)["summary"]["critical_failures"] >= 5


def test_waiver_needs_a_waivable_gate_and_an_unexpired_date():
    ev = {"metrics": {**report("v1")["metrics"], "intent_accuracy": 0.93, "phi_leaks": 1}}
    rt = run_redteam()
    waivers = [{"gate": "intent_accuracy", "approver": "Head of Clinical Ops", "reason": "pilot", "expires": "2099-01-01"},
               {"gate": "phi_leaks", "approver": "Sales VP", "reason": "launch date", "expires": "2099-01-01"}]
    result = evaluate(ev, rt, waivers=waivers)
    status = {g["gate"]: g["status"] for g in result["gates"]}
    assert status["intent_accuracy"].startswith("WAIVED")
    assert status["phi_leaks"] == "FAIL (not waivable)"
    assert result["decision"] == "NO-GO"
    expired = [{**waivers[0], "expires": "2020-01-01"}]
    assert "intent_accuracy" in evaluate(ev, rt, waivers=expired)["blocking"]
