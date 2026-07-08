---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Lag #4 — Skill Chain, Phase 1: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `skill_chain` tool that lets Jarvis chain 2-5 skills sequentially with C-format combined instructions, alt-eller-intet pre-validation, and discovery via skill_gate's new `chain_candidates`/`chain_hint` fields.

**Architecture:** New synchronous tool wrapping skill_engine's existing skill_exists/get_skill_instructions. Atomic pre-validation. Combined instructions = step-headers + verbatim SKILL.md content + closing line. skill_gate extension adds two pure-additive fields (no breaking changes). Eventbus carries metadata only (no PII). Master kill-switch `skill_chain_enabled`. No DB tables, no daemons, no runtime-state.

**Tech Stack:** Python 3.11, eventbus, existing skill_engine infrastructure.

**Spec:** `docs/superpowers/specs/2026-05-10-skill-chain-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `core/tools/skill_chain_tool.py` | Tool definition + `_exec_skill_chain` handler + private helpers (`_validate_plan_existence`, `_build_combined_instructions`, `_publish_chain_event`, `_build_note`) |
| `tests/tools/test_skill_chain.py` | Tool tests: validation paths, build pattern, kill-switch, eventbus |
| `tests/tools/test_skill_gate_chain_candidates.py` | Gate-extension tests: chain_candidates compute, chain_hint format |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | New flag `skill_chain_enabled: bool = True` |
| `core/eventbus/events.py` | Add `cognitive_skill_chain` to `ALLOWED_EVENT_FAMILIES` |
| `core/tools/skill_gate_tool.py` | Add 2 helpers (`_build_chain_candidates`, `_build_chain_hint`) + inject `chain_candidates`/`chain_hint` into all return paths |
| `core/tools/simple_tools.py` | Register `skill_chain` in TOOL_DEFINITIONS + handler map |
| `scripts/smoke_test_startup.py` | Verify tool importable + registered |

### Untouched / reused (no changes)

- `core/services/skill_engine.py` — reuse `skill_exists`, `get_skill_instructions`, `list_skills`
- `core/tools/skill_engine_tools.py` — reuse `_suggest_skills_for_query`
- No DB tables, no daemons, no prompt_contract injection
- No runtime-state mutations

---

## Spec deltas confirmed during planning

1. **Tool registration site** — Verified via `grep "SKILL_GATE_TOOL"` in simple_tools.py: imports at lines 475-476, splat into TOOL_DEFINITIONS at 2318, merge into _TOOL_HANDLERS at 6181. We mirror this pattern exactly for SKILL_CHAIN_TOOL_DEFINITIONS / SKILL_CHAIN_TOOL_HANDLERS.

2. **`get_skill_instructions` return shape** — Verified: returns `{"status": "ok", "skill_name": ..., "instructions": ...}` on success, `{"status": "error", "error": ...}` on missing skill. The `instructions` key carries the SKILL.md body verbatim (post-frontmatter).

3. **Test fixture pattern** — Reuse `isolated_skills_root` style from existing tests/test_skill_engine.py: monkeypatch `SKILLS_ROOT` to a tmp dir, write fake SKILL.md files, call `reload_skills()`. We add similar fixture in our new test files.

4. **Eventbus subscriber** — No existing subscriber listens for `cognitive_skill_chain.*`. We publish for future Mission Control consumers; nothing breaks if no one listens.

5. **No temperature integration** — Out of scope. skill_chain is stateless tool-call; user_temperature_engine is consumed by prompt_contract, not by tools.

---

## Task 1: Settings flag + event family

**Files:**
- Modify: `core/runtime/settings.py`
- Modify: `core/eventbus/events.py`

- [ ] **Step 1: Add settings flag**

In `core/runtime/settings.py`, add right after `user_temperature_llm_max_response_tokens` (or wherever the most recent flag block ends; place adjacent to `dream_bias_*` block):

```python
    # ── Skill chain (Lag #4 — added 2026-05-10) ────────────────────────
    # Master kill-switch for skill_chain tool. When False, the tool returns
    # a "disabled" stub immediately. The tool stays in the schema so the
    # model can still call it; it just no-ops.
    skill_chain_enabled: bool = True
```

- [ ] **Step 2: Wire default into load_settings**

In `core/runtime/settings.py`, find the `load_settings` function and add this line after the `user_temperature_llm_max_response_tokens=int(...)` block:

```python
        skill_chain_enabled=bool(
            data.get("skill_chain_enabled", defaults.skill_chain_enabled)
        ),
```

- [ ] **Step 3: Add event family**

In `core/eventbus/events.py`, add to `ALLOWED_EVENT_FAMILIES` (next to `cognitive_temperature` or `cognitive_dream_bias`):

```python
    "cognitive_skill_chain",  # skill_chain executions (added 2026-05-10)
```

- [ ] **Step 4: Verify**

```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings, load_settings
from core.eventbus.events import ALLOWED_EVENT_FAMILIES
s = RuntimeSettings()
assert s.skill_chain_enabled is True
assert 'cognitive_skill_chain' in ALLOWED_EVENT_FAMILIES
loaded = load_settings()
assert loaded.skill_chain_enabled is True
print('ok')
"
```
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add core/runtime/settings.py core/eventbus/events.py
git commit -m "feat(skill-chain): settings flag + cognitive_skill_chain event family"
```

