"""Functional tests for the spec-driven signal_tracking framework.

Proves the generic lifecycle (track → persist → refresh → surface) against
mock DB callables, and that per-spec knobs (status set, stale window, early-
retire, events, supersede grouping) are honoured — i.e. reflection's rich
behaviour does NOT leak into a plain spec.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import core.services.signal_tracking_framework as f
from core.services.signal_tracking_framework import (
    SignalTrackingSpec,
    make_candidate,
    merge_fragments,
    parse_dt,
    stronger_confidence,
)


# ── utils ────────────────────────────────────────────────────────────────────
def test_parse_dt_z_and_tznormalize():
    assert parse_dt("2026-07-23T10:00:00Z") is not None
    assert parse_dt("not-a-date") is None
    # tz_normalize forces UTC on a naive stamp (autonomy_pressure/open_loop need this)
    got = parse_dt("2026-07-23T10:00:00", tz_normalize=True)
    assert got is not None and got.tzinfo is not None
    # py3.11 fromisoformat handles "Z" natively, so it parses either way; the
    # z_normalize toggle exists to preserve the originals' explicit .replace().
    assert parse_dt("2026-07-23T10:00:00Z", z_normalize=False) is not None


def test_merge_fragments_dedup_and_cap():
    assert merge_fragments("a", "a", "b") == "a | b"
    assert merge_fragments("a", "b", "c", "d", "e", cap=2) == "a | b"
    assert merge_fragments("", None, "  x  ") == "x"


def test_stronger_confidence():
    assert stronger_confidence("low", "high", "medium") == "high"
    assert stronger_confidence("low", "low") == "low"


# ── a plain (S-family) spec with mock DB ─────────────────────────────────────
class _FakeDB:
    def __init__(self):
        self.rows: list[dict] = []
        self.superseded: list[dict] = []

    def list_fn(self, *, limit):
        return list(self.rows[:limit])

    def upsert_fn(self, **kw):
        row = dict(kw)
        row["was_created"] = True
        row["was_updated"] = False
        self.rows.append(row)
        return row

    def update_status_fn(self, signal_id, *, status, updated_at, status_reason):
        for r in self.rows:
            if r.get("signal_id") == signal_id:
                r["status"] = status
                r["status_reason"] = status_reason
                r["updated_at"] = updated_at
                return dict(r)
        return None

    def supersede_fn(self, *, domain_key, exclude_signal_id, updated_at, status_reason):
        self.superseded.append({"domain_key": domain_key, "exclude": exclude_signal_id})
        return 2  # pretend 2 siblings superseded


def _plain_spec(db, extract):
    return SignalTrackingSpec(
        name="probe",
        slug="probe-signal",
        list_fn=db.list_fn,
        upsert_fn=db.upsert_fn,
        update_status_fn=db.update_status_fn,
        supersede_fn=db.supersede_fn,
        extract_fn=extract,
    )


def test_track_persists_and_publishes(monkeypatch):
    published: list[tuple[str, dict]] = []
    monkeypatch.setattr(f, "_publish", lambda name, payload: published.append((name, payload)))

    db = _FakeDB()

    def extract(spec, ctx):
        return [
            make_candidate(
                spec, signal_type="drift", discriminator="drift", key="focus-a",
                status="active", title="T", summary="S", rationale="R",
                status_reason="live", source_items=[{"support_count": 3}],
            )
        ]

    spec = _plain_spec(db, extract)
    out = f.track_for_visible_turn(spec, session_id="s1", run_id="r1")
    assert out["created"] == 1 and out["updated"] == 0
    assert len(db.rows) == 1
    row = db.rows[0]
    # canonical key uses the spec slug, NOT reflection's
    assert row["canonical_key"] == "probe-signal:drift:focus-a"
    assert row["signal_id"].startswith("probe-")
    # standard events fired; supersede happened + published
    names = [n for n, _ in published]
    assert "probe_signal.created" in names
    assert "probe_signal.superseded" in names
    assert db.superseded and db.superseded[0]["domain_key"] == "focus-a"
    # a plain spec must NOT emit reflection-only events
    assert "probe_signal.settled" not in names


def test_refresh_respects_window_and_no_early_retire(monkeypatch):
    published: list[tuple[str, dict]] = []
    monkeypatch.setattr(f, "_publish", lambda name, payload: published.append((name, payload)))
    db = _FakeDB()
    old = (datetime.now(UTC) - timedelta(days=9)).isoformat()
    fresh = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    db.rows = [
        {"signal_id": "a", "status": "active", "updated_at": old, "confidence": "low", "support_count": 1},
        {"signal_id": "b", "status": "active", "updated_at": fresh, "confidence": "low", "support_count": 1},
        {"signal_id": "c", "status": "archived", "updated_at": old},  # not refreshable
    ]
    spec = _plain_spec(db, lambda s, c: [])  # default stale_after_days=7, no early-retire
    res = f.refresh_statuses(spec)
    assert res["stale_marked"] == 1  # only 'a' (9d > 7d); 'b' fresh, 'c' wrong status
    assert any(n == "probe_signal.stale" for n, _ in published)


def test_early_retire_only_when_configured():
    db = _FakeDB()
    old = (datetime.now(UTC) - timedelta(days=3)).isoformat()
    db.rows = [{"signal_id": "a", "status": "active", "updated_at": old,
                "confidence": "low", "support_count": 1, "title": "x", "summary": "y"}]
    # plain spec: 3d < 7d window → NOT stale
    assert f.refresh_statuses(_plain_spec(db, lambda s, c: []))["stale_marked"] == 0
    # reflection-style spec: early_retire (low conf) → 2d window → 3d IS stale
    db2 = _FakeDB()
    db2.rows = [{"signal_id": "a", "status": "active", "updated_at": old,
                 "confidence": "low", "support_count": 1, "title": "x", "summary": "y"}]
    rich = SignalTrackingSpec(
        name="probe", slug="probe-signal",
        list_fn=db2.list_fn, upsert_fn=db2.upsert_fn, update_status_fn=db2.update_status_fn,
        extract_fn=lambda s, c: [], stale_after_days=14, early_retire_days=2,
        early_retire_predicate=lambda item: str(item.get("confidence")) == "low",
    )
    assert f.refresh_statuses(rich)["stale_marked"] == 1


def test_build_surface_buckets_and_summary():
    db = _FakeDB()
    db.rows = [
        {"signal_id": "1", "status": "active", "title": "A", "updated_at": "2026-07-23T10:00:00Z"},
        {"signal_id": "2", "status": "softening", "title": "B", "updated_at": "2026-07-23T09:00:00Z"},
        {"signal_id": "3", "status": "stale", "title": "C", "updated_at": "2026-07-01T09:00:00Z"},
    ]
    spec = _plain_spec(db, lambda s, c: [])
    surface = f.build_surface(spec, limit=8)
    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["current_status"] == "active"
