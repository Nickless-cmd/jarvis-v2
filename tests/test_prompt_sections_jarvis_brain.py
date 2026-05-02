"""Tests for core/services/prompt_sections/jarvis_brain.py — summary injection."""
from __future__ import annotations
import pytest


def test_build_section_returns_empty_when_no_file(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path)
    from core.services.prompt_sections.jarvis_brain import build_jarvis_brain_section
    text = build_jarvis_brain_section(token_budget=350)
    assert text == ""


def test_build_section_loads_summary_file(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path)
    summary = tmp_path / "jarvis_brain_summary.md"
    summary.write_text("# Hvad jeg ved nu\n\n**Engineering:** test.\n", encoding="utf-8")
    from core.services.prompt_sections.jarvis_brain import build_jarvis_brain_section
    text = build_jarvis_brain_section(token_budget=350)
    assert "Engineering" in text
    assert text.startswith("## Hvad jeg ved nu (min egen hjerne)")


def test_build_section_returns_empty_for_empty_file(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path)
    summary = tmp_path / "jarvis_brain_summary.md"
    summary.write_text("", encoding="utf-8")
    from core.services.prompt_sections.jarvis_brain import build_jarvis_brain_section
    text = build_jarvis_brain_section(token_budget=350)
    assert text == ""


def test_build_section_trims_at_section_boundary(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path)
    summary = tmp_path / "jarvis_brain_summary.md"
    # Create a deliberately oversized summary with section breaks
    summary.write_text(
        "**A:** " + "x" * 800 + "\n**B:** keep\n",
        encoding="utf-8",
    )
    from core.services.prompt_sections.jarvis_brain import build_jarvis_brain_section
    text = build_jarvis_brain_section(token_budget=20)  # very tight
    assert len(text) < 800  # was trimmed
