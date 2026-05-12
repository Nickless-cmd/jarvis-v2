# Skill Chain Phase 2 — Auto-planner + Adaptive Re-planning: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis to nye verbs på toppen af Phase 1's `skill_chain`: `propose_skill_chain(task_description)` (cheap-lane LLM foreslår en kæde) og `revise_skill_chain(reason, new_plan, revision_context)` (eksplicit pivot, dual-context). Lukker "jeg gætter når jeg plukker en kæde manuelt" + "ingen observability når jeg dropper en kæde."

**Architecture:** To nye stateless tool-moduler. `propose` kalder eksisterende `execute_public_safe_cheap_lane`, parser JSON-respons defensivt, validerer skill-eksistens + plan-længde + confidence-range, returnerer forslag (eller tom kæde). `revise` genbruger Phase 1's `_build_combined_instructions` + `_validate_plan_existence`, validerer `revision_context ∈ {pre_execution, mid_chain}`, emitter `cognitive_skill_chain.revised`-event med kontekst. Master killswitch `skill_chain_phase2_enabled`. Ingen DB, ingen daemons, ingen state.

**Tech Stack:** Python 3.11, eksisterende `core.services.cheap_provider_runtime.execute_public_safe_cheap_lane`, eventbus family `cognitive_skill_chain` (allerede registreret fra Phase 1).

**Spec:** `docs/superpowers/specs/2026-05-12-skill-chain-phase2-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `core/tools/skill_chain_propose_tool.py` | `_exec_propose_skill_chain` handler; prompt-builder; JSON-parse; skill-eksistens-validering; `cognitive_skill_chain.proposed` event. `PROPOSE_SKILL_CHAIN_TOOL_DEFINITIONS` + `PROPOSE_SKILL_CHAIN_TOOL_HANDLERS`. ~200 LOC. |
| `core/tools/skill_chain_revise_tool.py` | `_exec_revise_skill_chain` handler; genbruger Phase 1 builders; dual-context-event. `REVISE_SKILL_CHAIN_TOOL_DEFINITIONS` + `REVISE_SKILL_CHAIN_TOOL_HANDLERS`. ~130 LOC. |
| `tests/test_skill_chain_phase2.py` | Alle Phase 2 tests: validation, cheap-lane mocking (gyldig/malformed/timeout/tom-kæde), event-payloads, killswitch, dual-context, backwards-compat. |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | Add `skill_chain_phase2_enabled: bool = True` (master killswitch — én flag for begge nye tools). |
| `core/tools/simple_tools.py` | Import + splat begge nye tool-sets (mirror curiosity/plan_revision pattern). |
| `scripts/smoke_test_startup.py` | Verify imports + tool-registrering. |

### Untouched / reused

- **Phase 1 `core/tools/skill_chain_tool.py`** — uændret. Vi importerer `_build_combined_instructions` + `_validate_plan_existence` derfra. Phase 1 fortsætter med at virke som før.
- **`core/services/skill_engine.py`** — genbrug `list_skills()` (returnerer name+description+use_when+tags) og `skill_exists(name)`.
- **`core/services/cheap_provider_runtime.py`** — genbrug `execute_public_safe_cheap_lane(message=...)` (returnerer `{"text", "status", "provider", "model", ...}`).
- **`cognitive_skill_chain` event family** — allerede registreret fra Phase 1, ingen ny family.
- **`core/tools/skill_gate_tool.py`** — `chain_candidates` + `chain_hint`-felter uændrede.

---

## Spec deltas confirmed during planning

1. **Cheap-lane API bekræftet:** `core.services.cheap_provider_runtime.execute_public_safe_cheap_lane(message: str) -> dict` returnerer `{"text", "provider", "model", "status", "cost_usd", ...}`. Synchron, default timeout via `_execute_provider_chat`. Response.text er rå LLM-output — vi parser JSON selv defensivt.

2. **Skill-katalog format:** `skill_engine.list_skills()` returnerer `[{"name", "description", "use_when", "tags", ...}]`. Vi bruger kun `name` + `description` i prompt (`use_when` redundant for vores formål).

3. **Phase 1 builders:** `_build_combined_instructions(plan)` og `_validate_plan_existence(plan)` er module-level funktioner i `core/tools/skill_chain_tool.py` — kan importeres direkte. Verificeret i Read.

4. **Event family `cognitive_skill_chain`:** allerede tilladt (Phase 1 emitter `cognitive_skill_chain.executed`). Vi tilføjer `.proposed` og `.revised` — samme family, ingen registrering nødvendig.

5. **Simple_tools splat-pattern:** mirror curiosity (line ~488 import block, ~2336 TOOL_DEFINITIONS splat, ~6203 _TOOL_HANDLERS splat). Vi tilføjer EFTER `CURIOSITY_*` for at bevare logisk dato-orden.

---

## Task 1: Settings flag

**Files:**
- Modify: `core/runtime/settings.py`

- [ ] **Step 1: Add the flag**

In `core/runtime/settings.py`, find `curiosity_budget_enabled: bool = True` and add right after it:

```python
    # ── Skill Chain Phase 2 (added 2026-05-12 — AGI track #10) ────────────
    # When True: propose_skill_chain + revise_skill_chain tools registered.
    # When False: both tools error immediately, Phase 1 skill_chain works
    # as before (manual plukning). Master killswitch for both new tools.
    skill_chain_phase2_enabled: bool = True
```

- [ ] **Step 2: Wire default into load_settings**

In `core/runtime/settings.py`, find `curiosity_budget_enabled=bool(...)` block in `load_settings` and add right after its closing comma:

```python
        skill_chain_phase2_enabled=bool(
            data.get(
                "skill_chain_phase2_enabled",
                defaults.skill_chain_phase2_enabled,
            )
        ),
```

- [ ] **Step 3: Verify**

```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings, load_settings
s = RuntimeSettings()
assert s.skill_chain_phase2_enabled is True
print('OK:', load_settings().skill_chain_phase2_enabled)
"
```

Expected: `OK: True`

- [ ] **Step 4: Commit**

```bash
git add core/runtime/settings.py
git commit -m "feat(skill-chain-phase2): add skill_chain_phase2_enabled killswitch"
```

---

## Task 2: propose_skill_chain — module + cheap-lane integration

**Files:**
- Create: `core/tools/skill_chain_propose_tool.py`
- Create: `tests/test_skill_chain_phase2.py`

- [ ] **Step 1: Write the failing tests (validation + killswitch)**

Create `tests/test_skill_chain_phase2.py`:

```python
"""Skill Chain Phase 2 — tests.

AGI track #10. See spec at
docs/superpowers/specs/2026-05-12-skill-chain-phase2-design.md.
"""
from __future__ import annotations

import json
from typing import Any

import pytest


