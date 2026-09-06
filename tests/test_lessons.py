"""Task 5 (memory repair 2026-09-04): mistakes reach the next conversation."""
from __future__ import annotations

import sqlite3
from unittest.mock import patch

import pytest

from core.runtime import db_lessons as L
from core.services import lessons as S


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "lessons.sqlite"

    def _connect():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(L, "connect", _connect)
    return path


def test_record_correction_keeps_both_sides(db):
    r = S.record_correction(
        session_id="chat-1",
        user_words="nej, nøglen ligger i runtime.json, ikke i .env",
        jarvis_words="pfSense-nøglen ligger i .env",
    )
    assert r["outcome"] == "created" and r["status"] == "active"
    assert "runtime.json" in r["lesson"] and "efter jeg sagde" in r["lesson"]
    assert r["user_words"].startswith("nej, nøglen")
    assert r["jarvis_words"].startswith("pfSense-nøglen")


def test_tool_error_needs_two_occurrences(db):
    a = S.record_tool_error(tool_name="bash", error_text="ModuleNotFoundError: No module named 'core'")
    assert a["status"] == "proposed"
    b = S.record_tool_error(tool_name="bash", error_text="ModuleNotFoundError: No module named 'core'")
    assert b["status"] == "active" and b["evidence_count"] == 2


def test_review_lessons_are_proposed(db):
    out = S.record_review_lessons(["Verificér før jeg påstår noget", "x"], "self_review")
    assert len(out) == 1 and out[0]["status"] == "proposed"


def test_section_lists_similar_first_then_strong(db):
    S.record_correction(session_id="s", user_words="nej, mikrofonens gain må ikke dumpes ved TTS", jarvis_words="jeg sætter gain ned")
    S.record_correction(session_id="s", user_words="nej, pfsense-nøglen bor i runtime.json", jarvis_words="den ligger i .env")
    S.record_correction(session_id="s", user_words="nej, pfsense-nøglen bor i runtime.json", jarvis_words="den ligger i .env")
    text = S.build_lessons_section("hvor ligger pfsense nøglen?")
    lines = text.splitlines()
    assert lines[0].startswith("Lektier")
    assert "pfsense" in lines[1].lower()
    assert "gentaget 1×" in lines[1]
    assert sum(1 for ln in lines if ln.startswith("- [")) <= 6


def test_section_empty_without_active_lessons(db):
    S.record_review_lessons(["kun proposed"], "self_review")
    assert S.build_lessons_section("noget") == ""


def test_arc_rules_go_to_lessons_as_proposed_and_section_is_retired(db, tmp_path, monkeypatch):
    from core.services import arc_rule_extractor as arc

    assert arc.arc_rules_section() == ""
    arcs = tmp_path / "arcs"
    arcs.mkdir()
    monkeypatch.setattr(arc, "_arcs_dir", lambda: arcs)
    monkeypatch.setattr(arc, "_rules_path", lambda: arcs / "RULES.md")
    monkeypatch.setattr(arc, "_mark_processed", lambda p: None)
    arc_file = arcs / "monthly_2026-09.md"
    arc_file.write_text("# arc\n\nnoget om governance\n", encoding="utf-8")
    with patch("core.services.daemon_llm.daemon_llm_call",
               return_value="RULE: Deaktiver overvældende governance-mekanismer ved første tegn\n"), \
         patch("core.eventbus.bus.event_bus.publish", lambda *a, **k: None):
        out = arc.extract_rules_from_arc(arc_file)
    assert out.get("status") == "ok" and out.get("rules_added") == 1
    proposed = L.list_lessons(status="proposed")
    active = L.list_lessons(status="active")
    assert not active
    assert proposed and "governance" in proposed[0]["lesson"].lower()