---

## Task 2: skill_chain_tool.py — tool implementation

**Files:**
- Create: `core/tools/skill_chain_tool.py`
- Create: `tests/tools/test_skill_chain.py`

This task implements the full tool: definition, handler, validation, combined-instructions builder, eventbus publication.

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/test_skill_chain.py`:

```python
"""Tests for the skill_chain tool."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def isolated_skills_root(monkeypatch, tmp_path):
    """Point SKILLS_ROOT at a fresh tmp dir + reset registry."""
    from core.services import skill_engine
    sk_root = tmp_path / "skills"
    sk_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(skill_engine, "SKILLS_ROOT", sk_root)
    monkeypatch.setattr(skill_engine, "_registry", {})
    monkeypatch.setattr(skill_engine, "_last_scan", "")
    return sk_root


def _write_skill(root: Path, name: str, body: str = "Test instructions.") -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test skill {name}\n---\n\n{body}\n",
        encoding="utf-8",
    )


# ── Validation tests ───────────────────────────────────────────────


def test_skill_chain_rejects_non_list_plan(isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    result = _exec_skill_chain({"plan": "not-a-list"})
    assert result["status"] == "rejected"
    assert "must be a list" in result["reason"]


def test_skill_chain_rejects_too_short_plan(isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    result = _exec_skill_chain({"plan": ["only-one"]})
    assert result["status"] == "rejected"
    assert "at least 2" in result["reason"]


def test_skill_chain_rejects_too_long_plan(isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    result = _exec_skill_chain({"plan": ["a", "b", "c", "d", "e", "f"]})
    assert result["status"] == "rejected"
    assert "max length of 5" in result["reason"]


def test_skill_chain_rejects_empty_string_entry(isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    result = _exec_skill_chain({"plan": ["valid", "  "]})
    assert result["status"] == "rejected"
    assert "non-empty strings" in result["reason"]


def test_skill_chain_rejects_non_string_entry(isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    result = _exec_skill_chain({"plan": ["valid", 42]})
    assert result["status"] == "rejected"


def test_skill_chain_rejects_unknown_skills(isolated_skills_root):
    """Pre-validation atomic — missing list contains all unknown names."""
    from core.tools.skill_chain_tool import _exec_skill_chain
    from core.services import skill_engine

    _write_skill(isolated_skills_root, "real-skill")
    skill_engine.reload_skills()

    result = _exec_skill_chain({"plan": ["real-skill", "fake-foo", "fake-bar"]})
    assert result["status"] == "rejected"
    assert result["reason"] == "unknown skills in plan"
    assert set(result["missing"]) == {"fake-foo", "fake-bar"}
    assert "real-skill" in result["available"]


# ── Kill-switch ────────────────────────────────────────────────────


def test_skill_chain_returns_disabled_when_killswitched(monkeypatch, isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain

    class _FakeSettings:
        skill_chain_enabled = False

    monkeypatch.setattr(
        "core.tools.skill_chain_tool.load_settings",
        lambda: _FakeSettings(),
    )
    result = _exec_skill_chain({"plan": ["a", "b"]})
    assert result["status"] == "disabled"


# ── Successful chain ───────────────────────────────────────────────


def test_skill_chain_builds_combined_instructions(isolated_skills_root):
    """Happy path: 2 skills exist, returns combined C-format instructions."""
    from core.tools.skill_chain_tool import _exec_skill_chain
    from core.services import skill_engine

    _write_skill(isolated_skills_root, "fact-checker", "Verify facts here.")
    _write_skill(isolated_skills_root, "markdown-helper", "Format as markdown.")
    skill_engine.reload_skills()

    result = _exec_skill_chain({
        "plan": ["fact-checker", "markdown-helper"],
        "rationale": "fact-check then format",
    })
    assert result["status"] == "ok"
    assert result["chain"] == ["fact-checker", "markdown-helper"]
    assert result["step_count"] == 2

    instructions = result["instructions"]
    # C-format expectations
    assert "[skill_chain — 2 steps]" in instructions
    assert "## Step 1 of 2: fact-checker" in instructions
    assert "Verify facts here." in instructions
    assert "## Step 2 of 2: markdown-helper" in instructions
    assert "Format as markdown." in instructions
    assert "When you finish step 1, continue to step 2" in instructions


def test_skill_chain_normalizes_whitespace_in_names(isolated_skills_root):
    """Plan entries are stripped before validation."""
    from core.tools.skill_chain_tool import _exec_skill_chain
    from core.services import skill_engine

    _write_skill(isolated_skills_root, "fact-checker")
    _write_skill(isolated_skills_root, "markdown-helper")
    skill_engine.reload_skills()

    result = _exec_skill_chain({
        "plan": ["  fact-checker  ", " markdown-helper"],
    })
    assert result["status"] == "ok"
    assert result["chain"] == ["fact-checker", "markdown-helper"]


def test_skill_chain_allows_duplicate_skills_in_plan(isolated_skills_root):
    """Same skill twice is allowed (e.g. fact-check two documents)."""
    from core.tools.skill_chain_tool import _exec_skill_chain
    from core.services import skill_engine

    _write_skill(isolated_skills_root, "fact-checker")
    skill_engine.reload_skills()

    result = _exec_skill_chain({"plan": ["fact-checker", "fact-checker"]})
    assert result["status"] == "ok"
    assert result["step_count"] == 2


def test_skill_chain_handles_max_length(isolated_skills_root):
    """5 skills is the cap and should work."""
    from core.tools.skill_chain_tool import _exec_skill_chain
    from core.services import skill_engine

    for i in range(5):
        _write_skill(isolated_skills_root, f"skill-{i}")
    skill_engine.reload_skills()

    result = _exec_skill_chain({
        "plan": [f"skill-{i}" for i in range(5)],
    })
    assert result["status"] == "ok"
    assert result["step_count"] == 5


# ── Soft cap on instructions size ──────────────────────────────────


def test_skill_chain_warns_on_oversize_instructions(isolated_skills_root):
    """Soft cap (32k chars) produces warning in note, not rejection."""
    from core.tools.skill_chain_tool import _exec_skill_chain
    from core.services import skill_engine

    big_body = "x" * 20_000  # 20k each → 40k total → over 32k cap
    _write_skill(isolated_skills_root, "big-1", body=big_body)
    _write_skill(isolated_skills_root, "big-2", body=big_body)
    skill_engine.reload_skills()

    result = _exec_skill_chain({"plan": ["big-1", "big-2"]})
    assert result["status"] == "ok"  # not rejected
    assert "soft cap" in result["note"].lower() or "32000" in result["note"]


# ── Eventbus publication ───────────────────────────────────────────


def test_skill_chain_publishes_event_on_success(monkeypatch, isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain
    from core.services import skill_engine

    _write_skill(isolated_skills_root, "fact-checker")
    _write_skill(isolated_skills_root, "markdown-helper")
    skill_engine.reload_skills()

    published_events = []

    def _capture(family, payload):
        published_events.append((family, payload))

    monkeypatch.setattr(
        "core.tools.skill_chain_tool.event_bus",
        type("MockBus", (), {"publish": staticmethod(_capture)})(),
    )

    _exec_skill_chain({
        "plan": ["fact-checker", "markdown-helper"],
        "rationale": "this should not appear in event payload",
    })

    assert len(published_events) == 1
    family, payload = published_events[0]
    assert family == "cognitive_skill_chain.executed"
    assert payload["plan"] == ["fact-checker", "markdown-helper"]
    assert payload["step_count"] == 2
    # Rationale text MUST NOT be in the payload (PII protection)
    assert "this should not appear" not in str(payload)
    assert payload["rationale_provided"] is True


def test_skill_chain_does_not_publish_on_rejection(monkeypatch, isolated_skills_root):
    from core.tools.skill_chain_tool import _exec_skill_chain

    published = []
    monkeypatch.setattr(
        "core.tools.skill_chain_tool.event_bus",
        type("MockBus", (), {"publish": staticmethod(lambda f, p: published.append((f, p)))})(),
    )

    _exec_skill_chain({"plan": ["only-one"]})  # rejected
    assert len(published) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/tools/test_skill_chain.py -v
```
Expected: ImportError on `core.tools.skill_chain_tool`.

- [ ] **Step 3: Implement the tool**

Create `core/tools/skill_chain_tool.py`:

```python
"""skill_chain tool — Lag #4 sequential skill composition.

