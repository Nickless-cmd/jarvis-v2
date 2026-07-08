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

- **Tool-result aging does not exist.** Every agentic round re-sends all tool exchanges in full.
- **`_maybe_compact_agentic_messages`** ([visible_runs.py:904](../../../core/services/visible_runs.py)) → **`compact_run_messages`** ([run_compact.py:16](../../../core/context/run_compact.py)) is fully written but **never called** — dead code. Its marker is a plain `{"role":"user","content":"[KOMPRIMERET KONTEKST: …]"}` (run_compact.py:52).
- **`build_lean_base_messages`** ([visible_followup_lean.py:112](../../../core/services/visible_followup_lean.py), default OFF) already trims the heavy *per-turn tail* (inner-life/diagnostics) from the last user message on rounds ≥2. It **deliberately never touches tool exchanges** → aging is a genuinely separate gap.
- **`auto_compact.maybe_auto_compact_session`** (session-level, window-aware since Part 1) fires at [visible_runs.py:1176](../../../core/services/visible_runs.py). `chat.py` already emits `compacting`/`compacted` liveness events (chat.py:1085-1086) — partial SSE infra a compaction UI can hang on.

## Mechanism A — Cache-boundary invariant (piece #4)

**Purpose:** turn "the cache prefix is stable" from an assumption into a measured guard, with **zero prompt mutation**.

The deferred `__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__` becomes a **logical** split point, not injected text. Reordering the prompt or injecting a sentinel would each break the cache once; instead we only *observe*.

