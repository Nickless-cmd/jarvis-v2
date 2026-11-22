"""En tur der læser et godkendelses-resultat der kom efter turen var slut.

## Hullet den lukker (målt 22/11-2026, side-aa429f4212)

Af 4.028 godkendelses-kort blev 41 afgjort EFTER deres tur var slut — og 40 af
dem kørte kommandoen færdig, op til 38 minutter senere. Resultatet blev skrevet
i `chat_messages` som `role="tool"` (den vej blev lukket 24/5-2026), så Bjørn
så det. Men den tur der bad om lov var væk, og derfor var der ingen der LÆSTE
svaret og sagde hvad det betød. Han fik rådata uden en stemme på.

Hullet er altså ikke «turen mangler» — det er «resultatet mangler en læser».

Frekvensen er ~6 gange om måneden, hver anden dag. Det er under tærsklen for
en generel genoptagelses-maskine, men ikke under tærsklen for at lukke hullet:
den her enhed starter én kort tur der læser resultatet, ikke en mekanisme der
genoptager vilkårlige døde runs.

## Løkkefaren, og de tre værn mod den

En opfølgningstur er en RIGTIG tur: den kan selv bede om godkendelse. Bliver
den godkendt efter DEN er slut, ville den føde endnu en opfølgningstur — og så
videre. Alle tre værn er fail-closed: kan vi ikke afgøre det, starter vi intet.

1. ``approval_followup.<approval_id>`` skrives FØR turen startes. Samme kort
   føder derfor aldrig to ture — heller ikke hvis selve starten kaster.
2. ``approval_followup_run.<run_id>`` stempler den tur VI startede. Bed en
   opfølgningstur selv om godkendelse, findes dens run-id her, og der startes
   ingen anden. Kæden bliver én lang, ikke uendelig.
3. Sessionen skal være HELT fri (`active_run_for_session` er None). Ellers
   skabte vi to parallelle realiteter i samme samtale — samme fejl som
   `run_guard` blev bygget for at forhindre 13/10-2026.

## Hvorfor turen kun startes når den gamle er BEVISELIGT slut

`run_er_terminal` returnerer ``None`` når den ikke kan afgøre det. ``None`` er
ikke «slut»: en tur der stadig venter på godkendelsen får resultatet gennem
`wait_for_approval`, og en ekstra tur oveni ville give to svar på samme kort.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

_OPFOELGNING_PREFIX = "approval_followup."
_OPFOELGNING_RUN_PREFIX = "approval_followup_run."

#: Hvor længe markøren huskes. Et kort besvares inden for sin egen TTL (3600s),
#: og opfølgningen sker i samme sekund som afgørelsen — 30 dage er rigeligt, og
#: grænsen forhindrer at `runtime_state_kv` vokser uden ende.
MARKOER_LEVETID_S = 30 * 24 * 3600


def _markoer_noegle(approval_id: str) -> str:
    return f"{_OPFOELGNING_PREFIX}{str(approval_id or '').strip()}"


def _run_markoer_noegle(run_id: str) -> str:
    return f"{_OPFOELGNING_RUN_PREFIX}{str(run_id or '').strip()}"


def _laes(noegle: str) -> dict | None:
    """Læs en markør — ``None`` når den ikke findes eller er ulaesbar."""
    try:
        from core.runtime.db import get_runtime_state_value

        vaerdi = get_runtime_state_value(noegle, default=None)
        return vaerdi if isinstance(vaerdi, dict) else None
    except Exception:  # ulaesbar state: behandles som «findes ikke» af kalderen
        logger.warning("approval-followup: kunne ikke laese %s", noegle, exc_info=True)
        return None


def _skriv(noegle: str, vaerdi: dict) -> bool:
    """Skriv en markør. ``False`` betyder at den IKKE står på disken."""
    try:
        from core.runtime.db import set_runtime_state_value

        set_runtime_state_value(noegle, vaerdi)
        return True
    except Exception:
        logger.warning("approval-followup: kunne ikke skrive %s", noegle, exc_info=True)
        return False


def _er_utloebet(markoer: dict) -> bool:
    """Er markøren ældre end `MARKOER_LEVETID_S`? Ulaesbar tid = ikke udløbet."""
    raa = str(markoer.get("oprettet") or "").strip()
    if not raa:
        return False
    try:
        tid = datetime.fromisoformat(raa.replace("Z", "+00:00"))
        if tid.tzinfo is None:
            tid = tid.replace(tzinfo=UTC)
        return (datetime.now(UTC) - tid).total_seconds() > MARKOER_LEVETID_S
    except Exception:  # ulaesbar tid: vi kaster ikke en gyldig markoer vaek
        return False


def er_opfølgningstur(run_id: str) -> bool:
    """Blev DETTE run startet af os som en opfølgning?

    Kæde-værnet: en opfølgningstur må ikke selv kunne føde en opfølgningstur.
    """
    rid = str(run_id or "").strip()
    if not rid:
        return False
    return _laes(_run_markoer_noegle(rid)) is not None


def _allerede_fulgt_op(approval_id: str) -> bool:
    markoer = _laes(_markoer_noegle(approval_id))
    if markoer is None:
        return False
    if _er_utloebet(markoer):
        return False
    return True


def _besked(tool_name: str) -> str:
    """Det opfølgningsturen læser. Kort, ærligt og handlingsanvisende."""
    return (
        f"[Godkendelsen af {tool_name} kom efter turen var slut. Kommandoen "
        "kørte, og resultatet ligger som et værktøjssvar i samtalen ovenfor. "
        "Læs det og fortæl Bjørn hvad det betyder — han har set rådata, ikke "
        "din læsning af det.]"
    )


def start_opfølgning(
    *,
    approval_id: str,
    tool_name: str,
    session_id: str,
    oprindeligt_run_id: str,
    force_user_id: str | None = None,
) -> dict:
    """Start én tur der læser et sent godkendt resultat. Kaster aldrig.

    Returnerer ``{"started": bool, "grund": str, "run_id": str}``. ``grund``
    siger HVORFOR der ikke blev startet noget, så et fravær kan efterprøves
    frem for at ligne en fejl.
    """
    aid = str(approval_id or "").strip()
    sid = str(session_id or "").strip()
    rid = str(oprindeligt_run_id or "").strip()

    if not aid or not sid or not rid:
        return {"started": False, "grund": "mangler approval_id/session_id/run_id",
                "run_id": ""}

    # Værn 1 — samme kort føder aldrig to ture.
    if _allerede_fulgt_op(aid):
        return {"started": False, "grund": "kortet er allerede fulgt op", "run_id": ""}

    # Værn 2 — kæden må ikke kunne forlænges af sig selv.
    if er_opfølgningstur(rid):
        return {"started": False,
                "grund": "turen var selv en opfølgning — kæden stopper her",
                "run_id": ""}

    # Turen skal være BEVISELIGT slut. `None` er ikke «slut».
    try:
        from core.services.visible_runs_outcomes import run_er_terminal

        terminal = run_er_terminal(rid)
    except Exception:
        logger.warning("approval-followup: kunne ikke afgoere terminal for %s",
                       rid, exc_info=True)
        return {"started": False, "grund": "kunne ikke afgøre om turen er slut",
                "run_id": ""}
    if terminal is not True:
        return {"started": False,
                "grund": "turen lever stadig og får resultatet selv", "run_id": ""}

    # Værn 3 — ingen parallelle realiteter i samme samtale.
    try:
        from core.services import run_event_log as rel

        levende = rel.active_run_for_session(sid)
    except Exception:
        logger.warning("approval-followup: kunne ikke se om sessionen er fri",
                       exc_info=True)
        return {"started": False, "grund": "kunne ikke afgøre om sessionen er fri",
                "run_id": ""}
    if levende:
        return {"started": False, "grund": f"sessionen er optaget af {str(levende)[:40]}",
                "run_id": ""}

    # Markøren skrives FØR starten: kaster starten, står den stadig — og så
    # forsøger vi ikke igen på samme kort.
    nu = datetime.now(UTC).isoformat()
    if not _skriv(_markoer_noegle(aid), {
        "approval_id": aid, "session_id": sid, "oprindeligt_run": rid,
        "oprettet": nu,
    }):
        return {"started": False, "grund": "kunne ikke skrive markøren", "run_id": ""}

    try:
        from core.services.visible_runs_sections.detached_run import (
            start_user_run_detached,
        )

        nyt_run = start_user_run_detached(
            message=_besked(str(tool_name or "værktøjet")),
            session_id=sid,
            force_user_id=force_user_id or None,
            # Uden en origin tolker klientens reducer turen som en runde i den
            # FORRIGE tur og fletter teksten ind i en besked han allerede har
            # læst (målt 12/11-2026). Værdien ligger bevidst UDEN FOR
            # `autonomous_sessions.ORIGINS`: `_bruger_til_stede` spørger
            # sessionen først (19/10-2026), så et menneske er til stede — men
            # en kendt system-oprindelse ville stadig være en forkert påstand.
            origin="approval-followup",
        )
    except Exception as exc:
        logger.warning("approval-followup: start fejlede for %s: %s", aid, exc,
                       exc_info=True)
        return {"started": False, "grund": f"start fejlede: {str(exc)[:120]}",
                "run_id": ""}

    # Værn 2's anden halvdel: stempl det run vi netop startede.
    _skriv(_run_markoer_noegle(str(nyt_run)), {
        "approval_id": aid, "oprindeligt_run": rid, "oprettet": nu,
    })
    logger.info(
        "approval-followup: %s afgjort efter turen — startede %s der laeser resultatet",
        aid, str(nyt_run)[:28],
    )
    return {"started": True, "grund": "resultatet har fået en læser",
            "run_id": str(nyt_run)}
