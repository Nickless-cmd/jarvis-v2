# Forgetting Phase 1 — Day 1 baseline

**Date:** 2026-05-10
**Deployed:** ffd6a539e6272d571b10d88211654ae55c6abba8 (jarvis-runtime restart)

## Initial state

- `absence_traces` rows: 1 (auto_counter, month=2026-05, count=1)
- `cognitive_chronicle_entries` total rows: 2
  - 1 already soft-deleted by daemon's first cycle (`chr-seed-w14`, created 2026-04-06)
  - 1 active (`chr-cd4d698e3b`, created 2026-04-17 — under 30-day threshold)
- `cognitive_personal_project_journal` total rows: 16, none over 30 days
- Soft-deleted rows on chronicle: 1 (one fade observed on day-1)

## First auto-cycle output

Forced cycle via `run_auto_cycle(workspace_id='default')`:
```python
{'workspace_id': 'default', 'soft_deleted': 0, 'hard_deleted': 0}
```

Zero new fades — daemon's lifespan-startup cycle already processed the only candidate.

## Heartbeat injection live output

```
Forglemmelsens vægt: 1 ting er fadet i denne måned (2026-05).
```

This will appear in the heartbeat awareness section every cycle until the
month rolls over to 2026-06 (counter resets per month spec).

## Tool fail-graceful verification

`release_memory` with bogus `memory_id`:
```python
{'status': 'not_found', 'reason': 'memory_id does-not-exist not in cognitive_chronicle_entries'}
```

No traceback. Schema integrity preserved.

## Open observations

- Auto-fade volume is low — only 1 row qualified on day-1. Expected to grow as
  more chronicle/journal entries cross the 30-day age threshold over time.
- The `chr-seed-w14` row (only fade so far) was a seed entry from 2026-04-06.
  The grace window means it won't hard-delete until 2026-05-17 — consistent
  with the 7-day spec.
- The daemon currently scans only `cognitive_chronicle_entries` and
  `cognitive_personal_project_journal`. Other episodic tables are deferred to
  Phase 2 per the audit doc.
- No self-track usage yet (release_memory tool live but unused). Acceptable
  in phase 1 — observation criterion in spec is "at least once unprompted
  within 30 days".
