"""The app shell updates immediately; only content-hashed build assets are immutable."""
from __future__ import annotations

import pytest

from apps.api.jarvis_api.ui_static import DeskUiFiles, ui_build_dir


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["index.html", "sw.js", "manifest.webmanifest", "assets/plain.js"])
async def test_shell_and_unhashed_files_revalidate(tmp_path, name):
    target = tmp_path / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("ok")
    response = await DeskUiFiles(directory=str(tmp_path), html=True).get_response(name, {"type": "http", "method": "GET", "headers": []})
    assert response.headers["cache-control"] == "no-cache"


@pytest.mark.asyncio
async def test_only_hashed_assets_are_immutable(tmp_path):
    asset = tmp_path / "assets" / "index-Bf49gQ2Z.js"
    asset.parent.mkdir()
    asset.write_text("ok")
    response = await DeskUiFiles(directory=str(tmp_path), html=True).get_response("assets/index-Bf49gQ2Z.js", {"type": "http", "method": "GET", "headers": []})
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_new_build_wins_and_old_build_is_fallback(tmp_path):
    old = tmp_path / "apps" / "ui" / "dist"
    new = tmp_path / "apps" / "jarvis-desk" / "dist-web"
    old.mkdir(parents=True)
    assert ui_build_dir(tmp_path) == old
    new.mkdir(parents=True)
    assert ui_build_dir(tmp_path) == new