@pytest.fixture()
def clean_state(tmp_path, monkeypatch):
    """Isolated workspace + DB so events don't pollute across tests."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))
    import core.runtime.config as cfg
    monkeypatch.setattr(cfg, "STATE_DIR", str(tmp_path / "state"))
    import importlib
    import core.runtime.db as db
    importlib.reload(db)
    return None


# --- propose: validation ---

def test_propose_rejects_empty_task(clean_state):
    from core.tools.skill_chain_propose_tool import _exec_propose_skill_chain
    result = _exec_propose_skill_chain({"task_description": ""})
    assert result["status"] == "rejected"
    assert "task_description" in result["reason"].lower()


def test_propose_rejects_short_task(clean_state):
    from core.tools.skill_chain_propose_tool import _exec_propose_skill_chain
    result = _exec_propose_skill_chain({"task_description": "short"})
    assert result["status"] == "rejected"
    assert "10" in result["reason"]


def test_propose_killswitch(clean_state, monkeypatch):
    from core.tools import skill_chain_propose_tool as p

    class FakeSettings:
        skill_chain_phase2_enabled = False

    monkeypatch.setattr(p, "load_settings", lambda: FakeSettings())
    result = p._exec_propose_skill_chain({
        "task_description": "fact-check this article and format as markdown",
    })
    assert result["status"] == "disabled"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_skill_chain_phase2.py -v 2>&1 | tail -10
```

Expected: 3 fail with `ModuleNotFoundError: core.tools.skill_chain_propose_tool`.

- [ ] **Step 3: Create skeleton `skill_chain_propose_tool.py`**

Create `core/tools/skill_chain_propose_tool.py`:

```python
"""propose_skill_chain tool — Skill Chain Phase 2 (AGI track #10).

Givet en task_description, kald cheap-lane LLM med fuldt skill-katalog
og lad den foreslå en ordnet kæde af 2-5 skills (eller tom hvis ingen
meningsfuld kæde findes).

Returnerer struktureret forslag — ikke autorisation. Jarvis bestemmer
om han kører `skill_chain(plan=...)` med forslaget eller justerer.

Stateless. Ingen DB, ingen state-machine. Mirror plan_revise_tool /
world_model_tools pattern.

See spec: docs/superpowers/specs/2026-05-12-skill-chain-phase2-design.md
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from core.runtime.settings import load_settings

logger = logging.getLogger(__name__)


_MIN_TASK_LEN = 10
_MIN_PLAN_LEN = 2
_MAX_PLAN_LEN = 5
_TASK_EXCERPT_MAX = 120  # PII-bound on event payload
_RATIONALE_MAX_CHARS = 600  # bound on stored rationale


def _phase2_enabled() -> bool:
    try:
        return bool(load_settings().skill_chain_phase2_enabled)
    except Exception:
        return True  # fail-open


def _exec_propose_skill_chain(args: dict[str, Any]) -> dict[str, Any]:
    """Tool handler for propose_skill_chain."""
    # 1. Killswitch
    if not _phase2_enabled():
        return {
            "status": "disabled",
            "note": "skill_chain_phase2 is disabled in runtime settings",
        }

    # 2. Validate task_description
    task = str(args.get("task_description") or "").strip()
    if not task:
        return {"status": "rejected", "reason": "task_description is required"}
    if len(task) < _MIN_TASK_LEN:
        return {
            "status": "rejected",
            "reason": f"task_description must be at least {_MIN_TASK_LEN} chars",
        }

    # 3-7: To be implemented in subsequent steps
    return {"status": "error", "reason": "implementation incomplete"}
```

- [ ] **Step 4: Run tests to verify validation passes (killswitch + short task)**

```bash
conda run -n ai pytest tests/test_skill_chain_phase2.py -v 2>&1 | tail -10
```

Expected: 3 passed.

- [ ] **Step 5: Add prompt-builder and catalog-fetch tests**

Append to `tests/test_skill_chain_phase2.py`:

```python
def test_build_prompt_includes_skill_catalog(clean_state):
    from core.tools.skill_chain_propose_tool import _build_propose_prompt
    catalog = [
        {"name": "skill_a", "description": "Does A things"},
        {"name": "skill_b", "description": "Does B things"},
    ]
    prompt = _build_propose_prompt(
        task_description="fact-check and summarize",
        catalog=catalog,
    )
    assert "skill_a" in prompt
    assert "Does A things" in prompt
    assert "fact-check and summarize" in prompt
    assert '"plan"' in prompt  # JSON schema hint
    assert '"confidence"' in prompt
    assert '"rationale"' in prompt


def test_build_prompt_includes_empty_plan_fallback_instruction(clean_state):
    """Prompt must explicitly tell cheap-lane it may return [] if no chain fits."""
    from core.tools.skill_chain_propose_tool import _build_propose_prompt
    prompt = _build_propose_prompt(task_description="task here long enough", catalog=[])
    assert "[]" in prompt or "tom" in prompt.lower() or "empty" in prompt.lower()
```

- [ ] **Step 6: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_skill_chain_phase2.py -k "build_prompt" -v 2>&1 | tail -10
```

Expected: 2 fail with `cannot import name '_build_propose_prompt'`.

- [ ] **Step 7: Add `_build_propose_prompt` to module**

In `core/tools/skill_chain_propose_tool.py`, replace the placeholder `return {"status": "error", "reason": "implementation incomplete"}` line and add helper functions:

```python
def _build_propose_prompt(
    *,
    task_description: str,
    catalog: list[dict[str, Any]],
) -> str:
    """Build the cheap-lane prompt. Compact — ~2-3k tokens for 50 skills."""
    catalog_lines = []
    for entry in catalog:
        name = str(entry.get("name") or "").strip()
        desc = str(entry.get("description") or "").strip()
        if not name:
            continue
        # 1-line per skill — cap description at 120 chars to keep prompt tight
        desc_compact = desc[:120].replace("\n", " ").strip()
        catalog_lines.append(f"- {name}: {desc_compact}")
    catalog_block = "\n".join(catalog_lines) if catalog_lines else "(katalog tomt)"

    return (
        "Du er en skill-planner. Givet en opgave-beskrivelse og et "
        "katalog af tilgængelige skills, foreslå en ordnet kæde af "
        f"{_MIN_PLAN_LEN}-{_MAX_PLAN_LEN} skills der løser opgaven.\n"
        "\n"
        "Returnér KUN valid JSON med præcis disse felter:\n"
        '  {"plan": [...], "rationale": "...", "confidence": 0.0-1.0}\n'
        "\n"
        f"- plan: liste af {_MIN_PLAN_LEN}-{_MAX_PLAN_LEN} skill-navne i "
        "eksekveringsrækkefølge. Hvis INGEN meningsfuld kæde findes "
        "(opgaven er for vag, eller én skill er nok), returnér [] (tom liste).\n"
        "- rationale: 1-2 sætninger om hvorfor kæden løser opgaven, "
        "eller hvorfor ingen kæde virker. Maks 600 tegn.\n"
        "- confidence: dit estimat af hvor godt kæden løser opgaven, "
        "i intervallet 0.0 til 1.0.\n"
        "\n"
        f"Opgave: {task_description}\n"
        "\n"
        "Katalog:\n"
        f"{catalog_block}\n"
    )
```

- [ ] **Step 8: Run prompt tests to verify they pass**

```bash
conda run -n ai pytest tests/test_skill_chain_phase2.py -k "build_prompt" -v 2>&1 | tail -5
```

Expected: 2 passed.

- [ ] **Step 9: Add JSON-parse + validation tests**

Append to `tests/test_skill_chain_phase2.py`:

```python
def test_parse_response_valid_json(clean_state):
    from core.tools.skill_chain_propose_tool import _parse_propose_response
    text = '{"plan": ["a", "b"], "rationale": "because", "confidence": 0.7}'
    result = _parse_propose_response(text)
    assert result["status"] == "ok"
    assert result["plan"] == ["a", "b"]
    assert result["confidence"] == 0.7
    assert result["rationale"] == "because"


def test_parse_response_empty_plan_is_valid(clean_state):
    """Tom-kæde-fallback: cheap-lane må returnere plan=[]."""
    from core.tools.skill_chain_propose_tool import _parse_propose_response
    text = '{"plan": [], "rationale": "kan ikke finde meningsfuld kæde", "confidence": 0.1}'
    result = _parse_propose_response(text)
    assert result["status"] == "ok"
    assert result["plan"] == []


def test_parse_response_malformed_json_fails(clean_state):
    from core.tools.skill_chain_propose_tool import _parse_propose_response
    result = _parse_propose_response("not valid json at all")
    assert result["status"] == "error"
    assert "invalid" in result["reason"].lower() or "parse" in result["reason"].lower()


def test_parse_response_extracts_json_from_markdown_fence(clean_state):
    """Cheap-lane often wraps JSON in ```json``` fences. Tolerate it."""
    from core.tools.skill_chain_propose_tool import _parse_propose_response
    text = 'Sure!\n```json\n{"plan": ["a", "b"], "rationale": "x", "confidence": 0.5}\n```'
    result = _parse_propose_response(text)
    assert result["status"] == "ok"
    assert result["plan"] == ["a", "b"]


def test_parse_response_confidence_out_of_range_rejected(clean_state):
    from core.tools.skill_chain_propose_tool import _parse_propose_response
    text = '{"plan": ["a", "b"], "rationale": "x", "confidence": 1.5}'
    result = _parse_propose_response(text)
    assert result["status"] == "error"


def test_parse_response_plan_too_long_rejected(clean_state):
    from core.tools.skill_chain_propose_tool import _parse_propose_response
    text = '{"plan": ["a","b","c","d","e","f","g"], "rationale": "x", "confidence": 0.5}'
    result = _parse_propose_response(text)
    assert result["status"] == "error"


def test_parse_response_plan_single_skill_rejected(clean_state):
    """1 skill is not a chain. Reject (cheap-lane should have returned [])."""
    from core.tools.skill_chain_propose_tool import _parse_propose_response
    text = '{"plan": ["a"], "rationale": "just one", "confidence": 0.5}'
    result = _parse_propose_response(text)
    assert result["status"] == "error"


def test_parse_response_rationale_truncated(clean_state):
    from core.tools.skill_chain_propose_tool import _parse_propose_response
    long_rationale = "x" * 1000
    text = json.dumps({"plan": ["a","b"], "rationale": long_rationale, "confidence": 0.5})
    result = _parse_propose_response(text)
    assert result["status"] == "ok"
    assert len(result["rationale"]) <= 600
```

- [ ] **Step 10: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_skill_chain_phase2.py -k "parse_response" -v 2>&1 | tail -15
```

Expected: 8 fail with `cannot import name '_parse_propose_response'`.

- [ ] **Step 11: Add `_parse_propose_response` to module**

In `core/tools/skill_chain_propose_tool.py`, add right after `_build_propose_prompt`:

```python
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)


