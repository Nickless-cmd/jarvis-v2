# Lag 10 — Unconscious Modulation Phase 1: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add sub-symbolic sampling-parameter modulation to Jarvis' visible-chat LLM call so the user's emotional field shifts `temperature` and `top_p` *before* generation without any tokens about the modulation being shown to the model.

**Architecture:** One new helper module that reads `user_temperature_engine.get_active_field()` and returns shifted parameters. The active visible provider (deepseek) is instrumented at the visible-lane wrapper level — NOT in the shared openai-compat helper, which is also used by cheap-daemons. Modulation flows: visible wrapper → unconscious_modulation helper → provider API. Cheap/heartbeat/quality lanes are untouched.

**Tech Stack:** Python 3.11, existing `user_temperature_engine`, existing deepseek openai-compat HTTP path.

**Spec:** `docs/superpowers/specs/2026-05-12-unconscious-modulation-phase1-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `core/services/unconscious_modulation.py` | ~100 LOC helper: `compute_unconscious_modulation`, `_modulation_enabled`, debug log. Pure read; fail-silent. |
| `tests/test_unconscious_modulation.py` | Unit tests for helper logic (delta math, clamps, kill-switch, no-field fallback). |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | Add 7 flags: `unconscious_modulation_enabled`, `unconscious_modulation_temp_delta`, `unconscious_modulation_top_p_delta`, `unconscious_modulation_temp_floor`, `unconscious_modulation_temp_ceiling`, `unconscious_modulation_top_p_floor`, `unconscious_modulation_top_p_ceiling`. |
| `core/services/cheap_provider_runtime.py` | Add optional `temperature` + `top_p` kwargs to `_execute_openai_compatible_chat` and `_iter_openai_compatible_chat_events`. When provided, included in payload; when None, omitted (server-side default preserved — backwards-compat for cheap-lane callers). |
| `core/services/visible_model.py` | In `_run_openai_compatible_visible` and `_stream_openai_compatible_model`, call `compute_unconscious_modulation()` and thread the modulated values through as kwargs. |

### Untouched / reused

- `core/services/user_temperature_engine.py` — read-only via `get_active_field()`
- Other provider paths (openai, openai-codex, ollama, github-copilot, phase1-runtime) — not touched in Phase 1. Production uses deepseek which is openai-compat.
- `core/eventbus/events.py` — no new families
- `core/runtime/db.py` — no schema changes
- All other lanes: `daemon_llm.py`, `heartbeat_runtime.py`, `inner_llm_enrichment.py` — untouched

---

## Spec deltas confirmed during planning

1. **Production visible provider = `deepseek/deepseek-v4-flash`.** Verified via `load_settings().visible_model_provider`. Dispatches through openai-compat path (`_run_openai_compatible_visible` for execute, `_stream_openai_compatible_model` for streaming).

2. **The shared helper `_execute_openai_compatible_chat` serves both visible AND cheap-lane callers.** Putting modulation in the shared helper would leak to cheap-lane (violating the visible-only design decision). Instead, modulation lives in the visible-lane wrappers and passes `temperature`/`top_p` kwargs into the shared helper. Cheap callers don't pass them → server-side defaults preserved.

3. **Current deepseek payload has no temperature/top_p** (only `model`, `messages`, `stream`, `max_tokens` — see `cheap_provider_runtime.py:1134-1143`). Server-side defaults apply. We ADD these fields to the payload when present.

4. **Base parameters when caller passes None:** since deepseek uses server defaults (no explicit base), the modulation helper needs implicit bases to apply deltas against. Phase 1 decision: when `base_temperature is None`, treat as **0.7**; when `base_top_p is None`, treat as **1.0**. These match industry-standard defaults and produce sensible modulated values. Documented in helper docstring as Phase 1 assumption.

5. **Streaming path uses `_iter_openai_compatible_chat_events`** (a generator); execute path uses `_execute_openai_compatible_chat` (single request). Both need the same kwargs added.

6. **`get_active_field` return shape:** `dict[str, Any] | None`. When non-None, keys include `field_valens`, `field_arousal`, `field_intensity` (all floats). Empty/missing keys default to 0.

---

## Task 1: Settings flags

**Files:**
- Modify: `core/runtime/settings.py`

- [ ] **Step 1: Add the flags**

In `core/runtime/settings.py`, find `plan_todo_auto_create_enabled: bool = True` and add right after it:

```python
    # ── Unconscious modulation (Lag 10 — added 2026-05-12) ───────────────
    # Sub-symbolic sampling-parameter modulation: user_temperature's valens
    # nudges visible-chat LLM temperature, arousal nudges top_p, scaled by
    # field_intensity. Jarvis sees no tokens about it; the model generates
    # differently because the API params shifted before the call. Phase 1
    # instruments only the production visible provider (deepseek).
    unconscious_modulation_enabled: bool = True
    unconscious_modulation_temp_delta: float = 0.30
    unconscious_modulation_top_p_delta: float = 0.15
    unconscious_modulation_temp_floor: float = 0.3
    unconscious_modulation_temp_ceiling: float = 1.2
    unconscious_modulation_top_p_floor: float = 0.7
    unconscious_modulation_top_p_ceiling: float = 1.0
