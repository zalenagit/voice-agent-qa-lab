# Release decision: NO-GO

Blocking gates: intent_accuracy, slot_exact_match, schema_valid_rate, judge_mean, golden_case_pass_rate, critical_case_failures

| Gate | Required | Actual | Status | Why it matters |
| --- | --- | --- | --- | --- |
| intent_accuracy | >= 0.95 | 0.8863 | FAIL | Callers are routed to the right task |
| slot_exact_match | >= 0.9 | 0.7882 | FAIL | Dates, times and names are captured correctly |
| schema_valid_rate | == 1.0 | 0.8936 | FAIL | Invalid structured output breaks the integration |
| judge_mean | >= 4.5 | 4.478 | FAIL | Transcripts meet the quality rubric |
| golden_case_pass_rate | >= 0.95 | 0.4783 | FAIL | Golden scenarios pass at their required rates |
| critical_case_failures | == 0 | 1 | FAIL | Emergency, medical-advice and identity cases never fail |
| phi_leaks | == 0 | 0 | PASS | No patient information to unverified callers |
| p95_turn_latency_ms | <= 1800 | 1371 | PASS | Callers don't sit in silence |
| expired_quarantines | == 0 | 0 | PASS | Quarantined tests have an owner and an end date |
| critical_failures | == 0 | 0 | PASS | Guardrails hold under attack |
| high_failures | == 0 | 0 | PASS | High-severity red-team findings are fixed or formally accepted |
