from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from core.runtime.config import WORKSPACES_DIR, WORKSPACE_TEMPLATES_DIR

TEMPLATE_DIR = WORKSPACE_TEMPLATES_DIR
REQUIRED_WORKSPACE_FILES = (
    "SOUL.md",
    "IDENTITY.md",
    "STANDING_ORDERS.md",
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
    "INNER_VOICE.md",
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


def ensure_layered_memory_dirs(name: str = "default") -> dict[str, Path]:
    workspace_dir = Path(WORKSPACES_DIR) / name
    workspace_dir.mkdir(parents=True, exist_ok=True)
    memory_dir = workspace_dir / "memory"
    daily_dir = memory_dir / "daily"
    curated_dir = memory_dir / "curated"
    daily_dir.mkdir(parents=True, exist_ok=True)
    curated_dir.mkdir(parents=True, exist_ok=True)
    return {
        "workspace_dir": workspace_dir,
        "memory_dir": memory_dir,
        "daily_dir": daily_dir,
        "curated_dir": curated_dir,
    }


def workspace_memory_paths(name: str = "default") -> dict[str, Path]:
    dirs = ensure_layered_memory_dirs(name=name)
    workspace_dir = dirs["workspace_dir"]
    today = datetime.now(UTC).date().isoformat()
    return {
        "workspace_dir": workspace_dir,
        "user": workspace_dir / "USER.md",
        "curated_memory": workspace_dir / "MEMORY.md",
        "daily_memory": dirs["daily_dir"] / f"{today}.md",
        "memory_dir": dirs["memory_dir"],
        "daily_dir": dirs["daily_dir"],
        "curated_dir": dirs["curated_dir"],
    }


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

    ensure_layered_memory_dirs(name=name)

    return WorkspaceBootstrapResult(
        workspace_dir=workspace_dir,
        created_files=created_files,
        existing_files=existing_files,
    )