def _extract_json_blob(text: str) -> str:
    """Tolerate markdown fences and prose around JSON."""
    text = text.strip()
    fence_match = _JSON_FENCE_RE.search(text)
    if fence_match:
        return fence_match.group(1).strip()
    # No fence — try to find first {...} block
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start:end + 1]
    return text


def _parse_propose_response(text: str) -> dict[str, Any]:
    """Parse cheap-lane response. Returns {status, plan, rationale, confidence}
    or {status: error, reason}."""
    raw = (text or "").strip()
    if not raw:
        return {"status": "error", "reason": "empty response"}

    blob = _extract_json_blob(raw)
    try:
        data = json.loads(blob)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "status": "error",
            "reason": f"invalid JSON in cheap-lane response: {exc}",
        }

    if not isinstance(data, dict):
        return {"status": "error", "reason": "response is not a JSON object"}

    plan = data.get("plan")
    if not isinstance(plan, list):
        return {"status": "error", "reason": "plan must be a list"}
    if plan and not all(isinstance(s, str) and s.strip() for s in plan):
        return {"status": "error", "reason": "plan entries must be non-empty strings"}
    # Tom plan = legitim "ved ikke"-fallback; ellers 2-5 entries
    if plan and (len(plan) < _MIN_PLAN_LEN or len(plan) > _MAX_PLAN_LEN):
        return {
            "status": "error",
            "reason": f"plan length must be 0 (empty) or {_MIN_PLAN_LEN}-{_MAX_PLAN_LEN}",
        }

    confidence = data.get("confidence")
    try:
        confidence_f = float(confidence)
    except (TypeError, ValueError):
        return {"status": "error", "reason": "confidence must be numeric"}
    if not (0.0 <= confidence_f <= 1.0):
        return {"status": "error", "reason": "confidence must be in [0.0, 1.0]"}

    rationale = str(data.get("rationale") or "").strip()
    if not rationale:
        return {"status": "error", "reason": "rationale is required"}

    return {
        "status": "ok",
        "plan": [str(s).strip() for s in plan],
        "rationale": rationale[:_RATIONALE_MAX_CHARS],
        "confidence": confidence_f,
    }
```

- [ ] **Step 12: Run parse tests to verify they pass**

```bash
conda run -n ai pytest tests/test_skill_chain_phase2.py -k "parse_response" -v 2>&1 | tail -10
```

Expected: 8 passed.

- [ ] **Step 13: Commit progress so far**

```bash
git add core/tools/skill_chain_propose_tool.py tests/test_skill_chain_phase2.py
git commit -m "feat(skill-chain-phase2): propose tool skeleton + prompt builder + JSON parser"
```

---

## Task 3: propose_skill_chain — cheap-lane integration + event + tool definition

**Files:**
- Modify: `core/tools/skill_chain_propose_tool.py`
- Modify: `tests/test_skill_chain_phase2.py`

- [ ] **Step 1: Write the failing tests (end-to-end with mocked cheap-lane)**

Append to `tests/test_skill_chain_phase2.py`:

```python
def test_propose_end_to_end_with_mocked_cheap_lane(clean_state, monkeypatch):
    """Happy path: cheap-lane returns valid JSON with real skill names."""
    from core.tools import skill_chain_propose_tool as p
    from core.services import skill_engine

    real_skills = skill_engine.list_skills()
    if len(real_skills) < 2:
        pytest.skip("need at least 2 real skills to test plan-existence validation")
    a, b = real_skills[0]["name"], real_skills[1]["name"]

    fake_text = json.dumps({
        "plan": [a, b],
        "rationale": "First a, then b makes sense",
        "confidence": 0.75,
    })

    def fake_cheap_lane(*, message: str) -> dict[str, Any]:
        return {"status": "completed", "text": fake_text, "provider": "fake", "model": "x"}

    monkeypatch.setattr(p, "execute_public_safe_cheap_lane", fake_cheap_lane)

    result = p._exec_propose_skill_chain({
        "task_description": "do the thing with a and b",
    })
    assert result["status"] == "ok"
    assert result["plan"] == [a, b]
    assert result["confidence"] == 0.75
    assert result["rationale"] == "First a, then b makes sense"
    assert result["model_used"] == "x"


