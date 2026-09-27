"""Trace storage is best effort so telemetry cannot break a model call."""

from core.services.cheap_lane_route_write import _spor_uden_at_vaelte


def test_route_write_failure_is_logged_without_interrupting_call(caplog):
    def broken_write(**_fields):
        raise RuntimeError("telemetry unavailable")

    assert _spor_uden_at_vaelte(broken_write, provider="p") == ""
    assert "rute-sporet kunne ikke skrives" in caplog.text
