"""Smoke test for core.services.hardware_body.

The public hardware state getter should expose a collected snapshot and cache
the computed pressure classification.
"""

from core.services import hardware_body


def test_get_hardware_state_returns_collected_snapshot(monkeypatch) -> None:
    hardware_body._cache = {}
    hardware_body._cache_at = 0.0
    monkeypatch.setattr(
        hardware_body,
        "_collect",
        lambda: {
            "cpu_pct": 91.0,
            "ram_pct": 82.0,
            "disk_free_gb": 12.0,
            "cpu_temp_c": 78.0,
            "gpus": [],
            "pressure": "high",
            "energy_budget": 54,
            "circadian_preference": "morgen",
            "wake_state": "alert",
        },
    )

    state = hardware_body.get_hardware_state()

    assert state["cpu_pct"] == 91.0
    assert state["pressure"] == "high"
    assert state["energy_budget"] == 54
    assert state["circadian_preference"] == "morgen"
    assert state["wake_state"] == "alert"
