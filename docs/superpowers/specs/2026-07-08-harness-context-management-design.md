# Harness Refactor Part B — Context & Tool-Result Management

**Date:** 2026-07-08
**Status:** Approved (design)
**Program:** Harness refactor (see `2026-07-08-harness-model-tiering-design.md` for the A/B/C/D/E map). Part 1 (earned model-trust + tiered instructions + window-aware compaction) shipped `a6b03b35` LIVE.
**Depends on:** `core/services/model_trust.py` (`model_strength`) from Part 1.

## Goal

Stop the agentic loop from re-sending every tool result in full on every round (the 20k+ token bloat Jarvis flagged), and make context-compaction transparent to the client — **without breaking the 98.5 % prefix-cache hit-rate** that keeps token-burn at ~$0.03/day.

## Non-negotiable constraint: cache-prefix byte-stability

The container relies on provider prefix-caching. Any change that mutates a byte *inside* the cached prefix mid-stream forces a re-cache of everything after that byte. Every mechanism below is designed around this:

- **A** changes **zero** prompt bytes (pure observability).
- **B** and **C** mutate `base_messages` **once, at end-of-round, forward-carried** — never inside the per-round retry fence ([visible_runs.py:2305](../../../core/services/visible_runs.py)), so the byte-identical-retry invariant (D11) holds. Each mutation costs one re-cache, then the aged/compacted list is carried forward unchanged.
- Both B and C default to **shadow** (compute + observe, do not mutate) and are gated behind kill-switches.

## Ground truth (verified in code, 2026-07-08)

- **Tool results live in `_followup_exchanges`** (a `list[ToolExchange]`, [visible_followup_events.py:128](../../../core/services/visible_followup_events.py)), **separate from `base_messages`** (chat history). Each `ToolExchange` has `.text`, `.tool_calls`, `.results: list[ToolResult]`, `.reasoning_content`; each `ToolResult` has `.tool_call_id`, `.tool_name`, `.content`. Tool-result bytes = `exchange.results[j].content`.
- **Provider-agnostic tool-result aging does not exist.** `OpenAICompatFollowupAdapter` ([visible_followup_adapters.py:669](../../../core/services/visible_followup_adapters.py) — the deepseek/GLM primary visible lane) and `CodexFollowupAdapter` (:1029) replay **all** exchanges full every round — this is the 20k+ bloat. Only `OllamaFollowupAdapter` has crude per-adapter bounding (`_compact_exchanges` :126 — keep last 10, hard-truncate each result at 8000 chars). Aging must be a **shared transform on `_followup_exchanges`** applied in `visible_runs.py` before the adapter call, so all lanes benefit and the policy is unified.
- **`_maybe_compact_agentic_messages`** ([visible_runs.py:904](../../../core/services/visible_runs.py)) → **`compact_run_messages`** ([run_compact.py:16](../../../core/context/run_compact.py)) is fully written but **never called** — dead code. Its marker is a plain `{"role":"user","content":"[KOMPRIMERET KONTEKST: …]"}` (run_compact.py:52).
- **`build_lean_base_messages`** ([visible_followup_lean.py:112](../../../core/services/visible_followup_lean.py), default OFF) already trims the heavy *per-turn tail* (inner-life/diagnostics) from the last user message on rounds ≥2. It **deliberately never touches tool exchanges** → aging is a genuinely separate gap.
- **`auto_compact.maybe_auto_compact_session`** (session-level, window-aware since Part 1) fires at [visible_runs.py:1176](../../../core/services/visible_runs.py). `chat.py` already emits `compacting`/`compacted` liveness events (chat.py:1085-1086) — partial SSE infra a compaction UI can hang on.

## Mechanism A — Cache-boundary invariant (piece #4)

**Purpose:** turn "the cache prefix is stable" from an assumption into a measured guard, with **zero prompt mutation**.

The deferred `__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__` becomes a **logical** split point, not injected text. Reordering the prompt or injecting a sentinel would each break the cache once; instead we only *observe*.

**Design:**
- The **system message** *is* the static prefix — the lean commentary confirms all per-turn dynamic content is relocated to the last *user* message, so `base_messages[0]` (the system message, built at [visible_runs.py:1738](../../../core/services/visible_runs.py)) is the cache-critical byte-stable region. Mechanism A hashes it there — **it does not touch `prompt_contract`** (a 3776-line Boy-Scout god file), avoiding both risk and the extract-first rule.
- A new observer `core/services/cache_boundary_observer.py` records `(provider, model, section_shape) → static_prefix_sha` per run and compares against the previous run for the same key. Unexpected drift → nerve `context/cache_boundary_drift`.
- `section_shape` = a coarse structural bucket = the number of `"\n\n"`-separated blocks in the system message. A legitimately restructured prompt (different block count) becomes a *different* key and cannot false-flag; only a *same-shape* byte change (the real cache-buster) trips the nerve. Coarse is fine — this is a regression tripwire, not a precise diff.
- Wiring is inline in `visible_runs.py` right after `base_messages` is built: `sha = sha256(base_messages[0]["content"])`, `shape = content.count("\n\n")`, then `observe_static_prefix(...)` in a try/except.