def test_propose_rejects_plan_with_unknown_skill(clean_state, monkeypatch):
    """Cheap-lane hallucinated a skill that doesn't exist. We reject."""
    from core.tools import skill_chain_propose_tool as p
    from core.services import skill_engine

    real = skill_engine.list_skills()
    if not real:
        pytest.skip("need at least 1 real skill")
    real_name = real[0]["name"]

    fake_text = json.dumps({
        "plan": [real_name, "totally_made_up_skill_xyz"],
        "rationale": "x",
        "confidence": 0.5,
    })

    def fake_cheap_lane(*, message: str) -> dict[str, Any]:
        return {"status": "completed", "text": fake_text, "provider": "x", "model": "y"}

    monkeypatch.setattr(p, "execute_public_safe_cheap_lane", fake_cheap_lane)

    result = p._exec_propose_skill_chain({"task_description": "task long enough"})
    assert result["status"] == "rejected"
    assert "totally_made_up_skill_xyz" in result.get("missing", [])


def test_propose_empty_plan_passes_through(clean_state, monkeypatch):
    """Cheap-lane returns plan=[] — that's a legitimate 'ved ikke'-signal."""
    from core.tools import skill_chain_propose_tool as p

    fake_text = json.dumps({
        "plan": [],
        "rationale": "kan ikke finde meningsfuld kæde for denne opgave",
        "confidence": 0.0,
    })

    def fake_cheap_lane(*, message: str) -> dict[str, Any]:
        return {"status": "completed", "text": fake_text, "provider": "x", "model": "y"}

    monkeypatch.setattr(p, "execute_public_safe_cheap_lane", fake_cheap_lane)

    result = p._exec_propose_skill_chain({"task_description": "task long enough"})
    assert result["status"] == "ok"
    assert result["plan"] == []
    assert result["confidence"] == 0.0
    assert "ved ikke" in result["rationale"] or "kan ikke" in result["rationale"]


def test_propose_cheap_lane_malformed_response(clean_state, monkeypatch):
    from core.tools import skill_chain_propose_tool as p

    def fake_cheap_lane(*, message: str) -> dict[str, Any]:
        return {"status": "completed", "text": "I'm sorry I can't help", "provider": "x", "model": "y"}

    monkeypatch.setattr(p, "execute_public_safe_cheap_lane", fake_cheap_lane)
    result = p._exec_propose_skill_chain({"task_description": "task long enough"})
    assert result["status"] == "error"


def test_propose_cheap_lane_exception_handled(clean_state, monkeypatch):
    from core.tools import skill_chain_propose_tool as p

    def fake_cheap_lane(*, message: str) -> dict[str, Any]:
        raise RuntimeError("network timeout")

    monkeypatch.setattr(p, "execute_public_safe_cheap_lane", fake_cheap_lane)
    result = p._exec_propose_skill_chain({"task_description": "task long enough"})
    assert result["status"] == "error"
    assert "cheap-lane" in result["reason"].lower()


def test_propose_tool_definitions_registered():
    from core.tools.skill_chain_propose_tool import (
        PROPOSE_SKILL_CHAIN_TOOL_DEFINITIONS,
        PROPOSE_SKILL_CHAIN_TOOL_HANDLERS,
    )
    names = [
        (e.get("function") or {}).get("name")
        for e in PROPOSE_SKILL_CHAIN_TOOL_DEFINITIONS if isinstance(e, dict)
    ]
    assert "propose_skill_chain" in names
    assert "propose_skill_chain" in PROPOSE_SKILL_CHAIN_TOOL_HANDLERS
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_skill_chain_phase2.py -v 2>&1 | tail -10
```

Expected: 6 fail (missing cheap-lane import / missing tool defs).

- [ ] **Step 3: Complete the propose handler — full implementation**

In `core/tools/skill_chain_propose_tool.py`, add the imports at top (right after `from core.runtime.settings import load_settings`):

```python
from core.services.cheap_provider_runtime import execute_public_safe_cheap_lane
from core.services.skill_engine import list_skills, skill_exists
```

Then **replace** the existing `_exec_propose_skill_chain` function (the skeleton stub with the "implementation incomplete" line) with the full implementation:

```python
def _exec_propose_skill_chain(args: dict[str, Any]) -> dict[str, Any]:
    """Tool handler for propose_skill_chain.

    Pipeline:
      1. Killswitch
      2. Validate task_description (≥ 10 chars)
      3. Fetch skill catalog
      4. Build prompt
      5. Invoke cheap-lane
      6. Parse JSON response
      7. Validate skill existence (alt-eller-intet)
      8. Emit cognitive_skill_chain.proposed event
      9. Return structured proposal
    """
    # 1. Killswitch
    if not _phase2_enabled():
        return {
            "status": "disabled",
            "note": "skill_chain_phase2 is disabled in runtime settings",
        }

    # 2. Validate task_description
    task = str(args.get("task_description") or "").strip()
    if not task:
        return {"status": "rejected", "reason": "task_description is required"}
    if len(task) < _MIN_TASK_LEN:
        return {
            "status": "rejected",
            "reason": f"task_description must be at least {_MIN_TASK_LEN} chars",
        }

    # 3. Fetch catalog
    try:
        catalog = list_skills()
    except Exception as exc:
        logger.warning("propose_skill_chain: catalog fetch failed: %s", exc)
        return {"status": "error", "reason": f"skill catalog unavailable: {exc}"}

    # 4. Build prompt
    prompt = _build_propose_prompt(task_description=task, catalog=catalog)

    # 5. Invoke cheap-lane
    try:
        cheap_result = execute_public_safe_cheap_lane(message=prompt)
    except Exception as exc:
        logger.warning("propose_skill_chain: cheap-lane invocation failed: %s", exc)
        return {"status": "error", "reason": f"cheap-lane error: {exc}"}

    response_text = str(cheap_result.get("text") or "")
    model_used = str(cheap_result.get("model") or "")
    provider_used = str(cheap_result.get("provider") or "")

    # 6. Parse response
    parsed = _parse_propose_response(response_text)
    if parsed["status"] != "ok":
        return {
            "status": "error",
            "reason": parsed["reason"],
            "raw_response_excerpt": response_text[:200],
            "model_used": model_used,
        }

    plan = parsed["plan"]
    rationale = parsed["rationale"]
    confidence = parsed["confidence"]

    # 7. Validate skill existence (only when plan non-empty)
    missing = [name for name in plan if not skill_exists(name)]
    if missing:
        return {
            "status": "rejected",
            "reason": "cheap-lane suggested unknown skills",
            "missing": missing,
            "rejected_plan": plan,
            "rationale": rationale,
            "confidence": confidence,
        }

    # 8. Emit event (metadata only — task_excerpt PII-bounded, rationale_length not text)
    _publish_propose_event(
        plan=plan,
        confidence=confidence,
        rationale_length=len(rationale),
        model_used=model_used,
        provider_used=provider_used,
        task_excerpt=task[:_TASK_EXCERPT_MAX],
    )

    # 9. Return proposal to Jarvis (rationale text DOES return to caller —
    # event_payload is the PII-bounded version; tool return value is the
    # full Jarvis-facing payload)
    return {
        "status": "ok",
        "plan": plan,
        "rationale": rationale,
        "confidence": confidence,
        "model_used": model_used,
        "provider_used": provider_used,
        "is_empty_chain": len(plan) == 0,
    }


