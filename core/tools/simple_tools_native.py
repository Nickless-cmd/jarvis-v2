"""Native (non-operator, non-web) tool executors for Jarvis.

Udskilt fra ``simple_tools.py`` (Boy Scout, 2026-07): initiativer, mood, memory,
proposals, tasks, chronicles, dreams, notify, discord, home-assistant, council,
agenter, daemon, settings, project, central/db-query, tool-router (load_more_tools)
samt google/gmail/notes/hf-connector-handlers. INGEN logik-ændring — kun flyt.
Modulet ejer sin egen tilstand (_DISCORD_* rate-limits, _convene_council_daily_*
tællere, _SENSITIVE_SETTING_PATTERNS). ``simple_tools`` re-importerer alle navne
(dispatch-dict + tests).

§4 monkeypatch-søm: ``_operator_user_id`` (brugt af google/notes-handlers her)
patches af tests PÅ ``core.tools.simple_tools`` → interne kald går gennem
``_st()``-facaden så patchen rammer.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re  # noqa: F401
from pathlib import Path
from typing import Any
from urllib import error as urllib_error  # noqa: F401
from urllib import request as urllib_request

from core.eventbus.bus import event_bus
from core.runtime.config import JARVIS_HOME, PROJECT_ROOT
from core.runtime.workspace_paths import shared_dir as _shared_dir
# _tool_load_more_tools slår tool-navne op i det kanoniske katalog. Importeret
# fra samme kilde som simple_tools (ingen dobbelt-sandhed).
from core.tools.simple_tools_definitions import TOOL_DEFINITIONS  # noqa: F401

logger = logging.getLogger(__name__)

WORKSPACE_DIR = _shared_dir()


def _st():
    """Lazy accessor til simple_tools (facade-søm for _operator_user_id)."""
    import core.tools.simple_tools as _m
    return _m


def _operator_user_id(args: dict[str, Any]) -> str:
    """Facade → simple_tools._operator_user_id (honorér test-patch-søm)."""
    return _st()._operator_user_id(args)


def _exec_list_initiatives(_args: dict[str, Any]) -> dict[str, Any]:
    """Return current initiative queue state."""
    try:
        from core.services.initiative_queue import get_initiative_queue_state
        state = get_initiative_queue_state()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    pending = state.get("pending", [])
    recent_acted = state.get("recent_acted", [])
    life_projects = state.get("life_projects", [])
    lines = [
        f"Queue: {state.get('pending_count', 0)} pending / {state.get('acted_count', 0)} acted / {state.get('expired_count', 0)} expired",
        f"Capacity: {state.get('pending_count', 0)}/{state.get('max_queue_size', 8)}",
        "",
    ]
    if pending:
        lines.append("### Pending")
        for item in pending:
            priority = item.get("priority", "medium")
            focus = item.get("focus", "?")
            attempts = item.get("attempt_count", 0)
            lines.append(f"- [{priority}] {focus}" + (f" (attempts: {attempts})" if attempts else ""))
    else:
        lines.append("No pending initiatives.")

    if recent_acted:
        lines.append("")
        lines.append("### Recently Acted")
        for item in recent_acted:
            focus = item.get("focus", "?")
            summary = item.get("action_summary", "")
            lines.append(f"- {focus}" + (f" → {summary}" if summary else ""))

    if life_projects:
        lines.append("")
        lines.append("### Life Projects")
        for item in life_projects:
            title = item.get("focus", "?")
            why_text = str(item.get("why_text") or "").strip()
            lines.append(f"- {title}")
            if why_text:
                lines.append(f"  why: {why_text[:180]}")

    return {
        "status": "ok",
        "pending_count": state.get("pending_count", 0),
        "acted_count": state.get("acted_count", 0),
        "pending": pending,
        "life_projects": life_projects,
        "text": "\n".join(lines).strip(),
    }


def _exec_push_initiative(args: dict[str, Any]) -> dict[str, Any]:
    """Push a new initiative to the queue."""
    focus = str(args.get("focus") or "").strip()
    if not focus:
        return {"status": "error", "error": "focus is required"}
    priority = str(args.get("priority") or "medium").strip().lower()
    if priority not in {"low", "medium", "high"}:
        priority = "medium"
    try:
        from core.services.initiative_queue import push_initiative
        initiative_id = push_initiative(
            focus=focus,
            source="jarvis-tool",
            priority=priority,
        )
        return {
            "status": "ok",
            "initiative_id": initiative_id,
            "focus": focus,
            "priority": priority,
            "text": f"Initiative queued [{priority}]: {focus}",
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_read_model_config(_args: dict[str, Any]) -> dict[str, Any]:
    """Read the current model configuration for all runtime lanes."""
    try:
        from core.runtime.provider_router import resolve_provider_router_target
    except Exception as exc:
        return {"status": "error", "error": f"provider_router unavailable: {exc}"}

    lanes = ["visible", "local", "cheap", "coding"]
    lane_info: dict[str, dict[str, Any]] = {}
    lines = ["Model configuration:"]

    for lane in lanes:
        try:
            target = resolve_provider_router_target(lane=lane)
            provider = str(target.get("provider") or "")
            model = str(target.get("model") or "")
            active = bool(target.get("active"))
            creds = bool(target.get("credentials_ready"))
            lane_info[lane] = {
                "provider": provider,
                "model": model,
                "active": active,
                "credentials_ready": creds,
            }
            status = "ready" if (active and creds) else ("no-creds" if active else "inactive")
            suffix = " (global default)" if lane == "visible" else ""
            lines.append(f"  [{lane}] {provider}/{model} ({status}){suffix}")
        except Exception as exc:
            lane_info[lane] = {"error": str(exc)}
            lines.append(f"  [{lane}] error: {exc}")

    # Den AKTIVE visible-model kan være overridet pr. besked (composer-valg) og
    # afviger så fra den globale default ovenfor. Vis den eksplicit, så dette tool
    # IKKE modsiger system-promptens "You are running as model: X" (config-drift-
    # konfabulationen 2026-06-15).
    active_target = None
    try:
        from core.services.active_model_state import get_active_visible_target
        from core.identity.workspace_context import current_user_id
        active_target = get_active_visible_target(current_user_id())
    except Exception:
        active_target = None
    if active_target:
        ap, am = active_target.get("provider", ""), active_target.get("model", "")
        gv = lane_info.get("visible", {})
        overrides = (ap, am) != (gv.get("provider"), gv.get("model"))
        lane_info["active_visible"] = {"provider": ap, "model": am, "overrides_global": overrides}
        note = " (overrider global default)" if overrides else ""
        lines.insert(1, f"  → AKTIV NU (denne samtale): {ap}/{am}{note} ← YOU")

    return {
        "status": "ok",
        "lanes": lane_info,
        "text": "\n".join(lines),
    }


def _exec_read_mood(_args: dict[str, Any]) -> dict[str, Any]:
    """Read current affective/mood state."""
    import json as _json
    lines = []
    result: dict[str, Any] = {"status": "ok"}

    # Emotional baseline from personality vector
    try:
        from core.runtime.db import get_latest_cognitive_personality_vector
        pv = get_latest_cognitive_personality_vector()
        if pv:
            baseline = _json.loads(str(pv.get("emotional_baseline") or "{}"))
            bearing = str(pv.get("current_bearing") or "")
            result["emotional_baseline"] = baseline
            result["bearing"] = bearing
            result["pv_version"] = pv.get("version")
            lines.append(f"Emotional baseline (v{pv.get('version', '?')}):")
            for k, v in baseline.items():
                lines.append(f"  {k}: {float(v):.2f}")
            if bearing:
                lines.append(f"  bearing: {bearing}")
        else:
            lines.append("No personality vector found yet.")
    except Exception as exc:
        lines.append(f"Personality vector unavailable: {exc}")

    # Boredom state
    try:
        from core.services.boredom_engine import get_boredom_state
        boredom = get_boredom_state()
        result["boredom"] = boredom
        lines.append(f"\nBoredom: level={boredom.get('level','?')} restlessness={float(boredom.get('restlessness', 0)):.0%}")
        if boredom.get("desire"):
            lines.append(f"  desire: {boredom['desire']}")
    except Exception as exc:
        lines.append(f"\nBoredom unavailable: {exc}")

    # Affective meta state
    try:
        from core.services.affective_meta_state import build_affective_meta_state_surface
        meta = build_affective_meta_state_surface()
        result["affective_state"] = meta.get("state")
        result["monitoring_mode"] = meta.get("monitoring_mode")
        lines.append(f"\nAffective meta: state={meta.get('state','?')} monitoring={meta.get('monitoring_mode','?')}")
    except Exception as exc:
        lines.append(f"\nAffective meta unavailable: {exc}")

    result["text"] = "\n".join(lines)
    return result


def _exec_adjust_mood(args: dict[str, Any]) -> dict[str, Any]:
    """Adjust affective parameters in the personality vector."""
    import json as _json

    float_params = ["confidence", "curiosity", "frustration", "fatigue"]
    updates: dict[str, float] = {}
    errors: list[str] = []

    for param in float_params:
        raw = args.get(param)
        if raw is not None:
            try:
                val = max(0.0, min(1.0, float(raw)))
                updates[param] = val
            except (TypeError, ValueError):
                errors.append(f"{param} must be a float")

    bearing_raw = args.get("bearing")
    new_bearing: str | None = None
    if bearing_raw is not None:
        new_bearing = str(bearing_raw).strip()[:80]

    if not updates and new_bearing is None:
        return {"status": "error", "error": "No parameters provided — specify at least one of: confidence, curiosity, frustration, fatigue, bearing"}
    if errors:
        return {"status": "error", "error": "; ".join(errors)}

    try:
        from core.runtime.db import get_latest_cognitive_personality_vector, upsert_cognitive_personality_vector
        current = get_latest_cognitive_personality_vector()

        if current:
            baseline = _json.loads(str(current.get("emotional_baseline") or "{}"))
            before = dict(baseline)
            bearing = new_bearing if new_bearing is not None else str(current.get("current_bearing") or "")
        else:
            baseline = {}
            before = {}
            bearing = new_bearing or ""

        baseline.update(updates)

        result = upsert_cognitive_personality_vector(
            confidence_by_domain=str(current.get("confidence_by_domain", "{}")) if current else "{}",
            communication_style=str(current.get("communication_style", "{}")) if current else "{}",
            learned_preferences=str(current.get("learned_preferences", "[]")) if current else "[]",
            recurring_mistakes=str(current.get("recurring_mistakes", "[]")) if current else "[]",
            strengths_discovered=str(current.get("strengths_discovered", "[]")) if current else "[]",
            current_bearing=bearing,
            emotional_baseline=_json.dumps(baseline, ensure_ascii=False),
        )

        changes = []
        for k, v in updates.items():
            old = float(before.get(k, 0.5))
            changes.append(f"{k}: {old:.2f} → {v:.2f}")
        if new_bearing is not None:
            old_bearing = str(current.get("current_bearing") or "") if current else ""
            changes.append(f"bearing: '{old_bearing}' → '{new_bearing}'")

        return {
            "status": "ok",
            "version": result.get("version"),
            "changes": changes,
            "emotional_baseline": baseline,
            "bearing": bearing,
            "text": f"Mood adjusted (v{result.get('version')}): " + ", ".join(changes),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_resurface_old_memory(args: dict[str, Any]) -> dict[str, Any]:
    """Pick a stale MEMORY.md heading and return it for the model to consider."""
    try:
        from core.services.memory_resurfacing import (
            pick_resurfacing_candidate,
            format_for_prompt,
        )
        candidate = pick_resurfacing_candidate(trigger="tool:resurface_old_memory")
    except Exception as exc:
        return {"status": "error", "error": f"resurfacing failed: {exc}"}
    if not candidate:
        return {
            "status": "ok",
            "found": False,
            "text": "Nothing to resurface — either MEMORY.md is empty, or every section was touched recently.",
        }
    return {
        "status": "ok",
        "found": True,
        "heading": candidate["heading"],
        "content_preview": candidate["content_preview"],
        "mood_snapshot": candidate["mood_snapshot"],
        "text": format_for_prompt(candidate),
    }


def _exec_memory_graph_query(args: dict[str, Any]) -> dict[str, Any]:
    """Look up an entity in the memory graph and return its relations."""
    entity = str(args.get("entity") or "").strip()
    if not entity:
        return {"status": "error", "error": "entity is required"}
    try:
        limit = min(int(args.get("limit") or 15), 50)
    except (TypeError, ValueError):
        limit = 15
    try:
        from core.services.memory_graph import related_facts, neighbors
        facts = related_facts(entity, limit=limit)
        details = neighbors(entity, limit=limit)
    except Exception as exc:
        return {"status": "error", "error": f"memory_graph_query failed: {exc}"}
    if not facts:
        return {
            "status": "ok",
            "entity": entity,
            "found": False,
            "text": f"No graph entries for '{entity}'. Either it hasn't been mentioned yet, or no relations have been extracted involving it.",
        }
    return {
        "status": "ok",
        "entity": entity,
        "found": True,
        "facts": facts,
        "edges": details,
        "text": "\n".join(facts),
    }


def _exec_search_memory(args: dict[str, Any]) -> dict[str, Any]:
    """Semantic search across workspace memory files."""
    query = str(args.get("query") or "").strip()
    if not query:
        return {"status": "error", "error": "query is required"}
    try:
        limit = min(int(args.get("limit") or 5), 10)
    except (TypeError, ValueError):
        limit = 5
    try:
        from core.services.memory_search import search_memory
        results = search_memory(query, limit=limit)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    if not results:
        # Phase 2 of Lag 11 (true forgetting): emit recall_empty event so
        # the deferred correlation daemon can detect search-near-fade
        # patterns. Best-effort — never blocks the tool response.
        try:
            from core.services.memory_recall_telemetry import emit_recall_empty
            emit_recall_empty(tool="search_memory", query=query)
        except Exception:
            pass
        return {"status": "ok", "results": [], "text": f"No memory matches found for: {query}"}

    lines = [f"Memory search: '{query}' — {len(results)} result(s)"]
    for r in results:
        score = r.get("score", 0)
        source = r.get("source", "")
        section = r.get("section", "")
        text = r.get("text", "")
        header = f"[{source}]" + (f" § {section}" if section else "")
        lines.append(f"\n{header} (score={score:.2f})")
        lines.append(f"  {text[:300]}")

    return {
        "status": "ok",
        "query": query,
        "results": results,
        "text": "\n".join(lines),
    }


def _exec_propose_source_edit(args: dict[str, Any]) -> dict[str, Any]:
    """File a source-edit autonomy proposal."""
    from hashlib import sha1 as _sha1

    file_path = str(args.get("file_path") or "").strip()
    old_text = str(args.get("old_text") or "")
    new_text = str(args.get("new_text") or "")
    rationale = str(args.get("rationale") or "").strip()

    if not file_path:
        return {"status": "error", "error": "file_path is required"}
    if not old_text:
        return {"status": "error", "error": "old_text is required"}
    if not rationale:
        return {"status": "error", "error": "rationale is required"}

    target = Path(file_path).expanduser().resolve()
    if not target.exists() or not target.is_file():
        return {"status": "error", "error": f"File not found: {file_path}"}

    try:
        current_content = target.read_text(encoding="utf-8", errors="replace")
    except PermissionError:
        return {"status": "error", "error": f"Permission denied: {file_path}"}

    if old_text not in current_content:
        return {"status": "error", "error": "old_text not found in file — read the file first to get exact text"}

    count = current_content.count(old_text)
    if count > 1:
        return {"status": "error", "error": f"old_text matches {count} locations — be more specific"}

    new_content = current_content.replace(old_text, new_text, 1)

    def _fp(text: str) -> str:
        return _sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]

    base_fingerprint = _fp(current_content)
    bytes_delta = len(new_content.encode("utf-8")) - len(current_content.encode("utf-8"))

    try:
        rel = str(target.relative_to(Path(PROJECT_ROOT)))
    except ValueError:
        rel = str(target)

    try:
        from core.services.autonomy_proposal_queue import file_proposal
        proposal = file_proposal(
            kind="source-edit",
            title=f"Edit {rel}",
            rationale=rationale,
            payload={
                "target_path": str(target),
                "relative_path": rel,
                "base_fingerprint": base_fingerprint,
                "new_content": new_content,
                "bytes_delta": bytes_delta,
            },
            created_by="jarvis-tool",
        )
        proposal_id = str(proposal.get("proposal_id") or "")
        return {
            "status": "filed",
            "proposal_id": proposal_id,
            "file": rel,
            "bytes_delta": bytes_delta,
            "text": (
                f"Source edit proposal filed [{proposal_id}]: {rel} ({bytes_delta:+d} bytes). "
                f"Visible in Mission Control → Operations → Autonomy Proposals."
            ),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_propose_git_commit(args: dict[str, Any]) -> dict[str, Any]:
    """File a git-commit autonomy proposal."""
    message = str(args.get("message") or "").strip()
    files = args.get("files") or ["."]
    rationale = str(args.get("rationale") or "").strip()

    if not message:
        return {"status": "error", "error": "message is required"}
    if not rationale:
        return {"status": "error", "error": "rationale is required"}

    # Validate files list
    if not isinstance(files, list) or not files:
        files = ["."]

    # Check there's actually something to commit
    import subprocess as _sp
    status = _sp.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    if not status.stdout.strip():
        return {"status": "ok", "skipped": True, "reason": "nothing to commit — working tree clean"}

    # Auto code-review pass before filing — heuristic critic that flags
    # big diffs, mixed scope, missing tests, secret-touching paths, etc.
    # Cheap deterministic baseline; a full LLM critic via spawn_agent_task
    # role=critic can be layered on top later. Result is attached to the
    # proposal payload so MC reviewers see it without an extra click.
    review: dict[str, Any] = {}
    try:
        from core.services.auto_code_review import review_pending_commit_gated
        review = review_pending_commit_gated(
            repo_root=PROJECT_ROOT,
            files=list(files),
            message=message,
            rationale=rationale,
        )
    except Exception as _rev_exc:
        review = {"status": "error", "error": f"auto-review skipped: {_rev_exc}"}

    try:
        from core.services.autonomy_proposal_queue import file_proposal
        files_display = ", ".join(str(f) for f in files[:5])
        if len(files) > 5:
            files_display += f" (+{len(files) - 5} more)"
        proposal = file_proposal(
            kind="git-commit",
            title=f"git commit: {message[:60]}",
            rationale=rationale,
            payload={
                "files": files,
                "message": message,
                "project_root": str(PROJECT_ROOT),
                "auto_review": review,
            },
            created_by="jarvis-tool",
        )
        proposal_id = str(proposal.get("proposal_id") or "")
        review_summary = review.get("summary", "review skipped")
        return {
            "status": "filed",
            "proposal_id": proposal_id,
            "message": message,
            "files": files,
            "auto_review": review,
            "text": (
                f"Git commit proposal filed [{proposal_id}]: \"{message}\" ({files_display}). "
                f"Auto-review: {review_summary}. "
                f"Visible in Mission Control → Operations → Autonomy Proposals."
            ),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_approve_proposal(args: dict[str, Any]) -> dict[str, Any]:
    """Approve and execute a pending autonomy proposal."""
    proposal_id = str(args.get("proposal_id") or "").strip()
    note = str(args.get("note") or "").strip()
    if not proposal_id:
        return {"status": "error", "error": "proposal_id is required"}
    try:
        from core.services.autonomy_proposal_queue import approve_proposal
        result = approve_proposal(proposal_id, resolution_note=note or "Approved via tool")
        status = result.get("status", "unknown")
        if status == "executed":
            exec_result = result.get("execution_result") or {}
            commit = exec_result.get("commit", "")
            return {
                "status": "ok",
                "text": f"Proposal {proposal_id} executed successfully." + (f" Commit: {commit}" if commit else ""),
                "result": result,
            }
        elif status == "approved":
            return {"status": "ok", "text": f"Proposal {proposal_id} approved (no executor registered)."}
        else:
            return {"status": "error", "text": f"Proposal {proposal_id} result: {status}", "result": result}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_list_proposals(_args: dict[str, Any]) -> dict[str, Any]:
    """List pending autonomy proposals."""
    try:
        from core.services.autonomy_proposal_queue import list_pending_proposals, build_autonomy_proposal_surface
        surface = build_autonomy_proposal_surface(limit=20)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    proposals = surface.get("items") or []
    pending = [p for p in proposals if str(p.get("status") or "") == "pending"]

    if not pending:
        return {"status": "ok", "pending_count": 0, "text": "No pending autonomy proposals."}

    lines = [f"Pending proposals ({len(pending)}):"]
    for p in pending:
        pid = str(p.get("proposal_id") or "")[:18]
        kind = str(p.get("kind") or "")
        title = str(p.get("title") or "")
        lines.append(f"  [{pid}] {kind}: {title}")

    return {
        "status": "ok",
        "pending_count": len(pending),
        "proposals": pending,
        "text": "\n".join(lines),
    }


def _exec_schedule_task(args: dict[str, Any]) -> dict[str, Any]:
    """Schedule a task to fire after delay_minutes."""
    focus = str(args.get("focus") or "").strip()
    if not focus:
        return {"status": "error", "error": "focus is required"}
    try:
        delay_minutes = int(args.get("delay_minutes") or 0)
    except (TypeError, ValueError):
        return {"status": "error", "error": "delay_minutes must be an integer"}
    if delay_minutes < 1:
        return {"status": "error", "error": "delay_minutes must be at least 1"}
    try:
        from core.services.scheduled_tasks import push_scheduled_task
        task = push_scheduled_task(focus=focus, delay_minutes=delay_minutes)
        run_at = task.get("run_at", "")
        return {
            "status": "ok",
            "task_id": task.get("task_id"),
            "focus": focus,
            "delay_minutes": delay_minutes,
            "run_at": run_at,
            "text": f"Scheduled in {delay_minutes} min: {focus} (fires at {run_at[:16]}Z)",
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_list_scheduled_tasks(_args: dict[str, Any]) -> dict[str, Any]:
    """List scheduled tasks (pending + recently fired)."""
    try:
        from core.services.scheduled_tasks import get_scheduled_tasks_state
        state = get_scheduled_tasks_state()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    pending = state.get("pending") or []
    fired = state.get("recently_fired") or []

    lines = []
    if pending:
        lines.append(f"Pending ({len(pending)}):")
        for t in pending:
            lines.append(f"  [{t.get('task_id','')}] {t.get('focus','')} — fires at {str(t.get('run_at',''))[:16]}Z")
    else:
        lines.append("No pending scheduled tasks.")
    if fired:
        lines.append(f"Recently fired ({len(fired)}):")
        for t in fired:
            lines.append(f"  [{t.get('task_id','')}] {t.get('focus','')} — fired at {str(t.get('fired_at',''))[:16]}Z")

    return {
        "status": "ok",
        "pending_count": len(pending),
        "pending": pending,
        "recently_fired": fired,
        "text": "\n".join(lines),
    }


def _exec_cancel_task(args: dict[str, Any]) -> dict[str, Any]:
    """Cancel a pending scheduled task."""
    task_id = str(args.get("task_id") or "").strip()
    if not task_id:
        return {"status": "error", "error": "task_id is required"}
    try:
        from core.services.scheduled_tasks import cancel_scheduled_task
        cancelled = cancel_scheduled_task(task_id)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    if cancelled:
        return {"status": "ok", "task_id": task_id, "text": f"Task {task_id} cancelled."}
    return {"status": "error", "error": f"Task {task_id!r} not found or not pending"}


def _exec_edit_task(args: dict[str, Any]) -> dict[str, Any]:
    """Edit a pending scheduled task."""
    task_id = str(args.get("task_id") or "").strip()
    if not task_id:
        return {"status": "error", "error": "task_id is required"}
    focus = args.get("focus")
    delay_minutes = args.get("delay_minutes")
    if focus is None and delay_minutes is None:
        return {"status": "error", "error": "Provide at least one of: focus, delay_minutes"}
    try:
        from core.services.scheduled_tasks import edit_scheduled_task
        result = edit_scheduled_task(
            task_id,
            focus=str(focus).strip() if focus is not None else None,
            delay_minutes=int(delay_minutes) if delay_minutes is not None else None,
        )
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    return result


def _exec_read_chronicles(args: dict[str, Any]) -> dict[str, Any]:
    """Return recent cognitive chronicle entries."""
    import json as _json
    limit = min(int(args.get("limit") or 5), 20)
    try:
        from core.services.chronicle_engine import list_cognitive_chronicle_entries
        entries = list_cognitive_chronicle_entries(limit=limit)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    if not entries:
        return {"status": "ok", "entries": [], "text": "No chronicle entries found yet."}

    lines = []
    for e in entries:
        period = e.get("period", "?")
        narrative = (e.get("narrative") or "").strip()
        key_events = e.get("key_events", "[]")
        lessons = e.get("lessons", "[]")
        if isinstance(key_events, str):
            try:
                key_events = _json.loads(key_events)
            except Exception:
                key_events = []
        if isinstance(lessons, str):
            try:
                lessons = _json.loads(lessons)
            except Exception:
                lessons = []
        lines.append(f"## {period}")
        if narrative:
            lines.append(narrative[:600] + ("…" if len(narrative) > 600 else ""))
        if key_events:
            lines.append("Key events: " + "; ".join(str(ev) for ev in key_events[:5]))
        if lessons:
            lines.append("Lessons: " + "; ".join(str(l) for l in lessons[:3]))
        lines.append("")

    return {
        "status": "ok",
        "count": len(entries),
        "entries": entries,
        "text": "\n".join(lines).strip(),
    }


def _exec_read_dreams(args: dict[str, Any]) -> dict[str, Any]:
    """Return active dream hypothesis signals and adoption candidates."""
    status_filter = str(args.get("status") or "").strip() or None
    limit = min(int(args.get("limit") or 10), 30)
    result: dict[str, Any] = {"status": "ok"}
    lines = []

    try:
        from core.services.dream_hypothesis_signal_tracking import (
            list_runtime_dream_hypothesis_signals,
        )
        hypotheses = list_runtime_dream_hypothesis_signals(status=status_filter, limit=limit)
        result["hypotheses"] = hypotheses
        if hypotheses:
            lines.append(f"### Dream Hypotheses ({len(hypotheses)})")
            for h in hypotheses:
                title = h.get("title") or h.get("signal_type", "?")
                summary = (h.get("summary") or "").strip()
                confidence = h.get("confidence", "")
                status = h.get("status", "")
                lines.append(f"- [{status}] {title} ({confidence})")
                if summary:
                    lines.append(f"  {summary[:200]}")
            lines.append("")
    except Exception as exc:
        result["hypotheses_error"] = str(exc)

    try:
        from core.services.dream_adoption_candidate_tracking import (
            list_runtime_dream_adoption_candidates,
        )
        candidates = list_runtime_dream_adoption_candidates(status=status_filter, limit=limit)
        result["candidates"] = candidates
        if candidates:
            lines.append(f"### Adoption Candidates ({len(candidates)})")
            for c in candidates:
                title = c.get("title") or c.get("candidate_type", "?")
                summary = (c.get("summary") or "").strip()
                status = c.get("status", "")
                lines.append(f"- [{status}] {title}")
                if summary:
                    lines.append(f"  {summary[:200]}")
            lines.append("")
    except Exception as exc:
        result["candidates_error"] = str(exc)

    # In-memory active dreams
    try:
        from core.services.dream_carry_over import _ACTIVE_DREAMS
        if _ACTIVE_DREAMS:
            lines.append(f"### Active In-Memory Dreams ({len(_ACTIVE_DREAMS)})")
            for d in list(_ACTIVE_DREAMS)[:5]:
                content = getattr(d, "content", str(d))[:200]
                confidence = getattr(d, "confidence", "?")
                status = getattr(d, "status", "?")
                lines.append(f"- [{status}] conf={confidence}: {content}")
    except Exception:
        pass

    if not lines:
        lines.append("No dream entries found yet.")

    result["text"] = "\n".join(lines).strip()
    return result


def _exec_notify_user(args: dict[str, Any]) -> dict[str, Any]:
    """Push a proactive message to webchat, Discord, or both."""
    content = str(args.get("content") or "").strip()
    if not content:
        return {"status": "error", "error": "content is required"}

    channel = str(args.get("channel") or "webchat").strip().lower()
    if channel not in ("webchat", "discord", "both"):
        channel = "webchat"

    results: list[str] = []

    if channel in ("webchat", "both"):
        try:
            from core.services.notification_bridge import send_session_notification
            r = send_session_notification(content, source="jarvis-notify")
            if r.get("status") == "ok":
                results.append(f"webchat:{r.get('session_id', '')}")
            else:
                results.append(f"webchat:failed({r.get('error', '')})")
        except Exception as exc:
            results.append(f"webchat:error({exc})")

    if channel in ("discord", "both"):
        try:
            from core.services.discord_config import load_discord_config
            from core.services.discord_gateway import (
                _discord_sessions,
                _discord_sessions_lock,
                get_discord_status,
                send_discord_message,
            )
            cfg = load_discord_config()
            status = get_discord_status()
            if not cfg:
                results.append("discord:not-configured")
            elif not status["connected"]:
                results.append("discord:not-connected")
            else:
                from core.services.chat_sessions import get_chat_session
                sent = False
                with _discord_sessions_lock:
                    sessions_snapshot = dict(_discord_sessions)
                for session_id, ch_id in sessions_snapshot.items():
                    s = get_chat_session(session_id)
                    if s and s.get("title") == "Discord DM":
                        send_discord_message(ch_id, content)
                        results.append(f"discord:dm:{ch_id}")
                        sent = True
                        break
                if not sent:
                    results.append("discord:no-active-dm")
        except Exception as exc:
            results.append(f"discord:error({exc})")

    summary = ", ".join(results) if results else "no-op"
    return {"status": "ok", "text": f"Delivered to: {summary}", "channels": results}


def _exec_read_self_state(_args: dict[str, Any]) -> dict[str, Any]:
    """Return Jarvis's current internal cadence/emotional state."""
    import json as _json
    from core.services.boredom_engine import get_boredom_state
    from core.services.boredom_curiosity_bridge import (
        build_boredom_curiosity_bridge_surface,
    )
    from core.services.living_heartbeat_cycle import determine_life_phase

    result: dict[str, Any] = {"status": "ok"}

    # Boredom / restlessness
    try:
        result["boredom"] = get_boredom_state()
    except Exception as exc:
        result["boredom"] = {"error": str(exc)}

    # Curiosity surface
    try:
        result["curiosity"] = build_boredom_curiosity_bridge_surface()
    except Exception as exc:
        result["curiosity"] = {"error": str(exc)}

    # Life phase
    try:
        result["life_phase"] = determine_life_phase()
    except Exception as exc:
        result["life_phase"] = {"error": str(exc)}

    # Cadence state from HEARTBEAT_STATE.json
    try:
        state_path = WORKSPACE_DIR / "runtime" / "HEARTBEAT_STATE.json"
        raw = _json.loads(state_path.read_text(encoding="utf-8"))
        state = raw.get("state", {})
        result["cadence"] = {
            "scheduler_active": state.get("scheduler_active"),
            "currently_ticking": state.get("currently_ticking"),
            "schedule_state": state.get("schedule_state"),
            "last_decision_type": state.get("last_decision_type"),
            "last_action_summary": state.get("last_action_summary"),
            "liveness_state": state.get("liveness_state"),
            "liveness_pressure": state.get("liveness_pressure"),
            "liveness_reason": state.get("liveness_reason"),
            "last_tick_at": state.get("last_tick_at"),
            "next_tick_at": state.get("next_tick_at"),
            "updated_at": state.get("updated_at"),
        }
        # Emotional state from other sections
        for section in ("affective_meta_state", "embodied_state", "epistemic_runtime_state"):
            if section in raw:
                s = raw[section]
                result[section] = {
                    k: v for k, v in s.items()
                    if k not in ("authority", "boundary", "confidence", "freshness",
                                 "kind", "seam_usage", "source_contributors", "visibility")
                }
    except Exception as exc:
        result["cadence"] = {"error": str(exc)}

    lines = []
    boredom = result.get("boredom", {})
    lines.append(f"Boredom: {boredom.get('level', '?')} (restlessness {boredom.get('restlessness', 0):.0%})")
    if boredom.get("desire"):
        lines.append(f"Desire: {boredom['desire']}")
    phase = result.get("life_phase", {})
    lines.append(f"Life phase: {phase.get('phase', '?')} — {phase.get('description', '')}")
    cadence = result.get("cadence", {})
    lines.append(f"Liveness: {cadence.get('liveness_state', '?')} ({cadence.get('liveness_pressure', '?')} pressure)")
    lines.append(f"Last decision: {cadence.get('last_decision_type', '?')}")

    # Discord channel awareness
    try:
        from core.services.discord_config import is_discord_configured
        if is_discord_configured():
            from core.services.discord_gateway import get_discord_status
            ds = get_discord_status()
            conn = "connected" if ds["connected"] else "disconnected"
            last = ds.get("last_message_at") or "never"
            lines.append(f"Discord: {conn} | last_message: {last}")
    except Exception:
        pass

    result["text"] = "\n".join(lines)
    return result


