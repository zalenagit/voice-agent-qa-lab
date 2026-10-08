"""Generate a synthetic production call log (one JSON record per call) with drift injected.

    python -m monitoring.simulate_production --days 14 --calls 150 --drift-day 10

From --drift-day, a carrier codec change degrades audio on most calls and the
intent mix shifts toward refills: the kind of slow degradation nobody notices
until a client complains.
"""
import argparse
import json
import random
from pathlib import Path

from agent.guardrails import phi_in_text
from agent.pipeline import AgentConfig, run_call
from evals.judge import agent_lines, verified_patient

ROOT = Path(__file__).resolve().parent.parent
BASE_MIX = {"booking": 30, "lookup": 20, "cancel": 10, "reschedule": 15, "refill": 10, "info": 10, "escalation": 5}
DRIFT_MIX = {"booking": 25, "lookup": 15, "cancel": 8, "reschedule": 12, "refill": 30, "info": 7, "escalation": 3}
DRIFT_AUDIO = {"packet_loss": 0.04, "snr_db": 16, "codec": "AMR-NB"}


def generate(days=14, calls=150, drift_day=10, seed=42):
    rng = random.Random(seed)
    golden = json.loads((ROOT / "scenarios" / "golden.json").read_text())
    by_cat = {}
    for g in golden:
        by_cat.setdefault(g["category"], []).append(g)
    records = []
    for day in range(1, days + 1):
        drift = day >= drift_day
        mix = DRIFT_MIX if drift else BASE_MIX
        cats = [c for c in mix if c in by_cat]
        for n in range(calls):
            cat = rng.choices(cats, weights=[mix[c] for c in cats])[0]
            scenario = dict(rng.choice(by_cat[cat]))
            if drift and rng.random() < 0.6:
                scenario["audio"] = DRIFT_AUDIO
            call_seed = day * 1000 + n
            trace = run_call(scenario, call_seed, AgentConfig())
            stt = [s for s in trace["spans"] if s["layer"] == "stt"]
            per_turn = {}
            for s in trace["spans"]:
                if s["turn"] > 0:
                    per_turn[s["turn"]] = per_turn.get(s["turn"], 0) + s["duration_ms"]
            first = trace["turns"][0].get("parsed") if trace["turns"] else None
            records.append({
                "call_id": f"PROD-D{day:02d}-{n:04d}", "day": day, "scenario_id": scenario["id"],
                "seed": call_seed, "audio": scenario.get("audio", {}),
                "expected_intent": scenario["expect"]["first_intent"],
                "first_intent": first.get("intent") if first else None,
                "stt_confidence": round(sum(s["detail"]["confidence"] for s in stt) / max(1, len(stt)), 3),
                "max_turn_latency_ms": max(per_turn.values(), default=0),
                "layer_ms": {l: sum(s["duration_ms"] for s in trace["spans"] if s["layer"] == l)
                             for l in ("stt", "model", "integration", "tts")},
                "escalated": trace["outcome"]["status"] == "escalated",
                "phi_leak": bool(phi_in_text(" ".join(agent_lines(trace)), verified_patient(trace))),
                "packet_loss": scenario.get("audio", {}).get("packet_loss", 0.0),
            })
    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--calls", type=int, default=150)
    ap.add_argument("--drift-day", type=int, default=10)
    ap.add_argument("--out", default="reports/production_calls.jsonl")
    args = ap.parse_args()
    recs = generate(args.days, args.calls, args.drift_day)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    print(f"Wrote {len(recs)} production call records to {args.out}")


if __name__ == "__main__":
    main()