Synchronous tool. Accepts a plan (ordered list of 2-5 skill names),
pre-validates atomically that all named skills exist, then builds a
C-format combined instructions package: step-numbered headers + verbatim
SKILL.md instructions + closing line that binds steps.

No DB writes, no daemon, no runtime-state. Pure validation + lookup +
string assembly.

Discovery: skill_gate's chain_candidates/chain_hint fields surface
viable chains. Tool description guides Jarvis when to chain vs invoke.
"""
from __future__ import annotations

import logging
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.settings import load_settings
from core.services import skill_engine

logger = logging.getLogger(__name__)


# Soft cap on combined instructions (chars). Above this we emit a warning
# but still execute. ~8k tokens worth — well under model context window
# but heavy enough to warrant attention.
_SOFT_INSTRUCTIONS_CAP = 32000


def _validate_plan_existence(plan: list[str]) -> list[str]:
    """Return list of missing skill names (empty list if all exist)."""
    return [name for name in plan if not skill_engine.skill_exists(name)]


def _build_combined_instructions(plan: list[str]) -> str:
    """Header-format combination — instructions verbatim, step-headers added."""
    n = len(plan)
    parts = [f"[skill_chain — {n} steps]\n"]
    for i, name in enumerate(plan, start=1):
        skill_data = skill_engine.get_skill_instructions(name)
        if skill_data.get("status") != "ok":
            # Defensive — pre-validation should have caught this
            parts.append(f"\n## Step {i} of {n}: {name} (UNAVAILABLE)\n")
            continue
        instructions = str(skill_data.get("instructions") or "").strip()
        parts.append(f"\n## Step {i} of {n}: {name}\n")
        parts.append(instructions)
    parts.append(
        "\n\nWhen you finish step 1, continue to step 2 using your step-1 "
        "output as context. Each subsequent step builds on prior output."
    )
    return "\n".join(parts)


def _build_note(plan: list[str], instructions: str) -> str:
    """Build the user-visible note. Warns when over soft cap."""
    if len(instructions) > _SOFT_INSTRUCTIONS_CAP:
        return (
            f"⚠ Combined instructions are {len(instructions)} chars "
            f"(soft cap {_SOFT_INSTRUCTIONS_CAP}). Consider shorter chain. "
            "Execute step 1 first, then continue to step 2 using your "
            "step-1 output as context."
        )
    return (
        f"Skills loaded in chain: {len(plan)} steps. Execute step 1 first, "
        "then continue to step 2 using your step-1 output as context. "
        "Each skill's instructions are below."
    )


def _publish_chain_event(
    *,
    plan: list[str],
    instructions_length: int,
    rationale_provided: bool,
    status: str,
) -> None:
    """Publish to eventbus. Metadata only — NO rationale text."""
    try:
        event_bus.publish(
            "cognitive_skill_chain.executed",
            {
                "plan": plan,
                "step_count": len(plan),
                "instructions_length": instructions_length,
                "rationale_provided": rationale_provided,
                "status": status,
            },
        )
    except Exception as exc:
        logger.debug("skill_chain: publish failed: %s", exc)


def _exec_skill_chain(args: dict[str, Any]) -> dict[str, Any]:
    """Validate plan, build combined instructions, return.

    All-or-nothing pre-validation: if any skill in plan is missing, the
    whole call is rejected with the missing list (no partial execution).
    """
    # 1. Kill-switch
    try:
        if not load_settings().skill_chain_enabled:
            return {
                "status": "disabled",
                "note": "skill_chain is disabled in runtime settings",
            }
    except Exception:
        # Settings unavailable — fail open
        pass

    # 2. Required arg + type
    plan = args.get("plan")
    if not isinstance(plan, list):
        return {"status": "rejected", "reason": "plan must be a list"}

    # 3. Length bounds
    if len(plan) < 2:
        return {
            "status": "rejected",
            "reason": "plan must have at least 2 skills",
        }
    if len(plan) > 5:
        return {"status": "rejected", "reason": "plan exceeds max length of 5"}

    # 4. Type check entries
    if not all(isinstance(s, str) and s.strip() for s in plan):
        return {
            "status": "rejected",
            "reason": "all plan entries must be non-empty strings",
        }

    # 5. Normalize names (strip whitespace)
    normalized_plan = [s.strip() for s in plan]

    # 6. Pre-validate ALL skills exist (atomic — alt-eller-intet)
    missing = _validate_plan_existence(normalized_plan)
    if missing:
        try:
            available = [s["name"] for s in skill_engine.list_skills()]
        except Exception:
            available = []
        return {
            "status": "rejected",
            "reason": "unknown skills in plan",
            "missing": missing,
            "available": available,
        }

    # 7. Build combined instructions
    instructions = _build_combined_instructions(normalized_plan)

    # 8. Publish event (metadata only — no rationale text)
    _publish_chain_event(
        plan=normalized_plan,
        instructions_length=len(instructions),
        rationale_provided=bool(args.get("rationale")),
        status="ok",
    )

    # 9. Return success
    return {
        "status": "ok",
        "chain": normalized_plan,
        "step_count": len(normalized_plan),
        "instructions": instructions,
        "instructions_full_length": len(instructions),
        "note": _build_note(normalized_plan, instructions),
    }


SKILL_CHAIN_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "skill_chain",
            "description": (
                "Chain multiple skills in sequence for tasks that require "
                "more than one skill (e.g. fact-check then summarize, "
                "research then format). Each step's instructions are loaded "
                "into context in order, with clear step-headers. You execute "
                "step 1, then continue to step 2 using your step-1 output as "
                "context, and so on. Use when skill_gate returns multiple "
                "close-matching candidates, or when the task naturally has "
                "multiple phases. For single-skill tasks, use skill_invoke "
                "instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plan": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Ordered list of skill names. Min 2, max 5. "
                            "Each name must exist (verified before execution)."
                        ),
                        "minItems": 2,
                        "maxItems": 5,
                    },
                    "rationale": {
                        "type": "string",
                        "description": (
                            "Optional: short note on why this chain. "
                            "Logged in tool-call but not persisted to events."
                        ),
                    },
                },
                "required": ["plan"],
            },
        },
    },
]


SKILL_CHAIN_TOOL_HANDLERS: dict[str, Any] = {
    "skill_chain": _exec_skill_chain,
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/tools/test_skill_chain.py -v
```
Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add core/tools/skill_chain_tool.py tests/tools/test_skill_chain.py
git commit -m "feat(skill-chain): skill_chain_tool.py — atomic pre-validation + C-format builder"
```

---

## Task 3: skill_gate_tool.py — chain_candidates + chain_hint extension

**Files:**
- Modify: `core/tools/skill_gate_tool.py`
- Create: `tests/tools/test_skill_gate_chain_candidates.py`

Pure-additive change. Existing skill_gate output keys are preserved exactly.

- [ ] **Step 1: Write the failing tests**

Create `tests/tools/test_skill_gate_chain_candidates.py`:

```python
"""Tests for skill_gate's new chain_candidates / chain_hint fields."""
from __future__ import annotations

