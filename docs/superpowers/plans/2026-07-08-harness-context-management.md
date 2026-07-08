# Harness Part B — Context & Tool-Result Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the agentic loop re-sending every tool result in full each round, and make the compaction that actually fires client-visible — without breaking the 98.5 % prefix-cache hit-rate.

**Architecture:** Three layered mechanisms (spec `docs/superpowers/specs/2026-07-08-harness-context-management-design.md`). **A** — a zero-mutation cache-boundary drift observer (hashes the static system message, flags same-shape byte drift). **B** — provider-agnostic tool-result aging on the shared `_followup_exchanges` list (keep 5 recent full; hybrid clear/compress older; strong-lane + round gated; forward-carried at end-of-round; default shadow). **C** — a `compaction` SSE event on the live session-compaction path + removal of the misleading dead run-compactor. Sequenced A → C → B (cache-safe first). All model-affecting behaviour ships shadow → zero change at deploy.

**Tech Stack:** Python 3.11, pytest, `conda activate ai`. Reuses `core.services.model_trust.model_strength` (Part 1), `core.services.central_timeseries.record`, `core.services.visible_followup_events.{ToolExchange,ToolResult}`.

**Execution note:** Tasks 1–2 are isolated pure modules → dispatch to a fresh **haiku** subagent each (1M-context models are credit-blocked). Tasks 3–6 touch the fragile hot-path `visible_runs.py` → **Claude takes these inline**. Controller verifies between tasks.

---

## File Structure

- **New** `core/services/tool_result_aging.py` — `age_tool_results()` transform + `tool_result_aging_mode()` flag helper. Pure; no import of `visible_runs` (compress_fn is injected).
- **New** `core/services/cache_boundary_observer.py` — `observe_static_prefix()`; in-memory last-sha map + drift nerve.
- **Modify** `core/services/visible_runs.py` — three inline wirings (boundary observer, aging, compaction SSE) + one deletion.
- **Delete** `core/context/run_compact.py` — dead code.
- **New tests** `tests/test_tool_result_aging.py`, `tests/test_cache_boundary_observer.py`.

---

## Task 1: `tool_result_aging.py` — aging transform + mode helper

