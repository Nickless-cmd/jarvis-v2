from __future__ import annotations


def test_recall_telemetry_error_shape_keeps_scalar_window(monkeypatch) -> None:
    from core.services import memory_recall_telemetry as telemetry

    monkeypatch.setattr("core.runtime.db.connect", lambda: (_ for _ in ()).throw(RuntimeError("down")))
    result = telemetry.count_recent_recall_empty(hours=0)
    assert result == {"status": "error", "window_hours": 1, "total": 0, "by_tool": {}}
