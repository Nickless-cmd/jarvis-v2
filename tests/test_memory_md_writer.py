from __future__ import annotations

from core.memory.memory_md_writer import (
    find_section,
    merge_duplicate_headings,
    normalize_heading,
    upsert_section,
)


def test_normalize_heading_ignores_case_dates_and_punctuation():
    assert normalize_heading("## Decisions") == normalize_heading("decisions")
    assert normalize_heading("Container netværk — IPv6 (oprettet 2026-07-16)") == normalize_heading("Container netværk — IPv6")
    assert normalize_heading("Drømme-konsolidering 2026-07-12") == normalize_heading("Drømme-konsolidering")


def test_upsert_adds_then_replaces_case_insensitively(tmp_path):
    p = tmp_path / "MEMORY.md"
    p.write_text("# MEMORY\n\n## Hardware\n- gpu\n", encoding="utf-8")
    r = upsert_section(p, "Decisions", "- første beslutning")
    assert r["action"] == "added"
    r = upsert_section(p, "decisions", "- ny version")
    assert r["action"] == "updated"
    text = p.read_text(encoding="utf-8")
    assert text.count("## ") == 2
    assert "første beslutning" not in text and "ny version" in text
    assert find_section(text, "DECISIONS") is not None


def test_append_mode_skips_present_lines(tmp_path):
    p = tmp_path / "MEMORY.md"
    p.write_text("## Curated Memory\n- a\n", encoding="utf-8")
    assert upsert_section(p, "Curated Memory", "- a\n- b", mode="append")["action"] == "appended"
    assert upsert_section(p, "Curated Memory", "- a", mode="append")["action"] == "unchanged"
    body = p.read_text(encoding="utf-8")
    assert body.count("- a") == 1 and "- b" in body


def test_merge_duplicate_headings_preserves_bodies():
    text = "## A\n- 1\n\n## B\n- x\n\n## a\n- 2\n"
    out, merged = merge_duplicate_headings(text)
    assert merged == 1
    assert out.count("## ") == 2
    assert out.index("- 2") < out.index("## B")
