"""Vinket om at batche vaerktoejskald.

Grundsandheden er maalt, ikke gaettet: 13/9-2026 over tre timers koersel kaldte
**304 af 366 agentiske runder praecis ét vaerktoej**. Kun 62 batchede to eller
flere. Med et rundebudget paa 30 er ét kald pr. runde forklaringen paa at turen
loeb toer og Bjoern maatte skrive «Forsæt» 24 gange det doegn.
"""
from core.services.tool_batch_notice import (
    MAKS_PR_TUR, MIN_RUNDER_TILBAGE, tool_batch_notice,
)


def _vink(kald=1, tilbage=20, vist=0, forrige=1) -> str:
    """`forrige=1` er standarden: moensteret gentager sig.

    Det er et KRAV, ikke en detalje — se
    `test_tier_naar_det_ENKELTE_kald_ikke_gentager_sig`.
    """
    return tool_batch_notice(
        forrige_runde_kald=kald, runder_tilbage=tilbage, gange_vist=vist,
        forrige_forrige_kald=forrige)


def test_vinker_naar_forrige_runde_kun_brugte_ét_kald():
    assert "SAMME runde" in _vink(kald=1)


def test_tier_naar_det_ENKELTE_kald_ikke_gentager_sig():
    """4/10-2026 — fixet. Ét kald er ikke bevis på manglende batching.

    Maalt i drift: vinket fyrede midt i en strengt sekventiel kaede
    (laes → maal → beslut → laes), hvor hvert kald ventede paa det forrige.
    Runden FOER den forrige havde batchet, saa der var ingen vane at rette —
    kun et enkelt kald der var det rigtige svar. Bjoern 4/10: «den genere dig».
    """
    assert _vink(kald=1, forrige=2) == ""
    assert _vink(kald=1, forrige=0) == ""
    assert _vink(kald=1, forrige=5) == ""


def test_tier_naar_vi_ikke_KENDER_den_forrige_forrige():
    """Ukendt tal → tavshed.

    Et vink vi ikke kan begrunde, sender vi ikke. Samme fail-retning som resten
    af filen: hellere tie end at paastaa noget usandt om en runde.
    """
    assert tool_batch_notice(
        forrige_runde_kald=1, runder_tilbage=20, gange_vist=0) == ""


def test_vanen_skal_vaere_der_foer_vinket_kommer():
    """To runder i traek med praecis ét kald = vanen er paa vej.

    Det er den ENESTE vej til vinket nu, og det er hele pointen: maalt 13/9
    kaldte 304 af 366 runder ét vaerktoej, saa to-i-traek er stadig den
    tilstand vinket skal rette. Det der er fjernet er det ISOLEREDE kald.
    """
    assert _vink(kald=1, forrige=1) != ""


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
