---
status: færdig
audited: 2026-07-08
ground_truth: 1/1 refs alive, 2d old
---
# Centralens resterende blinde vinkler (2026-07-06)

> Fundet af 8-bøtte multi-agent investigation (137 services) + adversarisk verifikation.
> Kilde: docs/central_connectivity_matrix.md. Kør `python scripts/central_connectivity_audit.py` for at regenerere grundlaget.

## Executive summary

Efter adversarisk verifikation: **2 bekræftede WIRE_HIGH blinde vinkler**. Resten faldt til
WIRE_LOW (19), DEAD_LEAVE (66) eller FALSE_POSITIVE (46 — matrixen over-flagger kraftigt).

**Vigtigste blinde vinkel:** `compact_ground_truth` — når en komprimerings-summary modsiger
git/DB ground-truth (fabrikeret hukommelse) ser Centralen intet. Præcis den fejlklasse der
ramte os da auto-komprimering stoppede ubemærket ~23. juni.

## WIRE_HIGH (bekræftet) — sorteret efter værdi ÷ effort

| # | Service | Bøtte | Tabt signal | Effort | Evidens |
|---|---------|-------|-------------|--------|---------|
| 1 | **compact_ground_truth** ⚠️ | context | Verificeret-falske komprimerings-claims (hallucineret hukommelse) skrives KUN til privat tabel `compaction_validation_failures` — ingen event, ingen `central()`. Eneste overflade = `logger.warning` (som ikke engang rammer container-journalen). | **S** | `compact_ground_truth.py:408/476-477`; konsumeret af `session_compact.py:79-91` |
| 2 | **process_watcher** | dark_b | `process_watcher.match` fyres når en konfigureret runtime-state-watch tripper — men `match`-familien er ikke i bridge → watches er usynlige. Bruger/Jarvis-erklærede conditions-of-interest. | **M** | `process_watcher.py:470` `event_bus.publish('process_watcher.match')`; ikke i FAMILY_ROUTES |

## WIRE_LOW / senere (19 — de mest interessante)

- **cheap_lane_balancer** — per-slot provider-health (circuit-breaker/cooldowns). Overlapper eksisterende provider-health-nerve.
- **context_window_manager** — read-only kontekst-pres; `_emit_context_window_manager_event` **defineret og aldrig kaldt** (dead decoy).
- **runtime_hook_runtime** — heartbeat-initiative → followup-task. Synlighed i hook→task.
- **task_worker** — succeeded/failed/blocked outcomes pr. runtime_task.
- **memory_pruning_daemon** — `memory_pruning.cycle_completed` counts ("learning to forget").
- **meta_learning_retrospective** — ugentlig LLM-retrospektiv memo.

## DEAD_LEAVE (66) / FALSE_POSITIVE (46)

Mest bemærkelsesværdige falske positiver (fælder ved næste audit):
- **session_compact** — kun logger-overflade; ægte kilde er compact_ground_truth. Ikke dobbelt-wire.
- **Tool-wrappers en masse** (operator_tools, process_tools, recall_memory_tools, stripe_tools, …) — observeres allerede via execute_tool/tool_observer.
- **Dream/reflection-lag** (dream_consolidation_daemon, dream_motif_daemon, deep_reflection_slot, thought_stream_daemon, apophenia_guard) — PRIVATE_NO_EGRESS, ikke Centralens mandat.
- **process_watcher_tools** = falsk positiv, men **process_watcher** (daemonen) er ægte WIRE_HIGH — forveksl dem ikke.

## Anbefalet rækkefølge

1. **Wire `compact_ground_truth` → Centralen (effort S, højest ROI).** Efter INSERT i `_log_validation_failure` (`:476-477`): emit `compaction/validation_failed` (marker_id, claim, verdict, modsigelse). Lukker 23.-juni-regressionen. Metadata-only, ingen dual-truth.
2. **Tilføj `process_watcher.match` til FAMILY_ROUTES (effort M).** Alle watch-fires synlige, ikke kun opt-in actions.
3. **Wire `runtime_hook_runtime` hook→task-dispatch (effort S-M).**
4. **Wire `task_worker` task-outcomes (effort M).** #3+#4 dækker hele hook→task→outcome-kæden.
5. **Ryd dead decoy i `context_window_manager`** — wire kontekst-pres reelt, eller slet den ubrugte `_emit`-funktion.
