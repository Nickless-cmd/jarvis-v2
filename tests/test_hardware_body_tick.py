"""Tests for run_hardware_body_tick — cadence-producer der føder Jarvis' krop
til Centralen (rådets #1). Verificerer at ticket recorder en skalar + skalar-meta
til central_timeseries("system","hardware_body"), og at den er self-safe."""
from __future__ import annotations

from unittest.mock import patch

from core.services import central_timeseries as ts
from core.services import hardware_body


def _last_point():
    pts = ts.recent("system", "hardware_body")
    return pts[-1] if pts else None


def test_tick_records_scalar_and_meta():
    fake_state = {
        "cpu_pct": 12.5,
        "ram_pct": 44.0,
        "disk_free_gb": 340.0,
        "cpu_temp_c": 41.0,
        "pressure": "low",
        # non-scalar felter der IKKE må lække ind i meta:
        "gpus": [{"index": 0, "util_pct": 3}],
        "energy_level": "høj",
    }
    with patch.object(hardware_body, "get_hardware_state", return_value=fake_state):
        out = hardware_body.run_hardware_body_tick()

    assert out.get("status") == "ok"
    pt = _last_point()
    assert pt is not None, "intet datapunkt recorded"
    # primær skalar = cpu_pct
    assert float(pt.value) == 12.5
    meta = pt.meta or {}
    assert meta.get("cpu_pct") == 12.5
    assert meta.get("ram_pct") == 44.0
    assert meta.get("disk_free_gb") == 340.0
    assert meta.get("cpu_temp_c") == 41.0
    # KUN skalarer i meta (egress-sikkert) — ingen lister/dicts
    for k, v in meta.items():
        assert isinstance(v, (int, float, str, bool)) or v is None, f"ikke-skalar meta: {k}={v!r}"
    assert "gpus" not in meta


def test_tick_self_safe_on_error():
    with patch.object(hardware_body, "get_hardware_state", side_effect=RuntimeError("boom")):
        # må ALDRIG kaste
        out = hardware_body.run_hardware_body_tick()
    assert isinstance(out, dict)
    assert out.get("status") in ("error", "skipped")


def test_tick_accepts_cadence_kwargs():
    """internal_cadence kalder run_fn med trigger= og last_visible_at= kwargs."""
    with patch.object(hardware_body, "get_hardware_state", return_value={"cpu_pct": 5.0}):
        out = hardware_body.run_hardware_body_tick(trigger="cadence", last_visible_at="")
    assert out.get("status") == "ok"


def test_tick_skips_when_no_hardware_data():
    with patch.object(hardware_body, "get_hardware_state", return_value={}):
        out = hardware_body.run_hardware_body_tick()
    assert out.get("status") in ("skipped", "ok")