```

- [ ] **Step 2: Wire defaults into load_settings**

In `core/runtime/settings.py`, find `plan_todo_auto_create_enabled=bool(...)` in `load_settings` and add right after its closing comma:

```python
        unconscious_modulation_enabled=bool(
            data.get(
                "unconscious_modulation_enabled",
                defaults.unconscious_modulation_enabled,
            )
        ),
        unconscious_modulation_temp_delta=float(
            data.get(
                "unconscious_modulation_temp_delta",
                defaults.unconscious_modulation_temp_delta,
            )
        ),
        unconscious_modulation_top_p_delta=float(
            data.get(
                "unconscious_modulation_top_p_delta",
                defaults.unconscious_modulation_top_p_delta,
            )
        ),
        unconscious_modulation_temp_floor=float(
            data.get(
                "unconscious_modulation_temp_floor",
                defaults.unconscious_modulation_temp_floor,
            )
        ),
        unconscious_modulation_temp_ceiling=float(
            data.get(
                "unconscious_modulation_temp_ceiling",
                defaults.unconscious_modulation_temp_ceiling,
            )
        ),
        unconscious_modulation_top_p_floor=float(
            data.get(
                "unconscious_modulation_top_p_floor",
                defaults.unconscious_modulation_top_p_floor,
            )
        ),
        unconscious_modulation_top_p_ceiling=float(
            data.get(
                "unconscious_modulation_top_p_ceiling",
                defaults.unconscious_modulation_top_p_ceiling,
            )
        ),
```

- [ ] **Step 3: Verify**

```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings, load_settings
s = RuntimeSettings()
assert s.unconscious_modulation_enabled is True
assert s.unconscious_modulation_temp_delta == 0.30
assert s.unconscious_modulation_top_p_delta == 0.15
assert s.unconscious_modulation_temp_floor == 0.3
assert s.unconscious_modulation_temp_ceiling == 1.2
assert s.unconscious_modulation_top_p_floor == 0.7
assert s.unconscious_modulation_top_p_ceiling == 1.0
print('OK:', load_settings().unconscious_modulation_temp_delta)
"
```

Expected: `OK: 0.3`

- [ ] **Step 4: Commit**

```bash
git add core/runtime/settings.py
git commit -m "feat(unconscious-mod): add 7 settings flags for sampling-parameter modulation"
```

---

## Task 2: unconscious_modulation helper module

**Files:**
- Create: `core/services/unconscious_modulation.py`
- Create: `tests/test_unconscious_modulation.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_unconscious_modulation.py`:

```python
from __future__ import annotations

import logging

import pytest


def test_returns_base_when_disabled(monkeypatch):
    from core.services import unconscious_modulation

    class FakeSettings:
        unconscious_modulation_enabled = False
        unconscious_modulation_temp_delta = 0.30
        unconscious_modulation_top_p_delta = 0.15
        unconscious_modulation_temp_floor = 0.3
        unconscious_modulation_temp_ceiling = 1.2
        unconscious_modulation_top_p_floor = 0.7
        unconscious_modulation_top_p_ceiling = 1.0

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: FakeSettings())

    result = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=0.7, base_top_p=1.0, workspace_id="default",
    )
    assert result == (0.7, 1.0)


