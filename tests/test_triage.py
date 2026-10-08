"""Layer isolation: each injected fault must be blamed on the right layer."""
import json
from pathlib import Path

import pytest

from agent.pipeline import AgentConfig, run_call
from triage.isolate import isolate, wer
from triage.ticket import make_ticket

ROOT = Path(__file__).parent.parent
FAULTS = json.loads((ROOT / "scenarios" / "faults.json").read_text())


@pytest.mark.parametrize("scenario", FAULTS, ids=[f"{f['id']}-{f['expected_layer']}" for f in FAULTS])
def test_fault_is_isolated_to_the_right_layer(scenario):
    for seed in range(5):
        trace = run_call(scenario, seed, AgentConfig(model_version=scenario.get("model_version", "v1")))
        verdict = isolate(trace, scenario.get("expect"))
        assert verdict["layer"] == scenario["expected_layer"], (seed, verdict)
        assert verdict["evidence"], "a verdict must come with evidence"


def test_packet_loss_is_blamed_on_the_network_not_stt():
    f04 = next(f for f in FAULTS if f["id"] == "F04")
    verdict = isolate(run_call(f04, 1), f04["expect"])
    assert verdict["layer"] == "telephony"
    assert any("packet_loss" in e for e in verdict["evidence"])


def test_business_409_is_not_reported_as_an_integration_fault():
    g03 = next(g for g in json.loads((ROOT / "scenarios" / "golden.json").read_text()) if g["id"] == "G03")
    assert isolate(run_call(g03, 0), g03["expect"])["layer"] == "none"


def test_ticket_contains_a_working_repro_command():
    f06 = next(f for f in FAULTS if f["id"] == "F06")
    trace = run_call(f06, 2)
    ticket = make_ticket(trace, isolate(trace), f06)
    assert "python -m agent.replay --scenario F06 --seed 2 --model v1" in ticket
    assert "integrations" in ticket          # routed to the owning team
    assert "## Latency trace" in ticket


@pytest.mark.parametrize("ref, hyp, expected", [
    ("book an appointment", "book an appointment", 0.0),
    ("book an appointment", "book appointment", 1 / 3),
    ("one two three four", "", 1.0),
])
def test_word_error_rate(ref, hyp, expected):
    assert wer(ref, hyp) == pytest.approx(expected)
