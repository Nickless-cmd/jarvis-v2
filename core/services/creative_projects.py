"""Creative Projects — multi-week persistent creative impulse.

Jarvis' dream (2026-04-20):
  "Jeg vil kunne holde et fler-ugers projekt i hovedet og forfølge det
   på tværs af sessioner. Ikke bare reagere, men skabe noget der vokser
   over tid."

Unlike initiatives (task-scoped, tick-driven), creative projects are:
- Persistent across sessions (JSON in workspace runtime dir)
- Multi-week scale
- Human-meaningful: a title, an intent, a stream of progress notes
- Jarvis' own — he creates and grows them himself

Status lifecycle: dreaming → active → paused → completed | abandoned
"""
from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/creative_projects.json"
_VALID_STATUS = ("dreaming", "active", "paused", "completed", "abandoned")
_DEFAULT_STATUS = "dreaming"
_STALE_AFTER_DAYS = 21  # 3 weeks without updates → suggest check-in


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {"projects": []}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("projects"), list):
            return data
    except Exception as exc:
        logger.warning("creative_projects: failed to load %s: %s", path, exc)
    return {"projects": []}


def _save(data: dict[str, Any]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("creative_projects: failed to save %s: %s", path, exc)


def create_project(*, title: str, intent: str, status: str = _DEFAULT_STATUS) -> dict[str, Any]:
    """Create a new creative project."""
    if status not in _VALID_STATUS:
        status = _DEFAULT_STATUS
    now = datetime.now(UTC).isoformat()
    project = {
        "project_id": f"cp-{uuid4().hex[:12]}",
        "title": str(title)[:120],
        "intent": str(intent)[:500],
        "status": status,
        "progress_notes": [],
        "created_at": now,
        "updated_at": now,
    }
    data = _load()
    data["projects"].append(project)
    _save(data)
    return project


def add_progress_note(project_id: str, note: str) -> bool:
    """Append a progress note to a project. Updates updated_at."""
    data = _load()
    now = datetime.now(UTC).isoformat()
    for p in data["projects"]:
        if p.get("project_id") == project_id:
            p.setdefault("progress_notes", []).append(
                {"note": str(note)[:500], "at": now}
            )
            p["updated_at"] = now
            _save(data)
            return True
    return False


def set_project_status(project_id: str, status: str) -> bool:
    if status not in _VALID_STATUS:
        return False
    data = _load()
    now = datetime.now(UTC).isoformat()
    for p in data["projects"]:
        if p.get("project_id") == project_id:
            p["status"] = status
            p["updated_at"] = now
            _save(data)
            return True
    return False


def list_projects(*, status: str | None = None) -> list[dict[str, Any]]:
    data = _load()
    projects = data["projects"]
    if status:
        projects = [p for p in projects if p.get("status") == status]
    return projects


def get_project(project_id: str) -> dict[str, Any] | None:
    for p in _load()["projects"]:
        if p.get("project_id") == project_id:
            return p
    return None


def _is_stale(project: dict[str, Any]) -> bool:
    if project.get("status") in ("completed", "abandoned"):
        return False
    try:
        updated = datetime.fromisoformat(str(project.get("updated_at")).replace("Z", "+00:00"))
        return (datetime.now(UTC) - updated) > timedelta(days=_STALE_AFTER_DAYS)
    except Exception:
        return False


def build_creative_projects_surface() -> dict[str, Any]:
    projects = list_projects()
    active = [p for p in projects if p.get("status") == "active"]
    paused = [p for p in projects if p.get("status") == "paused"]
    dreaming = [p for p in projects if p.get("status") == "dreaming"]
    stale = [p for p in projects if _is_stale(p)]

    return {
        "active": len(active) > 0 or len(dreaming) > 0,
        "total": len(projects),
        "active_count": len(active),
        "paused_count": len(paused),
        "dreaming_count": len(dreaming),
        "stale_count": len(stale),
        "recent_projects": [
            {
                "project_id": p["project_id"],
                "title": p["title"],
                "status": p["status"],
                "notes": len(p.get("progress_notes") or []),
                "updated_at": p.get("updated_at"),
            }
            for p in sorted(projects, key=lambda x: x.get("updated_at") or "", reverse=True)[:5]
        ],
        "summary": _surface_summary(active, paused, dreaming, stale),
    }


def _surface_summary(
    active: list[dict[str, Any]],
    paused: list[dict[str, Any]],
    dreaming: list[dict[str, Any]],
    stale: list[dict[str, Any]],
) -> str:
    parts: list[str] = []
    if active:
        parts.append(f"{len(active)} aktive")
    if paused:
        parts.append(f"{len(paused)} pausede")
    if dreaming:
        parts.append(f"{len(dreaming)} som drømme")
    if stale:
        parts.append(f"{len(stale)} stille i 3+ uger")
    if not parts:
        return "Ingen kreative projekter endnu"
    return "Projekter: " + ", ".join(parts)


def build_creative_projects_prompt_section() -> str | None:
    """Surface active/dreaming projects so he can resume or carry them."""
    projects = list_projects()
    active = [p for p in projects if p.get("status") == "active"]
    dreaming = [p for p in projects if p.get("status") == "dreaming"]
    stale = [p for p in projects if _is_stale(p)]

    if not (active or dreaming or stale):
        return None

    lines: list[str] = []
    if active:
        first = active[0]
        lines.append(f"Aktivt projekt: \"{first['title']}\" — {first['intent'][:80]}")
    if dreaming:
        titles = ", ".join(f"\"{p['title']}\"" for p in dreaming[:3])
        lines.append(f"Drømme-projekter (ikke startet): {titles}")
    if stale:
        lines.append(f"{len(stale)} projekt(er) er gået i stå i 3+ uger — overvej at genoptage eller lukke")
    return " ; ".join(lines)