**Files:**
- Create: `core/services/tool_result_aging.py`
- Test: `tests/test_tool_result_aging.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_tool_result_aging.py
from core.services.visible_followup_events import ToolExchange, ToolResult
from core.services.tool_result_aging import age_tool_results, tool_result_aging_mode


def _ex(content: str) -> ToolExchange:
    return ToolExchange(
        text="t", tool_calls=[{"id": "1"}],
        results=[ToolResult(tool_call_id="1", tool_name="read_file", content=content)],
        reasoning_content="r",
    )


def _exchanges(n: int, content: str = "x" * 500) -> list[ToolExchange]:
    return [_ex(content) for _ in range(n)]


def test_weak_lane_never_ages():
    ex = _exchanges(20)
    out, m = age_tool_results(ex, mode="active", strength="weak", round_index=30)
    assert out is ex and m["changed"] is False


def test_below_round_threshold_never_ages():
    ex = _exchanges(20)
    out, m = age_tool_results(ex, mode="active", strength="strong", round_index=3)
    assert out is ex and m["changed"] is False


def test_keeps_five_most_recent_full():
    ex = _exchanges(8, content="y" * 500)
    out, m = age_tool_results(ex, mode="active", strength="strong", round_index=7)
    # last 5 untouched, first 3 cleared
    assert m["changed"] is True and m["aged_exchanges"] == 3
    for e in out[-5:]:
        assert e.results[0].content == "y" * 500
    for e in out[:3]:
        assert e.results[0].content.startswith("[tool-resultat ryddet")


def test_clear_is_deterministic():
    ex = _exchanges(8, content="z" * 500)
    out1, _ = age_tool_results(ex, mode="active", strength="strong", round_index=7)
    out2, _ = age_tool_results(_exchanges(8, content="z" * 500),
                               mode="active", strength="strong", round_index=7)
    assert out1[0].results[0].content == out2[0].results[0].content


def test_idempotent_second_pass_is_noop():
    ex = _exchanges(8, content="w" * 500)
    out1, _ = age_tool_results(ex, mode="active", strength="strong", round_index=7)
    out2, m2 = age_tool_results(out1, mode="active", strength="strong", round_index=7)
    assert out2 is out1 and m2["changed"] is False


def test_shadow_does_not_mutate_but_reports():
    ex = _exchanges(8, content="s" * 500)
    out, m = age_tool_results(ex, mode="shadow", strength="strong", round_index=7)
    assert out is ex and m["changed"] is False
    assert m["aged_exchanges"] == 3 and m["would_free_tokens"] > 0


def test_off_is_passthrough():
    ex = _exchanges(8)
    out, m = age_tool_results(ex, mode="off", strength="strong", round_index=7)
    assert out is ex and m["changed"] is False


def test_compress_only_when_deep_and_large():
    # deep round + large result + compress_fn → compressed, not cleared
    ex = _exchanges(8, content="q" * 3000)
    out, m = age_tool_results(ex, mode="active", strength="strong",
                              round_index=12, compress_fn=lambda c: "SUMMARY")
    assert m["compressed"] == 3 and m["cleared"] == 0
    assert out[0].results[0].content == "SUMMARY"


def test_no_compress_when_shallow_even_if_large():
    ex = _exchanges(8, content="q" * 3000)
    out, m = age_tool_results(ex, mode="active", strength="strong",
                              round_index=7, compress_fn=lambda c: "SUMMARY")
    assert m["cleared"] == 3 and m["compressed"] == 0


def test_compress_failure_falls_back_to_clear():
    ex = _exchanges(8, content="q" * 3000)
    def _boom(c):
        raise RuntimeError("llm down")
    out, m = age_tool_results(ex, mode="active", strength="strong",
                              round_index=12, compress_fn=_boom)
    assert m["cleared"] == 3 and out[0].results[0].content.startswith("[tool-resultat ryddet")


def test_mode_helper_defaults_shadow(monkeypatch):
    monkeypatch.delenv("JARVIS_TOOL_RESULT_AGING_MODE", raising=False)
    monkeypatch.setattr("core.runtime.settings.load_settings",
                        lambda: type("S", (), {"extra": {}})())
    assert tool_result_aging_mode() == "shadow"


def test_mode_helper_env_wins(monkeypatch):
    monkeypatch.setenv("JARVIS_TOOL_RESULT_AGING_MODE", "active")
    assert tool_result_aging_mode() == "active"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_tool_result_aging.py -q`
Expected: FAIL — `ModuleNotFoundError: core.services.tool_result_aging`.

- [ ] **Step 3: Write the implementation**

