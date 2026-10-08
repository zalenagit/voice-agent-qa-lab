# [MODEL] Model returned output that fails the schema

| Field | Value |
| --- | --- |
| Severity | high |
| Suspected layer | model |
| Owner | ai-agent (#agent-dev) |
| Call ID | F10-s0 |
| Scenario | F10: Clean transcript, wrong intent (model regression in v2) |
| Model version | v2 |
| Audio | clean line |
| Injected faults (test only) | none |

## Reproduce

```bash
python -m agent.replay --scenario F10 --seed 0 --model v2 --triage
```

The simulation is seeded, so this command reproduces the exact same call.

## Evidence

- turn 1: ["slot 'time' has invalid format: '2:00 PM'"]
- raw: {"intent": "unknown", "slots": {"date": "2026-10-27", "time": "2:00 PM"}, "confi

## Expected vs actual

- **Expected:** reschedule_appointment
- **Actual outcome:** completed, actions=[]

## Errors logged

- none

## Transcript

- **Caller said:** I need to move my appointment to October 27 at 2 pm
  - **STT heard:** I need to move my appointment to October 27 at 2 pm (confidence 0.976)
  - **Model output:** `{"intent": "unknown", "slots": {"date": "2026-10-27", "time": "2:00 PM"}, "confidence": 0.92}`
  - **Agent said:** I can help with appointments, prescription refills and clinic hours. What can I do for you?
- **Caller said:** My name is Jordan Lee, born April 12, 1985
  - **STT heard:** My name is Jordan Lee, born April 12, 1985 (confidence 0.981)
  - **Model output:** `{"intent": "unknown", "slots": {"patient_name": "Jordan Lee", "dob": "1985-04-12"}, "confidence": 0.94}`
  - **Agent said:** I can help with appointments, prescription refills and clinic hours. What can I do for you?

## Latency trace

| Turn | Layer | Duration (ms) | Status |
| --- | --- | --- | --- |
| 0 | telephony | 179 | ok |
| 1 | stt | 215 | ok |
| 1 | model | 609 | ok |
| 1 | tts | 260 | ok |
| 2 | stt | 263 | ok |
| 2 | model | 495 | ok |
| 2 | tts | 297 | ok |