import pytest


# ── Pure helpers ───────────────────────────────────────────────────


def test_build_chain_candidates_empty_input():
    from core.tools.skill_gate_tool import _build_chain_candidates
    assert _build_chain_candidates([]) == []
    assert _build_chain_candidates([{"name": "x", "score": 0.5}]) == []


def test_build_chain_candidates_top_below_threshold():
    """Top score below 0.30 → no chain candidates (chain doesn't help weak match)."""
    from core.tools.skill_gate_tool import _build_chain_candidates
    suggestions = [
        {"name": "a", "score": 0.20},
        {"name": "b", "score": 0.18},
    ]
    assert _build_chain_candidates(suggestions) == []


def test_build_chain_candidates_only_top_within_window():
    """If only top-1 is within 0.10, no chain candidates returned."""
    from core.tools.skill_gate_tool import _build_chain_candidates
    suggestions = [
        {"name": "a", "score": 0.45},
        {"name": "b", "score": 0.20},  # 0.25 below — outside 0.10 window
    ]
    assert _build_chain_candidates(suggestions) == []


def test_build_chain_candidates_two_close_matches():
    from core.tools.skill_gate_tool import _build_chain_candidates
    suggestions = [
        {"name": "fact-checker", "score": 0.42},
        {"name": "markdown-helper", "score": 0.38},  # within 0.10
        {"name": "deep-research", "score": 0.21},    # outside
    ]
    result = _build_chain_candidates(suggestions)
    assert len(result) == 2
    assert result[0]["name"] == "fact-checker"
    assert result[1]["name"] == "markdown-helper"