def _publish_propose_event(
    *,
    plan: list[str],
    confidence: float,
    rationale_length: int,
    model_used: str,
    provider_used: str,
    task_excerpt: str,
) -> None:
    """Defensively publish cognitive_skill_chain.proposed. Never blocks."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "cognitive_skill_chain.proposed",
            {
                "plan": plan,
                "step_count": len(plan),
                "is_empty_chain": len(plan) == 0,
                "confidence": confidence,
                "rationale_length": rationale_length,
                "model_used": model_used,
                "provider_used": provider_used,
                "task_excerpt": task_excerpt,
            },
        )
    except Exception as exc:
        logger.debug("propose_skill_chain: event publish failed: %s", exc)
```

- [ ] **Step 4: Add tool-definitions block**

Append to `core/tools/skill_chain_propose_tool.py`:

```python
PROPOSE_SKILL_CHAIN_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "propose_skill_chain",
            "description": (
                "Foreslå en ordnet kæde af 2-5 skills til at løse en given "
                "opgave. Bruger cheap-lane LLM med fuldt skill-katalog "
                "(~50 skills) til at vælge meningsfulde sekvenser. "
                "Returnér struktureret forslag: {plan, rationale, "
                "confidence (0-1), model_used}. Confidence er DIT filter — "
                "lav confidence betyder du bør justere kæden selv. "
                "Tom plan ([]) er legitimt resultat når ingen meningsfuld "
                "kæde findes. Forslag er IKKE autorisation — kald "
                "`skill_chain(plan=...)` for at eksekvere, eller "
                "`revise_skill_chain(...)` for at justere før eksekvering."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": (
                            "Klar beskrivelse af opgaven der skal løses. "
                            "Mindst 10 tegn."
                        ),
                    },
                },
                "required": ["task_description"],
            },
        },
    },
]

PROPOSE_SKILL_CHAIN_TOOL_HANDLERS: dict[str, Any] = {
    "propose_skill_chain": _exec_propose_skill_chain,
}
```

- [ ] **Step 5: Run all propose tests**

```bash
conda run -n ai pytest tests/test_skill_chain_phase2.py -v 2>&1 | tail -20
```

Expected: 19 passed.

- [ ] **Step 6: Commit**

```bash
git add core/tools/skill_chain_propose_tool.py tests/test_skill_chain_phase2.py
git commit -m "feat(skill-chain-phase2): propose_skill_chain end-to-end (cheap-lane + validation + event)"
```

---

## Task 4: revise_skill_chain — module + dual-context

**Files:**
- Create: `core/tools/skill_chain_revise_tool.py`
- Modify: `tests/test_skill_chain_phase2.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_skill_chain_phase2.py`:

```python
# --- revise: validation ---

def test_revise_killswitch(clean_state, monkeypatch):
    from core.tools import skill_chain_revise_tool as r

    class FakeSettings:
        skill_chain_phase2_enabled = False

    monkeypatch.setattr(r, "load_settings", lambda: FakeSettings())
    result = r._exec_revise_skill_chain({
        "reason": "valid reason that is long enough",
        "new_plan": ["a", "b"],
        "revision_context": "pre_execution",
    })
    assert result["status"] == "disabled"


def test_revise_rejects_short_reason(clean_state):
    from core.tools.skill_chain_revise_tool import _exec_revise_skill_chain
    result = _exec_revise_skill_chain({
        "reason": "x",
        "new_plan": ["a", "b"],
        "revision_context": "pre_execution",
    })
    assert result["status"] == "rejected"
    assert "reason" in result["reason"].lower()


def test_revise_rejects_missing_reason(clean_state):
    from core.tools.skill_chain_revise_tool import _exec_revise_skill_chain
    result = _exec_revise_skill_chain({
        "new_plan": ["a", "b"],
        "revision_context": "pre_execution",
    })
    assert result["status"] == "rejected"


def test_revise_rejects_invalid_revision_context(clean_state):
    from core.tools.skill_chain_revise_tool import _exec_revise_skill_chain
    result = _exec_revise_skill_chain({
        "reason": "long enough reason here",
        "new_plan": ["a", "b"],
        "revision_context": "something_else",
    })
    assert result["status"] == "rejected"
    assert "revision_context" in result["reason"].lower()


def test_revise_rejects_plan_too_short(clean_state):
    from core.tools.skill_chain_revise_tool import _exec_revise_skill_chain
    result = _exec_revise_skill_chain({
        "reason": "long enough reason here",
        "new_plan": ["a"],
        "revision_context": "pre_execution",
    })
    assert result["status"] == "rejected"


def test_revise_rejects_plan_too_long(clean_state):
    from core.tools.skill_chain_revise_tool import _exec_revise_skill_chain
    result = _exec_revise_skill_chain({
        "reason": "long enough reason here",
        "new_plan": ["a", "b", "c", "d", "e", "f"],
        "revision_context": "pre_execution",
    })
    assert result["status"] == "rejected"


def test_revise_rejects_unknown_skills_atomically(clean_state):
    """Mirror Phase 1 alt-eller-intet validation."""
    from core.tools.skill_chain_revise_tool import _exec_revise_skill_chain
    from core.services import skill_engine

    real = skill_engine.list_skills()
    if not real:
        pytest.skip("need at least 1 real skill")
    real_name = real[0]["name"]

    result = _exec_revise_skill_chain({
        "reason": "valid reason that is long enough",
        "new_plan": [real_name, "totally_made_up_skill"],
        "revision_context": "pre_execution",
    })
    assert result["status"] == "rejected"
    assert "totally_made_up_skill" in result.get("missing", [])


def test_revise_succeeds_pre_execution(clean_state):
    """Happy path: pre_execution revision builds combined instructions."""
    from core.tools.skill_chain_revise_tool import _exec_revise_skill_chain
    from core.services import skill_engine

    real = skill_engine.list_skills()
    if len(real) < 2:
        pytest.skip("need at least 2 real skills")
    a, b = real[0]["name"], real[1]["name"]

    result = _exec_revise_skill_chain({
        "reason": "propose-forslaget passede ikke til opgaven",
        "new_plan": [a, b],
        "revision_context": "pre_execution",
    })
    assert result["status"] == "ok"
    assert result["new_plan"] == [a, b]
    assert isinstance(result["instructions"], str)
    assert len(result["instructions"]) > 50
    assert result["revision_context"] == "pre_execution"


def test_revise_succeeds_mid_chain(clean_state):
    """Happy path: mid_chain revision works identically."""
    from core.tools.skill_chain_revise_tool import _exec_revise_skill_chain
    from core.services import skill_engine

    real = skill_engine.list_skills()
    if len(real) < 2:
        pytest.skip("need at least 2 real skills")
    a, b = real[0]["name"], real[1]["name"]

    result = _exec_revise_skill_chain({
        "reason": "step 1 afslørede at jeg skal en anden retning",
        "new_plan": [a, b],
        "revision_context": "mid_chain",
    })
    assert result["status"] == "ok"
    assert result["revision_context"] == "mid_chain"


def test_revise_tool_definitions_registered():
    from core.tools.skill_chain_revise_tool import (
        REVISE_SKILL_CHAIN_TOOL_DEFINITIONS,
        REVISE_SKILL_CHAIN_TOOL_HANDLERS,
    )
    names = [
        (e.get("function") or {}).get("name")
        for e in REVISE_SKILL_CHAIN_TOOL_DEFINITIONS if isinstance(e, dict)
    ]
    assert "revise_skill_chain" in names
    assert "revise_skill_chain" in REVISE_SKILL_CHAIN_TOOL_HANDLERS
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_skill_chain_phase2.py -v 2>&1 | tail -10
```

Expected: 10 fail with `ModuleNotFoundError: core.tools.skill_chain_revise_tool`.

- [ ] **Step 3: Create `core/tools/skill_chain_revise_tool.py`**

```python
"""revise_skill_chain tool — Skill Chain Phase 2 (AGI track #10).

Eksplicit revision-verb for skill_chain. Gyldig i to kontekster:

  - pre_execution: Jarvis modtog et forslag fra propose_skill_chain men
    vil justere kæden før han kører den.
  - mid_chain: Jarvis er midt i at eksekvere en kæde og indser at
    retningen ikke længere passer baseret på intermediate result.

Genbruger Phase 1's `_build_combined_instructions` og
`_validate_plan_existence` direkte fra skill_chain_tool.py. Stateless —
ingen state-machine, ingen chain_id.

See spec: docs/superpowers/specs/2026-05-12-skill-chain-phase2-design.md
"""
from __future__ import annotations

import logging
from typing import Any

from core.runtime.settings import load_settings
from core.tools.skill_chain_tool import (
    _build_combined_instructions,
    _validate_plan_existence,
)

logger = logging.getLogger(__name__)


_MIN_REASON_LEN = 10
_MIN_PLAN_LEN = 2
_MAX_PLAN_LEN = 5
_REASON_PAYLOAD_MAX = 200  # bound on event payload (not on input)
_VALID_CONTEXTS = ("pre_execution", "mid_chain")


def _phase2_enabled() -> bool:
    try:
        return bool(load_settings().skill_chain_phase2_enabled)
    except Exception:
        return True  # fail-open


def _exec_revise_skill_chain(args: dict[str, Any]) -> dict[str, Any]:
    """Tool handler for revise_skill_chain.

    Validates → pre-validates skill existence → builds combined
    instructions → emits event → returns.
    """
    # 1. Killswitch
    if not _phase2_enabled():
        return {
            "status": "disabled",
            "note": "skill_chain_phase2 is disabled in runtime settings",
        }

    # 2. Validate reason
    reason = str(args.get("reason") or "").strip()
    if not reason:
        return {"status": "rejected", "reason": "reason is required"}
    if len(reason) < _MIN_REASON_LEN:
        return {
            "status": "rejected",
            "reason": f"reason must be at least {_MIN_REASON_LEN} chars",
        }

    # 3. Validate revision_context
    revision_context = str(args.get("revision_context") or "").strip()
    if revision_context not in _VALID_CONTEXTS:
        return {
            "status": "rejected",
            "reason": (
                f"revision_context must be one of {_VALID_CONTEXTS}, "
                f"got {revision_context!r}"
            ),
        }

    # 4. Validate new_plan structure
    new_plan = args.get("new_plan")
    if not isinstance(new_plan, list):
        return {"status": "rejected", "reason": "new_plan must be a list"}
    if not all(isinstance(s, str) and s.strip() for s in new_plan):
        return {
            "status": "rejected",
            "reason": "new_plan entries must be non-empty strings",
        }
    normalized = [s.strip() for s in new_plan]
    if len(normalized) < _MIN_PLAN_LEN:
        return {
            "status": "rejected",
            "reason": f"new_plan must have at least {_MIN_PLAN_LEN} skills",
        }
    if len(normalized) > _MAX_PLAN_LEN:
        return {
            "status": "rejected",
            "reason": f"new_plan exceeds max length of {_MAX_PLAN_LEN}",
        }

    # 5. Pre-validate skill existence (alt-eller-intet, mirror Phase 1)
    missing = _validate_plan_existence(normalized)
    if missing:
        return {
            "status": "rejected",
            "reason": "unknown skills in new_plan",
            "missing": missing,
        }

    # 6. Build combined instructions (genbrug Phase 1)
    instructions = _build_combined_instructions(normalized)

    # 7. Emit event
    _publish_revise_event(
        new_plan=normalized,
        reason=reason[:_REASON_PAYLOAD_MAX],
        revision_context=revision_context,
        instructions_length=len(instructions),
    )

    # 8. Return success
    return {
        "status": "ok",
        "new_plan": normalized,
        "revision_context": revision_context,
        "instructions": instructions,
        "instructions_length": len(instructions),
    }


def _publish_revise_event(
    *,
    new_plan: list[str],
    reason: str,
    revision_context: str,
    instructions_length: int,
) -> None:
    """Defensively publish cognitive_skill_chain.revised. Never blocks."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "cognitive_skill_chain.revised",
            {
                "new_plan": new_plan,
                "step_count": len(new_plan),
                "reason": reason,
                "revision_context": revision_context,
                "instructions_length": instructions_length,
            },
        )
    except Exception as exc:
        logger.debug("revise_skill_chain: event publish failed: %s", exc)


