from __future__ import annotations
from core.services import dream_consolidation_daemon as d


def test_session_gate_skips_when_too_few(isolated_runtime, monkeypatch):
    monkeypatch.setattr(d, "_load", lambda: {"consolidations": [], "last_run_at": "2020-01-01T00:00:00+00:00"})
    monkeypatch.setattr(d, "_is_idle_enough", lambda: (True, 99))
    monkeypatch.setattr(d, "_sessions_since", lambda last: 2)  # < 5
    called = {"n": 0}
    monkeypatch.setattr(d, "consolidate_now", lambda: called.__setitem__("n", 1) or {})
    r = d.tick()
    assert r["skipped"] is True and "too-few-sessions" in r["reason"]
    assert called["n"] == 0


def test_lock_skips_when_held(isolated_runtime, monkeypatch):
    monkeypatch.setattr(d, "_load", lambda: {"consolidations": [], "last_run_at": None})
    monkeypatch.setattr(d, "_is_idle_enough", lambda: (True, 99))
    monkeypatch.setattr(d, "_sessions_since", lambda last: 10)
    monkeypatch.setattr(d, "_acquire_consolidation_lock", lambda: False)
    called = {"n": 0}
    monkeypatch.setattr(d, "consolidate_now", lambda: called.__setitem__("n", 1) or {})
    r = d.tick()
    assert r["skipped"] is True and r["reason"] == "already-dreaming"
    assert called["n"] == 0


def test_runs_and_releases_lock_when_gates_pass(isolated_runtime, monkeypatch):
    monkeypatch.setattr(d, "_load", lambda: {"consolidations": [], "last_run_at": None})
    monkeypatch.setattr(d, "_is_idle_enough", lambda: (True, 99))
    monkeypatch.setattr(d, "_sessions_since", lambda last: 10)
    monkeypatch.setattr(d, "_acquire_consolidation_lock", lambda: True)
    released = {"n": 0}
    monkeypatch.setattr(d, "_release_consolidation_lock", lambda: released.__setitem__("n", released["n"] + 1))
    monkeypatch.setattr(d, "consolidate_now", lambda: {"consolidations": ["x"]})
    r = d.tick()
    assert r == {"consolidations": ["x"]}
    assert released["n"] == 1


# ── _is_idle_enough: fuld stilhed vs. lav aktivitet (fix 2026-08-30) ──────
# Før krævede gaten 30 min UDEN synlige runs — hvilket aldrig indtraf fordi der
# altid er et chat-run hvert 15-20 min. Nu: <= 2 runs i 30 min = lav aktivitet.


def _run(started_at: str) -> dict:
    return {"started_at": started_at, "text_preview": "x"}


def test_idle_full_silence_allows(monkeypatch):
    """Ingen synlige runs i 30+ min → fuld stilhed → tilladt."""
    monkeypatch.setattr(
        "core.runtime.db.recent_visible_runs",
        lambda limit=20: [_run("2026-08-29T00:00:00+00:00")],
    )
    ok, minutes = d._is_idle_enough()
    assert ok is True and minutes >= 30


def _iso(minutes_ago: int) -> str:
    from datetime import UTC, datetime, timedelta
    return (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()


def test_idle_low_activity_allows(monkeypatch):
    """1-2 synlige runs i 30-min vinduet → lav aktivitet → tilladt."""
    monkeypatch.setattr(
        "core.runtime.db.recent_visible_runs",
        lambda limit=20: [_run(_iso(10))],
    )
    ok, _ = d._is_idle_enough()
    assert ok is True


def test_idle_active_chat_blocks(monkeypatch):
    """> 2 synlige runs i 30-min vinduet → aktiv samtale → blokeret."""
    monkeypatch.setattr(
        "core.runtime.db.recent_visible_runs",
        lambda limit=20: [_run(_iso(5)), _run(_iso(10)), _run(_iso(15))],
    )
    ok, _ = d._is_idle_enough()
    assert ok is False


def test_idle_exception_is_fail_closed(monkeypatch):
    """DB-fejl → fail-closed (False), aldrig blind konsolidering."""
    def boom(limit=20):
        raise RuntimeError("db down")
    monkeypatch.setattr("core.runtime.db.recent_visible_runs", boom)
    ok, _ = d._is_idle_enough()
    assert ok is False
