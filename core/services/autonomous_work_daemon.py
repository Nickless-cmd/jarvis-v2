"""Autonomous Work Daemon — Jarvis works on his own when Bjørn is away.

Jarvis' PLAN_WILD_IDEAS #12 (2026-04-20). Activates during low-activity
periods. Proposes work from a whitelist of allowed activities — never
direct mutation outside the proposal system.

Philosophy: this daemon *plans* and *logs*. It does not execute
destructive actions. It files work-proposals that Bjørn/Jarvis can
inspect and approve. For tiny self-contained actions (like incubator
seed creation), it calls through to the existing services.

Whitelist (allowed proposal types):
- memory_consolidate  — summarize recent day into consolidated notes
- incubator_seed      — nudge creative_instinct to generate seeds
- research            — queue a web_search for an incubator topic (proposal)
- workspace_refactor  — propose edits to evolvable work-prompt files
- blog_draft          — if Bjørn asked for one, draft outline

Rate limit: max 3 proposals per hour, with low-activity detection gating
the daemon itself.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.runtime.workspace_paths import shared_dir

logger = logging.getLogger(__name__)

_LOG_MAX = 300
_MAX_PROPOSALS_PER_HOUR = 3
_LOW_ACTIVITY_MINUTES = 15

_ALLOWED_TYPES: tuple[str, ...] = (
    "memory_consolidate",
    "incubator_seed",
    "research",
    "workspace_refactor",
    "blog_draft",
)


def _storage_path() -> Path:
    return shared_dir() / "runtime" / "autonomous_work_log.json"


def _load() -> list[dict[str, Any]]:
    path = _storage_path()
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception as exc:
        logger.warning("autonomous_work: load failed: %s", exc)
    return []


def _save(items: list[dict[str, Any]]) -> None:
    if len(items) > _LOG_MAX:
        items = items[-_LOG_MAX:]
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("autonomous_work: save failed: %s", exc)


def _proposals_last_hour() -> int:
    log = _load()
    cutoff = datetime.now(UTC) - timedelta(hours=1)
    count = 0
    for entry in reversed(log):
        try:
            ts = datetime.fromisoformat(str(entry.get("at")).replace("Z", "+00:00"))
            if ts >= cutoff:
                count += 1
            else:
                break
        except Exception:
            continue
    return count


def _is_low_activity() -> tuple[bool, str]:
    """Low-activity = no visible runs in last _LOW_ACTIVITY_MINUTES."""
    try:
        from core.runtime.db import recent_visible_runs
        runs = recent_visible_runs(limit=5) or []
        if not runs:
            return True, "no-runs"
        latest = runs[0]
        ts = str(latest.get("started_at") or "")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            minutes_since = (datetime.now(UTC) - dt).total_seconds() / 60
            if minutes_since >= _LOW_ACTIVITY_MINUTES:
                return True, f"idle-{int(minutes_since)}m"
            return False, f"active-{int(minutes_since)}m-ago"
        except Exception:
            return True, "cannot-parse-ts"
    except Exception:
        return True, "db-unavailable"


def _pending_initiatives() -> list[dict[str, Any]]:
    try:
        from core.services.initiative_queue import get_pending_initiatives
        return list(get_pending_initiatives() or [])
    except Exception:
        return []


def _log_entry(entry: dict[str, Any]) -> None:
    log = _load()
    log.append(entry)
    _save(log)


def _file_proposal(
    *,
    proposal_type: str,
    title: str,
    details: dict[str, Any],
    rationale: str,
) -> str:
    """Record a work proposal for later execution/approval."""
    if proposal_type not in _ALLOWED_TYPES:
        raise ValueError(f"proposal_type not whitelisted: {proposal_type}")
    prop_id = f"aw-{uuid4().hex[:12]}"
    entry = {
        "proposal_id": prop_id,
        "at": datetime.now(UTC).isoformat(),
        "type": proposal_type,
        "title": str(title)[:160],
        "details": dict(details),
        "rationale": str(rationale)[:400],
        "status": "pending",
    }
    _log_entry(entry)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "autonomous_work.proposal",
            {
                "proposal_id": prop_id,
                "type": proposal_type,
                "title": entry["title"],
            },
        )
    except Exception:
        pass
    return prop_id


# --- Individual planners ---

def _maybe_propose_memory_consolidate() -> str | None:
    """Propose a daily memory consolidation when ~end of day locally."""
    from core.util.timezone import dk_now as _dk_now
    now_local = _dk_now()
    # Trigger window: 22:00-00:00 local, once per day
    if not (22 <= now_local.hour):
        return None
    log = _load()
    today_key = now_local.date().isoformat()
    for e in log:
        if e.get("type") == "memory_consolidate" and str(e.get("at", ""))[:10] == today_key:
            return None  # already proposed today
    return _file_proposal(
        proposal_type="memory_consolidate",
        title="Consolidate today's memory notes",
        details={"date": today_key},
        rationale="End-of-day window; roll up today's private-brain fragments.",
    )


def _maybe_nudge_incubator() -> str | None:
    """If incubator is sparse, nudge creative_instinct to generate."""
    try:
        from core.services.creative_instinct_daemon import build_creative_instinct_surface
        s = build_creative_instinct_surface()
        active_seeds = int(s.get("active_seeds") or 0)
        if active_seeds >= 3:
            return None
    except Exception:
        return None
    # Trigger creative_instinct tick directly (it has its own cadence gate)
    try:
        from core.services.creative_instinct_daemon import tick as ci_tick
        ci_tick(0.0)
    except Exception:
        pass
    return _file_proposal(
        proposal_type="incubator_seed",
        title="Nudged creative_instinct for fresh idea seeds",
        details={},
        rationale="Incubator had <3 active seeds.",
    )


def _maybe_propose_research() -> str | None:
    """Vælg ét maturing seed der IKKE allerede har et ventende forslag.

    ⚠️ RETTET 3/11-2026. Før: `list_seeds(status="maturing")[:1]` — altid det
    første element i en usorteret liste. Målt: 294 identiske forslag om
    `seed-616b2bc12b` over seks dage, mens de 11 andre maturing seeds aldrig
    blev foreslået. Planneren var ikke «ivrig», den var fastlåst.
    """
    try:
        from core.services.creative_instinct_daemon import list_seeds
        maturing = list(list_seeds(status="maturing"))
    except Exception:
        return None
    if not maturing:
        return None

    # Hvilke seeds har allerede et ventende forslag? Dem springer vi over —
    # ellers får det samme seed et nyt forslag hvert tick.
    optagede = {
        str((e.get("details") or {}).get("seed_id"))
        for e in _load()
        if e.get("status") == "pending" and e.get("type") == "research"
    }
    ledige = [s for s in maturing if str(s.get("seed_id")) not in optagede]
    if not ledige:
        # Alle maturing seeds har et ventende forslag. Det er IKKE et signal om
        # at producere et mere — det er køen der venter på behandling.
        return None

    seed = ledige[0]
    return _file_proposal(
        proposal_type="research",
        title=f"Research for seed: {str(seed.get('spark', ''))[:80]}",
        details={"seed_id": seed.get("seed_id"), "spark": seed.get("spark")},
        rationale="Maturing seed would benefit from external research.",
    )


def _plan_once() -> list[str]:
    """Run planning passes and return list of created proposal_ids."""
    created: list[str] = []
    remaining = max(0, _MAX_PROPOSALS_PER_HOUR - _proposals_last_hour())
    planners = (
        _maybe_propose_memory_consolidate,
        _maybe_nudge_incubator,
        _maybe_propose_research,
    )
    for planner in planners:
        if remaining <= 0:
            break
        try:
            pid = planner()
            if pid:
                created.append(pid)
                remaining -= 1
        except Exception as exc:
            logger.debug("autonomous_work planner %s failed: %s", planner.__name__, exc)
    return created


def _pending_count() -> int:
    return sum(1 for e in _load() if e.get("status") == "pending")


# --- Forbruger (C3, 3/11-2026) ---------------------------------------------
#
# Målt før denne blev bygget: 300 poster, ALLE `pending`. 294 af dem var det
# SAMME forslag om det SAMME seed — `_maybe_propose_research` tog
# `list_seeds(status="maturing")[:1]`, altså altid det første element i en
# usorteret liste, og filede et nyt identisk forslag hvert 15. minut i seks
# dage. De 11 andre maturing seeds blev aldrig foreslået.
#
# Forbrugeren gør tre ting, og kun det den kan gøre ærligt:
#   1. DEDUPLIKERER — én repræsentant per (type, nøgle), resten lukkes som
#      `rejected` med en note der peger på repræsentanten.
#   2. VERIFICERER GRUNDLAGET — findes seed'et? er datoen passeret? blev
#      handlingen allerede udført ved oprettelsen? Et forslag hvis grundlag er
#      væk lukkes som `rejected` med den faktiske grund.
#   3. BEVARER det levende — men nu som ÉT synligt forslag i stedet for 294.
#
# Den UDFØRER ikke netværksarbejde (research) automatisk. Et research-forslag er
# en beslutning om hvad der er værd at undersøge, ikke en rutine — og et
# automatisk web_search ville være en ekstern handling ingen har set.

def _forslag_noegle(entry: dict[str, Any]) -> str:
    """Stabil identitet for et forslag. To forslag med samme nøgle er dubletter.

    Nøglen er (type, grundlag) — ikke titlen, som kan variere i længde for det
    samme seed. `details` bærer grundlaget: `seed_id` for research, `date` for
    memory_consolidate.
    """
    typ = str(entry.get("type") or "")
    details = entry.get("details") or {}
    if not isinstance(details, dict):
        details = {}
    if typ == "research":
        return f"research|{details.get('seed_id') or entry.get('title') or ''}"
    if typ == "memory_consolidate":
        return f"memory_consolidate|{details.get('date') or ''}"
    return f"{typ}|{entry.get('title') or ''}"


def _grundlag_findes(entry: dict[str, Any]) -> tuple[bool, str]:
    """Lever forslagets grundlag stadig? Returnerer (ok, begrundelse).

    `ok=False` betyder at forslaget beskriver noget der ikke længere er sandt —
    og så skal det lukkes, ikke blive liggende som om det venter på noget.
    """
    typ = str(entry.get("type") or "")
    details = entry.get("details") or {}
    if not isinstance(details, dict):
        details = {}

    if typ == "research":
        seed_id = details.get("seed_id")
        if not seed_id:
            return False, "forslaget bærer intet seed_id"
        try:
            from core.services.creative_instinct_daemon import list_seeds
            seed = next((s for s in list_seeds() if s.get("seed_id") == seed_id), None)
        except Exception as exc:  # butikken kan ikke læses: grundlaget er UBEKRÆFTET, ikke dødt — en manglende måling må ikke ligne en afvisning
            return True, f"seed-opslag fejlede ({type(exc).__name__}), grundlag uafklaret"
        if seed is None:
            return False, f"seed {seed_id} findes ikke længere"
        status = str(seed.get("status") or "")
        if status == "withered":
            return False, f"seed {seed_id} er withered"
        if status == "adopted":
            return False, f"seed {seed_id} er allerede adopted"
        return True, f"seed {seed_id} er {status}"

    if typ == "memory_consolidate":
        dato = str(details.get("date") or "")
        if not dato:
            return False, "forslaget bærer ingen dato"
        try:
            from datetime import date as _date
            d = _date.fromisoformat(dato)
        except Exception:  # utolkbar dato: behandl som aktuel — en dårlig gætning må ikke lukke et forslag
            return True, f"datoen '{dato}' kunne ikke tolkes"
        # En konsolidering for en dag der er passeret med mere end et døgn er
        # forældet: noterne for den dag er ikke længere «i dag».
        alder = (datetime.now(UTC).date() - d).days
        if alder > 1:
            return False, f"dagen {dato} ligger {alder} dage tilbage"
        return True, f"dagen {dato} er aktuel"

    if typ == "incubator_seed":
        # Handlingen blev udført i `_maybe_nudge_incubator` FØR forslaget blev
        # fil'et — `ci_tick` kaldes på linjen ovenover. Forslaget er derfor en
        # KVITTERING, ikke ventende arbejde, og `pending` var en løgn.
        return False, "handlingen blev udført ved oprettelsen (ci_tick)"

    return True, "typen har intet automatisk grundlagstjek"


def consume_proposals(*, max_age_days: int = 14) -> dict[str, Any]:
    """Behandl køen: luk det døde med begrundelse, bevar det levende.

    Kaldes fra `tick()` FØR produktions-gaten, så køen ikke kan stå fast.
    Kaster ALDRIG — en fejl i bookkeeping må ikke standse hjerteslaget.
    """
    try:
        items = _load()
        pending = [e for e in items if e.get("status") == "pending"]
        if not pending:
            return {"closed": 0, "kept": 0, "duplicates": 0}

        nu = datetime.now(UTC)
        grupper: dict[str, list[dict[str, Any]]] = {}
        for e in pending:
            grupper.setdefault(_forslag_noegle(e), []).append(e)

        lukket = 0
        dubletter = 0
        bevaret = 0
        grunde: dict[str, int] = {}

        for noegle, gruppe in grupper.items():
            gruppe.sort(key=lambda e: str(e.get("at") or ""))
            rep = gruppe[0]

            # 1. Dubletter — alt efter den ældste i gruppen.
            for dup in gruppe[1:]:
                dup["status"] = "rejected"
                dup["resolved_at"] = nu.isoformat()
                dup["resolution_note"] = (
                    f"dublet af {rep.get('proposal_id')} — samme forslag fil'et "
                    f"{len(gruppe)} gange"
                )
                lukket += 1
                dubletter += 1
                grunde["dublet"] = grunde.get("dublet", 0) + 1

            # 2. Grundlaget for repræsentanten.
            ok, grund = _grundlag_findes(rep)
            if not ok:
                rep["status"] = "rejected"
                rep["resolved_at"] = nu.isoformat()
                rep["resolution_note"] = grund
                lukket += 1
                grunde[grund[:40]] = grunde.get(grund[:40], 0) + 1
                continue

            # 3. Alder — et forslag der har ventet for længe er ikke længere
            #    det samme spørgsmål. Luk det med alderen som grund.
            try:
                alder_dage = (nu - datetime.fromisoformat(
                    str(rep.get("at") or "").replace("Z", "+00:00")
                )).days
            except Exception:  # utolkbart tidsstempel: alder 0 betyder «behold», den sikre side
                alder_dage = 0
            if alder_dage > max_age_days:
                rep["status"] = "rejected"
                rep["resolved_at"] = nu.isoformat()
                rep["resolution_note"] = (
                    f"forældet: ventede {alder_dage} dage (grænse {max_age_days}); "
                    f"grundlaget var '{grund}'"
                )
                lukket += 1
                grunde["forældet"] = grunde.get("forældet", 0) + 1
                continue

            bevaret += 1

        if lukket:
            _save(items)
            logger.info(
                "autonomous_work: forbruger lukkede %d forslag (%d dubletter), beholdt %d",
                lukket, dubletter, bevaret,
            )
        return {
            "closed": lukket,
            "kept": bevaret,
            "duplicates": dubletter,
            "reasons": grunde,
        }
    except Exception as exc:
        logger.warning("autonomous_work: consume failed: %s", exc)
        return {"closed": 0, "kept": 0, "duplicates": 0, "error": str(exc)[:200]}


# --- Udøver (C3, 3/11-2026) ------------------------------------------------
#
# Forbrugeren ovenfor lukker det DØDE. Men målt kl. 19:36 stod to forslag
# stadig `pending` — deres grundlag levede, og ingen ville nogensinde gøre
# noget ved dem. Forbrugeren var halvdelen af en mekanisme.
#
# Udøveren deler efter hvad policyen FAKTISK tillader, ikke efter hvad der
# ville være pænt:
#
#   * `memory_consolidate` — intern. `synthesize_daily_journal` skriver en
#     lokal fil med et lokalt modelkald. Må gerne køre autonomt.
#   * `research` — kræver `web_search`, som IKKE står i `AUTONOMOUS_TOOLS`
#     (målt: False). Et autonomt run må ikke handle i omverdenen. Forslaget
#     udføres derfor ikke; det bærer nu den grund, så fladen kan sige hvorfor.
#
# Målt før den blev bygget, og grunden til at den ER en udøver og ikke bare
# endnu en tæller: begge de to overlevende forslag viste sig allerede udført
# ad andre veje — `2026-11-02-daily.md` lå i `jarvis_brain/observation/`, og
# `incubator_seed` kalder `ci_tick` før posten skrives. `pending` var i begge
# tilfælde en løgn om at noget ventede.

def _udfoer_memory_consolidate(entry: dict[str, Any]) -> tuple[str, str]:
    """Konsolidér den dag forslaget peger på. Returnerer (status, note).

    Idempotent: findes journalen, er arbejdet allerede gjort — så lukkes
    forslaget som `completed` med stien som bevis, ikke som `rejected`.
    """
    from datetime import date as _date

    details = entry.get("details") or {}
    dato = str(details.get("date") or "")
    try:
        day = _date.fromisoformat(dato)
    except Exception:  # utolkbar dato: forslaget kan ikke udføres, og skal sige hvorfor
        return "rejected", f"datoen '{dato}' kunne ikke tolkes"

    try:
        from core.services.daily_journal import journal_exists_for, synthesize_daily_journal
    except Exception as exc:  # modulet mangler: forslaget er UDFØRT-uafklaret, ikke dødt
        return "pending", f"daily_journal kunne ikke importeres ({type(exc).__name__})"

    if journal_exists_for(day):
        return "completed", f"journalen for {dato} fandtes allerede — intet at gøre"

    try:
        result = synthesize_daily_journal(day)
    except Exception as exc:  # syntesen kastede: forslaget bliver staaende, nu med grunden
        return "pending", f"syntesen fejlede ({type(exc).__name__}: {str(exc)[:120]})"

    status = str(result.get("status") or "")
    if status == "written":
        return "completed", f"journal skrevet: {result.get('path')}"
    if status == "skipped":
        return "completed", f"allerede skrevet ({result.get('reason')})"
    if status == "no-content":
        return "rejected", f"ingen indhold for {dato} at konsolidere"
    return "pending", f"syntesen svarede '{status}': {result.get('reason')}"


def _udfoer_research(entry: dict[str, Any]) -> tuple[str, str]:
    """Research kan ikke udføres autonomt — sig det med den faktiske grund."""
    try:
        from core.tools.autonomous_tool_policy import AUTONOMOUS_TOOLS
    except Exception:  # policyen kan ikke læses: antag det STRENGE svar
        return "pending", "kunne ikke afgøre om web_search er autonomt tilladt"
    if "web_search" in AUTONOMOUS_TOOLS:
        return "pending", "web_search er autonomt tilladt, men ingen udfører er koblet på"
    return "pending", (
        "kræver web_search, som ikke er autonomt tilladt — "
        "et research-forslag skal køres som et synligt run"
    )


def execute_proposals() -> dict[str, Any]:
    """Udfør de forslag hvis grundlag OG policy tillader det nu.

    Kaldes fra `tick()` efter `consume_proposals()`. Kaster ALDRIG — en fejl
    her må ikke standse hjerteslaget.

    Forslag der ikke kan udføres bliver `pending` med et `blocked_by`-felt, så
    de stadig er synlige. En manglende udfører må ikke ligne en afvisning.
    """
    udfoert: dict[str, int] = {}
    blokeret: dict[str, int] = {}
    try:
        items = _load()
        pending = [e for e in items if e.get("status") == "pending"]
        if not pending:
            return {"executed": 0, "blocked": 0}

        handlers = {
            "memory_consolidate": _udfoer_memory_consolidate,
            "research": _udfoer_research,
        }
        aendret = False
        nu = datetime.now(UTC)

        for entry in pending:
            typ = str(entry.get("type") or "")
            handler = handlers.get(typ)
            if handler is None:
                entry["blocked_by"] = f"typen '{typ}' har ingen udfører"
                blokeret[typ] = blokeret.get(typ, 0) + 1
                aendret = True
                continue

            status, note = handler(entry)
            if status == "pending":
                # Stadig blokeret — men nu med den faktiske grund, ikke tavshed.
                if entry.get("blocked_by") != note:
                    entry["blocked_by"] = note
                    aendret = True
                blokeret[typ] = blokeret.get(typ, 0) + 1
                continue

            entry["status"] = status
            entry["resolved_at"] = nu.isoformat()
            entry["resolution_note"] = note
            entry.pop("blocked_by", None)
            udfoert[status] = udfoert.get(status, 0) + 1
            aendret = True

        if aendret:
            _save(items)
        if udfoert:
            logger.info("autonomous_work: udfører lukkede %s", udfoert)
        return {"executed": sum(udfoert.values()), "blocked": sum(blokeret.values())}
    except Exception as exc:
        logger.warning("autonomous_work: execute failed: %s", exc)
        return {"executed": 0, "blocked": 0, "error": str(exc)[:200]}


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Plan work proposals during low activity.

    ⚠️ RETTET 3/11-2026 — daemonen producerede i det uendelige ind i en log
    ingen forbruger. Målt: 300 poster (loggens loft), ALLE `pending`, ældste
    28/10. `_save` trimmer til de nyeste 300, så gamle forslag ikke blev
    afvist — de blev **stille kasseret** ved rotation, mens fladen fortsat
    meldte «300 afventende af 300 total».

    `resolve_proposal` findes og virker, men kaldes kun manuelt. Der er altså
    ingen automatisk forbruger: hvert tick fyldte loggen op og skubbede et
    gammelt forslag ud, uden at nogen nogensinde så det.

    Nu standses produktionen når køen er fuld af ubehandlede forslag. Det er
    ærligere at sige «jeg har 300 ubesvarede forslag og laver ikke flere» end
    at blive ved med at skrive dem ind i en roterende fil der skjuler dem.
    """
    low, reason = _is_low_activity()
    if not low:
        return {"skipped": True, "reason": reason}

    # C3-forbrugeren kører FØR produktions-gaten: ellers kan køen aldrig
    # tømmes, og daemonen ville stå fast for evigt på «queue-full-unconsumed».
    forbrug = consume_proposals()

    # Udøveren kører efter forbrugeren: forbrugeren fjerner det døde, udøveren
    # gør det levende. Uden den anden halvdel var forbrugeren en tæller.
    udfoersel = execute_proposals()

    if _proposals_last_hour() >= _MAX_PROPOSALS_PER_HOUR:
        return {
            "skipped": True,
            "reason": "rate-limited",
            "consumed": forbrug,
            "executed": udfoersel,
        }

    ventende = _pending_count()
    if ventende >= _LOG_MAX:
        return {
            "skipped": True,
            "reason": "queue-full-unconsumed",
            "pending": ventende,
            "consumed": forbrug,
            "executed": udfoersel,
        }

    created = _plan_once()
    return {
        "skipped": False,
        "activity_reason": reason,
        "proposals_created": len(created),
        "proposal_ids": created,
        "consumed": forbrug,
        "executed": udfoersel,
    }