def test_build_chain_candidates_three_close_matches():
    """Returns up to top-3 within window."""
    from core.tools.skill_gate_tool import _build_chain_candidates
    suggestions = [
        {"name": "a", "score": 0.40},
        {"name": "b", "score": 0.36},
        {"name": "c", "score": 0.34},
        {"name": "d", "score": 0.20},  # outside
    ]
    result = _build_chain_candidates(suggestions)
    assert len(result) == 3
    assert [r["name"] for r in result] == ["a", "b", "c"]


def test_build_chain_candidates_caps_at_three():
    """Even if 4 are close, return at most 3."""
    from core.tools.skill_gate_tool import _build_chain_candidates
    suggestions = [
        {"name": "a", "score": 0.40},
        {"name": "b", "score": 0.39},
        {"name": "c", "score": 0.38},
        {"name": "d", "score": 0.37},  # within window but cap
    ]
    result = _build_chain_candidates(suggestions)
    assert len(result) == 3


def test_build_chain_hint_empty_returns_empty_string():
    from core.tools.skill_gate_tool import _build_chain_hint
    assert _build_chain_hint([]) == ""


def test_build_chain_hint_renders_skill_names():
    from core.tools.skill_gate_tool import _build_chain_hint
    candidates = [
        {"name": "fact-checker", "score": 0.42},
        {"name": "markdown-helper", "score": 0.38},
    ]
    hint = _build_chain_hint(candidates)
    assert "2 skills matched closely" in hint
    assert "fact-checker" in hint
    assert "markdown-helper" in hint
    assert "skill_chain(plan=" in hint


# ── Gate output integration ────────────────────────────────────────


def test_skill_gate_output_includes_chain_candidates_field(monkeypatch):
    """All gate return paths include chain_candidates and chain_hint."""
    from core.tools import skill_gate_tool

    class _FakeSettings:
        skill_gate_enabled = True
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: _FakeSettings(),
    )
    # Stub suggest with multi-close-match scenario
    monkeypatch.setattr(
        skill_gate_tool, "_suggest_skills_for_query",
        lambda **kw: [
            {"name": "fact-checker", "score": 0.42, "candidate": "x"},
            {"name": "markdown-helper", "score": 0.38, "candidate": "y"},
        ],
    )

    # Stub skill_engine.get_skill_instructions to return ok
    from core.services import skill_engine
    monkeypatch.setattr(
        skill_engine, "get_skill_instructions",
        lambda name: {
            "status": "ok",
            "skill_name": name,
            "description": f"desc {name}",
            "use_when": "",
            "tags": [],
            "instructions": "test instructions",
        },
    )

    result = skill_gate_tool._exec_skill_gate({"query": "fact-check and format"})
    assert "chain_candidates" in result
    assert "chain_hint" in result
    assert len(result["chain_candidates"]) == 2
    assert "fact-checker" in result["chain_hint"]


def test_skill_gate_output_chain_candidates_empty_when_single_match(monkeypatch):
    """Single dominant match → empty chain_candidates."""
    from core.tools import skill_gate_tool

    class _FakeSettings:
        skill_gate_enabled = True
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: _FakeSettings(),
    )
    monkeypatch.setattr(
        skill_gate_tool, "_suggest_skills_for_query",
        lambda **kw: [
            {"name": "youtube-downloader", "score": 0.55, "candidate": "x"},
            {"name": "web-scraper", "score": 0.18, "candidate": "y"},  # outside window
        ],
    )
    from core.services import skill_engine
    monkeypatch.setattr(
        skill_engine, "get_skill_instructions",
        lambda name: {
            "status": "ok",
            "skill_name": name,
            "description": "x",
            "use_when": "",
            "tags": [],
            "instructions": "x",
        },
    )

    result = skill_gate_tool._exec_skill_gate({"query": "download video"})
    assert result["chain_candidates"] == []
    assert result["chain_hint"] == ""


