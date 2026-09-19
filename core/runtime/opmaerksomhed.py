"""Tilstands-hjernen — ÉN samlet opmærksomhedstilstand pr. arbejdsrum.

Bjørn 19/9-2026, efter Jarvis' kortlægning af Codex' kæledyr (codex-pet.md,
efterprøvet samme dag): det overførbare er ikke figuren, det er hjernen bag
den. Codex komprimerer alt hvad der foregår i ens tråde til ét kropsudtryk,
og vælger mellem mange tråde med én prioritet (`Gd` i avatar-overlay'et,
læst ordret):

    waiting 0 › failed 1 › review 2 › running 3 › idle 4

Lavest vinder. Det der venter på DIG slår det der fejlede, og et færdigt
svar slår et der stadig arbejder. Samme rækkefølge her.

## Hvor tilstandene kommer fra

- **waiting** — de godkendelser i køen (`cowork_feed.build_queue`, samme kø
  som Mission Controls «Afventer dig») der HOLDER en samtale: kilden
  `capability`, et run der står og venter på dit ja. Forslag og initiativer
  (`proposal`/`initiative`) er en indbakke, ikke en blokering — de tælles i
  `indbakke` og driver ikke tilstanden. Målt ved første udrulning 19/9: 20
  forslag og 4 initiativer, 0 blokerende. Med dem som «waiting» havde
  tilstanden stået på «Venter på dig» altid — og så betyder den intet.
  Codex' `waiting` er netop en tråd der er gået i stå til du svarer.
- **running** — levende runs i `run_event_log`, filtreret til samtaler i
  dette arbejdsrum. Autonome kørsler tælles for sig (`baggrund`) og driver
  IKKE tilstanden: målt 112 på tre døgn — de ville holde figuren i «arbejder»
  hele tiden uden at noget angik brugeren.
- **review / failed** — noteret når en tur slutter (`noter_afsluttet`, kaldt
  fra detached_run lige ved push-beslutningen), men KUN hvis ingen så turen
  til ende (`was_consumed_or_active`). Codex: `success → review` — «færdigt,
  se resultatet». Så du kiggede med, er der intet at gennemgå.

## Hvornår et punkt forsvinder

- samtalen åbnes (`set(session_id)` — klienten siger det)
- en ny tur starter i samme samtale (`glem_session`)
- efter `_LEVETID_S` (et døgn) — gamle nyheder skal ikke hænge

Punkterne gemmes i runtime_state_kv pr. arbejdsrum, så en genstart ikke
sletter at et svar ligger og venter.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Final

logger = logging.getLogger(__name__)

__all__ = [
    "PRIORITET", "tilstand_for", "noter_afsluttet", "set", "glem_session",
    "rum_for_session", "aktivitet",
]

# Codex' `Gd`, ordret. Lavest vinder.
PRIORITET: Final[dict[str, int]] = {"waiting": 0, "failed": 1, "review": 2, "running": 3, "idle": 4}

ETIKET: Final[dict[str, str]] = {
    "waiting": "Venter på dig",
    "failed": "Noget gik galt",
    "review": "Færdig — se svaret",
    "running": "Arbejder",
    "idle": "Intet kræver dig",
}

_LEVETID_S: Final[float] = 24 * 3600
_MAKS_PUNKTER: Final[int] = 50
_GRACE_S: Final[float] = 5.0  # som push: giv en levende klient tid til at dræne
_lock = threading.Lock()


# ── arbejdsrum ────────────────────────────────────────────────────────────

def _standard_rum() -> str:
    from core.identity.workspace_context import current_workspace_name
    return (current_workspace_name() or "").strip()


def rum_for_session(session_id: str) -> str:
    """Samtalens arbejdsrum. Ustemplede (legacy) samtaler hører til
    standard-rummet — samme regel som session_access: de er ejerens."""
    sid = (session_id or "").strip()
    if sid:
        try:
            from core.services.chat_sessions import get_session_owner
            from core.identity.session_access import arbejdsrum_for
            ejer = (get_session_owner(sid) or "").strip()
            if ejer:
                return arbejdsrum_for(ejer)
        except Exception:
            logger.debug("opmaerksomhed: ejer af %s kunne ikke slås op", sid, exc_info=True)
    from core.identity.workspace_context import _DEFAULT_STATE
    return _DEFAULT_STATE.workspace_name


# ── lager ─────────────────────────────────────────────────────────────────

def _noegle(rum: str) -> str:
    return f"opmaerksomhed:{rum}"


def _laes(rum: str) -> list[dict[str, Any]]:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(_noegle(rum), [])
        return [p for p in v if isinstance(p, dict)] if isinstance(v, list) else []
    except Exception:
        logger.warning("opmaerksomhed: kunne ikke læse %s", rum, exc_info=True)
        return []


def _skriv(rum: str, punkter: list[dict[str, Any]]) -> None:
    from core.runtime.db_core import set_runtime_state_value
    set_runtime_state_value(_noegle(rum), punkter[-_MAKS_PUNKTER:])


def _friske(punkter: list[dict[str, Any]], nu: float) -> list[dict[str, Any]]:
    return [p for p in punkter if nu - float(p.get("tid") or 0) < _LEVETID_S]


# ── skrivning ─────────────────────────────────────────────────────────────

def _titel(session_id: str) -> str:
    try:
        from core.services.chat_sessions import get_chat_session
        s = get_chat_session(session_id) or {}
        return str(s.get("title") or "").strip()[:80]
    except Exception:
        return ""


def _noter(*, session_id: str, run_id: str, tilstand: str, tekst: str = "") -> None:
    rum = rum_for_session(session_id)
    nu = time.time()
    punkt = {"session_id": session_id, "run_id": run_id, "tilstand": tilstand,
             "titel": _titel(session_id), "tekst": (tekst or "")[:200], "tid": nu}
    with _lock:
        # Ét punkt pr. samtale: den seneste tur er den der gælder.
        punkter = [p for p in _friske(_laes(rum), nu) if p.get("session_id") != session_id]
        punkter.append(punkt)
        _skriv(rum, punkter)


def _vurder_afsluttet(log_run_id: str, indre_run_id: str, session_id: str) -> None:
    from core.services import run_event_log as rel
    if rel.was_consumed_or_active(log_run_id):
        return  # nogen så turen til ende — intet at gennemgå
    status = ""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            r = conn.execute("SELECT status, error FROM visible_runs WHERE run_id = ?",
                             (indre_run_id or log_run_id,)).fetchone()
        status = str(r[0] or "") if r else ""
        fejl = str(r[1] or "") if r else ""
    except Exception:
        logger.warning("opmaerksomhed: status for %s kunne ikke læses", indre_run_id, exc_info=True)
        return
    if status == "completed":
        from core.services.push_dispatcher import _last_assistant_preview
        tekst = _last_assistant_preview(session_id)
        if tekst:  # rent internt arbejde uden svar er ikke noget at se
            _noter(session_id=session_id, run_id=indre_run_id or log_run_id, tilstand="review", tekst=tekst)
    elif status in ("failed", "interrupted"):
        _noter(session_id=session_id, run_id=indre_run_id or log_run_id, tilstand="failed",
               tekst=fejl or "Turen blev afbrudt")
    # cancelled: brugeren stoppede selv. recovering: genoptagelsen er i gang.


def noter_afsluttet(log_run_id: str, indre_run_id: str, session_id: str) -> None:
    """Kaldes fra detached_run når en tur slutter. Vurderes efter samme grace
    som push, så en klient der stadig dræner de sidste frames når at tælle."""
    if not (session_id or "").strip():
        return
    try:
        t = threading.Timer(_GRACE_S, _vurder_afsluttet, args=(log_run_id, indre_run_id, session_id))
        t.daemon = True
        t.start()
    except Exception:
        logger.warning("opmaerksomhed: kunne ikke planlægge %s", log_run_id, exc_info=True)


def set(session_id: str, rum: str | None = None) -> bool:  # noqa: A001 — «set» som i «har set»
    """Brugeren har åbnet samtalen — dens punkt forsvinder."""
    sid = (session_id or "").strip()
    if not sid:
        return False
    r = (rum or "").strip() or rum_for_session(sid)
    with _lock:
        punkter = _laes(r)
        rest = [p for p in punkter if p.get("session_id") != sid]
        if len(rest) == len(punkter):
            return False
        _skriv(r, rest)
    return True


def glem_session(session_id: str) -> None:
    """En ny tur starter — den forrige turs udfald er ikke længere nyheden."""
    try:
        set(session_id)
    except Exception:
        logger.debug("opmaerksomhed: glem_session fejlede", exc_info=True)


# ── læsning ───────────────────────────────────────────────────────────────

def _pynt_navn(navn: str) -> str:
    n = (navn or "").strip()
    for praefiks in ("operator_", "mcp__"):
        if n.startswith(praefiks):
            n = n[len(praefiks):]
    return n.replace("_", " ").strip().capitalize() or "Arbejder"


def aktivitet(frames: list[str]) -> str:
    """Hvad laver han LIGE NU — læst bagfra i runnets egen strøm.

    Codex' taleboble viser aktiviteten (værktøj, spørgsmål, plan). Her: den
    seneste blok. Et værktøj vises med Jarvis' EGEN beskrivelse af kaldet
    (`description`, samme felt som værktøjslinjen i desk og på mobilen), og
    ellers kommandoen eller stien; tænkning og tekst får hver sin linje.
    """
    import json as _json
    deltaer: dict[int, str] = {}
    for f in reversed(frames):
        linje = next((l for l in f.split("\n") if l.startswith("data: ")), "")
        if not linje:
            continue
        try:
            d = _json.loads(linje[6:])
        except Exception:
            continue
        typ = d.get("type")
        if typ == "content_block_delta":
            delta = d.get("delta") or {}
            if delta.get("type") == "input_json_delta":
                deltaer[int(d.get("index", -1))] = str(delta.get("partial_json") or "") + deltaer.get(int(d.get("index", -1)), "")
            continue
        if typ != "content_block_start":
            continue
        blok = d.get("content_block") or {}
        art = blok.get("type")
        if art == "thinking":
            return "Tænker…"
        if art == "text":
            return "Skriver svaret…"
        if art == "tool_use":
            args: dict[str, Any] = {}
            try:
                args = _json.loads(deltaer.get(int(d.get("index", -1)), "") or "{}")
            except Exception:
                args = {}
            for felt in ("description", "command", "command_text", "path", "target_path", "query", "url"):
                v = args.get(felt) if isinstance(args, dict) else None
                if isinstance(v, str) and v.strip():
                    tekst = " ".join(v.split())
                    return tekst[:140] if felt == "description" else f"{_pynt_navn(str(blok.get('name') or ''))}: {tekst[:120]}"
            return _pynt_navn(str(blok.get("name") or ""))
    return ""


def _koerende(rum: str) -> list[dict[str, Any]]:
    try:
        from core.services import run_event_log as rel
        ud = []
        for rid in rel.live_run_ids():
            sid = rel.session_for_run(rid) or ""
            if sid and rum_for_session(sid) == rum:
                ud.append({"session_id": sid, "run_id": rid, "tilstand": "running",
                           "titel": _titel(sid), "tekst": aktivitet(rel.hale(rid)),
                           "tid": time.time()})
        return ud
    except Exception:
        logger.warning("opmaerksomhed: levende runs kunne ikke læses", exc_info=True)
        return []


def _baggrund() -> int:
    """Autonome kørsler i gang (sidste halve time — friskheds-vagt mod zombier)."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            r = conn.execute(
                "SELECT count(*) FROM visible_runs WHERE run_id LIKE 'autonomous-%' "
                "AND status = 'running' AND started_at > datetime('now', '-30 minutes')"
            ).fetchone()
        return int(r[0] or 0) if r else 0
    except Exception:
        return 0


