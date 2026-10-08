# Quality in production

`python -m monitoring.monitor reports/production_calls.jsonl --sample-rate 0.1`

1. **Sample live calls.** A deterministic 10% sample goes to review. The synthetic ground truth stands in for a human label.
2. **Track daily metrics:** intent accuracy on reviewed calls, STT confidence, p95 turn latency, escalation rate and PHI leaks.
3. **Compare to a baseline** (days 1-7) and the post-launch SLOs.
4. **Detect drift:**
   - Transcription quality drops (confidence falls more than 0.04, or goes below the SLO)
   - Intent accuracy drops (more than 5 points, or below the SLO)
   - Latency regresses (p95 up more than 25%, or above the SLO)
   - The caller intent mix shifts (PSI above 0.2 on all calls' predicted intents). When that happens, the golden set may no longer represent real traffic.
5. **Route to the root-cause owner.** If packet loss rose along with the quality drop, the alert goes to voice-infra, not to the model team. Every alert includes example call IDs and replay commands.
6. **Don't page twice.** An ongoing issue updates one alert ("Day 10-14, ongoing") instead of creating a new one every day.

In the [example report](examples/production-report.md), a carrier codec change on day 10 degrades audio. The monitor flags it on day 10, routes it to voice-infra with replayable calls, and separately flags that refill calls tripled, so the golden set needs more refill cases.
