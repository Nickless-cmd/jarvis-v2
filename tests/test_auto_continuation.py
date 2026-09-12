"""Auto-fortsættelsens kanter.

Grundsandheden: Bjoern skrev «Forsæt» 24 gange 12.–13. september, og syv af
fjorten ture den nat stoppede paa praecis 30 runder — rundebudgettets loft,
bogfoert som `reason=completed`, samme ord som en faerdig tur.

Mekanikken er triviel; kanterne er det farlige. En fortsaettelse der fyrer
forkert koster penge, kan loebe i ring, og kan komme til at paastaa at
brugeren bad om noget han ikke bad om.
"""
import pytest

from core.services.auto_continuation import (
    MAKS_KAEDE, OPBRUGT, beslut, fortsaettelses_besked,
)


def _b(**over):
    kw = dict(exit_reason=OPBRUGT, slaaet_til=True, autonom=False,
              kaede_nr=0, bruger_skrev_imens=False)
    kw.update(over)
    return beslut(**kw)


def test_fortsaetter_naar_budgettet_loeb_toert():
    assert _b().fortsaet is True


@pytest.mark.parametrize("udfald", [
    "completed", "user-cancelled", "shutdown", "provider-not-supported",
    "interrupted:tool-fejl", "user-steer-stop-mid-stream", "", None,
])
def test_fortsaetter_ALDRIG_paa_noget_andet_end_opbrugt_budget(udfald):
    """Alt andet end «loeb toer» betyder at nogen eller noget greb ind."""
    assert _b(exit_reason=udfald).fortsaet is False


def test_killswitch_vinder_over_alt():
    assert _b(slaaet_til=False).fortsaet is False


def test_autonome_runs_fortsaetter_ikke_sig_selv():
    """De har deres egen kadence og deres eget budget."""
    assert _b(autonom=True).fortsaet is False


def test_brugeren_der_skriver_imens_tager_over():
    assert _b(bruger_skrev_imens=True).fortsaet is False


def test_kaeden_har_et_loft():
    for n in range(MAKS_KAEDE):
        assert _b(kaede_nr=n).fortsaet is True, f"kaede {n} burde fortsaette"
    assert _b(kaede_nr=MAKS_KAEDE).fortsaet is False
    assert _b(kaede_nr=MAKS_KAEDE + 9).fortsaet is False


def test_grunden_siger_hvorfor_ogsaa_naar_svaret_er_nej():
    """En fortsaettelse der udebliver skal kunne forklares uden at laese koden."""
    assert "kaede-loft" in _b(kaede_nr=MAKS_KAEDE).grund
    assert "slaaet fra" in _b(slaaet_til=False).grund
    assert "autonomt" in _b(autonom=True).grund
    assert "completed" in _b(exit_reason="completed").grund


def test_ugyldigt_kaede_tal_stopper_frem_for_at_fortsaette():
    """Tvivl skal falde ud til IKKE at bruge penge."""
    assert _b(kaede_nr="to").fortsaet is False


def test_beskeden_udgiver_sig_ALDRIG_for_at_vaere_brugerens():
    """Auto-fortsaettelsen har fabrikeret samtykke i dette hus foer — en
    maskinskrevet besked der stod som om Bjoern havde skrevet den."""
    t = fortsaettelses_besked(1)
    assert "automatisk" in t.lower()
    assert "Forsæt" not in t, "ligner brugerens egen besked"


def test_beskeden_fortaeller_hvor_i_kaeden_han_er():
    assert "1/3" in fortsaettelses_besked(1, 3)
    assert "3/3" in fortsaettelses_besked(3, 3)


def test_beskeden_giver_ham_en_vej_UD_af_kaeden():
    """Uden den ville han kalde vaerktoejer til loftet, ogsaa naar han var
    faerdig — og hver fortsaettelse koster et helt run."""
    t = fortsaettelses_besked(1)
    assert "færdigt" in t or "færdig" in t
