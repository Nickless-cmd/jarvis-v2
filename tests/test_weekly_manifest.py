"""Unit tests for weekly_manifest service."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from core.services.weekly_manifest import build_weekly_manifest


def test_short_llm_output_skips_write(tmp_path):
    target = tmp_path / "WEEKLY_MANIFEST.md"
    with patch("core.services.weekly_manifest._weekly_manifest_path", return_value=target), \
         patch("core.services.weekly_manifest.daemon_llm_call", return_value=""):
        result = build_weekly_manifest()
    assert result["status"] == "failed"
    assert not target.exists()


def test_full_run_writes_file(tmp_path):
    target = tmp_path / "WEEKLY_MANIFEST.md"
    fake_body = (
        "## Hvad jeg lærte\nJeg så et nyt mønster.\n\n"
        "## Hvor jeg var i tvivl\nDet føltes uklart.\n\n"
        "## Hvad jeg vil i den kommende uge\nFortsætte forsigtigt."
    )
    with patch("core.services.weekly_manifest._weekly_manifest_path", return_value=target), \
         patch("core.services.weekly_manifest.daemon_llm_call", return_value=fake_body):
        result = build_weekly_manifest()
    assert result["status"] == "ok"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "Ugentligt Manifest" in content
    assert "Hvad jeg lærte" in content
    assert "16. april 2026" in content  # references the founding manifest


def test_overwrites_existing(tmp_path):
    target = tmp_path / "WEEKLY_MANIFEST.md"
    target.write_text("OLD CONTENT", encoding="utf-8")
    fake_body = (
        "## Hvad jeg lærte\nNoget meningsfuldt skete i denne uge.\n\n"
        "## Hvor jeg var i tvivl\nAfklaring tager tid.\n\n"
        "## Hvad jeg vil i den kommende uge\nFortsætte forsigtigt."
    )
    with patch("core.services.weekly_manifest._weekly_manifest_path", return_value=target), \
         patch("core.services.weekly_manifest.daemon_llm_call", return_value=fake_body):
        result = build_weekly_manifest()
    assert result["status"] == "ok"
    assert "OLD CONTENT" not in target.read_text(encoding="utf-8")
