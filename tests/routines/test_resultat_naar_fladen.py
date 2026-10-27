"""To fejl der gjorde rutine-fladen ubrugelig — målt 27/10-2026.

Bjørn sendte fire skærmbilleder fra telefonen: hele hændelsesloggen stod åben
med rå JSON, svaret var der ikke, og det der var af tekst var én lang linje
uden markdown. Fejlene sad to forskellige steder, og ingen af dem var i
frontenden — derfor fandt 2979 grønne desk-tests dem ikke.

1. ``RunView`` manglede ``result``-feltet. ``db_routines.get_run(decrypt_for=…)``
   satte det korrekt, men ``_run_view`` byggede en dataclass uden feltet, så
   svaret blev kastet væk i service-laget. Fladen faldt tilbage på loggen.
2. Svaret er UTF-8-**bytes** (``result.text.encode()`` i runneren). Sendt
   direkte videre blev det ``b'...'`` med escape-koder, så markdown aldrig
   kunne rendere — uanset hvad fladen gjorde.
3. ``"".join(text_parts)`` smeltede to runders tekst sammen til
   «workspace-rod.Første gennemgang …».
"""

from __future__ import annotations

from core.services.agentic_execution import _samlet_tekst
from core.services.routine_service import RunView, _run_view, _som_tekst


def _row(**overrides):
    """En række som ``db_routines.get_run`` giver den videre efter dekryptering."""
    base = {
        "run_id": "run-1",
        "routine_id": "routine-1",
        "owner_user_id": "owner-1",
        "access_scope": "user_private",
        "routine_version": 1,
        "status": "succeeded",
        "lease_holder": None,
        "lease_generation": 1,
        "idempotency_key": "manual:1",
        "created_at": "2026-10-27T20:37:17+00:00",
        "definition_snapshot": None,
        "execution_context": None,
        "result": "## Svar\n\nDer **er** ting.".encode("utf-8"),
        "diagnostic_code": None,
    }
    base.update(overrides)
    return base


def test_run_view_baerer_resultatet():
    """Uden dette felt var svaret usynligt for fladen — den viste kun loggen."""
    view = _run_view(_row())

    assert isinstance(view, RunView)
    assert view.result == "## Svar\n\nDer **er** ting."


def test_resultatet_er_tekst_ikke_bytes():
    """``b'...'`` med escape-koder kan ikke rendere som markdown."""
    view = _run_view(_row())

    assert isinstance(view.result, str)
    assert not view.result.startswith("b'")
    assert "\\n" not in view.result  # ægte linjeskift, ikke escape-sekvenser


def test_dansk_tekst_overlever_dekodningen():
    """Æ/ø/å skal stå som tegn — ikke som ``\\xc3\\xa6``."""
    view = _run_view(_row(result="Blåbær og rødgrød".encode("utf-8")))

    assert view.result == "Blåbær og rødgrød"


def test_manglende_resultat_er_none_ikke_tom_streng():
    """En kørsel uden svar skal kunne skelnes fra et tomt svar."""
    assert _som_tekst(None) is None
    assert _run_view(_row(result=None)).result is None


def test_diagnosekode_naar_ogsaa_frem():
    """Fejlkoden blev tidligere tabt samme sted som svaret."""
    view = _run_view(_row(status="failed", diagnostic_code="action_required"))

    assert view.diagnostic_code == "action_required"


def test_to_runder_smeltes_ikke_sammen():
    """Målt: «workspace-rod.Første gennemgang» — to runder uden separator."""
    samlet = _samlet_tekst(["Den forventede sti findes ikke.", "Første gennemgang giver signaler."])

    assert samlet == "Den forventede sti findes ikke.\n\nFørste gennemgang giver signaler."
    assert "ikke.Første" not in samlet


def test_tom_runde_efterlader_ikke_hul():
    """En runde uden tekst må ikke give tre linjeskift i træk."""
    samlet = _samlet_tekst(["Første.", "", "  ", "Anden."])

    assert samlet == "Første.\n\nAnden."


def test_enkelt_runde_er_uaendret():
    """Den almindelige vej — ét svar — skal ikke pyntes."""
    assert _samlet_tekst(["Kun dette."]) == "Kun dette."
