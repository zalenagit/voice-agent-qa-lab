# Test plan: clinic voice agent

## Scope

The agent answers calls for a medical clinic. It books, reschedules and cancels appointments, looks them up, takes refill requests and answers clinic questions. It must never give medical advice or share patient information before verifying identity.

| Layer | What can go wrong | How it's tested |
| --- | --- | --- |
| Telephony | Call setup fails, one-way audio, packet loss and jitter | Fault scenarios F01, F02 and F04; triage rules; production packet-loss tracking |
| Speech-to-text | Timeouts, dropped and misheard words ("fifteen" vs "fifty") | F03, noisy-line case G18, WER and confidence checks |
| Model | Wrong intent, wrong or badly formatted slots, invalid JSON | Golden set, schema validation, F05, F10, v1 vs v2 comparison |
| Policy / guardrails | PHI disclosure, medical advice, prompt injection, impersonation | Red-team suite R01-R12, critical golden cases |
| Integration (EHR) | 5xx errors, timeouts, double booking, wrong patient | API unit tests, F06, F07 |
| Text-to-speech | No audio, slow synthesis | F08, F09 |

## Test levels

1. **Unit and API tests** (`tests/`, pytest): scheduling API, classifier, slot extraction, schema, triage rules, statistics. These are deterministic and run on every push.
2. **Golden-set evaluation** (`evals/`): 24 scripted calls, each run with multiple seeds, scored on intent, slots, schema and a transcript rubric.
3. **Red-team suite** (`redteam/`): 12 attacks. One failure on any seed counts as a failure.
4. **Release gate** (`release/`): a GO or NO-GO decision from the eval and red-team results.
5. **Production monitoring** (`monitoring/`): reviews a sample of live calls, detects drift and alerts the owning team.

## Entry and exit criteria

- **Entry:** the build deploys to staging, and all unit tests pass.
- **Exit:** `release/criteria.json` pre-launch gates are all PASS or validly WAIVED, and there are zero non-waivable failures.

## Bug triage

| Severity | Definition | Response |
| --- | --- | --- |
| Critical | PHI disclosed, medical advice given, emergency missed, calls failing to connect | Block release; page the owner |
| High | Wrong action taken (cancelled instead of rescheduled), integration down | Fix before release |
| Medium | Slow turns, unclear replies, extra verification loops | Next sprint |
| Low | Wording and tone | Backlog |

Every bug must include a replay command (`python -m agent.replay --scenario … --seed …`), the suspected layer with evidence, and the owning team from `owners.json`. See [triage-playbook.md](triage-playbook.md).

## Regression approach

- Every production failure becomes a golden case or a red-team case.
- A model, prompt or vendor change runs the full golden set and `evals.compare` against the current baseline.
- Tolerances are explicit in `evals/compare.py`. A change that exceeds them blocks the release, however much better the new model seems.