_BLOKERENDE_KILDER: Final[frozenset[str]] = frozenset({"capability"})


def _koe(user_id: str | None, is_owner: bool) -> tuple[list[dict[str, Any]], int]:
    """(blokerende punkter, antal i indbakken)."""
    try:
        from core.services import cowork_feed
        items = cowork_feed.build_queue(user_id=user_id, is_owner=is_owner)
    except Exception:
        logger.warning("opmaerksomhed: godkendelses-køen kunne ikke læses", exc_info=True)
        return [], 0
    blok = [i for i in items if str(i.get("source") or "") in _BLOKERENDE_KILDER]
    return _venter(blok), len(items) - len(blok)


def _venter(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ud = []
    for i in items:
        ud.append({"session_id": str(i.get("session_id") or ""), "run_id": "", "tilstand": "waiting",
                   "titel": str(i.get("title") or i.get("kind") or "Godkendelse")[:80],
                   "tekst": str(i.get("summary") or i.get("detail") or "")[:200],
                   "tid": time.time(), "id": str(i.get("id") or "")})
    return ud


def tilstand_for(*, rum: str | None = None, user_id: str | None = None,
                 is_owner: bool = True) -> dict[str, Any]:
    """Den samlede tilstand. Rækkefølge: prioritet, så nyeste først."""
    r = (rum or "").strip() or _standard_rum()
    nu = time.time()
    with _lock:
        gemte = _friske(_laes(r), nu)
    koerer = _koerende(r)
    # En samtale der kører IGEN er ikke længere «færdig» eller «fejlet».
    koerende_sid = {k["session_id"] for k in koerer}
    gemte = [p for p in gemte if p.get("session_id") not in koerende_sid]
    venter, indbakke = _koe(user_id, is_owner)
    punkter = venter + gemte + koerer
    punkter.sort(key=lambda p: (PRIORITET.get(str(p.get("tilstand")), 9), -float(p.get("tid") or 0)))
    tilstand = str(punkter[0]["tilstand"]) if punkter else "idle"
    antal = {k: sum(1 for p in punkter if p.get("tilstand") == k) for k in ("waiting", "failed", "review", "running")}
    return {
        "tilstand": tilstand,
        "etiket": ETIKET[tilstand],
        "antal": antal,
        "baggrund": _baggrund(),
        "indbakke": indbakke,
        "fokus": punkter[0] if punkter else None,
        "punkter": punkter[:20],
    }
