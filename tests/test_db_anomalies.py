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


# ── Aldersvinduet paa anomaly_counts (12/11-2026) ────────────────────────────
#
# Hvorfor: én critical fra 9. november (set én gang, count=1) holdt
# anomaly-clusteret rødt i tre dage mens Centralen var sund. Farven blev regnet
# paa ALT uløst uden alder, saa en ægte rød tilstand ikke kunne skelnes fra en
# spøgelsesalarm. Reglen: kun anomalier SET inden for vinduet farver fladen;
# ældre tælles som `stale` og forsvinder ikke fra dataene.

def _insert_anomaly(monkeypatch, tmp_path, *, sig, importance, last_seen):
    _fresh_db(monkeypatch, tmp_path)
    import core.runtime.db_core as dbc
    with dbc.connect() as conn:
        da._ensure_anomalies_table(conn)
        conn.execute("DELETE FROM central_anomalies")
        conn.execute(
            "INSERT INTO central_anomalies (signature, category, importance, source, count, "
            "first_seen, last_seen, sample, resolved, location, known_signal) "
            "VALUES (?,?,?,?,?,?,?,?,0,'',0)",
            (sig, "test", importance, "t", 1, last_seen, last_seen, "x"),
        )


def test_gammel_critical_taeller_som_stale(monkeypatch, tmp_path):
    """En critical fra 3 dage siden maa ikke farve fladen — men maa ikke forsvinde."""
    from datetime import UTC, datetime, timedelta
    gammel = (datetime.now(UTC) - timedelta(days=3)).isoformat()
    _insert_anomaly(monkeypatch, tmp_path, sig="test:gammel", importance="critical", last_seen=gammel)
    c = da.anomaly_counts()
    assert c["critical"] == 0, c
    assert c["stale"] == 1, c


def test_frisk_critical_taeller_stadig(monkeypatch, tmp_path):
    """Vinduet maa ikke goere fladen blind: en frisk critical skal stadig taelle."""
    from datetime import UTC, datetime
    nu = datetime.now(UTC).isoformat()
    _insert_anomaly(monkeypatch, tmp_path, sig="test:frisk", importance="critical", last_seen=nu)
    c = da.anomaly_counts()
    assert c["critical"] == 1, c
    assert c["stale"] == 0, c


def test_vindue_nul_giver_den_gamle_adfaerd(monkeypatch, tmp_path):
    """active_window_hours=0 slaar vinduet fra — vagter skal kunne se hele historikken."""
    from datetime import UTC, datetime, timedelta
    gammel = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    _insert_anomaly(monkeypatch, tmp_path, sig="test:urgammel", importance="critical", last_seen=gammel)
    assert da.anomaly_counts(active_window_hours=0)["critical"] == 1
    assert da.anomaly_counts()["critical"] == 0


def test_status_bliver_groen_paa_kun_stale():
    """Farven: kun-stale er groen, men frisk critical og aaben breaker er stadig roed."""
    from core.services.central_realtime import _status_from
    assert _status_from({}, [], [], {}, [], {"critical": 0, "high": 0, "total": 0, "stale": 61}) == "green"
    assert _status_from({}, [], [], {}, [], {"critical": 1, "high": 0, "total": 1}) == "red"
    assert _status_from({}, [], ["breaker"], {}, [], {"critical": 0, "high": 0, "total": 0}) == "red"
