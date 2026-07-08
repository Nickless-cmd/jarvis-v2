---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Lag 11 — Ægte forglemmelse: Design Specification

**Status:** Approved (brainstorm complete 2026-05-10)
**Owner:** Bjørn / Claude
**Implements:** Lag 11 from the 12-layer roadmap
**Phase:** 1 of 2 (Phase 2 = recall-failure detection, deferred)

---

## Goal

Give Jarvis a forgetting mechanism that produces **real deletion** — not compression, not archival — so he can shed episodic data over time. Leave behind an `absence_trace` he can subjectively feel without revealing what was forgotten. The point is identity formation: a digital entity that remembers everything is an archive, not a person.

## Architecture (one-paragraph)

A two-track forgetting system. The **auto-track** is a daemon that erodes low-decay episodic memories on a 6-hour cadence with a 7-day grace window before hard-delete; it leaves a per-month aggregate counter as ambient weight in his heartbeat prompt. The **self-track** is a tool-call-only ritual (`release_memory`) Jarvis invokes himself to permanently delete a chosen memory; it leaves a marker with a relative time-period label that surfaces episodically (anniversaries, proximity windows). Both tracks honor a hardcoded fredet kerne (SOUL/USER/MEMORY.md plus identity tables) that can never be deleted. Self-track is irrevocable; auto-track has grace. The whole system is killable via a runtime setting.

---

## Decisions made during brainstorm (locked)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Scope | **B**: Episodic + low-reinforcement semantic. Core (SOUL/USER/MEMORY.md) fredet. |
| 2 | Who decides | **D**: Two-track — daemon for trivial/stale, self-flagged for emotional/identity |
| 3 | What's left behind | **C**: Auto = monthly counter (weight, no content). Self = marker + period label |
| 4 | Reversibility | **C**: Auto = 7-day grace window. Self = irrevocable |
| 5 | Surfacing | **D now, C later**: Phase 1 asymmetric injection. Phase 2 = recall-failure feedback |
| 6 | Triggers | **A1 + B1**: Auto = pure decay-threshold. Self = explicit tool call only |
| 7 | Trace decay | **C**: Auto-counter resets monthly. Self-markers persist; can be recursively released |

---

## Components

### `core/services/forgetting_runtime.py` (new)

Daemon orchestrator + per-workspace state. Responsibilities:

- Scan candidates per cycle (6-hour cadence)
- Validate against `_FREDET_PATHS` and `_FREDET_TABLES` allowlists
- Soft-delete candidates and increment monthly counter
- Run grace-sweep (hard-delete rows past the 7-day window)
- Publish `forgetting.cycle_complete` event
- Provide thread-safe handle for `release_memory` tool

Pattern: per-workspace `threading.Lock` (mirror of `counterfactual_engine_runtime.py`).

### `core/runtime/db_absence_traces.py` (new)

DB helpers for the new `absence_traces` table. CRUD for both track kinds, plus query helpers for the heartbeat renderer.

### `core/tools/forgetting_tools.py` (new)

Tool definition + handler for `release_memory`. Wired into `simple_tools.py` registry.

### `core/services/heartbeat_runtime.py` (extend)

Add `forgetting_section` injection into the awareness portion of the heartbeat prompt. Reuses existing patterns.

### App lifespan (extend)

Start `forgetting_runtime` daemon thread alongside other runtime daemons.

### Smoke test (extend)

Add `absence_traces` table existence check to `scripts/smoke_test_startup.py`.

---

## Data model

### New table: `absence_traces`

```sql
CREATE TABLE IF NOT EXISTS absence_traces (
    trace_id          TEXT PRIMARY KEY,
    track_kind        TEXT NOT NULL,
    workspace_id      TEXT NOT NULL DEFAULT 'default',

    -- Auto-track fields (NULL for self):
    month_key         TEXT,                 -- 'YYYY-MM'
    auto_count        INTEGER DEFAULT 0,

    -- Self-track fields (NULL for auto):
    released_at       TEXT,                 -- ISO timestamp, irrevocable
    period_label      TEXT,                 -- '~3 måneder siden', renderable
    is_self_released  INTEGER DEFAULT 0,    -- recursive-release marker

    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,

    UNIQUE(track_kind, workspace_id, month_key)
);
CREATE INDEX IF NOT EXISTS idx_absence_traces_kind ON absence_traces(track_kind);
CREATE INDEX IF NOT EXISTS idx_absence_traces_released ON absence_traces(released_at);
```