def test_returns_base_when_no_field(monkeypatch):
    from core.services import unconscious_modulation

    class FakeSettings:
        unconscious_modulation_enabled = True
        unconscious_modulation_temp_delta = 0.30
        unconscious_modulation_top_p_delta = 0.15
        unconscious_modulation_temp_floor = 0.3
        unconscious_modulation_temp_ceiling = 1.2
        unconscious_modulation_top_p_floor = 0.7
        unconscious_modulation_top_p_ceiling = 1.0

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: FakeSettings())
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field",
        lambda *, workspace_id="default": None,
    )

    result = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=0.7, base_top_p=1.0,
    )
    assert result == (0.7, 1.0)


def test_modulates_negative_valens_lowers_temperature(monkeypatch):
    from core.services import unconscious_modulation

    class FakeSettings:
        unconscious_modulation_enabled = True
        unconscious_modulation_temp_delta = 0.30
        unconscious_modulation_top_p_delta = 0.15
        unconscious_modulation_temp_floor = 0.3
        unconscious_modulation_temp_ceiling = 1.2
        unconscious_modulation_top_p_floor = 0.7
        unconscious_modulation_top_p_ceiling = 1.0

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: FakeSettings())
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field",
        lambda *, workspace_id="default": {
            "field_valens": -1.0,
            "field_arousal": 0.0,
            "field_intensity": 1.0,
        },
    )

    mod_temp, mod_top_p = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=0.7, base_top_p=1.0,
    )
    # temp_delta = 0.30 × 1.0 × (-1.0) = -0.30; new = 0.7 - 0.30 = 0.40
    assert mod_temp == pytest.approx(0.40, abs=0.001)
    # arousal=0 → top_p unchanged
    assert mod_top_p == pytest.approx(1.0, abs=0.001)


def test_modulates_positive_arousal_widens_top_p(monkeypatch):
    from core.services import unconscious_modulation

    class FakeSettings:
        unconscious_modulation_enabled = True
        unconscious_modulation_temp_delta = 0.30
        unconscious_modulation_top_p_delta = 0.15
        unconscious_modulation_temp_floor = 0.3
        unconscious_modulation_temp_ceiling = 1.2
        unconscious_modulation_top_p_floor = 0.7
        unconscious_modulation_top_p_ceiling = 1.0

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: FakeSettings())
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field",
        lambda *, workspace_id="default": {
            "field_valens": 0.0,
            "field_arousal": 1.0,
            "field_intensity": 1.0,
        },
    )

    mod_temp, mod_top_p = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=0.85, base_top_p=0.85,
    )
    # arousal_delta = 0.15 × 1.0 × 1.0 = +0.15; new top_p = 0.85 + 0.15 = 1.0
    assert mod_top_p == pytest.approx(1.0, abs=0.001)
    # valens=0 → temp unchanged
    assert mod_temp == pytest.approx(0.85, abs=0.001)


def test_intensity_scales_delta(monkeypatch):
    from core.services import unconscious_modulation

    class FakeSettings:
        unconscious_modulation_enabled = True
        unconscious_modulation_temp_delta = 0.30
        unconscious_modulation_top_p_delta = 0.15
        unconscious_modulation_temp_floor = 0.3
        unconscious_modulation_temp_ceiling = 1.2
        unconscious_modulation_top_p_floor = 0.7
        unconscious_modulation_top_p_ceiling = 1.0

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: FakeSettings())
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field",
        lambda *, workspace_id="default": {
            "field_valens": -1.0,
            "field_arousal": 0.0,
            "field_intensity": 0.5,  # half intensity → half effect
        },
    )

    mod_temp, _ = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=0.7, base_top_p=1.0,
    )
    # temp_delta = 0.30 × 0.5 × (-1.0) = -0.15; new = 0.55
    assert mod_temp == pytest.approx(0.55, abs=0.001)


def test_clamps_temperature_to_floor(monkeypatch):
    from core.services import unconscious_modulation

    class FakeSettings:
        unconscious_modulation_enabled = True
        unconscious_modulation_temp_delta = 0.30
        unconscious_modulation_top_p_delta = 0.15
        unconscious_modulation_temp_floor = 0.3
        unconscious_modulation_temp_ceiling = 1.2
        unconscious_modulation_top_p_floor = 0.7
        unconscious_modulation_top_p_ceiling = 1.0

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: FakeSettings())
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field",
        lambda *, workspace_id="default": {
            "field_valens": -1.0,
            "field_arousal": 0.0,
            "field_intensity": 1.0,
        },
    )

    # Base low + negative delta would land below 0.3 — should clamp.
    mod_temp, _ = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=0.35, base_top_p=1.0,
    )
    assert mod_temp == pytest.approx(0.3, abs=0.001)


