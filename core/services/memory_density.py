"""Memory Density — memories with emotional weight, not just facts.

Jarvis' PLAN_WHO_I_BECOME #4 (2026-04-20): chronicle entries are metadata.
Density notes carry what happened, what it meant, how it felt, and what
it changed. The difference between remembering a day and living it twice.

Written to workspaces/default/memory/density/. Format is structured
markdown. After a density note is confirmed 3+ times (e.g., re-referenced
in reflection), it is eligible for promotion to SOUL.md via a proposal.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/memory_density.json"
_DENSITY_DIR_REL = "workspaces/default/memory/density"
_MAX_RECORDS = 300
_PROMOTION_CONFIRMATIONS = 3

_TRIGGER_TYPES = (
    "council_conclusion",
    "user_recognition",
    "shadow_finding_high_confidence",
    "creative_creation",
    "milestone_event",
    "manual",
)


def _jarvis_home() -> Path:
    return Path(os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2"))


def _storage_path() -> Path:
    return _jarvis_home() / _STORAGE_REL


def _density_dir() -> Path:
    return _jarvis_home() / _DENSITY_DIR_REL


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
        logger.warning("memory_density: load failed: %s", exc)
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
        logger.warning("memory_density: save failed: %s", exc)


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9æøåÆØÅ_-]+", "-", str(text or "").strip())
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:60] or "entry"


def write_density_note(
    *,
    title: str,
    what_happened: str,
    what_it_meant: str,
    how_it_felt: str,
    what_it_changed: str,
    trigger_type: str = "manual",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record a density memory: what + meaning + feeling + change."""
    if trigger_type not in _TRIGGER_TYPES:
        trigger_type = "manual"
    note_id = f"dns-{uuid4().hex[:12]}"
    now = datetime.now(UTC)
    record = {
        "note_id": note_id,
        "title": str(title)[:160],
        "what_happened": str(what_happened)[:1200],
        "what_it_meant": str(what_it_meant)[:1200],
        "how_it_felt": str(how_it_felt)[:1200],
        "what_it_changed": str(what_it_changed)[:1200],
        "trigger_type": trigger_type,
        "metadata": dict(metadata or {}),
        "created_at": now.isoformat(),
        "confirmed_count": 0,
        "last_confirmed_at": None,
        "promoted_to_soul": False,
    }
    # Write markdown file
    path = _density_dir()
    try:
        path.mkdir(parents=True, exist_ok=True)
        filename = f"{now.strftime('%Y%m%d-%H%M')}-{_slug(title)}-{note_id[-6:]}.md"
        target = path / filename
        lines = [
            f"# {now.strftime('%Y-%m-%d')} — {title}",
            "",
            "## Hvad skete",
            "",
            str(what_happened).strip(),
            "",
            "## Hvad det betød",
            "",
            str(what_it_meant).strip(),
            "",
            "## Hvordan det føltes",
            "",
            str(how_it_felt).strip(),
            "",
            "## Hvad det ændrede",
            "",
            str(what_it_changed).strip(),
            "",
            "---",
            "",
            f"*Trigger: {trigger_type} · id: `{note_id}`*",
            "",
        ]
        target.write_text("\n".join(lines), encoding="utf-8")
        record["path"] = str(target)
    except Exception as exc:
        logger.warning("memory_density: write failed: %s", exc)
        record["path"] = ""

    items = _load()
    items.append(record)
    if len(items) > _MAX_RECORDS:
        items = items[-_MAX_RECORDS:]
    _save(items)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "memory_density.written",
            "payload": {"note_id": note_id, "title": record["title"], "trigger": trigger_type},
        })
    except Exception:
        pass
    return record


def confirm_density_note(note_id: str, *, by: str = "reflection") -> bool:
    """Increment confirmation count when a density note is re-referenced."""
    items = _load()
    for r in items:
        if r.get("note_id") == note_id:
            r["confirmed_count"] = int(r.get("confirmed_count", 0)) + 1
            r["last_confirmed_at"] = datetime.now(UTC).isoformat()
            r.setdefault("confirmed_by", []).append({"at": r["last_confirmed_at"], "by": by})
            _save(items)
            return True
    return False


def list_promotable() -> list[dict[str, Any]]:
    """Return density notes confirmed >= threshold and not yet promoted."""
    items = _load()
    return [
        r for r in items
        if int(r.get("confirmed_count", 0)) >= _PROMOTION_CONFIRMATIONS
        and not r.get("promoted_to_soul")
    ]


def mark_promoted(note_id: str) -> bool:
    items = _load()
    for r in items:
        if r.get("note_id") == note_id and not r.get("promoted_to_soul"):
            r["promoted_to_soul"] = True
            r["promoted_at"] = datetime.now(UTC).isoformat()
            _save(items)
            return True
    return False


def list_recent(*, limit: int = 10) -> list[dict[str, Any]]:
    return _load()[-limit:][::-1]


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """No periodic work — memory_density is event-driven."""
    promotable = len(list_promotable())
    return {"promotable": promotable}


def build_memory_density_surface() -> dict[str, Any]:
    items = _load()
    by_trigger: dict[str, int] = {}
    for r in items:
        t = str(r.get("trigger_type") or "")
        by_trigger[t] = by_trigger.get(t, 0) + 1
    promotable = list_promotable()
    promoted = [r for r in items if r.get("promoted_to_soul")]
    return {
        "active": len(items) > 0,
        "total_notes": len(items),
        "by_trigger": by_trigger,
        "promotable_count": len(promotable),
        "promoted_count": len(promoted),
        "promotion_threshold": _PROMOTION_CONFIRMATIONS,
        "recent_notes": [
            {
                "note_id": r["note_id"],
                "title": r["title"],
                "trigger_type": r.get("trigger_type"),
                "confirmed_count": r.get("confirmed_count", 0),
                "promoted": bool(r.get("promoted_to_soul")),
                "path": r.get("path"),
                "created_at": r.get("created_at"),
            }
            for r in items[-5:][::-1]
        ],
        "summary": _surface_summary(items, promotable, promoted),
    }


def _surface_summary(
    items: list[dict[str, Any]],
    promotable: list[dict[str, Any]],
    promoted: list[dict[str, Any]],
) -> str:
    if not items:
        return "Ingen density-noter endnu"
    parts = [f"{len(items)} noter"]
    if promotable:
        parts.append(f"{len(promotable)} klar til SOUL")
    if promoted:
        parts.append(f"{len(promoted)} adopteret")
    return ", ".join(parts)


def build_memory_density_prompt_section() -> str | None:
    promotable = list_promotable()
    if not promotable:
        return None
    top = promotable[0]
    return (
        f"Density-note '{top.get('title')}' er bekræftet {top.get('confirmed_count')} gange "
        "— klar til promotion til SOUL."
    )