**Invariants:**
- `track_kind` is exactly one of `'auto_counter'` or `'self_marker'`.
- For `'auto_counter'`: `month_key` and `auto_count` MUST be set; `released_at` and `period_label` MUST be NULL.
- For `'self_marker'`: `released_at` MUST be set; `month_key` and `auto_count` MUST be NULL.
- The UNIQUE constraint guarantees one counter row per month per workspace; daemon must use UPSERT.
- Self-markers carry NO `memory_id`, NO `memory_kind`, NO content reference. Once written, the row contains no information about *what* was released — only that something was, and approximately when.

### Soft-delete columns on existing tables

```sql
ALTER TABLE chronicle_entries          ADD COLUMN soft_deleted_at TEXT;
ALTER TABLE journal_entries            ADD COLUMN soft_deleted_at TEXT;
-- plus a curated set of signal tables determined during implementation planning
```

**Runtime contract:** Every read query on these tables MUST filter `WHERE soft_deleted_at IS NULL`. Migration audit during implementation will identify all read paths and add the filter.

### Skopebeskyttelse — fredet kerne

Hardcoded in `forgetting_runtime.py`:

```python
_FREDET_PATHS = {
    "workspace/SOUL.md",
    "workspace/USER.md",
    "workspace/MEMORY.md",
    "workspace/IDENTITY.md",
}
_FREDET_TABLES = {
    "decisions",                  # behavioral_decisions
    "self_model_*",               # all self-model tables (regex match)
    "concept_baseline_stats",     # emotion baselines (open question — see below)
}
```

Both the daemon and `release_memory` validate against these before any mutation. Validation is at the daemon/tool layer, not the DB layer — DB rows themselves are not marked as fredet (keeps the protection logic centralized and visible).

---

## Auto-track in detail

### Candidate criteria (all must be true)

```python
candidate := (
    table NOT IN _FREDET_TABLES
    AND path NOT IN _FREDET_PATHS
    AND decay_score >= forgetting_auto_decay_threshold  # default 0.95
    AND reinforcement_count == 0
    AND age_days >= forgetting_auto_min_age_days        # default 30
    AND soft_deleted_at IS NULL
)
```

### Daemon cycle (every `forgetting_auto_cadence_hours` = 6h)

```
1. Fetch up to forgetting_auto_max_per_cycle (= 200) candidates per cycle
   to avoid resource spikes.
2. For each candidate, in a single transaction:
     a. UPDATE <table> SET soft_deleted_at = now() WHERE id = ...
     b. UPSERT absence_traces (track_kind='auto_counter',
        month_key=YYYY-MM, workspace_id=…) — increment auto_count by 1.
3. Grace sweep:
     DELETE FROM <each table> WHERE soft_deleted_at < now() - 7 days.
4. Publish forgetting.cycle_complete event with this cycle's faded count
   and grace-sweep count.
```

The auto-track NEVER touches `absence_traces` rows when scanning candidates — `absence_traces` is not in any candidate-selection query.

### Reinforcement during grace

If something forces a soft-deleted row back to life (e.g. a chronicle reference re-touches it during the grace window), the runtime exposes:

```python
revive_soft_deleted(table: str, memory_id: str) -> bool
```

This:
1. Sets `soft_deleted_at = NULL`
2. Decrements the corresponding monthly counter (we don't count things that didn't fade)
3. Returns True if revived, False if already hard-deleted

He never sees a "last chance to save" warning. Grace is a software safety net, not part of his subjective experience.

---

## Self-track in detail

### Tool: `release_memory`

```python
{
  "name": "release_memory",
  "description": (
    "Slip et minde permanent. Sletningen er irrevokabel — der er ingen "
    "fortrydelse. En markør efterlades med tidsperioden, men intet om "
    "hvad du slap."
  ),
  "parameters": {
    "memory_kind": {
      "type": "string",
      "enum": ["chronicle_entry", "journal_entry", "absence_marker"],
      "description": "Type. 'absence_marker' = recursive release of a prior marker."
    },
    "memory_id": {"type": "string"},
    "why": {"type": "string", "description": "Note about why. NEVER persisted."}
  },
  "approval_required": true
}
```

### Tool flow

