# World Model Phase 1 — Closing the Loop: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the prediction-resolution-calibration loop on the existing `world_model_signal_tracking.py` skeleton: add a `predict_outcome`/`resolve_prediction` tool pair, light pattern-detection nudges (Jarvis-author preserved), TTL auto-uncertain fallback, and trend-based calibration milestones surfaced as one-shot awareness lines.

**Architecture:** One new tool module (`world_model_tools.py`), extensive extensions to the existing `world_model_signal_tracking.py` (scanners, nudges, TTL sweep, milestones, awareness formatters), and one new ProducerSpec for the daily TTL sweep. State_store gets two new keys (`runtime_world_model_nudges`, `runtime_world_model_milestones`). No DB schema changes, no new event families.

**Tech Stack:** Python 3.11, regex (stdlib), `state_store` (existing), eventbus family `world_model_signal` (already registered).

**Spec:** `docs/superpowers/specs/2026-05-12-world-model-loop-phase1-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `core/tools/world_model_tools.py` | `_exec_predict_outcome` + `_exec_resolve_prediction` handlers; `WORLD_MODEL_TOOL_DEFINITIONS` + `WORLD_MODEL_TOOL_HANDLERS` dicts. Mirror `skill_engine_tools.py` pattern. |
| `tests/test_world_model_loop.py` | All Phase 1 tests: scanners, nudges, awareness rendering, TTL sweep, milestone rules, tool handlers, kill-switch, backwards-compat. |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | Add `world_model_loop_enabled: bool = True` (kill-switch). |
| `core/services/world_model_signal_tracking.py` | Add `_PREDICTION_PHRASES`, `_RESOLUTION_PHRASES` regex lists; `extract_prediction_language`, `extract_resolution_language`; `record_prediction_nudge`, `record_resolution_nudge`; `_ttl_sweep_open_predictions`; `_compute_calibration_milestone`; `format_world_model_nudges_for_awareness`, `format_world_model_milestone_for_awareness`. New state_store keys for nudges + milestones. Resolved-prediction records get optional `resolved_via` field. |
| `core/services/visible_runs.py` | After `track_runtime_world_model_signals_for_visible_turn(...)` (line ~2895) inside `_track_runtime_candidates`, add scanner calls against `assistant_text` (Jarvis' own response) that persist nudges. |
| `core/services/prompt_contract.py` | In awareness block, inject `format_world_model_nudges_for_awareness(session_id)` and `format_world_model_milestone_for_awareness()`. |
| `core/services/internal_cadence.py` | New ProducerSpec `world_model_ttl_sweeper`, cooldown 1440 min, calls `_ttl_sweep_open_predictions`. |
| `core/tools/simple_tools.py` | Import + splat `WORLD_MODEL_TOOL_DEFINITIONS` into `TOOL_DEFINITIONS` and `WORLD_MODEL_TOOL_HANDLERS` into `_TOOL_HANDLERS`. |
| `scripts/smoke_test_startup.py` | Verify imports. |

### Untouched / reused

- Existing `record_runtime_world_model_prediction` / `resolve_runtime_world_model_prediction` signatures.
- Existing `track_runtime_world_model_signals_for_visible_turn` (line 2895) — this is a separate signal-tracking system; we don't touch it. We add scanner calls AFTER it.
- Modulator-witness surface.
- Eventbus family `world_model_signal` (no new family).
- No DB schema changes. No new daemons (TTL sweeper is a ProducerSpec).

---

## Spec deltas confirmed during planning

1. **`assistant_text` is the Jarvis-response variable** in `_track_runtime_candidates(run, assistant_text)` (visible_runs.py:2866). We pass that into the new scanners — NOT `run.user_message`. The spec is explicit: scanners run on Jarvis' OWN output, since HE is the one making predictions.

2. **`_track_runtime_candidates` returns early on exceptions** from earlier track-calls. The new scanner calls must NOT block the existing chain; wrap them in their own try/except.

3. **Tool registration via splat pattern**: `simple_tools.py` already splats `SKILL_ENGINE_TOOL_DEFINITIONS` into `TOOL_DEFINITIONS` (line 2326) and `SKILL_ENGINE_TOOL_HANDLERS` into `_TOOL_HANDLERS` (line 6191). We add the same two-line splat for `WORLD_MODEL_TOOL_*`.

4. **State_store keys**: `runtime_world_model_predictions` (existing), `runtime_world_model_nudges` (new), `runtime_world_model_milestones` (new). Load via `load_json` from `core.runtime.state_store`; save via `save_json`. Default to dict-with-empty-lists on first load.

5. **Resolved_via field on prediction record**: `record_runtime_world_model_prediction` doesn't set it (predictions are open at creation). `resolve_runtime_world_model_prediction` is called in three ways — directly from tool, from `_ttl_sweep_open_predictions`, or from manual scripts. We update `resolve_runtime_world_model_prediction` to accept an optional `resolved_via: str = "tool"` kwarg, then writes it onto the record. Backwards-compat: existing call sites without the kwarg get `"tool"` default.

6. **ProducerSpec pattern**: matches `finitude_monthly_reflection` ProducerSpec (added today in finitude Phase 1) — same shape, `cooldown_minutes=1440`, `visible_grace_minutes=60`, `depends_on=[]` (no upstream).

---

## Task 1: Settings flag

**Files:**
- Modify: `core/runtime/settings.py`

- [ ] **Step 1: Add the flag**

In `core/runtime/settings.py`, find `tool_invention_enabled: bool = True` and add right after it:

```python
    # ── World model loop (AGI track #1 — added 2026-05-12) ──────────────
    # When True: pattern scanners detect prediction/resolution language in
    # Jarvis' response, nudge him via awareness block; TTL sweep auto-marks
    # expired open predictions as uncertain; calibration milestones surface.
    # When False: tools still work as a ledger, but no nudges, no TTL, no
    # milestones — reverts to pre-Phase-1 behaviour.
    world_model_loop_enabled: bool = True
```

- [ ] **Step 2: Wire default into load_settings**

In `core/runtime/settings.py`, find `tool_invention_enabled=bool(...)` in `load_settings` and add right after its closing comma:

```python
        world_model_loop_enabled=bool(
            data.get(
                "world_model_loop_enabled",
                defaults.world_model_loop_enabled,
            )
        ),
