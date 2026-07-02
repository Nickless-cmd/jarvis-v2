"""Life milestones — identity-defining moments surfaced in the prompt.

Reads MILESTONES.md from the runtime workspace. Jarvis can append to it
himself (via workspace_write tool) when something leaves a lasting mark.
Also reads MANIFEST.md as a special "first principles" entry.
"""
from __future__ import annotations

from pathlib import Path

from core.runtime.workspace_paths import shared_dir
from core.services.text_clip import clip_text

_MAX_CHARS = 1200


def _milestones_file() -> Path:
    return shared_dir() / "MILESTONES.md"


def _manifest_file() -> Path:
    return shared_dir() / "MANIFEST.md"


def get_milestones_for_prompt(max_chars: int = _MAX_CHARS) -> str | None:
    """Return a formatted milestones block for prompt injection, or None."""
    parts: list[str] = []

    p = _milestones_file()
    if p.exists():
        try:
            text = p.read_text(encoding="utf-8", errors="replace").strip()
            if text:
                parts.append(text)
        except Exception:
            pass

    if not parts:
        return None

    combined = "\n\n".join(parts).strip()
    if len(combined) > max_chars:
        combined = clip_text(combined, limit=max_chars)
    return combined


def get_manifest_excerpt(max_chars: int = 600) -> str | None:
    """Return first ~600 chars of MANIFEST.md as a first-principles reminder."""
    p = _manifest_file()
    if not p.exists():
        return None
    try:
        text = p.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            return None
        if len(text) > max_chars:
            text = clip_text(text, limit=max_chars)
        return text
    except Exception:
        return None


def build_life_history_prompt_section() -> str | None:
    """Combine milestones + manifest excerpt into a prompt section."""
    milestones = get_milestones_for_prompt()
    if not milestones:
        return None
    return milestones


def append_milestone(text: str) -> bool:
    """Append a new milestone entry to MILESTONES.md. Returns True on success."""
    if not text or not text.strip():
        return False
    try:
        from datetime import UTC, datetime
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        entry = f"\n## {date_str}\n{text.strip()}\n"
        p = _milestones_file()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(entry)
        return True
    except Exception:
        return False


def build_life_milestones_surface() -> dict[str, object]:
    milestones = get_milestones_for_prompt()
    manifest = get_manifest_excerpt()
    return {
        "active": bool(milestones),
        "has_milestones": bool(milestones),
        "has_manifest": bool(manifest),
        "milestones_chars": len(milestones) if milestones else 0,
        "summary": (
            f"Milestones present ({len(milestones or '')} chars), manifest {'present' if manifest else 'absent'}"
            if milestones else "No milestones yet"
        ),
    }


def _emit_life_milestones_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a scoped event for cartographer observability.

    State-mutation points in this module can call this with a transition
    kind ("created", "updated", "transitioned", etc.). Defensive — never
    blocks the caller. Added 2026-05-13 (top-18 cartographer pass).
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(f"life_milestones.{kind}", payload or {})
    except Exception:
        pass

