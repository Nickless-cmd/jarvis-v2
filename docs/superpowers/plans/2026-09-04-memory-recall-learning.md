# Memory, Recall & Learning Repair — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jarvis remembers, recalls and learns from mistakes: one ranked recall path, a prompt that actually carries relevant memory, noise writers silenced, and a closed lesson loop.

**Architecture:** No new storage layers. Fix ranking in the existing brain index, select MEMORY.md by section via the existing embedding index, route every recall source through one fused `recall()` entry point, gate noise at the writers, and add one small `lessons` table that every mistake source feeds and the prompt reads.

**Tech Stack:** Python 3.11, SQLite (FTS5 available on CT105 and locally), numpy, existing nomic embeddings via `semantic_memory._embed_ollama`, pytest.

**Branch:** `fix/memory-recall-learning` (worktree `.claude/worktrees/memory-fix`). Audit that motivated this: artifact "Hvorfor Jarvis ikke husker" (2026-09-04) and memory note `reference_memory_audit_2026_09`.

## Global Constraints

- Read-only vs. production: nothing in this plan restarts or mutates CT105. Data-cleanup is a dry-run-default script run only after Bjørn approves.
- No file over 1500 lines; `prompt_contract.py` (4673) is touched with surgical edits only, new logic goes in `core/services/prompt_sections/` modules.
- Every behaviour change has a unit test in `tests/`. Run `/opt/conda/envs/ai/bin/python -m pytest tests/<file> -q`.
- Commit via `python scripts/commit_with_attribution.py --repo . --actor opus --origin interactive --approved-by bjorn --message '...' --path ...`. New scripts/modules make `docs/reference/api` stale: run `scripts/api_docs_gen.py` + `scripts/api_reference_gen.py` and stage the docs.
- Danish user-facing prompt text; English code comments allowed.

---

## Root cause → task map

| Root cause | Task |
|---|---|
| R1 brain ranking runaway | Task 1 |
| R2 MEMORY.md = last 4 lines, recall under "citér aldrig" | Task 2 |
| R3 promotion template noise, unindexed curated-memory.md, md proposals | Task 3, Task 4 (mtime fix) |
| R4 learning has no path | Task 5 |
| R5 10 tools / 4 indexes / dead unified_recall / 73% empty | Task 4 |
| R6 write side drowns read side | Task 3 |
| R7 dual truth, 5 MEMORY.md writers, USER.md | Task 6 |
| Measurement | Task 7 |
| One-off data cleanup (approval-gated) | Task 8 |

---

### Task 1: Brain ranking — importance cap, cosine floor, bump discipline

**Files:** `core/services/jarvis_brain.py` (search_brain → search_brain_scored, bump_salience, frontmatter recall_count), `core/tools/jarvis_brain_tools.py` (min_cosine=0.5), `core/services/prompt_sections/jarvis_brain_facts.py` (no bump), `scripts/brain_salience_reset.py`, `tests/test_jarvis_brain_ranking.py`.

- [x] Tests: relevant beats runaway; salience capped by importance; bump once per 24h; tool passes min_cosine; auto-inject no bump; reset caps file+index.

### Task 2: Memory gets its own place in the prompt; MEMORY.md by section

**Files:** `core/services/memory_search.py` (`search_memory(query, *, limit, sources=None, workspace_dir=None)`, `_memory_files` by mtime), `core/services/prompt_sections/memory_md_selection.py` (`select_memory_md_sections`), `core/services/prompt_contract.py` (section selector, caps 3/1500; brain facts + multi-signal → `_dyn_memory_recall`; `[HUKOMMELSE]` header), `scripts/memory_md_dedupe_headings.py`, tests.

- [ ] Tests: section selection picks the matching section; dedupe merges duplicate headings with backup; prompt renders `[HUKOMMELSE]` once, brain facts not under `INTERN DIAGNOSTIK`.

### Task 3: Silence the noise writers

**Files:** `core/memory/promotion_substance.py` (`has_substance`, `is_telemetry_fragment`, `strip_telemetry_fragments`), `core/memory/private_layer_pipeline.py`, `core/runtime/db_private_signals.py`, `core/services/prompt_support_signals.py`, `core/services/memory_md_update_proposal_tracking.py` (sentence-like domain keys dropped; fresh > 7d → stale), `core/services/policy_abstraction.py` (reinforce instead of insert), `core/services/experiential_memory.py` (no empty lesson), `core/services/theory_of_mind.py` (user only), `core/services/semantic_indexer.py` + `semantic_memory.py` (skip released), `core/services/session_distillation.py` (strip telemetry), tests.

- [ ] Tests per gate.

### Task 4: One recall path

**Files:** `core/runtime/workspace_paths.py` (`workspace_dir_or_owner`), `core/services/memory_search.py`, `core/runtime/db_fts.py` (FTS5 over session_summaries + chat_messages), `core/services/recall.py` (`recall()` fused ranking), `core/tools/recall_tool.py` + registration + chat scope, delete `core/services/unified_recall.py`, `memory_recall_engine.multi_signal_recall_section` delegates, tests.

- [ ] Tests: FTS keyword hit; fused ordering; empty message + event; owner fallback; chat scope; dead module gone.

### Task 5: Lessons — learn from mistakes end to end

**Files:** `core/runtime/db_lessons.py`, `core/services/lessons.py`, hooks in `experience_correction_listener.py`, `visible_runs.py` (tool errors), `self_review_unified.py`, `regret_engine.py`, `arc_rule_extractor.py` (rules → proposed lessons; section returns ""), `prompt_contract.py` (lessons section + morning thread in tail), tests.

- [ ] Tests: upsert/evidence/repeat; correction stores words; section shape; arc rules proposed.

### Task 6: Hygiene — one MEMORY.md writer, USER.md core, dead duplicates

**Files:** `core/memory/memory_md_writer.py` (`upsert_section`), route `memory_tools`, `candidate_workflow`, `end_of_run_memory_consolidation` through it; `prompt_sections/workspace_files.py` USER.md `## Kerne`; delete `prospective_memory.py`; tests.

### Task 7: Probe set and measurement

**Files:** `tests/fixtures/memory_probes.json`, `scripts/memory_probe.py`, test.

### Task 8: One-off data cleanup (dry-run default, approval-gated)

**Files:** `scripts/memory_noise_cleanup.py`, test.

---

## Verification (end of plan)

1. Affected test files green; `python -m compileall core apps/api scripts` clean.
2. On CT105, read-only: clone branch to `/tmp/jarvis-branch`, run `scripts/memory_probe.py` against the live DB (no restart, no writes) → hit@3 before vs after.
3. Report to Bjørn; deploy + cleanup only on his go.
