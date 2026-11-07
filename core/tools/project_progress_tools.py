"""Værktøjs-indgange til to projekt-systemer der ellers ingen indgang havde.

sustained_project: langvarige projekter (``sustained_attention``). ``create`` og
    ``progress`` er indgangene der manglede; uden ``create`` kunne ``progress``
    aldrig ramme noget, for intet andet opretter et projekt.
creative_project: kreative projekter (``creative_projects``). Projekterne sås af
    ``seed_system``; det der manglede var at Jarvis kunne notere fremdrift.

Begge delegerer til produktionens service-funktioner. Ingen kopi af logikken:
et værktøj der fejler gør det fordi servicen afviser, og afvisningen gives
videre som en ærlig fejl — ikke som en tavs default.
"""
from __future__ import annotations

from typing import Any

from core.services import creative_projects, sustained_attention

_SUSTAINED_ACTIONS = ("create", "progress", "list")
_CREATIVE_ACTIONS = ("progress", "list")


def _err(message: str) -> dict[str, Any]:
    return {"status": "error", "error": message}


def _exec_sustained_project(args: dict[str, Any]) -> dict[str, Any]:
    action = str(args.get("action") or "").strip().lower()
    if action not in _SUSTAINED_ACTIONS:
        return _err(f"action must be one of {_SUSTAINED_ACTIONS}")

    if action == "list":
        status = str(args.get("status") or "").strip().lower() or None
        projects = sustained_attention.list_projects(status=status)
        return {"status": "ok", "count": len(projects), "projects": projects}

    if action == "create":
        name = str(args.get("name") or "").strip()
        if not name:
            return _err("name is required for create")
        try:
            project = sustained_attention.create_project(
                name=name,
                description=str(args.get("description") or ""),
                why=str(args.get("why") or ""),
                priority=str(args.get("priority") or "medium"),
                autonomy_level=str(args.get("autonomy_level") or "suggest"),
            )
        except ValueError as exc:  # servicens loft (max aktive projekter) er svaret, ikke et uheld
            return _err(str(exc))
        return {"status": "ok", "project": project}

    project_id = str(args.get("project_id") or "").strip()
    note = str(args.get("note") or "").strip()
    if not project_id:
        return _err("project_id is required for progress")
    if not note:
        return _err("note is required for progress")
    if not sustained_attention.add_progress(project_id, note):
        existing = sustained_attention.get_project(project_id)
        if existing is None:
            return _err(f"project_id {project_id!r} not found")
        return _err(
            f"project {project_id!r} is {existing.get('status')}; progress can "
            "only be added to an active or paused project"
        )
    return {"status": "ok", "project": sustained_attention.get_project(project_id)}


def _exec_creative_project(args: dict[str, Any]) -> dict[str, Any]:
    action = str(args.get("action") or "").strip().lower()
    if action not in _CREATIVE_ACTIONS:
        return _err(f"action must be one of {_CREATIVE_ACTIONS}")

    if action == "list":
        status = str(args.get("status") or "").strip().lower() or None
        projects = creative_projects.list_projects(status=status)
        return {"status": "ok", "count": len(projects), "projects": projects}

    project_id = str(args.get("project_id") or "").strip()
    note = str(args.get("note") or "").strip()
    if not project_id:
        return _err("project_id is required for progress")
    if not note:
        return _err("note is required for progress")
    if not creative_projects.add_progress_note(project_id, note):
        return _err(f"project_id {project_id!r} not found")
    return {"status": "ok", "project": creative_projects.get_project(project_id)}


PROJECT_PROGRESS_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "sustained_project",
            "description": (
                "Dine langvarige projekter (højst 5 aktive). action=create "
                "åbner et nyt; action=progress skriver en note om hvad du har "
                "gjort (og genoptager et pauset projekt); action=list viser "
                "projekterne med deres id. Et projekt uden fremdrift i 7 dage "
                "sættes automatisk på pause."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": list(_SUSTAINED_ACTIONS)},
                    "project_id": {"type": "string", "description": "Kræves for progress (fra list/create)."},
                    "note": {"type": "string", "description": "Kræves for progress. Hvad blev gjort."},
                    "name": {"type": "string", "description": "Kræves for create."},
                    "description": {"type": "string"},
                    "why": {"type": "string", "description": "Hvorfor projektet betyder noget."},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "autonomy_level": {"type": "string", "enum": ["suggest", "act", "own"]},
                    "status": {"type": "string", "description": "Filter for list: active|paused|completed|abandoned."},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "creative_project",
            "description": (
                "Dine kreative projekter. action=progress skriver en "
                "fremdriftsnote; action=list viser projekterne med deres id."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": list(_CREATIVE_ACTIONS)},
                    "project_id": {"type": "string", "description": "Kræves for progress (fra list)."},
                    "note": {"type": "string", "description": "Kræves for progress."},
                    "status": {"type": "string", "description": "Filter for list: dreaming|active|paused|completed|abandoned."},
                },
                "required": ["action"],
            },
        },
    },
]

PROJECT_PROGRESS_TOOL_HANDLERS: dict[str, Any] = {
    "sustained_project": _exec_sustained_project,
    "creative_project": _exec_creative_project,
}
