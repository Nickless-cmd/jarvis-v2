from __future__ import annotations

from types import SimpleNamespace


def test_past_context_router_calls_recall_only_for_context_cues(monkeypatch):
    from core.services import past_context_router as pcr
    import core.services.recall as recall_mod

    calls = []

    def fake_recall(query, **kwargs):
        calls.append((query, kwargs))
        return {
            "results": [
                {"source": "chat", "text": "Vi besluttede at bruge recall først."},
            ],
        }

    monkeypatch.setattr(recall_mod, "recall", fake_recall)
    assert pcr.build_past_context_section("kan du huske hvad vi besluttede?") \
        == "Relevant tidligere kontekst:\n- [chat] Vi besluttede at bruge recall først."
    assert calls and calls[0][1]["sources"] == ["session_summary", "chat"]
    assert pcr.build_past_context_section("hej") == ""


def test_memory_answer_gate_keeps_only_substantive_matches():
    from core.services.prompt_sections.memory_selection import (
        _filter_answer_changing_memory,
        memory_could_change_answer,
    )

    assert memory_could_change_answer("hvad besluttede vi om DeepSeek cache?", "DeepSeek cache skal ligge stabilt")
    assert not memory_could_change_answer("hvad er status?", "Jarvis skal være hjælpsom")
    assert _filter_answer_changing_memory(
        "brug Jarvis brain",
        ["generisk note", "Jarvis brain bruger cosine floor"],
    ) == ["Jarvis brain bruger cosine floor"]


def test_tool_routing_hint_prefers_personal_tools_before_web():
    from core.tools.tool_scoping import preferred_tools_for_user_message, tool_routing_hint

    assert preferred_tools_for_user_message("hvad var vores beslutning?")[0] == "recall"
    assert preferred_tools_for_user_message("find seneste nyheder på web")[0] == "web_search"
    assert "før web_search" in tool_routing_hint("kan du huske min plan?")


def test_post_tool_answer_guard_flags_hollow_tool_answers():
    from core.services.post_tool_answer_guard import (
        is_hollow_post_tool_answer,
        should_replace_with_synthesis,
    )

    exchanges = [SimpleNamespace(tool_calls=[{"name": "read_file"}])]
    assert is_hollow_post_tool_answer("done", exchanges)
    assert is_hollow_post_tool_answer("", exchanges)
    assert not is_hollow_post_tool_answer("Jeg læste filen og fandt fejlen.", exchanges)
    assert should_replace_with_synthesis("done", "Jeg læste filen og fandt fejlen.")


def test_skill_gate_keeps_borderline_match_summary_only(monkeypatch):
    from core.tools import skill_gate_tool
    from core.services import skill_engine

    monkeypatch.setattr(
        skill_gate_tool,
        "_suggest_skills_for_query",
        lambda *a, **k: [{"name": "research", "score": 0.35}],
    )
    monkeypatch.setattr(skill_engine, "record_skill_usage", lambda *a, **k: None)
    monkeypatch.setattr(skill_engine, "get_skill_instructions", lambda name: {
        "status": "ok",
        "instructions": "FULL INSTRUCTIONS",
        "description": "Research helper",
        "use_when": "Use for research.",
        "tags": ["research"],
    })
    monkeypatch.setattr(
        "core.runtime.settings.load_settings",
        lambda: SimpleNamespace(skill_gate_enabled=True),
    )

    result = skill_gate_tool._exec_skill_gate({"query": "research this"})
    assert result["mode"] == "suggested"
    assert result["instructions"] == ""
    assert result["instructions_loaded"] is False
    assert "Research helper" in result["skill_summary"]

    full = skill_gate_tool._exec_skill_gate({"query": "research this", "load_full": True})
    assert full["instructions"] == "FULL INSTRUCTIONS"
    assert full["instructions_loaded"] is True


def test_prompt_section_impact_observes_last_prompt_answer(monkeypatch):
    from core.services import prompt_section_impact as psi
    import core.eventbus.bus as bus

    events = []
    monkeypatch.setattr(bus.event_bus, "publish", lambda name, payload: events.append((name, payload)))

    psi.remember_prompt_sections(
        session_id="s1",
        sections=[("memory", "DeepSeek cache boundary must stay stable")],
    )
    impacts = psi.observe_last_prompt_answer_impact(
        session_id="s1",
        run_id="r1",
        answer_text="The DeepSeek cache boundary stayed stable.",
    )
    assert impacts[0]["impact_score"] > 0
    assert events[0][0] == "prompt.section_answer_impact"
