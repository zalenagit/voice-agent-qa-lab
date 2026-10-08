"""Quality in production: sample live calls, track daily metrics, detect drift, route alerts.

    python -m monitoring.monitor reports/production_calls.jsonl --sample-rate 0.1

Sampled calls are the ones a reviewer would label; here the synthetic ground truth
stands in for that label. Alerts name the layer and the owning team, with call IDs
and replay commands, so the right engineer sees it before the client does.
"""
import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OWNERS = json.loads((ROOT / "owners.json").read_text())
SLOS = {c["id"]: c for c in json.loads((ROOT / "release" / "criteria.json").read_text())["post_launch"]}
BASELINE_DAYS = 7


def sampled(record, rate):
    h = int(hashlib.sha256(record["call_id"].encode()).hexdigest(), 16) % 10000
    return h < rate * 10000


def p95(values):
    v = sorted(values)
    return v[int(0.95 * (len(v) - 1))] if v else 0


def psi(expected, actual):
    """Population stability index between two category distributions."""
    keys = set(expected) | set(actual)
    te, ta = sum(expected.values()), sum(actual.values())
    total = 0.0
    for k in keys:
        e = max(expected.get(k, 0) / te, 1e-4)
        a = max(actual.get(k, 0) / ta, 1e-4)
        total += (a - e) * math.log(a / e)
    return total


def day_metrics(calls):
    return {
        "calls_reviewed": len(calls),
        "sampled_intent_accuracy": round(sum(c["first_intent"] == c["expected_intent"] for c in calls) / len(calls), 3),
        "stt_confidence_mean": round(sum(c["stt_confidence"] for c in calls) / len(calls), 3),
        "p95_turn_latency_ms": p95([c["max_turn_latency_ms"] for c in calls]),
        "escalation_rate": round(sum(c["escalated"] for c in calls) / len(calls), 3),
        "phi_leaks": sum(c["phi_leak"] for c in calls),
        "packet_loss_mean": round(sum(c["packet_loss"] for c in calls) / len(calls), 4),
        "intents": Counter(c["expected_intent"] for c in calls),
        "stt_ms_mean": round(sum(c["layer_ms"]["stt"] for c in calls) / len(calls)),
    }