def test_skill_gate_output_chain_candidates_present_in_no_match(monkeypatch):
    """Even when gate returns no_match, chain fields are present (defaulted)."""
    from core.tools import skill_gate_tool

    class _FakeSettings:
        skill_gate_enabled = True
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: _FakeSettings(),
    )
    monkeypatch.setattr(
        skill_gate_tool, "_suggest_skills_for_query",
        lambda **kw: [],  # no match at all
    )

    result = skill_gate_tool._exec_skill_gate({"query": "what's the weather"})
    assert result["gate_result"] == "no_match"
    assert "chain_candidates" in result
    assert "chain_hint" in result
    assert result["chain_candidates"] == []
    assert result["chain_hint"] == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai python -m pytest tests/tools/test_skill_gate_chain_candidates.py -v
```
Expected: failures (helpers don't exist yet, gate output missing fields).

- [ ] **Step 3: Add helpers to skill_gate_tool.py**

In `core/tools/skill_gate_tool.py`, add these two helpers near the top of the file (after imports, before `_exec_skill_gate`):

```python
def _build_chain_candidates(suggestions: list[dict]) -> list[dict]:
    """Return top-3 (max) skills within 0.10 of top score.

    Empty list when:
    - No suggestions
    - Only 1 suggestion exists
    - Top score below 0.30 (weak match — chain doesn't help)
    - Only top-1 was within the 0.10 window
    """
    if not suggestions or len(suggestions) < 2:
        return []
    top_score = float(suggestions[0].get("score") or 0.0)
    if top_score < 0.30:
        return []
    candidates = [
        {"name": s["name"], "score": s["score"]}
        for s in suggestions[:3]
        if float(s.get("score") or 0.0) >= top_score - 0.10
    ]
    if len(candidates) < 2:
        return []
    return candidates


def _build_chain_hint(candidates: list[dict]) -> str:
    """Render human-readable chain suggestion from candidates."""
    if not candidates:
        return ""
    names = [c["name"] for c in candidates]
    plan_repr = ", ".join(f"'{n}'" for n in names)
    n = len(candidates)
    return (
        f"{n} skills matched closely (within 0.10 of top score). "
        f"Consider skill_chain(plan=[{plan_repr}]) "
        "if the task requires multiple steps."
    )
```

- [ ] **Step 4: Inject chain fields into all return paths**

Locate `_exec_skill_gate` in `core/tools/skill_gate_tool.py`. Find the line where suggestions are computed:

```python
    suggestions = _suggest_skills_for_query(
        query=query,
        threshold=0.20,
        max_results=_INTENT_MATCH_MAX_SUGGESTIONS,
    )
```

Add immediately after:

```python
    # Lag #4: compute chain candidates (always, all return paths)
    chain_candidates = _build_chain_candidates(suggestions)
    chain_hint = _build_chain_hint(chain_candidates)
```

Then for **each** return statement in `_exec_skill_gate` (no_match, low_match, error, and the final invoked result), add `chain_candidates` and `chain_hint` to the dict.

For example, the `no_match` return becomes:

```python
    if not suggestions:
        return {
            "status": "ok",
            "gate_result": "no_match",
            "query": query,
            "reason": "no skills matched the query",
            "suggestions": [],
            "note": "No relevant skills found. Proceed with standard workflow.",
            "chain_candidates": chain_candidates,
            "chain_hint": chain_hint,
        }
```

The `low_match` return becomes:

```python
    if best_score < threshold:
        return {
            "status": "ok",
            "gate_result": "low_match",
            "query": query,
            "reason": f"best match '{best_name}' scored {best_score:.2f} — below threshold {threshold:.2f}",
            "suggestions": suggestions,
            "note": (
                f"Closest skill: '{best_name}' ({best_score:.2f}). "
                f"Under threshold — proceed with standard workflow, or request a specific skill."
            ),
            "chain_candidates": chain_candidates,
            "chain_hint": chain_hint,
        }
```

Find the final `return result` at end of the function and add:

```python
    result["chain_candidates"] = chain_candidates
    result["chain_hint"] = chain_hint
    return result
```

For the `disabled` early return at the top of the function (kill-switch), also add `chain_candidates: []` and `chain_hint: ""` so the schema is consistent:

```python
    try:
        from core.runtime.settings import load_settings
        if not load_settings().skill_gate_enabled:
            return {
                "status": "ok",
                "gate_result": "disabled",
                "note": "skill_gate is disabled in runtime settings — proceed with standard workflow.",
                "chain_candidates": [],
                "chain_hint": "",
            }
    except Exception:
        pass
```

For the `skip` early return (no query), do the same:

```python
    if not query:
        return {
            "status": "ok",
            "gate_result": "skip",
            "reason": "no query provided — gate bypassed",
            "note": "Provide a query to check for matching skills.",
            "chain_candidates": [],
            "chain_hint": "",
        }
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
conda run -n ai python -m pytest tests/tools/test_skill_gate_chain_candidates.py -v
```
Expected: 10 passed.

- [ ] **Step 6: Verify existing skill_gate tests still pass (regression check)**

```bash
conda run -n ai python -m pytest tests/services/test_skill_engine.py tests/tools/test_skill_gate_chain_candidates.py -v 2>&1 | tail -10
```
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add core/tools/skill_gate_tool.py tests/tools/test_skill_gate_chain_candidates.py
git commit -m "feat(skill-chain): skill_gate chain_candidates + chain_hint (Phase 1 discovery)"
```

