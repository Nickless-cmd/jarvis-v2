# Harness Refactor Part C — Tool Concurrency

**Date:** 2026-07-08
**Status:** Approved (design)
**Program:** Harness refactor (see `2026-07-08-harness-model-tiering-design.md` A/B/C/D/E map). Part 1 (A, model-trust) `a6b03b35` + Part B (context) `aa3e604c` shipped LIVE. C is independent of trust-data accumulation.

## Goal

Execute independent tool calls within one agentic round **concurrently** instead of strictly sequentially, cutting wall-clock on multi-tool rounds (e.g. three `read_file` + a `search_memory`) — while preserving result ordering, cache-prefix byte-stability, approval/gate handling, and safety for anything that mutates state.

## Ground truth (verified 2026-07-08)

- The round executor `_execute_simple_tool_calls` ([visible_runs.py:5315](../../../core/services/visible_runs.py)) loops `for tc in tool_calls[:_MAX_CAPABILITIES_PER_TURN]:` and calls `_exec = execute_tool_force if force else execute_tool` one call at a time, appending results **in emission order**. This is the sequential bottleneck. It runs inside a single thread-pool worker the loop awaits at [visible_runs.py:3563](../../../core/services/visible_runs.py); an SSE heartbeat keeps the stream alive during it.
- **Per-call shared mutable state** (must stay race-free): the dedup set `controller.seen_simple_tool_call_signatures` (signature = `json.dumps({tool_name, arguments}, sort_keys=True)`, [:5384](../../../core/services/visible_runs.py)); `agentic_tool_cache.get_cached_result`/write; `controller.record(...)`; per-call gate decision (`gate_enforcement`) and `approval_needed`.
- **No read-only metadata on tools.** They are a flat `name → _exec_*` dispatch dict ([simple_tools.py](../../../core/tools/simple_tools.py)). Classification is ours to define.

## Two approved decisions

1. **Allowlist (read-only opt-in):** only an explicit set of known read-only tools may parallelize. Anything unlisted/new → treated as unsafe → sequential. Fail-safe: a new mutating tool is never accidentally parallelized.
2. **All-or-nothing mixed rounds:** a round parallelizes **only if every** call is allowlisted. Any non-safe tool present → the whole round runs sequentially exactly as today (byte-identical). Eliminates all read-vs-write reorder hazards.

## Architecture

### Boy-Scout extraction (prerequisite)

`visible_runs.py` is >2000 lines, so per the repo rule we first extract the nearest natural unit before modifying it: move `_execute_simple_tool_calls` (and its per-call helpers) into a new focused module `core/services/simple_tool_executor.py`, **re-exported** from `visible_runs` for backward compatibility (`from core.services.simple_tool_executor import _execute_simple_tool_calls`). Existing behaviour is byte-preserved by this move (pure relocation, no logic change) — verified by the existing executor tests passing unchanged. The concurrency logic then lives in this small, testable file rather than in-place in the 5700-line hot-path file.

### New module `core/services/tool_concurrency.py` (pure policy)

```
_PARALLEL_SAFE: frozenset[str]   # curated read-only allowlist
_MAX_CONCURRENCY = 6

def concurrency_mode() -> str:            # "off" | "on", default "off"
def is_parallelizable(tool_calls, *, mode) -> bool:
    # True iff mode=="on" AND len(tool_calls) >= 2 AND every call's name in _PARALLEL_SAFE
```

Initial `_PARALLEL_SAFE` (curated from the real registry — all read-only, no writes/approval/state-mutation): `read_file`, `read_tool_result`, `read_attachment`, `read_self_docs`, `read_model_config`, `read_mood`, `read_self_state`, `read_chronicles`, `read_dreams`, `list_dir`, `find_files`, `search`, `search_memory`, `search_chat_history`, `search_sessions`, `list_initiatives`, `list_proposals`, `list_scheduled_tasks`, `heartbeat_status`, `operator_read_file`, `operator_list_dir`, `operator_list_windows`, `operator_list_processes`, `operator_process_status`, `operator_process_list`, `operator_scheduled_list`, `operator_browser_get_text`, `operator_browser_get_links`, `operator_browser_status`, `operator_clipboard_read`, `operator_find_image`, `web_fetch`, `web_search`, `operator_webfetch`, `get_weather`, `get_exchange_rate`, `get_news`, `github_list_issues`, `github_list_prs`, `gmail_search`, `gmail_list`, `calendar_list_events`, `drive_search`, `docs_read`, `sheets_read`, `slides_read`, `pdf_read`, `note_list`, `note_search`, `hf_search_models`, `hf_model_info`.
(`operator_webfetch`/`web_fetch` are read-only network GETs — safe to overlap. Excluded on purpose: every `*write*`, `operator_bash*`, `operator_click/type/key`, mutation/rollback, approval-gated, and anything stateful.)

