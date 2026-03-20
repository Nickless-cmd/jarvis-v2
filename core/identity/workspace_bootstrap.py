from __future__ import annotations

from pathlib import Path
import shutil

from core.runtime.config import WORKSPACES_DIR

TEMPLATE_DIR = Path("workspace/templates")


def ensure_default_workspace(name: str = "default") -> Path:
    workspace_dir = Path(WORKSPACES_DIR) / name
    workspace_dir.mkdir(parents=True, exist_ok=True)

    if TEMPLATE_DIR.exists():
        for src in TEMPLATE_DIR.iterdir():
            if not src.is_file():
                continue
            dest = workspace_dir / src.name
            if not dest.exists():
                shutil.copy2(src, dest)

    return workspace_dir
