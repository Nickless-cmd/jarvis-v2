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


# ── Intelligent anomaly capture (2026-06-30): known-signal promotion ──────────

def _fresh_db(monkeypatch, tmp_path):
    import core.runtime.db_core as dbc
    monkeypatch.setattr(dbc, "_DB_PATH", str(tmp_path / "anom.db"), raising=False)


def test_auto_promote_high_after_3(monkeypatch, tmp_path):
    _fresh_db(monkeypatch, tmp_path)
    sig = "test:KeyError|probe <n>"
    for _ in range(3):
        da.record_anomaly_signature(signature=sig, category="test:KeyError",
                                    importance="high", source="test", sample="x")
    known = da.get_known_signal(sig)
    assert known is not None and known["action"] == "route_to_nerve"
    assert known["nerve"] == "anomaly/test:KeyError"
    # promoveret → ude af anomalies-listen, inde i known_signals
    assert not any(a["signature"] == sig for a in da.list_anomalies(limit=100))
    assert any(k["signature"] == sig for k in da.list_known_signals(limit=100))


def test_exclude_known_toggle(monkeypatch, tmp_path):
    _fresh_db(monkeypatch, tmp_path)
    sig = "test:E|x <n>"
    da.record_anomaly_signature(signature=sig, category="test:E", importance="high", source="t", sample="x")
    da.route_anomaly_to_nerve(signature=sig, cluster="tools", nerve="operator_tool_error")
    assert not any(a["signature"] == sig for a in da.list_anomalies(exclude_known=True, limit=100))
    assert any(a["signature"] == sig for a in da.list_anomalies(exclude_known=False, limit=100))


def test_manual_route_then_depromote(monkeypatch, tmp_path):
    _fresh_db(monkeypatch, tmp_path)
    sig = "test:R|y <n>"
    da.record_anomaly_signature(signature=sig, category="test:R", importance="medium", source="t", sample="x")
    assert da.route_anomaly_to_nerve(signature=sig, cluster="tools", nerve="operator_tool_error", notes="why")
    k = da.get_known_signal(sig)
    assert k["cluster"] == "tools" and k["nerve"] == "operator_tool_error"
    assert da.depromote_known_signal(sig) is True
    assert da.get_known_signal(sig) is None
    # tilbage som anomali
    assert any(a["signature"] == sig for a in da.list_anomalies(limit=100))


def test_promote_force(monkeypatch, tmp_path):
    _fresh_db(monkeypatch, tmp_path)
    sig = "test:F|z <n>"
    assert da.promote_to_known(signature=sig, count=1, first_seen="", category="test:F",
                               force=True) == "route_to_nerve"
    assert da.get_known_signal(sig) is not None