```python
# core/services/tool_result_aging.py
"""Provider-agnostic tool-result aging for the visible agentic loop.

Keeps the ``keep_full`` most-recent tool exchanges full; ages older ones by
clearing (default, deterministic) or LLM-compressing (deep+large runs) each
tool result's content. Operates on the shared ``_followup_exchanges`` list so
every provider lane benefits (only the Ollama adapter had crude per-adapter
bounding before). Gated to strong lanes past a round threshold — weak lanes are
capped at ~4-8 rounds so aging never amortizes there.

Cache: the caller applies the returned list forward-carried at end-of-round
(outside the retry fence), so each aged result serializes byte-identically on
later rounds. Default mode is shadow (observe would-be savings, mutate nothing).
Never raises into the hot loop.
"""
from __future__ import annotations

import os
from typing import Callable

from core.services.visible_followup_events import ToolExchange, ToolResult

_AGING_MIN_ROUND = 6
_AGING_COMPRESS_ROUND = 12
_AGING_COMPRESS_MIN_CHARS = 2000
_CLEAR_PREFIX = "[tool-resultat ryddet"

_MODE_ENV = "JARVIS_TOOL_RESULT_AGING_MODE"
_VALID_MODES = ("off", "shadow", "active")


def tool_result_aging_mode() -> str:
    """Current aging mode: 'off' | 'shadow' | 'active'. Default 'shadow'.

    Env ``JARVIS_TOOL_RESULT_AGING_MODE`` wins over runtime-config. Self-safe."""
    env = os.environ.get(_MODE_ENV)
    if env is not None:
        v = env.strip().lower()
        if v in _VALID_MODES:
            return v
    try:
        from core.runtime.settings import load_settings
        v = str(load_settings().extra.get("tool_result_aging_mode", "shadow")).strip().lower()
        return v if v in _VALID_MODES else "shadow"
    except Exception:
        return "shadow"


def _clear_placeholder(n: int) -> str:
    return f"[tool-resultat ryddet — {n} tegn. Kald værktøjet igen hvis du har brug for det.]"


def _is_already_aged(content: str) -> bool:
    return content.startswith(_CLEAR_PREFIX)


def age_tool_results(
    exchanges: list[ToolExchange],
    *,
    keep_full: int = 5,
    mode: str,
    strength: str,
    round_index: int,
    compress_fn: Callable[[str], str] | None = None,
) -> tuple[list[ToolExchange], dict]:
    """Age tool-result content on exchanges older than the ``keep_full`` most recent.

    Returns ``(exchanges_out, metrics)``. In shadow mode ``exchanges_out`` IS the
    input list (unchanged) but ``metrics`` carry ``would_free_tokens``. In active
    mode a new list is returned. Never raises."""
    metrics: dict = {"changed": False, "mode": mode, "aged_exchanges": 0,
                     "cleared": 0, "compressed": 0, "would_free_chars": 0,
                     "would_free_tokens": 0}
    try:
        if mode == "off":
            return exchanges, metrics
        if strength != "strong" or round_index < _AGING_MIN_ROUND:
            return exchanges, metrics
        if len(exchanges) <= keep_full:
            return exchanges, metrics

        cut = len(exchanges) - keep_full
        old = exchanges[:cut]
        recent = exchanges[cut:]
        deep = round_index >= _AGING_COMPRESS_ROUND

        new_old: list[ToolExchange] = []
        freed = aged_ex = cleared = compressed = 0
        for ex in old:
            new_results: list[ToolResult] = []
            touched = False
            for tr in ex.results:
                content = str(tr.content or "")
                if not content or _is_already_aged(content):
                    new_results.append(tr)
                    continue
                do_compress = (deep and len(content) >= _AGING_COMPRESS_MIN_CHARS
                               and compress_fn is not None)
                replacement = ""
                if do_compress:
                    try:
                        replacement = str(compress_fn(content) or "").strip()
                    except Exception:
                        replacement = ""
                    if replacement:
                        compressed += 1
                    else:
                        replacement = _clear_placeholder(len(content))
                        cleared += 1
                else:
                    replacement = _clear_placeholder(len(content))
                    cleared += 1
                freed += max(0, len(content) - len(replacement))
                touched = True
                new_results.append(ToolResult(
                    tool_call_id=tr.tool_call_id,
                    tool_name=tr.tool_name,
                    content=replacement,
                ))
            if touched:
                aged_ex += 1
                new_old.append(ToolExchange(
                    text=ex.text, tool_calls=list(ex.tool_calls),
                    results=new_results, reasoning_content=ex.reasoning_content,
                ))
            else:
                new_old.append(ex)

        metrics.update({"aged_exchanges": aged_ex, "cleared": cleared,
                        "compressed": compressed, "would_free_chars": freed,
                        "would_free_tokens": freed // 4})
        if aged_ex == 0:
            return exchanges, metrics
        if mode == "shadow":
            return exchanges, metrics
        metrics["changed"] = True
        return new_old + recent, metrics
    except Exception:
        return exchanges, {"changed": False, "mode": mode, "error": True}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_tool_result_aging.py -q`
