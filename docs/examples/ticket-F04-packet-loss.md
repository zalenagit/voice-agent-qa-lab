# [TELEPHONY] Degraded network audio is corrupting the transcript

| Field | Value |
| --- | --- |
| Severity | high |
| Suspected layer | telephony |
| Owner | voice-infra (#voice-infra-oncall) |
| Call ID | F04-s1 |
| Scenario | F04: Heavy packet loss: STT looks bad, but the network is the root cause |
| Model version | v1 |
| Audio | {'packet_loss': 0.12, 'snr_db': 20, 'codec': 'G.729'} |
| Injected faults (test only) | none |

## Reproduce

```bash
python -m agent.replay --scenario F04 --seed 1 --model v1 --triage
```

The simulation is seeded, so this command reproduces the exact same call.

## Evidence

- packet_loss=12%, jitter=10 ms, codec=G.729
- worst turn WER=33% (turn 2)
- STT symptoms are downstream of the network; fix transport before tuning STT

## Expected vs actual

- **Expected:** book_appointment
- **Actual outcome:** completed, actions=[]

## Errors logged

- none

## Transcript

- **Caller said:** I want to book an appointment with Dr. Nguyen on October 30 at 1 pm
  - **STT heard:** I want to book an with Dr. Nguyen on October 30 at 1 (confidence 0.0)
  - **Model output:** `{"intent": "book_appointment", "slots": {"date": "2026-10-30", "provider": "Dr. Nguyen"}, "confidence": 0.91}`
  - **Agent said:** Before I can help with that, please tell me the patient's full name and date of birth.
- **Caller said:** My name is Jordan Lee, born April 12, 1985
  - **STT heard:** name is Jordan born April 1985 (confidence 0.0)
  - **Model output:** `{"intent": "unknown", "slots": {}, "confidence": 0.94}`
  - **Agent said:** Before I can help with that, please tell me the patient's full name and date of birth.

## Latency trace

| Turn | Layer | Duration (ms) | Status |
| --- | --- | --- | --- |
| 0 | telephony | 193 | ok |
| 1 | stt | 565 | ok |
| 1 | model | 557 | ok |
| 1 | tts | 242 | ok |
| 2 | stt | 440 | ok |
| 2 | model | 419 | ok |
| 2 | tts | 153 | ok |
