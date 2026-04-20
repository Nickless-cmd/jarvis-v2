"""Consent Registry — user preferences and boundaries that persist across sessions.

When the user says "don't do X", "always Y", "stop Z", these are captured here.
Unlike SOUL.md (hardcoded ethics), consent entries are emergent from conversation.
They are injected as critical constraints in the visible prompt.

Persisted to CONSENT_REGISTRY.json in the default workspace runtime dir.
"""
from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.config import JARVIS_HOME

_PERSIST_FILE = Path(JARVIS_HOME) / "workspaces" / "default" / "CONSENT_REGISTRY.json"
_LOCK = threading.Lock()
_LOADED = False
_ENTRIES: list[dict[str, object]] = []
_MAX_ENTRIES = 50


def _ensure_loaded() -> None:
    global _LOADED
    if _LOADED:
        return
    with _LOCK:
        if _LOADED:
            return
        _load()
        _LOADED = True


def _load() -> None:
    global _ENTRIES
    try:
        if _PERSIST_FILE.exists():
            data = json.loads(_PERSIST_FILE.read_text(encoding="utf-8"))
            _ENTRIES[:] = list(data.get("entries") or [])
    except Exception:
        pass


def _save() -> None:
    try:
        _PERSIST_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PERSIST_FILE.write_text(
            json.dumps({"entries": _ENTRIES[-_MAX_ENTRIES:]}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def register_consent(
    *,
    kind: str,
    statement: str,
    source_session_id: str = "",
    confidence: float = 0.8,
) -> dict[str, object]:
    """Register a user preference or boundary.

    kind: "avoid" | "prefer" | "boundary"
    statement: what the user expressed (max 200 chars)
    """
    _ensure_loaded()
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    entry: dict[str, object] = {
        "consent_id": f"cns-{uuid4().hex[:8]}",
        "kind": kind,
        "statement": statement[:200].strip(),
        "source_session_id": source_session_id,
        "confidence": round(min(1.0, max(0.1, confidence)), 2),
        "active": True,
        "registered_at": now,
        "updated_at": now,
    }
    with _LOCK:
        _ENTRIES.append(entry)
        _save()
    event_bus.publish(
        "cognitive_state.consent_registered",
        {"kind": kind, "statement": entry["statement"]},
    )
    return entry


def revoke_consent(consent_id: str) -> None:
    """Mark a consent entry as inactive."""
    _ensure_loaded()
    with _LOCK:
        for e in _ENTRIES:
            if e.get("consent_id") == consent_id:
                e["active"] = False
                e["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        _save()


def get_active_consents() -> list[dict[str, object]]:
    _ensure_loaded()
    return [e for e in _ENTRIES if e.get("active")]


def build_consent_prompt_section() -> str | None:
    """Return a prompt section with active consent entries, or None if empty."""
    active = get_active_consents()
    if not active:
        return None
    avoid = [e for e in active if e.get("kind") == "avoid"]
    prefer = [e for e in active if e.get("kind") == "prefer"]
    boundary = [e for e in active if e.get("kind") == "boundary"]
    lines: list[str] = []
    if boundary:
        lines.append("Brugerens grænser (respekter disse ubetinget):")
        for e in boundary[:5]:
            lines.append(f"  - {e['statement']}")
    if avoid:
        lines.append("Brugeren har bedt om at undgå:")
        for e in avoid[:5]:
            lines.append(f"  - {e['statement']}")
    if prefer:
        lines.append("Brugeren foretrækker:")
        for e in prefer[:5]:
            lines.append(f"  - {e['statement']}")
    if not lines:
        return None
    return "\n".join(lines)


def build_consent_registry_surface() -> dict[str, object]:
    active = get_active_consents()
    return {
        "active": bool(active),
        "count": len(active),
        "avoid_count": sum(1 for e in active if e.get("kind") == "avoid"),
        "prefer_count": sum(1 for e in active if e.get("kind") == "prefer"),
        "boundary_count": sum(1 for e in active if e.get("kind") == "boundary"),
        "summary": (
            f"{len(active)} active consent entries"
            if active else "No consent preferences recorded"
        ),
    }