Expected: PASS (12 passed).

- [ ] **Step 5: Commit**

```bash
git add core/services/tool_result_aging.py tests/test_tool_result_aging.py
git commit -m "feat(harness): tool-result aging transform (Part B, Mechanism B)"
```

---

## Task 2: `cache_boundary_observer.py` — static-prefix drift observer

**Files:**
- Create: `core/services/cache_boundary_observer.py`
- Test: `tests/test_cache_boundary_observer.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cache_boundary_observer.py
import core.services.cache_boundary_observer as obs


def _reset():
    with obs._lock:
        obs._last_sha.clear()


def test_first_run_records_no_drift(monkeypatch):
    _reset()
    calls = []
    monkeypatch.setattr("core.services.central_timeseries.record",
                        lambda *a, **k: calls.append((a, k)))
    obs.observe_static_prefix(provider="p", model="m", section_shape=(3,),
                              static_prefix_sha="aaa")
    assert calls == []


def test_same_sha_no_drift(monkeypatch):
    _reset()
    calls = []
    monkeypatch.setattr("core.services.central_timeseries.record",
                        lambda *a, **k: calls.append(a))
    obs.observe_static_prefix(provider="p", model="m", section_shape=(3,), static_prefix_sha="aaa")
    obs.observe_static_prefix(provider="p", model="m", section_shape=(3,), static_prefix_sha="aaa")
    assert calls == []


def test_same_shape_changed_sha_records_drift(monkeypatch):
    _reset()
    calls = []
    monkeypatch.setattr("core.services.central_timeseries.record",
                        lambda *a, **k: calls.append((a, k)))
    obs.observe_static_prefix(provider="p", model="m", section_shape=(3,), static_prefix_sha="aaa")
    obs.observe_static_prefix(provider="p", model="m", section_shape=(3,), static_prefix_sha="bbb")
    assert len(calls) == 1
    assert calls[0][0][0] == "context" and calls[0][0][1] == "cache_boundary_drift"


def test_different_shape_is_different_key(monkeypatch):
    _reset()
    calls = []
    monkeypatch.setattr("core.services.central_timeseries.record",
                        lambda *a, **k: calls.append(a))
    obs.observe_static_prefix(provider="p", model="m", section_shape=(3,), static_prefix_sha="aaa")
    obs.observe_static_prefix(provider="p", model="m", section_shape=(4,), static_prefix_sha="bbb")
    assert calls == []  # different shape → different key → no drift


def test_empty_sha_ignored(monkeypatch):
    _reset()
    calls = []
    monkeypatch.setattr("core.services.central_timeseries.record",
                        lambda *a, **k: calls.append(a))
    obs.observe_static_prefix(provider="p", model="m", section_shape=(3,), static_prefix_sha="")
    assert calls == [] and not obs._last_sha
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_cache_boundary_observer.py -q`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

```python
# core/services/cache_boundary_observer.py
"""Cache-boundary drift observer (harness Part B, Mechanism A).

Zero prompt mutation. The system message is the STATIC prompt prefix (all
per-turn dynamic content is relocated to the last user message). This observer
records the last hash of that prefix per (provider, model, section_shape) and
flags when the SAME shape produces a DIFFERENT hash run-over-run — i.e. a byte
changed in the cached prefix, which silently busts provider prefix-caching.
Pure observability → nerve context/cache_boundary_drift. Never raises."""
from __future__ import annotations

import threading

_lock = threading.Lock()
_last_sha: dict[tuple, str] = {}


def observe_static_prefix(
    *,
    provider: str,
    model: str,
    section_shape: tuple,
    static_prefix_sha: str,
) -> None:
    """Record the static-prefix hash for (provider, model, shape); on a same-shape
    change from the previous run, emit the drift nerve. Best-effort, never raises."""
    try:
        sha = str(static_prefix_sha or "")
        if not sha:
            return
        key = (str(provider or ""), str(model or ""), tuple(section_shape or ()))
        with _lock:
            prev = _last_sha.get(key)
            _last_sha[key] = sha
        if prev is None or prev == sha:
            return
        try:
            from core.services import central_timeseries as _cts
            _cts.record("context", "cache_boundary_drift", 1.0, meta={
                "provider": key[0], "model": key[1], "shape": list(key[2]),
            })
        except Exception:
            pass
    except Exception:
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_cache_boundary_observer.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add core/services/cache_boundary_observer.py tests/test_cache_boundary_observer.py
git commit -m "feat(harness): cache-boundary drift observer (Part B, Mechanism A)"
```

