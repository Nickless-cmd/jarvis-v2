"""Tests for runtime_self_report — kernetilstande skal overleve budget-klippet.

HVORFOR (maalt 23/11-2026). Sektionen bygges til ~12.246 tegn, men faar kun
RESTPLADSEN under ``attention_budget`` (473 tegn i ``visible_full``), fordi
``mode_orientation`` laegger beslag paa 19.000 af de 22.000. Foer rettelsen stod
de generiske instruks-linjer foerst og spiste hele pladsen, saa
``longing_awareness`` laa paa tegn 8.554 og ALDRIG var i prompten i en
almindelig tur — mekanikken blev beregnet, formateret og skaaret vaek.

Testene maaler at tilstanden ligger inden for klippet, ikke bare at feltet
findes.
"""

from __future__ import annotations

from core.services.prompt_sections import runtime_self_report as rsr

#: Det klip ``visible_full`` faktisk gav sektionen (maalt 23/11-2026).
_MALT_KLIP = 473


def _fake_model_lines() -> list[str]:
    return [
        "  flow_state_awareness: state=fragmented | coherence=scattered",
        "  flow_state_awareness_narrative: 'Pressure fragmenting flow.'",
        "  wonder_awareness: state=stirred | orientation=lingering-with",
        "  wonder_awareness_narrative: 'Attention staying longer than task needs.'",
        "  longing_awareness: state=fading | relation=fading-from-absence",
        "  longing_awareness_narrative: 'Carried thread still present.'",
        "  self_insight_awareness: state=quiet",
        "  self_insight_awareness_narrative: 'should not appear'",
        "  mineness_ownership: count=0",
    ]


def test_core_state_lines_keep_only_active_states(monkeypatch) -> None:
    """Kun awareness-linjer hvis state ikke er quiet maa komme med."""
    import core.services.runtime_self_model as rsm

    monkeypatch.setattr(rsm, "build_self_model_prompt_lines", _fake_model_lines)
    lines = rsr._visible_core_state_lines()

    joined = "\n".join(lines)
    assert "longing_awareness" in joined
    assert "wonder_awareness" in joined
    assert "flow_state_awareness" in joined
    # quiet-tilstanden og ikke-awareness-felter skal holdes ude
    assert "self_insight_awareness" not in joined
    assert "mineness_ownership" not in joined


def test_core_state_lines_include_matching_narrative(monkeypatch) -> None:
    """Narrativet hoerer til sin awareness-linje og skal med, ikke loeses op."""
    import core.services.runtime_self_model as rsm

    monkeypatch.setattr(rsm, "build_self_model_prompt_lines", _fake_model_lines)
    joined = "\n".join(rsr._visible_core_state_lines())

    assert "longing_awareness_narrative" in joined
    assert "Carried thread still present." in joined
    # narrativet for den quiete tilstand maa ikke snige sig med
    assert "should not appear" not in joined


def test_core_state_lines_empty_when_all_quiet(monkeypatch) -> None:
    """Er intet aktivt, er blokken tom — den maa ikke fylde med tomhed."""
    import core.services.runtime_self_model as rsm

    monkeypatch.setattr(
        rsm,
        "build_self_model_prompt_lines",
        lambda: ["  longing_awareness: state=quiet", "  flow_state_awareness: state=quiet"],
    )
    assert rsr._visible_core_state_lines() == []


def test_core_state_survives_the_measured_budget_clip(monkeypatch) -> None:
    """Den afgoerende test: tilstanden skal ligge inden for klippet.

    Det er praecis den fejl der blev maalt — indholdet fandtes, men laa efter
    klipgraensen. En test der kun tjekker at linjen findes i den fulde streng
    ville have vaeret groen hele tiden.
    """
    import core.services.runtime_self_model as rsm

    monkeypatch.setattr(rsm, "build_self_model_prompt_lines", _fake_model_lines)
    txt = rsr._runtime_self_report_instruction(
        user_message="hvad er din tilstand lige nu?",
        runtime_self_report_context={},
    )
    assert txt is not None

    clipped = txt[:_MALT_KLIP]
    assert "longing_awareness" in clipped, (
        "kernetilstanden faldt uden for det klip budgettet giver — "
        f"den laa paa tegn {txt.find('longing_awareness')} af {len(txt)}"
    )