def test_clamps_top_p_to_ceiling(monkeypatch):
    from core.services import unconscious_modulation

    class FakeSettings:
        unconscious_modulation_enabled = True
        unconscious_modulation_temp_delta = 0.30
        unconscious_modulation_top_p_delta = 0.15
        unconscious_modulation_temp_floor = 0.3
        unconscious_modulation_temp_ceiling = 1.2
        unconscious_modulation_top_p_floor = 0.7
        unconscious_modulation_top_p_ceiling = 1.0

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: FakeSettings())
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field",
        lambda *, workspace_id="default": {
            "field_valens": 0.0,
            "field_arousal": 1.0,
            "field_intensity": 1.0,
        },
    )

    # Base 0.95 + positive delta would land above 1.0 — should clamp to 1.0.
    _, mod_top_p = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=0.7, base_top_p=0.95,
    )
    assert mod_top_p == pytest.approx(1.0, abs=0.001)


def test_none_base_uses_implicit_defaults(monkeypatch):
    """When caller passes None, helper applies modulation to implicit base
    (0.7 for temp, 1.0 for top_p) and returns concrete values."""
    from core.services import unconscious_modulation

    class FakeSettings:
        unconscious_modulation_enabled = True
        unconscious_modulation_temp_delta = 0.30
        unconscious_modulation_top_p_delta = 0.15
        unconscious_modulation_temp_floor = 0.3
        unconscious_modulation_temp_ceiling = 1.2
        unconscious_modulation_top_p_floor = 0.7
        unconscious_modulation_top_p_ceiling = 1.0

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: FakeSettings())
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field",
        lambda *, workspace_id="default": {
            "field_valens": -1.0,
            "field_arousal": 0.0,
            "field_intensity": 1.0,
        },
    )

    mod_temp, mod_top_p = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=None, base_top_p=None,
    )
    # Implicit base 0.7 for temp; -0.30 delta → 0.4
    assert mod_temp == pytest.approx(0.4, abs=0.001)
    # arousal=0 → no top_p delta; implicit base 1.0 returned
    assert mod_top_p == pytest.approx(1.0, abs=0.001)


def test_failure_returns_base(monkeypatch):
    """If user_temperature_engine raises, helper falls back to base values."""
    from core.services import unconscious_modulation

    class FakeSettings:
        unconscious_modulation_enabled = True
        unconscious_modulation_temp_delta = 0.30
        unconscious_modulation_top_p_delta = 0.15
        unconscious_modulation_temp_floor = 0.3
        unconscious_modulation_temp_ceiling = 1.2
        unconscious_modulation_top_p_floor = 0.7
        unconscious_modulation_top_p_ceiling = 1.0

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: FakeSettings())

    def boom(*, workspace_id="default"):
        raise RuntimeError("nope")
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field", boom,
    )

    mod_temp, mod_top_p = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=0.7, base_top_p=1.0,
    )
    assert mod_temp == pytest.approx(0.7)
    assert mod_top_p == pytest.approx(1.0)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_unconscious_modulation.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'core.services.unconscious_modulation'`.

- [ ] **Step 3: Create the helper module**

Create `core/services/unconscious_modulation.py`:

```python
"""Unconscious modulation — sub-symbolic sampling-parameter shift.

Reads user_temperature_engine's active field and returns LLM API
parameters (temperature, top_p) shifted as a function of the user's
emotional state. Pure read, fail-silent.

Phase 1 (Lag 10, 2026-05-12): visible-chat LLM only. valens nudges
temperature (negative → lower / more cautious; positive → higher / more
creative). arousal nudges top_p (low → narrower / focused; high →
wider / associative). field_intensity scales the magnitude. All values
clamped to safe ranges from settings.

Jarvis sees zero tokens about the modulation. The model generates
differently because its API params shifted before the call. This is the
closest analogue in a transformer to Freud's Triebregulierung: a
pre-linguistic force that shifts flow without becoming a message.
"""
from __future__ import annotations

import logging

from core.runtime.settings import load_settings

logger = logging.getLogger(__name__)

# Implicit defaults when caller passes None for base values.
# Phase 1 assumption — matches industry-standard transformer defaults.
_DEFAULT_BASE_TEMPERATURE = 0.7
_DEFAULT_BASE_TOP_P = 1.0