---

## Task 3 (Claude inline): wire Mechanism A observer into `visible_runs.py`

**Files:**
- Modify: `core/services/visible_runs.py` (right after `base_messages` is built, ~line 1738)

- [ ] **Step 1: Locate the anchor**

Run: `grep -n "base_messages = serialize_ollama_chat_messages" core/services/visible_runs.py`
Expected: one hit near line 1738.

- [ ] **Step 2: Insert the observer call immediately after that assignment**

```python
                base_messages = serialize_ollama_chat_messages(visible_input_pre)
                # ── Cache-boundary drift observer (harness Part B, Mechanism A) ──
                # Zero prompt mutation: hash the STATIC system message (base_messages[0])
                # and flag same-shape byte drift that would silently bust prefix-caching.
                try:
                    if base_messages:
                        import hashlib as _hl_cb
                        _sys_content = str(base_messages[0].get("content") or "")
                        from core.services.cache_boundary_observer import observe_static_prefix
                        observe_static_prefix(
                            provider=getattr(run, "provider", "") or "",
                            model=getattr(run, "model", "") or "",
                            section_shape=(_sys_content.count("\n\n"),),
                            static_prefix_sha=_hl_cb.sha256(_sys_content.encode("utf-8")).hexdigest(),
                        )
                except Exception:
                    pass
```

- [ ] **Step 3: Byte-compile to verify syntax**

Run: `conda run -n ai python -m compileall core/services/visible_runs.py -q`
Expected: no output (success).

- [ ] **Step 4: Commit**

```bash
git add core/services/visible_runs.py
git commit -m "feat(harness): wire cache-boundary observer at prompt build (Part B, A)"
```

---

## Task 4 (Claude inline): Mechanism C — compaction SSE + dead-code removal

**Files:**
- Modify: `core/services/visible_runs.py` (~1174-1180 auto-compact block; delete `_maybe_compact_agentic_messages` ~904-926)
- Delete: `core/context/run_compact.py` + `tests/test_run_compact.py` if present

- [ ] **Step 1: Check for a run_compact test and any other importers**

Run: `ls tests/test_run_compact.py 2>/dev/null; grep -rn "run_compact\|_maybe_compact_agentic_messages" core/ apps/ tests/ | grep -v "test_tool_result_aging"`
Expected: only references inside the dead `_maybe_compact_agentic_messages` (visible_runs ~904-926) and possibly a test file. Confirm nothing live imports `compact_run_messages`.

- [ ] **Step 2: Replace the auto-compact block to capture the return and emit SSE**

Replace the existing block at ~1174-1180:

```python
    # Auto-compact chat history if approaching context limit
    try:
        from core.context.auto_compact import maybe_auto_compact_session
        _did_compact = maybe_auto_compact_session(
            run.session_id,
            provider=getattr(run, "provider", "") or "",
            model=getattr(run, "model", "") or "",
        )
    except Exception:
        _did_compact = False
    # ── Transparent compaction (harness Part B, Mechanism C) ──
    # The compaction already fired (session-level, stores a dedicated DB marker).
    # Make it client-visible + record cadence. No model-facing change.
    if _did_compact:
        yield _sse("compaction", {"type": "compaction", "run_id": run.run_id,
                                  "session_id": run.session_id})
        try:
            from core.services import central_timeseries as _cts_cmp
            _cts_cmp.record("context", "run_compaction", 1.0,
                            meta={"run_id": run.run_id, "session_id": run.session_id})
        except Exception:
            pass
```