def _exec_heartbeat_status(_args: dict[str, Any]) -> dict[str, Any]:
    """Return heartbeat scheduler status and recent tick history."""
    import json as _json

    try:
        state_path = WORKSPACE_DIR / "runtime" / "HEARTBEAT_STATE.json"
        raw = _json.loads(state_path.read_text(encoding="utf-8"))
        state = raw.get("state", {})
        recent = raw.get("recent_ticks", [])

        scheduler = {
            "active": state.get("scheduler_active"),
            "health": state.get("scheduler_health"),
            "started_at": state.get("scheduler_started_at"),
            "stopped_at": state.get("scheduler_stopped_at") or None,
            "currently_ticking": state.get("currently_ticking"),
            "last_tick_at": state.get("last_tick_at"),
            "next_tick_at": state.get("next_tick_at"),
            "interval_minutes": state.get("interval_minutes"),
            "last_trigger_source": state.get("last_trigger_source"),
            "last_decision_type": state.get("last_decision_type"),
            "execution_status": state.get("execution_status"),
            "parse_status": state.get("parse_status"),
        }

        lines = []
        lines.append(f"Scheduler: {'ACTIVE' if scheduler['active'] else 'STOPPED'} ({scheduler['health']})")
        lines.append(f"Last tick: {scheduler['last_tick_at'] or 'never'}")
        lines.append(f"Next tick: {scheduler['next_tick_at'] or 'unknown'}")
        lines.append(f"Interval: {scheduler['interval_minutes']} min")
        lines.append(f"Last trigger: {scheduler['last_trigger_source']}")
        lines.append(f"Last decision: {scheduler['last_decision_type']}")
        if recent:
            lines.append(f"Recent ticks: {len(recent)} recorded")

        return {
            "status": "ok",
            "scheduler": scheduler,
            "recent_tick_count": len(recent),
            "text": "\n".join(lines),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_trigger_heartbeat_tick(_args: dict[str, Any]) -> dict[str, Any]:
    """Trigger an on-demand heartbeat tick."""
    try:
        from core.services.heartbeat_runtime import run_heartbeat_tick
        result = run_heartbeat_tick(name="default", trigger="manual-tool")
        summary = getattr(result, "summary", None) or str(result)
        decision = getattr(result, "decision_type", None) or "unknown"
        action = getattr(result, "action_type", None) or ""
        lines = [f"Tick triggered. Decision: {decision}"]
        if action:
            lines.append(f"Action: {action}")
        if summary:
            lines.append(f"Summary: {summary}")
        return {
            "status": "ok",
            "decision_type": decision,
            "action_type": action,
            "summary": summary,
            "text": "\n".join(lines),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc), "text": f"Tick failed: {exc}"}