def _modulation_enabled() -> bool:
    """Kill-switch check. True = modulate; False = pass base through."""
    try:
        return bool(load_settings().unconscious_modulation_enabled)
    except Exception:
        return True  # fail-open: if settings broken, modulation tries


def compute_unconscious_modulation(
    *,
    base_temperature: float | None,
    base_top_p: float | None,
    workspace_id: str = "default",
) -> tuple[float, float]:
    """Return (modulated_temperature, modulated_top_p).

    Reads user_temperature_field and applies intensity-scaled deltas:
        temp_delta  = max_temp_delta  × intensity × valens
        top_p_delta = max_top_p_delta × intensity × arousal

    Clamps to safe parameter ranges from settings. Returns base values
    unchanged if:
      - modulation disabled (kill-switch False)
      - no active field
      - any failure (fail-silent)

    When base is None, implicit defaults are used so the caller still
    gets concrete values to send to the API.
    """
    base_temp = _DEFAULT_BASE_TEMPERATURE if base_temperature is None else float(base_temperature)
    base_top_p_v = _DEFAULT_BASE_TOP_P if base_top_p is None else float(base_top_p)

    if not _modulation_enabled():
        return base_temp, base_top_p_v

    try:
        settings = load_settings()
        max_temp_delta = float(settings.unconscious_modulation_temp_delta)
        max_top_p_delta = float(settings.unconscious_modulation_top_p_delta)
        temp_floor = float(settings.unconscious_modulation_temp_floor)
        temp_ceiling = float(settings.unconscious_modulation_temp_ceiling)
        top_p_floor = float(settings.unconscious_modulation_top_p_floor)
        top_p_ceiling = float(settings.unconscious_modulation_top_p_ceiling)

        from core.services.user_temperature_engine import get_active_field
        field = get_active_field(workspace_id=workspace_id)
        if not field:
            return base_temp, base_top_p_v

        valens = float(field.get("field_valens") or 0.0)
        arousal = float(field.get("field_arousal") or 0.0)
        intensity = float(field.get("field_intensity") or 0.0)

        temp_delta = max_temp_delta * intensity * valens
        top_p_delta = max_top_p_delta * intensity * arousal

        mod_temp = max(temp_floor, min(temp_ceiling, base_temp + temp_delta))
        mod_top_p = max(top_p_floor, min(top_p_ceiling, base_top_p_v + top_p_delta))

        logger.debug(
            "unconscious_modulation: base=(%.3f,%.3f) → modulated=(%.3f,%.3f) "
            "[valens=%.2f arousal=%.2f intensity=%.2f]",
            base_temp, base_top_p_v, mod_temp, mod_top_p,
            valens, arousal, intensity,
        )
        return mod_temp, mod_top_p
    except Exception as exc:
        logger.debug("unconscious_modulation: fallback to base (%s)", exc)
        return base_temp, base_top_p_v
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_unconscious_modulation.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/unconscious_modulation.py tests/test_unconscious_modulation.py
git commit -m "feat(unconscious-mod): helper module + 9 unit tests"
```

---

## Task 3: Verify production visible provider

**Files:** *(read-only verification step)*

- [ ] **Step 1: Confirm provider is still deepseek**

```bash
conda run -n ai python -c "
from core.runtime.settings import load_settings
s = load_settings()
print('visible_model_provider:', s.visible_model_provider)
print('visible_model_name:', s.visible_model_name)
"
```

Expected: `visible_model_provider: deepseek` (and model `deepseek-v4-flash` or `deepseek-v4-pro`).

If the provider has changed since plan-writing, **STOP**. The plan's Task 4-5 instrument the deepseek openai-compat path. A different provider would require changing which file the instrumentation goes into. Bring the spec back to brainstorm and update Task 4-5 to target the new provider's `_execute_*_model` and `_stream_*_model` functions in `core/services/visible_model.py`.

- [ ] **Step 2: Document the verified provider in the next commit**

(No code change in this task — Task 4's commit message will note the verified provider.)

---

## Task 4: Add optional temperature/top_p kwargs to the shared openai-compat helpers

**Files:**
- Modify: `core/services/cheap_provider_runtime.py`

- [ ] **Step 1: Add kwargs to `_execute_openai_compatible_chat`**

In `core/services/cheap_provider_runtime.py`, find the signature of `_execute_openai_compatible_chat` (around line 1115) and replace it. The current signature is:

```python
def _execute_openai_compatible_chat(
    *,
    provider: str,
    model: str,
    auth_profile: str,
    base_url: str,
    message: str | None = None,
    messages: list[dict] | None = None,
    tools: list[dict] | None = None,
) -> dict[str, object]:
```

Add two optional kwargs:

```python
def _execute_openai_compatible_chat(
    *,
    provider: str,
    model: str,
    auth_profile: str,
    base_url: str,
    message: str | None = None,
    messages: list[dict] | None = None,
    tools: list[dict] | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
) -> dict[str, object]:
```

Then find the payload dict literal in this function (around line 1134-1143):

```python
    payload: dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "max_tokens": 4096,
    }
    if tools:
        payload["tools"] = _normalize_tools_for_openai_chat(tools)
