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
