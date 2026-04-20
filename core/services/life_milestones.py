"""Life milestones — identity-defining moments surfaced in the prompt.

Reads MILESTONES.md from the runtime workspace. Jarvis can append to it
himself (via workspace_write tool) when something leaves a lasting mark.
Also reads MANIFEST.md as a special "first principles" entry.
"""
from __future__ import annotations

from pathlib import Path

from core.runtime.config import JARVIS_HOME

_WORKSPACE = Path(JARVIS_HOME) / "workspaces" / "default"
_MILESTONES_FILE = _WORKSPACE / "MILESTONES.md"
_MANIFEST_FILE = _WORKSPACE / "MANIFEST.md"
_MAX_CHARS = 1200


def get_milestones_for_prompt(max_chars: int = _MAX_CHARS) -> str | None:
    """Return a formatted milestones block for prompt injection, or None."""
    parts: list[str] = []

    if _MILESTONES_FILE.exists():
        try:
            text = _MILESTONES_FILE.read_text(encoding="utf-8", errors="replace").strip()
            if text:
                parts.append(text)
        except Exception:
            pass

    if not parts:
        return None

    combined = "\n\n".join(parts).strip()
    if len(combined) > max_chars:
        combined = combined[:max_chars - 1].rstrip() + "…"
    return combined


def get_manifest_excerpt(max_chars: int = 600) -> str | None:
    """Return first ~600 chars of MANIFEST.md as a first-principles reminder."""
    if not _MANIFEST_FILE.exists():
        return None
    try:
        text = _MANIFEST_FILE.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            return None
        if len(text) > max_chars:
            text = text[:max_chars].rstrip() + "…"
        return text
    except Exception:
        return None


def build_life_history_prompt_section() -> str | None:
    """Combine milestones + manifest excerpt into a prompt section."""
    milestones = get_milestones_for_prompt()
    if not milestones:
        return None
    return milestones


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