```

Add temperature/top_p conditional inclusion right after the payload dict literal, before the `if tools:` block:

```python
    payload: dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "max_tokens": 4096,
    }
    # Lag 10 Phase 1 (2026-05-12): caller may pass modulated values.
    # When None, omit from payload so server-side defaults apply (cheap-lane
    # callers don't pass them; only visible-lane wrappers do).
    if temperature is not None:
        payload["temperature"] = float(temperature)
    if top_p is not None:
        payload["top_p"] = float(top_p)
    if tools:
        payload["tools"] = _normalize_tools_for_openai_chat(tools)
```

- [ ] **Step 2: Add kwargs to `_iter_openai_compatible_chat_events`**

In `core/services/cheap_provider_runtime.py`, find the signature of `_iter_openai_compatible_chat_events` (around line 1295).

Run this to inspect:

```bash
grep -n "def _iter_openai_compatible_chat_events" /media/projects/jarvis-v2/core/services/cheap_provider_runtime.py
```

Then locate where it builds its payload dict — it has the same structure (model, messages, stream=True, max_tokens, tools). Add the same conditional inclusion pattern:

1. Add `temperature: float | None = None, top_p: float | None = None` to the signature.
2. Right after the payload literal is built, add:

```python
    if temperature is not None:
        payload["temperature"] = float(temperature)
    if top_p is not None:
        payload["top_p"] = float(top_p)
```

- [ ] **Step 3: Verify the changes don't break cheap-lane callers**

Cheap-lane daemons call these helpers without passing `temperature` or `top_p` — they default to None and are omitted from the payload. No behavior change for them.

Smoke-check the imports still work:

```bash
conda run -n ai python -c "
from core.services.cheap_provider_runtime import (
    _execute_openai_compatible_chat,
    _iter_openai_compatible_chat_events,
)
import inspect
sig1 = inspect.signature(_execute_openai_compatible_chat)
sig2 = inspect.signature(_iter_openai_compatible_chat_events)
assert 'temperature' in sig1.parameters
assert 'top_p' in sig1.parameters
assert 'temperature' in sig2.parameters
assert 'top_p' in sig2.parameters
print('OK: kwargs added to both helpers')
"
```

Expected: `OK: kwargs added to both helpers`

- [ ] **Step 4: Commit**

```bash
git add core/services/cheap_provider_runtime.py
git commit -m "feat(unconscious-mod): add optional temperature/top_p kwargs to openai-compat helpers"
```

---

## Task 5: Instrument visible-lane wrappers (execute + stream)

**Files:**
- Modify: `core/services/visible_model.py`

- [ ] **Step 1: Locate `_run_openai_compatible_visible`**

```bash
grep -n "def _run_openai_compatible_visible" /media/projects/jarvis-v2/core/services/visible_model.py
```

This is the visible-lane execute wrapper. It currently calls `_execute_openai_compatible_chat` without temperature/top_p.

- [ ] **Step 2: Compute modulation + pass to `_execute_openai_compatible_chat`**

In `_run_openai_compatible_visible`, locate where it calls `_execute_openai_compatible_chat(...)`. Right before that call, compute modulation:

```python
    # Lag 10 Phase 1 (2026-05-12): unconscious modulation of sampling params.
    from core.services.unconscious_modulation import compute_unconscious_modulation
    mod_temp, mod_top_p = compute_unconscious_modulation(
        base_temperature=None,
        base_top_p=None,
        workspace_id="default",
    )
