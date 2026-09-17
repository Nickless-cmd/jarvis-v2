"""Alle kørende baggrundsopgaver — uanset hvor de kører.

Bjørn 12/9-2026: «et sted hvor brugeren kan se de aktive opgaver der kører,
uanset om det er bash commander eller andre ting».

Der er TO kilder, og det er ikke en designfejl — de to slags arbejde er
virkelig forskellige:

``supervisor``
    Langtidsservicer på serveren (`process_supervisor`): trading-bot, workers,
    pollere. Målt 12/9 kørte fire. De har navne, logfiler og skal kunne stoppes
    og startes uafhængigt af en samtale.

``operator``
    Ad hoc-shells på Bjørns EGEN maskine (`operator_background`), gemt som
    filer i ``/tmp/jarvis-bg/<id>.{log,pid,rc}``. De opstår midt i en opgave og
    dør igen. Målt 12/9 lå der poster fra samme dag.

``agent``
    Scout-agenter (`scout_agent`, før `explore`) — læsende research-agenter i
    agent-registret. Tilføjet 17/9-2026: Jarvis gjorde dem til baggrundsjob fra
    start til slut, og Bjørn: «scout agenter [skal] vises i baggrundsjob panel
    i desk». Før var de usynlige her, selv mens de arbejdede i minutter.

Et panel der kun viste den ene ville være sandt om sin form og tavst om sit
indhold — man ville tro der ikke kørte noget, mens der gjorde.

## Hvorfor operator-siden læses med ÉN kommando

Hver fil kunne læses for sig, men det er en netværkstur over broen pr. fil.
Én compound-kommando giver hele billedet i én tur — samme afvejning som
``hostname`` der hænger på git-status' kommando.

``ps -o stat=`` giver ``T`` for en standset proces, så pause-tilstanden kommer
med i samme svar frem for at skulle gættes.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

_ROD = "/tmp/jarvis-bg"

# Én kommando, ét svar. `stat -c %Y` er filens mtime i sekunder — .pid skrives
# når shellen starter, så den ER starttidspunktet.
_LISTE_CMD = (
    f'for f in {_ROD}/*.pid; do '
    '[ -e "$f" ] || continue; '
    'id=$(basename "$f" .pid); pid=$(cat "$f" 2>/dev/null); '
    f'rc=""; [ -f "{_ROD}/$id.rc" ] && rc=$(cat "{_ROD}/$id.rc" 2>/dev/null); '
    'st="dead"; if kill -0 "$pid" 2>/dev/null; then st=$(ps -o stat= -p "$pid" 2>/dev/null | cut -c1); fi; '
    'start=$(stat -c %Y "$f" 2>/dev/null); '
    'cmd=$(tr "\\n" " " < "$f".cmd 2>/dev/null | cut -c1-120); '
    'echo "$id|$pid|$st|$rc|$start|$cmd"; '
    'done'
)


def _nu() -> float:
    return datetime.now(UTC).timestamp()


def _operator_jobs(uid: str, exec_fn) -> list[dict[str, Any]]:
    """Baggrunds-shells på operatørens maskine. Tom liste hvis broen tier.

    Fail-soft med vilje: en død bro betyder at vi ikke VED om der kører noget
    derovre, og panelet siger det med et eget felt — ikke ved at lade som om
    listen var tom.
    """
    res = exec_fn("operator_bash", {"command": _LISTE_CMD, "_user_id": uid})
    if res.get("status") != "ok":
        raise BroTier(str(res.get("error") or res.get("reason") or "broen svarede ikke"))
    ud = str((res.get("result") or {}).get("stdout") or "")
    jobs: list[dict[str, Any]] = []
    nu = _nu()
    for linje in ud.splitlines():
        dele = linje.strip().split("|")
        if len(dele) < 5 or not dele[0]:
            continue
        jid, pid, st, rc, start = dele[0], dele[1], dele[2], dele[3], dele[4]
        kommando = dele[5] if len(dele) > 5 else ""
        levende = st not in ("dead", "", "Z")
        jobs.append({
            "id": jid,
            "kilde": "operator",
            "navn": jid,
            "kommando": kommando or "(baggrunds-shell)",
            # T = standset af et signal. Den kommer GRATIS med i `ps -o stat=`
            # og skulle ellers gaettes.
            "status": "paused" if st == "T" else ("running" if levende else "exited"),
            "pid": _tal(pid),
            "sekunder": max(0, int(nu - _tal(start))) if _tal(start) else None,
            "exit_code": _tal(rc) if rc.strip() else None,
            "can_pause": levende,
        })
    return jobs


class BroTier(RuntimeError):
    """Broen svarede ikke — vi VED ikke hvad der kører på operatørens maskine."""


def _tal(v: Any) -> int:
    try:
        return int(str(v).strip())
    except Exception:
        return 0


def _supervisor_jobs() -> list[dict[str, Any]]:
    from core.services.process_supervisor import list_processes
    ud = list_processes(include_stopped=True)
    jobs = []
    for p in ud.get("processes") or []:
        sek = p.get("uptime_seconds")
        jobs.append({
            "id": str(p.get("name") or ""),
            "kilde": "supervisor",
            "navn": str(p.get("name") or ""),
            "kommando": str(p.get("command") or ""),
            "status": str(p.get("status") or ""),
            "pid": p.get("pid"),
            "sekunder": int(sek) if isinstance(sek, (int, float)) else None,
            "exit_code": p.get("exit_code"),
            "can_pause": bool(p.get("can_pause")),
        })
    return jobs


#: Scout-agentens tool-policies (`simple_tools_explore._explore_spawn`).
_SCOUT_POLICIES = frozenset({"read-only-runtime", "read-only-workstation"})
_AGENT_AKTIV = frozenset({"planned", "queued", "starting", "running", "active", "waiting"})
#: Hvor længe en FÆRDIG scout står under «Færdige». Den kan ikke ryddes
#: herfra (der er intet at slette — den er en række i registret), så den
#: skal ældes ud af sig selv i stedet for at hobe sig op.
_SCOUT_FAERDIG_VINDUE_S = 3600


def _iso_ts(v: Any) -> float | None:
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _scout_jobs() -> list[dict[str, Any]]:
    """Scout-agenter der kører — og dem der blev færdige den seneste time."""
    from core.runtime.db_agent_runtime import list_agent_registry_entries
    nu = _nu()
    jobs: list[dict[str, Any]] = []
    for a in list_agent_registry_entries(include_completed=True, limit=200):
        if str(a.get("role") or "") != "researcher":
            continue
        if str(a.get("tool_policy") or "") not in _SCOUT_POLICIES:
            continue
        status = str(a.get("status") or "")
        start = _iso_ts(a.get("created_at"))
        aktiv = status in _AGENT_AKTIV
        slut = None if aktiv else (_iso_ts(a.get("completed_at")) or _iso_ts(a.get("updated_at")))
        if not aktiv and (slut is None or nu - slut > _SCOUT_FAERDIG_VINDUE_S):
            continue
        maal = str(a.get("goal") or "").strip().splitlines()
        emne = maal[0] if maal else ""
        jobs.append({
            "id": str(a.get("agent_id") or ""),
            "kilde": "agent",
            "navn": "Scout-agent" + (
                " · din maskine" if a.get("tool_policy") == "read-only-workstation" else ""),
            "kommando": emne[:120] or "(scout)",
            "status": "running" if aktiv else "exited",
            "pid": None,
            "sekunder": int(((nu if aktiv else slut) or nu) - start) if start else None,
            # «failed» er en fejl og skal blive stående under «Kører»-filteret
            # (_skal_vises); en annulleret eller udløbet scout er ikke gået galt.
            "exit_code": None if aktiv else (1 if status == "failed" else 0),
            "can_pause": False,
        })
    return jobs


def liste(*, uid: str = "", exec_fn=None, kun_aktive: bool = True) -> dict[str, Any]:
    """Alle jobs fra begge kilder.

    `kun_aktive` fjerner det der er FÆRDIGT — Bjørn: «de skal automatisk
    forsvinde når opgave er fuldført». Et job der fejlede bliver derimod
    stående: det er ikke fuldført, det er gået galt, og det er netop dem man
    skal se. Et panel der altid er tomt bliver et panel man holder op med at
    åbne.
    """
    jobs = _supervisor_jobs()
    try:
        jobs += _scout_jobs()
    except Exception:
        # Registret er en tilføjelse til panelet, ikke dets fundament: fejler det,
        # skal supervisor- og operator-jobbene stadig vises.
        logger.warning("background_jobs: kunne ikke læse scout-agenter", exc_info=True)
    bro_ok = True
    if exec_fn is not None:
        try:
            jobs += _operator_jobs(uid, exec_fn)
        except Exception as exc:
            bro_ok = False
            logger.debug("background_jobs: operator-siden svarede ikke: %s", exc)
    if kun_aktive:
        jobs = [j for j in jobs if _skal_vises(j)]
    # Koerende foerst, derefter laengst koerende oeverst. Det man skal gribe
    # ind i staar oeverst; det der bare koerer og koerer staar under.
    jobs.sort(key=lambda j: (j["status"] == "exited", -(j.get("sekunder") or 0)))
    return {"jobs": jobs, "bridge_ok": bro_ok}


def _skal_vises(job: dict[str, Any]) -> bool:
    """Kører den, eller gik den galt?

    En afsluttet opgave forsvinder — men KUN hvis den lykkedes. `exit_code`
    forskellig fra 0 er ikke «fuldført», og at skjule den ville betyde at en
    fejl bare stille forsvandt.
    """
    if job.get("status") in ("running", "paused"):
        return True
    kode = job.get("exit_code")
    return kode is not None and int(kode) != 0
