from __future__ import annotations

from pathlib import Path

from core.identity.workspace_bootstrap import ensure_default_workspace

CAPABILITY_FILES = {
    "tools": "TOOLS.md",
    "skills": "SKILLS.md",
}


def load_workspace_capabilities(name: str = "default") -> dict[str, object]:
    workspace_dir = ensure_default_workspace(name=name)
    tools = _document_summary(workspace_dir / CAPABILITY_FILES["tools"], kind="tool")
    skills = _document_summary(workspace_dir / CAPABILITY_FILES["skills"], kind="skill")
    return {
        "workspace": str(workspace_dir),
        "name": name,
        "tools": tools,
        "skills": skills,
        "declared_capabilities": [
            *tools["declared_capabilities"],
            *skills["declared_capabilities"],
        ],
    }


def _document_summary(path: Path, *, kind: str) -> dict[str, object]:
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "title": None,
            "has_text": False,
            "headings": [],
            "declared_capabilities": [],
        }

    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines()]
    headings = [line.lstrip("#").strip() for line in lines if line.startswith("#")]
    content_lines = [line for line in lines if line and not line.startswith("#")]
    declared_capabilities = [
        {
            "kind": kind,
            "name": heading,
            "source_doc": path.name,
            "runnable": False,
            "execution_mode": "declared-only",
            "status": "declared-only",
        }
        for heading in headings[1:8]
        if heading
    ]

    return {
        "path": str(path),
        "exists": True,
        "title": headings[0] if headings else None,
        "has_text": bool(content_lines),
        "headings": headings[1:8],
        "declared_capabilities": declared_capabilities,
    }
