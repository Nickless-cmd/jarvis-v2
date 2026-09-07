"""Værnets stemme: hvad siger vi, når det tvungne forsøg OGSÅ gav nul kald?

Baggrund 7/9-2026: vagten opdagede løftet, tvang en runde med
tool_choice=required, fik stadig nul værktøjskald — og skrev det udelukkende
til eventbussen. Bjørn så fire løfter i træk og skrev «Kør» hver gang.
"""
from core.services.hollow_promise_round import hollow_promise_note, note_outcome


def test_nul_kald_er_ikke_loest():
    assert note_outcome(run_id="r", provider="deepseek", model="m", round_index=1,
                        session_id="s", forced=True, tool_calls=0) is False


def test_et_kald_er_loest():
    assert note_outcome(run_id="r", provider="deepseek", model="m", round_index=1,
                        session_id="s", forced=True, tool_calls=1) is True


def test_beskeden_indroemmer_at_intet_blev_udfoert():
    n = hollow_promise_note("deepseek-v4-pro")
    assert "ingen værktøjer" in n
    assert "ikke udført" in n


def test_ingen_model_beskyldes():
    """Første udgave hængte modellen ud ved navn. Bjørn rettede mig, og tallene
    gav ham ret: vision-modellen løser 11 af 15, flash uden syn 13 af 16 — det
    er tilfældigt pr. forsøg. En forkert beskyldning ville sende ham ud at
    skifte model uden grund."""
    for m in ("deepseek-v4-flash-vision-exp", "deepseek-v4-flash", "", None):
        n = hollow_promise_note(m or "")
        assert "vision" not in n.lower()
        assert "Skift model" not in n
        assert "`" not in n


def test_beskeden_er_den_samme_uanset_model():
    assert hollow_promise_note("a") == hollow_promise_note("b") == hollow_promise_note("")


def test_beskeden_siger_at_der_blev_forsoegt_to_gange():
    # Ellers lyder det som om han gav op med det samme.
    assert "to gange" in hollow_promise_note("")
