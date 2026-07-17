from core.services.central_realtime import runtime_liveness


def test_runtime_liveness_reports_truthful_topology():
    info = runtime_liveness()
    # Only the two real systemd units — NOT heartbeat/central.
    assert set(info["systemd_services"]) == {"jarvis-api", "jarvis-runtime"}
    # The note must explicitly deny that heartbeat/central are separate services,
    # so Jarvis stops inventing them as "inactive services".
    assert "IKKE separate" in info["note"]
    # Heartbeat freshness keys always present (values may be None in an empty DB).
    assert "heartbeat_last_tick_age_seconds" in info
    assert "heartbeat_alive" in info


def test_runtime_liveness_never_raises():
    # Self-safe contract: must return a dict even if the DB is unavailable.
    info = runtime_liveness()
    assert isinstance(info, dict)
    assert "systemd_services" in info
