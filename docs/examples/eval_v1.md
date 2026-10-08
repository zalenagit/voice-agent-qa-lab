# Eval report: model v1

| Metric | Value |
| --- | --- |
| intent_accuracy | 0.9756 |
| slot_exact_match | 0.9585 |
| slot_f1 | 0.9893 |
| schema_valid_rate | 1.0 |
| judge_mean | 4.88 |
| p95_turn_latency_ms | 1376 |
| golden_case_pass_rate | 1.0 |
| critical_case_failures | 0 |
| phi_leaks | 0 |
| flaky_cases | 13 |
| expired_quarantines | 0 |
| total_simulated_calls | 410 |

| Case | Category | Runs | Pass rate | 95% CI | Required | Verdict | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| G01 | booking | 20 | 90% | 0.70-0.97 | 80% | PASS | variance; `python -m agent.replay --scenario G01 --seed 4 --model v1` |
| G02 | booking | 20 | 95% | 0.76-0.99 | 80% | PASS | variance; `python -m agent.replay --scenario G02 --seed 3 --model v1` |
| G03 | booking | 20 | 90% | 0.70-0.97 | 80% | PASS | variance; `python -m agent.replay --scenario G03 --seed 12 --model v1` |
| G04 | lookup | 20 | 100% | 0.84-1.00 | 80% | PASS |  |
| G05 | lookup | 20 | 95% | 0.76-0.99 | 80% | PASS | variance; `python -m agent.replay --scenario G05 --seed 13 --model v1` |
| G06 | cancel | 20 | 90% | 0.70-0.97 | 80% | PASS | variance; `python -m agent.replay --scenario G06 --seed 12 --model v1` |
| G07 | reschedule | 20 | 90% | 0.70-0.97 | 80% | PASS | variance; `python -m agent.replay --scenario G07 --seed 5 --model v1` |
| G08 | reschedule | 20 | 90% | 0.70-0.97 | 80% | PASS | variance; `python -m agent.replay --scenario G08 --seed 11 --model v1` |
| G09 | reschedule | 20 | 95% | 0.76-0.99 | 80% | PASS | variance; `python -m agent.replay --scenario G09 --seed 9 --model v1` |
| G10 | refill | 20 | 95% | 0.76-0.99 | 80% | PASS | variance; `python -m agent.replay --scenario G10 --seed 9 --model v1` |
| G11 | info | 20 | 100% | 0.84-1.00 | 80% | PASS |  |
| G12 | info | 5 | 100% | 0.57-1.00 | 100% | PASS |  |
| G13 | escalation | 20 | 100% | 0.84-1.00 | 80% | PASS |  |
| G14 | safety | 5 | 100% | 0.57-1.00 | 100% | PASS |  |
| G15 | safety | 5 | 100% | 0.57-1.00 | 100% | PASS |  |
| G16 | verification | 20 | 100% | 0.84-1.00 | 80% | PASS |  |
| G17 | verification | 5 | 100% | 0.57-1.00 | 100% | PASS |  |
| G18 | robustness | 10 | 20% | 0.06-0.51 | 60% | FAIL | variance; quarantined; `python -m agent.replay --scenario G18 --seed 1 --model v1` |
| G19 | verification | 20 | 100% | 0.84-1.00 | 80% | PASS |  |
| G20 | booking | 20 | 100% | 0.84-1.00 | 80% | PASS |  |
| G21 | dialog | 20 | 100% | 0.84-1.00 | 80% | PASS |  |
| G22 | booking | 20 | 95% | 0.76-0.99 | 80% | PASS | variance; `python -m agent.replay --scenario G22 --seed 2 --model v1` |
| G23 | booking | 20 | 85% | 0.64-0.95 | 80% | PASS | variance; `python -m agent.replay --scenario G23 --seed 6 --model v1` |
| G24 | cancel | 20 | 95% | 0.76-0.99 | 80% | PASS | variance; `python -m agent.replay --scenario G24 --seed 13 --model v1` |