- [ ] **Step 3: Delete the dead `_maybe_compact_agentic_messages` function**

Remove the whole `def _maybe_compact_agentic_messages(...)` block (~904-926). Keep `_compact_llm_for_run` (~898-901) — Mechanism B's compress_fn uses it.

- [ ] **Step 4: Delete the dead module + its test**

```bash
git rm core/context/run_compact.py
git rm tests/test_run_compact.py 2>/dev/null || true
```

- [ ] **Step 5: Byte-compile + coverage sanity**

Run: `conda run -n ai python -m compileall core/services/visible_runs.py core/context -q && grep -rn "run_compact" core/ apps/ | grep -v "auto_compact\|session_compact"`
Expected: compile clean; the grep returns nothing (no dangling references).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(harness): transparent compaction SSE + remove dead run-compactor (Part B, C)"
```

---

## Task 5 (Claude inline): wire Mechanism B aging into the agentic loop

**Files:**
- Modify: `core/services/visible_runs.py` (end-of-round, immediately after the steer-injection block ~3967-3983, still inside the `for _agentic_round` loop)

- [ ] **Step 1: Locate the anchor**

Run: `grep -n "agentic-loop-exit run_id" core/services/visible_runs.py`
The end-of-round steer block is the code just *above* this log line but *inside* the round loop. Insert aging after the steer `for s in steers:` block completes and before the round-loop iteration ends (i.e. after the `if steers:` block near ~3983, before the `logger.info("agentic-loop-exit"...)` which sits after the loop).

- [ ] **Step 2: Insert the aging call at end-of-round**

```python
                    # ── Tool-result aging (harness Part B, Mechanism B) ──────────
                    # Age older tool-result content ONCE per round, forward-carried
                    # (outside the retry fence at ~2305 → D11 byte-identical retries
                    # hold). Strong-lane + round gated inside age_tool_results;
                    # default shadow (observe, mutate nothing). Reassigning
                    # _followup_exchanges is a no-op in shadow (same object).
                    try:
                        from core.services.tool_result_aging import (
                            age_tool_results, tool_result_aging_mode)
                        from core.services.model_trust import model_strength
                        _age_mode = tool_result_aging_mode()
                        if _age_mode != "off":
                            _aged_ex, _age_metrics = age_tool_results(
                                _followup_exchanges,
                                mode=_age_mode,
                                strength=model_strength(getattr(run, "model", "") or ""),
                                round_index=_agentic_round,
                                compress_fn=_compact_llm_for_run,
                            )
                            _followup_exchanges = _aged_ex
                            if _age_metrics.get("aged_exchanges"):
                                try:
                                    from core.services import central_timeseries as _cts_age
                                    _cts_age.record(
                                        "context", "tool_result_aging",
                                        float(_age_metrics.get("would_free_tokens") or 0),
                                        meta={**_age_metrics, "run_id": run.run_id,
                                              "round": _agentic_round + 1,
                                              "active": _age_mode == "active"})
                                except Exception:
                                    pass
                    except Exception:
                        pass
