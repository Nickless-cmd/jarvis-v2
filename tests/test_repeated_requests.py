"""Gentagne anmodninger og rettelser → ét regel-forslag (blok C, 2026-09-04)."""
from __future__ import annotations

import sqlite3

import pytest

from core.services import repeated_requests as RR


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "rr.sqlite"

    def _connect():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(RR, "connect", _connect)
    return path


def test_the_same_request_in_different_words_is_the_same_request(db):
    assert RR.normalize("husk commit") == RR.normalize("commit det, husk nu")
    assert RR.normalize("kan du lige committe") != RR.normalize("ryd op i logfilerne")


def test_third_time_across_two_sessions_matures(db):
    a = RR.note_request(text="husk at committe arbejdet", session_id="s1")
    b = RR.note_request(text="commit arbejdet husk", session_id="s1")
    c = RR.note_request(text="husk commit af arbejdet", session_id="s2")
    assert a["status"] == "new" and a["matured"] is False
    assert b["matured"] is False          # tre gange kræves
    assert c["matured"] is True and c["mention_count"] == 3 and c["session_count"] == 2


def test_three_times_in_one_session_is_not_a_rule(db):
    for _ in range(4):
        res = RR.note_request(text="ryd de stale markers", session_id="s1")
    assert res["mention_count"] == 4 and res["matured"] is False


def test_a_correction_matures_the_second_time_in_one_session(db):
    RR.note_request(text="skriv paa dansk ikke engelsk", session_id="s1", kind="correction")
    res = RR.note_request(text="dansk ikke engelsk skriv", session_id="s1", kind="correction")
    assert res["matured"] is True and res["mention_count"] == 2


def test_short_requests_are_ignored(db):
    assert RR.note_request(text="ok", session_id="s1")["status"] == "skipped"


def test_question_carries_the_number_that_triggered_it(db):
    q = RR.build_question(text="husk at committe", mention_count=3, session_count=2, kind="request")
    assert "3 gange" in q and "2 samtaler" in q and "husk at committe" in q
    qc = RR.build_question(text="svar paa dansk", mention_count=2, session_count=1, kind="correction")
    assert "rettet mig" in qc and "2 gange" in qc


def test_it_is_only_asked_once(db, monkeypatch):
    added: list[dict] = []
    monkeypatch.setattr("core.services.proactive_candidates.add_candidate",
                        lambda **kw: (added.append(kw), {"status": "added"})[1])
    RR.note_and_surface(text="husk at committe arbejdet", session_id="s1")
    RR.note_and_surface(text="commit arbejdet husk", session_id="s1")
    res = RR.note_and_surface(text="husk commit af arbejdet", session_id="s2")
    assert res["surfaced"] is True and len(added) == 1
    assert added[0]["source"] == "repeated_requests"
    # Fjerde gang: allerede spurgt → intet nyt spørgsmål.
    again = RR.note_and_surface(text="husk commit arbejdet nu", session_id="s3")
    assert again.get("surfaced") is not True and len(added) == 1


def test_yes_writes_a_kerne_line_with_its_reason(db, tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "USER.md").write_text("# USER\n\n## Kerne\n- Sprog: dansk\n", encoding="utf-8")
    monkeypatch.setattr("core.identity.workspace_bootstrap.ensure_default_workspace", lambda: ws)
    RR.note_request(text="husk at committe arbejdet", session_id="s1")
    RR.note_request(text="commit arbejdet husk", session_id="s1")
    res = RR.note_request(text="husk commit af arbejdet", session_id="s2")
    out = RR.record_decision(request_id=res["request_id"], accepted=True)
    assert out["written"] is True
    text = (ws / "USER.md").read_text(encoding="utf-8")
    assert "husk commit af arbejdet" in text and "bedt om 3 gange" in text


def test_no_is_remembered_so_he_is_not_asked_again(db):
    RR.note_request(text="brug altid mork tilstand her", session_id="s1")
    RR.note_request(text="mork tilstand altid brug her", session_id="s1")
    res = RR.note_request(text="altid mork tilstand brug her", session_id="s2")
    RR.record_decision(request_id=res["request_id"], accepted=False)
    again = RR.note_request(text="mork tilstand her altid brug", session_id="s3")
    assert again["matured"] is False
    assert RR.counts().get(RR.STATUS_DECLINED) == 1