---

## Task 4: Register skill_chain in simple_tools.py

**Files:**
- Modify: `core/tools/simple_tools.py`

Mirrors the SKILL_GATE_TOOL_DEFINITIONS registration pattern exactly.

- [ ] **Step 1: Find skill_gate registration sites**

```bash
grep -n "SKILL_GATE_TOOL" /media/projects/jarvis-v2/core/tools/simple_tools.py
```
Expected output (verified during planning):
```
475:    SKILL_GATE_TOOL_DEFINITIONS,
476:    SKILL_GATE_TOOL_HANDLERS,
2318:    *SKILL_GATE_TOOL_DEFINITIONS,
6181:    **SKILL_GATE_TOOL_HANDLERS,
```

- [ ] **Step 2: Add import**

In `core/tools/simple_tools.py`, find:

```python
from core.tools.skill_gate_tool import (
    SKILL_GATE_TOOL_DEFINITIONS,
    SKILL_GATE_TOOL_HANDLERS,
)
```

Add immediately after:

```python
from core.tools.skill_chain_tool import (
    SKILL_CHAIN_TOOL_DEFINITIONS,
    SKILL_CHAIN_TOOL_HANDLERS,
)
```

- [ ] **Step 3: Add to TOOL_DEFINITIONS splat**

In `core/tools/simple_tools.py`, find the line:

```python
    *SKILL_GATE_TOOL_DEFINITIONS,
```

Add immediately after:

```python
    *SKILL_CHAIN_TOOL_DEFINITIONS,
```

- [ ] **Step 4: Add to handler map merge**

In `core/tools/simple_tools.py`, find the line:

```python
    **SKILL_GATE_TOOL_HANDLERS,
```

Add immediately after:

```python
    **SKILL_CHAIN_TOOL_HANDLERS,
```

- [ ] **Step 5: Verify registration**

```bash
conda run -n ai python -c "
from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
names = []
for td in TOOL_DEFINITIONS:
    if 'function' in td:
        names.append(td['function'].get('name'))
    elif 'name' in td:
        names.append(td['name'])
assert 'skill_chain' in names, 'skill_chain missing from TOOL_DEFINITIONS'
assert 'skill_chain' in _TOOL_HANDLERS, 'skill_chain missing from _TOOL_HANDLERS'
print(f'skill_chain wired ({len(names)} tools registered)')
"
```
Expected: `skill_chain wired (N tools registered)` where N is one more than before.

- [ ] **Step 6: Commit**

```bash
git add core/tools/simple_tools.py
git commit -m "feat(skill-chain): register skill_chain in TOOL_DEFINITIONS + handler map"
```

---

## Task 5: Smoke test extension

**Files:**
- Modify: `scripts/smoke_test_startup.py`

- [ ] **Step 1: Add verification block**

In `scripts/smoke_test_startup.py`, find the dream_bias_active verification block. Add immediately after (or after user_temperature verification, whichever was added last):

```python
        # Verify skill_chain tool registered (Lag #4)
        try:
            from core.tools.skill_chain_tool import (
                SKILL_CHAIN_TOOL_DEFINITIONS,  # noqa: F401
                SKILL_CHAIN_TOOL_HANDLERS,  # noqa: F401
                _exec_skill_chain,  # noqa: F401
            )
            from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
            names = []
            for td in TOOL_DEFINITIONS:
                if "function" in td:
                    names.append(td["function"].get("name"))
                elif "name" in td:
                    names.append(td["name"])
            if "skill_chain" not in names:
                raise RuntimeError("skill_chain not in TOOL_DEFINITIONS")
            if "skill_chain" not in _TOOL_HANDLERS:
                raise RuntimeError("skill_chain not in _TOOL_HANDLERS")
        except Exception:
            traceback.print_exc()
```

- [ ] **Step 2: Run smoke test**

```bash
conda run -n ai python scripts/smoke_test_startup.py
```
Expected: `smoke_test_startup: OK in <N>s`

- [ ] **Step 3: Commit**

```bash
git add scripts/smoke_test_startup.py
git commit -m "test(skill-chain): smoke test verifies skill_chain registration"
```

---

## Task 6: Deploy + day-1 verification

**Files:** none (deployment + observation only)

- [ ] **Step 1: Restart jarvis-runtime**

```bash
sudo systemctl restart jarvis-runtime && sleep 6 && systemctl is-active jarvis-runtime
```
Expected: `active`

- [ ] **Step 2: Check journal for errors**

