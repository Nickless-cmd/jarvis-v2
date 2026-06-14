"""Tests for memory_resurfacing — §16 encryption-aware MEMORY.md-læsning."""
from __future__ import annotations

import pytest


def test_list_headings_plaintext(tmp_path, monkeypatch) -> None:
    import core.services.memory_resurfacing as mr
    mem = tmp_path / "MEMORY.md"
    mem.write_text("# MEMORY\n\n## Emne A\nindhold\n\n## Emne B\nmere\n", encoding="utf-8")
    monkeypatch.setattr(mr, "_memory_md", lambda: mem)
    headings = mr._list_memory_headings()
    texts = [h for _, h in headings]
    assert "Emne A" in texts and "Emne B" in texts


def test_list_headings_missing_file(tmp_path, monkeypatch) -> None:
    import core.services.memory_resurfacing as mr
    monkeypatch.setattr(mr, "_memory_md", lambda: tmp_path / "NOPE.md")
    assert mr._list_memory_headings() == []


def test_content_for_heading_plaintext(tmp_path, monkeypatch) -> None:
    import core.services.memory_resurfacing as mr
    mem = tmp_path / "MEMORY.md"
    mem.write_text("## Emne A\nlinje 1\nlinje 2\n## Emne B\nandet\n", encoding="utf-8")
    monkeypatch.setattr(mr, "_memory_md", lambda: mem)
    content = mr._content_for_heading("Emne A")
    assert "linje 1" in content