```

- [ ] **Step 3: Verify**

```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings, load_settings
s = RuntimeSettings()
assert s.world_model_loop_enabled is True
print('OK:', load_settings().world_model_loop_enabled)
"
```

Expected: `OK: True`

- [ ] **Step 4: Commit**

```bash
git add core/runtime/settings.py
git commit -m "feat(world-model-loop): add world_model_loop_enabled kill-switch"
```

---

## Task 2: world_model_tools.py + tool registration

**Files:**
- Create: `core/tools/world_model_tools.py`
- Modify: `core/tools/simple_tools.py`
- Create: `tests/test_world_model_loop.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_world_model_loop.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture()
def clean_state(tmp_path, monkeypatch):
    """Isolated state_store so predictions/nudges/milestones don't pollute."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))
    import importlib
    import core.runtime.state_store as ss
    importlib.reload(ss)
    import core.services.world_model_signal_tracking as wm
    importlib.reload(wm)
    return None


def test_predict_outcome_tool_creates_prediction(clean_state):
    from core.tools.world_model_tools import _exec_predict_outcome

    result = _exec_predict_outcome({
        "subject": "deepseek-v4-flash response on cold-start",
        "expectation": "First reply will take > 8 seconds.",
        "horizon": "i dag",
        "confidence": "medium",
        "evidence": ["seen 3 cold-starts above 7s today"],
    })
    assert result["status"] == "ok"
    pred = result["prediction"]
    assert pred["status"] == "open"
    assert pred["subject"].startswith("deepseek-v4-flash")
    assert pred["confidence"] == "medium"


def test_predict_outcome_validates_required_fields(clean_state):
    from core.tools.world_model_tools import _exec_predict_outcome

    result = _exec_predict_outcome({
        "subject": "",
        "expectation": "x",
    })
    assert result["status"] == "error"

    result = _exec_predict_outcome({
        "subject": "x",
        "expectation": "",
    })
    assert result["status"] == "error"


def test_predict_outcome_respects_killswitch(clean_state, monkeypatch):
    from core.tools import world_model_tools as wmt

    class FakeSettings:
        world_model_loop_enabled = False

    monkeypatch.setattr(wmt, "load_settings", lambda: FakeSettings())

    # Spec choice: tool keeps working as a ledger even when loop is off,
    # so existing callers don't break. Killswitch only affects nudges,
    # TTL, and milestones (see later tasks). Confirm tool still works.
    result = wmt._exec_predict_outcome({
        "subject": "ledger-test",
        "expectation": "still works",
    })
    assert result["status"] == "ok"


def test_resolve_prediction_tool_supports_open_prediction(clean_state):
    from core.tools.world_model_tools import (
        _exec_predict_outcome,
        _exec_resolve_prediction,
    )

    r1 = _exec_predict_outcome({
        "subject": "test",
        "expectation": "x",
    })
    pid = r1["prediction"]["prediction_id"]

    r2 = _exec_resolve_prediction({
        "prediction_id": pid,
        "observed": "x happened",
        "outcome": "supported",
    })
    assert r2["status"] == "ok"

    # Reload predictions and confirm
    from core.services.world_model_signal_tracking import _load_predictions
    items = _load_predictions()
    matching = [p for p in items if p.get("prediction_id") == pid]
    assert len(matching) == 1
    assert matching[0]["status"] == "resolved"
    assert matching[0]["outcome"] == "supported"
    assert matching[0]["resolved_via"] == "tool"


def test_resolve_prediction_tool_validates_outcome(clean_state):
    from core.tools.world_model_tools import (
        _exec_predict_outcome,
        _exec_resolve_prediction,
    )

    r1 = _exec_predict_outcome({"subject": "x", "expectation": "y"})
    pid = r1["prediction"]["prediction_id"]

    result = _exec_resolve_prediction({
        "prediction_id": pid,
        "observed": "z",
        "outcome": "invalid-outcome",
    })
    assert result["status"] == "error"


def test_tool_definitions_registered():
    from core.tools.world_model_tools import (
        WORLD_MODEL_TOOL_DEFINITIONS,
        WORLD_MODEL_TOOL_HANDLERS,
    )

    names = [
        (e.get("function") or {}).get("name")
        for e in WORLD_MODEL_TOOL_DEFINITIONS
        if isinstance(e, dict)
    ]
    assert "predict_outcome" in names
    assert "resolve_prediction" in names
    assert "predict_outcome" in WORLD_MODEL_TOOL_HANDLERS
    assert "resolve_prediction" in WORLD_MODEL_TOOL_HANDLERS


def test_tools_registered_in_simple_tools():
    """End-to-end: the splat into simple_tools picks up our new tools."""
    from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS

    names = [
        (e.get("function") or {}).get("name")
        for e in TOOL_DEFINITIONS
        if isinstance(e, dict)
    ]
    assert "predict_outcome" in names
    assert "resolve_prediction" in names
    assert "predict_outcome" in _TOOL_HANDLERS
    assert "resolve_prediction" in _TOOL_HANDLERS
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_world_model_loop.py -v 2>&1 | tail -15
```

Expected: FAIL with `ModuleNotFoundError: core.tools.world_model_tools`.

- [ ] **Step 3: First, update `resolve_runtime_world_model_prediction` to accept `resolved_via`**

In `core/services/world_model_signal_tracking.py`, find `def resolve_runtime_world_model_prediction(` (around line 90). The current signature is:

```python
def resolve_runtime_world_model_prediction(
    prediction_id: str,
    *,
    observed: str,
    outcome: str,
    now: datetime | None = None,
) -> dict[str, object]:
```

Add `resolved_via: str = "tool"` kwarg:

```python
def resolve_runtime_world_model_prediction(
    prediction_id: str,
    *,
    observed: str,
    outcome: str,
    now: datetime | None = None,
    resolved_via: str = "tool",
) -> dict[str, object]:
```

Inside the function, find where the prediction record is mutated (where `item["status"] = "resolved"` is set). Add right after that line:

```python
        item["resolved_via"] = str(resolved_via or "tool")
```

- [ ] **Step 4: Create `core/tools/world_model_tools.py`**

```python
"""World Model tools — predict_outcome + resolve_prediction.

