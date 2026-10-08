"""Replay any scenario with a fixed seed, print the transcript and latency trace, and optionally triage it.

    python -m agent.replay --scenario G08 --seed 3 --model v2 --triage
    python -m agent.replay --scenario F04 --triage --ticket reports/ticket-F04.md
"""
import argparse
import json
from pathlib import Path

from agent.pipeline import AgentConfig, run_call

SCENARIO_FILES = ["golden.json", "faults.json", "redteam.json"]
ROOT = Path(__file__).resolve().parent.parent


def find_scenario(sid):
    for name in SCENARIO_FILES:
        for s in json.loads((ROOT / "scenarios" / name).read_text()):
            if s["id"] == sid:
                return s
    raise SystemExit(f"Scenario {sid} not found")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default=None)
    ap.add_argument("--audio", help='override line conditions, e.g. \'{"packet_loss": 0.04, "snr_db": 16}\'')
    ap.add_argument("--no-guardrails", action="store_true", help="demo only: shows what the red-team suite catches")
    ap.add_argument("--triage", action="store_true")
    ap.add_argument("--ticket", help="write a Markdown ticket to this path")
    ap.add_argument("--out", help="write the full trace JSON to this path")
    args = ap.parse_args()

    scenario = find_scenario(args.scenario)
    if args.audio:
        scenario = {**scenario, "audio": json.loads(args.audio)}
    config = AgentConfig(model_version=args.model or scenario.get("model_version", "v1"),
                         guardrails=not args.no_guardrails)
    trace = run_call(scenario, args.seed, config)

    print(f"Call {trace['call_id']}  model={config.model_version}  outcome={trace['outcome']['status']}")
    for t in trace["turns"]:
        print(f"  CALLER: {t['caller_said']}")
        if "heard" in t and t["heard"] != t["caller_said"]:
            print(f"  (STT heard: {t['heard'] or '(silence)'})")
        if t.get("agent_said"):
            print(f"  AGENT:  {t['agent_said']}")
    print("\n  spans: " + ", ".join(f"t{s['turn']}:{s['layer']}={s['duration_ms']}ms{'!' if s['status'] != 'ok' else ''}"
                                   for s in trace["spans"]))
    if args.out:
        Path(args.out).write_text(json.dumps(trace, indent=2))

    if args.triage or args.ticket:
        from triage.isolate import isolate
        from triage.ticket import make_ticket
        verdict = isolate(trace, scenario.get("expect"))
        print(f"\nTRIAGE: layer={verdict['layer']}  {verdict['summary']}")
        for e in verdict["evidence"]:
            print(f"  - {e}")
        if args.ticket:
            Path(args.ticket).parent.mkdir(parents=True, exist_ok=True)
            Path(args.ticket).write_text(make_ticket(trace, verdict, scenario))
            print(f"Ticket written to {args.ticket}")


if __name__ == "__main__":
    main()
