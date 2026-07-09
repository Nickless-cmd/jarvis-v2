# tests/test_docs_drift_watchdog.py
import json
from datetime import datetime, timedelta, timezone
from core.services import docs_drift_watchdog as w


def test_read_report_missing_is_empty(tmp_path):
    assert w.read_report(tmp_path / "nope.json") == {}


def test_check_docs_drift_reads_counts(tmp_path):
    rep = tmp_path / "drift_report.json"
    rep.write_text(json.dumps({"counts": {"hard": 2, "soft": 5}, "generated_at": "2026-07-08T00:00:00+00:00"}))
    state = w.check_docs_drift(report_path=rep, repo=tmp_path)
    assert state["hard_count"] == 2 and state["soft_count"] == 5
    assert state["report_present"] is True
    assert state["generated_at"].startswith("2026-07-08")


def test_check_docs_drift_missing_report_safe(tmp_path):
    state = w.check_docs_drift(report_path=tmp_path / "nope.json", repo=tmp_path)
    assert state["hard_count"] == 0 and state["report_present"] is False


def test_report_stale_is_age_based_not_mtime(tmp_path):
    """report_stale reflects the report's own generated_at age (not filesystem mtimes),
    so a deploy that rewrites file mtimes never false-positives."""
    rep = tmp_path / "drift_report.json"
    # Fresh report → not stale, even though the file was just written (mtime is 'now').
    fresh = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    rep.write_text(json.dumps({"counts": {"hard": 0, "soft": 0}, "generated_at": fresh}))
    assert w.check_docs_drift(report_path=rep, repo=tmp_path)["report_stale"] is False
    # Old report → stale.
    old = (datetime.now(timezone.utc) - timedelta(days=w._REPORT_STALE_AFTER_DAYS + 1)).isoformat()
    rep.write_text(json.dumps({"counts": {"hard": 0, "soft": 0}, "generated_at": old}))
    assert w.check_docs_drift(report_path=rep, repo=tmp_path)["report_stale"] is True
    # Missing report → stale.
    assert w.check_docs_drift(report_path=tmp_path / "gone.json", repo=tmp_path)["report_stale"] is True


def test_build_surface_never_throws():
    surf = w.build_docs_drift_surface()
    assert isinstance(surf, dict) and "hard_count" in surf
