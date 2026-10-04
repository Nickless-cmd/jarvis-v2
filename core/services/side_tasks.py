"""Side-task flag — keep the main thread focused.

When working on task A, Jarvis often notices something tangential that
should be done — but derailing into it costs context and momentum. The
side-task flag lets him capture it without acting: "noted, flagged for
later", and the user (or a future session) can pick it up.

Mirrors my own ``mcp__ccd_session__spawn_task``: short title, longer
self-contained prompt, optional plain-English tldr. Surfaces in the
visible prompt as a small list so the user sees what's queued and can
dismiss anything that's not actually wanted.

Per-session for context, but visible across the workspace so a side
task flagged in Discord is visible in webchat too. Persisted via
state_store.

Status: ``pending``, ``queued`` og ``activated`` er ÅBNE — de står i inboxen
og over chatten i Desk til nogen afslutter dem.
``completed`` og ``dismissed`` er terminale og kan ikke genåbnes. Før fandtes
kun ``dismissed`` som slutpunkt, så en opgave der BLEV lavet, forsvandt som
om den var droppet — og en ``activated`` forsvandt fra prompten i samme
øjeblik den blev taget op.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Final
from uuid import uuid4

from core.runtime.state_store import load_json, med_laas, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "side_tasks"
_VALID_STATUSES = ("pending", "queued", "activated", "completed", "dismissed")
_AABNE = frozenset({"pending", "queued", "activated"})
_TERMINALE = frozenset({"completed", "dismissed"})
_MAX_SHOWN = 6


def _kort(tekst: str, maks: int) -> str:
    """Afkort ved en ORD-grænse, så en halv sætning ikke læses som en hel.

    Den gamle `tldr[:240]` skar midt i «send_session_notificati», og en
    afkortet instruks er værre end ingen: den ser ud som et fuldt svar.
    """
    t = " ".join(str(tekst or "").split())
    if len(t) <= maks:
        return t
    skaaret = t[:maks].rsplit(" ", 1)[0].rstrip(",.;:-—")
    return (skaaret or t[:maks]) + "…"


def _load_all() -> list[dict[str, Any]]:
    raw = load_json(_STATE_KEY, [])
    if not isinstance(raw, list):
        return []
    return [r for r in raw if isinstance(r, dict)]


def _save_all(items: list[dict[str, Any]]) -> None:
    save_json(_STATE_KEY, items)
    # state_store.save_json is deliberately best-effort for optional daemons.
    # Side tasks are user-visible obligations: never return "ok" after a
    # swallowed write error. Mutations hold med_laas, so read-back is stable.
    if _load_all() != items:
        raise OSError("side tasks could not persist")


def _age_label(created_at: Any) -> str | None:
    """Kort alders-tag, fx ``3 dage`` eller ``5t`` — eller None hvis ukendt.

    Uden det ser en opgave der har ligget åben i ti dage lige så frisk ud som
    en fra i morges. En glemt opgave er ikke en ventende opgave, og forskellen
    skal kunne ses på prompten — der er ingen automatik der lukker dem
    (målt 3/10-2026: ``resolve()`` kaldes kun eksplicit).
    """
    if not created_at:
        return None
    try:
        ts = datetime.fromisoformat(str(created_at))
    except (TypeError, ValueError):  # ugyldig dato er ikke en fejl — vi udelader bare alderen
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    seconds = (datetime.now(UTC) - ts).total_seconds()
    if seconds < 0:
        return None
    if seconds < 3600:
        return f"{int(seconds // 60)}min"
    if seconds < 86400:
        return f"{int(seconds // 3600)}t"
    dage = int(seconds // 86400)
    return "1 dag" if dage == 1 else f"{dage} dage"


def flag(*, title: str, prompt: str, tldr: str = "", session_id: str | None = None,
         finding_key: str = "", source_run_id: str = "", evidence: str = "") -> dict[str, Any]:
    title = (title or "").strip()
    prompt = (prompt or "").strip()
    if not title or not prompt:
        return {"status": "error", "error": "title and prompt are required"}
    key = str(finding_key or "").strip()[:240]
    with med_laas(_STATE_KEY):
        items = _load_all()
        if key:
            existing = next((r for r in items if r.get("finding_key") == key), None)
            if existing:
                return {"status": "ok", "side_task_id": existing["side_task_id"],
                        "title": existing.get("title", ""), "deduplicated": True}
        record = {
            "side_task_id": f"side-{uuid4().hex[:10]}",
            "title": title[:120],
            "prompt": prompt[:2000],
            "tldr": tldr[:240] if tldr else "",
            "status": "pending",
            "session_id": str(session_id or "_default"),
            "created_at": datetime.now(UTC).isoformat(),
        }
        if key:
            record["finding_key"] = key
        if source_run_id:
            record["source_run_id"] = str(source_run_id)[:120]
        if evidence:
            record["evidence"] = str(evidence)[:1000]
        items.append(record)
        _save_all(items)
    return {"status": "ok", "side_task_id": record["side_task_id"], "title": title}


def list_pending() -> list[dict[str, Any]]:
    return [r for r in _load_all() if r.get("status") == "pending"]


def list_open() -> list[dict[str, Any]]:
    """Alle åbne — ventende, køede og igangværende."""
    return [r for r in _load_all() if r.get("status") in _AABNE]


def get(side_task_id: str) -> dict[str, Any] | None:
    return next((r for r in _load_all() if r.get("side_task_id") == side_task_id), None)


def list_alle(*, maks: int = 50) -> list[dict[str, Any]]:
    """ALLE opgaver, nyeste først — også de lukkede.

    Bjørn 3/10-2026: «desk har ikk noget panel der viser opgaver der er
    flagged selv om jeg har trykket dem væk». `/cowork/side-tasks` svarer kun
    med de ÅBNE, så en opgave der blev lukket forsvandt sporløst — og dermed
    kunne man ikke se forskel på «lukket» og «blev den nogensinde gemt?».

    Målt samme dag: alle seks poster i hans fil var terminale, så kortet var
    korrekt tomt — men umuligt at skelne fra tabt data. Det var selve
    symptomet: persistensen VIRKEDE (bevist med to processer), men der var
    ingen visning der kunne vise det.
    """
    poster = sorted(_load_all(), key=lambda r: str(r.get("created_at", "")),
                    reverse=True)
    return poster[:max(1, int(maks))]


def resolve(side_task_id: str, *, decision: str,
            arbejds_session: str | None = None,
            arbejds_run_id: str | None = None,
            lukket_af: str = "", reason: str = "") -> dict[str, Any]:
    """Flyt en opgaves status. `arbejds_session` knytter den til den samtale
    der løser den — se `arbejds_session_for` for hvorfor det er nødvendigt."""
    decision = (decision or "").strip().lower()
    if decision not in {"queued", "dismissed", "activated", "completed"}:
        return {"status": "error", "error": "unknown side-task decision"}
    with med_laas(_STATE_KEY):
        items = _load_all()
        found = next((r for r in items if r.get("side_task_id") == side_task_id), None)
        if found is None:
            return {"status": "error", "error": f"unknown side_task_id {side_task_id}"}
        old = str(found.get("status") or "")
        if old in _TERMINALE:
            return {"status": "error",
                    "error": f"side task {side_task_id} is already {old} and cannot be reopened"}
        if decision == "queued" and old == "activated":
            return {"status": "error", "error": "active side task cannot be queued"}
        now = datetime.now(UTC).isoformat()
        found["status"] = decision
        found["updated_at"] = now
        if decision == "queued":
            found["queued_at"] = now
        elif decision == "activated":
            found["activated_at"] = now
        else:
            found["resolved_at"] = now
        if arbejds_session:
            found["arbejds_session"] = str(arbejds_session)
        if arbejds_run_id:
            found["arbejds_run_id"] = str(arbejds_run_id)
        if lukket_af:
            found["lukket_af"] = str(lukket_af)[:60]
        if reason and decision == "dismissed":
            found["dismiss_reason"] = str(reason)[:500]
        _save_all(items)
    return {"status": "ok", "side_task_id": side_task_id, "new_status": decision}


def arbejds_session_for(session_id: str) -> dict[str, Any] | None:
    """Den ÅBNE side-opgave denne samtale blev startet for — eller ``None``.

    ## Hvorfor den findes

    Bjørn 3/10-2026: «op til trods løste han opgave og så måtte jeg minde ham
    om at markere den flaggede opgave færdig».

    Målt: desk starter opgaven i en NY samtale (`startSideOpgave` → ny session
    → `sendLoesrevet`) og sætter status til `activated`. Men den nye sessions
    id blev aldrig gemt på opgaven, så INTET kunne bagefter vide at den samtale
    hørte til opgave X. Dermed kunne hverken runtimen eller Jarvis selv lukke
    den — den stod som «(i gang)» i prompten indtil et menneske greb ind.

    Det er samme blokerede ligevægt som indbakke-spec'ens §2: en tilstand uden
    nogen der lukker den. Linket her er leddet der manglede.
    """
    sid = str(session_id or "").strip()
    if not sid:
        return None
    for r in _load_all():
        if r.get("status") in _AABNE and str(r.get("arbejds_session") or "") == sid:
            return r
    return None


def side_tasks_prompt_section(session_id: str | None = None) -> str | None:
    """Listen over åbne side-opgaver — og en eksplicit lukke-instruks når
    DENNE samtale er den der løser én af dem.

    Bjørn 3/10-2026: «måtte jeg minde ham om at markere den flaggede opgave
    færdig». Listen viste opgaven som «(i gang)», men intet sagde hvis ansvar
    det var at lukke den, eller at netop denne samtale VAR arbejdet. En liste
    uden et ansvar bliver stående.

    `session_id` er valgfri, så gamle kaldere ikke brækker — men uden den kan
    afsnittet ikke sige hvilken opgave turen hører til.
    """
    aabne = list_open()
    if not aabne:
        return None
    mit = arbejds_session_for(str(session_id or "")) if session_id else None
    aabne.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
    bullets = []
    for r in aabne[:_MAX_SHOWN]:
        # HELE id'et: Jarvis skal kunne afslutte opgaven med præcis det id han
        # ser. Et afkortet id (før: de sidste 10 tegn) kan han ikke bruge.
        sid = str(r.get("side_task_id", ""))
        title = _kort(str(r.get("title", "")), 70)
        # Kun et STIKORD af tldr'en (3/10-2026). Bjørn: «noget forurener
        # side-opgave sessionen … det er samme opgave han laver i en anden
        # session med mig». Målt samme dag stod der 240 tegn med
        # fremgangsmåden i — «Fixet er tre dele: stop aesthetic-daemonens
        # spam, flyt udgangen til send_session_notificati» — afkortet
        # midt i et ord. Det er ikke et flag, det er en arbejdsordre, og den
        # stod i HVER sessions prompt. Opgavens fulde tekst hører i den
        # samtale der løser den, ikke i alle de andre.
        tldr = _kort(str(r.get("tldr", "")).strip(), 70)
        suffix = f" — {tldr}" if tldr else ""
        tag = " (i gang)" if r.get("status") == "activated" else " (i kø)" if r.get("status") == "queued" else ""
        alder = _age_label(r.get("created_at"))
        alder_tag = f" ({alder})" if alder else ""
        bullets.append(f"  [{sid}]{tag} {title}{suffix}{alder_tag}")
    extra = f"  (+{len(aabne) - _MAX_SHOWN} mere)" if len(aabne) > _MAX_SHOWN else ""
    # Mærkningen. Tre egenskaber, som i `visible_run_guard_notices`: hvad
    # listen ER, hvad den IKKE er, og et eksplicit forbud mod den forkerte
    # læsning. Uden det sidste blev en flagget opgave læst som en opgave at
    # gå i gang med — i enhver samtale den stod i.
    afsnit = (
        "Flaggede side-tasks (deferred) — en HUSKELISTE, ikke opgaver du er "
        "sat til. Ingen af dem er bedt om i denne samtale, og du må IKKE "
        "begynde paa en af dem her. Er en af dem arbejdet i netop denne "
        "samtale, staar det udtrykkeligt nedenfor.\n"
        + "\n".join(bullets) + extra
    )
    if mit is not None:
        # Lukke-instruksen. Den staar KUN i den samtale opgaven blev startet
        # for, saa den ikke bliver stoej i alle andre ture.
        afsnit += (
            f"\n\nDENNE samtale er arbejdet paa [{mit.get('side_task_id')}] "
            f"«{mit.get('title')}». Naar den er loest, skal DU lukke den:\n"
            "  dismiss_side_task(side_task_id=\"" + str(mit.get("side_task_id")) + "\", "
            "decision=\"completed\")\n"
            "Kan den ikke loeses, sig hvad der mangler og lad den staa aaben. "
            "Ingen anden lukker den for dig."
        )
    return afsnit


def _exec_flag_side_task(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.session_context_resolve import aktiv_session_id, aktivt_run_id
    session_id = str(args.get("session_id") or aktiv_session_id("") or "")
    if args.get("finding_kind"):
        from core.services.run_finding_accounting import record_finding
        run_id = str(aktivt_run_id("") or "")
        return record_finding(
            kind=str(args.get("finding_kind") or ""),
            disposition=str(args.get("disposition") or "side_task"),
            path=str(args.get("path") or ""),
            behavior=str(args.get("behavior") or ""),
            evidence=str(args.get("evidence") or ""),
            title=str(args.get("title") or ""),
            next_step=str(args.get("prompt") or ""),
            reason=str(args.get("reason") or ""),
            run_id=run_id, session_id=session_id,
            finding_key=str(args.get("finding_key") or ""),
            existing_side_task_id=str(args.get("existing_side_task_id") or ""),
        )
    return flag(
        title=str(args.get("title") or ""),
        prompt=str(args.get("prompt") or ""),
        tldr=str(args.get("tldr") or ""),
        session_id=session_id,
        finding_key=str(args.get("finding_key") or ""),
        evidence=str(args.get("evidence") or ""),
    )


def _exec_list_side_tasks(_args: dict[str, Any]) -> dict[str, Any]:
    items = list_open()
    return {"status": "ok", "side_tasks": items, "count": len(items)}


def _exec_dismiss_side_task(args: dict[str, Any]) -> dict[str, Any]:
    # `decision` er valgfri, så gamle kald uden den stadig betyder «drop den».
    # Med decision=completed kan Jarvis afslutte en opgave han har LAVET, uden
    # et nyt værktøj i det store register (simple_tools.py er over grænsen).
    decision = str(args.get("decision") or "dismissed").strip().lower()
    if decision not in _TERMINALE:
        return {"status": "error", "error": "decision must be 'completed' or 'dismissed'"}
    return resolve(str(args.get("side_task_id") or ""), decision=decision)


def _exec_activate_side_task(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.session_context_resolve import aktiv_session_id, aktivt_run_id
    decision = str(args.get("status") or "activated").strip().lower()
    if decision not in {"queued", "activated"}:
        return {"status": "error", "error": "status must be queued or activated"}
    return resolve(str(args.get("side_task_id") or ""), decision=decision,
                   arbejds_session=(str(args.get("session_id") or aktiv_session_id("") or "") or None)
                   if decision == "activated" else None,
                   arbejds_run_id=(str(args.get("run_id") or aktivt_run_id("") or "") or None)
                   if decision == "activated" else None)


SIDE_TASK_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "flag_side_task",
            "description": (
                "Capture a tangential thing-to-do without derailing the current "
                "task. Use this when you notice something during your main work "
                "that should be addressed later. For an unresolved test gap, "
                "set finding_kind='coverage_gap', disposition, path, behavior, "
                "evidence, and a concrete next step in prompt. Record fixed or "
                "declined findings with the same fields and a reason. A new "
                "relevant failing test must be fixed in current work, never "
                "deferred through a side task."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short imperative phrase, e.g. 'Fix stale README badge'."},
                    "prompt": {"type": "string", "description": "Self-contained instructions; the picker won't have your context."},
                    "tldr": {"type": "string", "description": "Plain-English 1-2 sentence summary for the user."},
                    "session_id": {"type": "string"},
                    "finding_kind": {"type": "string", "enum": ["coverage_gap", "new_test_failure", "preexisting_test_failure", "other"]},
                    "disposition": {"type": "string", "enum": ["side_task", "fixed_now", "existing_side_task", "declined", "blocked"]},
                    "path": {"type": "string"},
                    "behavior": {"type": "string"},
                    "evidence": {"type": "string"},
                    "reason": {"type": "string"},
                    "finding_key": {"type": "string"},
                    "existing_side_task_id": {"type": "string"},
                },
                "required": ["title", "prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_side_tasks",
            "description": "List open side-tasks — pending, queued and active — across all sessions.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dismiss_side_task",
            "description": (
                "Close a flagged side-task. decision='completed' when it has been done; "
                "decision='dismissed' (default) when the user said no or it's no longer relevant. "
                "Closed tasks disappear from the prompt and from Desk and cannot be reopened."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "side_task_id": {"type": "string"},
                    "decision": {"type": "string", "enum": ["completed", "dismissed"],
                                 "description": "completed = done; dismissed = dropped (default)."},
                },
                "required": ["side_task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "activate_side_task",
            "description": "Move a flagged side-task to queue or active work. Active work should include its session_id and run_id when known; this does not dispatch work.",
            "parameters": {
                "type": "object",
                "properties": {"side_task_id": {"type": "string"},
                               "status": {"type": "string", "enum": ["queued", "activated"]},
                               "session_id": {"type": "string"}, "run_id": {"type": "string"}},
                "required": ["side_task_id"],
            },
        },
    },
]




#: Efter så lang stilstand flyttes en `activated` opgave tilbage til ventende.
#: Stilstand kan aldrig markere `completed`; den status kræver en eksplicit
#: verificering. Tærsklen er et målbart udgangspunkt, ikke bevis på succes.
STILSTAND_MINUTTER: Final[float] = 30.0


def _minutter_siden(tidsstempel: Any) -> float | None:
    """Minutter siden et ISO-tidsstempel — ``None`` hvis det ikke kan læses.

    Fail mod `None`, altså «ved ikke», frem for 0 eller uendeligt: et
    ulæseligt tidsstempel må hverken udløse en lukning eller blokere en.
    """
    if not tidsstempel:
        return None
    try:
        ts = datetime.fromisoformat(str(tidsstempel))
    except (TypeError, ValueError):  # et ulaeseligt tidsstempel er «ved ikke»,
        # ikke «for laenge siden»: fail-retningen staar i docstringen, og en
        # lukning paa et gaet er uigenkaldelig (`completed` er terminal).
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    sekunder = (datetime.now(UTC) - ts).total_seconds()
    if sekunder < 0:
        return None
    return sekunder / 60.0


def _sidst_aktiv(session_id: str) -> str | None:
    """Hvornår samtalen sidst sagde noget (`chat_sessions.updated_at`).

    Verificeret live 3/10-2026: kolonnen følger den seneste besked præcist i
    alle tre aktive samtaler. Én kolonne, ingen besked-gennemløb — samme stil
    som `session_permission` og `session_view`, og modsat det udfaste
    `get_chat_session` der henter hele historikken for ét metadata-felt.
    """
    sid = str(session_id or "").strip()
    if not sid:
        return None
    try:
        from core.runtime.db import connect
        with connect() as conn:
            r = conn.execute(
                "SELECT updated_at FROM chat_sessions WHERE session_id = ?", (sid,),
            ).fetchone()
        return str(r[0]) if r and r[0] else None
    except Exception:
        logger.warning("side-opgaver: kunne ikke laese aktivitet for %s",
                       sid, exc_info=True)
        return None


def _arbejds_run_aktiv(session_id: str) -> bool:
    """Et langt run må ikke omklassificeres på grund af stille chat-historik."""
    try:
        from core.services.visible_runs import get_active_visible_run
        active = get_active_visible_run() or {}
        return str(active.get("session_id") or "") == session_id
    except Exception:
        logger.warning("side-opgaver: kunne ikke laese aktivt run", exc_info=True)
        return True  # usikkerhed må ikke flytte en aktiv opgave tilbage


def fej_faerdige(*, stilstand_minutter: float | None = None) -> dict[str, Any]:
    """Flyt forladte `activated` opgaver tilbage til `pending`.

    ## Hvorfor en fejer og ikke en overgang ved runnets slutning

    En opgave kan tage flere runs. Det første afsluttede run er ikke bevis
    for at hele sideopgaven er færdig.

    Stilstand er ikke bevis for at arbejdet er udført eller verificeret.
    `completed` er terminal og sættes kun eksplicit. Når en arbejdssamtale
    har ligget stille, gør vi opgaven ventende igen uden at tabe historikken.

    ## Hvorfor ingen ny daemon

    Huset har 40 daemoner der kun tikker når han har travlt. Fejeren kaldes i
    stedet fra to steder der allerede sker: opstart (som husets andre fejere i
    `app.py`) og hver runs efterbehandling. Den sidste betyder at fejningen
    sker netop når der ER aktivitet, uden at nogen poller.

    `tilbage_til_venter` tæller flyttede opgaver; `lukket` bevares som nul for
    gamle kaldere. `venter` tæller opgaver under tærsklen eller med aktivt run.

    Kaster aldrig: en fejer må ikke kunne vælte en opstart eller et run.
    """
    graense = float(stilstand_minutter if stilstand_minutter is not None
                    else STILSTAND_MINUTTER)
    svar: dict[str, Any] = {"lukket": 0, "venter": 0, "uden_link": 0, "ids": []}
    try:
        for r in list_open():
            if r.get("status") != "activated":
                continue
            sid = str(r.get("arbejds_session") or "").strip()
            if not sid:
                svar["uden_link"] += 1
                continue
            stille = _minutter_siden(_sidst_aktiv(sid))
            if stille is None:
                # Ved ikke → lad den staa. En opgave maa ikke flyttes paa et gaet.
                svar["venter"] += 1
                continue
            if stille < graense:
                svar["venter"] += 1
                continue
            if _arbejds_run_aktiv(sid):
                svar["venter"] += 1
                continue
            tid = str(r.get("side_task_id") or "")
            with med_laas(_STATE_KEY):
                items = _load_all()
                found = next((x for x in items if x.get("side_task_id") == tid), None)
                if found is None or found.get("status") != "activated":
                    continue
                found["status"] = "pending"
                found["stale_at"] = datetime.now(UTC).isoformat()
                found["stale_reason"] = f"arbejdssession stille i {int(stille)}min"
                found.pop("arbejds_session", None)
                found.pop("arbejds_run_id", None)
                _save_all(items)
            svar["ids"].append(tid)
            svar["tilbage_til_venter"] = int(svar.get("tilbage_til_venter") or 0) + 1
            logger.info("side-opgave %s tilbage til ventende — %s stille i %d min",
                        tid, sid, int(stille))
    except Exception:
        logger.warning("side-opgave-fejning fejlede", exc_info=True)
    return svar