REVISE_SKILL_CHAIN_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "revise_skill_chain",
            "description": (
                "Erklær eksplicit at du dropper én kæde til fordel for en "
                "anden. Gyldig i to kontekster: 'pre_execution' (du så et "
                "propose_skill_chain-forslag og vil justere før du kører) "
                "eller 'mid_chain' (du er midt i at eksekvere og indser "
                "at retningen ikke længere passer). Returnerer combined "
                "instructions for den nye plan — samme format som "
                "skill_chain. Stateless: ingen chain_id, ingen state-"
                "machine. Brug dette FREM FOR at kalde skill_chain igen, "
                "så vi får observability på dine revisioner."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": (
                            "Hvorfor reviderer du? 1-2 sætninger om hvad "
                            "der ændrede dig fra den oprindelige kæde. "
                            "Mindst 10 tegn."
                        ),
                    },
                    "new_plan": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Den nye kæde — 2-5 skill-navne i "
                            "eksekveringsrækkefølge."
                        ),
                    },
                    "revision_context": {
                        "type": "string",
                        "enum": ["pre_execution", "mid_chain"],
                        "description": (
                            "'pre_execution' hvis du dropper et forslag før "
                            "eksekvering. 'mid_chain' hvis du pivoter midt i."
                        ),
                    },
                },
                "required": ["reason", "new_plan", "revision_context"],
            },
        },
    },
]

