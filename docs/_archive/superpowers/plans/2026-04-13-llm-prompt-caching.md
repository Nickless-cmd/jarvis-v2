# LLM Prompt Caching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce daemon LLM calls by 60-80% through three layered caching mechanisms without losing output quality.

**Architecture:** Layer B (tick-scoped cache) provides per-tick memoization of identity/signal reads. Layer A (response cache) skips LLM calls when prompt hasn't changed. Layer C (call ordering) groups daemons by prompt prefix similarity for Ollama KV cache reuse. All three are independent and stack.

**Tech Stack:** Python 3.11, hashlib (SHA256), in-memory dicts, existing daemon_llm_call/heartbeat_runtime infrastructure.

---

### File Structure

| File | Responsibility |
|------|---------------|
| Create: `apps/api/jarvis_api/services/tick_cache.py` | Per-tick in-memory cache with start/end lifecycle |
| Modify: `apps/api/jarvis_api/services/daemon_llm.py` | Add response cache with TTL per daemon |
| Modify: `apps/api/jarvis_api/services/identity_composer.py` | Wire tick_cache into `build_identity_preamble()` |
| Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py` | Wire start/end_tick, reorder daemon groups |
| Create: `tests/test_tick_cache.py` | Tests for tick cache lifecycle |
| Create: `tests/test_daemon_llm_cache.py` | Tests for response cache TTL and hit/miss |

---

### Task 1: Tick Cache Module (Layer B foundation)

**Files:**
- Create: `apps/api/jarvis_api/services/tick_cache.py`
- Create: `tests/test_tick_cache.py`

- [ ] **Step 1: Write failing tests for tick cache**

```python
# tests/test_tick_cache.py
"""Tests for tick-scoped in-memory cache."""
from __future__ import annotations


class TestTickCacheInactive:
    def test_get_returns_none_when_inactive(self) -> None:
        from apps.api.jarvis_api.services import tick_cache

        tick_cache._cache = None
        assert tick_cache.get("anything") is None

    def test_set_is_noop_when_inactive(self) -> None:
        from apps.api.jarvis_api.services import tick_cache

        tick_cache._cache = None
        tick_cache.set("key", "value")
        assert tick_cache.get("key") is None


class TestTickCacheLifecycle:
    def test_start_activates_cache(self) -> None:
        from apps.api.jarvis_api.services import tick_cache

        tick_cache._cache = None
        tick_cache.start_tick()
        assert tick_cache._cache is not None
        tick_cache.end_tick()

    def test_end_clears_cache(self) -> None:
        from apps.api.jarvis_api.services import tick_cache

        tick_cache.start_tick()
        tick_cache.set("key", "value")
        tick_cache.end_tick()
        assert tick_cache._cache is None

    def test_get_set_within_tick(self) -> None:
        from apps.api.jarvis_api.services import tick_cache

        tick_cache.start_tick()
        tick_cache.set("energy", "high")
        assert tick_cache.get("energy") == "high"
        tick_cache.end_tick()

    def test_get_returns_none_for_missing_key(self) -> None:
        from apps.api.jarvis_api.services import tick_cache

        tick_cache.start_tick()
        assert tick_cache.get("nonexistent") is None
        tick_cache.end_tick()

    def test_start_tick_resets_previous_data(self) -> None:
        from apps.api.jarvis_api.services import tick_cache

        tick_cache.start_tick()
        tick_cache.set("old_key", "old_value")
        tick_cache.start_tick()
        assert tick_cache.get("old_key") is None
        tick_cache.end_tick()