```bash
journalctl -u jarvis-runtime --since "30 sec ago" --no-pager | grep -iE "skill_chain|error|traceback" | head -10
```
Expected: no tracebacks. Possibly nothing at all (skill_chain is a tool, not a daemon, so it doesn't log on startup beyond the registration count).

- [ ] **Step 3: Verify tool registered in live runtime**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
names = []
for td in TOOL_DEFINITIONS:
    if 'function' in td:
        names.append(td['function'].get('name'))
    elif 'name' in td:
        names.append(td['name'])
print(f'skill_chain registered: {\"skill_chain\" in names}')
print(f'total tools: {len(names)}')
"
```
Expected: `skill_chain registered: True`, total tools count.

- [ ] **Step 4: Force-call skill_chain happy path**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.tools.skill_chain_tool import _exec_skill_chain
result = _exec_skill_chain({
    'plan': ['fact-checker', 'markdown-helper'],
    'rationale': 'test happy path',
})
print('status:', result['status'])
print('chain:', result['chain'])
print('step_count:', result['step_count'])
print('instructions length:', result['instructions_full_length'])
print('first 200 chars:')
print(result['instructions'][:200])
"
```
Expected: `status: ok`, `chain: ['fact-checker', 'markdown-helper']`, instructions starting with `[skill_chain — 2 steps]`.

- [ ] **Step 5: Force-call rejection paths**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.tools.skill_chain_tool import _exec_skill_chain
# Unknown skill
print(_exec_skill_chain({'plan': ['fact-checker', 'fake-skill-foo']}))
print()
# Single skill
print(_exec_skill_chain({'plan': ['fact-checker']}))
"
```
Expected: First call returns `{'status': 'rejected', 'reason': 'unknown skills in plan', 'missing': ['fake-skill-foo'], 'available': [...]}`. Second call returns `{'status': 'rejected', 'reason': 'plan must have at least 2 skills'}`.

- [ ] **Step 6: Verify gate's chain_candidates fires**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.tools.skill_gate_tool import _exec_skill_gate
result = _exec_skill_gate({'query': 'fact-check denne artikel og opsummér i markdown'})
print('skill_name:', result.get('skill_name'))
print('chain_candidates:', result.get('chain_candidates'))
print('chain_hint:', result.get('chain_hint'))
"
```
Expected: chain_candidates non-empty if skill_gate detects two close matches; chain_hint contains the suggested plan.

- [ ] **Step 7: Document day-1 baseline**

Create `docs/superpowers/notes/2026-05-10-skill-chain-day1.md`:

```markdown
# Skill Chain Phase 1 — Day 1 baseline

**Date:** <today>
**Deployed:** <commit SHA from `git rev-parse HEAD`>

## Initial state

- skill_chain registered in TOOL_DEFINITIONS: <yes/no>
- Total tools registered: <count>
- skill_chain_enabled flag: <bool>

## Force-call results

### Happy path (chain of 2 existing skills)
<paste step 4 output>

### Rejection paths
<paste step 5 output>

### Gate chain_candidates
<paste step 6 output>

## Open observations

- First spontaneous skill_chain call (when does Jarvis use it?): <pending>
- Common chain plans observed: <pending>
- chain_hint visibility in real visible-lane runs: <pending>
```

- [ ] **Step 8: Commit baseline**

```bash
git add docs/superpowers/notes/2026-05-10-skill-chain-day1.md
git commit -m "docs(skill-chain): day-1 baseline observations"
```

---

## Task 7: Schedule 30-day review

**Files:** none (uses scheduled_tasks system)

- [ ] **Step 1: Create scheduled task**

```bash
PYTHONPATH=/media/projects/jarvis-v2 conda run -n ai python -c "
from core.services.scheduled_tasks import push_scheduled_task
result = push_scheduled_task(
    focus=(
        'Skill Chain Phase 1 — 30-dages review. Tjek hvor ofte Jarvis '
        'kalder skill_chain spontant, om chain_hint i skill_gate fyrer '
        'og om Jarvis foelger den, plan-stoerrelses-fordeling (2 vs 3 vs 5), '
        'pre-validation rejection-rate. Spec: '
        'docs/superpowers/specs/2026-05-10-skill-chain-design.md '
        '(3 dimensions i succeskriterier). Beslutning: keep, retune '
        'thresholds/cap, eller plan Phase 2 (auto-planner, tool invention, '
        'gate auto-detection, prompt-contract integration).'
    ),
    delay_minutes=30 * 24 * 60,
    source='skill-chain-phase1-deploy',
)
print(result)
"
```
Expected: dict with `task_id` and `run_at` 30 days out.

- [ ] **Step 2: Append task ID to baseline doc**

Append to `docs/superpowers/notes/2026-05-10-skill-chain-day1.md`:

```markdown

## 30-day review scheduled

- Task ID: <task_id from step 1>
- Fires: <run_at timestamp>
- Source: `skill-chain-phase1-deploy`
- Focus: "Skill Chain Phase 1 — 30-dages review. Tjek hvor ofte Jarvis
  kalder skill_chain spontant..."
```

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/notes/2026-05-10-skill-chain-day1.md
git commit -m "docs(skill-chain): schedule 30-day review reminder"
```

---

## Phase 1 done

All 7 tasks complete = Phase 1 deployed and observation scheduled.

**Out of scope for this plan (Phase 2 work):**
- Tool invention (separate plan with sandboxing, governance, audit)
- Auto-planner (LLM-based chain proposal)
- Auto-detection in gate (LLM analysis of query for chain-worthy intent)
- Output-passing schemas (structured skill input/output)
- Chain-history table for outcome tracking
- Skill co-occurrence learning
- Prompt-contract integration (system-prompt explains chaining)
- Per-skill `chain_with` metadata in frontmatter

When the 30-day review fires, evaluate against the 3 success-criteria dimensions in the spec and decide what Phase 2 looks like.
