"""Tests for council_memory_service — append and read."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


def _make_service(tmp_path: Path):
    import apps.api.jarvis_api.services.council_memory_service as svc
    log_file = tmp_path / "COUNCIL_LOG.md"
    return svc, log_file


def test_append_creates_file_if_missing(tmp_path):
    svc, log_file = _make_service(tmp_path)
    with patch.object(svc, "_LOG_FILE", log_file):
        svc.append_council_conclusion(
            topic="Hvad begrænser mig?",
            score=0.72,
            members=["filosof", "kritiker", "synthesizer"],
            signals=["autonomy_pressure", "open_loop"],
            transcript="filosof: ...\nkritiker: ...",
            conclusion="Rådet konkluderer at Jarvis bør prioritere autonomi.",
            initiative=None,
        )
    assert log_file.exists()


def test_append_writes_markdown_structure(tmp_path):
    svc, log_file = _make_service(tmp_path)
    with patch.object(svc, "_LOG_FILE", log_file):
        svc.append_council_conclusion(
            topic="Hvad begrænser mig?",
            score=0.72,
            members=["filosof", "kritiker", "synthesizer"],
            signals=["autonomy_pressure", "open_loop"],
            transcript="filosof: ...\nkritiker: ...",
            conclusion="Rådet konkluderer.",
            initiative=None,
        )
    content = log_file.read_text(encoding="utf-8")
    assert "## " in content
    assert "Hvad begrænser mig?" in content
    assert "0.72" in content
    assert "filosof" in content
    assert "autonomy_pressure" in content
    assert "Rådet konkluderer." in content
    assert "### Transcript" in content
    assert "### Konklusion" in content


def test_append_writes_initiative_when_provided(tmp_path):
    svc, log_file = _make_service(tmp_path)
    with patch.object(svc, "_LOG_FILE", log_file):
        svc.append_council_conclusion(
            topic="Test",
            score=0.60,
            members=["synthesizer"],
            signals=["desire"],
            transcript="x",
            conclusion="Done.",
            initiative="Jarvis should write a poem.",
        )
    content = log_file.read_text(encoding="utf-8")
    assert "### Initiative-forslag" in content
    assert "Jarvis should write a poem." in content


def test_multiple_appends_accumulate(tmp_path):
    svc, log_file = _make_service(tmp_path)
    with patch.object(svc, "_LOG_FILE", log_file):
        for i in range(3):
            svc.append_council_conclusion(
                topic=f"Emne {i}",
                score=0.60,
                members=["synthesizer"],
                signals=["desire"],
                transcript="x",
                conclusion=f"Konklusion {i}",
                initiative=None,
            )
    import re
    content = log_file.read_text(encoding="utf-8")
    # Count entry headers only (lines starting with "## ")
    assert len(re.findall(r"^## ", content, re.MULTILINE)) == 3


def test_read_all_entries_returns_parsed_list(tmp_path):
    svc, log_file = _make_service(tmp_path)
    with patch.object(svc, "_LOG_FILE", log_file):
        svc.append_council_conclusion(
            topic="Parse test",
            score=0.65,
            members=["filosof"],
            signals=["conflict"],
            transcript="filosof: test",
            conclusion="Parsed.",
            initiative=None,
        )
        entries = svc.read_all_entries()
    assert len(entries) == 1
    assert entries[0]["topic"] == "Parse test"
    assert entries[0]["conclusion"] == "Parsed."


def test_read_all_entries_empty_when_no_file(tmp_path):
    svc, log_file = _make_service(tmp_path)
    with patch.object(svc, "_LOG_FILE", log_file):
        entries = svc.read_all_entries()
    assert entries == []
