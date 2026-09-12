"""Vinket om at batche vaerktoejskald.

Grundsandheden er maalt, ikke gaettet: 13/9-2026 over tre timers koersel kaldte
**304 af 366 agentiske runder praecis ét vaerktoej**. Kun 62 batchede to eller
flere. Med et rundebudget paa 30 er ét kald pr. runde forklaringen paa at turen
loeb toer og Bjoern maatte skrive «Forsæt» 24 gange det doegn.
"""
from core.services.tool_batch_notice import (
    MAKS_PR_TUR, MIN_RUNDER_TILBAGE, tool_batch_notice,
)


def _vink(kald=1, tilbage=20, vist=0) -> str:
    return tool_batch_notice(
        forrige_runde_kald=kald, runder_tilbage=tilbage, gange_vist=vist)


def test_vinker_naar_forrige_runde_kun_brugte_ét_kald():
    assert "SAMME runde" in _vink(kald=1)


def test_tier_naar_han_allerede_batcher():
    """To kald er allerede den adfaerd vi beder om. Et vink dér er nag."""
    assert _vink(kald=2) == ""
    assert _vink(kald=7) == ""


def test_tier_naar_der_slet_ikke_var_kald():
    """Foerste runde, eller en ren tekst-runde: der var intet at batche."""
    assert _vink(kald=0) == ""


def test_holder_op_efter_faa_gange():
    assert _vink(vist=MAKS_PR_TUR - 1) != ""
    assert _vink(vist=MAKS_PR_TUR) == ""
    assert _vink(vist=MAKS_PR_TUR + 5) == ""


def test_tier_taet_paa_rundegraensen():
    """Dér er rundebudget-varslet det vigtigste. To beskeder om rytmen i samme
    runde traekker i hver sin retning."""
    assert _vink(tilbage=MIN_RUNDER_TILBAGE) != ""
    assert _vink(tilbage=MIN_RUNDER_TILBAGE - 1) == ""
    assert _vink(tilbage=0) == ""


def test_vinket_naevner_afhaengighed_saa_han_ikke_batcher_forkert():
    """Kald der bygger paa et resultat MAA ikke batches. Uden det ville vinket
    invitere til at koere `read_file` paa en sti et andet kald skulle finde."""
    t = _vink()
    assert "afhænger" in t and "vente" in t


def test_skraldeinput_giver_tavshed_ikke_et_kast():
    """Vinket sidder i den hotte loekke. Et kast her maa aldrig kunne ramme en
    koersel."""
    assert tool_batch_notice(
        forrige_runde_kald="to", runder_tilbage=None, gange_vist=0) == ""
