"""Task worker — consumes queued runtime_tasks in heartbeat tick cadence.

Responsibilities:
- Claim the next queued task ordered by priority and age
- Dispatch to a handler based on the task's `kind`
- Mark `succeeded`/`failed` with a short result_summary

This worker is deliberately thin: it converts tasks from `queued` to a terminal
state so Jarvis' runtime no longer accumulates dead queue entries. Richer
handlers (hooking into runtime_action_executor, LLM-driven follow-through) can
be layered on top in subsequent work.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import runtime_tasks
from core.runtime.state_store import load_json, save_json

_WORKER_ID = "task-worker"


def claimable_kinds() -> tuple[str, ...]:
    """Kinds workeren kan claime — AFLEDT af handler-registret.

    Én sandhed: en kind kan kun claimes hvis der er en handler til den. Den
    gamle håndskrevne allowlist kunne drive fra producenterne (`curriculum-focus`
    blev produceret men aldrig claimet).
    """
    return tuple(_KIND_HANDLERS)


def claim_next_task(
    kinds: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any] | None:
    """Claim the next queued task atomically (queued -> running + lease).

    Returns the claimed task dict, or ``None`` if nothing claimable is queued.
    """
    allowed = tuple(kinds) if kinds else claimable_kinds()
    # runtime_tasks.list_tasks already sorts by (priority_rank, retry_at/updated_at).
    queued = runtime_tasks.list_tasks(status="queued", limit=50)
    for task in queued:
        if str(task.get("kind") or "") not in allowed:
            continue
        claimed = runtime_tasks.claim_task(str(task["task_id"]), owner=_WORKER_ID)
        if claimed is not None:  # None = en anden claimer vandt racet
            return claimed
    return None


#: Hvorfor followup-handlers melder `blocked` og ikke `succeeded`
#:
#: MÅLT 1/11-2026: 5.776 initiative-followup-tasks stod som `succeeded`, alle med
#: en `... acknowledged: <goal>`-streng som resultat. Præcis 1 af dem havde en
#: ikke-tom `artifact_ref`. 5.794 flows stod fast på trin 1 af 2. Samme mål blev
#: gentaget 306 gange over 50 dage.
#:
#: En streng der gentager instruksen er et EKKO, ikke et resultat. Handlers her
#: kan kun videresende et mål — de har ingen værktøjsadgang og kan ikke producere
#: et artefakt. Den ægte udførelse sker i den autonome run som
#: `dispatch_heartbeat_initiative` starter. Derfor: `blocked`, med grunden skrevet
#: ned, så køen ikke lukkes på en løgn.
_FOLLOWUP_BLOCKED = (
    "ingen handler kan udføre dette mål — det kræver en kørende bane med "
    "værktøjsadgang (se dispatch_heartbeat_initiative)"
)


def _followup_result(kind: str, task: dict[str, Any]) -> dict[str, str]:
    goal = str(task.get("goal") or "").strip()
    return {
        "status": "blocked",
        "summary": f"{kind}: videresendt, ikke udført — {goal[:200]}",
        "artifact_ref": "",
        "blocked_reason": _FOLLOWUP_BLOCKED,
    }


def _handle_initiative_followup(task: dict[str, Any]) -> dict[str, str]:
    return _followup_result("initiative-followup", task)


def _handle_heartbeat_followup(task: dict[str, Any]) -> dict[str, str]:
    return _followup_result("heartbeat-followup", task)


def _handle_open_loop_followup(task: dict[str, Any]) -> dict[str, str]:
    return _followup_result("open-loop-follow-up", task)


def _handle_agency_bridge_repair(task: dict[str, Any]) -> dict[str, str]:
    """Prepare a repair brief for a weak agency bridge.

    The worker must not silently edit source. It turns the runtime task into a
    durable, MC-visible brief that a visible/coding lane can pick up under the
    normal approval flow.
    """
    scope = str(task.get("scope") or "").strip()
    goal = str(task.get("goal") or "").strip()
    edge = _matching_agency_edge(scope=scope, goal=goal)
    task_id = str(task.get("task_id") or "")
    brief = {
        "task_id": task_id,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "awaiting-visible-repair",
        "scope": scope,
        "goal": goal,
        "edge": edge,
        "recommended_next_action": (
            "Open a visible/coding-lane repair pass for this agency bridge. "
            "Inspect the missing markers, add the smallest bridge that makes "
            "the runtime connection real, then rerun the cartographer scan."
        ),
        "suggested_files": _suggested_agency_files(scope=scope, edge=edge),
    }
    _store_agency_repair_brief(task_id=task_id, brief=brief)
    missing = ", ".join(edge.get("missing_markers") or []) if edge else ""
    return {
        "status": "blocked",
        "summary": (
            "Agency bridge repair brief prepared; source changes require "
            f"visible/coding lane approval. {scope or goal}"[:240]
        ),
        "artifact_ref": f"state:agency_bridge_repair_briefs:{task_id}",
        "blocked_reason": (
            "repair brief ready; awaiting approved implementation lane"
            + (f"; missing markers: {missing[:180]}" if missing else "")
        ),
    }


def _handle_observability_bridge_repair(task: dict[str, Any]) -> dict[str, str]:
    scope = str(task.get("scope") or "").strip()
    goal = str(task.get("goal") or "").strip()
    task_id = str(task.get("task_id") or "")
    service = Path(scope).stem if scope else ""
    brief = {
        "task_id": task_id,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "awaiting-visible-repair",
        "scope": scope,
        "goal": goal,
        "service": service,
        "recommended_next_action": (
            "Add a minimal build_*surface for this service or connect an existing "
            "surface to Mission Control/System Cartographer. Then rerun the "
            "cartographer and verify the dark edge drops or its coverage score rises."
        ),
        "suggested_files": _suggested_observability_files(scope=scope, service=service),
    }
    _store_observability_repair_brief(task_id=task_id, brief=brief)
    return {
        "status": "blocked",
        "summary": (
            "Observability bridge repair brief prepared; source changes require "
            f"visible/coding lane approval. {service or scope or goal}"[:240]
        ),
        "artifact_ref": f"state:observability_bridge_repair_briefs:{task_id}",
        "blocked_reason": "observability brief ready; awaiting approved implementation lane",
    }


def _handle_theater_refactor(task: dict[str, Any]) -> dict[str, str]:
    scope = str(task.get("scope") or "").strip()
    goal = str(task.get("goal") or "").strip()
    task_id = str(task.get("task_id") or "")
    audit_file = _matching_theater_file(scope=scope)
    brief = {
        "task_id": task_id,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "awaiting-visible-refactor",
        "scope": scope,
        "goal": goal,
        "audit_file": audit_file,
        "recommended_next_action": (
            "Convert this layer from narrative-first prompting to structured "
            "appraisal state. Preserve voice as optional rendering, but make "
            "evidence, confidence, expiry, and allowed runtime effects the durable truth."
        ),
        "refactor_contract": {
            "state_before_prose": True,
            "requires_evidence": True,
            "requires_confidence": True,
            "requires_decay_or_expiry": True,
            "requires_allowed_effects": True,
            "first_person_text_is_rendering_only": True,
        },
        "suggested_files": _suggested_theater_files(scope=scope),
    }
    _store_theater_refactor_brief(task_id=task_id, brief=brief)
    return {
        "status": "blocked",
        "summary": (
            "Theater refactor brief prepared; source changes require "
            f"visible/coding lane approval. {scope or goal}"[:240]
        ),
        "artifact_ref": f"state:theater_refactor_briefs:{task_id}",
        "blocked_reason": "theater refactor brief ready; awaiting approved implementation lane",
    }


def _handle_generic(task: dict[str, Any]) -> dict[str, str]:
    return {
        "status": "succeeded",
        "summary": f"generic task acknowledged: {str(task.get('goal') or '')[:120]}",
        "artifact_ref": "",
        "blocked_reason": "",
    }


#: Nyt domæne starter UNDER midten: et læringsmål findes fordi domænet er svagt
#: (planen sorterer svage domæner først). 0.5 ville være en påstand ingen har
#: dækning for. Samme niveau som de svageste målte domæner (~0.3).
_NEW_DOMAIN_START = 0.3
#: Løft kun ved BEVIST arbejde; lille, så ét run aldrig kan flytte et domæne meget.
_LIFT_EVIDENCED = 0.05
#: Et run der fejlede er et (svagt) tegn på at domænet ikke er mestret.
_DROP_FAILED = 0.03


def _run_did_work_from_outcomes(run_id: str) -> bool:
    """Bevis pr. RUN — ikke pr. session.

    MÅLT 20/11-2026: den session-baserede port kunne ALDRIG passere for et
    autonomt run. Sessionen ``auto-work-<dato>`` indeholdt 465 tool-rækker og
    8 assistent-svar — og NUL ``user``-rækker, fordi den autonome prompt ikke
    persisteres som en brugerbesked. Porten ledte efter målet i en user-række
    der ikke findes, returnerede False hver gang, og ``_confidence_delta`` gav
    0.0. Derfor stod ``adherence-analyse`` på 0.35 i alle 1.011 vektor-versioner:
    tallet blev aldrig målt, kun arvet.

    ``runtime_action_outcomes`` bærer ``run_id`` (1.963 distinkte runs, også
    autonome) og er dermed den ægte per-run-evidens. Sessionen er delt mellem
    dagens runs, så et tidsvindue kunne kreditere naboens arbejde; run_id kan ikke.
    """
    if not run_id:
        return False
    try:
        from core.runtime.db import connect

        with connect() as conn:
            tools = conn.execute(
                "SELECT COUNT(*) FROM runtime_action_outcomes WHERE run_id = ?",
                (run_id,),
            ).fetchone()[0]
            answer = conn.execute(
                "SELECT LENGTH(COALESCE(text_preview, '')) FROM visible_runs"
                " WHERE run_id = ?",
                (run_id,),
            ).fetchone()
    except Exception:  # noqa: BLE001 — kan beviset ikke læses, er svaret "intet bevist"
        return False
    return int(tools or 0) > 0 and bool(answer and int(answer[0] or 0) > 0)


def _run_did_work(session_id: str, goal: str, *, run_id: str = "") -> bool:
    """Beviser sessionen at runnet FAKTISK gjorde noget for dette mål?

    Kræver, efter den seneste besked der bærer målet, mindst ét værktøjskald
    OG et ikke-tomt assistent-svar. «Runnet sluttede uden fejl» er ikke bevis:
    det er præcis 1/11-fejlen (5.776 tasks ``succeeded`` uden at noget var gjort).

    Er ``run_id`` kendt, bruges per-run-evidensen i stedet — se
    ``_run_did_work_from_outcomes``. Den session-baserede vej nedenfor kan kun
    bruges hvor målet faktisk blev gemt som en brugerbesked.
    """
    if run_id:
        return _run_did_work_from_outcomes(run_id)
    try:
        from core.services.chat_sessions import recent_chat_session_messages

        rows = recent_chat_session_messages(session_id, limit=80)
    except Exception:  # noqa: BLE001 — kan beviset ikke læses, er svaret "intet bevist"
        return False
    chrono = list(reversed(rows))  # nyeste-først -> kronologisk
    start = None
    for i, row in enumerate(chrono):
        if str(row.get("role")) == "user" and goal and goal in str(row.get("content") or ""):
            start = i
    if start is None:
        return False
    after = chrono[start + 1:]
    tools = any(str(r.get("role")) == "tool" for r in after)
    answer = any(
        str(r.get("role")) == "assistant" and str(r.get("content") or "").strip()
        for r in after
    )
    return tools and answer


def _confidence_delta(outcome: str, did_work: bool) -> float:
    if outcome == "completed" and did_work:
        return _LIFT_EVIDENCED
    if outcome == "failed":
        return -_DROP_FAILED
    # completed uden bevis, interrupted: observationen registreres, men intet
    # løftes og intet sænkes — vi ved det ikke.
    return 0.0


def record_curriculum_outcome(
    domain: str, *, outcome: str, did_work: bool
) -> dict[str, Any]:
    """Registrér et afsluttet curriculum-run mod domænets confidence.

    Opretter domænet i ``confidence_by_domain`` hvis det mangler. Retning:
    +0.05 kun for ``completed`` MED bevis for arbejde; −0.03 ved ``failed``;
    ellers uændret. En task der melder succes uden at noget blev gjort løfter
    ALDRIG noget.
    """
    import json

    from core.runtime.db_cognitive import (
        get_latest_cognitive_personality_vector,
        upsert_cognitive_personality_vector,
    )

    key = " ".join(str(domain or "").lower().split())[:120]
    if not key:
        return {"recorded": False, "reason": "intet domæne"}
    current = get_latest_cognitive_personality_vector() or {}
    try:
        domains = json.loads(str(current.get("confidence_by_domain") or "{}"))
    except ValueError:
        domains = {}
    if not isinstance(domains, dict):
        domains = {}
    # Genbrug eksisterende nøgle uanset store/små bogstaver.
    existing = next((k for k in domains if str(k).lower().split() == key.split()), None)
    name = existing or key
    created = name not in domains
    before = float(domains.get(name, _NEW_DOMAIN_START))
    delta = _confidence_delta(outcome, did_work)
    after = max(0.0, min(1.0, round(before + delta, 4)))
    if not created and after == before:
        return {"recorded": False, "reason": "uændret", "before": before, "after": after}
    domains[name] = after
    upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps(domains, ensure_ascii=False),
        communication_style=str(current.get("communication_style", "{}")),
        learned_preferences=str(current.get("learned_preferences", "[]")),
        recurring_mistakes=str(current.get("recurring_mistakes", "[]")),
        strengths_discovered=str(current.get("strengths_discovered", "[]")),
        current_bearing=str(current.get("current_bearing", "")),
        emotional_baseline=str(current.get("emotional_baseline", "{}")),
    )
    return {"recorded": True, "created": created, "before": before, "after": after}


def _make_curriculum_completion_callback(domain: str, goal: str):
    def _cb(
        *,
        outcome: str = "",
        session_id: str = "",
        visible_run_id: str = "",
        **_kw: Any,
    ) -> None:
        did_work = outcome == "completed" and _run_did_work(
            session_id, goal, run_id=str(visible_run_id or "")
        )
        record_curriculum_outcome(domain, outcome=outcome, did_work=did_work)

    return _cb


def _handle_curriculum_focus(task: dict[str, Any]) -> dict[str, str]:
    """Læringsmål fra self_experiments — sendes til en autonom bane med værktøjer.

    MÅLT 20/11-2026: den tidligere handler meldte ``blocked`` og pegede på «en
    kørende bane med værktøjsadgang» — men ingen kode startede den bane. Otte
    læringsmål stod fast siden 30/10, og en `blocked`-tilstand intet kan forlade
    er ikke ærlig, den er en død ende.

    Nu materialiseres målet som et autonomt run (origin ``work``, så det lander i
    en synlig ``auto-work-<dato>``-session). ``succeeded`` meldes KUN når runnet
    faktisk blev født — ellers gentog vi 1/11-2026-fejlen, hvor 5.776 tasks stod
    ``succeeded`` uden at noget var gjort.
    """
    goal = str(task.get("goal") or "").strip()
    if not goal:
        return {
            "status": "failed",
            "summary": "curriculum-focus uden goal",
            "artifact_ref": "",
            "blocked_reason": "",
        }
    scope = str(task.get("scope") or "").strip()
    prompt_goal = goal
    prompt = (
        "LÆRINGSMÅL (fra self_experiments): "
        f"{goal}\n\n"
        "Arbejd med målet konkret: find den adfærd det peger på i koden eller "
        "loggen, ret den hvis rettelsen ligger inden for rammen, og skriv hvad "
        "du målte — ikke hvad du forventer."
    )
    try:
        from core.services.visible_autonomous_run import start_autonomous_run

        started = start_autonomous_run(
            prompt,
            origin="work",
            task_id=str(task.get("task_id") or ""),
            max_tool_calls=24,
            max_seconds=600.0,
            # Koblingen RUN -> CONFIDENCE: domænet er task.scope. Uden scope
            # kender vi intet domæne, og så registreres intet (ingen opfundet nøgle).
            completion_callback=(
                _make_curriculum_completion_callback(scope, prompt_goal)
                if scope else None
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "summary": (
                f"curriculum-focus: kunne ikke starte bane — "
                f"{type(exc).__name__}: {exc}"
            )[:240],
            "artifact_ref": "",
            "blocked_reason": f"run-start fejlede: {type(exc).__name__}",
        }
    if not started:
        return {
            "status": "blocked",
            "summary": f"curriculum-focus: run-guarden afviste banen — {goal[:150]}",
            "artifact_ref": "",
            "blocked_reason": (
                "run-guard/gut-gate afviste det autonome run; intet blev sendt afsted"
            ),
        }
    return {
        "status": "succeeded",
        "summary": f"curriculum-focus: sendt til autonom bane — {goal[:150]}",
        "artifact_ref": f"run:work:{task.get('task_id')}",
        "blocked_reason": "",
    }


#: ÉT handler-register. `claimable_kinds()` afledes herfra.
_KIND_HANDLERS: dict[str, Any] = {
    "initiative-followup": _handle_initiative_followup,
    "heartbeat-followup": _handle_heartbeat_followup,
    "generic": _handle_generic,
    "open-loop-follow-up": _handle_open_loop_followup,
    "agency_bridge_repair": _handle_agency_bridge_repair,
    "observability_bridge_repair": _handle_observability_bridge_repair,
    "theater_refactor": _handle_theater_refactor,
    "curriculum-focus": _handle_curriculum_focus,
}

# Bagudkompatibelt navn (afledt, ikke håndskrevet).
_DEFAULT_KINDS: tuple[str, ...] = tuple(_KIND_HANDLERS)


def _execute_task(task: dict[str, Any]) -> None:
    """Execute a single task and persist its final status. Never raises."""
    kind = str(task.get("kind") or "")
    task_id = str(task.get("task_id") or "")
    try:
        handler = _KIND_HANDLERS.get(kind)
        if handler is None:
            runtime_tasks.update_task(
                task_id,
                status="failed",
                result_summary=f"unknown kind: {kind}",
            )
            return
        result = handler(task)
        runtime_tasks.update_task(
            task_id,
            status=result["status"],
            blocked_reason=result.get("blocked_reason", ""),
            result_summary=(result.get("summary") or "ok")[:500],
            artifact_ref=result.get("artifact_ref", ""),
        )
    except Exception as exc:  # noqa: BLE001
        runtime_tasks.update_task(
            task_id,
            status="failed",
            result_summary=f"error: {type(exc).__name__}: {exc}"[:500],
        )


def tick_task_worker(budget: int = 3) -> dict[str, Any]:
    """Run one worker tick: claim and execute up to ``budget`` tasks.

    Returns a summary dict suitable for ``daemon_manager.record_daemon_tick``.
    """
    processed = 0
    succeeded = 0
    failed = 0
    blocked = 0
    allowed = claimable_kinds()
    # Reaper først: en task der blev claimet af en worker der døde, må ikke stå
    # `running` for evigt.
    try:
        reaped = len(runtime_tasks.reap_expired_leases())
    except Exception:  # noqa: BLE001
        reaped = 0
    for _ in range(max(0, int(budget))):
        task = claim_next_task(kinds=allowed)
        if task is None:
            break
        _execute_task(task)
        reloaded = runtime_tasks.get_task(str(task["task_id"]))
        processed += 1
        status = str((reloaded or {}).get("status") or "")
        if status == "succeeded":
            succeeded += 1
        elif status == "failed":
            failed += 1
        elif status == "blocked":
            blocked += 1
    remaining = [
        t
        for t in runtime_tasks.list_tasks(status="queued", limit=50)
        if str(t.get("kind") or "") in allowed
    ]
    return {
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
        "blocked": blocked,
        "remaining_queued": len(remaining),
        "reaped": reaped,
    }


def _matching_agency_edge(*, scope: str, goal: str) -> dict[str, Any]:
    try:
        from core.services.agency_cartographer import get_cartographer_snapshot

        snapshot = get_cartographer_snapshot(refresh=True)
        candidates = list(snapshot.get("taskCandidates") or [])
        edges = list(snapshot.get("edges") or [])
        for candidate in candidates:
            if scope and str(candidate.get("scope") or "").strip() == scope:
                edge_id = str(candidate.get("id") or "").removeprefix("agency-")
                return _edge_by_id(edges, edge_id) or dict(candidate)
            if goal and str(candidate.get("goal") or "").strip() == goal:
                edge_id = str(candidate.get("id") or "").removeprefix("agency-")
                return _edge_by_id(edges, edge_id) or dict(candidate)
        for edge in edges:
            if scope and str(edge.get("target") or "").strip() == scope:
                return dict(edge)
    except Exception:
        return {}
    return {}


def _edge_by_id(edges: list[dict[str, Any]], edge_id: str) -> dict[str, Any]:
    for edge in edges:
        if str(edge.get("id") or "") == edge_id:
            return dict(edge)
    return {}


def _store_agency_repair_brief(*, task_id: str, brief: dict[str, Any]) -> None:
    data = load_json("agency_bridge_repair_briefs", {})
    if not isinstance(data, dict):
        data = {}
    data[task_id] = brief
    save_json("agency_bridge_repair_briefs", data)


def _store_observability_repair_brief(*, task_id: str, brief: dict[str, Any]) -> None:
    data = load_json("observability_bridge_repair_briefs", {})
    if not isinstance(data, dict):
        data = {}
    data[task_id] = brief
    save_json("observability_bridge_repair_briefs", data)


def _store_theater_refactor_brief(*, task_id: str, brief: dict[str, Any]) -> None:
    data = load_json("theater_refactor_briefs", {})
    if not isinstance(data, dict):
        data = {}
    data[task_id] = brief
    save_json("theater_refactor_briefs", data)


def _matching_theater_file(*, scope: str) -> dict[str, Any]:
    if not scope:
        return {}
    try:
        from core.services.theater_audit import build_theater_audit_surface

        surface = build_theater_audit_surface()
        for item in surface.get("files") or []:
            if str(item.get("path") or "").strip() == scope:
                return dict(item)
    except Exception:
        return {}
    return {}


def _suggested_agency_files(*, scope: str, edge: dict[str, Any]) -> list[str]:
    haystack = " ".join([
        scope,
        str(edge.get("id") or ""),
        str(edge.get("target") or ""),
        str(edge.get("title") or ""),
    ]).lower()
    suggestions: list[str] = ["core/services/agency_cartographer.py"]
    if "senses" in haystack or "sensory" in haystack:
        suggestions.extend([
            "core/services/sensory_archive.py",
            "core/services/perceptual_event_engine.py",
            "core/services/memory_emotional_context.py",
        ])
    if "emotion" in haystack:
        suggestions.extend([
            "core/services/emotion_concepts_channel_triggers.py",
            "core/services/memory_emotional_context.py",
        ])
    if "repair" in haystack:
        suggestions.append("core/services/self_repair_engine.py")
    if "executive" in haystack:
        suggestions.append("core/services/living_executive.py")
    if "tools" in haystack:
        suggestions.extend([
            "core/services/tool_intent_runtime.py",
            "core/services/runtime_action_outcome_tracking.py",
        ])
    if "mission control" in haystack or "hidden" in haystack:
        suggestions.extend([
            "core/services/agency_map.py",
            "apps/api/jarvis_api/routes/mission_control_introspection.py",
        ])
    return list(dict.fromkeys(suggestions))


def _suggested_observability_files(*, scope: str, service: str) -> list[str]:
    suggestions = []
    if scope:
        suggestions.append(scope)
    suggestions.extend([
        "core/services/system_cartographer.py",
        "core/services/agency_map.py",
        "apps/api/jarvis_api/routes/mission_control_introspection.py",
    ])
    if service == "identity_composer":
        suggestions.insert(0, "core/services/identity_composer.py")
    return list(dict.fromkeys(suggestions))


def _suggested_theater_files(*, scope: str) -> list[str]:
    suggestions = []
    if scope:
        suggestions.append(scope)
    suggestions.extend([
        "core/services/theater_audit.py",
        "core/services/system_cartographer.py",
        "core/services/agency_map.py",
        "apps/api/jarvis_api/routes/mission_control_introspection.py",
    ])
    if scope.endswith("cognitive_state_assembly.py"):
        suggestions.extend([
            "core/services/cognitive_state_assembly.py",
            "core/services/affective_meta_state.py",
            "core/services/somatic_daemon.py",
        ])
    return list(dict.fromkeys(suggestions))




def build_task_worker_surface() -> dict[str, Any]:
    """Mission Control-surface: hvad ligger der i koeen, og hvad endte de i?

    READ-ONLY: samme tabel som `claim_next_task` (`runtime_tasks`), men grupperet
    — ingen task bliver claimet. Viser det der ellers er skjult: at followup-
    kinds ALTID ender `blocked` (se `_FOLLOWUP_BLOCKED`), og hvor mange
    `running` der aldrig blev afsluttet.
    """
    base = {"mode": "task-worker", "claimable_kinds": list(claimable_kinds())}
    try:
        from core.runtime.db import connect
        with connect() as conn:
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_tasks'").fetchone() is None:
                return {**base, "active": False, "reason": "tabellen runtime_tasks findes ikke endnu",
                        "signals": {}, "summary": "ingen tasks er nogensinde oprettet"}
            rows = conn.execute("SELECT kind, status, COUNT(*) FROM runtime_tasks GROUP BY kind, status").fetchall()
            oldest_queued = conn.execute(
                "SELECT MIN(created_at) FROM runtime_tasks WHERE status='queued'").fetchone()[0]
            oldest_running = conn.execute(
                "SELECT MIN(updated_at) FROM runtime_tasks WHERE status='running'").fetchone()[0]
            newest = conn.execute("SELECT MAX(updated_at) FROM runtime_tasks").fetchone()[0]
            reasons = conn.execute(
                "SELECT blocked_reason, COUNT(*) FROM runtime_tasks WHERE status='blocked' AND blocked_reason!='' "
                "GROUP BY blocked_reason ORDER BY COUNT(*) DESC LIMIT 3").fetchall()
    except Exception as exc:  # surface skal melde aarsagen, ikke kaste ind i MC
        return {**base, "active": False,
                "reason": f"runtime_tasks kunne ikke laeses: {type(exc).__name__}: {exc}"[:300],
                "signals": {}, "summary": "task-koe ulaeselig"}
    by_status: dict[str, int] = {}
    claimable = 0
    unclaimable: dict[str, int] = {}
    followup_blocked = 0
    for kind, status, n in rows:
        by_status[str(status)] = by_status.get(str(status), 0) + int(n)
        if status == "queued":
            if kind in _KIND_HANDLERS:
                claimable += int(n)
            else:
                unclaimable[str(kind)] = unclaimable.get(str(kind), 0) + int(n)
        if status == "blocked" and str(kind).endswith(("followup", "follow-up")):
            followup_blocked += int(n)
    total = sum(by_status.values())
    return {
        **base, "active": total > 0,
        **({} if total else {"reason": "runtime_tasks er tom"}),
        "signals": {"total": total, "by_status": by_status, "claimable_queued": claimable,
                    "unclaimable_queued": sum(unclaimable.values()),
                    "unclaimable_kinds": unclaimable,
                    "followup_blocked": followup_blocked,
                    "blocked_reasons": [{"reason": str(r[0])[:160], "count": int(r[1])} for r in reasons],
                    "oldest_queued_at": oldest_queued, "oldest_running_updated_at": oldest_running,
                    "newest_update_at": newest},
        "summary": (f"{total} tasks; {claimable} kan claimes, {by_status.get('running', 0)} kører, "
                    f"{by_status.get('blocked', 0)} blokeret ({followup_blocked} followup)"
                    + (f"; {sum(unclaimable.values())} queued kan IKKE claimes: {unclaimable}" if unclaimable else "")),
    }