### Executor change (in `simple_tool_executor.py`)

"**Parallelize the invocation, serialize the bookkeeping**" — only the pure tool IO overlaps; all shared-state stays single-threaded:

1. **Not parallelizable** (`is_parallelizable` False) → the existing sequential loop runs unchanged (zero risk).
2. **Parallelizable** → three phases:
   - **Prepare (single-thread, in order):** for each call compute signature → dedup against `seen_...` set (and add), `agentic_tool_cache` lookup, gate decision. Produce a per-index plan entry: a finished result dict (duplicate/cached/gate-blocked) **or** a "run" token `(idx, name, arguments, exec_fn)`.
   - **Invoke (parallel):** run the "run" tokens' `exec_fn(name, arguments, ...)` concurrently via `ThreadPoolExecutor(max_workers=min(_MAX_CONCURRENCY, n))`, collecting raw results keyed by `idx`. Only the tool functions run here — no shared-state writes.
   - **Finalize (single-thread, in order):** for each executed call do cache-write + `controller.record` + result-dict assembly. Emit the full `results` list in **original index order**.

### Safety invariants

- **Determinism / cache byte-stability:** results are indexed and re-emitted in emission order regardless of completion order → serialization identical to the sequential path → prefix cache undisturbed. A test asserts parallel and sequential paths produce **identical** result lists.
- **No shared-state races:** dedup set, cache, and `controller.record` are only touched in the single-threaded prepare/finalize phases. The concurrent phase runs pure tool functions only.
- **Approval / gate / writes:** never in the allowlist → a round containing one is never parallelized → existing approval/gate/`force` logic runs untouched on the sequential path.
- **Streaming liveness:** the whole executor still runs inside the one outer thread-pool worker the loop awaits; the SSE heartbeat is unaffected.
- **Kill-switch:** `settings.extra["tool_concurrency_mode"]` (+ env `JARVIS_TOOL_CONCURRENCY_MODE`), default `"off"` → byte-identical to today until flipped. Same dual-read pattern as the Part B / lean flags.
- **Observability:** when a round runs in parallel, record nerve `tool/concurrency` with `{n, cap, saved_ms_estimate}` so Central sees when/how much it fires.

### Not in scope (YAGNI)

- **Model-tiering the cap:** a fixed `_MAX_CONCURRENCY = 6` (reads are IO-bound). Tiering the cap on `model_strength` is a trivial later lever, noted not built.
- **Partition (partial parallelism on mixed rounds):** rejected in favour of all-or-nothing.

## Testing

- `tests/test_tool_concurrency.py`: allowlist membership (a known write tool is NOT safe; a known reader IS); `is_parallelizable` — all-safe+≥2+on → True; one non-safe present → False; `<2` calls → False; mode off → False.
- `tests/test_simple_tool_executor.py` (new, covers the extracted module): sequential path unchanged (existing behaviour); parallel path produces a result list **identical** to sequential for the same read-only calls including out-of-order completion (fake tools with varied sleeps); dedup still suppresses a repeated identical call in a parallel round; a cached result is served without re-invoking; emission order preserved.
- Full-suite gate must stay green (the extraction must not change existing executor-test outcomes).

## Files

- **New:** `core/services/tool_concurrency.py` + `tests/test_tool_concurrency.py`.
- **New (Boy-Scout extraction):** `core/services/simple_tool_executor.py` (holds `_execute_simple_tool_calls` + per-call helpers, re-exported from `visible_runs`) + `tests/test_simple_tool_executor.py`.
- **Modify:** `core/services/visible_runs.py` (remove the executor body, add the re-export import — inline).

## Deploy

Env `conda activate ai`; full-suite gate ~20 min; deploy = ff-pull + restart `jarvis-runtime` & `jarvis-api` on `bs@10.0.0.39`. Ships `off` → zero behaviour change until flipped `on`.
