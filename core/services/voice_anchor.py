"""Voice anchor — combined static seed + auto-refreshed external exemplars.

Pure file read. No LLM, no DB, no side effects. Returns a markdown blob
suitable for inclusion at the top of an LLM prompt to anchor Jarvis' voice.

Two files in workspace root:
- VOICE.md         — static seed authored once. Direction: tone, rhythm,
                     vocabulary, what to avoid. Not auto-rewritten.
- VOICE_RECENT.md  — auto-managed by voice_curator. 3-5 exemplar blocks
                     from external output (chat / chronicle / prior journals).
"""

from __future__ import annotations

from pathlib import Path

from core.identity.workspace_bootstrap import ensure_default_workspace


def read_voice_anchor() -> str:
    """Return concatenated VOICE.md + VOICE_RECENT.md, or empty string.

    Each section gets a markdown header so the LLM can tell them apart.
    Missing files are silently skipped (so this works on fresh installs).
    """
    workspace = ensure_default_workspace()
    parts: list[str] = []

    static_path = workspace / "VOICE.md"
    if static_path.exists():
        body = static_path.read_text(encoding="utf-8", errors="replace").strip()
        if body:
            parts.append("## VOICE.md (static seed)\n\n" + body)

    recent_path = workspace / "VOICE_RECENT.md"
    if recent_path.exists():
        body = recent_path.read_text(encoding="utf-8", errors="replace").strip()
        if body:
            parts.append("## VOICE_RECENT.md (recent exemplars)\n\n" + body)

    return "\n\n".join(parts)
