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
import json
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
    # Kanaltilstand er en routingbeslutning, ikke almindelig cachedata: en
    # stale læsning kan sende en workstation-kommando til containeren.
    from core.runtime.db_core import connect
    with connect() as conn:
        row = conn.execute(
            "SELECT value_json FROM runtime_state_kv WHERE key = ?", (_KEY,)
        ).fetchone()
    if row is None:
        return {}
    value = json.loads(str(row["value_json"]))
    if not isinstance(value, dict):
        raise ValueError("operator-kanalens tilstand er ugyldig")
    return value


def _opdater_post(session_id: str, post: dict[str, Any]) -> None:
    """Skriv ÉN sessions post — atomisk.

    Målt 7/10-2026: `open_channel`, `close_channel` og `_forny` læste HELE
    ordbogen, satte én nøgle og skrev HELE ordbogen tilbage. Med to processer
    (api + runtime) der hver har sin egen 2-sekunders læse-cache betød det, at
    en frisk åbning kunne blive overskrevet af et forældet billede fra en anden
    skriver — kanalen «glap» uden at nogen havde lukket den. Læs-gene-skriv
    sker nu i én IMMEDIATE-transaktion, så kun denne nøgle ændres og ingen
    andens arbejde tabes.

    Fejler den, KASTER den. Kalderne fanger og svarer `status: error` — en
    kvittering på noget der ikke blev gemt er præcis den tavse fejl kanalen
    skal være fri for.
    """
    from datetime import UTC, datetime

    from core.runtime.db_core import clear_runtime_state_cache, connect

    key = str(session_id or "").strip()
    if not key:
        raise ValueError("session_id mangler")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT value_json FROM runtime_state_kv WHERE key = ?", (_KEY,)
        ).fetchone()
        st = json.loads(str(row["value_json"])) if row is not None else {}
        if not isinstance(st, dict):
            raise ValueError("operator-kanalens tilstand er ugyldig")
        st[key] = post
        conn.execute(
            "INSERT INTO runtime_state_kv (key, value_json, updated_at) "
            "VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET "
            "value_json = excluded.value_json, updated_at = excluded.updated_at",
            (_KEY, json.dumps(st, ensure_ascii=False), datetime.now(UTC).isoformat()),
        )
        conn.commit()
    # Egen proces skal se sin egen skrivning straks; læse-cachen er 2 s gammel.
    clear_runtime_state_cache()


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
    try:
        post = (_load().get(str(session_id or "").strip()) or {})
    except Exception:
        # En læsefejl må ikke blive en 500 i UI'et — men den må heller ikke
        # ligne «lukket, alt vel». Svaret siger eksplicit at det er ukendt;
        # `open: False` betyder her «ikke bevist åben», aldrig «lukket med vilje».
        logger.warning("operator_channel: status kunne ikke læses", exc_info=True)
        return {"status": "error", "open": False, "ukendt": True,
                "error": "kanalens tilstand kunne ikke læses"}
    aaben = _aktiv(post)
    ud: dict[str, Any] = {"status": "ok", "open": aaben}
    if aaben:
        ud["aabnet"] = post.get("aabnet")
        ud["udloeber_om_s"] = int(_TTL_S - (time.time() - float(post["aabnet"])))
    return ud


def is_open(session_id: str) -> bool:
    """Er kanalen åben? KASTER ved læsefejl — med vilje.

    Returnerede den ``False`` på en DB-fejl, ville `maybe_reroute_bash` svare
    «kanalen er lukket» og køre Bjørns kommando på containeren i det stille.
    Det er netop den fejl kanalen findes for at forhindre, så usikkerhed skal
    op, ikke skjules. Kalderen (`_exec_bash`) fanger og afviser kommandoen.
    """
    return bool(_aktiv((_load().get(str(session_id or "").strip()) or {})))


def open_channel(session_id: str, *, is_owner: bool) -> dict[str, Any]:
    if not is_owner:
        return {"status": "error", "error": "operator-kanalen er kun for owner"}
    sid = str(session_id or "").strip()
    if not sid:
        return {"status": "error", "error": "session_id mangler"}
    try:
        _opdater_post(sid, {"open": True, "aabnet": time.time()})
    except Exception:
        logger.warning("operator_channel: åbning kunne ikke gemmes", exc_info=True)
        return {"status": "error", "error": "operator-kanalen kunne ikke åbnes: tilstanden er utilgængelig"}
    return {"status": "ok", "open": True,
            "text": ("Operator-kanalen er åben: bash kører nu på Bjørns maskine "
                     f"uden godkendelse pr. kald. Lukker af sig selv om {_TTL_S // 3600} timer.")}


def close_channel(session_id: str, *, is_owner: bool) -> dict[str, Any]:
    if not is_owner:
        return {"status": "error", "error": "operator-kanalen er kun for owner"}
    sid = str(session_id or "").strip()
    try:
        # Bevar posten, så manuel lukning ikke forveksles med TTL-udløb.
        _opdater_post(sid, {"open": False, "lukket": time.time()})
    except Exception:
        logger.warning("operator_channel: lukning kunne ikke gemmes", exc_info=True)
        return {"status": "error", "error": "operator-kanalen kunne ikke lukkes: tilstanden er utilgængelig"}
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
    _opdater_post(str(session_id),
                  {"open": True, "aabnet": time.time(), "genaabnet": True})


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
        try:
            _forny(sid)
        except Exception:
            logger.warning("operator_channel: fjernkommando udført, men fornyelse fejlede",
                           exc_info=True)
            r["kanal"] = {"note": "[operator-kanal] Kommandoen blev udført på "
                          "workstation, men kanalens fornyelse kunne ikke gemmes."}
        else:
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
