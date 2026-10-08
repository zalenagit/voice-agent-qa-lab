"""Turn a bad call into a reproducible ticket an engineer can act on."""
import json
from pathlib import Path

OWNERS = json.loads((Path(__file__).resolve().parent.parent / "owners.json").read_text())


def latency_table(trace):
    rows = ["| Turn | Layer | Duration (ms) | Status |", "| --- | --- | --- | --- |"]
    rows += [f"| {s['turn']} | {s['layer']} | {s['duration_ms']} | {s['status']} |" for s in trace["spans"]]
    return "\n".join(rows)


def make_ticket(trace, verdict, scenario):
    layer = verdict["layer"]
    owner = OWNERS.get(layer, OWNERS["unknown"])
    model = trace["config"]["model_version"]
    turns = []
    for t in trace["turns"]:
        turns.append(f"- **Caller said:** {t['caller_said']}")
        if "heard" in t:
            turns.append(f"  - **STT heard:** {t['heard'] or '(silence)'} (confidence {t.get('stt_confidence')})")
        if t.get("model_output_raw"):
            turns.append(f"  - **Model output:** `{t['model_output_raw']}`")
        if t.get("agent_said"):
            turns.append(f"  - **Agent said:** {t['agent_said']}")
    errors = "\n".join(f"- `{e['layer']}` {e['code']}: {e['msg']}" for e in trace["outcome"]["errors"]) or "- none"
    return f"""# [{layer.upper()}] {verdict['summary']}

| Field | Value |
| --- | --- |
| Severity | {verdict['severity']} |
| Suspected layer | {layer} |
| Owner | {owner['team']} ({owner['contact']}) |
| Call ID | {trace['call_id']} |
| Scenario | {scenario.get('id')}: {scenario.get('description', '')} |
| Model version | {model} |
| Audio | {trace['audio'] or 'clean line'} |
| Injected faults (test only) | {', '.join(trace['faults']) or 'none'} |

## Reproduce

```bash
python -m agent.replay --scenario {scenario.get('id')} --seed {trace['seed']} --model {model} --triage
```

The simulation is seeded, so this command reproduces the exact same call.

## Evidence

{chr(10).join('- ' + e for e in verdict['evidence']) or '- (none)'}

## Expected vs actual

- **Expected:** {scenario.get('expect', {}).get('first_intent', 'call completes and the caller hears a correct reply')}
- **Actual outcome:** {trace['outcome']['status']}, actions={trace['outcome']['actions']}

## Errors logged

{errors}

## Transcript

{chr(10).join(turns)}

## Latency trace

{latency_table(trace)}
"""
