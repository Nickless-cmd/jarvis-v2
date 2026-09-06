from __future__ import annotations


def test_estimate_section_impact_scores_overlap():
    from core.services.prompt_section_impact import estimate_section_impact

    impact = estimate_section_impact(
        "memory",
        "DeepSeek cache boundary must stay stable",
        "DeepSeek cache boundary stayed stable.",
    )
    assert impact.overlap_terms >= 3
    assert impact.impact_score > 0


def test_observe_last_prompt_answer_impact_publishes(monkeypatch):
    from core.services import prompt_section_impact as psi
    import core.eventbus.bus as bus

    events = []
    monkeypatch.setattr(bus.event_bus, "publish", lambda name, payload: events.append((name, payload)))
    psi.remember_prompt_sections(session_id="s1", sections=[("memory", "DeepSeek cache")])

    impacts = psi.observe_last_prompt_answer_impact(
        session_id="s1",
        run_id="r1",
        answer_text="DeepSeek cache",
    )

    assert impacts
    assert events[0][0] == "prompt.section_answer_impact"


def test_visible_prompt_build_remembers_sections_for_impact(isolated_runtime):
    """Regression (2026-09-04): remember_prompt_sections ran before the nested
    _label_of was bound → UnboundLocalError swallowed → no impact events ever."""
    from core.services import prompt_section_impact as psi

    prompt_contract = isolated_runtime.prompt_contract
    psi._LAST_SECTIONS.clear()
    prompt_contract.build_visible_chat_prompt_assembly(
        provider="openai", model="gpt-5", user_message="hvilken GPU har jeg?", session_id="s-impact",
    )
    assert "s-impact" in psi._LAST_SECTIONS
    _ts, sections = psi._LAST_SECTIONS["s-impact"]
    assert len(sections) > 5
    labels = [lbl for lbl, _ in sections]
    assert any("SOUL" in lbl for lbl in labels)
    impacts = psi.observe_last_prompt_answer_impact(
        session_id="s-impact", run_id="r", answer_text="Du har en GTX 1070 til embeddings",
    )
    assert impacts and all("impact_score" in i for i in impacts)


def test_prompt_family_is_publishable():
    """2026-09-04: 'prompt' manglede i ALLOWED_EVENT_FAMILIES → publish raisede stille →
    prompt.section_answer_impact (og prompt.assembly_size) landede aldrig i events."""
    from core.eventbus.events import ALLOWED_EVENT_FAMILIES, Event

    assert "prompt" in ALLOWED_EVENT_FAMILIES
    Event.create("prompt.section_answer_impact", {"run_id": "r", "answer_chars": 1, "sections": []})
    Event.create("prompt.assembly_size", {"chars": 1})