REVISE_SKILL_CHAIN_TOOL_HANDLERS: dict[str, Any] = {
    "revise_skill_chain": _exec_revise_skill_chain,
}
```

- [ ] **Step 4: Run all revise tests**

```bash
conda run -n ai pytest tests/test_skill_chain_phase2.py -v 2>&1 | tail -15
```

Expected: 29 passed (19 propose + 10 revise).

- [ ] **Step 5: Commit**

```bash
git add core/tools/skill_chain_revise_tool.py tests/test_skill_chain_phase2.py
git commit -m "feat(skill-chain-phase2): revise_skill_chain dual-context (pre_execution + mid_chain)"
```

---

## Task 5: Register tools + smoke + 30-day review

**Files:**
- Modify: `core/tools/simple_tools.py`
- Modify: `scripts/smoke_test_startup.py`
- Modify: `tests/test_skill_chain_phase2.py`

- [ ] **Step 1: Write the failing registration test**

Append to `tests/test_skill_chain_phase2.py`:

```python
def test_both_tools_registered_via_simple_tools():
    """End-to-end: splat into simple_tools picks up both Phase 2 tools."""
    from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
    names = {
        (e.get("function") or {}).get("name")
        for e in TOOL_DEFINITIONS if isinstance(e, dict)
    }
    assert "propose_skill_chain" in names
    assert "revise_skill_chain" in names
    assert "propose_skill_chain" in _TOOL_HANDLERS
    assert "revise_skill_chain" in _TOOL_HANDLERS
    # Phase 1 skill_chain must still be present
    assert "skill_chain" in names
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n ai pytest tests/test_skill_chain_phase2.py -k "registered_via_simple_tools" -v 2>&1 | tail -5
```

Expected: FAIL — Phase 2 tools missing from TOOL_DEFINITIONS.

- [ ] **Step 3: Register in `simple_tools.py` — imports**

In `core/tools/simple_tools.py`, find the existing `CURIOSITY_TOOL_DEFINITIONS` import block (line ~491). Add right after that import:

```python
from core.tools.skill_chain_propose_tool import (
    PROPOSE_SKILL_CHAIN_TOOL_DEFINITIONS,
    PROPOSE_SKILL_CHAIN_TOOL_HANDLERS,
)
from core.tools.skill_chain_revise_tool import (
    REVISE_SKILL_CHAIN_TOOL_DEFINITIONS,
    REVISE_SKILL_CHAIN_TOOL_HANDLERS,
)
```

- [ ] **Step 4: Register in `simple_tools.py` — TOOL_DEFINITIONS splat**

In `core/tools/simple_tools.py`, find `*CURIOSITY_TOOL_DEFINITIONS,` in the `TOOL_DEFINITIONS` list. Add right after it:

```python
    *PROPOSE_SKILL_CHAIN_TOOL_DEFINITIONS,
    *REVISE_SKILL_CHAIN_TOOL_DEFINITIONS,
```

- [ ] **Step 5: Register in `simple_tools.py` — _TOOL_HANDLERS splat**

In `core/tools/simple_tools.py`, find `**CURIOSITY_TOOL_HANDLERS,` in the `_TOOL_HANDLERS` dict. Add right after it:

```python
    **PROPOSE_SKILL_CHAIN_TOOL_HANDLERS,
    **REVISE_SKILL_CHAIN_TOOL_HANDLERS,
```

- [ ] **Step 6: Run registration test to verify it passes**

```bash
conda run -n ai pytest tests/test_skill_chain_phase2.py -v 2>&1 | tail -10
```

Expected: 30 passed.

- [ ] **Step 7: Smoke-check tool registration manually**

```bash
conda run -n ai python -c "
from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
names = {(e.get('function') or {}).get('name') for e in TOOL_DEFINITIONS if isinstance(e, dict)}
for n in ['propose_skill_chain', 'revise_skill_chain', 'skill_chain']:
    assert n in names, f'{n} missing from TOOL_DEFINITIONS'
    assert n in _TOOL_HANDLERS, f'{n} missing from _TOOL_HANDLERS'
print('OK: propose_skill_chain + revise_skill_chain + Phase 1 skill_chain all registered')
"
```

Expected: `OK: propose_skill_chain + revise_skill_chain + Phase 1 skill_chain all registered`

- [ ] **Step 8: Add smoke imports to smoke_test_startup.py**

In `scripts/smoke_test_startup.py`, find the Curiosity-budget smoke block (added earlier today). Add right after the closing `except Exception: traceback.print_exc()` of that block:

```python
        # Skill Chain Phase 2 — AGI track #10 (added 2026-05-12)
        try:
            from core.tools.skill_chain_propose_tool import (  # noqa: F401
                _exec_propose_skill_chain,
                _build_propose_prompt,
                _parse_propose_response,
                PROPOSE_SKILL_CHAIN_TOOL_DEFINITIONS,
                PROPOSE_SKILL_CHAIN_TOOL_HANDLERS,
            )
            from core.tools.skill_chain_revise_tool import (  # noqa: F401
                _exec_revise_skill_chain,
                REVISE_SKILL_CHAIN_TOOL_DEFINITIONS,
                REVISE_SKILL_CHAIN_TOOL_HANDLERS,
            )
            from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
            _sc2_names = {
                (e.get("function") or {}).get("name")
                for e in TOOL_DEFINITIONS if isinstance(e, dict)
            }
            for _n in ("propose_skill_chain", "revise_skill_chain"):
                if _n not in _sc2_names:
                    raise RuntimeError(f"{_n} missing from TOOL_DEFINITIONS")
                if _n not in _TOOL_HANDLERS:
                    raise RuntimeError(f"{_n} missing from _TOOL_HANDLERS")
            # Phase 1 must still be present (backwards-compat check)
            if "skill_chain" not in _sc2_names:
                raise RuntimeError("Phase 1 skill_chain missing — regression!")
        except Exception:
            traceback.print_exc()
```

- [ ] **Step 9: Run all affected test suites — verify no regression**

```bash
conda run -n ai pytest tests/test_skill_chain_phase2.py tests/test_curiosity_budget.py tests/test_plan_revision.py tests/test_multistep_planner.py tests/test_tool_invention.py tests/test_world_model_loop.py 2>&1 | tail -12
```

Expected: all green (30 + 30 + 19 + 28 + 20 + 29 = 156 tests).

If `tests/tools/test_skill_chain.py` (Phase 1 tests) exists, also run it:

```bash
conda run -n ai pytest tests/tools/test_skill_chain.py 2>&1 | tail -5
```

Expected: all Phase 1 skill_chain tests still green.

- [ ] **Step 10: Run smoke test**

```bash
conda run -n ai python scripts/smoke_test_startup.py 2>&1 | tail -20
```

Expected: no tracebacks; smoke completes.

- [ ] **Step 11: Production probe — verify both tools listed + Phase 1 intact**

```bash
conda run -n ai python -c "
from core.tools.simple_tools import TOOL_DEFINITIONS
names = {(e.get('function') or {}).get('name') for e in TOOL_DEFINITIONS if isinstance(e, dict)}
for n in ('propose_skill_chain', 'revise_skill_chain', 'skill_chain'):
    assert n in names
