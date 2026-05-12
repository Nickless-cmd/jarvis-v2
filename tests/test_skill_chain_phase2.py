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
    assert '"plan"' in prompt
    assert '"confidence"' in prompt
    assert '"rationale"' in prompt


def test_build_prompt_includes_empty_plan_fallback_instruction(clean_state):
    from core.tools.skill_chain_propose_tool import _build_propose_prompt
    prompt = _build_propose_prompt(task_description="task here long enough", catalog=[])
    assert "[]" in prompt or "tom" in prompt.lower() or "empty" in prompt.lower()


def test_parse_response_valid_json(clean_state):
    from core.tools.skill_chain_propose_tool import _parse_propose_response
    text = '{"plan": ["a", "b"], "rationale": "because", "confidence": 0.7}'
    result = _parse_propose_response(text)
    assert result["status"] == "ok"
    assert result["plan"] == ["a", "b"]
    assert result["confidence"] == 0.7
    assert result["rationale"] == "because"


def test_parse_response_empty_plan_is_valid(clean_state):
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
