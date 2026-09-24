"""Én doer ind og ud af en godkendelse — Fase 4's sidste stykke.

Spec'en: «move policy resolution, request/decision persistence, answerer
dispatch, expiry, and the Phase 3 atomic claim bridge behind
`ApprovalRuntime`.»

## Hvad der faktisk var spredt — maalt, ikke antaget

BESLUTNINGEN var allerede samlet: tre svarere (chat /approve, /deny, cowork)
gaar alle gennem `resolve_pending_approval`, hvor udloeb, ejerskab, digest og
den atomiske overtagelse ligger. Den doer skal ikke bygges om; den virker.

KORTET var derimod bygget i haanden FIRE steder. Det er ikke teoretisk: hver
gang Fase 4 tilfoejede et felt — ejer, tidsstempel, digest — skulle det
tilfoejes fire gange, og en glemt kopi ville have vaeret et stille hul. Tre
gange paa én dag har det moenster kostet en ekstra runde.

Derfor er dette moduls kerne `build_request()`: ét sted der ved hvordan et
gyldigt kort ser ud, saa et nyt kald-sted ikke KAN glemme et felt.

UDLOEBET blev kun tjekket to steder — ved svar og ved opstart. Et udloebet kort
blev altsaa liggende i filen til nogen roerte det. Ikke et sikkerhedshul (svar
afvises), men tilstanden loej om hvad der var i vente. `sweep_expired()` er
fejningen der manglede.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

# Felter ethvert kort SKAL have. Fase 4 tilfoejede de tre sidste én ad gangen,
# hver gang fire steder. Listen er her saa en test kan haevde den.
PAAKRAEVEDE = ("tool_name", "arguments", "run_id", "session_id",
               "created_at", "owner_user_id", "invocation_digest")


def new_id() -> str:
    return f"approval-{uuid4().hex[:12]}"


def build_request(*, tool_name: str, arguments: dict[str, Any],
                  result: Any, run: Any,
                  created_at: str | None = None) -> dict[str, Any]:
    """Byg et gyldigt godkendelses-kort. Det ENE sted formen bor.

    `run` giver ejer og herkomst; resten kommer fra kaldet. Ejeren og digesten
    udledes gennem `visible_runs`' egne hjaelpere, saa der ikke opstaar en
    anden definition af «hvem» og «samme kald».
    """
    import core.services.visible_runs as _vr

    return {
        "tool_name": tool_name,
        "arguments": arguments,
        "result": result,
        "run_id": getattr(run, "run_id", "") or "",
        "session_id": getattr(run, "session_id", "") or "",
        # Fladen turen blev skrevet fra. Uden den ved notifikationen ikke
        # hvor den skal hen, og falder tilbage på en rangliste over enheder.
        "surface": getattr(run, "surface", "") or "",
        "created_at": created_at or datetime.now(UTC).isoformat(),
        "owner_user_id": _vr._godkendelses_ejer(run),
        "invocation_digest": _vr._kald_digest(tool_name, arguments),
    }


def pending_for_session(session_id: str) -> dict[str, Any] | None:
    """Det ventende godkendelses-kort for ÉN samtale — eller ``None``.

    ## Hvorfor den findes (20/9-2026)

    Desk får kortet som et LIVE-event i streamen; mobilen finder det ved at
    polle. Er streamen ikke forbundet i det øjeblik kortet laves — en
    genforbindelse, et vindue der lige er åbnet, et svar der kom videre efter
    en afbrydelse — ser desk det ALDRIG. Bjørn 20/9-2026: «jeg sidder og laver
    noget med ham i desk og så står han bare og hænger, indtil jeg kigger på
    min telefon og så ligger der et approval card».

    Kortet har hele tiden vidst hvilken samtale det hørte til
    (`build_request` sætter `session_id`); der var bare ingen der kunne spørge.

    Nyeste først, så et gammelt kort ikke skygger for det han venter på.
    """
    sid = str(session_id or "").strip()
    if not sid:
        return None
    import core.services.visible_runs as _vr

    kandidater = [
        {**kort, "approval_id": aid}
        for aid, kort in _vr.godkendelser_nu().items()
        if str((kort or {}).get("session_id") or "") == sid
    ]
    if not kandidater:
        return None
    kandidater.sort(key=lambda k: str(k.get("created_at") or ""), reverse=True)
    return kandidater[0]


def pending_for_owner(user_id: str) -> dict[str, Any] | None:
    """Det ventende kort for en EJER — uanset hvilken samtale det hører til.

    ## Hvorfor den findes (20/9-2026, samme aften som `pending_for_session`)

    Session-udgaven lukkede kun det halve hul. Bjørn 20/9: «der ligger en jeg
    ikke kan få lov at se som skal godkendes, den holder hans run».

    Målt i det øjeblik: FIRE kort ventede, alle i session
    `chat-ceb50330…` — en samtale desk ikke selv streamede. Desk spurgte kun
    om sin EGEN arbejdende session, og kun mens dens egen stream kørte. To
    gates, og kortene lå uden for dem begge.

    Et kort hører til en ejer, ikke til det vindue der tilfældigvis er åbent.
    Nyeste først, og `session_id` følger med, så klienten kan sige HVOR det
    kom fra i stedet for at vise et kort uden ophav.
    """
    uid = str(user_id or "").strip()
    if not uid:
        return None
    import core.services.visible_runs as _vr

    kandidater = [
        {**kort, "approval_id": aid}
        for aid, kort in _vr.godkendelser_nu().items()
        if str((kort or {}).get("owner_user_id") or "") == uid
    ]
    if not kandidater:
        return None
    kandidater.sort(key=lambda k: str(k.get("created_at") or ""), reverse=True)
    return kandidater[0]


def alle_pending_for_owner(user_id: str) -> list[dict[str, Any]]:
    """ALLE ventende kort for en EJER — ikke kun det nyeste.

    K2 (2026-09-22): `pending_for_owner` returnerer med vilje kun ét kort, og
    det er rigtigt for kaldere der vil vise ét kort. Men notifikations-feedens
    afstemning (`notifikations_emittere.afstem_godkendelser`) brugte den
    samme funktion til at lægge RÆKKER — og fik derfor kun det NYESTE kort
    nogensinde med. Efterprøvet: fire kort ventede samtidig, kun ét nåede
    feeden, stabilt over gentagne afstemninger.

    Selvsamme scenarie var grunden til at `pending_for_owner` blev bygget i
    sin tid (se dens docstring) — det halve hul lukkede aldrig helt.

    `pending_for_owner` er URØRT: andre kaldere skal fortsat kun se ét kort.
    """
    uid = str(user_id or "").strip()
    if not uid:
        return []
    import core.services.visible_runs as _vr

    kandidater = [
        {**kort, "approval_id": aid}
        for aid, kort in _vr.godkendelser_nu().items()
        if str((kort or {}).get("owner_user_id") or "") == uid
    ]
    kandidater.sort(key=lambda k: str(k.get("created_at") or ""), reverse=True)
    return kandidater


def decide(approval_id: str, *, approved: bool,
           answered_by: str | None = None) -> dict[str, Any]:
    """Svar paa en godkendelse. Den ENE vej ind for enhver svarer.

    Delegerer med vilje til `resolve_pending_approval`: dér ligger udloebet,
    ejerskabet, digesten og den atomiske overtagelse allerede, og at flytte
    dem ville vaere at bygge den mest konsekvenstunge sti om uden en fejl at
    rette.
    """
    from core.services.visible_runs_approvals import resolve_pending_approval
    return resolve_pending_approval(approval_id, approved=approved,
                                    answered_by=answered_by)


def state(approval_id: str) -> dict[str, Any] | None:
    """Hvad ved vi om dette kort? None hvis det ikke findes.

    Kaster videre hvis DB-opslaget bag `_get_visible_approval_state` fejler —
    fanges IKKE her. Eneste kalder (2026-09-21, `grep -rn
    "approval_runtime.state("`) er `notifikationer_hydrering._hydrer_approval`,
    hvis eget `except Exception` i `_hydrer` skal se fejlen for at kunne
    skelne «kortet findes ikke» fra «ejeren kunne ikke naas». Et internt net
    her ville goere de to umulige at skelne igen (se
    docs/superpowers/specs/2026-09-21-notifikations-feed-design.md).
    """
    import core.services.visible_runs as _vr
    # Disken, ikke processens kopi: kortet kan vaere skabt i den ANDEN proces.
    kort = _vr.godkendelser_nu().get(approval_id)
    if kort is not None:
        return dict(kort)
    delt = _vr._get_visible_approval_state(approval_id)
    return dict(delt) if delt else None


def sweep_expired() -> dict[str, int]:
    """Fjern udloebne kort. Returnerer hvad der blev fejet.

    Fejningen der manglede: udloeb blev kun tjekket ved svar og ved opstart, saa
    et doedt kort blev liggende og fik tilstanden til at loeve om hvad der var
    i vente. Kaster aldrig.
    """
    ud = {"fejet": 0, "tilbage": 0}
    try:
        import core.services.visible_runs as _vr
        from core.services.visible_runs_approvals import _er_udloebet

        # Fejningen koerer i BEGGE processer. Uden read-modify-write under laas
        # ville den ene kunne gemme sin (aeldre) dict oven paa den andens nye
        # kort — altsaa slette et kort Bjoern venter paa at se.
        aktuelle = _vr.godkendelser_nu()
        doede = [k for k, v in aktuelle.items()
                 if isinstance(v, dict) and _er_udloebet(v)]
        for k in doede:
            _vr.fjern_godkendelse(k)
        if doede:
            logger.info("approval_runtime: fejede %d udloebne kort", len(doede))
        ud["fejet"] = len(doede)
        ud["tilbage"] = len(_vr.godkendelser_nu())
    except Exception:
        logger.warning("approval_runtime: fejningen fejlede", exc_info=True)
    return ud