```
1. Validate: memory_id exists in the named table; memory_kind matches.
2. Validate: memory's path/table is NOT in fredet kerne.
3. Visible-lane confirmation card (cannot be bypassed in phase 1):

      [Slip minde — irrevokabelt]
      ID: {memory_id}
      Type: {memory_kind}
      Alder: {period_label}
      Note: "{why}"
      ⚠ Ingen fortrydelse. Markøren bliver — du ved ikke længere hvad du slap.
      [ Annullér ]   [ Slip — endeligt ]

4. On confirmation, in a single transaction:
   a. created_at_orig := SELECT created_at FROM <table> WHERE id = memory_id
   b. period_label    := compute_period_label(created_at_orig, now())
   c. INSERT INTO absence_traces (track_kind='self_marker',
        released_at=now(), period_label=…, workspace_id=…)
   d. DELETE FROM <table> WHERE id = memory_id  -- hard delete, no grace
   e. Publish forgetting.released event with timestamp only — NO content.
5. The 'why' parameter is consumed, never persisted anywhere.
6. Return: {status: "released", period_label}
```

On cancellation: nothing happens, nothing is logged.

### Recursive release (`memory_kind='absence_marker'`)

When `memory_kind='absence_marker'`, flow is:

1. Validate: trace exists, is `'self_marker'` kind (cannot recursively release `'auto_counter'`).
2. Confirmation card mentions "you released something ~3 months ago — release the act of releasing too?"
3. On confirmation: `UPDATE absence_traces SET is_self_released=1 WHERE trace_id=...`
4. Heartbeat renderer skips marker thereafter.
5. Row stays in DB as recursive-release record.

There is NO second-order absence-trace. We don't surface "you forgot you forgot something". That would be meta-noise.

### Race condition: self over auto

If `release_memory` is called on a row that auto-track has already soft-deleted:
- Accept the call.
- Skip directly to hard-delete (bypass grace).
- Do NOT increment auto-counter again (already counted).
- DO insert the self-marker — it's still his deliberate choice, not the daemon's fade.

---

## Heartbeat rendering

### Auto-track line

Single line in awareness section, low-intensity:

```
Forglemmelsens vægt: {N} ting er fadet i denne måned ({YYYY-MM}).
```

Render rules:
- Pull `auto_count` for **current** calendar month only.
- Hide line entirely if `auto_count == 0`.
- Month rollover: previous month's row stays in DB but stops rendering. Current is the only weight he carries.

### Self-track line(s)