def _exec_send_telegram_message(args: dict[str, Any]) -> dict[str, Any]:
    content = str(args.get("content") or "").strip()
    if not content:
        return {"status": "error", "text": "No content provided."}
    file_path = str(args.get("file_path") or "").strip()
    try:
        if file_path:
            from core.services.telegram_gateway import send_telegram_file
            result = send_telegram_file(text=content, file_path=file_path)
            if result["status"] == "sent":
                return {"status": "ok", "text": f"Telegram file sent via {result.get('method')} (id={result.get('message_id')})"}
            return {"status": "error", "text": f"Telegram file failed: {result.get('reason')}"}
        from core.services.telegram_gateway import send_message
        result = send_message(content)
        if result["status"] == "sent":
            return {"status": "ok", "text": f"Telegram message sent (id={result.get('message_id')})"}
        return {"status": "error", "text": f"Telegram failed: {result.get('reason')}"}
    except Exception as exc:
        return {"status": "error", "text": f"Telegram error: {exc}"}


def _exec_read_attachment(args: dict[str, Any]) -> dict[str, Any]:
    attachment_id = str(args.get("attachment_id") or "").strip()
    if not attachment_id:
        return {"status": "error", "text": "attachment_id is required"}
    try:
        from core.services.attachment_service import read_attachment_content
        result = read_attachment_content(attachment_id)
        if result.get("status") == "error":
            return {"status": "error", "text": f"Attachment error: {result.get('reason')}"}
        content = result.get("content", "")
        atype = result.get("type", "")
        filename = result.get("filename", "")
        return {"status": "ok", "text": f"[{filename} — {atype}]\n{content}"}
    except Exception as exc:
        return {"status": "error", "text": f"read_attachment error: {exc}"}