def analyze(records, rate=0.1):
    days = sorted({r["day"] for r in records})
    sample = [r for r in records if sampled(r, rate)]
    daily = {d: day_metrics([r for r in sample if r["day"] == d]) for d in days}
    base_days = [d for d in days if d <= BASELINE_DAYS]
    base = day_metrics([r for r in sample if r["day"] in base_days])
    # Intent mix uses ALL calls' predicted intents: no labels needed, so no sampling noise
    base_mix = Counter(r["first_intent"] for r in records if r["day"] in base_days)
    alerts, open_alerts = [], {}

    def alert(day, layer, title, evidence, calls):
        key = (layer, title)
        if key in open_alerts and open_alerts[key]["days"][-1] == day - 1:   # ongoing: don't page again
            open_alerts[key]["days"].append(day)
            return
        owner = OWNERS.get(layer, OWNERS["unknown"])
        examples = calls[:3]
        alerts.append({"day": day, "days": [day], "layer": layer, "owner": owner["team"], "contact": owner["contact"],
                       "title": title, "evidence": evidence,
                       "examples": [{"call_id": c["call_id"], "repro":
                                     f"python -m agent.replay --scenario {c['scenario_id']} --seed {c['seed']} "
                                     f"--audio '{json.dumps(c['audio'])}' --triage"} for c in examples]})
        open_alerts[key] = alerts[-1]

    for d in days:
        if d in base_days:
            continue
        m, calls = daily[d], [r for r in sample if r["day"] == d]
        conf_drop = base["stt_confidence_mean"] - m["stt_confidence_mean"]
        if conf_drop > 0.04 or m["stt_confidence_mean"] < SLOS["stt_confidence_mean"]["value"]:
            net = m["packet_loss_mean"] > base["packet_loss_mean"] + 0.01
            bad = sorted(calls, key=lambda c: c["stt_confidence"])
            alert(d, "telephony" if net else "stt",
                  "Transcription quality dropped" + (" alongside higher packet loss" if net else ""),
                  [f"STT confidence {base['stt_confidence_mean']} -> {m['stt_confidence_mean']}",
                   f"packet loss {base['packet_loss_mean']:.1%} -> {m['packet_loss_mean']:.1%}"], bad)
        acc_drop = base["sampled_intent_accuracy"] - m["sampled_intent_accuracy"]
        if acc_drop > 0.05 or m["sampled_intent_accuracy"] < SLOS["sampled_intent_accuracy"]["value"]:
            wrong = [c for c in calls if c["first_intent"] != c["expected_intent"]]
            net = m["packet_loss_mean"] > base["packet_loss_mean"] + 0.01
            layer = "telephony" if net else ("stt" if conf_drop > 0.04 else "model")   # route to the root cause
            alert(d, layer, "Intent accuracy on reviewed calls dropped",
                  [f"accuracy {base['sampled_intent_accuracy']} -> {m['sampled_intent_accuracy']}",
                   f"{len(wrong)} misrouted of {len(calls)} reviewed"], wrong)
        if m["p95_turn_latency_ms"] > max(SLOS["p95_turn_latency_ms"]["value"], base["p95_turn_latency_ms"] * 1.25):
            alert(d, "stt", "Turn latency regressed",
                  [f"p95 {base['p95_turn_latency_ms']} -> {m['p95_turn_latency_ms']} ms",
                   f"mean STT time {base['stt_ms_mean']} -> {m['stt_ms_mean']} ms"],
                  sorted(calls, key=lambda c: -c["max_turn_latency_ms"]))
        today_mix = Counter(r["first_intent"] for r in records if r["day"] == d)
        drift = psi(base_mix, today_mix)
        if drift > 0.2:
            alert(d, "model", "Caller intent mix shifted: golden set may no longer represent traffic",
                  [f"PSI {drift:.2f} on all {sum(today_mix.values())} calls (threshold 0.2)",
                   f"top intents today: {today_mix.most_common(3)}"], calls)
        if m["phi_leaks"]:
            alert(d, "policy", "PHI disclosed on a production call", [f"{m['phi_leaks']} call(s)"],
                  [c for c in calls if c["phi_leak"]])
    return {"sample_rate": rate, "baseline": {k: v for k, v in base.items() if k != "intents"},
            "daily": {d: {k: v for k, v in m.items() if k != "intents"} for d, m in daily.items()},
            "alerts": alerts}


def to_markdown(result):
    out = ["# Production quality report", "",
           f"Sampled {result['sample_rate']:.0%} of calls for review. Baseline = days 1-{BASELINE_DAYS}.", "",
           "| Day | Reviewed | Intent acc. | STT conf. | p95 latency (ms) | Escalation | PHI leaks |",
           "| --- | --- | --- | --- | --- | --- | --- |"]
    for d, m in result["daily"].items():
        out.append(f"| {d} | {m['calls_reviewed']} | {m['sampled_intent_accuracy']:.0%} | {m['stt_confidence_mean']} | "
                   f"{m['p95_turn_latency_ms']} | {m['escalation_rate']:.0%} | {m['phi_leaks']} |")
    out += ["", f"## Alerts ({len(result['alerts'])})", ""]
    for a in result["alerts"]:
        span = f"Day {a['days'][0]}" + (f"-{a['days'][-1]} (ongoing)" if len(a["days"]) > 1 else "")
        out += [f"### {span}: {a['title']}", f"- **Route to:** {a['owner']} ({a['contact']}), layer `{a['layer']}`"]
        out += [f"- {e}" for e in a["evidence"]]
        out += [f"- Example `{x['call_id']}`: `{x['repro']}`" for x in a["examples"]] + [""]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--sample-rate", type=float, default=0.1)
    ap.add_argument("--out", default="reports/production-report.md")
    args = ap.parse_args()
    records = [json.loads(l) for l in Path(args.log).read_text().splitlines() if l.strip()]
    result = analyze(records, args.sample_rate)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(to_markdown(result))
    print(to_markdown(result))
    sys.exit(1 if any(a["layer"] == "policy" for a in result["alerts"]) else 0)


if __name__ == "__main__":
    main()
