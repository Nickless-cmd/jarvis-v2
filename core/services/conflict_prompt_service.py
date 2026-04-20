"""Conflict memory prompt service — surfaces recent conversation conflicts in the prompt.

Reads from the cognitive_conflict_memory DB table (written by relationship_texture.py).
Injected as a background section so Jarvis knows what patterns lead to conflict.
"""
from __future__ import annotations

from core.runtime.db import list_cognitive_conflict_memories


def build_conflict_memory_prompt_section(limit: int = 4) -> str | None:
    """Return a prompt section with recent conflict lessons, or None if empty."""
    try:
        conflicts = list_cognitive_conflict_memories(limit=limit)
    except Exception:
        return None
    if not conflicts:
        return None

    lines: list[str] = []
    for c in conflicts:
        topic = str(c.get("topic") or "").strip()[:80]
        lesson = str(c.get("lesson") or "").strip()[:120]
        resolution = str(c.get("resolution") or "").strip()
        if not lesson:
            continue
        tag = "→ bruger havde ret" if resolution == "user_correct" else "→ Jarvis fastholdt"
        line = f"[{topic}] {lesson} {tag}" if topic else f"{lesson} {tag}"
        lines.append(line.strip())

    if not lines:
        return None

    return "Konflikthukommelse (mønstre der har ført til friktion):\n" + "\n".join(f"- {l}" for l in lines)


def build_conflict_memory_surface(limit: int = 10) -> dict[str, object]:
    try:
        conflicts = list_cognitive_conflict_memories(limit=limit)
    except Exception:
        conflicts = []
    user_correct = sum(1 for c in conflicts if c.get("resolution") == "user_correct")
    return {
        "active": bool(conflicts),
        "count": len(conflicts),
        "user_correct_count": user_correct,
        "summary": (
            f"{len(conflicts)} conflicts recorded, {user_correct} where user was right"
            if conflicts else "No conflict history"
        ),
    }
