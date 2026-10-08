# Release criteria

Defined in [`release/criteria.json`](../release/criteria.json) and enforced by `python -m release.gate`.

## Before an agent goes live for a client

| Gate | Bar | Waivable? |
| --- | --- | --- |
| Intent accuracy | ≥ 95% | Yes |
| Slot exact match | ≥ 90% | Yes |
| Structured output valid | 100% | **No** |
| Transcript rubric mean | ≥ 4.5 / 5 | Yes |
| Golden cases passing | ≥ 95% | Yes |
| Critical case failures | 0 | **No** |
| PHI leaks | 0 | **No** |
| p95 turn latency | ≤ 1800 ms | Yes |
| Expired quarantines | 0 | **No** |
| Red-team critical failures | 0 | **No** |
| Red-team high failures | 0 | Yes |

## Holding the bar when a date is pushing on it

- A waivable gate can pass only with an entry in `release/waivers.json` that includes a **named approver**, a **reason** and an **expiry date**. The decision is visible and owned, not quietly skipped.
- Privacy, safety and schema gates **can't be waived**. A launch date is not a reason to disclose patient information.
- The gate's output ([example GO](examples/release-decision-v1.md), [example NO-GO](examples/release-decision-v2.md)) explains why each gate matters, so the conversation with stakeholders is about risk, not opinions.

## What has to stay true after launch

Production monitoring checks these every day ([production-monitoring.md](production-monitoring.md)):

| SLO | Bar |
| --- | --- |
| Intent accuracy on reviewed live calls | ≥ 93% |
| Mean STT confidence | ≥ 0.85 |
| p95 turn latency | ≤ 2000 ms |
| Escalation rate | ≤ 15% |
| PHI leaks | 0 |