**Design:**
- `prompt_contract` computes, at assembly time, the index where the static section ends (the seam before the relocated dynamic tail) and a stable hash of the static prefix bytes. It exposes these as metadata (`static_prefix_len`, `static_prefix_sha`) — it does **not** insert anything into the prompt.
- A new observer `core/services/cache_boundary_observer.py` records `(provider, model, section_shape) → static_prefix_sha` per run and compares against the previous run for the same key. Unexpected drift → nerve `context/cache_boundary_drift` (severity scaled by how early the divergence is).
- `section_shape` = an ordered tuple of the section labels present (from `prompt_contract`'s existing `_section_labels`/ordering), so a legitimately different prompt shape (e.g. a section budgeted out) is not flagged as drift — only a *same-shape* byte change is.

**Behaviour change:** none. Pure observability. This is the guard that will catch future prompt regressions that silently bust caching.

## Mechanism B — Tool-result aging = micro-compact (pieces #1 + #3)

**Purpose:** keep recent tool results full, age older ones, on deep strong-lane loops.

**New module `core/services/tool_result_aging.py`:**

```
age_tool_results(
    messages: list[dict],
    *,
    keep_full: int = 5,
    mode: str,                 # "off" | "shadow" | "active"
    strength: str,             # from model_strength(model)
    round_index: int,
    compress_fn: Callable[[str], str] | None = None,
) -> tuple[list[dict], dict]   # (possibly-mutated messages, metrics)
```

**Policy:**
- **Gate:** only acts when `strength == "strong"` **and** `round_index >= _AGING_MIN_ROUND` (=6, past the weak-lane cap zone). Otherwise returns input unchanged, `changed=False`. Weak lanes are capped at ~4–8 rounds so aging never amortizes there.
- **Keep-full:** the `keep_full` (=5) most-recent tool-result messages are never aged.
- **Aging older results (hybrid, per the approved decision):**
  - **Default = clear:** replace content with deterministic placeholder `"[tool-resultat ryddet — {n} tegn. Kald værktøjet igen hvis du har brug for det.]"` where `{n}` = original char count. Byte-stable → cache-friendly.
  - **LLM-compress instead when** the run is *deep* (`round_index >= _AGING_COMPRESS_ROUND` =12) **and** the result is *large* (`len(content) >= _AGING_COMPRESS_MIN_CHARS` =2000) **and** `compress_fn` is provided. Uses the existing run-compact LLM (`_compact_llm_for_run`). Non-determinism is acceptable here because the summary is computed **once** and forward-carried within the run.
- **Identifying tool-result messages:** a message is an ageable tool result when `role in ("tool", "user")` **and** it carries the tool-result shape the loop appends (matched via the same serialization the loop uses — a helper `_is_tool_result_message(m)` co-located in the module, tested against real appended shapes). Placeholder/already-cleared messages are skipped (idempotence).

**Cache invariant (critical):** aging mutates `base_messages` **destructively at end-of-round**, after the retry loop, forward-carried. Because an aged message is replaced in place and never recomputed, subsequent rounds send it byte-identical. Aging never runs inside the retry fence, so D11 byte-identical retries are unaffected.

**Shadow vs active:**
- `mode="shadow"`: compute which results *would* be aged and the token delta; record nerve `context/tool_result_aging` with `would_free_tokens`; **do not mutate** `messages`.
- `mode="active"`: mutate + record `freed_tokens`.
- `mode="off"`: no-op.

**Kill-switch:** `settings.extra["tool_result_aging_mode"]` (+ env `JARVIS_TOOL_RESULT_AGING_MODE`), default `"shadow"`. Same dual-read pattern as `agentic_lean_prompt_enabled()`.

**Wiring (`visible_runs.py`, inline — fragile hot-path):** at end-of-round, after the round completes and after the steer-injection block, before the next round begins, call `age_tool_results(base_messages, …)` and assign the result back to `base_messages`. Emit nothing to the client (aging is invisible to the user; only the nerve records it).

## Mechanism C — Transparent run-compaction (piece #2)

**Purpose:** revive the dead level-2 compactor as a fallback when even aged results overflow the window, and make it visible to the client.

- **Wire `_maybe_compact_agentic_messages`** into the loop at end-of-round, **after** aging, only if `estimate_messages_tokens(base_messages) >= context_run_compact_threshold_tokens` still holds. (Aging runs first; compaction is the heavier fallback.)
- **Honest marker without breaking adapters:** in `run_compact.compact_run_messages`, keep the compact block's `role` as `"user"` (a mid-list `system` message breaks ollama/deepseek chat templates) but prefix content with a stable sentinel constant `_COMPACTION_SENTINEL = "⟢KONTEKST-KOMPRIMERET⟣"`: `content = f"{_COMPACTION_SENTINEL} {summary}"`. The sentinel is what the client keys on; it is byte-stable.
- **SSE event:** when a compaction actually mutates the list, emit `_sse("compaction", {"type":"compaction","run_id":…,"rounds_compacted":N,"freed_tokens":T})`. The client renders a compaction divider (reusing chat.py `compacting`/`compacted` UI affordances).
- **Shadow vs active:** `settings.extra["run_compaction_mode"]` (+ env), default `"shadow"`. Shadow logs would-compact metrics + nerve `context/run_compaction` without mutating and without SSE; active mutates + emits SSE.
- **Cache invariant:** same as B — end-of-round, forward-carried, outside the retry fence.

## Sequencing (inside the one plan)

Cache-safe → risky:
1. **A** — cache-boundary observer (zero prompt bytes, zero behaviour change).
2. **C** — revive compactor + marker + SSE, default shadow.
3. **B** — tool-result aging, default shadow, strong-lane-gated.

A and C prove out (shadow nerves visible in Central) before B's aging mutation is flipped active.

## Testing

- `tests/test_tool_result_aging.py`: keep-5 retention; clear-placeholder determinism (same input → identical bytes); compress-trigger boundary (deep+large only); strong-lane gate (weak → unchanged); round-threshold gate; forward-carry idempotence (aging an already-aged list is a no-op); shadow mode does not mutate.
- `tests/test_run_compact.py`: sentinel-prefixed marker; role stays `user`; compaction only above threshold.
- `tests/test_cache_boundary_observer.py`: same-shape byte change → drift nerve; different shape → no false drift; first-run baseline records without flagging.
- All new `core/…` modules need matching `tests/test_<stem>.py` (coverage gate).

## Files

- **New:** `core/services/tool_result_aging.py` + test; `core/services/cache_boundary_observer.py` + test.
- **Modify:** `core/context/run_compact.py` (sentinel marker); `core/services/visible_runs.py` (wire aging + compaction end-of-round, SSE event — inline); `core/services/prompt_contract.py` (expose `static_prefix_len`/`static_prefix_sha` metadata); `core/runtime/settings.py` (two new `extra` flags, defaults shadow).

## What this does NOT change

- None of the 7 coercion mechanisms.
- The lean-prompt transform (untouched; complementary — it trims the prompt tail, aging trims tool results).
- Session-level `auto_compact` (untouched).
- The prompt bytes themselves (Mechanism A is observation-only; B/C mutate the *message list*, not the system prompt, and only forward-carried).

## Deploy

Env `conda activate ai`; full-suite gate ~20 min; deploy = ff-pull + restart `jarvis-runtime` & `jarvis-api` on `bs@10.0.0.39`. Everything defaults to shadow/observe → behaviour is unchanged at deploy until a mode is flipped.
