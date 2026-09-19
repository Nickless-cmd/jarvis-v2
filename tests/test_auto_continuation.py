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
    OPBRUGT, "shutdown", "completed-truncated",
    "interrupted:tool-fejl", "early-exit-empty-text", "pending-tool-intent",
])
def test_recoverable_runsegmenter_fortsaetter(udfald):
    assert _b(exit_reason=udfald).fortsaet is True


@pytest.mark.parametrize("udfald", [
    "completed", "user-cancelled", "user-steer-stop-mid-stream", "", None,
    # En model uden followup-adapter får den ikke af at prøve igen — samme tur
    # ville ramme samme mur tre gange (visible_terminal_policy, cf6b437db
    # 17/9-2026). Testen stod tilbage på den gamle liste.
    "provider-not-supported",
])
def test_finale_udfald_fortsaetter_ikke(udfald):
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


# ────────────────────────────────────────────────────────────────────────
# «ukendt» daekkede TO tilstande — maalt 13/9-2026
#
# Fire beslutninger loed `udfald=ukendt`, og ordet daekkede baade «turen naaede
# aldrig bogfoerings-punktet» (et KORREKT nej) og «udfaldet blev noteret under
# en noegle vi ikke slog op» (en FEJL). Med ét ord for begge kan man ikke se
# hvilken man har — og saa bliver den anden aldrig fundet.
# ────────────────────────────────────────────────────────────────────────

def test_intet_bogfoert_er_IKKE_det_samme_som_bogfoert_tomt():
    import core.services.auto_continuation as ac
    ac._UDFALD.clear()
    # intet bogfoert
    assert ac.hent_udfald("findes-ikke", "heller-ikke") == ac.IKKE_BOGFOERT
    # bogfoert, men tomt
    ac.noter_udfald("r-tom", "", "s-tom")
    assert ac.hent_udfald("r-tom", "s-tom") == ""
    assert ac.hent_udfald("r-tom", "s-tom") != ac.IKKE_BOGFOERT
    ac._UDFALD.clear()


def test_beslutningens_GRUND_skelner_de_to():
    """Grunden havner i journalen. Kan man ikke skelne dér, kan man ikke
    skelne nogen steder."""
    import core.services.auto_continuation as ac
    ac._UDFALD.clear()
    uden = ac.beslut(exit_reason=ac.hent_udfald("x", "y"), slaaet_til=True,
                     autonom=False, kaede_nr=0, bruger_skrev_imens=False)
    assert "ikke-bogfoert" in uden.grund

    ac.noter_udfald("r", "completed", "s")
    med = ac.beslut(exit_reason=ac.hent_udfald("r", "s"), slaaet_til=True,
                    autonom=False, kaede_nr=0, bruger_skrev_imens=False)
    assert "completed" in med.grund and "ikke-bogfoert" not in med.grund
    ac._UDFALD.clear()


def test_sentinel_udloeser_ALDRIG_en_fortsaettelse():
    """Et manglende udfald maa ikke kunne forveksles med et budget der loeb
    toert. Tvivl fortsaetter ikke af sig selv."""
    import core.services.auto_continuation as ac
    b = ac.beslut(exit_reason=ac.IKKE_BOGFOERT, slaaet_til=True, autonom=False,
                  kaede_nr=0, bruger_skrev_imens=False)
    assert b.fortsaet is False


def test_session_fallbacken_virker_stadig():
    """Vagt mod at skelnen braekker den fallback der var hele pointen med
    b32928c8c: de to sider af en tur bruger FORSKELLIGE run-id."""
    import core.services.auto_continuation as ac
    ac._UDFALD.clear()
    ac.noter_udfald("indre-id", ac.OPBRUGT, "fælles-session")
    # opslag med det YDRE id — kun sessionen er faelles
    assert ac.hent_udfald("ydre-id", "fælles-session") == ac.OPBRUGT
    ac._UDFALD.clear()


def test_ny_tur_arver_ikke_forrige_turs_udfald():
    """17/9-2026: session-noeglen blev aldrig nulstillet. En kort tur (ingen
    agentisk loekke -> intet noteret) arvede «opbrugt» fra turen foer."""
    from core.services import auto_continuation as ac
    ac.noter_udfald("visible-foerste", ac.OPBRUGT, "s-arv")
    assert ac.hent_udfald("visible-relay-anden", "s-arv") == ac.OPBRUGT  # uden nulstilling: arvet
    ac.glem_session_udfald("s-arv")
    assert ac.hent_udfald("visible-relay-anden", "s-arv") == ac.IKKE_BOGFOERT
    # Runnets eget id er stadig slaaet op, hvis det findes.
    assert ac.hent_udfald("visible-foerste", "s-arv") == ac.OPBRUGT


def test_detached_run_glemmer_udfaldet_ved_ny_tur():
    import inspect
    from core.services.visible_runs_sections import detached_run
    kilde = inspect.getsource(detached_run.start_user_run_detached)
    i_glem = kilde.index("glem_session_udfald(sid)")
    i_traad = kilde.index("def _in_thread")
    assert i_glem < i_traad, "skal ske ved turens start, foer traaden koerer"