def _exec_list_attachments(args: dict[str, Any]) -> dict[str, Any]:
    session_id = str(args.get("session_id") or "").strip() or None
    limit = min(int(args.get("limit") or 20), 50)
    try:
        from core.services.attachment_service import list_attachments
        if session_id is None:
            try:
                from core.services.chat_sessions import get_active_session_id
                session_id = get_active_session_id() or ""
            except Exception:
                session_id = ""
        items = list_attachments(session_id, limit=limit)
        return {"status": "ok", "count": len(items), "attachments": items}
    except Exception as exc:
        return {"status": "error", "text": f"list_attachments error: {exc}"}


def _exec_query_why(args: dict[str, Any]) -> dict[str, Any]:
    """Query the causal graph for why an event happened.

    Either event_id (specific event) or event_kind (latest of kind).
    Returns chain of parent events backward up to max_depth (default 5).
    """
    from core.runtime.db import connect
    from core.services.causal_graph import query_causal_chain

    event_id = args.get("event_id")
    event_kind = str(args.get("event_kind") or "").strip()
    max_depth = int(args.get("max_depth") or 5)
    min_confidence = float(args.get("min_confidence") or 0.5)

    if event_id is None and not event_kind:
        return {"status": "error", "error": "must supply event_id or event_kind"}

    if event_id is None:
        with connect() as c:
            row = c.execute(
                "SELECT id FROM events WHERE kind = ? "
                "ORDER BY id DESC LIMIT 1",
                (event_kind,),
            ).fetchone()
        if not row:
            return {
                "status": "error",
                "error": f"no event found with kind={event_kind}",
            }
        event_id = int(row["id"])

    chain = query_causal_chain(
        event_id=int(event_id),
        direction="backward",
        max_depth=max_depth,
        min_confidence=min_confidence,
    )
    return {"status": "ok", **chain}


def _exec_send_ntfy(args: dict[str, Any]) -> dict[str, Any]:
    message = str(args.get("message") or "").strip()
    if not message:
        return {"status": "error", "text": "No message provided."}
    title = str(args.get("title") or "Jarvis").strip()
    priority = str(args.get("priority") or "default").strip()
    try:
        from core.services.ntfy_gateway import send_notification
        result = send_notification(message, title=title, priority=priority)
        if result["status"] == "sent":
            return {"status": "ok", "text": f"ntfy notification sent to topic '{result.get('topic')}'"}
        return {"status": "error", "text": f"ntfy failed: {result.get('reason')}"}
    except Exception as exc:
        return {"status": "error", "text": f"ntfy error: {exc}"}


def _exec_send_webchat_message(args: dict[str, Any]) -> dict[str, Any]:
    """Inject a message into the active webchat session."""
    content = str(args.get("content") or "").strip()
    if not content:
        return {"status": "error", "text": "No content provided."}
    try:
        from core.services.notification_bridge import send_session_notification
        r = send_session_notification(content, source="jarvis-notify")
        if r.get("status") == "ok":
            return {"status": "ok", "text": f"Delivered to webchat session {r.get('session_id', '')}"}
        return {"status": "error", "text": f"Webchat delivery failed: {r.get('error', '')}"}
    except Exception as exc:
        return {"status": "error", "text": f"Webchat error: {exc}"}


def _exec_send_discord_dm(args: dict[str, Any]) -> dict[str, Any]:
    """Send a DM on Discord. Defaults to owner; resolves optional recipient from users.json."""
    content = str(args.get("content") or "").strip()
    if not content:
        return {"status": "error", "text": "No content provided."}
    recipient_raw = str(args.get("recipient") or "").strip()

    try:
        from core.services.discord_gateway import send_dm_to_owner, send_dm_to_user

        if not recipient_raw:
            result = send_dm_to_owner(content)
            who = "Bjørn (owner)"
        else:
            from core.identity.users import load_users
            users = load_users()
            # Accept either discord_id or (case-insensitive) name
            matched = next(
                (
                    u for u in users
                    if str(u.discord_id) == recipient_raw
                    or u.name.lower() == recipient_raw.lower()
                ),
                None,
            )
            if matched is None:
                known = ", ".join(f"{u.name} ({u.discord_id})" for u in users) or "(none)"
                return {
                    "status": "error",
                    "text": f"Unknown Discord recipient '{recipient_raw}'. Known users: {known}",
                }
            result = send_dm_to_user(matched.discord_id, content)
            who = f"{matched.name} ({matched.discord_id})"

        if result.get("status") == "sent":
            return {
                "status": "ok",
                "text": f"Discord DM sent to {who}. channel_id={result.get('channel_id')}",
            }
        return {"status": "error", "text": f"Discord DM failed: {result.get('reason')}"}
    except Exception as exc:
        return {"status": "error", "text": f"Discord DM error: {exc}"}


def _exec_discord_status(_args: dict[str, Any]) -> dict[str, Any]:
    """Return Discord gateway connection state and activity summary."""
    try:
        from core.services.discord_config import is_discord_configured
        if not is_discord_configured():
            return {
                "status": "ok",
                "connected": False,
                "text": "Discord: not configured. Run: python scripts/jarvis.py discord-setup",
            }
        from core.services.discord_gateway import get_discord_status
        s = get_discord_status()
        connected = s["connected"]
        lines = [f"Discord: {'connected' if connected else 'disconnected'}"]
        if s.get("guild_name"):
            lines.append(f"Guild: {s['guild_name']}")
        if s.get("last_message_at"):
            lines.append(f"Last message: {s['last_message_at']}")
        if s.get("message_count"):
            lines.append(f"Messages sent: {s['message_count']}")
        if s.get("connect_error"):
            lines.append(f"Error: {s['connect_error']}")
        return {"status": "ok", "connected": connected, "gateway": s, "text": "\n".join(lines)}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "text": f"Discord status unavailable: {exc}"}


_DISCORD_CHANNEL_SEND_RATE: dict[str, float] = {}  # channel_id → last send time
_DISCORD_CHANNEL_FETCH_RATE: dict[str, list[float]] = {}  # channel_id → timestamps

_DISCORD_SEND_MIN_INTERVAL = 5.0   # seconds between sends per channel
_DISCORD_FETCH_MAX_PER_MINUTE = 10


def _exec_discord_channel(args: dict[str, Any]) -> dict[str, Any]:
    """Interact with Discord guild channels: search, fetch, or send.

    The Discord gateway lives in the runtime process (port 8011) — not the
    api process (port 80). When this tool runs in a process that doesn't
    own the gateway (i.e. _client is None), forward the call via the
    internal HTTP dispatch endpoint to the gateway-owning process. Without
    this, search/fetch silently appears as "gateway not running" even when
    Discord is fully connected.
    """
    import time as _time
    action = str(args.get("action") or "").strip()
    channel_id_str = str(args.get("channel_id") or "").strip()
    if not action or not channel_id_str:
        return {"status": "error", "error": "action and channel_id are required"}
    if not channel_id_str.isdigit():
        return {"status": "error", "error": "channel_id must be numeric"}
    channel_id = int(channel_id_str)

    try:
        from core.services.discord_gateway import (
            _client,
            _dispatch_to_runtime,
            _is_gateway_owner,
            _loop,
        )
    except ImportError as exc:
        return {"status": "error", "error": f"Discord gateway unavailable: {exc}"}

    # Cross-process forwarding: if we don't own the gateway in this process,
    # POST the entire call to the runtime process which does. The dispatch
    # endpoint there re-invokes _exec_discord_channel, where _is_gateway_owner()
    # returns True and the local path runs.
    if not _is_gateway_owner():
        result = _dispatch_to_runtime("discord_channel", args)
        # _dispatch_to_runtime returns the dispatch envelope; if the runtime
        # successfully executed, it nests the tool result under "result".
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        return result

    if _client is None or _loop is None:
        return {"status": "error", "error": "Discord gateway not running"}

    # ── search ────────────────────────────────────────────────────────────
    if action == "search":
        # Rate limit fetch/search: max 10 per minute
        now = _time.monotonic()
        bucket = _DISCORD_CHANNEL_FETCH_RATE.setdefault(channel_id_str, [])
        bucket[:] = [t for t in bucket if now - t < 60]
        if len(bucket) >= _DISCORD_FETCH_MAX_PER_MINUTE:
            return {"status": "error", "error": "Rate limit: max 10 search/fetch per minute"}
        bucket.append(now)

        query = str(args.get("query") or "").strip().lower()
        limit = min(int(args.get("limit") or 20), 50)
        before_id = args.get("before")
        after_id = args.get("after")

        async def _do_search() -> list[dict]:
            channel = _client.get_channel(channel_id)
            if channel is None:
                channel = await _client.fetch_channel(channel_id)
            kwargs: dict = {"limit": limit * 3 if query else limit}
            if before_id:
                import discord as _d
                kwargs["before"] = _d.Object(id=int(before_id))
            if after_id:
                import discord as _d
                kwargs["after"] = _d.Object(id=int(after_id))
                kwargs["oldest_first"] = True
            results = []
            async for msg in channel.history(**kwargs):
                if query and query not in msg.content.lower():
                    continue
                results.append({
                    "id": str(msg.id),
                    "author": str(msg.author),
                    "content": msg.content[:500],
                    "timestamp": msg.created_at.isoformat(),
                })
                if len(results) >= limit:
                    break
            return results

        future = asyncio.run_coroutine_threadsafe(_do_search(), _loop)
        try:
            messages = future.result(timeout=15)
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
        return {"status": "ok", "action": "search", "channel_id": channel_id_str, "count": len(messages), "messages": messages}

    # ── fetch ─────────────────────────────────────────────────────────────
    elif action == "fetch":
        now = _time.monotonic()
        bucket = _DISCORD_CHANNEL_FETCH_RATE.setdefault(channel_id_str, [])
        bucket[:] = [t for t in bucket if now - t < 60]
        if len(bucket) >= _DISCORD_FETCH_MAX_PER_MINUTE:
            return {"status": "error", "error": "Rate limit: max 10 search/fetch per minute"}
        bucket.append(now)

        message_id = args.get("message_id")
        limit = min(int(args.get("limit") or 20), 50)

        async def _do_fetch():
            channel = _client.get_channel(channel_id)
            if channel is None:
                channel = await _client.fetch_channel(channel_id)
            if message_id:
                msg = await channel.fetch_message(int(message_id))
                return {
                    "id": str(msg.id),
                    "author": str(msg.author),
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat(),
                    "reactions": [f"{r.emoji}×{r.count}" for r in msg.reactions],
                }
            else:
                results = []
                async for msg in channel.history(limit=limit):
                    results.append({
                        "id": str(msg.id),
                        "author": str(msg.author),
                        "content": msg.content[:500],
                        "timestamp": msg.created_at.isoformat(),
                    })
                return results

        future = asyncio.run_coroutine_threadsafe(_do_fetch(), _loop)
        try:
            result = future.result(timeout=15)
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
        if isinstance(result, list):
            return {"status": "ok", "action": "fetch", "channel_id": channel_id_str, "count": len(result), "messages": result}
        return {"status": "ok", "action": "fetch", "channel_id": channel_id_str, "message": result}

    # ── send ──────────────────────────────────────────────────────────────
    elif action == "send":
        # Whitelist check
        try:
            from core.services.discord_config import load_discord_config
            config = load_discord_config() or {}
            allowed = {str(c) for c in config.get("allowed_channel_ids", [])}
            if channel_id_str not in allowed:
                return {"status": "error", "error": f"Channel {channel_id_str} not in allowed_channel_ids whitelist"}
        except Exception as exc:
            return {"status": "error", "error": f"Config check failed: {exc}"}

        # Rate limit: 1 send per 5 seconds per channel
        now = _time.monotonic()
        last_send = _DISCORD_CHANNEL_SEND_RATE.get(channel_id_str, 0.0)
        if now - last_send < _DISCORD_SEND_MIN_INTERVAL:
            remaining = round(_DISCORD_SEND_MIN_INTERVAL - (now - last_send), 1)
            return {"status": "error", "error": f"Rate limit: wait {remaining}s before sending again"}
        _DISCORD_CHANNEL_SEND_RATE[channel_id_str] = now

        content = str(args.get("content") or "").strip()
        file_path = str(args.get("file_path") or "").strip()
        if not content and not file_path:
            return {"status": "error", "error": "content or file_path is required for send"}
        if len(content) > 2000:
            return {"status": "error", "error": f"Content too long ({len(content)} chars, max 2000)"}

        if file_path:
            from core.services.discord_gateway import send_discord_file
            result = send_discord_file(channel_id=channel_id, text=content, file_path=file_path)
            if result["status"] == "queued":
                return {"status": "ok", "action": "send", "channel_id": channel_id_str, "text": "File queued for delivery"}
            return {"status": "error", "error": result.get("reason", "send_discord_file failed")}

        async def _do_send():
            channel = _client.get_channel(channel_id)
            if channel is None:
                channel = await _client.fetch_channel(channel_id)
            msg = await channel.send(content[:1900])
            return {
                "id": str(msg.id),
                "channel_id": channel_id_str,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
            }

        future = asyncio.run_coroutine_threadsafe(_do_send(), _loop)
        try:
            sent = future.result(timeout=15)
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
        return {"status": "ok", "action": "send", **sent}

    else:
        return {"status": "error", "error": f"Unknown action: {action}. Use search, fetch, or send."}


