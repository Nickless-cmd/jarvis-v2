"""Select the shared Desk web build and serve its static files with safe caching."""
from __future__ import annotations

import re
from pathlib import Path

from fastapi.staticfiles import StaticFiles


def ui_build_dir(repo_root: Path) -> Path | None:
    preferred = repo_root / "apps" / "jarvis-desk" / "dist-web"
    if preferred.is_dir():
        return preferred
    fallback = repo_root / "apps" / "ui" / "dist"
    return fallback if fallback.is_dir() else None


_HASHED_ASSET = re.compile(r"assets/.+-[A-Za-z0-9_-]{8,}\.[A-Za-z0-9]+\Z")


class DeskUiFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["cache-control"] = (
            "public, max-age=31536000, immutable"
            if _HASHED_ASSET.fullmatch(path) else "no-cache"
        )
        return response
