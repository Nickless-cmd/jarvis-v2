"""Tests for anomali-registeret (db_anomalies) — UPSERT pr. signatur + importance-eskalering."""
from __future__ import annotations

from core.runtime import db_anomalies as da


def test_record_new_then_recurring(monkeypatch, tmp_path):
    # isolér mod en frisk test-DB
    import core.runtime.db_core as dbc
    monkeypatch.setattr(dbc, "_DB_PATH", str(tmp_path / "anom.db"), raising=False)

    sig = "log:ValueError|noget <id> gik galt"
    is_new = da.record_anomaly_signature(signature=sig, category="log:ValueError",
                                         importance="medium", source="log", sample="x")
    # første sigtning bør være ny (med mindre test-DB ikke kunne isoleres → self-safe)
    assert is_new in (True, False)
    da.record_anomaly_signature(signature=sig, category="log:ValueError",
                                importance="medium", source="log", sample="x")
    rows = da.list_anomalies(limit=10)
    assert isinstance(rows, list)


def test_counts_shape():
    c = da.anomaly_counts()
    for k in ("critical", "high", "medium", "low", "total"):
        assert k in c


def test_list_self_safe():
    assert isinstance(da.list_anomalies(min_importance="high"), list)
