from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.runtime import db_runtime_executive_signals as registry


def _loop_rows(db, thread_id: str) -> list[dict]:
    """Læs direkte fra tabellen — ikke gennem servicelaget."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT signal_id, canonical_key, status, status_reason, run_id, "
            "source_run_id, thread_id FROM runtime_open_loop_signals "
            "WHERE thread_id = ? ORDER BY id",
            (thread_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def _declare(tracking, name="Hvorfor driver loops?", run_id="run-A"):
    return tracking.declare_open_loop_thread(
        name=name, declared_by="jarvis", run_id=run_id, session_id="s1"
    )


@pytest.mark.parametrize(
    ("name", "declared_by"),
    [("", "jarvis"), ("   ", "bjorn"), ("Et navn", "heuristic"), ("Et navn", "")],
)
def test_thread_needs_a_set_name_and_a_conscious_declarer(
    isolated_runtime, name, declared_by
) -> None:
    tracking = isolated_runtime.open_loop_tracking
    with pytest.raises(ValueError):
        tracking.declare_open_loop_thread(
            name=name, declared_by=declared_by, run_id="run-A"
        )
    assert registry.list_runtime_threads() == []
    assert isolated_runtime.db.list_runtime_open_loop_signals(limit=10) == []


def test_declared_name_is_stored_verbatim_and_reused_not_redeclared(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.open_loop_tracking

    out = _declare(tracking, name="  Hvorfor   driver loops? ")
    thread = out["thread"]

    assert thread["name"] == "Hvorfor driver loops?"
    assert thread["status"] == "open"
    assert thread["declared_by"] == "jarvis"
    assert thread["opened_in_run_id"] == "run-A"
    assert thread["closed_at"] == ""
    assert registry.get_open_runtime_thread_by_name("hvorfor driver loops?")["thread_id"] == (
        thread["thread_id"]
    )
    # Eksakt navn, ikke fuzzy: en omformulering er ikke den samme tråd.
    assert registry.get_open_runtime_thread_by_name("Hvorfor driver loop?") is None
    with pytest.raises(ValueError):
        _declare(tracking, name="hvorfor driver loops?", run_id="run-B")
    assert len(registry.list_runtime_threads()) == 1


def test_thread_spans_two_runs_stays_open_and_closes_only_on_evidence(
    isolated_runtime,
) -> None:
    """Beviset for færdig, målt i tabellen: et loop der overlever sin første
    kørsel og først lukker når spørgsmålet er besvaret."""
    tracking = isolated_runtime.open_loop_tracking
    db = isolated_runtime.db
    out = _declare(tracking)
    tid = out["thread"]["thread_id"]

    # Kørsel A slutter: kilde-kørslen er terminal. Det må ikke lukke tråden.
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO visible_runs (run_id, lane, provider, model, status, finished_at) "
            "VALUES ('run-A', 'visible', 'test', 'test', 'completed', ?)",
            (datetime.now(UTC).isoformat(),),
        )
    tracking.refresh_runtime_open_loop_signal_statuses()
    rows = _loop_rows(db, tid)
    assert [r["status"] for r in rows] == ["open"]

    # Kørsel B berører samme tråd: SAMME række, run_id flytter, source_run_id bliver.
    tracking.touch_open_loop_thread(tid, run_id="run-B", session_id="s2")
    rows = _loop_rows(db, tid)
    assert len(rows) == 1
    assert rows[0]["canonical_key"] == f"open-loop:open-loop:thread:{tid}"
    assert rows[0]["thread_id"] == tid
    assert rows[0]["source_run_id"] == "run-A"
    assert rows[0]["run_id"] == "run-B"
    assert rows[0]["status"] == "open"

    # Fladen læser status in {open, softening}: tråden er synlig som arbejde.
    surface = tracking._build_runtime_open_loop_signal_surface_uncached(limit=8)
    assert surface["summary"]["open_count"] == 1

    # Ingen af de svage veje lukker: kørslens udfald, tid, eller et tomt bevis.
    for kwargs in (
        {"evidence": "", "answered_in_run_id": "run-B"},
        {"evidence": "   ", "answered_in_run_id": "run-B"},
        {"evidence": "Svaret står i commit abc", "answered_in_run_id": ""},
        {"evidence": "Svaret står i commit abc", "answered_in_run_id": "run-A"},
    ):
        with pytest.raises(ValueError):
            tracking.close_open_loop_thread(tid, **kwargs)
        assert [r["status"] for r in _loop_rows(db, tid)] == ["open"]
        assert registry.get_runtime_thread(tid)["status"] == "open"

    closed = tracking.close_open_loop_thread(
        tid, evidence="Loops lukkede sig selv; fjernet i 38a1339a0", answered_in_run_id="run-B"
    )
    assert closed["status"] == "closed"
    assert closed["closed_in_run_id"] == "run-B"
    assert closed["closure_evidence"] == "Loops lukkede sig selv; fjernet i 38a1339a0"
    assert closed["closed_at"]
    rows = _loop_rows(db, tid)
    assert [r["status"] for r in rows] == ["closed"]
    assert rows[0]["status_reason"] == (
        "Answered in run-B: Loops lukkede sig selv; fjernet i 38a1339a0"
    )


def test_silence_never_decays_a_declared_thread(isolated_runtime) -> None:
    tracking = isolated_runtime.open_loop_tracking
    db = isolated_runtime.db
    tid = _declare(tracking)["thread"]["thread_id"]
    old = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    with db.connect() as conn:
        conn.execute(
            "UPDATE runtime_open_loop_signals SET updated_at = ?, created_at = ? "
            "WHERE thread_id = ?",
            (old, old, tid),
        )

    result = tracking.refresh_runtime_open_loop_signal_statuses()

    assert result == {"stale_marked": 0, "auto_closed": 0}
    assert [r["status"] for r in _loop_rows(db, tid)] == ["open"]


def test_thread_loop_cannot_be_closed_around_the_evidence_gate(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.open_loop_tracking
    db = isolated_runtime.db
    tid = _declare(tracking)["thread"]["thread_id"]
    signal_id = _loop_rows(db, tid)[0]["signal_id"]

    with pytest.raises(ValueError):
        db.update_runtime_open_loop_signal_status(
            signal_id, status="closed", updated_at=datetime.now(UTC).isoformat()
        )
    with pytest.raises(ValueError):
        db.upsert_runtime_open_loop_signal(
            signal_id="x", signal_type="open-loop",
            canonical_key=f"open-loop:open-loop:thread:{tid}", status="closed",
            title="t", summary="s", rationale="r", source_kind="k", confidence="high",
            evidence_summary="", support_summary="", support_count=1, session_count=1,
            created_at="2026-11-05T00:00:00+00:00", updated_at="2026-11-05T00:00:00+00:00",
            run_id="run-B", thread_id=tid,
        )
    assert [r["status"] for r in _loop_rows(db, tid)] == ["open"]


def test_closed_or_unknown_thread_cannot_be_touched(isolated_runtime) -> None:
    tracking = isolated_runtime.open_loop_tracking
    db = isolated_runtime.db
    tid = _declare(tracking)["thread"]["thread_id"]
    tracking.close_open_loop_thread(
        tid, evidence="Besvaret i samtalen", answered_in_run_id="run-B"
    )

    with pytest.raises(ValueError):
        tracking.touch_open_loop_thread(tid, run_id="run-C")
    with pytest.raises(ValueError):
        tracking.touch_open_loop_thread("thread-missing", run_id="run-C")
    assert [r["status"] for r in _loop_rows(db, tid)] == ["closed"]
    # Et lukket navn kan erklæres igen som NY tråd med ny identitet.
    again = _declare(tracking, run_id="run-D")["thread"]
    assert again["thread_id"] != tid


def test_supersede_for_domain_now_matches_thread_keyed_siblings(
    isolated_runtime,
) -> None:
    """Fælden fra opgaven: supersede matchede intet så længe nøglen bar run-id.
    Med thread-nøglen rammer den søsterrækken — og kun den."""
    tracking = isolated_runtime.open_loop_tracking
    db = isolated_runtime.db
    tid = _declare(tracking)["thread"]["thread_id"]
    other = _declare(tracking, name="En anden undersøgelse")["thread"]["thread_id"]

    # Samme tråd, ny signal_type → ny nøgle; den gamle række skal retires.
    thread = registry.get_runtime_thread(tid)
    tracking._write_thread_loop(
        thread=thread, run_id="run-B", session_id="s2", summary="", signal_type="persistent-open-loop"
    )

    rows = {r["canonical_key"]: r["status"] for r in _loop_rows(db, tid)}
    assert rows == {
        f"open-loop:open-loop:thread:{tid}": "superseded",
        f"open-loop:persistent-open-loop:thread:{tid}": "open",
    }
    assert [r["status"] for r in _loop_rows(db, other)] == ["open"]


def test_supersede_matches_nothing_for_a_per_run_domain(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.open_loop_tracking
    tid = _declare(tracking)["thread"]["thread_id"]
    n = db.supersede_runtime_open_loop_signals_for_domain(
        domain_key="run-A", exclude_signal_id="none",
        updated_at=datetime.now(UTC).isoformat(), status_reason="x",
    )
    assert n == 0
    assert [r["status"] for r in _loop_rows(db, tid)] == ["open"]


def test_per_turn_candidate_with_the_same_title_does_not_merge_into_a_thread(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.open_loop_tracking
    db = isolated_runtime.db
    tid = _declare(tracking, name="Danish concise calibration")["thread"]["thread_id"]

    tracking._persist_open_loop_signals(
        signals=[{
            "signal_type": "open-loop",
            "canonical_key": "open-loop:open-loop:visible-xyz",
            "title": "Open loop: Danish concise calibration",
            "summary": "per-turn",
        }],
        session_id="s9",
        run_id="visible-xyz",
    )

    assert len(_loop_rows(db, tid)) == 1
    legacy = [
        r for r in db.list_runtime_open_loop_signals(limit=10) if not r["thread_id"]
    ]
    assert [(r["canonical_key"], r["source_run_id"]) for r in legacy] == [
        ("open-loop:open-loop:visible-xyz", "visible-xyz")
    ]


def test_old_table_is_migrated_and_legacy_rows_get_source_run_id(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    with db.connect() as conn:
        conn.execute("DROP TABLE IF EXISTS runtime_open_loop_signals")
        conn.execute(
            """CREATE TABLE runtime_open_loop_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL, canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open', title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '', rationale TEXT NOT NULL DEFAULT '',
            source_kind TEXT NOT NULL DEFAULT '', confidence TEXT NOT NULL DEFAULT '',
            evidence_summary TEXT NOT NULL DEFAULT '', support_summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '', run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '', support_count INTEGER NOT NULL DEFAULT 1,
            session_count INTEGER NOT NULL DEFAULT 1, merge_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
        )
        conn.execute(
            "INSERT INTO runtime_open_loop_signals (signal_id, signal_type, run_id, "
            "created_at, updated_at) VALUES ('old', 'open-loop', 'run-old', 'a', 'a')"
        )
        conn.commit()

    rows = db.list_runtime_open_loop_signals(limit=5)

    assert [(r["signal_id"], r["thread_id"], r["source_run_id"]) for r in rows] == [
        ("old", "", "run-old")
    ]