def list_proposals(*, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    items = _load()
    if status:
        items = [e for e in items if e.get("status") == status]
    return items[-limit:][::-1]


def resolve_proposal(proposal_id: str, *, outcome: str, note: str = "") -> bool:
    """Close a proposal. outcome in {'approved', 'rejected', 'completed'}."""
    if outcome not in ("approved", "rejected", "completed"):
        return False
    items = _load()
    for e in items:
        if e.get("proposal_id") == proposal_id and e.get("status") == "pending":
            e["status"] = outcome
            e["resolved_at"] = datetime.now(UTC).isoformat()
            if note:
                e["resolution_note"] = str(note)[:300]
            _save(items)
            return True
    return False


def build_autonomous_work_surface() -> dict[str, Any]:
    items = _load()
    pending = [e for e in items if e.get("status") == "pending"]
    rejected = [e for e in items if e.get("status") == "rejected"]
    completed = [e for e in items if e.get("status") == "completed"]
    by_type: dict[str, int] = {}
    for e in pending:
        t = str(e.get("type") or "")
        by_type[t] = by_type.get(t, 0) + 1
    # Unikke forslag vs. dubletter — køen kan se stor ud uden at indeholde
    # mange forskellige spørgsmål.
    unikke = len({_forslag_noegle(e) for e in pending})
    # Blokerede forslag venter ikke på mig — de venter på en tilladelse eller
    # en udfører der ikke findes. Det skal fladen kunne sige.
    blokerede = {str(e.get("type") or ""): str(e.get("blocked_by") or "")
                 for e in pending if e.get("blocked_by")}
    return {
        "active": len(items) > 0,
        "pending_count": len(pending),
        "pending_unique": unikke,
        "blocked_count": len(blokerede),
        "blocked_by": blokerede,
        "rejected_count": len(rejected),
        "completed_count": len(completed),
        "total_proposals": len(items),
        "by_type_pending": by_type,
        "allowed_types": list(_ALLOWED_TYPES),
        "max_per_hour": _MAX_PROPOSALS_PER_HOUR,
        "recent": items[-5:][::-1],
        "summary": _surface_summary(pending, items),
    }


def _surface_summary(pending: list[dict[str, Any]], all_items: list[dict[str, Any]]) -> str:
    """Summarise the queue — og sig naar den ikke bliver forbruget.

    3/11-2026: fladen skrev «300 afventende forslag af 300 total» som om det var
    en travl kø. Maalt var det en log der var loebet fuld: alle 300 `pending`,
    aeldste 28/10, og `_save` trimmede de aeldste vaek ved rotation saa de ikke
    blev afvist — de blev kasseret uden spor.

    Nu findes der en forbruger (`consume_proposals`), og fladen siger baade hvor
    mange der venter, hvor mange UNIKKE de er, og hvad forbrugeren har lukket.
    """
    if not all_items:
        return "Ingen autonomous-work forslag endnu"

    # Alder paa det aeldste ventende forslag — det er dét der afsloerer om
    # koeen bliver behandlet eller bare fyldt op.
    aeldste_dage: int | None = None
    ats = sorted(str(e.get("at")) for e in pending if e.get("at"))
    if ats:
        try:
            aeldste = datetime.fromisoformat(ats[0].replace("Z", "+00:00"))
            aeldste_dage = max(0, (datetime.now(UTC) - aeldste).days)
        except Exception:  # utolkbart tidsstempel — alderen er en berigelse, ikke et krav
            aeldste_dage = None

    lukket = sum(
        1 for e in all_items
        if e.get("status") in ("rejected", "completed", "approved")
    )
    unikke = len({_forslag_noegle(e) for e in pending})

    if pending and len(pending) >= _LOG_MAX:
        alder = f", ældste {aeldste_dage} dage" if aeldste_dage is not None else ""
        return (
            f"Køen er FULD: {len(pending)} afventende ({unikke} unikke){alder}. "
            f"{lukket} er behandlet. Forbrugeren kører ved hvert tick — bliver den "
            "ved med at stå fuld, kan den ikke afgøre grundlaget for forslagene."
        )
    if pending:
        alder = f", ældste {aeldste_dage} dage" if aeldste_dage is not None else ""
        dup = f" ({len(pending) - unikke} er dubletter)" if len(pending) > unikke else ""
        # Blokerede forslag venter ikke på mig — de venter på en tilladelse
        # eller en udfører der ikke findes. Uden denne sætning ser de ud som
        # arbejde der bare ikke er blevet taget endnu.
        blokeret = [e for e in pending if e.get("blocked_by")]
        blok = ""
        if blokeret:
            typer = sorted({str(e.get("type") or "") for e in blokeret})
            blok = (
                f" {len(blokeret)} af dem er BLOKERET ({', '.join(typer)}) — "
                "de venter på en tilladelse, ikke på mig."
            )
        return (
            f"{len(pending)} afventende, {unikke} unikke{dup}{alder}. "
            f"{lukket} behandlet.{blok}"
        )
    return f"0 afventende — {lukket} forslag behandlet"


def build_autonomous_work_prompt_section() -> str | None:
    """Sig hvad der venter — med type, dato og hvad der blokerer.

    ⚠️ RETTET 3/11-2026. Før: `pending[-1]` (det NYESTE forslag) og titlen
    gengivet råt. Målt: sektionen sagde «Consolidate today's memory notes» om
    et forslag der gjaldt 2. november, og nævnte ét af to forslag som om det
    andet ikke fandtes. Titlen var skrevet den dag forslaget blev fil'et;
    «today» blev aldrig oversat til en dato.

    Nu bærer linjen den faktiske dato, og et forslag der er blokeret af
    policyen siger det — ellers ser det ud som om det venter på mig.
    """
    items = _load()
    pending = [e for e in items if e.get("status") == "pending"]
    if not pending:
        return None

    linjer: list[str] = []
    for e in pending[:3]:
        typ = str(e.get("type") or "")
        details = e.get("details") or {}
        if not isinstance(details, dict):
            details = {}
        if typ == "memory_consolidate" and details.get("date"):
            hvad = f"konsolidér noterne for {details['date']}"
        elif typ == "research" and details.get("seed_id"):
            hvad = f"research på {details['seed_id']}"
        else:
            hvad = str(e.get("title") or "")[:80]
        blok = e.get("blocked_by")
        linjer.append(f"- {hvad} ({typ})" + (f" — BLOKERET: {blok}" if blok else ""))

    flere = f" (+{len(pending) - len(linjer)} mere)" if len(pending) > len(linjer) else ""
    return "Mens du var væk filede jeg disse forslag:\n" + "\n".join(linjer) + flere
