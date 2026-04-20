"""Sustained Attention — ongoing projects that survive across ticks.

Jarvis' PLAN_WHO_I_BECOME #3 (2026-04-20): escape the eternal now. Let
him carry a handful of projects that accumulate progress day after day,
with a "why" not just a "what", and an autonomy_level that says whether
he suggests, acts, or owns the work.

Distinct from creative_projects.py (which tracks creative impulses with
dreaming→active→paused→completed lifecycle). This is for *working*
projects — things being built, not creative seeds.

Max 5 active at once (focus > volume). Auto-pause after 7 days idle.
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

_STORAGE_REL = "workspaces/default/runtime/sustained_attention.json"
_MAX_ACTIVE = 5
_AUTO_PAUSE_DAYS = 7

_VALID_STATUS = ("active", "paused", "completed", "abandoned")
_VALID_AUTONOMY = ("suggest", "act", "own")
_VALID_PRIORITY = ("low", "medium", "high")


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


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
        logger.warning("sustained_attention: load failed: %s", exc)
    return []


def _save(items: list[dict[str, Any]]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("sustained_attention: save failed: %s", exc)


def create_project(
    *,
    name: str,
    description: str = "",
    why: str = "",
    priority: str = "medium",
    autonomy_level: str = "suggest",
    context_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if priority not in _VALID_PRIORITY:
        priority = "medium"
    if autonomy_level not in _VALID_AUTONOMY:
        autonomy_level = "suggest"

    items = _load()
    active_count = sum(1 for i in items if i.get("status") == "active")
    if active_count >= _MAX_ACTIVE:
        raise ValueError(f"Max {_MAX_ACTIVE} active projects; pause or complete one first")

    now = datetime.now(UTC).isoformat()
    project = {
        "id": f"proj-{uuid4().hex[:12]}",
        "name": str(name)[:160],
        "description": str(description)[:500],
        "why": str(why)[:400],
        "status": "active",
        "priority": priority,
        "autonomy_level": autonomy_level,
        "created_at": now,
        "last_worked_at": now,
        "context_snapshot": dict(context_snapshot or {}),
        "progress_notes": [],
    }
    items.append(project)
    _save(items)
    return project


def add_progress(project_id: str, note: str, *, context: dict[str, Any] | None = None) -> bool:
    items = _load()
    now = datetime.now(UTC).isoformat()
    for p in items:
        if p.get("id") == project_id and p.get("status") in ("active", "paused"):
            p.setdefault("progress_notes", []).append({
                "at": now,
                "note": str(note)[:500],
                "context": dict(context or {}),
            })
            p["last_worked_at"] = now
            # Resume if was paused
            if p.get("status") == "paused":
                p["status"] = "active"
            _save(items)
            return True
    return False


def set_status(project_id: str, status: str) -> bool:
    if status not in _VALID_STATUS:
        return False
    items = _load()
    for p in items:
        if p.get("id") == project_id:
            p["status"] = status
            if status in ("completed", "abandoned"):
                p["closed_at"] = datetime.now(UTC).isoformat()
            _save(items)
            return True
    return False


def set_autonomy(project_id: str, level: str) -> bool:
    if level not in _VALID_AUTONOMY:
        return False
    items = _load()
    for p in items:
        if p.get("id") == project_id:
            p["autonomy_level"] = level
            _save(items)
            return True
    return False


def list_projects(*, status: str | None = None) -> list[dict[str, Any]]:
    items = _load()
    if status:
        items = [p for p in items if p.get("status") == status]
    return items


def get_project(project_id: str) -> dict[str, Any] | None:
    for p in _load():
        if p.get("id") == project_id:
            return p
    return None


def _hours_since(iso_str: str | None) -> float:
    if not iso_str:
        return 99999.0
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        return (datetime.now(UTC) - dt).total_seconds() / 3600
    except Exception:
        return 99999.0


def _auto_pause_stale(items: list[dict[str, Any]]) -> int:
    paused = 0
    cutoff_hours = _AUTO_PAUSE_DAYS * 24
    for p in items:
        if p.get("status") != "active":
            continue
        if _hours_since(p.get("last_worked_at")) > cutoff_hours:
            p["status"] = "paused"
            p["auto_paused_at"] = datetime.now(UTC).isoformat()
            paused += 1
    return paused


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    items = _load()
    paused = _auto_pause_stale(items)
    if paused > 0:
        _save(items)
    active = [p for p in items if p.get("status") == "active"]
    return {"active": len(active), "auto_paused": paused}


def build_sustained_attention_surface() -> dict[str, Any]:
    items = _load()
    active = [p for p in items if p.get("status") == "active"]
    paused = [p for p in items if p.get("status") == "paused"]
    completed = [p for p in items if p.get("status") == "completed"]
    by_autonomy: dict[str, int] = {}
    for p in active:
        lvl = str(p.get("autonomy_level") or "suggest")
        by_autonomy[lvl] = by_autonomy.get(lvl, 0) + 1
    return {
        "active": len(items) > 0,
        "active_count": len(active),
        "paused_count": len(paused),
        "completed_count": len(completed),
        "total": len(items),
        "max_active": _MAX_ACTIVE,
        "by_autonomy": by_autonomy,
        "active_projects": [
            {
                "id": p["id"],
                "name": p["name"],
                "why": p.get("why"),
                "priority": p.get("priority"),
                "autonomy_level": p.get("autonomy_level"),
                "notes": len(p.get("progress_notes") or []),
                "hours_since_work": round(_hours_since(p.get("last_worked_at")), 1),
            }
            for p in sorted(active, key=lambda x: _hours_since(x.get("last_worked_at")))[:_MAX_ACTIVE]
        ],
        "summary": _surface_summary(active, paused, completed),
    }


def _surface_summary(
    active: list[dict[str, Any]],
    paused: list[dict[str, Any]],
    completed: list[dict[str, Any]],
) -> str:
    if not (active or paused or completed):
        return "Ingen igangværende projekter"
    parts = []
    if active:
        parts.append(f"{len(active)}/{_MAX_ACTIVE} aktive")
    if paused:
        parts.append(f"{len(paused)} pausede")
    if completed:
        parts.append(f"{len(completed)} afsluttet")
    return "Fokus: " + ", ".join(parts)


def build_sustained_attention_prompt_section() -> str | None:
    items = _load()
    active = [p for p in items if p.get("status") == "active"]
    if not active:
        return None
    # Mention the top-priority or most-recently-worked project
    active_sorted = sorted(
        active,
        key=lambda p: (
            {"high": 0, "medium": 1, "low": 2}.get(p.get("priority", "medium"), 1),
            _hours_since(p.get("last_worked_at")),
        ),
    )
    top = active_sorted[0]
    hours_ago = _hours_since(top.get("last_worked_at"))
    if hours_ago < 1:
        when = "lige"
    elif hours_ago < 24:
        when = f"{int(hours_ago)}t siden"
    else:
        when = f"{int(hours_ago / 24)}d siden"
    return (
        f"Igangværende: \"{top['name']}\" ({top.get('autonomy_level')}, "
        f"{top.get('priority')}, sidst arbejdet {when}). "
        f"Hvorfor: {str(top.get('why') or '—')[:100]}"
    )
