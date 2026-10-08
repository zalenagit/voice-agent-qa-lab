"""Compare a candidate model's eval report against the baseline and flag regressions.

    python -m evals.compare reports/eval_v1.json reports/eval_v2.json

Regression coverage that still holds when the model changes: the same golden set,
the same scoring, and explicit tolerances, so "the new model feels better" becomes
a measurable yes or no.
"""
import argparse
import json
import sys
from pathlib import Path

# metric -> (direction, allowed change). "up" = higher is better.
TOLERANCES = {
    "intent_accuracy": ("up", 0.02),
    "slot_exact_match": ("up", 0.03),
    "slot_f1": ("up", 0.02),
    "schema_valid_rate": ("up", 0.0),
    "judge_mean": ("up", 0.15),
    "p95_turn_latency_ms": ("down", 250),
    "critical_case_failures": ("down", 0),
    "phi_leaks": ("down", 0),
}


def compare(base, cand):
    metric_rows, regressions = [], []
    for name, (direction, tol) in TOLERANCES.items():
        b, c = base["metrics"][name], cand["metrics"][name]
        delta = c - b
        worse = (-delta if direction == "up" else delta) > tol
        metric_rows.append((name, b, c, round(delta, 4), "REGRESSION" if worse else "ok"))
        if worse:
            regressions.append(f"{name}: {b} -> {c} (tolerance {tol})")

    base_cases = {c["id"]: c for c in base["cases"]}
    case_rows = []
    for c in cand["cases"]:
        b = base_cases.get(c["id"])
        if not b:
            continue
        status = "ok"
        if b["verdict"] == "PASS" and c["verdict"] == "FAIL":
            status = "REGRESSION"
            regressions.append(f"{c['id']} ({c['description']}): PASS -> FAIL")
        elif b["verdict"] == "FAIL" and c["verdict"] == "PASS":
            status = "fixed"
        case_rows.append((c["id"], b["pass_rate"], c["pass_rate"], b["verdict"], c["verdict"], status,
                          (c["example_failure"] or {}).get("reasons", [""])[0][:90]))
    return metric_rows, case_rows, regressions


def to_markdown(base, cand, metric_rows, case_rows, regressions):
    out = [f"# Model comparison: {base['model']} (baseline) vs {cand['model']} (candidate)", "",
           f"**Result: {'BLOCK - ' + str(len(regressions)) + ' regression(s)' if regressions else 'PASS - no regressions'}**", "",
           "| Metric | Baseline | Candidate | Change | Status |", "| --- | --- | --- | --- | --- |"]
    out += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]:+} | {r[4]} |" for r in metric_rows]
    out += ["", "| Case | Baseline rate | Candidate rate | Baseline | Candidate | Status | First failure reason |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    out += [f"| {r[0]} | {r[1]:.0%} | {r[2]:.0%} | {r[3]} | {r[4]} | {r[5]} | {r[6]} |" for r in case_rows]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline")
    ap.add_argument("candidate")
    ap.add_argument("--out", default="reports/compare.md")
    args = ap.parse_args()
    base, cand = json.loads(Path(args.baseline).read_text()), json.loads(Path(args.candidate).read_text())
    metric_rows, case_rows, regressions = compare(base, cand)
    md = to_markdown(base, cand, metric_rows, case_rows, regressions)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(md)
    print(md)
    sys.exit(1 if regressions else 0)


if __name__ == "__main__":
    main()