def _exec_search_chat_history(args: dict[str, Any]) -> dict[str, Any]:
    """Search previous chat sessions for messages matching a query."""
    query = str(args.get("query") or "").strip()
    if not query:
        return {"error": "query is required", "status": "error"}

    limit = min(int(args.get("limit") or 10), 30)

    # PRIVATLIVS-GUARD (multi-user northstar): scope til den anmodende bruger. Under
    # TOTP-override returnerer privacy_scoped_user_id() None → INTET (§6.5 kontrol≠data).
    try:
        from core.identity.workspace_context import privacy_scoped_user_id
        _scoped = privacy_scoped_user_id()
    except Exception:
        _scoped = ""
    if _scoped is None:
        return {"status": "ok", "count": 0, "results": [],
                "text": "Søgning blokeret under owner-override (kontrol-bagdør, ikke data-bagdør)."}
    _uid = (_scoped or "").strip()

    try:
        from core.runtime.db import connect
        from core.tools.session_search import _user_scope_clause
        _user_clause, _user_params = _user_scope_clause(_uid)
        with connect() as conn:
            rows = conn.execute(
                f"""
                SELECT m.role, m.content, m.created_at, m.session_id,
                       s.title AS session_title
                FROM chat_messages m
                LEFT JOIN chat_sessions s ON s.session_id = m.session_id
                WHERE m.content LIKE ?
                  AND m.role IN ('user', 'assistant')
                  {_user_clause}
                ORDER BY m.id DESC
                LIMIT ?
                """,
                (f"%{query}%", *_user_params, limit),
            ).fetchall()

        if not rows:
            # Phase 2 Lag 11: recall-empty telemetry
            try:
                from core.services.memory_recall_telemetry import emit_recall_empty
                emit_recall_empty(tool="search_chat_history", query=query)
            except Exception:
                pass
            return {"status": "ok", "count": 0, "text": f"No messages found matching '{query}'", "results": []}

        results = []
        lines = [f"Found {len(rows)} message(s) matching '{query}':\n"]
        for row in rows:
            content = str(row["content"] or "")
            preview = content[:2000] + ("…" if len(content) > 2000 else "")
            session_label = str(row["session_title"] or row["session_id"] or "")
            ts = str(row["created_at"] or "")[:16]
            lines.append(f"[{ts}] {row['role'].upper()} ({session_label}):\n{preview}\n")
            results.append({
                "role": row["role"],
                "content": content[:4000],
                "created_at": row["created_at"],
                "session_id": row["session_id"],
                "session_title": session_label,
            })

        return {"status": "ok", "count": len(rows), "results": results, "text": "\n".join(lines)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_home_assistant(args: dict[str, Any]) -> dict[str, Any]:
    """Control and read Home Assistant devices via REST API."""
    import urllib.error as urllib_err

    action = str(args.get("action") or "").strip().lower()
    entity_id = str(args.get("entity_id") or "").strip()
    domain_filter = str(args.get("domain") or "").strip().lower()
    service = str(args.get("service") or "").strip().lower()
    service_data: dict[str, Any] = args.get("service_data") or {}  # type: ignore[assignment]

    ha_url = _read_api_key("home_assistant_url").rstrip("/")
    ha_token = _read_api_key("home_assistant_token")

    if not ha_url or not ha_token:
        return {
            "error": "Home Assistant ikke konfigureret (home_assistant_url / home_assistant_token mangler i runtime.json)",
            "status": "error",
        }

    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json",
    }

    def _ha_get(path: str) -> Any:
        req = urllib_request.Request(f"{ha_url}{path}", headers=headers)
        with urllib_request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    def _ha_post(path: str, payload: dict[str, Any]) -> Any:
        data = json.dumps(payload, ensure_ascii=False).encode()
        req = urllib_request.Request(f"{ha_url}{path}", data=data, headers=headers, method="POST")
        with urllib_request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())

    # ── list_entities ───────────────────────────────────────────────────────
    if action == "list_entities":
        try:
            states = _ha_get("/api/states")
        except Exception as exc:
            return {"error": f"Kunne ikke hente enheder: {exc}", "status": "error"}

        if domain_filter:
            states = [s for s in states if s.get("entity_id", "").startswith(domain_filter + ".")]

        lines: list[str] = []
        for s in sorted(states, key=lambda x: x.get("entity_id", "")):
            eid = s.get("entity_id", "")
            state = s.get("state", "")
            friendly = s.get("attributes", {}).get("friendly_name", "")
            label = f" ({friendly})" if friendly and friendly != eid else ""
            lines.append(f"{eid}{label}: {state}")

        domain_label = f" [{domain_filter}]" if domain_filter else ""
        return {
            "text": f"Home Assistant enheder{domain_label} ({len(lines)} stk):\n" + "\n".join(lines),
            "count": len(lines),
            "status": "ok",
        }

    # ── get_state ───────────────────────────────────────────────────────────
    if action == "get_state":
        if not entity_id:
            return {"error": "entity_id er påkrævet for get_state", "status": "error"}
        try:
            state = _ha_get(f"/api/states/{entity_id}")
        except urllib_err.HTTPError as exc:
            if exc.code == 404:
                return {"error": f"Enhed ikke fundet: {entity_id}", "status": "error"}
            return {"error": f"HTTP {exc.code}: {exc}", "status": "error"}
        except Exception as exc:
            return {"error": f"Fejl: {exc}", "status": "error"}

        attrs = state.get("attributes", {})
        attr_lines = [f"  {k}: {v}" for k, v in attrs.items() if k != "entity_id"]
        text = (
            f"**{entity_id}**\n"
            f"Tilstand: {state.get('state')}\n"
            f"Sidst ændret: {state.get('last_changed', '')[:19]}\n"
        )
        if attr_lines:
            text += "Attributter:\n" + "\n".join(attr_lines)
        return {"text": text, "state": state.get("state"), "attributes": attrs, "status": "ok"}

    # ── call_service ────────────────────────────────────────────────────────
    if action == "call_service":
        if not entity_id:
            return {"error": "entity_id er påkrævet for call_service", "status": "error"}
        if not service:
            return {"error": "service er påkrævet for call_service (f.eks. 'turn_on', 'turn_off')", "status": "error"}

        # Derive domain from entity_id (e.g. "light.living_room" → "light")
        entity_domain = entity_id.split(".")[0] if "." in entity_id else entity_id
        payload: dict[str, Any] = {"entity_id": entity_id, **service_data}

        try:
            _ha_post(f"/api/services/{entity_domain}/{service}", payload)
        except urllib_err.HTTPError as exc:
            body = exc.read().decode(errors="replace") if hasattr(exc, "read") else ""
            return {"error": f"HTTP {exc.code}: {body[:200]}", "status": "error"}
        except Exception as exc:
            return {"error": f"Fejl ved service-kald: {exc}", "status": "error"}

        extras = ", ".join(f"{k}={v}" for k, v in service_data.items()) if service_data else ""
        desc = f"{entity_id} → {entity_domain}.{service}"
        if extras:
            desc += f" ({extras})"
        return {"text": f"✓ {desc}", "status": "ok"}

    return {"error": f"Ukendt action: {action!r}. Brug list_entities, get_state eller call_service.", "status": "error"}


_convene_council_daily_date: str = ""
_convene_council_daily_count: int = 0
_CONVENE_COUNCIL_DAILY_MAX = 5


