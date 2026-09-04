# Nudge Redesign — Implementation Plan (executed)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two dead nudge wells with one delivery path that actually reaches Bjørn, and make the hollow-promise guard force action instead of asking for it, with measurable outcomes.

**Architecture:** `outbound_nudges.push_nudge` keeps its signature (14 call sites untouched) but becomes a router: telemetry → event, mid-run user messages → own prompt section, everything else → `proactive_candidates` → `proactivity_bridge` (presence-gated, digest, cap). In conversation at most one relevant candidate is shown as a "Siden sidst" line and auto-counted as delivered when mentioned. Hollow promise → next round `tool_choice="required"` + `runtime.hollow_promise_detected/outcome` events.

**Tech Stack:** Python 3.11, SQLite, pytest, eventbus (family `runtime`/`nudge`).

**Measured before (2026-09-04, CT105):** outbound_nudges 506/7 d (89 % "Autonom run ✓ færdig"), 0 sent ever; prompt asked for a non-existent `mark_sent` tool inside the "citér ALDRIG" block; nudge_broend.json 751 pending autonomous-run rows, 0 sent; hollow-promise nudge rounds: 10/10 died with DeepSeek 400 the same day.

## Global Constraints

- No deletion of the 14 daemon call sites; `push_nudge` stays backward compatible (returns `{"status": ...}`).
- Nothing here sends to Bjørn directly — delivery is `proactivity_bridge` only.
- Every behaviour change has a unit test; commits via `scripts/commit_with_attribution.py`.

---

### Task 1: `core/services/proactive_candidates.py` — the one queue
- [x] table + add/dedupe/list/mark/expire; `relevant_for` (lexical), `build_since_last_line`, `mark_mentioned_if_overlap`, `bridge_candidates`
- [x] tests/test_proactive_candidates.py

### Task 2: `push_nudge` router + midway section
- [x] `route_for`: midway | telemetry | bridge; telemetry never stored; bridge → candidates
- [x] `format_midway_for_prompt` (Bjørns beskeder undervejs) — own tail section, prewarm never consumes
- [x] prompt_contract: awareness "pending outbound nudges" removed; midway → `_tail_add`; "Siden sidst" → `_dyn_memory_recall`
- [x] visible_runs_learning_signals: `mark_mentioned_if_overlap` after each answer
- [x] proactivity_bridge: collects candidates, marks surfaced

### Task 3: autonomous runs → telemetry
- [x] `_observe_autonomous_run`: `runtime.autonomous_run_finished` event; failed/interrupted → medium candidate; completed never a message
- [x] tests/services/test_autonomous_run_nudge.py rewritten

### Task 4: hollow promise forces action
- [x] `core/services/hollow_promise_round.py`: `next_round_tool_choice`, `note_detected`, `note_outcome`
- [x] visible_runs: `_hollow_force_next` → `tool_choice="required"` (openai-compat providers); outcome persisted after the forced round
- [x] tests/test_hollow_promise_round.py

### Task 5: drain the wells
- [x] `scripts/nudge_well_cleanup.py` (dry-run default): dismiss telemetry rows, dismiss stale midway, re-route real pending into candidates; drop pending autonomous_run entries from nudge_broend.json

## Measure after deploy

```sql
SELECT kind, json_extract(payload_json,'$.resolved'), count(*) FROM events
WHERE kind='runtime.hollow_promise_outcome' GROUP BY 1,2;
SELECT status, count(*) FROM proactive_candidates GROUP BY 1;
```
