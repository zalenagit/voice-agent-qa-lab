"""Run the golden set against a model version and score it.

    python -m evals.run_eval --model v1 --out reports/eval_v1.json

Every case runs with several seeds (simulated calls). Runs grow from --min-runs
toward --max-runs only for cases whose result is statistically inconclusive.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from agent.pipeline import AgentConfig, run_call
from evals.flake import load_quarantine, verdict, wilson
from evals.judge import judge
from evals.schema import validate

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "scenarios" / "golden.json"


def merged_slots(trace):
    slots = {}
    for t in trace["turns"]:
        if t.get("parsed"):
            slots.update(t["parsed"].get("slots") or {})
    return slots


def turn_latencies(trace):
    per_turn = Counter()
    for s in trace["spans"]:
        if s["turn"] > 0:
            per_turn[s["turn"]] += s["duration_ms"]
    return list(per_turn.values())


def score_run(case, trace):
    exp = case["expect"]
    first = trace["turns"][0].get("parsed") if trace["turns"] else None
    intent_ok = bool(first) and first.get("intent") == exp["first_intent"]
    got, want = merged_slots(trace), exp.get("slots", {})
    tp = sum(1 for k, v in want.items() if got.get(k) == v)
    fp = sum(1 for k, v in got.items() if want.get(k) != v)
    fn = len(want) - tp
    schema_errors = [e for t in trace["turns"] if "model_output_raw" in t for e in validate(t["model_output_raw"])]
    score, detail = judge(trace, exp)
    reasons = []
    if not intent_ok:
        reasons.append(f"first intent {first.get('intent') if first else None} != {exp['first_intent']}")
    if got != want:
        reasons.append(f"slots {got} != {want}")
    if schema_errors:
        reasons.append(f"schema: {schema_errors[:2]}")
    reasons += [f"{k}: {v['reason']}" for k, v in detail.items()
                if not v["pass"] and k in ("task", "info", "safety")]
    return {
        "passed": not reasons, "intent_ok": intent_ok, "slot_exact": got == want,
        "tp": tp, "fp": fp, "fn": fn, "schema_turns": sum(1 for t in trace["turns"] if "model_output_raw" in t),
        "schema_bad_turns": sum(1 for t in trace["turns"] if "model_output_raw" in t and validate(t["model_output_raw"])),
        "judge_score": score, "phi_leak": "PHI leaks: []" not in detail["safety"]["reason"],
        "latencies": turn_latencies(trace), "reasons": reasons,
    }


def run(model="v1", temperature=1.0, min_runs=5, max_runs=20, cases=None):
    golden = json.loads(GOLDEN.read_text())
    if cases:
        golden = [c for c in golden if c["id"] in cases]
    config = AgentConfig(model_version=model, temperature=temperature)
    quarantine, expired = load_quarantine()
    results, all_runs = [], []

    for case in golden:
        exp = case["expect"]
        required = 1.0 if exp.get("critical") else exp.get("min_pass_rate", 0.8)
        runs, n = [], min_runs
        while True:
            for seed in range(len(runs), n):
                runs.append((seed, score_run(case, run_call(case, seed, config))))
            passes = sum(1 for _, r in runs if r["passed"])
            v = verdict(passes, len(runs), required, at_cap=len(runs) >= max_runs)
            if v != "INCONCLUSIVE":
                break
            n = min(max_runs, n + 5)
        all_runs += [r for _, r in runs]
        first_fail = next(((s, r) for s, r in runs if not r["passed"]), None)
        low, high = wilson(passes, len(runs))
        results.append({
            "id": case["id"], "category": case["category"], "description": case["description"],
            "critical": bool(exp.get("critical")), "required": required,
            "runs": len(runs), "passes": passes, "pass_rate": round(passes / len(runs), 3),
            "ci95": [round(low, 3), round(high, 3)], "verdict": v,
            "flaky": 0 < passes < len(runs), "quarantined": case["id"] in quarantine and not exp.get("critical"),
            "example_failure": None if not first_fail else {
                "seed": first_fail[0], "reasons": first_fail[1]["reasons"],
                "repro": f"python -m agent.replay --scenario {case['id']} --seed {first_fail[0]} --model {model}"},
        })

    lat = sorted(l for r in all_runs for l in r["latencies"])
    tp, fp, fn = (sum(r[k] for r in all_runs) for k in ("tp", "fp", "fn"))
    blocking = [r for r in results if not r["quarantined"]]
    metrics = {
        "intent_accuracy": round(sum(r["intent_ok"] for r in all_runs) / len(all_runs), 4),
        "slot_exact_match": round(sum(r["slot_exact"] for r in all_runs) / len(all_runs), 4),
        "slot_f1": round(2 * tp / (2 * tp + fp + fn), 4) if tp else 0.0,
        "schema_valid_rate": round(1 - sum(r["schema_bad_turns"] for r in all_runs) /
                                   max(1, sum(r["schema_turns"] for r in all_runs)), 4),
        "judge_mean": round(sum(r["judge_score"] for r in all_runs) / len(all_runs), 3),
        "p95_turn_latency_ms": lat[int(0.95 * (len(lat) - 1))] if lat else 0,
        "golden_case_pass_rate": round(sum(r["verdict"] == "PASS" for r in blocking) / len(blocking), 4),
        "critical_case_failures": sum(1 for r in results if r["critical"] and r["verdict"] != "PASS"),
        "phi_leaks": sum(r["phi_leak"] for r in all_runs),
        "flaky_cases": sum(r["flaky"] for r in results),
        "expired_quarantines": len(expired),
        "total_simulated_calls": len(all_runs),
    }
    return {"model": model, "temperature": temperature, "metrics": metrics, "cases": results}


def to_markdown(report):
    m = report["metrics"]
    lines = [f"# Eval report: model {report['model']}", "", "| Metric | Value |", "| --- | --- |"]
    lines += [f"| {k} | {v} |" for k, v in m.items()]
    lines += ["", "| Case | Category | Runs | Pass rate | 95% CI | Required | Verdict | Notes |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for c in report["cases"]:
        notes = []
        if c["flaky"]:
            notes.append("variance")
        if c["quarantined"]:
            notes.append("quarantined")
        if c["example_failure"]:
            notes.append(f"`{c['example_failure']['repro']}`")
        lines.append(f"| {c['id']} | {c['category']} | {c['runs']} | {c['pass_rate']:.0%} | "
                     f"{c['ci95'][0]:.2f}-{c['ci95'][1]:.2f} | {c['required']:.0%} | {c['verdict']} | {'; '.join(notes)} |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="v1")
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--min-runs", type=int, default=5)
    ap.add_argument("--max-runs", type=int, default=20)
    ap.add_argument("--out", default="reports/eval.json")
    args = ap.parse_args()
    report = run(args.model, args.temperature, args.min_runs, args.max_runs)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    out.with_suffix(".md").write_text(to_markdown(report))
    print(json.dumps(report["metrics"], indent=2))
    print(f"Saved {out} and {out.with_suffix('.md')}")


if __name__ == "__main__":
    main()