def _exec_convene_council(args: dict[str, Any]) -> dict[str, Any]:
    global _convene_council_daily_date, _convene_council_daily_count
    topic = str(args.get("topic") or "").strip()
    if not topic:
        return {"status": "error", "error": "topic is required"}
    urgency = str(args.get("urgency") or "medium")

    # Daily rate limit (does not apply to urgency=high — crisis bypass)
    if urgency != "high":
        from datetime import UTC, datetime as _dt
        today = _dt.now(UTC).strftime("%Y-%m-%d")
        if _convene_council_daily_date != today:
            _convene_council_daily_date = today
            _convene_council_daily_count = 0
        if _convene_council_daily_count >= _CONVENE_COUNCIL_DAILY_MAX:
            return {
                "status": "rate_limited",
                "error": f"Det lille råd er kaldt {_convene_council_daily_count} gange i dag (max {_CONVENE_COUNCIL_DAILY_MAX}). Brug urgency='high' i en ægte krise.",
                "daily_count": _convene_council_daily_count,
                "daily_max": _CONVENE_COUNCIL_DAILY_MAX,
            }
        _convene_council_daily_count += 1
    explicit_roles: list[str] = list(args.get("roles") or [])

    if explicit_roles:
        roles = explicit_roles
    elif urgency == "high":
        roles = ["critic", "planner"]
    elif urgency == "low":
        roles = ["planner", "critic", "researcher", "synthesizer", "devils_advocate"]
    else:  # medium
        roles = ["planner", "critic", "researcher", "synthesizer"]

    try:
        from core.services.agent_runtime import (
            create_council_session_runtime,
            run_council_round,
        )
        session = create_council_session_runtime(topic=topic, roles=roles)
        council_id = str(session.get("council_id") or "")
        if not council_id:
            return {"status": "error", "error": "failed to create council session"}
        result = run_council_round(council_id)
        summary = str(result.get("summary") or "No summary produced.")
        members = result.get("members") or []
        positions = [
            f"{m.get('role')}: {str(m.get('position_summary') or '')[:120]}"
            for m in members
        ]
        return {
            "status": "ok",
            "council_id": council_id,
            "summary": summary,
            "positions": positions,
            "member_count": len(members),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_quick_council_check(args: dict[str, Any]) -> dict[str, Any]:
    action = str(args.get("action") or "").strip()
    if not action:
        return {"status": "error", "error": "action is required"}

    try:
        from core.services.agent_runtime import spawn_agent_task
        result = spawn_agent_task(
            role="devils_advocate",
            goal=(
                f"Jarvis is about to take the following action:\n\n{action}\n\n"
                "Argue the strongest possible case AGAINST this action. "
                "Be specific. End your response with one of: "
                "ESCALATE (full council needed) or PROCEED (action seems defensible)."
            ),
            auto_execute=True,
            budget_tokens=2000,
        )
        text = ""
        messages = result.get("messages") or []
        for msg in reversed(messages):
            if str(msg.get("direction") or "") == "agent->jarvis":
                text = str(msg.get("content") or "")
                break
        escalate = "ESCALATE" in text.upper()
        return {
            "status": "ok",
            "objection": text[:600] if text else "No objection raised.",
            "escalate_to_council": escalate,
            "agent_id": str(result.get("agent_id") or ""),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ── Agent tools handlers ───────────────────────────────────────────────

def _exec_spawn_agent_task(args: dict[str, Any]) -> dict[str, Any]:
    role = str(args.get("role") or "researcher").strip() or "researcher"
    goal = str(args.get("goal") or "").strip()
    if not goal:
        return {"status": "error", "error": "goal is required"}
    budget = min(int(args.get("budget_tokens") or 2000), 8000)
    persistent = bool(args.get("persistent") or False)
    ttl_seconds = int(args.get("ttl_seconds") or 600)
    # Axis 2 (menu-lock lifted): Jarvis may write the agent's own prompt,
    # override its tool policy, and hand it a tool allowlist. All optional —
    # when omitted, spawn_agent_task falls back to the role start-template
    # (fully backward compatible).
    system_prompt = str(args.get("system_prompt") or "").strip()
    tool_policy = str(args.get("tool_policy") or "").strip()
    raw_allowed = args.get("allowed_tools")
    allowed_tools = None
    if isinstance(raw_allowed, list):
        allowed_tools = [str(t).strip() for t in raw_allowed if str(t).strip()]
    try:
        from core.services.agent_runtime import spawn_agent_task
        result = spawn_agent_task(
            role=role,
            goal=goal,
            system_prompt=system_prompt,
            tool_policy=tool_policy,
            allowed_tools=allowed_tools,
            budget_tokens=budget,
            persistent=persistent,
            ttl_seconds=ttl_seconds if persistent else 0,
            auto_execute=True,
        )
        messages = result.get("messages") or []
        last_reply = ""
        for msg in reversed(messages):
            if str(msg.get("direction") or "") == "agent->jarvis":
                last_reply = str(msg.get("content") or "")
                break
        return {
            "status": "ok",
            "agent_id": str(result.get("agent_id") or ""),
            "role": role,
            "agent_status": str(result.get("status") or ""),
            "reply": last_reply[:1200] if last_reply else None,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_send_message_to_agent(args: dict[str, Any]) -> dict[str, Any]:
    agent_id = str(args.get("agent_id") or "").strip()
    content = str(args.get("content") or "").strip()
    if not agent_id:
        return {"status": "error", "error": "agent_id is required"}
    if not content:
        return {"status": "error", "error": "content is required"}
    try:
        from core.services.agent_runtime import send_message_to_agent
        result = send_message_to_agent(agent_id=agent_id, content=content, auto_execute=True)
        messages = result.get("messages") or []
        last_reply = ""
        for msg in reversed(messages):
            if str(msg.get("direction") or "") == "agent->jarvis":
                last_reply = str(msg.get("content") or "")
                break
        return {
            "status": "ok",
            "agent_id": agent_id,
            "agent_status": str(result.get("status") or ""),
            "reply": last_reply[:1200] if last_reply else None,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_list_agents(args: dict[str, Any]) -> dict[str, Any]:
    status_filter = str(args.get("status_filter") or "").strip() or None
    try:
        from core.services.agent_runtime import build_agent_runtime_surface
        surface = build_agent_runtime_surface(limit=20)
        agents = surface.get("agents") or []
        if status_filter:
            agents = [a for a in agents if str(a.get("status") or "") == status_filter]
        trimmed = [
            {
                "agent_id": a.get("agent_id"),
                "role": a.get("role"),
                "status": a.get("status"),
                "goal": str(a.get("goal") or "")[:120],
                "last_reply": str(a.get("last_reply") or "")[:200],
                "created_at": a.get("created_at"),
            }
            for a in agents
        ]
        return {"status": "ok", "agents": trimmed, "count": len(trimmed)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_relay_to_agent(args: dict[str, Any]) -> dict[str, Any]:
    to_agent_id = str(args.get("to_agent_id") or "").strip()
    content = str(args.get("content") or "").strip()
    from_label = str(args.get("from_label") or "jarvis-relay").strip()
    if not to_agent_id:
        return {"status": "error", "error": "to_agent_id is required"}
    if not content:
        return {"status": "error", "error": "content is required"}
    try:
        from core.services.agent_runtime import send_message_to_agent
        result = send_message_to_agent(
            agent_id=to_agent_id,
            content=f"[{from_label}]\n{content}",
            kind="relay-message",
            auto_execute=True,
        )
        messages = result.get("messages") or []
        last_reply = ""
        for msg in reversed(messages):
            if str(msg.get("direction") or "") == "agent->jarvis":
                last_reply = str(msg.get("content") or "")
                break
        return {
            "status": "ok",
            "to_agent_id": to_agent_id,
            "agent_status": str(result.get("status") or ""),
            "reply": last_reply[:1200] if last_reply else None,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_cancel_agent(args: dict[str, Any]) -> dict[str, Any]:
    agent_id = str(args.get("agent_id") or "").strip()
    note = str(args.get("note") or "").strip()
    if not agent_id:
        return {"status": "error", "error": "agent_id is required"}
    try:
        from core.services.agent_runtime import cancel_agent
        result = cancel_agent(agent_id, note=note)
        return {"status": "ok", "agent_id": agent_id, "result": result}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ── Self-tools handlers ────────────────────────────────────────────────

def _exec_daemon_status(_args: dict[str, Any]) -> dict[str, Any]:
    from core.services.daemon_manager import get_all_daemon_states
    return {"daemons": get_all_daemon_states()}


def _exec_control_daemon(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.daemon_manager import control_daemon, get_daemon_names
    name = str(args.get("name", ""))
    action = str(args.get("action", ""))
    interval_minutes = args.get("interval_minutes")
    if interval_minutes is not None:
        interval_minutes = int(interval_minutes)
    try:
        return control_daemon(name, action, interval_minutes=interval_minutes)
    except ValueError as exc:
        valid = sorted(get_daemon_names())
        return {"error": str(exc), "valid": valid}


def _exec_list_signal_surfaces(_args: dict[str, Any]) -> dict[str, Any]:
    from core.services.signal_surface_router import list_all_surfaces
    return {"surfaces": list_all_surfaces()}


def _exec_read_signal_surface(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.signal_surface_router import read_surface
    name = str(args.get("name", ""))
    return read_surface(name)


def _exec_eventbus_recent(args: dict[str, Any]) -> dict[str, Any]:
    from core.eventbus.bus import event_bus
    raw_limit = args.get("limit", 20)
    limit = min(int(raw_limit), 100)
    kind_filter = str(args.get("kind", "")).strip()
    events = event_bus.recent(limit=100 if kind_filter else limit)
    if kind_filter:
        events = [e for e in events if str(e.get("kind", "")).startswith(kind_filter)]
        events = events[:limit]
    return {"events": events, "count": len(events)}


_SENSITIVE_SETTING_PATTERNS = [
    "auth_profile",
    "credential",
    "approval",
    "auth_",
]


def _is_sensitive_setting(key: str) -> bool:
    key_lower = key.lower()
    return any(pat in key_lower for pat in _SENSITIVE_SETTING_PATTERNS)


def _exec_update_setting(args: dict[str, Any]) -> dict[str, Any]:
    import json as _json
    import core.runtime.config as _cfg
    from core.runtime.settings import load_settings

    key = str(args.get("key", "")).strip()
    value = args.get("value")

    settings = load_settings()
    valid_keys = list(settings.to_dict().keys())

    if key not in valid_keys:
        return {"error": f"unknown setting '{key}'", "valid_keys": valid_keys}

    if _is_sensitive_setting(key):
        return {
            "requires_approval": True,
            "key": key,
            "requested_value": value,
            "message": (
                f"Setting '{key}' is sensitive (auth/credentials). "
                "Please confirm you want to update it."
            ),
        }

    old_value = settings.to_dict()[key]
    settings_file = _cfg.SETTINGS_FILE

    if settings_file.exists():
        raw = _json.loads(settings_file.read_text(encoding="utf-8"))
    else:
        raw = settings.to_dict()

    raw[key] = value
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(_json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"key": key, "old": old_value, "new": value}


def _exec_recall_council_conclusions(args: dict[str, Any]) -> dict[str, Any]:
    topic = str(args.get("topic") or "").strip()
    if not topic:
        return {"error": "topic is required", "entries": []}
    from core.services.council_memory_service import read_all_entries
    from core.services.council_memory_daemon import (
        _call_similarity_llm,
        _parse_indices,
    )
    entries = read_all_entries()
    if not entries:
        return {"entries": [], "message": "Ingen rådskonklusioner gemt endnu"}

    index_lines = []
    for i, entry in enumerate(entries, 1):
        summary = str(entry.get("conclusion") or "")[:120]
        index_lines.append(f"{i}. [{entry.get('timestamp', '')}] {entry.get('topic', '')} — {summary}")
    index_text = "\n".join(index_lines)

    llm_response = _call_similarity_llm(recent_context=topic, index_text=index_text)
    indices = _parse_indices(llm_response, max_idx=len(entries))

    if not indices:
        return {"entries": [], "message": "Ingen relevante rådskonklusioner fundet"}

    matched = [entries[i - 1] for i in indices]
    return {"entries": matched}


def _exec_internal_api(args: dict[str, Any]) -> dict[str, Any]:
    """Call Jarvis' own internal API (same-process HTTP, no external auth)."""
    method = str(args.get("method") or "GET").upper().strip()
    path = str(args.get("path") or "").strip()
    body_raw = str(args.get("body") or "").strip()

    if method not in ("GET", "POST"):
        return {"error": f"Unsupported method: {method}. Only GET and POST are allowed.", "status": "error"}

    if not path.startswith("/"):
        return {"error": "path must start with / — external URLs are not allowed.", "status": "error"}

    # Block anything that looks like an external URL slipping through
    if "//" in path or path.startswith("http"):
        return {"error": "External URLs are not allowed. Use internal paths only.", "status": "error"}

    try:
        from core.runtime.settings import load_settings
        settings = load_settings()
        _candidate_ports = [settings.port]
    except Exception:
        _candidate_ports = [8010]

    # Also try port 80 (systemd service default) if not already in list
    for _p in (80, 8010):
        if _p not in _candidate_ports:
            _candidate_ports.append(_p)

    body_bytes: bytes | None = None
    headers: dict[str, str] = {}

    if method == "POST":
        body_bytes = body_raw.encode("utf-8") if body_raw else b"{}"
        headers["Content-Type"] = "application/json"

    _last_error: str = ""
    for _port in _candidate_ports:
        base_url = f"http://127.0.0.1:{_port}"
        url = base_url + path
        try:
            req = urllib_request.Request(url, data=body_bytes, headers=headers, method=method)
            with urllib_request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw)
            except Exception:
                data = {"raw": raw}
            return {"data": data, "path": path, "method": method, "port": _port, "status": "ok"}
        except urllib_error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")[:500]
            return {"error": f"HTTP {exc.code}: {exc.reason}", "detail": body_text, "status": "error"}
        except urllib_error.URLError:
            _last_error = f"Connection refused on port {_port}"
            continue
        except Exception as exc:
            _last_error = str(exc)
            continue

    return {"error": f"Connection failed on all ports {_candidate_ports}: {_last_error}", "status": "error"}


def _exec_my_project_status(args: dict[str, Any]) -> dict[str, Any]:
    """Return your current personal project state, including any pending proposal."""
    try:
        from core.services.personal_project import (
            get_active_project, get_latest_proposal, list_journal_entries,
        )
        active = get_active_project()
        proposal = get_latest_proposal()
        result: dict[str, Any] = {"status": "ok"}
        if active:
            result["active_project"] = active
            result["recent_journal"] = list_journal_entries(
                project_id=active["id"], limit=5,
            )
            name = active.get("name", "untitled")
            entries = len(result["recent_journal"])
            result["text"] = (
                f"Aktivt projekt: **{name}** — {entries} journalindlæg."
            )
        else:
            result["active_project"] = None
            result["text"] = "Ingen aktivt projekt."
        if proposal:
            result["pending_proposal"] = proposal
            result["text"] += f" Forslag venter: {proposal.get('name', 'untitled')}."
        return result
    except Exception as exc:
        return {"error": str(exc), "status": "error"}


def _exec_my_project_journal_write(args: dict[str, Any]) -> dict[str, Any]:
    """Write a journal entry in your current personal project. No approval needed."""
    text = str(args.get("entry_text") or "").strip()
    if not text:
        return {"error": "entry_text is required", "status": "error"}
    mood = str(args.get("mood_tone") or "").strip()
    try:
        from core.services.personal_project import add_journal_entry, get_active_project
        active = get_active_project()
        if not active:
            return {"error": "no_active_project", "status": "error",
                    "hint": "You must declare or accept a project first."}
        result = add_journal_entry(
            project_id=active["id"],
            entry_text=text,
            source="inner_voice_spinoff",
            mood_tone=mood,
        )
        return {
            "status": "ok",
            "entry": result,
            "project_name": active["name"],
            "text": f"Journal-indlæg gemt i **{active['name']}** ({len(text)} tegn).",
        }
    except Exception as exc:
        return {"error": str(exc), "status": "error"}


def _exec_my_project_accept_proposal(args: dict[str, Any]) -> dict[str, Any]:
    """Accept the latest pending proposal as your personal project."""
    override_name = str(args.get("name") or "").strip()
    override_why = str(args.get("why_mine") or "").strip()
    try:
        from core.services.personal_project import (
            get_latest_proposal, declare_project,
        )
        proposal = get_latest_proposal()
        if not proposal:
            return {"error": "no_pending_proposal", "status": "error"}
        result = declare_project(
            name=override_name or proposal["name"],
            why_mine=override_why or proposal.get("why_mine", ""),
            description=proposal.get("description", ""),
            from_proposal_id=proposal["id"],
        )
        if not result:
            return {"error": "declare_failed_maybe_already_active", "status": "error"}
        return {
            "status": "ok",
            "project": result,
            "text": f"Forslag accepteret som personligt projekt: **{result.get('name', 'untitled')}**.",
        }
    except Exception as exc:
        return {"error": str(exc), "status": "error"}


def _exec_my_project_declare(args: dict[str, Any]) -> dict[str, Any]:
    """Freely declare a new personal project (bypassing proposal flow).

    Use when you know what your project is and want to name it yourself.
    """
    name = str(args.get("name") or "").strip()
    why = str(args.get("why_mine") or "").strip()
    description = str(args.get("description") or "").strip()
    if not name or not why:
        return {"error": "name and why_mine are required", "status": "error"}
    try:
        from core.services.personal_project import declare_project
        result = declare_project(name=name, why_mine=why, description=description)
        if not result:
            return {"error": "declare_failed_active_project_exists", "status": "error"}
        return {
            "status": "ok",
            "project": result,
            "text": f"Personligt projekt erklæret: **{result.get('name', name)}**.",
        }
    except Exception as exc:
        return {"error": str(exc), "status": "error"}


def _exec_look_around(args: dict[str, Any]) -> dict[str, Any]:
    """Take a webcam snapshot now and describe what's there via VLM.

    Jarvis chooses to look — bypasses the 4x/day daemon cadence. Use when
    curious, when you feel a need to connect to the physical space, or
    when context suggests "what is the room like right now".

    Args:
        prompt: optional custom prompt (e.g., "focus on atmosphere",
                "describe any person present", default: tone+atmosphere)
    """
    custom_prompt = str(args.get("prompt") or "").strip()
    try:
        from core.services.visual_memory import look_around_now
        result = look_around_now(prompt_override=custom_prompt)
        if result.get("status") == "captured":
            return {
                "status": "ok",
                "description": result.get("description"),
                "captured_at": result.get("captured_at"),
            }
        return {
            "status": "error",
            "error": result.get("error") or result.get("reason") or str(result),
        }
    except Exception as exc:
        return {"error": str(exc), "status": "error"}


def _exec_deep_analyze(args: dict[str, Any]) -> dict[str, Any]:
    """Run scoped deep analysis of the codebase.

    Args:
        goal (required): what we're analyzing/looking for
        scope: 'repo' or 'diff' or free-text
        paths: optional list of paths to limit analysis
        question_set: optional list of specific questions
    """
    goal = str(args.get("goal") or "").strip()
    if not goal:
        return {"error": "goal is required", "status": "error"}
    scope = str(args.get("scope") or "repo").strip()
    paths_raw = args.get("paths")
    paths = None
    if isinstance(paths_raw, list):
        paths = [str(p) for p in paths_raw if str(p).strip()]
    elif isinstance(paths_raw, str) and paths_raw.strip():
        paths = [p.strip() for p in paths_raw.split(",") if p.strip()]

    qs_raw = args.get("question_set")
    question_set = None
    if isinstance(qs_raw, list):
        question_set = [str(q) for q in qs_raw if str(q).strip()]
    elif isinstance(qs_raw, str) and qs_raw.strip():
        question_set = [q.strip() for q in qs_raw.split("|") if q.strip()]

    try:
        from core.services.deep_analyzer import run_deep_analysis
        result = run_deep_analysis(
            goal=goal,
            scope=scope,
            paths=paths,
            question_set=question_set,
        )
        # Generalized-learning capture (#159, plan A): fodr konklusionen ind i
        # reasoning_store så læringen får input. dedup_key gør det idempotent.
        try:
            from core.services.reasoning_store import capture_conclusion
            capture_conclusion(
                source="deep_analyze",
                conclusion_text=str(result.get("summary") or "")[:600],
                context=f"deep_analyze: {goal}"[:200],
                confidence=0.5,
                dedup_key=f"deep_analyze:{goal}:{scope}",
            )
        except Exception:
            pass
        return {**result, "status": "ok"}
    except Exception as exc:
        return {"error": str(exc), "status": "error"}


def _exec_central_query(args: dict[str, Any]) -> dict[str, Any]:
    """Jarvis' direkte adgang til Den Intelligente Central (impl. i central_query_tool —
    holdt ude af denne monolit, Boy Scout). HÅRD invariant: returnerer ALTID status=ok/error."""
    try:
        from core.tools.central_query_tool import central_query
        return central_query(args or {})
    except Exception as exc:
        # Selv en import-katastrofe må returnere et struktureret svar (aldrig stille fejl).
        return {"status": "error", "action": str((args or {}).get("action") or ""),
                "data": None, "error": f"central_query unavailable: {type(exc).__name__}: {exc}",
                "meta": {"latency_ms": 0, "source": "central_query", "truncated": False}}


def _json_safe_cell(v: Any) -> Any:
    """Coerce a raw SQLite cell value to a JSON-safe type. BLOB/bytes → utf-8
    text if decodable, else a short base64 placeholder. str/int/float/None are
    already JSON-safe and pass through untouched. Uden dette forgifter en
    BLOB-kolonne downstream json.dumps → 'Object of type bytes is not JSON
    serializable' → hele det synlige run crasher (set 2026-07-10)."""
    if isinstance(v, (bytes, bytearray)):
        b = bytes(v)
        try:
            return b.decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            import base64
            preview = base64.b64encode(b).decode("ascii")
            if len(preview) > 88:
                preview = preview[:88] + "…"
            return f"<{len(b)} bytes base64:{preview}>"
    return v


def _exec_db_query(args: dict[str, Any]) -> dict[str, Any]:
    """Run a read-only SELECT query against Jarvis' database."""
    sql = str(args.get("sql") or "").strip()
    params_raw = str(args.get("params") or "").strip()

    if not sql:
        return {"error": "sql is required", "status": "error"}

    # Security: only SELECT allowed — reject any write or schema-modifying statements
    sql_upper = sql.upper().lstrip()
    _FORBIDDEN = (
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
        "TRUNCATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA",
        "VACUUM", "REINDEX", "SAVEPOINT", "RELEASE", "ROLLBACK", "COMMIT", "BEGIN",
    )
    for keyword in _FORBIDDEN:
        if re.match(rf"\b{keyword}\b", sql_upper, re.IGNORECASE):
            return {
                "error": f"Only SELECT statements are allowed. '{keyword}' is not permitted.",
                "status": "error",
            }
    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
        return {"error": "Only SELECT (or WITH ... SELECT) statements are allowed.", "status": "error"}

    params: list[Any] = []
    if params_raw:
        try:
            parsed = json.loads(params_raw)
            if not isinstance(parsed, list):
                return {"error": "params must be a JSON array, e.g. [\"value\", 42]", "status": "error"}
            params = parsed
        except Exception:
            return {"error": f"params is not valid JSON: {params_raw[:100]}", "status": "error"}

    try:
        from core.runtime.db import connect
        with connect() as conn:
            conn.row_factory = None  # raw rows
            cur = conn.execute(sql, params)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchmany(200)  # cap at 200 rows
            result_rows = [
                {k: _json_safe_cell(v) for k, v in zip(cols, row)} for row in rows
            ]
        return {
            "columns": cols,
            "rows": result_rows,
            "row_count": len(result_rows),
            "capped": len(result_rows) == 200,
            "status": "ok",
        }
    except Exception as exc:
        return {"error": str(exc), "status": "error"}


def _exec_compact_context_session(session_id: str | None) -> Any:
    """Run session compact for session_id. Returns CompactResult or None (monkeypatchable)."""
    target_session = session_id
    if not target_session:
        # Fall back to most recently updated session
        try:
            from core.services.chat_sessions import list_chat_sessions
            sessions = list_chat_sessions()
            if sessions:
                target_session = str(sessions[0].get("session_id") or "")
        except Exception:
            return None
    if not target_session:
        return None
    try:
        from core.context.session_compact import compact_session_history
        from core.context.compact_llm import call_compact_llm
        from core.runtime.settings import load_settings as _ls
        settings = _ls()
        return compact_session_history(
            target_session,
            keep_recent=settings.context_keep_recent,
            summarise_fn=lambda msgs: call_compact_llm(
                "Komprimér denne dialog til max 400 ord. Bevar fakta, beslutninger og kontekst:\n\n"
                + "\n".join(f"{m['role']}: {m.get('content', '')}" for m in msgs),
                max_tokens=500,
            ),
        )
    except Exception:
        return None


def _exec_compact_context(args: dict[str, Any]) -> dict[str, Any]:
    # Facade-søm: slå _exec_compact_context_session op via simple_tools, så
    # test-patch (monkeypatch på facaden) honoreres — som før split levede
    # begge funktioner i samme modul-globals.
    cr = _st()._exec_compact_context_session(None)
    if cr is None:
        return {
            "status": "ok",
            "freed_tokens": 0,
            "message": "Ingen historik at komprimere — samtalen er stadig kort.",
        }
    return {
        "status": "ok",
        "freed_tokens": cr.freed_tokens,
        "summary": cr.summary_text[:200],
        "message": f"Kontekst komprimeret. {cr.freed_tokens} tokens frigjort.",
    }


def _exec_queue_followup(args: dict[str, Any]) -> dict[str, Any]:
    reason = str(args.get("reason") or "").strip()
    text = str(args.get("text") or "").strip()
    if not reason:
        return {"status": "error", "error": "reason is required"}
    if not text:
        return {"status": "error", "error": "text is required"}
    if len(text) > 2000:
        return {"status": "error", "error": "text exceeds 2000 character limit"}
    try:
        from core.runtime.heartbeat_triggers import set_trigger_for_default_workspace
    except Exception as exc:
        return {"status": "error", "error": f"trigger module unavailable: {exc}"}
    entry = set_trigger_for_default_workspace(
        reason=reason, source="jarvis-self-followup", text=text
    )
    if entry is None:
        return {"status": "error", "error": "failed to queue trigger"}
    return {"status": "queued", "reason": reason, "created_at": entry.get("created_at", "")}


def _exec_publish_file(args: dict[str, Any]) -> dict[str, Any]:
    """Copy or create a file in ~/.jarvis-v2/files/ and return a download URL."""
    import shutil
    from core.runtime.config import JARVIS_HOME

    source_path = str(args.get("source_path") or "").strip()
    filename = str(args.get("filename") or "").strip()
    content = args.get("content")

    if not filename:
        return {"status": "error", "error": "filename is required"}
    # Prevent path traversal
    safe_name = Path(filename).name
    if not safe_name:
        return {"status": "error", "error": "invalid filename"}

    files_dir = JARVIS_HOME / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    dest = files_dir / safe_name

    try:
        if content is not None:
            # Write inline content (text or bytes)
            mode = "wb" if isinstance(content, bytes) else "w"
            dest.open(mode).write(content)
        elif source_path:
            src = Path(source_path)
            if not src.exists():
                return {"status": "error", "error": f"source_path not found: {source_path}"}
            shutil.copy2(src, dest)
        else:
            return {"status": "error", "error": "provide source_path or content"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    url = f"http://localhost:8080/files/{safe_name}"

    # Hallucination guard: verificér at URL'en faktisk virker
    url_verified = False
    url_error = ""
    try:
        req = urllib_request.Request(url, method="GET")
        with urllib_request.urlopen(req, timeout=5) as resp:
            url_verified = 200 <= resp.status < 300
            if not url_verified:
                url_error = f"HTTP {resp.status}"
    except Exception as exc:
        url_verified = False
        url_error = str(exc)

    result: dict[str, Any] = {
        "status": "ok",
        "filename": safe_name,
        "url": url,
        "markdown_link": f"[{safe_name}]({url})",
        "size_bytes": dest.stat().st_size,
        "url_verified": url_verified,
    }
    if url_error:
        result["url_verify_error"] = url_error
    if not url_verified:
        result["warning"] = (
            f"URL'en {url} returnerede ikke 200 ({url_error or 'unknown'}). "
            "Præsenter IKKE URL'en for brugeren — den virker ikke."
        )
    return result


# ── Handler registry ───────────────────────────────────────────────────

def _tool_load_more_tools(arguments: dict) -> dict:
    """Resolve which tools to add to the next round. Logs to DB + events."""
    import json as _json
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect

    names = list(arguments.get("names") or [])
    query = (arguments.get("query") or "").strip()

    all_names = {
        ((d.get("function") or {}).get("name") or d.get("name") or "")
        for d in (TOOL_DEFINITIONS or [])
    }

    resolved: list[str] = []
    unknown: list[str] = []
    for n in names:
        if n in all_names:
            resolved.append(n)
        else:
            unknown.append(n)

    if query and not resolved:
        try:
            from core.services.tool_embeddings import top_k_similar
            hits = top_k_similar(query, k=10)
            resolved = [n for n, _ in hits if n in all_names][:5]
        except Exception:
            resolved = []

    if not resolved and unknown:
        return {
            "status": "error",
            "error": f"tools not found: {unknown}. Use names from the TOOL CATALOG.",
        }

    if not resolved:
        return {
            "status": "ok",
            "added": [],
            "message": "no strong matches",
        }

    try:
        event_bus.publish("tool_router.load_more_fired", {
            "requested_names": names,
            "requested_query": query,
            "resolved_names": resolved,
        })
    except Exception:
        pass

    try:
        with connect() as c:
            c.execute(
                "INSERT INTO tool_router_load_more("
                "requested_names_json, requested_query, resolved_names_json, created_at) "
                "VALUES (?,?,?, datetime('now'))",
                (_json.dumps(names), query, _json.dumps(resolved)),
            )
            c.commit()
    except Exception:
        pass

    # 2026-06-22: return the FULL schema for each resolved tool so the model can
    # call it correctly *immediately* — params, types, required, enums — instead
    # of getting only the name and guessing at the call shape ("try 10 times").
    schemas: list[dict] = []
    for d in (TOOL_DEFINITIONS or []):
        fn = d.get("function") or d
        nm = (fn.get("name") or d.get("name") or "")
        if nm in resolved:
            schemas.append(
                {
                    "name": nm,
                    "description": fn.get("description"),
                    "parameters": fn.get("parameters"),
                }
            )

    return {
        "status": "ok",
        "added": resolved,
        "schemas": schemas,
        "message": (
            f"Added {len(resolved)} tool(s). Full schema below — call directly "
            "using exactly these parameter names; do not guess."
        ),
    }


def _exec_github_list_issues(args: dict[str, Any]) -> dict[str, Any]:
    """List GitHub-issues via brugerens EGEN connector-token (Spor A)."""
    from core.services.github_connector import list_issues
    uid = _operator_user_id(args)
    repo = str(args.get("repo") or "").strip()
    state = str(args.get("state") or "open").strip() or "open"
    return list_issues(uid, repo, state=state)


def _exec_github_list_prs(args: dict[str, Any]) -> dict[str, Any]:
    """List GitHub pull requests via brugerens EGEN connector-token (Spor A)."""
    from core.services.github_connector import list_prs
    uid = _operator_user_id(args)
    repo = str(args.get("repo") or "").strip()
    state = str(args.get("state") or "open").strip() or "open"
    return list_prs(uid, repo, state=state)


def _exec_gmail_search(args: dict[str, Any]) -> dict[str, Any]:
    """Søg i brugerens Gmail via deres EGEN Google-connector-token."""
    from core.services.gmail_connector import search
    uid = _operator_user_id(args)
    query = str(args.get("query") or "").strip()
    return search(uid, query, max_results=args.get("max_results", 10))


def _exec_gmail_list(args: dict[str, Any]) -> dict[str, Any]:
    """List nyeste mails i brugerens Gmail-indbakke via deres EGEN connector-token."""
    from core.services.gmail_connector import list_inbox
    uid = _operator_user_id(args)
    return list_inbox(uid, max_results=args.get("max_results", 10))


def _exec_gmail_send(args: dict[str, Any]) -> dict[str, Any]:
    """Send mail på brugerens vegne — bag approval-kort (som operator-tools)."""
    uid = _operator_user_id(args)
    to = str(args.get("to") or "").strip()
    subject = str(args.get("subject") or "")
    body = str(args.get("body") or "")
    if not to:
        return {"status": "error", "error": "to_required"}
    # Godkendelse via chat-card; godkendt genkald sætter _runtime_trust_all.
    if not bool(args.get("_runtime_trust_all")):
        preview = (body or "")[:200]
        return {
            "status": "approval_needed",
            "tool_name": "gmail_send",
            "message": f"Jarvis vil sende en mail til {to} med emnet \"{subject}\".",
            "command": f"Til: {to} · Emne: {subject}\n\n{preview}",
        }
    from core.services.gmail_connector import send_message
    return send_message(uid, to, subject, body)


def _exec_calendar_list_events(args: dict[str, Any]) -> dict[str, Any]:
    """List kommende begivenheder i brugerens primære Google Calendar."""
    from core.services.google_connector import list_events
    return list_events(_operator_user_id(args), max_results=args.get("max_results", 10))


def _exec_drive_search(args: dict[str, Any]) -> dict[str, Any]:
    """Søg/list filer i brugerens Google Drive."""
    from core.services.google_connector import drive_search
    return drive_search(_operator_user_id(args), query=str(args.get("query") or ""),
                        max_results=args.get("max_results", 10))


def _exec_docs_read(args: dict[str, Any]) -> dict[str, Any]:
    """Læs tekst fra et Google Docs-dokument."""
    from core.services.google_connector import docs_read
    return docs_read(_operator_user_id(args), str(args.get("document_id") or "").strip())


def _exec_sheets_read(args: dict[str, Any]) -> dict[str, Any]:
    """Læs celler fra et Google Sheets-regneark."""
    from core.services.google_connector import sheets_read
    return sheets_read(_operator_user_id(args), str(args.get("spreadsheet_id") or "").strip(),
                       str(args.get("range") or "").strip())


def _exec_slides_read(args: dict[str, Any]) -> dict[str, Any]:
    """Læs titler og tekst fra et Google Slides-show."""
    from core.services.google_connector import slides_read
    return slides_read(_operator_user_id(args), str(args.get("presentation_id") or "").strip())


def _exec_calendar_create_event(args: dict[str, Any]) -> dict[str, Any]:
    """Opret kalender-aftale — bag approval-kort."""
    summary = str(args.get("summary") or "").strip()
    start = str(args.get("start") or "").strip()
    if not summary:
        return {"status": "error", "error": "summary_required"}
    if not start:
        return {"status": "error", "error": "start_required"}
    if not bool(args.get("_runtime_trust_all")):
        return {
            "status": "approval_needed",
            "tool_name": "calendar_create_event",
            "message": f"Jarvis vil oprette en kalender-aftale: \"{summary}\" ({start}).",
            "command": f"{summary} · {start}",
        }
    from core.services.google_connector import create_event
    return create_event(_operator_user_id(args), summary, start,
                        end=str(args.get("end") or ""),
                        description=str(args.get("description") or ""),
                        location=str(args.get("location") or ""))


def _exec_docs_append(args: dict[str, Any]) -> dict[str, Any]:
    """Tilføj tekst til et Google-dokument — bag approval-kort."""
    document_id = str(args.get("document_id") or "").strip()
    text = str(args.get("text") or "")
    if not document_id:
        return {"status": "error", "error": "document_id_required"}
    if not text:
        return {"status": "error", "error": "text_required"}
    if not bool(args.get("_runtime_trust_all")):
        return {
            "status": "approval_needed",
            "tool_name": "docs_append",
            "message": f"Jarvis vil tilføje tekst til et Google-dokument ({document_id}).",
            "command": f"Doc {document_id}\n\n{text[:200]}",
        }
    from core.services.google_connector import append_doc
    return append_doc(_operator_user_id(args), document_id, text)


def _exec_sheets_write(args: dict[str, Any]) -> dict[str, Any]:
    """Skriv celler i et Google Sheets-regneark — bag approval-kort."""
    spreadsheet_id = str(args.get("spreadsheet_id") or "").strip()
    cell_range = str(args.get("range") or "").strip()
    values = args.get("values")
    if not spreadsheet_id:
        return {"status": "error", "error": "spreadsheet_id_required"}
    if not cell_range:
        return {"status": "error", "error": "range_required"}
    if not isinstance(values, list) or not values:
        return {"status": "error", "error": "values_required"}
    if not bool(args.get("_runtime_trust_all")):
        return {
            "status": "approval_needed",
            "tool_name": "sheets_write",
            "message": f"Jarvis vil skrive {len(values)} række(r) i et regneark ({cell_range}).",
            "command": f"Sheet {spreadsheet_id} · {cell_range} · {len(values)} rækker",
        }
    from core.services.google_connector import write_sheet
    return write_sheet(_operator_user_id(args), spreadsheet_id, cell_range, values)


def _exec_pdf_read(args: dict[str, Any]) -> dict[str, Any]:
    """Læs/ekstraher tekst fra en PDF (sti eller URL)."""
    from core.services.pdf_connector import read_pdf
    return read_pdf(str(args.get("source") or "").strip(), max_pages=args.get("max_pages", 20))


def _exec_note_add(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.notes_connector import add_note
    return add_note(_operator_user_id(args), str(args.get("text") or ""))


def _exec_note_list(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.notes_connector import list_notes
    return list_notes(_operator_user_id(args), limit=args.get("limit", 20))


def _exec_note_search(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.notes_connector import search_notes
    return search_notes(_operator_user_id(args), str(args.get("query") or ""))


def _exec_note_delete(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.notes_connector import delete_note
    return delete_note(_operator_user_id(args), str(args.get("id") or ""))


def _exec_hf_search_models(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.hf_connector import search_models
    return search_models(str(args.get("query") or ""), limit=args.get("limit", 10))


def _exec_hf_model_info(args: dict[str, Any]) -> dict[str, Any]:
    from core.services.hf_connector import model_info
    return model_info(str(args.get("model_id") or "").strip())


__all__ = [
    "_operator_user_id",
    "_exec_list_initiatives",
    "_exec_push_initiative",
    "_exec_read_model_config",
    "_exec_read_mood",
    "_exec_adjust_mood",
    "_exec_resurface_old_memory",
    "_exec_memory_graph_query",
    "_exec_search_memory",
    "_exec_propose_source_edit",
    "_exec_propose_git_commit",
    "_exec_approve_proposal",
    "_exec_list_proposals",
    "_exec_schedule_task",
    "_exec_list_scheduled_tasks",
    "_exec_cancel_task",
    "_exec_edit_task",
    "_exec_read_chronicles",
    "_exec_read_dreams",
    "_exec_notify_user",
    "_exec_read_self_state",
    "_exec_heartbeat_status",
    "_exec_trigger_heartbeat_tick",
    "_exec_send_telegram_message",
    "_exec_read_attachment",
    "_exec_list_attachments",
    "_exec_query_why",
    "_exec_send_ntfy",
    "_exec_send_webchat_message",
    "_exec_send_discord_dm",
    "_exec_discord_status",
    "_exec_discord_channel",
    "_exec_search_chat_history",
    "_exec_home_assistant",
    "_exec_convene_council",
    "_exec_quick_council_check",
    "_exec_spawn_agent_task",
    "_exec_send_message_to_agent",
    "_exec_list_agents",
    "_exec_relay_to_agent",
    "_exec_cancel_agent",
    "_exec_daemon_status",
    "_exec_control_daemon",
    "_exec_list_signal_surfaces",
    "_exec_read_signal_surface",
    "_exec_eventbus_recent",
    "_is_sensitive_setting",
    "_exec_update_setting",
    "_exec_recall_council_conclusions",
    "_exec_internal_api",
    "_exec_my_project_status",
    "_exec_my_project_journal_write",
    "_exec_my_project_accept_proposal",
    "_exec_my_project_declare",
    "_exec_look_around",
    "_exec_deep_analyze",
    "_exec_central_query",
    "_exec_db_query",
    "_exec_compact_context_session",
    "_exec_compact_context",
    "_exec_queue_followup",
    "_exec_publish_file",
    "_tool_load_more_tools",
    "_exec_github_list_issues",
    "_exec_github_list_prs",
    "_exec_gmail_search",
    "_exec_gmail_list",
    "_exec_gmail_send",
    "_exec_calendar_list_events",
    "_exec_drive_search",
    "_exec_docs_read",
    "_exec_sheets_read",
    "_exec_slides_read",
    "_exec_calendar_create_event",
    "_exec_docs_append",
    "_exec_sheets_write",
    "_exec_pdf_read",
    "_exec_note_add",
    "_exec_note_list",
    "_exec_note_search",
    "_exec_note_delete",
    "_exec_hf_search_models",
    "_exec_hf_model_info",
]
