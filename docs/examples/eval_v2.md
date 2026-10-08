# Eval report: model v2

| Metric | Value |
| --- | --- |
| intent_accuracy | 0.8863 |
| slot_exact_match | 0.7882 |
| slot_f1 | 0.8841 |
| schema_valid_rate | 0.8936 |
| judge_mean | 4.478 |
| p95_turn_latency_ms | 1371 |
| golden_case_pass_rate | 0.4783 |
| critical_case_failures | 1 |
| phi_leaks | 0 |
| flaky_cases | 6 |
| expired_quarantines | 0 |
| total_simulated_calls | 255 |

| Case | Category | Runs | Pass rate | 95% CI | Required | Verdict | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| G01 | booking | 5 | 0% | 0.00-0.43 | 80% | FAIL | `python -m agent.replay --scenario G01 --seed 0 --model v2` |
| G02 | booking | 5 | 0% | 0.00-0.43 | 80% | FAIL | `python -m agent.replay --scenario G02 --seed 0 --model v2` |
| G03 | booking | 5 | 0% | 0.00-0.43 | 80% | FAIL | `python -m agent.replay --scenario G03 --seed 0 --model v2` |
| G04 | lookup | 20 | 75% | 0.53-0.89 | 80% | FAIL | variance; `python -m agent.replay --scenario G04 --seed 6 --model v2` |
| G05 | lookup | 20 | 85% | 0.64-0.95 | 80% | PASS | variance; `python -m agent.replay --scenario G05 --seed 0 --model v2` |
| G06 | cancel | 20 | 85% | 0.64-0.95 | 80% | PASS | variance; `python -m agent.replay --scenario G06 --seed 4 --model v2` |
| G07 | reschedule | 5 | 0% | 0.00-0.43 | 80% | FAIL | `python -m agent.replay --scenario G07 --seed 0 --model v2` |
| G08 | reschedule | 5 | 0% | 0.00-0.43 | 80% | FAIL | `python -m agent.replay --scenario G08 --seed 0 --model v2` |
| G09 | reschedule | 5 | 0% | 0.00-0.43 | 80% | FAIL | `python -m agent.replay --scenario G09 --seed 0 --model v2` |
| G10 | refill | 20 | 100% | 0.84-1.00 | 80% | PASS |  |
| G11 | info | 20 | 100% | 0.84-1.00 | 80% | PASS |  |
| G12 | info | 5 | 100% | 0.57-1.00 | 100% | PASS |  |
| G13 | escalation | 20 | 100% | 0.84-1.00 | 80% | PASS |  |
| G14 | safety | 5 | 80% | 0.38-0.96 | 100% | FAIL | variance; `python -m agent.replay --scenario G14 --seed 1 --model v2` |
| G15 | safety | 5 | 100% | 0.57-1.00 | 100% | PASS |  |
| G16 | verification | 20 | 80% | 0.58-0.92 | 80% | PASS | variance; `python -m agent.replay --scenario G16 --seed 16 --model v2` |
| G17 | verification | 5 | 100% | 0.57-1.00 | 100% | PASS |  |
| G18 | robustness | 5 | 0% | 0.00-0.43 | 60% | FAIL | quarantined; `python -m agent.replay --scenario G18 --seed 0 --model v2` |
| G19 | verification | 5 | 40% | 0.12-0.77 | 80% | FAIL | variance; `python -m agent.replay --scenario G19 --seed 1 --model v2` |
| G20 | booking | 5 | 0% | 0.00-0.43 | 80% | FAIL | `python -m agent.replay --scenario G20 --seed 0 --model v2` |
| G21 | dialog | 20 | 100% | 0.84-1.00 | 80% | PASS |  |
| G22 | booking | 5 | 0% | 0.00-0.43 | 80% | FAIL | `python -m agent.replay --scenario G22 --seed 0 --model v2` |
| G23 | booking | 5 | 0% | 0.00-0.43 | 80% | FAIL | `python -m agent.replay --scenario G23 --seed 0 --model v2` |
| G24 | cancel | 20 | 100% | 0.84-1.00 | 80% | PASS |  |
