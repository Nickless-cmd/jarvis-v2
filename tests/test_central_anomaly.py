"""Tests for anomali-detektoren — fanger/klassificerer udefinerede fejl."""
from __future__ import annotations

from core.services import central_anomaly as ca


def test_classify_importance():
    assert ca._classify("KeyError", "x mangler", "uncaught") == ("uncaught:KeyError", "high")
    assert ca._classify("TimeoutError", "provider timed out", "log")[1] == "low"
    assert ca._classify("RuntimeError", "permission denied for user", "log")[1] == "critical"
    assert ca._classify("MemoryError", "out of memory", "log")[1] == "critical"
    assert ca._classify("ValueError", "noget gik galt", "log")[1] == "medium"


def test_signature_strips_volatile():
    s1 = ca._signature("log:Error", "run aaaabbbbccccdddd failed at /a/b.py line 42")
    s2 = ca._signature("log:Error", "run eeeeffff00001111 failed at /c/d.py line 99")
    assert s1 == s2  # id/sti/tal normaliseret væk
    assert "<id>" in s1 and "<path>" in s1 and "<n>" in s1


def test_classify_category_is_source_and_type():
    cat, _ = ca._classify("AttributeError", "x", "thread")
    assert cat == "thread:AttributeError"


def test_record_is_self_safe(monkeypatch):
    # selv hvis DB-laget kaster, må record_anomaly aldrig kaste videre
    import core.runtime.db_anomalies as da
    monkeypatch.setattr(da, "record_anomaly_signature",
                        lambda **k: (_ for _ in ()).throw(RuntimeError("nede")))
    ca.record_anomaly(source="uncaught", exc_type="KeyError", message="boom")


def test_reentrancy_guard_blocks_nested(monkeypatch):
    calls = []
    import core.runtime.db_anomalies as da
    monkeypatch.setattr(da, "record_anomaly_signature", lambda **k: calls.append(1) or True)
    # simulér at vi allerede er inde i en anomali-registrering
    ca._guard.busy = True
    try:
        ca.record_anomaly(source="log", exc_type="X", message="nested")
        assert calls == []  # blokeret af reentrancy-guard
    finally:
        ca._guard.busy = False


def test_tb_location_extracts_file_line():
    import core.services.central_anomaly as ca
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        loc = ca._tb_location(sys.exc_info()[2])
    assert "test_central_anomaly.py:" in loc and " in " in loc


def test_record_anomaly_stores_location(isolated_runtime, monkeypatch):
    import core.services.central_anomaly as ca
    captured = {}
    monkeypatch.setattr("core.runtime.db_anomalies.record_anomaly_signature",
                        lambda **k: captured.update(k) or True)
    ca._cooldown.clear()
    ca.record_anomaly(source="test", exc_type="KeyError", message="missing",
                      location="core/x.py:42 in foo")
    assert captured.get("location") == "core/x.py:42 in foo"
