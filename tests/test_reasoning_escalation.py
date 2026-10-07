"""Unit tests for reasoning_escalation (R3 of reasoning-layer rollout)."""
from __future__ import annotations

from unittest.mock import patch

from core.services.reasoning_escalation import (
    evaluate_escalation,
    escalation_section,
)


def _stub_tier(tier: str, signals: list[str] | None = None):
    return {"tier": tier, "score": 80 if tier == "deep" else 30, "signals": signals or []}


def _stub_gate(failed: int = 0, unverified: int = 0):
    return {
        "mutation_count": unverified + failed,
        "verify_count": failed,
        "failed_verify_count": failed,
        "unverified_count": unverified,
        "failed_verifies": [],
    }


def test_no_escalation_for_fast_tier():
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("fast")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate()):
        result = evaluate_escalation("hej")
    assert result["escalate"] is False


def test_deep_without_failures_still_recommends_planner():
    """R3.1: deep tier alone (no gate failures) still surfaces a planner hint."""
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("deep")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate()):
        result = evaluate_escalation("design ny arkitektur")
    assert result["escalate"] is True
    assert result["recommendation"]["role"] == "planner"


def test_state_based_failed_verify_surfaces_on_fast_message():
    """R3.1 regression test: a failed verify from a previous turn must still
    surface even when the user's current message is fast-tier."""
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("fast")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate(failed=1)):
        result = evaluate_escalation("hvad er klokken?")
    assert result["escalate"] is True
    assert any("failed verify" in t for t in result["triggers"])


def test_escalation_for_deep_plus_failed_verify():
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("deep")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate(failed=1)):
        result = evaluate_escalation("kør migration")
    assert result["escalate"] is True
    assert result["recommendation"]["path"] is not None


def test_escalation_recommends_critic_on_multiple_failed_verifies():
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("reasoning")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate(failed=2)):
        result = evaluate_escalation("opdater config")
    assert result["escalate"] is True
    assert result["recommendation"]["path"] == "spawn_agent_task"
    assert result["recommendation"]["role"] == "critic"


def test_escalation_recommends_researcher_on_unverified_mutations():
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("deep")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate(unverified=4)):
        result = evaluate_escalation("rør mange filer")
    assert result["escalate"] is True
    assert result["recommendation"]["role"] == "researcher"


def test_risiko_markoerer_eskalerer_til_EN_uafhaengig_kritiker():
    """Der er kun ÉN vej tilbage, og testen skal paastaa netop den.

    Den hed `test_escalation_recommends_council_on_deep_with_risk_markers` og
    sluttede med `path in ("convene_council", "spawn_agent_task")` under
    kommentaren «either is acceptable». Begge grene gav altsaa groent, saa
    testen kunne ikke se forskel paa de to veje — og da `convene_council`
    forsvandt 7/10-2026, ville den have bestaaet uanset hvad eskaleringen
    pegede paa. Nu pinner den den ene vej der findes, med rolle og emne-hint.
    """
    with patch(
        "core.services.reasoning_escalation._safe_tier",
        return_value=_stub_tier("deep", signals=["destructive command marker", "production system"]),
    ), patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate(failed=1)):
        result = evaluate_escalation("rm -rf prod")
    assert result["escalate"] is True
    anb = result["recommendation"]
    assert anb["path"] == "spawn_agent_task"
    assert anb["role"] == "critic"
    assert anb["reason"], "en eskalering uden begrundelse siger ham ingenting"


def test_eskaleringen_peger_ALDRIG_paa_et_vaerktoej_der_ikke_findes():
    """Vagten bag 7/10-rettelsen: en eskalering der peger paa et fjernet
    vaerktoej er vaerre end ingen eskalering — han faar at vide at han SKAL
    gøre noget, og kaldet fejler.

    Den gaar gennem alle de kombinationer modulet selv forgrener paa, saa en
    ny gren ikke kan smutte ind med en doed sti.
    """
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS

    kataloget = {str(((d.get("function") or {}).get("name")) or "") for d in TOOL_DEFINITIONS}
    assert "spawn_agent_task" in kataloget, "forudsaetning: kataloget blev laest"

    risici = ["destructive command marker", "production system"]
    for tier in ("fast", "balanced", "deep"):
        for signaler in ([], risici):
            for fejlet, uverificerede in ((0, 0), (1, 0), (0, 4), (2, 3)):
                with patch("core.services.reasoning_escalation._safe_tier",
                           return_value=_stub_tier(tier, signals=signaler)), \
                     patch("core.services.reasoning_escalation._safe_gate",
                           return_value=_stub_gate(failed=fejlet, unverified=uverificerede)):
                    r = evaluate_escalation("noget")
                sti = (r.get("recommendation") or {}).get("path")
                if not sti:
                    continue
                assert sti in kataloget, (
                    "eskaleringen peger paa %r (tier=%s signaler=%d fejlet=%d "
                    "uverificerede=%d), som ikke staar i vaerktoejskataloget"
                    % (sti, tier, len(signaler), fejlet, uverificerede)
                )


def test_section_returns_none_when_no_escalation():
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("fast")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate()):
        assert escalation_section() is None


def test_section_returns_string_when_escalating():
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("deep")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate(failed=1)):
        section = escalation_section("design")
    assert section is not None
    assert "eskalering" in section.lower() or "escalation" in section.lower() or "🚨" in section


def test_tool_exec_wrapper():
    from core.services.reasoning_escalation import _exec_recommend_escalation
    with patch("core.services.reasoning_escalation._safe_tier", return_value=_stub_tier("fast")), \
         patch("core.services.reasoning_escalation._safe_gate", return_value=_stub_gate()):
        result = _exec_recommend_escalation({"message": "hej"})
    assert result["status"] == "ok"
    assert result["escalate"] is False