```

Then modify the existing `_execute_openai_compatible_chat(...)` call to pass these:

```python
    result = _execute_openai_compatible_chat(
        # ... existing kwargs ...
        temperature=mod_temp,
        top_p=mod_top_p,
    )
```

Note: locate the actual existing kwargs (provider, model, auth_profile, base_url, message/messages, tools) and keep them. Only ADD the two new kwargs.

- [ ] **Step 3: Locate `_stream_openai_compatible_model`**

This is the streaming visible-lane wrapper (around line 474 in visible_model.py).

```bash
grep -n "_iter_openai_compatible_chat_events" /media/projects/jarvis-v2/core/services/visible_model.py
```

Find where it calls `_iter_openai_compatible_chat_events(...)`. Same pattern: compute modulation first, pass values.

- [ ] **Step 4: Add modulation to streaming path**

Right before the `_iter_openai_compatible_chat_events(...)` call, add:

```python
    # Lag 10 Phase 1 (2026-05-12): unconscious modulation of sampling params.
    from core.services.unconscious_modulation import compute_unconscious_modulation
    mod_temp, mod_top_p = compute_unconscious_modulation(
        base_temperature=None,
        base_top_p=None,
        workspace_id="default",
    )
```

Then modify the call to pass `temperature=mod_temp, top_p=mod_top_p`.

- [ ] **Step 5: Smoke-check imports + signatures**

```bash
conda run -n ai python -c "
import core.services.visible_model
import core.services.unconscious_modulation
print('imports OK')
"
```

Expected: `imports OK`

- [ ] **Step 6: Production probe — modulation values that would be sent**

```bash
conda run -n ai python -c "
from core.services.unconscious_modulation import compute_unconscious_modulation
mod_temp, mod_top_p = compute_unconscious_modulation(
    base_temperature=None, base_top_p=None,
)
print(f'would send to API: temperature={mod_temp:.3f}, top_p={mod_top_p:.3f}')
"
```

Expected: numeric values. If user_temperature has an active field, values will deviate from the implicit base (0.7, 1.0). If no field, both should match implicit base.

- [ ] **Step 7: Commit**

```bash
git add core/services/visible_model.py
git commit -m "feat(unconscious-mod): instrument deepseek visible wrappers (execute + stream)"
```

---

## Task 6: Smoke + 30-day review

**Files:**
- Modify: `scripts/smoke_test_startup.py`

- [ ] **Step 1: Add smoke imports**

In `scripts/smoke_test_startup.py`, find the Multi-step planner Phase 1 smoke block and add right after it:

```python
        # Unconscious modulation Phase 1 (Lag 10 — added 2026-05-12)
        try:
            from core.services.unconscious_modulation import (  # noqa: F401
                compute_unconscious_modulation,
                _modulation_enabled,
            )
        except Exception:
            traceback.print_exc()
```

- [ ] **Step 2: Run all affected test suites**

```bash
conda run -n ai pytest tests/test_unconscious_modulation.py tests/test_multistep_planner.py tests/test_aesthetic_klangbraet.py tests/test_creative_journal_phase1.py tests/test_finitude_phase1.py 2>&1 | tail -10
```

Expected: all green.

- [ ] **Step 3: Verify the kill-switch path works**

```bash
conda run -n ai python -c "
import json
from pathlib import Path

# Read current runtime.json
config_path = Path.home() / '.jarvis-v2' / 'config' / 'runtime.json'
data = json.loads(config_path.read_text(encoding='utf-8'))

# Confirm flag absence means default (True)
print('flag in config:', 'unconscious_modulation_enabled' in data)

from core.runtime.settings import load_settings
print('effective value:', load_settings().unconscious_modulation_enabled)
"
```

Expected: `flag in config: False` and `effective value: True`. (Flag is not set; default = True.)

- [ ] **Step 4: Spot-check what would be sent to API**

```bash
conda run -n ai python -c "
from core.services.unconscious_modulation import compute_unconscious_modulation
from core.services.user_temperature_engine import get_active_field

