"""Auto-fortsættelsens kanter.

Grundsandheden: Bjoern skrev «Forsæt» 24 gange 12.–13. september, og syv af
fjorten ture den nat stoppede paa praecis 30 runder — rundebudgettets loft,
bogfoert som `reason=completed`, samme ord som en faerdig tur.

Mekanikken er triviel; kanterne er det farlige. En fortsaettelse der fyrer
forkert koster penge, kan loebe i ring, og kan komme til at paastaa at
brugeren bad om noget han ikke bad om.
"""
import pytest

from core.services.auto_continuation import IKKE_BOGFOERT, OPBRUGT, kaede_nr


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
