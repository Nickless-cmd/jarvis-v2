from __future__ import annotations

from pathlib import Path

from core.identity.workspace_bootstrap import ensure_default_workspace

CAPABILITY_FILES = {
    "tools": "TOOLS.md",
    "skills": "SKILLS.md",
}


def load_workspace_capabilities(name: str = "default") -> dict[str, object]:
    workspace_dir = ensure_default_workspace(name=name)
    return {
        "workspace": str(workspace_dir),
        "name": name,
        "tools": _document_summary(workspace_dir / CAPABILITY_FILES["tools"]),
        "skills": _document_summary(workspace_dir / CAPABILITY_FILES["skills"]),
    }


def _document_summary(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "title": None,
            "has_text": False,
            "headings": [],
        }

    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines()]
    headings = [line.lstrip("#").strip() for line in lines if line.startswith("#")]
    content_lines = [line for line in lines if line and not line.startswith("#")]

    return {
        "path": str(path),
        "exists": True,
        "title": headings[0] if headings else None,
        "has_text": bool(content_lines),
        "headings": headings[1:8],
    }
