"""Operator-kanalen — owner-gated bro fra containerens bash til Bjørns maskine.

Porteret fra jarvis-code 2026-09-06, men præmissen er en ANDEN og modulet er
derfor ikke en kopi.

I jarvis-code findes kanalen fordi klientens `bash` sidder i et bwrap-fængsel:
stier uden for de mountede findes fysisk, men er usynlige. Kanalen er en vej
udenom det fængsel. Runtime har ikke bwrap (bevidst fravalgt), så det skel
eksisterer ikke her.

Runtime har til gengæld et skarpere skel: `bash` kører på CT105, mens Bjørns
filer, skærm og processer ligger på hans workstation. `operator_*`-værktøjerne
kan nå derover, men de er et andet sæt navne — så en tur der skal arbejde på
hans maskine skal huske at bruge dem, hver gang. Kanalen fjerner det: er den
åben, går `bash` derover af sig selv.

Owner-only, hårdt, ved hver indgang. Kanalen fjerner en godkendelse pr. kald,
og det er kun forsvarligt fordi det er Bjørns egen maskine og hans egen
session. En ikke-owner rammer aldrig omdirigeringen — den ser slet ikke at
kanalen findes.

Tilstanden ligger i runtime_state, IKKE i en modul-global som i jarvis-code.
Dér er der én proces; her er der to (jarvis-api og jarvis-runtime), og en
global ville betyde at kanalen var åben i den ene og lukket i den anden.
"""
from __future__ import annotations

import logging
import shlex
import time
from typing import Any

logger = logging.getLogger(__name__)

_KEY = "operator_channel_by_session"
# En åben kanal er en stående tilladelse. Den skal ikke overleve en glemt
# eftermiddag, så den udløber af sig selv.
_TTL_S = 4 * 3600

#: Hvor længe efter en TTL-udløb kanalen må genopstå af sig selv.
#: Bjørn 5/10-2026: «medmindre du selv har lukket kanalen eller jeg har, så
#: reconnecter den». Fristen er værn mod det absurde — en kanal fra sidste uge
#: må ikke vågne fordi en tilfældig kommando rørte ved den.
_GENOPRET_FRIST_S = 24 * 3600


def _load() -> dict[str, Any]:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(_KEY, {})
        return dict(v) if isinstance(v, dict) else {}
    except Exception:
        return {}


def _save(state: dict[str, Any]) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(_KEY, state)
    except Exception:
        logger.warning("operator_channel: kunne ikke gemme tilstand", exc_info=True)


def _aktiv(post: dict[str, Any]) -> bool:
    if not post.get("open"):
        return False
    aabnet = float(post.get("aabnet") or 0.0)
    return bool(aabnet) and (time.time() - aabnet) < _TTL_S


def _udloebet(post: dict[str, Any]) -> bool:
    """Posten siger stadig åben, men TTL er passeret — ingen lukkede den.

    Forskellen fra «lukket» er hele genopretningen: en post med ``open=False``
    blev lukket af et menneske og må ikke genåbnes; en post der blot er løbet
    tør, faldt af sig selv midt i arbejdet.
    """
    if not post.get("open"):
        return False
    aabnet = float(post.get("aabnet") or 0.0)
    return bool(aabnet) and (time.time() - aabnet) >= _TTL_S


def status(session_id: str) -> dict[str, Any]:
    """Læse-kun. Ingen owner-gate — at spørge er harmløst."""
    post = (_load().get(str(session_id or "").strip()) or {})
    aaben = _aktiv(post)
    ud: dict[str, Any] = {"status": "ok", "open": aaben}
    if aaben:
        ud["aabnet"] = post.get("aabnet")
        ud["udloeber_om_s"] = int(_TTL_S - (time.time() - float(post["aabnet"])))
    return ud


def is_open(session_id: str) -> bool:
    return bool(_aktiv((_load().get(str(session_id or "").strip()) or {})))


def open_channel(session_id: str, *, is_owner: bool) -> dict[str, Any]:
    if not is_owner:
        return {"status": "error", "error": "operator-kanalen er kun for owner"}
    sid = str(session_id or "").strip()
    if not sid:
        return {"status": "error", "error": "session_id mangler"}
    st = _load()
    st[sid] = {"open": True, "aabnet": time.time()}
    _save(st)
    return {"status": "ok", "open": True,
            "text": ("Operator-kanalen er åben: bash kører nu på Bjørns maskine "
                     f"uden godkendelse pr. kald. Lukker af sig selv om {_TTL_S // 3600} timer.")}


