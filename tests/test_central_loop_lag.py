"""Loop-lag-monitor ("uret"): måler event-loop-sultning der skærer streams."""
from __future__ import annotations

from core.services import central_loop_lag as L


def test_record_updates_current_and_peak():
    L._SAMPLES.clear()
    L._STATE.update({"current_ms": 0.0, "peak_ms": 0.0, "peak_ts": 0.0})
    L._record(120.0)
    assert L.current_lag_ms() == 120.0
    L._record(40.0)
    assert L.current_lag_ms() == 40.0
    # recent_peak beholder toppen i vinduet
    assert L.recent_peak_ms(60.0) >= 120.0


def test_surface_shape():
    s = L.build_loop_lag_surface()
    assert set(s) >= {"current_lag_ms", "recent_peak_ms", "spike_threshold_ms"}


def test_self_safe_on_garbage():
    # Må aldrig kaste
    assert L.recent_peak_ms(0.0) >= 0.0
    assert L.current_lag_ms() >= 0.0