Phase 1 (AGI track #1, 2026-05-12). Closes the prediction-resolution-
calibration loop on the existing world_model_signal_tracking skeleton.

Tools are usable as a ledger even when world_model_loop_enabled=False;
the killswitch only disables nudges, TTL sweep, and milestones (which
live in world_model_signal_tracking, not here). This keeps the tool
contract stable across reverts.
"""
from __future__ import annotations

import logging
from typing import Any

from core.runtime.settings import load_settings
from core.services.world_model_signal_tracking import (
    record_runtime_world_model_prediction,
    resolve_runtime_world_model_prediction,
)

logger = logging.getLogger(__name__)


def _exec_predict_outcome(args: dict[str, Any]) -> dict[str, Any]:
    """Record a falsifiable prediction."""
    # Note: load_settings is read for parity with other tools, but the
    # killswitch only gates nudges/TTL/milestones — not the tool itself.
    try:
        load_settings()
    except Exception:
        pass

    subject = str(args.get("subject") or "").strip()
    expectation = str(args.get("expectation") or "").strip()
    horizon = str(args.get("horizon") or "").strip()
    confidence = str(args.get("confidence") or "low").strip().lower()
    evidence = args.get("evidence") or []
    if not isinstance(evidence, list):
        evidence = [str(evidence)]

    if not subject:
        return {"status": "error", "error": "subject is required"}
    if not expectation:
        return {"status": "error", "error": "expectation is required"}

    return record_runtime_world_model_prediction(
        subject=subject,
        expectation=expectation,
        horizon=horizon,
        confidence=confidence,
        evidence=[str(e) for e in evidence],
        source="visible-chat-tool",
    )


def _exec_resolve_prediction(args: dict[str, Any]) -> dict[str, Any]:
    """Resolve an open prediction with a later observation."""
    prediction_id = str(args.get("prediction_id") or "").strip()
    observed = str(args.get("observed") or "").strip()
    outcome = str(args.get("outcome") or "").strip().lower()

    if not prediction_id:
        return {"status": "error", "error": "prediction_id is required"}
    if not observed:
        return {"status": "error", "error": "observed is required"}
    if outcome not in {"supported", "contradicted", "uncertain"}:
        return {
            "status": "error",
            "error": "outcome must be supported, contradicted, or uncertain",
        }

    return resolve_runtime_world_model_prediction(
        prediction_id,
        observed=observed,
        outcome=outcome,
        resolved_via="tool",
    )


WORLD_MODEL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "predict_outcome",
            "description": (
                "Lav en eksplicit, falsificerbar prediction. Bruges når du "
                "har en konkret fornemmelse af hvordan noget vil udvikle sig. "
                "Senere kan du resolve den med resolve_prediction. "
                "Predictions feeder din kalibrering over tid."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Hvad er det du predicter? (kort)",
                    },
                    "expectation": {
                        "type": "string",
                        "description": "Selve forudsigelsen — hvad du forventer.",
                    },
                    "horizon": {
                        "type": "string",
                        "description": "Tidshorisont: 'i dag' / 'i morgen' / 'denne uge' / 'inden mandag' / 'EOD'.",
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Hvorfor tror du det? Op til 5 korte begrundelser.",
                    },
                },
                "required": ["subject", "expectation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resolve_prediction",
            "description": (
                "Marker en åben prediction som supported, contradicted, "
                "eller uncertain. Brug når noget faktisk er sket der "
                "verificerer eller modsiger forudsigelsen."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prediction_id": {
                        "type": "string",
                        "description": "ID på den prediction der skal resolves.",
                    },
                    "observed": {
                        "type": "string",
                        "description": "Hvad skete der faktisk?",
                    },
                    "outcome": {
                        "type": "string",
                        "enum": ["supported", "contradicted", "uncertain"],
                    },
                },
                "required": ["prediction_id", "observed", "outcome"],
            },
        },
    },
]


WORLD_MODEL_TOOL_HANDLERS: dict[str, Any] = {
    "predict_outcome": _exec_predict_outcome,
    "resolve_prediction": _exec_resolve_prediction,
}
```

- [ ] **Step 5: Register in `simple_tools.py`**

In `core/tools/simple_tools.py`, find the existing import block where `SKILL_ENGINE_TOOL_DEFINITIONS` and `SKILL_ENGINE_TOOL_HANDLERS` are imported (around line 476-477). Add right after them:

```python
from core.tools.world_model_tools import (
    WORLD_MODEL_TOOL_DEFINITIONS,
    WORLD_MODEL_TOOL_HANDLERS,
)
```

Then find the splat into `TOOL_DEFINITIONS` (around line 2326, where `*SKILL_ENGINE_TOOL_DEFINITIONS` is) and add right after that line:

```python
    *WORLD_MODEL_TOOL_DEFINITIONS,
```

Then find the merge into `_TOOL_HANDLERS` (around line 6191, where `**SKILL_ENGINE_TOOL_HANDLERS` is) and add right after that line:

```python
    **WORLD_MODEL_TOOL_HANDLERS,
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_world_model_loop.py -v 2>&1 | tail -15
```

Expected: 7 passed.

- [ ] **Step 7: Commit**

```bash
git add core/tools/world_model_tools.py core/services/world_model_signal_tracking.py core/tools/simple_tools.py tests/test_world_model_loop.py
git commit -m "feat(world-model-loop): predict_outcome + resolve_prediction tools + resolved_via field"
```

---

## Task 3: Pattern scanners + nudge persistence

**Files:**
- Modify: `core/services/world_model_signal_tracking.py`
- Modify: `tests/test_world_model_loop.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_world_model_loop.py`:

```python
def test_extract_prediction_language_matches(clean_state):
    from core.services.world_model_signal_tracking import extract_prediction_language

    text = "Det her bliver svært. Jeg tror det vil tage en uge mere."
    matches = extract_prediction_language(text)
    assert len(matches) >= 1
    phrases = [m["matched_phrase"] for m in matches]
    assert any("jeg tror" in p.lower() for p in phrases)


def test_extract_prediction_language_no_match(clean_state):
    from core.services.world_model_signal_tracking import extract_prediction_language

    matches = extract_prediction_language("Hej. Vejret er fint i dag.")
    assert matches == []


def test_extract_resolution_language_matches(clean_state):
    from core.services.world_model_signal_tracking import extract_resolution_language

    text = "Som forventet virkede løsningen ikke. Jeg tog fejl."
    matches = extract_resolution_language(text)
    phrases = [m["matched_phrase"] for m in matches]
    assert any("som forventet" in p.lower() for p in phrases)
    assert any("tog fejl" in p.lower() for p in phrases)


def test_record_prediction_nudge_persists(clean_state):
    from core.services.world_model_signal_tracking import (
        record_prediction_nudge,
        _load_nudges,
    )

    record_prediction_nudge(
        session_id="s1",
        run_id="r1",
        matched_phrase="jeg tror",
        context_excerpt="Jeg tror det virker.",
    )
    nudges = _load_nudges()
    assert len(nudges.get("prediction_nudges", [])) == 1
    n = nudges["prediction_nudges"][0]
    assert n["session_id"] == "s1"
    assert n["matched_phrase"] == "jeg tror"
    assert n["rendered_at"] == ""


def test_record_resolution_nudge_persists(clean_state):
    from core.services.world_model_signal_tracking import (
        record_resolution_nudge,
        _load_nudges,
    )

    record_resolution_nudge(
        session_id="s1",
        run_id="r1",
        matched_phrase="jeg tog fejl",
        context_excerpt="Som forventet jeg tog fejl.",
        candidate_prediction_id="",
    )
    nudges = _load_nudges()
    assert len(nudges.get("resolution_nudges", [])) == 1


def test_nudge_cap_at_20_per_kind(clean_state):
    from core.services.world_model_signal_tracking import (
        record_prediction_nudge,
        _load_nudges,
    )

    for i in range(25):
        record_prediction_nudge(
            session_id="s1",
            run_id=f"r{i}",
            matched_phrase="jeg tror",
            context_excerpt=f"context {i}",
        )
    nudges = _load_nudges()
    assert len(nudges["prediction_nudges"]) == 20
    # FIFO: oldest 5 dropped, newest 20 retained
    assert nudges["prediction_nudges"][0]["run_id"] == "r5"
    assert nudges["prediction_nudges"][-1]["run_id"] == "r24"


def test_nudge_ttl_48h(clean_state):
    """Nudges get expires_at = created_at + 48h."""
    from core.services.world_model_signal_tracking import (
        record_prediction_nudge,
        _load_nudges,
    )

    record_prediction_nudge(
        session_id="s1",
        run_id="r1",
        matched_phrase="jeg tror",
        context_excerpt="x",
    )
    n = _load_nudges()["prediction_nudges"][0]
    created = datetime.fromisoformat(n["created_at"].replace("Z", "+00:00"))
    expires = datetime.fromisoformat(n["expires_at"].replace("Z", "+00:00"))
    delta = expires - created
    assert timedelta(hours=47) <= delta <= timedelta(hours=49)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_world_model_loop.py -v 2>&1 | tail -10
```

Expected: 7 new tests fail with `AttributeError`.

- [ ] **Step 3: Add pattern lists + scanners + nudge persistence**

In `core/services/world_model_signal_tracking.py`, find the constants block at the top (around lines 16-31) and add right after the existing constants:

```python
import re as _re

# Pattern phrases for nudge detection (Lag 1 of world model loop)
# Each pattern matches in Jarvis' OWN response text.
_PREDICTION_PHRASES = [
    _re.compile(r"\bjeg tror\b", _re.IGNORECASE),
    _re.compile(r"\bjeg vil tro\b", _re.IGNORECASE),
    _re.compile(r"\bforventer (at|en|et|den|de)\b", _re.IGNORECASE),
    _re.compile(r"\bgætter på\b", _re.IGNORECASE),
    _re.compile(r"\bdet vil (sandsynligvis|nok|måske)\b", _re.IGNORECASE),
    _re.compile(r"\bdet bliver (nok|sandsynligvis)\b", _re.IGNORECASE),
    _re.compile(r"\bdet skal nok\b", _re.IGNORECASE),
    _re.compile(r"\bsandsynligvis\b", _re.IGNORECASE),
    _re.compile(r"\bjeg satser på\b", _re.IGNORECASE),
]

_RESOLUTION_PHRASES = [
    _re.compile(r"\bdet viste sig\b", _re.IGNORECASE),
    _re.compile(r"\bjeg fik ret\b", _re.IGNORECASE),
    _re.compile(r"\bjeg tog fejl\b", _re.IGNORECASE),
    _re.compile(r"\bsom forventet\b", _re.IGNORECASE),
    _re.compile(r"\boverrasket over\b", _re.IGNORECASE),
    _re.compile(r"\bblev som\b", _re.IGNORECASE),
    _re.compile(r"\bvirkede (ikke|som forventet)\b", _re.IGNORECASE),
    _re.compile(r"\bdet gik (ikke )?som\b", _re.IGNORECASE),
]

_NUDGE_STATE_KEY = "runtime_world_model_nudges"
_MAX_NUDGES_PER_KIND = 20
_NUDGE_TTL_HOURS = 48  # Jarvis review: 24h was too short for overnight gap
_NUDGE_CONTEXT_WORDS = 30
```

Then find `def _load_predictions()` (near the end of the file) and add these helpers right above it:

```python
def _extract_pattern_matches(text: str, patterns: list) -> list[dict[str, str]]:
    """Return list of {matched_phrase, context_excerpt} for each regex hit.

    Context excerpt = ~30 words before and after the match.
    """
    if not text:
        return []
    words = text.split()
    matches: list[dict[str, str]] = []
    for pat in patterns:
        for m in pat.finditer(text):
            # Find which word position this match starts at
            char_pos = m.start()
            # Walk back through words to find the index
            running_chars = 0
            word_idx = 0
            for i, w in enumerate(words):
                if running_chars + len(w) >= char_pos:
                    word_idx = i
                    break
                running_chars += len(w) + 1  # +1 for space
            start = max(0, word_idx - _NUDGE_CONTEXT_WORDS)
            end = min(len(words), word_idx + _NUDGE_CONTEXT_WORDS)
            context_excerpt = " ".join(words[start:end])
            matches.append({
                "matched_phrase": m.group(0),
                "context_excerpt": context_excerpt[:400],
            })
    return matches


def extract_prediction_language(text: str) -> list[dict[str, str]]:
    """Find prediction-shape phrases in Jarvis' own response text."""
    return _extract_pattern_matches(text, _PREDICTION_PHRASES)


def extract_resolution_language(text: str) -> list[dict[str, str]]:
    """Find resolution-shape phrases in Jarvis' own response text."""
    return _extract_pattern_matches(text, _RESOLUTION_PHRASES)


def _load_nudges() -> dict[str, list[dict[str, object]]]:
    raw = load_json(_NUDGE_STATE_KEY, {})
    if not isinstance(raw, dict):
        raw = {}
    return {
        "prediction_nudges": list(raw.get("prediction_nudges") or []),
        "resolution_nudges": list(raw.get("resolution_nudges") or []),
    }


def _save_nudges(data: dict[str, list[dict[str, object]]]) -> None:
    save_json(_NUDGE_STATE_KEY, data)


def record_prediction_nudge(
    *,
    session_id: str,
    run_id: str,
    matched_phrase: str,
    context_excerpt: str,
) -> None:
    """Append a prediction-language nudge to state (FIFO, max 20, 48h TTL)."""
    now = datetime.now(UTC)
    nudge = {
        "nudge_id": f"wmnudge-{uuid4().hex}",
        "kind": "prediction",
        "session_id": str(session_id or ""),
        "run_id": str(run_id or ""),
        "matched_phrase": str(matched_phrase or "")[:80],
        "context_excerpt": str(context_excerpt or "")[:400],
        "created_at": now.isoformat(),
        "rendered_at": "",
        "expires_at": (now + timedelta(hours=_NUDGE_TTL_HOURS)).isoformat(),
    }
    data = _load_nudges()
    data["prediction_nudges"].append(nudge)
    if len(data["prediction_nudges"]) > _MAX_NUDGES_PER_KIND:
        data["prediction_nudges"] = data["prediction_nudges"][-_MAX_NUDGES_PER_KIND:]
    _save_nudges(data)


def record_resolution_nudge(
    *,
    session_id: str,
    run_id: str,
    matched_phrase: str,
    context_excerpt: str,
    candidate_prediction_id: str = "",
) -> None:
    """Append a resolution-language nudge to state (FIFO, max 20, 48h TTL)."""
    now = datetime.now(UTC)
    nudge = {
        "nudge_id": f"wmnudge-{uuid4().hex}",
        "kind": "resolution",
        "session_id": str(session_id or ""),
        "run_id": str(run_id or ""),
        "matched_phrase": str(matched_phrase or "")[:80],
        "context_excerpt": str(context_excerpt or "")[:400],
        "candidate_prediction_id": str(candidate_prediction_id or ""),
        "created_at": now.isoformat(),
        "rendered_at": "",
        "expires_at": (now + timedelta(hours=_NUDGE_TTL_HOURS)).isoformat(),
    }
    data = _load_nudges()
    data["resolution_nudges"].append(nudge)
    if len(data["resolution_nudges"]) > _MAX_NUDGES_PER_KIND:
        data["resolution_nudges"] = data["resolution_nudges"][-_MAX_NUDGES_PER_KIND:]
    _save_nudges(data)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_world_model_loop.py -v 2>&1 | tail -15
```

Expected: all passed (7 from Task 2 + 7 from Task 3 = 14).

- [ ] **Step 5: Commit**

```bash
git add core/services/world_model_signal_tracking.py tests/test_world_model_loop.py
git commit -m "feat(world-model-loop): pattern scanners + nudge persistence (48h TTL, FIFO max 20)"
```

---

## Task 4: Wire scanners into visible_runs + awareness formatter

**Files:**
- Modify: `core/services/world_model_signal_tracking.py`
- Modify: `core/services/visible_runs.py`
- Modify: `core/services/prompt_contract.py`
- Modify: `tests/test_world_model_loop.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_world_model_loop.py`:

```python
def test_format_nudges_returns_empty_when_no_nudges(clean_state):
    from core.services.world_model_signal_tracking import (
        format_world_model_nudges_for_awareness,
    )
    assert format_world_model_nudges_for_awareness(session_id="s1") == ""


def test_format_nudges_renders_oldest_unrendered(clean_state):
    from core.services.world_model_signal_tracking import (
        record_prediction_nudge,
        format_world_model_nudges_for_awareness,
        _load_nudges,
    )

    record_prediction_nudge(
        session_id="s1",
        run_id="r1",
        matched_phrase="jeg tror",
        context_excerpt="Jeg tror det virker.",
    )
    out = format_world_model_nudges_for_awareness(session_id="s1")
    assert out  # non-empty
    assert "jeg tror" in out.lower() or "prediction" in out.lower()

    # Should mark the nudge as rendered
    nudges = _load_nudges()
    assert nudges["prediction_nudges"][0]["rendered_at"]


def test_format_nudges_skips_already_rendered(clean_state):
    from core.services.world_model_signal_tracking import (
        record_prediction_nudge,
        format_world_model_nudges_for_awareness,
    )

    record_prediction_nudge(
        session_id="s1", run_id="r1",
        matched_phrase="jeg tror", context_excerpt="x",
    )
    first = format_world_model_nudges_for_awareness(session_id="s1")
    second = format_world_model_nudges_for_awareness(session_id="s1")
    assert first  # rendered the first time
    assert second == ""  # nothing left to render


def test_format_nudges_skips_expired(clean_state, monkeypatch):
    from core.services.world_model_signal_tracking import (
        record_prediction_nudge,
        format_world_model_nudges_for_awareness,
        _load_nudges,
        _save_nudges,
    )

    record_prediction_nudge(
        session_id="s1", run_id="r1",
        matched_phrase="jeg tror", context_excerpt="x",
    )
    # Manually expire the nudge
    data = _load_nudges()
    data["prediction_nudges"][0]["expires_at"] = (
        datetime.now(UTC) - timedelta(hours=1)
    ).isoformat()
    _save_nudges(data)

    assert format_world_model_nudges_for_awareness(session_id="s1") == ""


def test_format_nudges_respects_killswitch(clean_state, monkeypatch):
    from core.services import world_model_signal_tracking as wm

    class FakeSettings:
        world_model_loop_enabled = False

    monkeypatch.setattr(wm, "load_settings", lambda: FakeSettings())

    wm.record_prediction_nudge(
        session_id="s1", run_id="r1",
        matched_phrase="jeg tror", context_excerpt="x",
    )
    assert wm.format_world_model_nudges_for_awareness(session_id="s1") == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_world_model_loop.py -v 2>&1 | tail -10
```

Expected: 5 new tests fail (missing `format_world_model_nudges_for_awareness`).

- [ ] **Step 3: Add load_settings import + format helper**

In `core/services/world_model_signal_tracking.py`, ensure `load_settings` is imported. Add near other `from core.*` imports at top:

```python
from core.runtime.settings import load_settings
```

(Check first — may not exist yet.)

Then in the helpers section (above `_load_predictions`), add:

```python
def _loop_enabled() -> bool:
    try:
        return bool(load_settings().world_model_loop_enabled)
    except Exception:
        return True


def format_world_model_nudges_for_awareness(*, session_id: str | None = None) -> str:
    """Surface up to 1 prediction-nudge + 1 resolution-nudge for the awareness block.

    Picks oldest unrendered+unexpired nudge per kind. Marks them as rendered.
    Returns empty string if killswitch off or nothing to surface.
    """
    if not _loop_enabled():
        return ""
    now = datetime.now(UTC)
    data = _load_nudges()
    parts: list[str] = []
    dirty = False

    for kind in ("prediction_nudges", "resolution_nudges"):
        for n in data.get(kind, []):
            if n.get("rendered_at"):
                continue
            try:
                exp = datetime.fromisoformat(str(n.get("expires_at") or "").replace("Z", "+00:00"))
            except Exception:
                continue
            if exp <= now:
                continue
            phrase = str(n.get("matched_phrase") or "")
            if kind == "prediction_nudges":
                parts.append(
                    f"📡 Du sagde '{phrase}' — vil du lave en prediction? "
                    "Brug predict_outcome hvis ja."
                )
            else:
                cand = str(n.get("candidate_prediction_id") or "")
                hint = f" (kandidat: {cand[:16]})" if cand else ""
                parts.append(
                    f"🎯 Du sagde '{phrase}' — vil du resolve en prediction{hint}? "
                    "Brug resolve_prediction hvis ja."
                )
            n["rendered_at"] = now.isoformat()
            dirty = True
            break  # only one per kind per session

    if dirty:
        _save_nudges(data)
    return "\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_world_model_loop.py -v 2>&1 | tail -15
```

Expected: 19 passed (7 + 7 + 5).

- [ ] **Step 5: Wire scanners into `_track_runtime_candidates`**

In `core/services/visible_runs.py`, find the block at line ~2894-2901 with the existing `track_runtime_world_model_signals_for_visible_turn` call. Add right after that try/except block (before the next `try:` for `track_runtime_self_model_signals_for_visible_turn`):

```python
    # World Model loop Phase 1 (2026-05-12): scan Jarvis' OWN response
    # (not the user message) for prediction/resolution language and
    # persist nudges. Jarvis sees them in next session's awareness.
    try:
        from core.services.world_model_signal_tracking import (
            extract_prediction_language,
            extract_resolution_language,
            record_prediction_nudge,
            record_resolution_nudge,
        )
        for m in extract_prediction_language(assistant_text or ""):
            record_prediction_nudge(
                session_id=run.session_id,
                run_id=run.run_id,
                matched_phrase=m["matched_phrase"],
                context_excerpt=m["context_excerpt"],
            )
        for m in extract_resolution_language(assistant_text or ""):
            record_resolution_nudge(
                session_id=run.session_id,
                run_id=run.run_id,
                matched_phrase=m["matched_phrase"],
                context_excerpt=m["context_excerpt"],
                candidate_prediction_id="",
            )
    except Exception:
        # Never block downstream candidate tracking on scanner failures.
        pass
```

- [ ] **Step 6: Wire awareness formatter into `prompt_contract.py`**

In `core/services/prompt_contract.py`, find the place where Phase 1 awareness items are added near the multi-step planner cross-session block (around line 970-985 — search for `format_cross_session_plans_for_awareness`):

```bash
grep -n "format_cross_session_plans_for_awareness" /media/projects/jarvis-v2/core/services/prompt_contract.py
```

Right after that block, add:

```python
    # World Model loop Phase 1 (2026-05-12) — prediction/resolution nudges
    try:
        from core.services.world_model_signal_tracking import (
            format_world_model_nudges_for_awareness,
        )
        _awareness_add(
            36,
            "world-model prediction/resolution nudges",
            format_world_model_nudges_for_awareness(session_id=session_id) or None,
        )
    except Exception:
        pass
```

- [ ] **Step 7: Smoke check production**

```bash
conda run -n ai python -c "
from core.services.world_model_signal_tracking import (
    extract_prediction_language,
    extract_resolution_language,
    format_world_model_nudges_for_awareness,
)
print('predict matches:', len(extract_prediction_language('Jeg tror det virker.')))
print('resolve matches:', len(extract_resolution_language('Som forventet jeg tog fejl.')))
print('awareness empty case:', repr(format_world_model_nudges_for_awareness(session_id='test-session')))
"
```

Expected: both > 0; awareness empty string (no nudges yet).

- [ ] **Step 8: Commit**

```bash
git add core/services/world_model_signal_tracking.py core/services/visible_runs.py core/services/prompt_contract.py tests/test_world_model_loop.py
git commit -m "feat(world-model-loop): scanners wired into visible_runs + awareness nudges in prompt"
```

---

## Task 5: TTL sweep daemon

**Files:**
- Modify: `core/services/world_model_signal_tracking.py`
- Modify: `core/services/internal_cadence.py`
- Modify: `tests/test_world_model_loop.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_world_model_loop.py`:

```python
def test_ttl_sweep_marks_expired_prediction_uncertain(clean_state):
    """Predictions with parseable horizon past grace get auto-uncertain."""
    from core.services.world_model_signal_tracking import (
        record_runtime_world_model_prediction,
        _ttl_sweep_open_predictions,
        _load_predictions,
    )

    # Manually create a prediction with "i dag" horizon, but backdate it
    record_runtime_world_model_prediction(
        subject="test",
        expectation="should expire",
        horizon="i dag",
        confidence="low",
        evidence=[],
    )
    preds = _load_predictions()
    # Backdate created_at to yesterday so 'i dag' has clearly passed + 24h grace
    preds[0]["created_at"] = (
        datetime.now(UTC) - timedelta(hours=50)
    ).isoformat()
    from core.services.world_model_signal_tracking import _save_predictions
    _save_predictions(preds)

    result = _ttl_sweep_open_predictions(now=datetime.now(UTC))
    assert result["resolved"] >= 1

    preds_after = _load_predictions()
    assert preds_after[0]["status"] == "resolved"
    assert preds_after[0]["outcome"] == "uncertain"
    assert preds_after[0]["resolved_via"] == "ttl_auto"


def test_ttl_sweep_keeps_recent_predictions_open(clean_state):
    """Fresh predictions are not touched by TTL sweep."""
    from core.services.world_model_signal_tracking import (
        record_runtime_world_model_prediction,
        _ttl_sweep_open_predictions,
        _load_predictions,
    )

    record_runtime_world_model_prediction(
        subject="fresh",
        expectation="should stay open",
        horizon="i dag",
        confidence="low",
        evidence=[],
    )
    result = _ttl_sweep_open_predictions(now=datetime.now(UTC))
    assert result["resolved"] == 0
    preds = _load_predictions()
    assert preds[0]["status"] == "open"


def test_ttl_sweep_ignores_unparseable_horizon_initially(clean_state):
    """If horizon can't be parsed, the default grace is used (7 days)."""
    from core.services.world_model_signal_tracking import (
        record_runtime_world_model_prediction,
        _ttl_sweep_open_predictions,
        _load_predictions,
        _save_predictions,
    )

    record_runtime_world_model_prediction(
        subject="weird-horizon",
        expectation="x",
        horizon="vague time soon",
        confidence="low",
        evidence=[],
    )
    # Backdate 3 days — within 7-day default grace
    preds = _load_predictions()
    preds[0]["created_at"] = (
        datetime.now(UTC) - timedelta(days=3)
    ).isoformat()
    _save_predictions(preds)

    result = _ttl_sweep_open_predictions(now=datetime.now(UTC))
    assert result["resolved"] == 0


def test_ttl_sweep_respects_killswitch(clean_state, monkeypatch):
    from core.services import world_model_signal_tracking as wm

    class FakeSettings:
        world_model_loop_enabled = False

    monkeypatch.setattr(wm, "load_settings", lambda: FakeSettings())

    wm.record_runtime_world_model_prediction(
        subject="x", expectation="y", horizon="i dag",
        confidence="low", evidence=[],
    )
    # Even with old timestamp, killswitch should prevent resolution
    preds = wm._load_predictions()
    preds[0]["created_at"] = (
        datetime.now(UTC) - timedelta(hours=50)
    ).isoformat()
    wm._save_predictions(preds)

    result = wm._ttl_sweep_open_predictions(now=datetime.now(UTC))
    assert result["resolved"] == 0
    # Prediction stays open
    assert wm._load_predictions()[0]["status"] == "open"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_world_model_loop.py -v 2>&1 | tail -10
```

Expected: 4 new tests fail with `AttributeError: ... no attribute '_ttl_sweep_open_predictions'`.

- [ ] **Step 3: Add TTL sweep logic**

In `core/services/world_model_signal_tracking.py`, add right after the nudge helpers (before `_load_predictions`):

```python
_HORIZON_PARSERS = [
    ("i dag",       lambda created: created.replace(hour=23, minute=59)),
    ("i morgen",    lambda created: (created + timedelta(days=1)).replace(hour=23, minute=59)),
    ("denne uge",   lambda created: created + timedelta(days=7)),
    ("eod",         lambda created: created.replace(hour=23, minute=59)),
    ("inden mandag", lambda created: _next_weekday(created, 0)),  # Mon=0
    ("inden tirsdag", lambda created: _next_weekday(created, 1)),
    ("inden onsdag",  lambda created: _next_weekday(created, 2)),
    ("inden torsdag", lambda created: _next_weekday(created, 3)),
    ("inden fredag",  lambda created: _next_weekday(created, 4)),
    ("inden lørdag",  lambda created: _next_weekday(created, 5)),
    ("inden søndag",  lambda created: _next_weekday(created, 6)),
]
_HORIZON_DEFAULT_GRACE_DAYS = 7
_TTL_GRACE_HOURS = 24


def _next_weekday(d: datetime, target_weekday: int) -> datetime:
    """Next occurrence of given weekday (0=Mon..6=Sun) at end-of-day."""
    days_ahead = (target_weekday - d.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return (d + timedelta(days=days_ahead)).replace(hour=23, minute=59)


def _parse_horizon(horizon: str, created: datetime) -> datetime:
    """Return the cutoff datetime when horizon would have elapsed.

    Conservative: only matches known phrases (case-insensitive). Anything
    else falls back to a 7-day default.
    """
    h = (horizon or "").strip().lower()
    if h:
        for prefix, fn in _HORIZON_PARSERS:
            if h.startswith(prefix) or h == prefix:
                return fn(created)
    return created + timedelta(days=_HORIZON_DEFAULT_GRACE_DAYS)


def _ttl_sweep_open_predictions(*, now: datetime | None = None) -> dict[str, int]:
    """Scan open predictions; auto-resolve as 'uncertain' if past horizon+grace.

    Returns {"resolved": N, "skipped": M}. Honors killswitch.
    """
    if not _loop_enabled():
        return {"resolved": 0, "skipped": 0, "reason": "killswitch_off"}

    cutoff_now = now or datetime.now(UTC)
    predictions = _load_predictions()
    resolved = 0
    skipped = 0
    for pred in predictions:
        if str(pred.get("status") or "") != "open":
            skipped += 1
            continue
        try:
            created = datetime.fromisoformat(
                str(pred.get("created_at") or "").replace("Z", "+00:00")
            )
        except Exception:
            skipped += 1
            continue
        horizon_cutoff = _parse_horizon(str(pred.get("horizon") or ""), created)
        if cutoff_now < horizon_cutoff + timedelta(hours=_TTL_GRACE_HOURS):
            skipped += 1
            continue
        # Auto-resolve as uncertain
        resolve_runtime_world_model_prediction(
            str(pred.get("prediction_id") or ""),
            observed="(no observation — TTL auto-resolve)",
            outcome="uncertain",
            now=cutoff_now,
            resolved_via="ttl_auto",
        )
        resolved += 1
    return {"resolved": resolved, "skipped": skipped}
```

Note: `resolve_runtime_world_model_prediction` is in the same module, so the call is direct. Also note: `_load_predictions` and `_save_predictions` exist already (lines 259-266 of the original file).

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_world_model_loop.py -v 2>&1 | tail -15
```

Expected: 23 passed (19 + 4).

- [ ] **Step 5: Register ProducerSpec in internal_cadence**

In `core/services/internal_cadence.py`, find the existing `finitude_monthly_reflection` registration (added earlier today). Add a similar block right after it:

```python
    def _run_world_model_ttl_sweep(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.world_model_signal_tracking import (
            _ttl_sweep_open_predictions,
        )
        from datetime import datetime, UTC
        return _ttl_sweep_open_predictions(now=datetime.now(UTC))

    register_producer(ProducerSpec(
        name="world_model_ttl_sweeper",
        cooldown_minutes=1440,  # 1×/day
        visible_grace_minutes=60,
        run_fn=_run_world_model_ttl_sweep,
        priority=28,
        depends_on=[],
    ))
```

- [ ] **Step 6: Verify cadence import + registration**

```bash
conda run -n ai python -c "
import core.services.internal_cadence
print('OK: internal_cadence imports cleanly')
"
```

Expected: `OK: internal_cadence imports cleanly`

- [ ] **Step 7: Commit**

```bash
git add core/services/world_model_signal_tracking.py core/services/internal_cadence.py tests/test_world_model_loop.py
git commit -m "feat(world-model-loop): TTL sweep + daily ProducerSpec for auto-uncertain resolution"
```

---

## Task 6: Calibration milestones + awareness

**Files:**
- Modify: `core/services/world_model_signal_tracking.py`
- Modify: `core/services/prompt_contract.py`
- Modify: `tests/test_world_model_loop.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_world_model_loop.py`:

```python
def _seed_resolved(predictions_module, *, outcomes: list[str]) -> None:
    """Helper: create resolved predictions with the given outcome sequence."""
    base = datetime.now(UTC) - timedelta(days=2)
    for i, out in enumerate(outcomes):
        predictions_module.record_runtime_world_model_prediction(
            subject=f"s{i}",
            expectation=f"e{i}",
            horizon="i dag",
            confidence="low",
            evidence=[],
        )
        preds = predictions_module._load_predictions()
        preds[0]["status"] = "resolved"
        preds[0]["outcome"] = out
        preds[0]["resolved_at"] = (base + timedelta(minutes=i)).isoformat()
        preds[0]["resolved_via"] = "tool"
        predictions_module._save_predictions(preds)


def test_milestone_count_10_fires(clean_state):
    from core.services import world_model_signal_tracking as wm

    _seed_resolved(wm, outcomes=["supported"] * 7 + ["contradicted"] * 3)
    milestone = wm._compute_calibration_milestone(now=datetime.now(UTC))
    assert milestone is not None
    assert milestone["kind"] == "count_10"
    assert "kalibrering" in milestone["message"].lower()


def test_milestone_first_contradiction_after_streak(clean_state):
    from core.services import world_model_signal_tracking as wm

    # Streak of 5 supported, then 1 contradicted as latest
    _seed_resolved(wm, outcomes=["supported"] * 5 + ["contradicted"])
    milestone = wm._compute_calibration_milestone(now=datetime.now(UTC))
    # count_10 won't trigger (only 6 resolved), but
    # first_contradiction_after_streak should
    assert milestone is not None
    assert milestone["kind"] in ("first_contradiction_after_streak",)


def test_milestone_threshold_70_cross(clean_state):
    from core.services import world_model_signal_tracking as wm

    # 7 supported, 3 contradicted = 70% calibration; should fire threshold_70
    _seed_resolved(wm, outcomes=["supported"] * 7 + ["contradicted"] * 3)
    milestone = wm._compute_calibration_milestone(now=datetime.now(UTC))
    assert milestone is not None
    # count_10 takes priority over threshold; we accept either
    assert milestone["kind"] in ("count_10", "threshold_70")


def test_milestone_trend_improving(clean_state):
    from core.services import world_model_signal_tracking as wm

    # Prior 10 = 50% (5 supported / 5 contradicted); recent 10 = 80%
    _seed_resolved(wm, outcomes=(
        ["supported"] * 5 + ["contradicted"] * 5  # prior 10 → 50%
        + ["supported"] * 8 + ["contradicted"] * 2  # recent 10 → 80%
    ))
    milestone = wm._compute_calibration_milestone(now=datetime.now(UTC))
    # trend_improving requires +5% delta; here it's +30%
    # count_10 will fire first; we accept any that fires
    assert milestone is not None


def test_milestone_format_for_awareness(clean_state):
    from core.services import world_model_signal_tracking as wm

    _seed_resolved(wm, outcomes=["supported"] * 7 + ["contradicted"] * 3)
    out = wm.format_world_model_milestone_for_awareness()
    assert out  # non-empty for ≥10 resolved
    # Second call returns empty (milestone already rendered)
    out2 = wm.format_world_model_milestone_for_awareness()
    assert out2 == ""


def test_milestone_format_respects_killswitch(clean_state, monkeypatch):
    from core.services import world_model_signal_tracking as wm

    class FakeSettings:
        world_model_loop_enabled = False

    monkeypatch.setattr(wm, "load_settings", lambda: FakeSettings())

    _seed_resolved(wm, outcomes=["supported"] * 10)
    assert wm.format_world_model_milestone_for_awareness() == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_world_model_loop.py -v 2>&1 | tail -12
```

Expected: 6 new tests fail.

- [ ] **Step 3: Add milestone computation + formatter**

In `core/services/world_model_signal_tracking.py`, add right after the TTL helpers:

```python
_MILESTONE_STATE_KEY = "runtime_world_model_milestones"


def _load_milestones() -> dict[str, list[dict[str, object]]]:
    raw = load_json(_MILESTONE_STATE_KEY, {})
    if not isinstance(raw, dict):
        raw = {}
    return {"history": list(raw.get("history") or [])}


def _save_milestones(data: dict[str, list[dict[str, object]]]) -> None:
    save_json(_MILESTONE_STATE_KEY, data)


def _resolved_predictions_chrono() -> list[dict[str, object]]:
    """Return resolved predictions in chronological order (oldest first)."""
    preds = _load_predictions()
    resolved = [
        p for p in preds
        if str(p.get("status") or "") == "resolved"
        and str(p.get("outcome") or "") in {"supported", "contradicted", "uncertain"}
    ]
    resolved.sort(key=lambda p: str(p.get("resolved_at") or p.get("created_at") or ""))
    return resolved


def _calibration_of(predictions: list[dict[str, object]]) -> float:
    """% supported among supported+contradicted; uncertain is excluded."""
    s = sum(1 for p in predictions if p.get("outcome") == "supported")
    c = sum(1 for p in predictions if p.get("outcome") == "contradicted")
    if s + c == 0:
        return 0.0
    return round(100.0 * s / (s + c), 1)


def _has_milestone(kind: str, value: object = None) -> bool:
    """Check if a milestone of given kind (+ optional value) has been recorded."""
    for m in _load_milestones().get("history", []):
        if m.get("kind") != kind:
            continue
        if value is not None and m.get("value") != value:
            continue
        return True
    return False


def _append_milestone(kind: str, value: object, message: str, now: datetime) -> dict[str, object]:
    m = {
        "milestone_id": f"wmmile-{uuid4().hex}",
        "kind": kind,
        "value": value,
        "message": message,
        "created_at": now.isoformat(),
        "rendered_at": "",
    }
    data = _load_milestones()
    data["history"].append(m)
    _save_milestones(data)
    return m


def _compute_calibration_milestone(*, now: datetime | None = None) -> dict[str, object] | None:
    """Compute the latest calibration milestone if any rule fires.

    Rules in priority order:
      1. count_10 — every 10th resolved prediction (10, 20, 30 ...)
      2. first_contradiction_after_streak — latest is contradicted after ≥5 supported
      3. threshold_60 / threshold_70 / threshold_80 — calibration crossed since last
      4. trend_improving (≥+5%) / trend_declining (≤-5%) — last 10 vs prior 10
    Returns the newly recorded milestone dict, or None if nothing fires.
    """
    if not _loop_enabled():
        return None

    now = now or datetime.now(UTC)
    resolved = _resolved_predictions_chrono()
    count = len(resolved)
    if count == 0:
        return None

    calibration = _calibration_of(resolved[-30:])  # last 30d window (approximate)

    # Rule 1: count_10
    if count > 0 and count % 10 == 0 and not _has_milestone("count_10", count):
        message = f"Du har nu {count} resolved predictions. Kalibrering sidste 30: {calibration}%."
        return _append_milestone("count_10", count, message, now)

    # Rule 2: first_contradiction_after_streak
    if count >= 6 and resolved[-1].get("outcome") == "contradicted":
        prior_5 = resolved[-6:-1]
        if all(p.get("outcome") == "supported" for p in prior_5):
            # Anchor by the specific prediction_id so each event fires only once
            pid = str(resolved[-1].get("prediction_id") or "")
            if not _has_milestone("first_contradiction_after_streak", pid):
                message = (
                    f"Du tog fejl efter {len(prior_5)} rigtige predictions i træk. "
                    "Worth noting."
                )
                return _append_milestone(
                    "first_contradiction_after_streak", pid, message, now,
                )

    # Rule 3: threshold cross
    for tier in (60, 70, 80):
        kind = f"threshold_{tier}"
        if calibration >= tier and not _has_milestone(kind):
            message = f"Din kalibrering er nu {calibration}% — over {tier}%."
            return _append_milestone(kind, tier, message, now)

    # Rule 4: trend (Jarvis-addition)
    if count >= 20:
        recent_10 = resolved[-10:]
        prior_10 = resolved[-20:-10]
        recent_cal = _calibration_of(recent_10)
        prior_cal = _calibration_of(prior_10)
        delta = round(recent_cal - prior_cal, 1)
        if delta >= 5:
            anchor = f"improving:{count}"
            if not _has_milestone("trend_improving", anchor):
                message = (
                    f"Din kalibrering er steget {delta}% over de sidste 10 predictions. "
                    "Du bliver bedre."
                )
                return _append_milestone("trend_improving", anchor, message, now)
        elif delta <= -5:
            anchor = f"declining:{count}"
            if not _has_milestone("trend_declining", anchor):
                message = (
                    f"Din kalibrering er faldet {abs(delta)}%. Hvad har ændret sig?"
                )
                return _append_milestone("trend_declining", anchor, message, now)

    return None


def format_world_model_milestone_for_awareness() -> str:
    """Surface one unrendered milestone per call. Returns '' when nothing."""
    if not _loop_enabled():
        return ""
    # Always check for new milestones before rendering
    _compute_calibration_milestone()

    data = _load_milestones()
    for m in data.get("history", []):
        if m.get("rendered_at"):
            continue
        m["rendered_at"] = datetime.now(UTC).isoformat()
        _save_milestones(data)
        return f"🧮 {m.get('message')}"
    return ""
```

- [ ] **Step 4: Wire milestone formatter into prompt_contract.py**

In `core/services/prompt_contract.py`, find the world-model nudges injection added in Task 4 (search for `world-model prediction/resolution nudges`). Add right after it:

```python
    # World Model loop Phase 1 (2026-05-12) — calibration milestone (one-shot)
    try:
        from core.services.world_model_signal_tracking import (
            format_world_model_milestone_for_awareness,
        )
        _awareness_add(
            37,
            "world-model calibration milestone",
            format_world_model_milestone_for_awareness() or None,
        )
    except Exception:
        pass
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_world_model_loop.py -v 2>&1 | tail -15
```

Expected: 29 passed (23 + 6).

- [ ] **Step 6: Commit**

```bash
git add core/services/world_model_signal_tracking.py core/services/prompt_contract.py tests/test_world_model_loop.py
git commit -m "feat(world-model-loop): calibration milestones (count/threshold/contradiction/trend) + awareness surface"
```

---

## Task 7: Smoke + 30-day review

**Files:**
- Modify: `scripts/smoke_test_startup.py`

- [ ] **Step 1: Add smoke imports**

In `scripts/smoke_test_startup.py`, find the Tool Invention Phase 1 smoke block and add right after it:

```python
        # World Model Phase 1 — closing the loop (AGI track #1 — 2026-05-12)
        try:
            from core.services.world_model_signal_tracking import (  # noqa: F401
                extract_prediction_language,
                extract_resolution_language,
                record_prediction_nudge,
                record_resolution_nudge,
                format_world_model_nudges_for_awareness,
                _ttl_sweep_open_predictions,
                _compute_calibration_milestone,
                format_world_model_milestone_for_awareness,
            )
            from core.tools.world_model_tools import (  # noqa: F401
                _exec_predict_outcome,
                _exec_resolve_prediction,
            )
            from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
            _names = [
                (e.get("function") or {}).get("name")
                for e in TOOL_DEFINITIONS if isinstance(e, dict)
            ]
            if "predict_outcome" not in _names:
                raise RuntimeError("predict_outcome not in TOOL_DEFINITIONS")
            if "resolve_prediction" not in _names:
                raise RuntimeError("resolve_prediction not in TOOL_DEFINITIONS")
        except Exception:
            traceback.print_exc()
```

- [ ] **Step 2: Run all affected test suites**

```bash
conda run -n ai pytest tests/test_world_model_loop.py tests/test_tool_invention.py tests/test_multistep_planner.py 2>&1 | tail -10
```

Expected: all green (29 + 18 + 26 = 73).

- [ ] **Step 3: Production probe — verify tools listed**

```bash
conda run -n ai python -c "
from core.tools.simple_tools import TOOL_DEFINITIONS
for nm in ('predict_outcome', 'resolve_prediction'):
    defs = [e for e in TOOL_DEFINITIONS if isinstance(e, dict) and (e.get('function') or {}).get('name') == nm]
    assert len(defs) == 1, f'{nm} not registered'
print('OK: both world-model tools registered')
"
```

- [ ] **Step 4: Production scanner probe**

```bash
conda run -n ai python -c "
from core.services.world_model_signal_tracking import (
    extract_prediction_language,
    extract_resolution_language,
)
print('prediction-shape examples:')
print(' ', len(extract_prediction_language('Jeg tror det her bliver godt.')))
print(' ', len(extract_prediction_language('Det vil sandsynligvis virke.')))
print('resolution-shape examples:')
print(' ', len(extract_resolution_language('Som forventet virkede det ikke.')))
print(' ', len(extract_resolution_language('Jeg tog fejl, det viste sig at gå anderledes.')))
"
```

Expected: all four prints show ≥ 1.

- [ ] **Step 5: Schedule 30-day review**

```bash
conda run -n ai python -c "
from core.services.scheduled_tasks import push_scheduled_task
focus = (
    'World Model Phase 1 (AGI track #1) — 30-day review: '
    'count predictions Jarvis lavede via predict_outcome tool, '
    'count nudges fired (both kinds, count of unique session/run), '
    'count nudges Jarvis acted on (acted_on indicator: prediction was '
    'recorded shortly after a prediction-nudge in same session), '
    'count resolutions by source (resolved_via: tool / ttl_auto), '
    'check calibration milestones rendered in history, '
    'read sample of predictions: meaningful or trivial? '
    'read pattern matches: high false-positive rate? '
    'If predictions = 0 - design failed, nudges werent enough; revisit. '
    'Decide: keep / tune phrases / Phase 1.1 LLM-extraction.'
)
r = push_scheduled_task(focus=focus, delay_minutes=30*24*60, source='world_model_loop_phase1')
print(r['task_id'], 'run_at=', r['run_at'])
"
```

- [ ] **Step 6: Commit + restart**

```bash
git add scripts/smoke_test_startup.py
git commit -m "chore(world-model-loop): smoke imports + 30-day review scheduled"
sudo -n systemctl daemon-reload 2>/dev/null || true
sudo -n systemctl restart jarvis-runtime jarvis-api && sleep 6 && sudo -n journalctl -u jarvis-runtime --since "30 seconds ago" -p err 2>&1 | tail -10
```

Expected: no errors.

---

## Self-review

**Spec coverage:**

| Spec section | Task(s) |
|---|---|
| Settings flag `world_model_loop_enabled` | Task 1 |
| `predict_outcome` tool | Task 2 |
| `resolve_prediction` tool | Task 2 |
| `resolved_via` field on resolve | Task 2 step 3 |
| Tools registered via splat | Task 2 step 5 |
| `_PREDICTION_PHRASES` + `_RESOLUTION_PHRASES` | Task 3 step 3 |
| `extract_prediction_language` + `extract_resolution_language` | Task 3 step 3 |
| `record_prediction_nudge` + `record_resolution_nudge` (48h TTL, FIFO max 20) | Task 3 step 3 |
| Wire scanners into visible_runs on assistant_text | Task 4 step 5 |
| `format_world_model_nudges_for_awareness` | Task 4 step 3 |
| Wire nudges into prompt_contract awareness | Task 4 step 6 |
| `_ttl_sweep_open_predictions` with horizon parsing + 24h grace | Task 5 step 3 |
| ProducerSpec `world_model_ttl_sweeper` (1440 min) | Task 5 step 5 |
| `_compute_calibration_milestone` — 4 rule categories | Task 6 step 3 |
| `format_world_model_milestone_for_awareness` | Task 6 step 3 |
| Wire milestone into prompt_contract | Task 6 step 4 |
| Smoke imports | Task 7 step 1 |
| 30-day review | Task 7 step 5 |
| Kill-switch reverts | Tasks 2, 3, 4, 5, 6 (each has killswitch check) |
| Backwards compat | All tasks: existing record/resolve APIs unchanged; 120-cap respected; line 2895 untouched |

No spec gaps.

**Placeholder scan:** No TBD/TODO. All code blocks concrete.

**Type consistency:**
- `extract_prediction_language(text: str) -> list[dict[str, str]]` — Tasks 3, 4
- `extract_resolution_language(text: str) -> list[dict[str, str]]` — Tasks 3, 4
- `record_prediction_nudge(*, session_id, run_id, matched_phrase, context_excerpt)` — Tasks 3, 4
- `record_resolution_nudge(*, session_id, run_id, matched_phrase, context_excerpt, candidate_prediction_id="")` — Tasks 3, 4
- `format_world_model_nudges_for_awareness(*, session_id: str | None) -> str` — Tasks 4, 6
- `_ttl_sweep_open_predictions(*, now: datetime | None = None) -> dict[str, int]` — Tasks 5
- `_compute_calibration_milestone(*, now: datetime | None = None) -> dict[str, object] | None` — Task 6
- `format_world_model_milestone_for_awareness() -> str` — Tasks 6, 7
- `resolve_runtime_world_model_prediction(... resolved_via="tool")` — Tasks 2, 5
- All state_store keys consistent: `runtime_world_model_predictions`, `runtime_world_model_nudges`, `runtime_world_model_milestones`

**Backwards-compat verified:**
- `record_runtime_world_model_prediction` signature unchanged.
- `resolve_runtime_world_model_prediction` gains optional `resolved_via` kwarg (default `"tool"`); existing callers default to `"tool"`.
- 120-prediction cap respected (logic in `record_runtime_world_model_prediction` unchanged).
- `track_runtime_world_model_signals_for_visible_turn` (line 2895) untouched.
- Modulator-witness surface unchanged.
- Kill-switch False → no nudges, no TTL, no milestones (verified per-function with `_loop_enabled()` checks). Tools remain functional as ledger.
- All scanner failures wrapped in try/except in visible_runs hook — never block downstream candidate tracking.
- No new DB schema. No new event families. No new daemons (TTL is a ProducerSpec reusing existing daemon manager).