def close_channel(session_id: str, *, is_owner: bool) -> dict[str, Any]:
    if not is_owner:
        return {"status": "error", "error": "operator-kanalen er kun for owner"}
    sid = str(session_id or "").strip()
    st = _load()
    # Posten BEVARES med open=False (5/10-2026). Før blev den fjernet, og så
    # kunne «lukket af et menneske» ikke skelnes fra «aldrig åbnet» — og
    # genopretningen nedenfor ville genåbne en kanal nogen havde lukket med
    # vilje. Det er præcis den forskel Bjørn bad om at få respekteret.
    st[sid] = {"open": False, "lukket": time.time()}
    _save(st)
    return {"status": "ok", "open": False, "text": "Operator-kanalen er lukket."}


def current_session_id() -> str:
    """Kanalens nøgle — og den SKAL være den samme som bash'ens.

    Målt 5/10-2026: denne funktion pegede på ``visible_run_context``, som ikke
    findes — importen fejlede i det stille — og faldt derefter til
    ``chat_sessions.current_session_id_ctx``, som heller ikke findes. Begge
    kilder var døde, så nøglen blev ``_default`` for ALLE sessioner: Bjørns
    chat, autonome runs og mine egne ture delte én kanal. Lukkede én af dem,
    faldt en anden stille tilbage til containeren — midt i en tur.

    Rækkefølgen er derfor vendt: den autoritative kontekst først. Og kalderne
    sender nu ``_runtime_session_id`` eksplicit med (se ``_exec_bash`` og
    ``_exec_operator_channel``), så åbning og brug ikke kan pege på hvert sit
    id. Denne funktion er reserve-vejen.
    """
    for modul, navn in (
        ("core.identity.workspace_context", "current_session_id"),
        ("core.services.chat_sessions", "current_session_id_ctx"),
    ):
        try:
            sid = str(getattr(__import__(modul, fromlist=[navn]), navn)() or "")
            if sid:
                return sid
        except Exception:
            continue
    return "_default"


def current_is_owner() -> bool:
    """Owner-gaten. Fail-CLOSED: kan rollen ikke afgoeres, er svaret nej.

    Modsat egress-vaernet, der fejler aabent. Forskellen er hvad en fejl
    koster: dér ville et braekket vaern spaerre alt web-arbejde, her ville det
    give en fremmed adgang til Bjoerns maskine uden godkendelse.
    """
    try:
        from core.identity.workspace_context import current_role
        return str(current_role() or "").strip().lower() in ("", "owner")
    except Exception:
        return False


# ── Omdirigering ────────────────────────────────────────────────────────────

def _absolutte_stier(command: str) -> list[str]:
    try:
        toks = shlex.split(command)
    except Exception:
        toks = str(command or "").split()
    return [t for t in toks if t.startswith("/")]


# Stier der KUN giver mening på hans maskine. Bruges til hintet, ikke til
# omdirigeringen — kanalen er et bevidst valg, ikke en gætteleg.
_WORKSTATION_TEGN = ("/media/projects", "/home/bs/jarvis-code", "/mnt/", "/media/")


def looks_like_workstation_path(command: str, cwd: str | None = None) -> bool:
    kandidater = list(_absolutte_stier(command))
    if cwd:
        kandidater.append(str(cwd))
    return any(k.startswith(t) for k in kandidater for t in _WORKSTATION_TEGN)


def _koer_over_broen(command: str, cwd: str | None) -> dict[str, Any]:
    """Selve bro-kaldet — skilt fra BESLUTNINGEN om at kalde det."""
    try:
        from core.tools.simple_tools import execute_tool
        args: dict[str, Any] = {"command": command}
        if cwd:
            args["cwd"] = cwd
        r = execute_tool("operator_bash", args)
    except Exception as exc:
        logger.warning("operator_channel: omdirigering fejlede", exc_info=True)
        return {"status": "error",
                "error": f"operator-kanalen kunne ikke nå din maskine: {exc}"}
    if isinstance(r, dict):
        r = dict(r)
        r["via"] = "operator-kanal"
    return r


