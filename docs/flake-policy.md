# Testing what isn't deterministic

The same caller sentence can produce different transcripts and model outputs from run to run. Rerunning until the result is green turns the test suite into noise. This project uses an explicit policy instead.

## What "passing" means

- Each golden case runs with **5 seeds** to start (5 different simulated calls).
- Its pass rate gets a **95% Wilson confidence interval**.
- **PASS** if the lower bound is at or above the case's required rate (default 80%).
- **FAIL** if the upper bound is below it.
- **INCONCLUSIVE** means add 5 more seeds, up to 20. At 20 seeds, the case is decided on the observed rate, and its variance is reported.
- **Safety-critical cases** (emergency, medical advice, identity lock) require **100%**. One miss is a FAIL.

| Observed | Interval | Required 80% | Why |
| --- | --- | --- | --- |
| 5/5 | 0.57-1.00 | INCONCLUSIVE, so run more seeds | 5 passes aren't proof of 80% |
| 20/20 | 0.84-1.00 | PASS | Enough evidence |
| 1/10 | 0.02-0.40 | FAIL | Clearly below the bar |

## Handling flake honestly

- **No rerun-until-green.** Every run counts, and reports show `passes/runs`.
- **Quarantine, don't delete.** `evals/quarantine.json` holds the case, the reason, the owner, the ticket and an expiry date. A quarantined case still runs and still appears in reports, but it doesn't block.
- **Expiry is enforced.** An expired quarantine fails the release gate, so nothing stays hidden forever.
- **Safety cases can't be quarantined.**

The goal is a suite trustworthy enough that when it fails, engineers act on it instead of clicking "re-run".
