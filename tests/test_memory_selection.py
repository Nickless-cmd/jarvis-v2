"""prompt_sections/memory_selection (extracted 2026-09-04): line/section selection + fallbacks."""
from __future__ import annotations

from unittest.mock import patch

from core.services.prompt_sections import memory_selection as MS


def test_workspace_memory_entries_strips_headings_and_bullets(tmp_path):
    p = tmp_path / "MEMORY.md"
    p.write_text("# MEMORY\n\n## A\n- første linje\n\n- anden  linje\n## B\n", encoding="utf-8")
    with patch("core.services.workspace_crypto.read_text_for_path", lambda path: path.read_text(encoding="utf-8")):
        entries = MS._workspace_memory_entries(p)
    assert entries == ["første linje", "anden linje"]


def test_heuristic_fallback_drops_lines_that_cannot_change_answer(tmp_path):
    entries = ["a b c", "d e f", "g h i", "j k l", "m n o"]
    with patch("core.runtime.db_core.get_runtime_state_value", lambda key, default=None: True), \
         patch("core.services.workspace_crypto.read_text_for_path", lambda path: None):
        sel = MS._select_relevant_memory_entries(
            entries, user_message="zzz", max_lines=2, max_chars=50, workspace_dir=tmp_path,
        )
    assert sel.lines == []
    assert sel.backend_status == "skipped-visible-hotpath"
    assert sel.fallback_used is True


def test_prompt_contract_reexports_names():
    from core.services import prompt_contract as pc

    assert pc._workspace_memory_section is MS._workspace_memory_section
    assert pc.MemorySectionSelection is MS.MemorySectionSelection
    assert pc._recent_daily_memory_lines is MS._recent_daily_memory_lines


def test_section_path_used_for_memory_md(tmp_path):
    p = tmp_path / "MEMORY.md"
    p.write_text("## pfSense\n- nøglen i .env\n", encoding="utf-8")
    with patch("core.services.workspace_crypto.read_text_for_path", lambda path: path.read_text(encoding="utf-8")), \
         patch("core.services.prompt_sections.memory_md_selection.select_memory_md_sections",
               lambda *a, **k: ["§ pfSense: nøglen i .env"]):
        sel = MS._workspace_memory_section(
            p, label="MEMORY.md", user_message="hvor er pfsense nøglen", max_lines=3, max_chars=1500,
            workspace_dir=tmp_path,
        )
    assert sel is not None and sel.backend_name == "section-embedding"
    assert sel.lines == ["§ pfSense: nøglen i .env"]