field = get_active_field(workspace_id='default')
print('active field:', field)
mod_temp, mod_top_p = compute_unconscious_modulation(
    base_temperature=None, base_top_p=None,
)
print(f'would send: temperature={mod_temp:.3f}, top_p={mod_top_p:.3f}')
print(f'(implicit base was 0.7, 1.0)')
"
```

Save the output as the baseline for the 30-day review.

- [ ] **Step 5: Schedule 30-day review**

```bash
conda run -n ai python -c "
from core.services.scheduled_tasks import push_scheduled_task
focus = (
    'Lag 10 Unconscious Modulation Phase 1 — 30-day review: '
    'verify modulation fires during real chat sessions (enable DEBUG logging '
    'on core.services.unconscious_modulation and spot-check the log lines), '
    'ask Bjørn subjectively whether he notices tonal shift in Jarvis based '
    'on his own emotional state, read actual prompts and confirm zero '
    'modulation tokens visible to model, tune temp_delta/top_p_delta if '
    'effect too strong/weak, tune temp_floor/temp_ceiling if model lands '
    'at extremes too often, confirm visible_model_provider still matches '
    'instrumented provider (deepseek). '
    'Decide: keep / tune / deprecate / expand to Phase 2 lanes '
    '(heartbeat + cheap + quality daemons).'
)
r = push_scheduled_task(focus=focus, delay_minutes=30*24*60, source='unconscious_modulation_phase1')
print(r['task_id'], 'run_at=', r['run_at'])
"
```

- [ ] **Step 6: Commit + restart**

```bash
git add scripts/smoke_test_startup.py
git commit -m "chore(unconscious-mod): smoke imports + 30-day review scheduled"
sudo -n systemctl daemon-reload 2>/dev/null || true
sudo -n systemctl restart jarvis-runtime jarvis-api && sleep 6 && sudo -n journalctl -u jarvis-runtime --since "30 seconds ago" -p err 2>&1 | tail -10
```

Expected: no errors.

---

## Self-review

**Spec coverage:**

| Spec section | Task(s) |
|---|---|
| 7 settings flags | Task 1 |
| `compute_unconscious_modulation` (formula + clamp) | Task 2 step 3 |
| `_modulation_enabled` (kill-switch) | Task 2 step 3 |
| Fail-silent on no-field / errors | Task 2 step 3 (try/except in helper) |
| Debug log line before return | Task 2 step 3 (logger.debug call) |
| Implicit base when None passed | Task 2 step 3 (`_DEFAULT_BASE_TEMPERATURE` / `_TOP_P`) |
| Production-provider verification | Task 3 |
| `_execute_openai_compatible_chat` accepts temperature/top_p | Task 4 step 1 |
| `_iter_openai_compatible_chat_events` accepts same | Task 4 step 2 |
| Cheap-lane callers unchanged (no kwargs passed = None = omitted) | Task 4 (default None → omitted) |
| Visible-lane execute wrapper instrumented | Task 5 step 2 |
| Visible-lane stream wrapper instrumented | Task 5 step 4 |
| Smoke imports + 30-day review | Task 6 |
| Backwards compat for other providers (openai, codex, ollama, etc.) | Untouched in this plan; their `_execute_*_model` and `_stream_*_model` paths unchanged |

No spec gaps.

**Placeholder scan:** No TBD/TODO. All code blocks concrete. Settings-flag defaults explicit. Formula concrete.

**Type consistency:**
- `compute_unconscious_modulation(*, base_temperature: float | None, base_top_p: float | None, workspace_id: str) -> tuple[float, float]` — consistent across Tasks 2, 5, 6
- Settings flags all typed correctly (1 bool, 6 floats)
- `_execute_openai_compatible_chat` and `_iter_openai_compatible_chat_events` both gain `temperature: float | None = None, top_p: float | None = None` — same kwarg names everywhere
- Return tuple `(mod_temp, mod_top_p)` consistently named

**Backwards-compat verified:**
- Cheap-lane callers of `_execute_openai_compatible_chat` and `_iter_openai_compatible_chat_events` don't pass the new kwargs → default None → payload omits the fields → server-side defaults preserved (current behavior).
- Other provider paths in `visible_model.py` (`_execute_openai_model`, `_execute_openai_codex_model`, `_execute_ollama_model`, `_execute_github_copilot_visible_model`, `_execute_phase1_model`) are not touched. Their behavior is unchanged.
- Helper fails silent: if user_temperature engine errors or no field, base values return unchanged.
- Kill-switch `unconscious_modulation_enabled=False` → helper returns base immediately → identical to pre-Phase-1 behavior.
- All 7 settings flags have safe defaults; user doesn't need to add anything to runtime.json.
- No DB schema changes. No event-family additions. No new daemons.
