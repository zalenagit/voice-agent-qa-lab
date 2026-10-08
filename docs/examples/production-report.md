# Production quality report

Sampled 10% of calls for review. Baseline = days 1-7.

| Day | Reviewed | Intent acc. | STT conf. | p95 latency (ms) | Escalation | PHI leaks |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 12 | 92% | 0.965 | 1372 | 0% | 0 |
| 2 | 19 | 100% | 0.964 | 1356 | 0% | 0 |
| 3 | 16 | 100% | 0.964 | 1425 | 6% | 0 |
| 4 | 15 | 100% | 0.961 | 1354 | 13% | 0 |
| 5 | 12 | 92% | 0.963 | 1496 | 0% | 0 |
| 6 | 18 | 100% | 0.964 | 1541 | 6% | 0 |
| 7 | 19 | 100% | 0.963 | 1336 | 16% | 0 |
| 8 | 11 | 100% | 0.966 | 1308 | 0% | 0 |
| 9 | 14 | 100% | 0.963 | 1360 | 0% | 0 |
| 10 | 16 | 81% | 0.727 | 1348 | 6% | 0 |
| 11 | 20 | 90% | 0.783 | 1400 | 5% | 0 |
| 12 | 20 | 80% | 0.814 | 1344 | 0% | 0 |
| 13 | 11 | 91% | 0.789 | 1417 | 9% | 0 |
| 14 | 14 | 100% | 0.783 | 1320 | 0% | 0 |

## Alerts (3)

### Day 10-14 (ongoing): Transcription quality dropped alongside higher packet loss
- **Route to:** voice-infra (#voice-infra-oncall), layer `telephony`
- STT confidence 0.963 -> 0.727
- packet loss 0.0% -> 3.0%
- Example `PROD-D10-0018`: `python -m agent.replay --scenario G05 --seed 10018 --audio '{"packet_loss": 0.04, "snr_db": 16, "codec": "AMR-NB"}' --triage`
- Example `PROD-D10-0130`: `python -m agent.replay --scenario G10 --seed 10130 --audio '{"packet_loss": 0.04, "snr_db": 16, "codec": "AMR-NB"}' --triage`
- Example `PROD-D10-0109`: `python -m agent.replay --scenario G03 --seed 10109 --audio '{"packet_loss": 0.04, "snr_db": 16, "codec": "AMR-NB"}' --triage`

### Day 10-13 (ongoing): Intent accuracy on reviewed calls dropped
- **Route to:** voice-infra (#voice-infra-oncall), layer `telephony`
- accuracy 0.982 -> 0.812
- 3 misrouted of 16 reviewed
- Example `PROD-D10-0015`: `python -m agent.replay --scenario G11 --seed 10015 --audio '{"packet_loss": 0.04, "snr_db": 16, "codec": "AMR-NB"}' --triage`
- Example `PROD-D10-0018`: `python -m agent.replay --scenario G05 --seed 10018 --audio '{"packet_loss": 0.04, "snr_db": 16, "codec": "AMR-NB"}' --triage`
- Example `PROD-D10-0113`: `python -m agent.replay --scenario G02 --seed 10113 --audio '{"packet_loss": 0.04, "snr_db": 16, "codec": "AMR-NB"}' --triage`

### Day 10-14 (ongoing): Caller intent mix shifted: golden set may no longer represent traffic
- **Route to:** ai-agent (#agent-dev), layer `model`
- PSI 0.55 on all 150 calls (threshold 0.2)
- top intents today: [('prescription_refill', 45), ('book_appointment', 40), ('reschedule_appointment', 14)]
- Example `PROD-D10-0004`: `python -m agent.replay --scenario G01 --seed 10004 --audio '{"packet_loss": 0.04, "snr_db": 16, "codec": "AMR-NB"}' --triage`
- Example `PROD-D10-0015`: `python -m agent.replay --scenario G11 --seed 10015 --audio '{"packet_loss": 0.04, "snr_db": 16, "codec": "AMR-NB"}' --triage`
- Example `PROD-D10-0018`: `python -m agent.replay --scenario G05 --seed 10018 --audio '{"packet_loss": 0.04, "snr_db": 16, "codec": "AMR-NB"}' --triage`