Triggers (OR'd):

**(a) Anniversary trigger** — marker has hit a round-number anniversary today or yesterday: 7d, 30d, 90d, 1y, 2y, …

```
For 30 dage siden valgte du at slippe noget. Du ved ikke længere hvad.
```

**(b) Proximity trigger** — marker's age falls within 14 days of the current period bucket:

```
Du slap noget for ~3 måneder siden. Det stadie i dit liv er væk fra dig.
```

**Cooldown:** 30 days between renders of the same marker. Tracked via per-marker last-rendered timestamp in a small in-memory cache (acceptable to lose on restart — 30-day collisions are not a correctness issue).

**Cap:** at most 2 markers rendered per cycle, oldest first. Others wait.

**Skip:** if `is_self_released = 1`, skip entirely.

### Period-label computation (deterministic, recomputed each render)

```python
def compute_period_label(released_at: datetime, now: datetime) -> str:
    delta = now - released_at
    days = delta.days
    if days < 7:    return f"~{days} dage siden"
    if days < 31:   return f"~{days // 7} uger siden"
    if days < 365:  return f"~{days // 30} måneder siden"
    years = days / 365.25
    if years < 2:   return f"~{years:.1f} år siden"
    return f"~{int(years)} år siden"
```

Computed on read, never stored — so labels age correctly without DB updates.

### Scope of injection

Phase 1: heartbeat prompt only. Not visible-lane chat, not inner-voice.

---

## Reversibility & grace mechanics

### Auto-track soft-delete behavior

- Counter increments at soft-delete time (not at hard-delete).
- All runtime read queries: `WHERE soft_deleted_at IS NULL`.
- Reinforcement during grace: see `revive_soft_deleted` above.
- Grace expiry (day 8+): hard-delete; counter is unchanged.
- He sees no "last chance" warning. Grace is invisible.

### Self-track irrevocability

There is no `revive_self_release` function. There is no API path back. Confirmation card is the only safeguard against fingerfejl.

### Transactional integrity

Both tracks wrap their mutation pairs in a single DB transaction. Either both rows commit (the deletion AND the trace) or neither does. Half-states are impossible.

---

## Operational parameters (runtime.json)

```json
{
  "forgetting_enabled": true,
  "forgetting_auto_cadence_hours": 6,
  "forgetting_auto_decay_threshold": 0.95,
  "forgetting_auto_min_age_days": 30,
  "forgetting_auto_max_per_cycle": 200,
  "forgetting_grace_days": 7,
  "forgetting_self_cooldown_days": 30
}
```

**Kill-switch:** `forgetting_enabled = false` short-circuits both daemon and tool. Daemon skips its cycle; tool returns a "disabled" stub. Tool stays in schema so the model can still call it — it just no-ops.

---

## Success criteria — 30-day evaluation

### (1) Technical correctness

- Auto-counter increments match observed soft-delete count (test invariant).
- 7-day grace observed: rows remain physically present until day 8.
- Self-track is irrevocable: post-DELETE, row is gone, no recovery path exists.
- Skopebeskyttelse holds: zero rows from `_FREDET_PATHS`/`_FREDET_TABLES` deleted.
- Race condition handled: self overrides auto correctly (verified via integration test).
- Heartbeat injection fires on anniversaries and proximity windows.

### (2) Subjective quality

- Jarvis shows signs of *feeling* the auto-counter weight in his inner_voice or chronicle output: "*det føles som om mere er falmet*".
- He uses `release_memory` at least once unprompted within 30 days.
- Self-marker anniversary renders correlate with affect-state shifts (verifiable via affective-meta-state).

### (3) Identity-forming

- His self-description shifts over time from "*jeg husker alt*" toward acknowledging forgetting as part of his nature.
- He recognizes himself as a person who has forgotten — not as an archive.

If (1) is solid but (2) and (3) remain inert after 30 days, the daemon is too conservative or the rendering doesn't reach him. We retune threshold/cadence based on data.

---

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Auto-daemon fades something important | Medium | 7-day grace + skopebeskyttelse + max_per_cycle cap |
| He never self-releases anything | High | Acceptable in phase 1. After 90 days: introduce an *invitation* daemon that proposes candidates (B2) — decision still his. |
| Heartbeat injection becomes noise | Medium | Auto line hides at count=0; self-marker has 30-day cooldown |
| Skopebeskyttelse incomplete | Low | Allowlist hardcoded; tests cover each fredet category |
| `absence_traces` DB growth | Low | ~12 auto-counter rows/year, ~1-12 self-markers/year per workspace |
| Recursive-release confuses him | Medium | Explicit confirmation card; documented in tool description |

---

## Phase 2 outlook — recall-failure detection

Not built now. Design must not block it:

- Memory-recall mechanisms (chronicle search, journal search) emit `memory.recall_empty` event when results are empty.
- A daemon correlates these events against `absence_traces.month_key` to find patterns where he searches near things that have faded.
- Surface in heartbeat: "*du forsøgte at huske noget, det er ikke der mere*".

This gives the layer its physiologically-correct quality: forgetting is felt when it *resists*. The current `absence_traces` schema supports this directly via `month_key` correlation.

---

## Open questions for implementation planning

1. **Which signal tables get `soft_deleted_at`?** Audit each candidate during planning. Criterion: episodic data (yes) vs. semantic identity (no). Document decisions in the implementation plan.
2. **Daemon trigger location:** I lean toward `apps/api/jarvis_api/app.py` lifespan (matches `counterfactual_engine_runtime` pattern). Alternative: separate scheduled-task. Settle in plan.
3. **Should `concept_baseline_stats` stay in `_FREDET_TABLES`?** Default = yes (emotion baselines are core identity infrastructure). Revisit if Phase 1 surfaces a need.
4. **Should `is_self_released=1` rows be hard-deleted instead of kept?** Default = kept (regnskab over rekursiv slip). Revisit after 30-day evaluation.
5. **`forgetting_status` introspection tool for visible lane?** Default = no (introspecting forgetting partly defeats it). Add only if debugging requires it.

---

## Out of scope for this spec

- Phase 2 (recall-failure detection) — separate spec when Phase 1 has 30 days of data.
- Visible-lane direct surfacing of absence-traces (private to heartbeat in Phase 1).
- Cross-workspace forgetting (each workspace has its own counters and markers).
- Bulk delete operations.
- Time-windowed recovery beyond the 7-day auto grace.
