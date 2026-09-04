from __future__ import annotations

import sqlite3

import pytest

from core.services import proactive_candidates as PC


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "pc.sqlite"

    def _connect():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(PC, "connect", _connect)
    PC._SHOWN.clear()
    return path


def test_add_dedupes_within_24h_and_normalizes_priority(db):
    a = PC.add_candidate(source="mail_checker", text="Ny mail fra Michelle om iOS-testen", priority="normal")
    b = PC.add_candidate(source="mail_checker", text="ny  mail fra michelle om ios-testen", priority="high")
    assert a["status"] == "added" and b["status"] == "duplicate"
    assert PC.list_pending()[0]["priority"] == "medium"
    assert PC.add_candidate(source="x", text="kort")["status"] == "skipped"


def test_list_orders_by_priority_then_recency(db):
    PC.add_candidate(source="a", text="lav prioritet besked her", priority="low")
    PC.add_candidate(source="b", text="kritisk: mailserveren svarer ikke", priority="critical")
    PC.add_candidate(source="c", text="run-closure: 3 ucommittede filer i repoet", priority="medium")
    assert [c["priority"] for c in PC.list_pending()] == ["critical", "medium", "low"]


def test_relevant_for_and_since_last_line(db):
    PC.add_candidate(source="run_closure_gate", text="autonomt run efterlod 3 ucommittede filer i repoet — auto-commit blokeret", priority="medium")
    PC.add_candidate(source="mail_checker", text="Ny mail fra Michelle om iOS-testen", priority="medium")
    line = PC.build_since_last_line("er der stadig ucommittede filer i repoet?", session_id="s1")
    assert line.startswith("Siden sidst") and "ucommittede" in line
    assert PC.build_since_last_line("hvad er vejret?", session_id="s1") == ""
    assert PC.build_since_last_line("hej", session_id="s1") == ""


def test_mentioned_when_answer_overlaps(db):
    PC.add_candidate(source="run_closure_gate", text="autonomt run efterlod 3 ucommittede filer i repoet", priority="medium")
    PC.build_since_last_line("hvad med de ucommittede filer i repoet?", session_id="s2")
    n = PC.mark_mentioned_if_overlap(session_id="s2", answer_text="Ja — det autonome run efterlod 3 ucommittede filer i repoet, jeg committer dem nu.", run_id="r1")
    assert n == 1
    assert PC.counts().get("mentioned") == 1
    assert PC.mark_mentioned_if_overlap(session_id="s2", answer_text="igen") == 0


def test_not_mentioned_when_answer_unrelated(db):
    PC.add_candidate(source="mail_checker", text="Ny mail fra Michelle om iOS-testen", priority="medium")
    PC.build_since_last_line("hvad sagde Michelle om iOS testen?", session_id="s3")
    assert PC.mark_mentioned_if_overlap(session_id="s3", answer_text="Vejret bliver fint i morgen.") == 0
    assert PC.counts().get("pending") == 1


def test_bridge_candidates_shape_and_mark_surfaced(db):
    PC.add_candidate(source="wakeup_dispatcher", text="Self-wakeup fyrede: morgenbrief-verifikation mangler", priority="high")
    items = PC.bridge_candidates()
    assert items and items[0]["source"] == "proactive_candidates" and items[0]["priority"] == "high"
    assert PC.mark([items[0]["source_id"]], "surfaced") == 1
    assert PC.list_pending() == []


def test_expire_stale(db):
    PC.add_candidate(source="a", text="gammel besked der aldrig blev leveret", priority="low")
    assert PC.expire_stale(days=0) == 1
