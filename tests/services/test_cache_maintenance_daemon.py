from core.services import cache_maintenance_daemon as cmd


def test_tick_returns_dict_and_is_cadence_gated(isolated_runtime, monkeypatch):
    # Force cadence: first call runs, immediate second call is gated.
    monkeypatch.setattr(cmd, "_last_tick_at", None)
    r1 = cmd.tick_cache_maintenance_daemon()
    assert isinstance(r1, dict)
    r2 = cmd.tick_cache_maintenance_daemon()
    assert r2.get("maintained") is False and r2.get("reason") == "cadence"


def test_surface_shape(isolated_runtime):
    s = cmd.build_cache_maintenance_surface()
    assert isinstance(s, dict) and "last_deleted" in s


def test_checkpoint_result_is_logged(isolated_runtime, caplog):
    with caplog.at_level("INFO", logger="core.services.cache_maintenance_daemon"):
        checkpoint = cmd.checkpoint_wal()
    assert "busy" in checkpoint
    assert any("WAL checkpoint" in record.message and "busy=" in record.message
               for record in caplog.records)