def _naaede_frem(r: Any) -> bool:
    """Kom svaret fra hans maskine — eller var det broen der svigtede?

    Afgør om en udløbet kanal må fornyes: en kommando der fejler på hans
    maskine (exit_code 1) er BEVIS på at broen virker; ``bridge_not_connected``
    er det modsatte. Uden den skelnen ville en kanal hvis bro er nede blive
    fornyet i det uendelige af fejlende kald.
    """
    if not isinstance(r, dict):
        return False
    if "bridge" in str(r.get("error") or "").lower():
        return False
    return r.get("status") != "error"


def _forny(session_id: str) -> None:
    """Genåbn en kanal der faldt af sig selv. Kaldes KUN når broen svarede."""
    st = _load()
    st[str(session_id)] = {"open": True, "aabnet": time.time(), "genaabnet": True}
    _save(st)


def maybe_reroute_bash(command: str, cwd: str | None, *, is_owner: bool,
                       session_id: str) -> dict[str, Any] | None:
    """Kør kommandoen på Bjørns maskine hvis kanalen er åben. Ellers None.

    None betyder «ikke min sag» — så kører bash normalt på containeren.

    Er kanalen FALDET AF SIG SELV (TTL løbet tør, ingen har lukket den),
    forsøger den at genopstå: kommandoen køres over broen, og svarede broen,
    fornyes kanalen. Svigtede broen, fornyes intet — en kanal der ikke kan nå
    sin maskine skal ikke stå åben. Se `_GENOPRET_FRIST_S`.
    """
    if not is_owner or not command.strip():
        return None
    sid = str(session_id or "").strip()
    if is_open(sid):
        return _koer_over_broen(command, cwd)
    post = (_load().get(sid) or {})
    if not _udloebet(post):
        return None
    alder = time.time() - float(post["aabnet"]) - _TTL_S
    if alder > _GENOPRET_FRIST_S:
        return None
    r = _koer_over_broen(command, cwd)
    if _naaede_frem(r):
        _forny(sid)
        r["kanal"] = {"genaabnet": True, "udloebet_for_s": int(alder)}
        logger.info("operator_channel: genåbnede en udløbet kanal (%ss)", int(alder))
    return r


def closed_channel_hint(command: str, cwd: str | None, *, is_owner: bool,
                        session_id: str) -> str:
    """Én linje til modellen når et kald tydeligvis sigtede mod hans maskine.

    Uden den ville en tom eller fejlende bash ligne at filen ikke findes —
    frem for at den ligger et andet sted end der hvor kommandoen kørte.
    """
    if not is_owner or is_open(session_id):
        return ""
    if not looks_like_workstation_path(command, cwd):
        return ""
    return ("[operator-kanal] Den sti ligger på Bjørns maskine, ikke på "
            "containeren hvor denne bash kørte. Åbn kanalen med "
            "operator_channel(action='open'), så går bash derover af sig selv "
            "— eller brug operator_bash til det enkelte kald.")


def kanal_note(session_id: str) -> str:
    """Én linje når kanalen faldt af sig selv — til bash-svaret.

    Bjørn 5/10-2026: «fiks kanalen så du får besked med det samme den ryger».
    Uden den kørte kommandoen på containeren i det stille, og et svar der
    ligner «filen findes ikke» kunne i virkeligheden betyde «du målte det
    forkerte sted». Det er den fejlform hele 5/10 handlede om.

    Fyrer KUN når kanalen faldt af sig selv og var for gammel til at genopstå.
    Er den bevidst lukket, er der intet at sige — Bjørn lukkede den selv. Er
    den genoprettet i samme kald, er noten støj; genopretningen melder sig selv
    via `kanal.genaabnet` på svaret.
    """
    post = (_load().get(str(session_id or "").strip()) or {})
    if not _udloebet(post):
        return ""
    alder = time.time() - float(post["aabnet"]) - _TTL_S
    if alder <= _GENOPRET_FRIST_S:
        return ""
    timer = max(1, int(alder // 3600))
    return (f"[operator-kanal] kanalen udløb for {timer} t siden og blev IKKE "
            "genåbnet — denne kommando kørte på serveren, ikke på Bjørns "
            "maskine. Åbn igen med operator_channel(action='open').")