class TestTickCacheStats:
    def test_stats_counts_hits_and_misses(self) -> None:
        from apps.api.jarvis_api.services import tick_cache

        tick_cache.start_tick()
        tick_cache.set("a", 1)
        tick_cache.get("a")  # hit
        tick_cache.get("b")  # miss
        stats = tick_cache.get_tick_cache_stats()
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        tick_cache.end_tick()

    def test_stats_when_inactive(self) -> None:
        from apps.api.jarvis_api.services import tick_cache

        tick_cache._cache = None
        stats = tick_cache.get_tick_cache_stats()
        assert stats["active"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_tick_cache.py -v`
Expected: FAIL — module not found or functions not defined

- [ ] **Step 3: Implement tick_cache module**

```python
# apps/api/jarvis_api/services/tick_cache.py
"""Tick-scoped in-memory cache — lives exactly one heartbeat tick.

Activated by start_tick() at tick start, cleared by end_tick() at tick end.
When inactive (_cache is None), get() returns None and set() is a no-op,
making it safe for non-heartbeat callers to use without guards.
"""
from __future__ import annotations

_cache: dict[str, object] | None = None
_hits: int = 0
_misses: int = 0


def start_tick() -> None:
    """Activate cache for this tick. Resets any previous data."""
    global _cache, _hits, _misses
    _cache = {}
    _hits = 0
    _misses = 0


def end_tick() -> None:
    """Deactivate cache and clear all data."""
    global _cache, _hits, _misses
    _cache = None
    _hits = 0
    _misses = 0


def get(key: str) -> object | None:
    """Return cached value or None. Safe to call when inactive."""
    global _hits, _misses
    if _cache is None:
        return None
    value = _cache.get(key)
    if value is not None:
        _hits += 1
    else:
        _misses += 1
    return value


def set(key: str, value: object) -> None:
    """Store value for this tick. No-op when inactive."""
    if _cache is None:
        return
    _cache[key] = value


def get_tick_cache_stats() -> dict[str, object]:
    """Return hit/miss stats for current tick."""
    return {
        "active": _cache is not None,
        "size": len(_cache) if _cache is not None else 0,
        "hits": _hits,
        "misses": _misses,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_tick_cache.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/tick_cache.py tests/test_tick_cache.py
git commit -m "feat: tick-scoped in-memory cache for heartbeat tick memoization"
```

---

### Task 2: Daemon Response Cache (Layer A)

**Files:**
- Modify: `apps/api/jarvis_api/services/daemon_llm.py`
- Create: `tests/test_daemon_llm_cache.py`

- [ ] **Step 1: Write failing tests for response cache**

```python
# tests/test_daemon_llm_cache.py
"""Tests for daemon LLM response cache."""
from __future__ import annotations

import time

import pytest


class TestResponseCacheHit:
    def test_second_call_returns_cached(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import apps.api.jarvis_api.services.daemon_llm as mod

        mod._response_cache.clear()
        call_count = 0

        def fake_cheap_lane(message: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"text": "LLM result", "provider": "groq"}

        monkeypatch.setattr(
            "apps.api.jarvis_api.services.non_visible_lane_execution.execute_cheap_lane",
            fake_cheap_lane,
        )

        result1 = mod.daemon_llm_call("test prompt", daemon_name="somatic")
        result2 = mod.daemon_llm_call("test prompt", daemon_name="somatic")

        assert result1 == result2
        assert call_count == 1  # only one LLM call

    def test_different_prompt_is_cache_miss(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import apps.api.jarvis_api.services.daemon_llm as mod

        mod._response_cache.clear()
        call_count = 0

        def fake_cheap_lane(message: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"text": f"Result {call_count}", "provider": "groq"}

        monkeypatch.setattr(
            "apps.api.jarvis_api.services.non_visible_lane_execution.execute_cheap_lane",
            fake_cheap_lane,
        )

        result1 = mod.daemon_llm_call("prompt A", daemon_name="somatic")
        result2 = mod.daemon_llm_call("prompt B", daemon_name="somatic")

        assert result1 != result2
        assert call_count == 2


class TestResponseCacheTTL:
    def test_expired_entry_is_cache_miss(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import apps.api.jarvis_api.services.daemon_llm as mod

        mod._response_cache.clear()
        call_count = 0

        def fake_cheap_lane(message: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"text": f"Result {call_count}", "provider": "groq"}

        monkeypatch.setattr(
            "apps.api.jarvis_api.services.non_visible_lane_execution.execute_cheap_lane",
            fake_cheap_lane,
        )

        # First call
        mod.daemon_llm_call("test prompt", daemon_name="somatic")

        # Expire the entry manually
        for key in mod._response_cache:
            text, _ = mod._response_cache[key]
            mod._response_cache[key] = (text, time.time() - 1)

        # Second call should be a miss
        mod.daemon_llm_call("test prompt", daemon_name="somatic")
        assert call_count == 2

    def test_ttl_varies_by_daemon_name(self) -> None:
        from apps.api.jarvis_api.services.daemon_llm import _get_cache_ttl

        assert _get_cache_ttl("somatic") == 90
        assert _get_cache_ttl("thought_stream") == 90
        assert _get_cache_ttl("curiosity") == 180
        assert _get_cache_ttl("meta_reflection") == 600
        assert _get_cache_ttl("session_summary") == 0
        assert _get_cache_ttl("unknown_daemon") == 120


class TestResponseCacheRules:
    def test_empty_response_not_cached(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import apps.api.jarvis_api.services.daemon_llm as mod

        mod._response_cache.clear()

        def fake_cheap_lane(message: str) -> dict:
            return {"text": "", "provider": "groq"}

        monkeypatch.setattr(
            "apps.api.jarvis_api.services.non_visible_lane_execution.execute_cheap_lane",
            fake_cheap_lane,
        )

        mod.daemon_llm_call("test", fallback="fallback text", daemon_name="somatic")
        assert len(mod._response_cache) == 0

    def test_no_cache_when_daemon_name_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import apps.api.jarvis_api.services.daemon_llm as mod

        mod._response_cache.clear()

        def fake_cheap_lane(message: str) -> dict:
            return {"text": "Result", "provider": "groq"}

        monkeypatch.setattr(
            "apps.api.jarvis_api.services.non_visible_lane_execution.execute_cheap_lane",
            fake_cheap_lane,
        )

        mod.daemon_llm_call("test", daemon_name="")
        assert len(mod._response_cache) == 0

    def test_no_cache_for_session_summary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import apps.api.jarvis_api.services.daemon_llm as mod

        mod._response_cache.clear()

        def fake_cheap_lane(message: str) -> dict:
            return {"text": "Summary text", "provider": "groq"}

        monkeypatch.setattr(
            "apps.api.jarvis_api.services.non_visible_lane_execution.execute_cheap_lane",
            fake_cheap_lane,
        )

        mod.daemon_llm_call("test", daemon_name="session_summary")
        assert len(mod._response_cache) == 0


class TestCacheHitLogging:
    def test_cache_hit_logs_with_provider_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import apps.api.jarvis_api.services.daemon_llm as mod

        mod._response_cache.clear()
        logged: list[dict] = []

        def fake_cheap_lane(message: str) -> dict:
            return {"text": "Result", "provider": "groq"}

        def fake_log(**kwargs: object) -> None:
            logged.append(dict(kwargs))

        monkeypatch.setattr(
            "apps.api.jarvis_api.services.non_visible_lane_execution.execute_cheap_lane",
            fake_cheap_lane,
        )
        monkeypatch.setattr(
            "core.runtime.db.daemon_output_log_insert",
            fake_log,
        )

        mod.daemon_llm_call("test", daemon_name="somatic")
        mod.daemon_llm_call("test", daemon_name="somatic")  # cache hit

        cache_logs = [l for l in logged if l.get("provider") == "cache"]
        assert len(cache_logs) == 1
        assert cache_logs[0]["daemon_name"] == "somatic"
        assert cache_logs[0]["success"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_daemon_llm_cache.py -v`
Expected: FAIL — `_response_cache` and `_get_cache_ttl` not found

- [ ] **Step 3: Implement response cache in daemon_llm.py**

Replace the entire contents of `apps/api/jarvis_api/services/daemon_llm.py` with:

```python
"""Shared LLM call for daemons — cheap lane first, heartbeat model fallback.

Includes prompt-hash response cache (Layer A) that skips LLM calls when
the same prompt is seen within the daemon's TTL window.
"""
from __future__ import annotations

import hashlib
import time

# ---------------------------------------------------------------------------
# Response cache — Layer A
# ---------------------------------------------------------------------------

_response_cache: dict[str, tuple[str, float]] = {}
# key: SHA256(prompt), value: (response_text, expires_at_timestamp)

_DAEMON_TTL: dict[str, int] = {
    # Fast (2-3 min cadence)
    "somatic": 90,
    "thought_stream": 90,
    # Medium (5-10 min cadence)
    "curiosity": 180,
    "conflict": 180,
    "reflection_cycle": 180,
    "user_model": 180,
    # Slow (30min+ cadence)
    "meta_reflection": 600,
    "irony": 600,
    "aesthetic_taste": 600,
    "development_narrative": 600,
    "existential_wonder": 600,
    "code_aesthetic": 600,
    # No cache
    "session_summary": 0,
}
_DEFAULT_TTL = 120


def _get_cache_ttl(daemon_name: str) -> int:
    """Return TTL in seconds for a daemon. 0 means no caching."""
    return _DAEMON_TTL.get(daemon_name, _DEFAULT_TTL)


def _check_cache(cache_key: str) -> str | None:
    """Return cached response if present and not expired, else None."""
    entry = _response_cache.get(cache_key)
    if entry is None:
        return None
    text, expires_at = entry
    if time.time() > expires_at:
        del _response_cache[cache_key]
        return None
    return text


def _store_cache(cache_key: str, text: str, daemon_name: str) -> None:
    """Store response in cache with daemon-specific TTL."""
    ttl = _get_cache_ttl(daemon_name)
    if ttl <= 0:
        return
    _response_cache[cache_key] = (text, time.time() + ttl)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def daemon_llm_call(
    prompt: str,
    *,
    max_len: int = 200,
    fallback: str = "",
    daemon_name: str = "",
) -> str:
    """Call LLM for daemon output. Tries cache first, then cheap lane (Groq),
    then heartbeat model. Returns stripped text or fallback on failure. Never raises.
    Logs raw output to daemon_output_log when daemon_name is provided.
    """
    # --- Layer A: check response cache ---
    cache_key = ""
    if daemon_name and _get_cache_ttl(daemon_name) > 0:
        cache_key = hashlib.sha256(prompt.encode()).hexdigest()
        cached = _check_cache(cache_key)
        if cached is not None:
            # Log cache hit for observability
            if daemon_name:
                try:
                    from core.runtime.db import daemon_output_log_insert

                    daemon_output_log_insert(
                        daemon_name=daemon_name,
                        raw_llm_output=cached[:2000],
                        parsed_result=cached[:500],
                        success=True,
                        provider="cache",
                    )
                except Exception:
                    pass
            return cached

    text = ""
    provider = ""

    # 1. Try cheap lane (Groq / fast provider)
    try:
        from apps.api.jarvis_api.services.non_visible_lane_execution import (
            execute_cheap_lane,
        )

        result = execute_cheap_lane(message=prompt)
        text = str(result.get("text") or "").strip()
        provider = str(result.get("provider") or "cheap")
    except Exception:
        pass

    # 2. Fallback to heartbeat model (Ollama / configured provider)
    if not text:
        try:
            from apps.api.jarvis_api.services.heartbeat_runtime import (
                _execute_heartbeat_model,
                _select_heartbeat_target,
                load_heartbeat_policy,
            )

            policy = load_heartbeat_policy()
            target = _select_heartbeat_target()
            result = _execute_heartbeat_model(
                prompt=prompt,
                target=target,
                policy=policy,
                open_loops=[],
                liveness=None,
            )
            text = str(result.get("text") or "").strip()
            provider = str(target.get("provider") or "heartbeat")
        except Exception:
            pass

    # 3. Clean up quotes
    raw_text = text
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()

    final = text[:max_len] if text else fallback

    # --- Layer A: store in cache (only successful responses) ---
    if cache_key and text:
        _store_cache(cache_key, final, daemon_name)

    # 4. Log output for debugging
    if daemon_name:
        try:
            from core.runtime.db import daemon_output_log_insert

            daemon_output_log_insert(
                daemon_name=daemon_name,
                raw_llm_output=raw_text[:2000],
                parsed_result=final[:500],
                success=bool(text),
                provider=provider,
            )
        except Exception:
            pass

    return final
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_daemon_llm_cache.py -v`
Expected: 8 passed

- [ ] **Step 5: Run existing tests to verify no regressions**

Run: `conda run -n ai python -m pytest tests/test_signal_decay.py tests/test_web_cache.py tests/test_session_summaries.py tests/test_tick_cache.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add apps/api/jarvis_api/services/daemon_llm.py tests/test_daemon_llm_cache.py
git commit -m "feat: daemon LLM response cache — hash-based with per-daemon TTL"
```

---

### Task 3: Wire Tick Cache into Heartbeat + Identity (Layer B integration)

**Files:**
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py`
- Modify: `apps/api/jarvis_api/services/identity_composer.py`

- [ ] **Step 1: Wire start_tick/end_tick into heartbeat_runtime.py**

Find the daemon section start (around line 1733, after `# Circadian energy` block, before `# Somatic phrase`). Add `start_tick()` before the first daemon and `end_tick()` after the last daemon group.

In `heartbeat_runtime.py`, find this line (around line 1746):

```python
    # Somatic phrase
    if _dm.is_enabled("somatic"):
```

Add immediately BEFORE it:

```python
    # --- Layer B: activate tick-scoped cache for daemon reads ---
    try:
        from apps.api.jarvis_api.services import tick_cache
        tick_cache.start_tick()
    except Exception:
        pass

```

Then find the end of the daemon section. After the last daemon block (council_memory, around line 2125), add:

```python
    # --- Layer B: deactivate tick-scoped cache ---
    try:
        from apps.api.jarvis_api.services import tick_cache
        tick_cache.end_tick()
    except Exception:
        pass

```

- [ ] **Step 2: Wire tick_cache into identity_composer.py**

In `apps/api/jarvis_api/services/identity_composer.py`, modify `build_identity_preamble()` (line 59-72). Replace the function body:

```python
def build_identity_preamble() -> str:
    """Return signal-driven identity string: '{name}. {bearing}. {energy}.'

    Falls back gracefully if signals are unavailable — always returns at least '{name}.'.
    Uses tick_cache when active to avoid rebuilding 12+ times per heartbeat tick.
    """
    try:
        from apps.api.jarvis_api.services import tick_cache
        cached = tick_cache.get("identity_preamble")
        if cached is not None:
            return cached
    except Exception:
        pass

    name = get_entity_name()
    parts = [name]
    bearing = _read_bearing()
    if bearing:
        parts.append(bearing)
    energy = _read_energy()
    if energy:
        parts.append(f"Energi: {energy}")
    result = ". ".join(parts) + "."

    try:
        from apps.api.jarvis_api.services import tick_cache
        tick_cache.set("identity_preamble", result)
    except Exception:
        pass

    return result
```

- [ ] **Step 3: Compile check**

Run: `conda run -n ai python -m compileall apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/services/identity_composer.py apps/api/jarvis_api/services/tick_cache.py -q`
Expected: No output (success)

- [ ] **Step 4: Run all tests**

Run: `conda run -n ai python -m pytest tests/test_tick_cache.py tests/test_daemon_llm_cache.py tests/test_signal_decay.py tests/test_web_cache.py tests/test_session_summaries.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/services/identity_composer.py
git commit -m "feat: wire tick cache into heartbeat lifecycle and identity preamble"
```

---

### Task 4: Reorder Daemon Execution (Layer C)

**Files:**
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py`

- [ ] **Step 1: Reorder daemon blocks**

In `heartbeat_runtime.py`, the daemon blocks (lines ~1746-2125) must be reordered. Move the entire `if _dm.is_enabled("...")` blocks into this order, keeping each block's code identical — only the ORDER changes:

**Group 1 — Hardware/energy context:**
1. `somatic` (currently first — stays)
2. `surprise` (move up from after somatic)
3. `conflict` (move up from after thought_action_proposal)

**Group 2 — Thought-stream context:**
4. `thought_stream` (move up)
5. `curiosity` (stays near thought_stream)
6. `thought_action_proposal` (stays near thought_stream)
7. `reflection_cycle` (move here)

**Group 3 — Cross-signal snapshot:**
8. `meta_reflection` (stays)
9. `user_model` (move here)

**Group 4 — Rare cadence (30min+/daily/weekly):**
10. `aesthetic_taste` (move here)
11. `irony` (move here)
12. `development_narrative` (stays)
13. `existential_wonder` (stays)
14. `code_aesthetic` (stays)

**Group 5 — Non-LLM / independent:**
15. `experienced_time` (move here)
16. `absence` (stays)
17. `creative_drift` (stays)
18. `dream_insight` (stays)
19. `memory_decay` (stays)
20. `signal_decay` (stays)
21. `desire` (stays)
22. `autonomous_council` (stays)
23. `council_memory` (stays)

Add group comments before each group:

```python
    # ── Group 1: Hardware/energy context (Ollama KV-cache friendly) ──
```
```python
    # ── Group 2: Thought-stream context ──
```
```python
    # ── Group 3: Cross-signal snapshot ──
```
```python
    # ── Group 4: Rare cadence (30min+/daily/weekly LLM daemons) ──
```
```python
    # ── Group 5: Non-LLM / independent daemons ──
```

**Important:** The `conflict` daemon reads from `_tss`, `_surp`, etc. — variables set by earlier daemons. After reordering, `conflict` comes BEFORE `thought_stream`. This means `conflict` must handle the case where `_tss` doesn't exist yet. Currently it uses `"_tss" in dir()` checks, which will evaluate correctly — if `_tss` is not yet defined, the check returns empty string. The existing guards handle this.

Actually, looking more carefully: `conflict` reads `_iv_mode_ts`, `_tss`, `_surp` — all set by `surprise` and `thought_stream`. Since `surprise` is in group 1 (before conflict) and `thought_stream` is in group 2 (after conflict in this ordering), `conflict` would lose access to `_tss`.

**Revised Group 1 ordering** to preserve data dependencies:

**Group 1 — Hardware/energy + thought foundation:**
1. `somatic`
2. `surprise`
3. `thought_stream`
4. `thought_action_proposal`
5. `conflict` (needs _tss, _surp from above)

**Group 2 — Reflection + curiosity:**
6. `reflection_cycle` (needs _tss, _surp, conflict)
7. `curiosity` (needs _tss)
8. `meta_reflection` (needs everything above)
9. `user_model`

**Group 3 — Rare cadence:**
10. `aesthetic_taste`
11. `irony`
12. `development_narrative`
13. `existential_wonder`
14. `code_aesthetic`

**Group 4 — Non-LLM / independent:**
15. `experienced_time`
16. `absence`
17. `creative_drift`
18. `dream_insight`
19. `memory_decay`
20. `signal_decay`
21. `desire`
22. `autonomous_council`
23. `council_memory`

- [ ] **Step 2: Compile check**

Run: `conda run -n ai python -m compileall apps/api/jarvis_api/services/heartbeat_runtime.py -q`
Expected: No output (success)

- [ ] **Step 3: Run all tests**

Run: `conda run -n ai python -m pytest tests/test_tick_cache.py tests/test_daemon_llm_cache.py tests/test_signal_decay.py tests/test_web_cache.py tests/test_session_summaries.py -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/services/heartbeat_runtime.py
git commit -m "refactor: reorder daemon execution for Ollama KV-cache locality"
```

---

### Self-Review

**Spec coverage:**
- Layer A (daemon response cache): Task 2 ✓
- Layer B (tick cache): Task 1 (module) + Task 3 (integration) ✓
- Layer C (call ordering): Task 4 ✓
- Observability (cache hit logging with provider="cache"): Task 2 Step 3 ✓
- Observability (tick cache stats): Task 1 Step 3 ✓
- What we do NOT cache: enforced in Task 2 (session_summary TTL=0, empty responses not cached) ✓
- Testing: Task 1 + Task 2 ✓

**Placeholder scan:** No TBD/TODO/placeholders found.

**Type consistency:** `_get_cache_ttl` used consistently in both test (Step 1) and implementation (Step 3). `tick_cache.get/set/start_tick/end_tick` used consistently across Task 1 and Task 3.
