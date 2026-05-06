import time
from pathlib import Path

from core.services import anthropic_identity as ai


def test_build_prefix_with_all_files(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "SOUL.md").write_text("I am Jarvis.")
    (ws / "IDENTITY.md").write_text("Identity facts.")
    (ws / "USER.md").write_text("Bjorn lives in Svendborg.")
    (ws / "STANDING_ORDERS.md").write_text("Be honest.")
    out = ai.build_identity_prefix(ws)
    assert "## SOUL.md" in out
    assert "I am Jarvis." in out
    assert "## IDENTITY.md" in out
    assert "## USER.md" in out
    assert "Bjorn lives in Svendborg." in out
    assert "## STANDING_ORDERS.md" in out


def test_build_prefix_with_missing_files(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "SOUL.md").write_text("Soul.")
    out = ai.build_identity_prefix(ws)
    assert "## SOUL.md" in out
    assert "## IDENTITY.md" not in out


def test_build_prefix_empty_workspace(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    out = ai.build_identity_prefix(ws)
    assert out == ""


def test_build_prefix_caches_until_mtime_changes(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "SOUL.md").write_text("v1")
    a = ai.build_identity_prefix(ws)
    b = ai.build_identity_prefix(ws)
    assert a == b
    time.sleep(0.01)
    (ws / "SOUL.md").write_text("v2")
    c = ai.build_identity_prefix(ws)
    assert "v2" in c