**Behaviour change:** none. Pure observability. This is the guard that will catch future prompt regressions that silently bust caching.

## Mechanism B — Tool-result aging = micro-compact (pieces #1 + #3)

**Purpose:** keep recent tool results full, age older ones, on deep strong-lane loops.

**New module `core/services/tool_result_aging.py`:**

```
age_tool_results(
    exchanges: list[ToolExchange],
    *,
    keep_full: int = 5,
    mode: str,                 # "off" | "shadow" | "active"
    strength: str,             # from model_strength(model)
    round_index: int,
    compress_fn: Callable[[str], str] | None = None,
) -> tuple[list[ToolExchange], dict]   # (possibly-new list, metrics)
```

Operates on `_followup_exchanges`. The ageable bytes are `exchange.results[j].content` on exchanges **older** than the `keep_full` most recent. `.text`, `.tool_calls`, `.reasoning_content` are left untouched (they carry the model's reasoning thread — cheap, and load-bearing for thinking models).

**Policy:**
- **Gate:** only acts when `strength == "strong"` **and** `round_index >= _AGING_MIN_ROUND` (=6, past the weak-lane cap zone). Otherwise returns input unchanged, `changed=False`. Weak lanes are capped at ~4–8 rounds so aging never amortizes there.
- **Keep-full:** the `keep_full` (=5) most-recent exchanges are never aged (slice `exchanges[-keep_full:]`).
- **Aging older exchanges (hybrid, per the approved decision):** for each `ToolResult` in an older exchange —
  - **Default = clear:** replace `.content` with deterministic placeholder `"[tool-resultat ryddet — {n} tegn. Kald værktøjet igen hvis du har brug for det.]"` where `{n}` = original char count. Byte-stable → cache-friendly.
  - **LLM-compress instead when** the run is *deep* (`round_index >= _AGING_COMPRESS_ROUND` =12) **and** the result is *large* (`len(content) >= _AGING_COMPRESS_MIN_CHARS` =2000) **and** `compress_fn` is provided. Uses the existing run-compact LLM (`_compact_llm_for_run`). Non-determinism is acceptable because the summary is computed **once** and forward-carried within the run.
- **Idempotence:** a `.content` already equal to a placeholder / already-compressed is skipped (starts-with the placeholder prefix or is short). Aging an already-aged list is a no-op → `changed=False`.

**Cache invariant (critical):** aging mutates `_followup_exchanges` **destructively at end-of-round**, after the retry loop, forward-carried — it replaces older exchanges' result content in place (builds new `ToolExchange`/`ToolResult` objects, reassigns the list) so subsequent rounds serialize them byte-identically. Aging never runs inside the retry fence, so D11 byte-identical retries are unaffected. This *supersedes* the crude Ollama truncation for the aged tail (Ollama's `_compact_exchanges` still runs on top harmlessly — it's deterministic on stable input).

**Shadow vs active:**
- `mode="shadow"`: compute which exchanges *would* be aged and the token delta; record nerve `context/tool_result_aging` with `would_free_tokens`; **return the input list unchanged**.
- `mode="active"`: return the aged list + record `freed_tokens`.
- `mode="off"`: no-op passthrough.

**Kill-switch:** `settings.extra["tool_result_aging_mode"]` (+ env `JARVIS_TOOL_RESULT_AGING_MODE`), default `"shadow"`. Same dual-read pattern as `agentic_lean_prompt_enabled()`.

**Wiring (`visible_runs.py`, inline — fragile hot-path):** at end-of-round, after the steer-injection block ([~visible_runs.py:3983](../../../core/services/visible_runs.py)) and before the next round begins, call `age_tool_results(_followup_exchanges, …)` and reassign `_followup_exchanges`. Emit nothing to the client (aging is invisible to the user; only the nerve records it).

## Mechanism C — Transparent compaction event (piece #2)

**Purpose:** make the compaction that *actually fires* visible to the client.

**Correction discovered during planning:** the `[KOMPRIMERET KONTEKST: …]` inline user-message ([run_compact.py:52](../../../core/context/run_compact.py)) belongs to `_maybe_compact_agentic_messages` — which is **dead code, never called**, and would target `base_messages` (chat history), a list that is *already post-compaction* at run start (session-level `auto_compact` runs at [visible_runs.py:1176](../../../core/services/visible_runs.py) before the loop). Reviving it adds nothing that `auto_compact` + Mechanism B don't already cover. The live compaction path — session-level `compact_session_history` — already stores a **dedicated DB `compact_marker`** (not an inline pseudo-message), so the "dedicated marker instead of a plain user-message" ask is *already satisfied* on the live path. What's missing is a **client-visible event** when it fires.

**Design:**
- At [visible_runs.py:1176](../../../core/services/visible_runs.py), capture the boolean return of `maybe_auto_compact_session(...)`. When `True`, emit `_sse("compaction", {"type":"compaction","run_id":run.run_id,"session_id":run.session_id})`. This is inside the SSE generator (yields already happen just above at :1161), so it reaches the client, which renders a compaction divider (reusing chat.py `compacting`/`compacted` affordances). Unknown-event-safe: clients ignore SSE event types they don't handle.
- Record nerve `context/run_compaction` (value `1.0`) on each live compaction so Central sees the cadence.
- **No behaviour change to the model:** the compaction itself already fires today; C only adds the client event + nerve. No shadow flag needed (it changes nothing the model sees); guarded only by a try/except so a telemetry failure never breaks the run.
- **Dead-code cleanup:** delete `_maybe_compact_agentic_messages` ([visible_runs.py:904](../../../core/services/visible_runs.py)) and `compact_run_messages` ([run_compact.py](../../../core/context/run_compact.py)) — Boy-Scout removal of the misleading dead path, so future readers don't wire the wrong list. `run_compact.py`'s test (if any) is removed with it.

## Sequencing (inside the one plan)

Cache-safe → risky:
1. **A** — cache-boundary observer (zero prompt bytes, zero behaviour change).
2. **C** — transparent compaction SSE event on the live path + dead-code cleanup (no model-facing change).
3. **B** — tool-result aging, default shadow, strong-lane-gated.

A and C carry zero risk; B ships shadow (nerve `context/tool_result_aging` visible in Central) before its aging mutation is flipped active per confidence.

## Testing

- `tests/test_tool_result_aging.py`: keep-5 retention (last 5 exchanges never aged); clear-placeholder determinism (same input → identical bytes); compress-trigger boundary (deep round ≥12 + result ≥2000 chars only); strong-lane gate (weak → unchanged); round-threshold gate (round <6 → unchanged); forward-carry idempotence (aging an already-aged list is a no-op); shadow mode returns input list unchanged.
- `tests/test_cache_boundary_observer.py`: same-shape byte change → drift nerve; different shape → no false drift; first-run baseline records without flagging.
- Mechanism C is verified live (trigger a compaction, confirm the SSE event) — no new unit test file; the deleted `compact_run_messages` takes its test with it.
- All new `core/…` modules need matching `tests/test_<stem>.py` (coverage gate).

## Files

- **New:** `core/services/tool_result_aging.py` + `tests/test_tool_result_aging.py`; `core/services/cache_boundary_observer.py` + `tests/test_cache_boundary_observer.py`.
- **Modify:** `core/services/visible_runs.py` (inline, all in this one file: wire the boundary observer right after `base_messages` is built ~:1738; wire aging at end-of-round on `_followup_exchanges` ~:3983; capture `maybe_auto_compact_session` return + emit `compaction` SSE ~:1176; delete dead `_maybe_compact_agentic_messages` ~:904). `prompt_contract.py` is **not** touched.
- **Delete:** `core/context/run_compact.py` (dead) + its test if present.
- **No `settings.py` change:** flags are read via `load_settings().extra.get("<flag>", "shadow")` + env, same pattern as `agentic_lean_prompt_enabled()`; the helper lives in `tool_result_aging.py`.

## What this does NOT change

- None of the 7 coercion mechanisms.
- The lean-prompt transform (untouched; complementary — it trims the prompt tail, aging trims tool results).
- Session-level `auto_compact` (untouched).
- The prompt bytes themselves (Mechanism A is observation-only; B/C mutate the *message list*, not the system prompt, and only forward-carried).

## Deploy

Env `conda activate ai`; full-suite gate ~20 min; deploy = ff-pull + restart `jarvis-runtime` & `jarvis-api` on `bs@10.0.0.39`. Everything defaults to shadow/observe → behaviour is unchanged at deploy until a mode is flipped.
