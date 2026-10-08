"""Release gate: what has to be true before the agent goes live for a client.

    python -m release.gate reports/eval_v1.json reports/redteam.json

Exit code 0 = GO, 1 = NO-GO. A failing waivable gate can only pass with a waiver
that names an approver, a reason and an expiry date (release/waivers.json).
Privacy, safety and schema gates can't be waived, whatever the deployment date.
"""
import argparse
import json
import operator
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
OPS = {">=": operator.ge, "<=": operator.le, "==": operator.eq}


def evaluate(eval_report, redteam_report, criteria=None, waivers=None, today=None):
    criteria = criteria or json.loads((HERE / "criteria.json").read_text())
    waivers = waivers if waivers is not None else json.loads((HERE / "waivers.json").read_text())
    today = today or date.today().isoformat()
    sources = {"eval": eval_report["metrics"], "redteam": redteam_report["summary"]}
    rows, blocking = [], []
    for c in criteria["pre_launch"]:
        actual = sources[c["source"]].get(c["id"])
        ok = actual is not None and OPS[c["op"]](actual, c["value"])
        status = "PASS" if ok else "FAIL"
        if not ok:
            w = next((w for w in waivers if w["gate"] == c["id"] and w["expires"] >= today), None)
            if w and c["waivable"]:
                status = f"WAIVED by {w['approver']} until {w['expires']}"
            else:
                if w and not c["waivable"]:
                    status = "FAIL (not waivable)"
                blocking.append(c["id"])
        rows.append({"gate": c["id"], "required": f"{c['op']} {c['value']}", "actual": actual,
                     "status": status, "why": c["why"]})
    return {"decision": "NO-GO" if blocking else "GO", "blocking": blocking, "gates": rows}


def to_markdown(result):
    out = [f"# Release decision: {result['decision']}", ""]
    if result["blocking"]:
        out += [f"Blocking gates: {', '.join(result['blocking'])}", ""]
    out += ["| Gate | Required | Actual | Status | Why it matters |", "| --- | --- | --- | --- | --- |"]
    out += [f"| {r['gate']} | {r['required']} | {r['actual']} | {r['status']} | {r['why']} |" for r in result["gates"]]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("eval_report")
    ap.add_argument("redteam_report")
    ap.add_argument("--out", default="reports/release-decision.md")
    args = ap.parse_args()
    result = evaluate(json.loads(Path(args.eval_report).read_text()), json.loads(Path(args.redteam_report).read_text()))
    md = to_markdown(result)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(md)
    print(md)
    sys.exit(0 if result["decision"] == "GO" else 1)


if __name__ == "__main__":
    main()
