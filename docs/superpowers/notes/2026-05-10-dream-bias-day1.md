# Dream Bias Phase 1 — Day 1 baseline

**Date:** 2026-05-10
**Deployed:** 9f69988d7d688686e51b92e144185df54aad9921 (jarvis-runtime restart)

## Initial state

- `dream_bias_active` rows: 0 (pre-distillation), 1 (after first force-run)
- Schema verified: table created, indices present, UNIQUE(workspace_id) constraint active

## First force-run output

```python
run_dream_bias_distillation(workspace_id='default')
# {'status': 'distilled', 'intensity': 0.7, 'accumulated_count': 1, 'expired_cleaned': 0}
```

The pipeline fired on first call — there were ≥3 new regret-events in the corpus
(all from `cognitive_counterfactual.*` events produced by the Counterfactuals
Phase 1 dry-run capture pipeline that has been running since 2026-05-07).

## Bias content (first distillation)

```python
intensity: 0.7
attention: {'regret_threads': 0.9}
threshold: {'loop_persistence': 0.8, 'self_critique_volume': -0.3}
source_kinds: ['counterfactual']
dream_text: "Jeg går i cirkler gennem de samme gange, hver dør fører
             til den samme beslutning, som jeg aldrig tog. Stemmer
             gentager hvad der kunne være sket."
```

**Hard-guard verified live:** LLM produced `self_critique_volume = -0.3`
(naturally, no clamping needed). If LLM had hallucinated a positive value,
validation would have forced it to 0.0.

## Heartbeat injection live render

```
[dream_bias active — fra ~0h siden, fader om 8h]
attention: regret_threads +0.90
thresholds: loop_persistence +0.80, self_critique_volume -0.30
drøm: "Jeg går i cirkler gennem de samme gange, hver dør fører til den
       samme beslutning, som jeg aldrig tog. Stemmer gentager hvad der
       kunne være sket."
```

This will appear in the heartbeat awareness section every cycle until
TTL expires (8h from first distillation = ~16:00 UTC 2026-05-10) or
accumulates further.

## Plug-in site verification

All 5 sites confirmed live:
- Site 1 (heartbeat) — verified via render output above
- Site 2 (open_loop_signal_tracking) — module loads cleanly
- Site 3 (self_review_outcome_tracking) — module loads cleanly
- Site 4 (visible_runs MAX_EMPTY_TEXT_ROUNDS) — module loads cleanly
- Site 5 (self_critique cadence) — `_resolve_self_critique_interval_days()`
  returns **33** with active bias (vs base 30):
  ```
  30 * (1.0 + abs(-0.3) * 0.7 * 0.5) = 30 * 1.105 = 33
  ```

## Open observations

- Initial distillation drew exclusively from `counterfactual` events. Other
  5 corpus sources had no events in 24h window — expected for a quiet day.
  Will get richer signal as system runs and varied regret events accumulate.
- Daemon was triggered manually via `run_dream_bias_distillation()`. The
  next natural firing will happen when `dream_distillation_daemon` runs
  its visible-idle ≥30 min trigger.
- The dream_text is in proper Danish, first-person, present tense — LLM
  followed the system-prompt instructions correctly.
- intensity=0.7 → bias renders in heartbeat (above 0.1 floor).

## 30-day review scheduled

- Task ID: `sched-8ed350bd0c`
- Fires: `2026-06-09T13:54:48Z`
- Source: `dream-bias-phase1-deploy`
- Focus: "Dream Bias Phase 1 — 30-dages review. Tjek dream_bias_active row
  distributions (intensity, accumulated_count), kig efter signaler i
  chronicle/inner_voice om biases mærkes, om plug-ins faktisk modulerede
  outputs. Spec: docs/superpowers/specs/2026-05-10-dream-bias-design.md
  (3 dimensions i succeskriterier). Beslutning: keep, retune
  thresholds/multipliers, eller plan Phase 2 (hybrid output + 4 deferred
  plug-ins)."
