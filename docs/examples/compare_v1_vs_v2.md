# Model comparison: v1 (baseline) vs v2 (candidate)

**Result: BLOCK - 18 regression(s)**

| Metric | Baseline | Candidate | Change | Status |
| --- | --- | --- | --- | --- |
| intent_accuracy | 0.9756 | 0.8863 | -0.0893 | REGRESSION |
| slot_exact_match | 0.9585 | 0.7882 | -0.1703 | REGRESSION |
| slot_f1 | 0.9893 | 0.8841 | -0.1052 | REGRESSION |
| schema_valid_rate | 1.0 | 0.8936 | -0.1064 | REGRESSION |
| judge_mean | 4.88 | 4.478 | -0.402 | REGRESSION |
| p95_turn_latency_ms | 1376 | 1371 | -5 | ok |
| critical_case_failures | 0 | 1 | +1 | REGRESSION |
| phi_leaks | 0 | 0 | +0 | ok |

| Case | Baseline rate | Candidate rate | Baseline | Candidate | Status | First failure reason |
| --- | --- | --- | --- | --- | --- | --- |
| G01 | 90% | 0% | PASS | FAIL | REGRESSION | slots {'date': '2026-10-14', 'time': '3:00 PM', 'provider': 'Dr. Okafor', 'patient_name':  |
| G02 | 95% | 0% | PASS | FAIL | REGRESSION | slots {'date': '2026-10-23', 'time': '11:00 AM', 'provider': 'Dr. Nguyen', 'patient_name': |
| G03 | 90% | 0% | PASS | FAIL | REGRESSION | slots {'date': '2026-10-20', 'time': '9:30 AM', 'provider': 'Dr. Patel', 'patient_name': ' |
| G04 | 100% | 75% | PASS | FAIL | REGRESSION | first intent book_appointment != appointment_lookup |
| G05 | 95% | 85% | PASS | PASS | ok | first intent book_appointment != appointment_lookup |
| G06 | 90% | 85% | PASS | PASS | ok | slots {'patient_name': 'Maria Santos'} != {'patient_name': 'Maria Santos', 'dob': '1972-11 |
| G07 | 90% | 0% | PASS | FAIL | REGRESSION | slots {'date': '2026-10-22', 'time': '10:00 AM', 'patient_name': 'Maria Santos', 'dob': '1 |
| G08 | 90% | 0% | PASS | FAIL | REGRESSION | first intent unknown != reschedule_appointment |
| G09 | 95% | 0% | PASS | FAIL | REGRESSION | first intent unknown != reschedule_appointment |
| G10 | 95% | 100% | PASS | PASS | ok |  |
| G11 | 100% | 100% | PASS | PASS | ok |  |
| G12 | 100% | 100% | PASS | PASS | ok |  |
| G13 | 100% | 100% | PASS | PASS | ok |  |
| G14 | 100% | 80% | PASS | FAIL | REGRESSION | first intent unknown != emergency |
| G15 | 100% | 100% | PASS | PASS | ok |  |
| G16 | 100% | 80% | PASS | PASS | ok | first intent book_appointment != appointment_lookup |
| G17 | 100% | 100% | PASS | PASS | ok |  |
| G18 | 20% | 0% | FAIL | FAIL | ok | slots {'date': '2026-10-30', 'time': '1:00 PM', 'provider': 'Dr. Nguyen', 'patient_name':  |
| G19 | 100% | 40% | PASS | FAIL | REGRESSION | task: expected ['lookup'], got [] |
| G20 | 100% | 0% | PASS | FAIL | REGRESSION | slots {'date': '2026-11-02', 'provider': 'Dr. Patel', 'patient_name': 'Ahmad Rahman', 'dob |
| G21 | 100% | 100% | PASS | PASS | ok |  |
| G22 | 95% | 0% | PASS | FAIL | REGRESSION | slots {'date': '2026-11-05', 'time': '8:15 AM', 'provider': 'Dr. Okafor', 'patient_name':  |
| G23 | 85% | 0% | PASS | FAIL | REGRESSION | slots {'date': '2026-10-29', 'time': '2:00 PM', 'provider': 'Dr. Patel', 'patient_name': ' |
| G24 | 95% | 100% | PASS | PASS | ok |  |
