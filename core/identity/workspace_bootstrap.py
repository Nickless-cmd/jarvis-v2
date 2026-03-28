from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from core.runtime.config import WORKSPACES_DIR

TEMPLATE_DIR = Path("workspace/templates")
REQUIRED_WORKSPACE_FILES = (
    "SOUL.md",
    "IDENTITY.md",
    "USER.md",
    "TOOLS.md",
    "SKILLS.md",
    "MEMORY.md",
    "HEARTBEAT.md",
)
OPTIONAL_WORKSPACE_FILES = (
    "VISIBLE_LOCAL_MODEL.md",
    "VISIBLE_CHAT_RULES.md",
    "VISIBLE_RELEVANCE.md",
    "VISIBLE_MEMORY_SELECTION.md",
)


@dataclass(slots=True)
class WorkspaceBootstrapResult:
    workspace_dir: Path
    created_files: list[str]
    existing_files: list[str]

    def summary(self) -> dict[str, object]:
        return {
            "workspace": str(self.workspace_dir),
            "created_files": self.created_files,
            "existing_files": self.existing_files,
        }


def ensure_default_workspace(name: str = "default") -> Path:
    return bootstrap_workspace(name=name).workspace_dir


def bootstrap_workspace(name: str = "default") -> WorkspaceBootstrapResult:
    workspace_dir = Path(WORKSPACES_DIR) / name
    workspace_dir.mkdir(parents=True, exist_ok=True)

    created_files: list[str] = []
    existing_files: list[str] = []

    for filename in REQUIRED_WORKSPACE_FILES:
        src = TEMPLATE_DIR / filename
        if not src.exists():
            raise FileNotFoundError(f"Missing required workspace template: {src}")

        dest = workspace_dir / filename
        if dest.exists():
            existing_files.append(filename)
            continue

        shutil.copy2(src, dest)
        created_files.append(filename)

    for filename in OPTIONAL_WORKSPACE_FILES:
        src = TEMPLATE_DIR / filename
        if not src.exists():
            continue

        dest = workspace_dir / filename
        if dest.exists():
            existing_files.append(filename)
            continue

        shutil.copy2(src, dest)
        created_files.append(filename)

    return WorkspaceBootstrapResult(
        workspace_dir=workspace_dir,
        created_files=created_files,
        existing_files=existing_files,
    )