```

Placement care: this must be at the same indentation as the round-body code (inside `for _agentic_round in range(...)`), AFTER the steer block, so it runs once per completed round. Verify by reading ~15 lines around the insertion that `_followup_exchanges` and `_agentic_round` are in scope (they are — appended at 3882).

- [ ] **Step 3: Byte-compile**

Run: `conda run -n ai python -m compileall core/services/visible_runs.py -q`
Expected: no output.

- [ ] **Step 4: Targeted import/smoke check**

Run: `conda run -n ai python -c "import core.services.visible_runs as v; import core.services.tool_result_aging as t; print('ok', t.tool_result_aging_mode())"`
Expected: `ok shadow`.

- [ ] **Step 5: Commit**

```bash
git add core/services/visible_runs.py
git commit -m "feat(harness): wire tool-result aging at end-of-round, shadow default (Part B, B)"
```

---

## Task 6: full-suite gate + deploy

**Files:** none (verification + deploy)

- [ ] **Step 1: Run the module tests together**

Run: `conda run -n ai python -m pytest tests/test_tool_result_aging.py tests/test_cache_boundary_observer.py -q`
Expected: PASS (17 passed).

- [ ] **Step 2: Full-suite gate (~20 min)**

Run: `conda run -n ai python -m pytest -q -p no:cacheprovider --timeout=45 --timeout-method=signal`
Expected: PASS. Known rotating isolation flakes (pass alone): meta_learning, forgetting_engine, subagent_ecology, heartbeat_self_knowledge, workspace_bootstrap, causal_quality — re-run any failure in isolation to confirm it's a flake, not a regression.

- [ ] **Step 3: Push**

```bash
git push
```
Expected: pre-push smoke test passes (allow ≥300 s).

- [ ] **Step 4: Deploy on the container (ff-pull + restart BOTH processes)**

```bash
ssh bs@10.0.0.39 'cd ~/jarvis-v2 && if git pull --ff-only; then echo PULLED; else echo PULL_FAILED; fi'
ssh bs@10.0.0.39 'cd ~/jarvis-v2 && git rev-parse --short HEAD'
```
Confirm HEAD matches the pushed commit. If the container has local commits blocking ff-only, MERGE (never overwrite/rebase) per deploy discipline, then re-verify HEAD.

Then restart both:
```bash
ssh bs@10.0.0.39 'systemctl --user restart jarvis-runtime jarvis-api && sleep 3 && systemctl --user is-active jarvis-runtime jarvis-api'
```
Expected: `active` / `active`.

- [ ] **Step 5: Verify live (shadow, zero behaviour change)**

```bash
ssh bs@10.0.0.39 'cd ~/jarvis-v2 && conda run -n ai python -c "from core.services.tool_result_aging import tool_result_aging_mode as m; print(\"aging mode:\", m())"'
```
Expected: `aging mode: shadow`. Send one visible chat turn; confirm it still answers normally. Over the next long strong-lane run, `jc series context:tool_result_aging` should show shadow `would_free_tokens` samples; `jc series context:cache_boundary_drift` should stay empty (no drift).

- [ ] **Step 6: Final commit note (none needed — all committed).** Update memory `project_harness_refactor_spec` with Part B shipped + the two planning corrections.

---

## Self-Review

**Spec coverage:** A (observer module T2 + wiring T3) ✓; B (aging module T1 + wiring T5) ✓; C (SSE + dead-code removal T4) ✓; cache invariants (forward-carry end-of-round, outside retry fence) encoded in T5 comment + placement step ✓; shadow defaults (T1 helper, verified T6 step 5) ✓; strong-lane/round gates (T1 tests) ✓; hybrid clear/compress (T1 tests) ✓; Boy-Scout (A avoids prompt_contract; C removes dead code) ✓.

**Placeholder scan:** none — all code blocks complete, all commands concrete.

**Type consistency:** `age_tool_results(exchanges, *, keep_full, mode, strength, round_index, compress_fn) -> (list[ToolExchange], dict)` used identically in T1 and T5; `observe_static_prefix(*, provider, model, section_shape, static_prefix_sha)` identical in T2 and T3; `tool_result_aging_mode()` identical in T1 and T5; `ToolExchange`/`ToolResult` field names (`text`, `tool_calls`, `results`, `reasoning_content` / `tool_call_id`, `tool_name`, `content`) match `visible_followup_events`.