print(f'OK: 3 skill-chain tools live (Phase 1 + Phase 2)')

# Confirm cheap-lane still callable
from core.services.cheap_provider_runtime import execute_public_safe_cheap_lane
print('OK: cheap-lane import works')

# Confirm prior AGI tracks unaffected
from core.services.plan_proposals import revise_plan
from core.services.world_model_signal_tracking import record_runtime_world_model_prediction
from core.services.curiosity_budget import curiosity_enabled
print('OK: all 4 prior AGI tracks still callable')
"
```

Expected: 3 OK lines.

- [ ] **Step 12: Schedule 30-day review**

```bash
conda run -n ai python -c "
from core.services.scheduled_tasks import push_scheduled_task
focus = (
    'Skill Chain Phase 2 (AGI track #10) — 30-day review: '
    'count propose_skill_chain calls per day; '
    'confidence-fordeling — klumper det sig ved 0.9 (overoptimistisk) eller 0.5 (usikker)? '
    'proposal-to-execution rate — hvor ofte koerer Jarvis et forslag uaendret inden 5 min? '
    'revision_context split — pre_execution vs mid_chain fordeling. '
    'tom-kaede-rate — hvor ofte returnerer cheap-lane plan=[]? Hvis >40%, prompt for restriktiv. '
    'cost — faktisk maanedlig cheap-lane cost. '
    'apophenia-tegn — laes 10 rationale-felter, opfundne kaeder? '
    'Beslutninger: hvis confidence altid 0.9 -> juster prompt; '
    'hvis pre_execution-revision-rate >50%% -> proposer-kvalitet er lav, overvej skill_gate pre-filter (c hybrid); '
    'hvis mid_chain almindeligt -> tilfoej completed_so_far i Phase 2.1; '
    'hvis tom-kaede stabilt hoej -> juster prompt eller reducer katalog-stoerrelse.'
)
r = push_scheduled_task(focus=focus, delay_minutes=30*24*60, source='skill_chain_phase2')
print(r['task_id'], 'run_at=', r['run_at'])
"
```

- [ ] **Step 13: Commit + restart**

```bash
git add core/tools/simple_tools.py scripts/smoke_test_startup.py tests/test_skill_chain_phase2.py
git commit -m "chore(skill-chain-phase2): register tools + smoke imports + 30-day review"
sudo -n systemctl daemon-reload 2>/dev/null || true
sudo -n systemctl restart jarvis-runtime jarvis-api && sleep 6 && sudo -n journalctl -u jarvis-runtime --since "30 seconds ago" -p err 2>&1 | tail -10
```

Expected: no errors.

---

## Self-review

**Spec coverage:**

| Spec section | Task(s) |
|---|---|
| Settings flag `skill_chain_phase2_enabled` (master killswitch) | Task 1 |
| `propose_skill_chain` tool — killswitch | Tasks 2, 3 |
| `propose_skill_chain` — task_description validation (≥10 chars) | Task 2 |
| `propose_skill_chain` — prompt builder (~2-3k tokens, fuld katalog) | Task 2 |
| `propose_skill_chain` — tom-kæde-fallback instruction in prompt | Task 2 (step 7) + Task 3 (parser accepts []) |
| `propose_skill_chain` — defensive JSON parser (markdown fence-tolerant) | Task 2 (steps 9-11) |
| `propose_skill_chain` — confidence range [0,1] validation | Task 2 (parser) |
| `propose_skill_chain` — plan length 0 or 2-5 validation | Task 2 (parser) |
| `propose_skill_chain` — skill existence (alt-eller-intet) | Task 3 |
| `propose_skill_chain` — cheap-lane exception handling | Task 3 |
| `propose_skill_chain` — cognitive_skill_chain.proposed event | Task 3 |
| Event payload — task_excerpt ≤ 120 chars (PII bound) | Task 3 |
| Event payload — rationale_length NOT text | Task 3 |
| `revise_skill_chain` tool — killswitch | Task 4 |
| `revise_skill_chain` — reason ≥ 10 chars validation | Task 4 |
| `revise_skill_chain` — revision_context ∈ {pre_execution, mid_chain} | Task 4 |
| `revise_skill_chain` — new_plan 2-5 entries | Task 4 |
| `revise_skill_chain` — alt-eller-intet skill validation (genbrug Phase 1) | Task 4 |
| `revise_skill_chain` — genbrug `_build_combined_instructions` from Phase 1 | Task 4 |
| `revise_skill_chain` — cognitive_skill_chain.revised event with revision_context | Task 4 |
| Tool registration via simple_tools splat | Task 5 (steps 3-5) |
| Smoke imports | Task 5 (step 8) |
| 30-day review schedule | Task 5 (step 12) |
| Restart verification | Task 5 (step 13) |
| Backwards-compat: Phase 1 skill_chain uændret | Task 5 (steps 7, 9, 11 — explicit checks) |
| Defensive event-publish (try/except) | Tasks 3, 4 (`_publish_*_event` helpers) |

No spec gaps.

**Placeholder scan:** No TBD/TODO. All code blocks concrete. All commands have expected output.

**Type consistency:**
- `_exec_propose_skill_chain(args: dict[str, Any]) -> dict[str, Any]` — Tasks 2, 3
- `_build_propose_prompt(*, task_description: str, catalog: list[dict[str, Any]]) -> str` — Task 2
- `_parse_propose_response(text: str) -> dict[str, Any]` — Tasks 2, 3
- `_publish_propose_event(*, plan, confidence, rationale_length, model_used, provider_used, task_excerpt) -> None` — Task 3
- `_exec_revise_skill_chain(args: dict[str, Any]) -> dict[str, Any]` — Task 4
- `_publish_revise_event(*, new_plan, reason, revision_context, instructions_length) -> None` — Task 4
- `_phase2_enabled() -> bool` — same name in both new modules (consistent)
- Constants reused: `_MIN_PLAN_LEN=2`, `_MAX_PLAN_LEN=5` in both new modules
- Tool names: `propose_skill_chain` and `revise_skill_chain` used consistently in defs, handlers, tests, smoke probe

**Backwards-compat verified:**
- Phase 1 `skill_chain_tool.py` not modified — confirmed by Read; we IMPORT from it
- Phase 1 `skill_chain` tool still registered (Task 5 step 1 test, step 7 probe, step 11 probe)
- Killswitch=False reverter alt: both tools error "disabled"
- No new event family — reuses existing `cognitive_skill_chain` (Phase 1)
- No DB schema changes, no new daemons
- All 4 prior AGI tracks tested for callability (Task 5 step 11)
- Existing 50+ skills untouched (we only READ catalog, never modify)
- `skill_gate` `chain_candidates`/`chain_hint` not touched
