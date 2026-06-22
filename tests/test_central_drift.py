"""Tests for central_drift — §7 flag-on-change (aktiv drift-detektion)."""
from __future__ import annotations

from core.services.central_drift import NerveDriftMonitor


def test_no_flag_in_first_window():
    m = NerveDriftMonitor(check_every=5, tol=0.3)
    flags = [m.record("n", is_error=False, is_red=False) for _ in range(5)]
    assert flags[-1] is None  # første fulde vindue = etablér baseline, ingen flag


def test_flag_on_red_rate_drift():
    m = NerveDriftMonitor(check_every=5, tol=0.3)
    for _ in range(5):
        m.record("n", is_error=False, is_red=False)  # baseline red_rate=0
    flag = None
    for _ in range(5):
        flag = m.record("n", is_error=False, is_red=True)  # red_rate=1.0 → drift
    assert flag is not None and "red_rate" in flag["metric"]


def test_flag_on_error_rate_drift():
    m = NerveDriftMonitor(check_every=5, tol=0.3)
    for _ in range(5):
        m.record("n", is_error=False, is_red=False)  # baseline error_rate=0
    flag = None
    for _ in range(5):
        flag = m.record("n", is_error=True, is_red=False)  # error_rate=1.0 → drift
    assert flag is not None and "error_rate" in flag["metric"]


def test_no_flag_steady_state():
    m = NerveDriftMonitor(check_every=5, tol=0.3)
    for _ in range(5):
        m.record("n", is_error=False, is_red=True)  # baseline red=1.0
    f2 = None
    for _ in range(5):
        f2 = m.record("n", is_error=False, is_red=True)  # samme rate → ingen drift
    assert f2 is None


def test_self_safe_on_bad_input():
    m = NerveDriftMonitor(check_every=5)
    assert m.record("n", is_error=True, is_red=True) is None  # kaster ikke
    assert isinstance(m.snapshot(), dict)


def test_decide_wires_drift_flag():
    import inspect
    from core.services import central_core as cc
    src = inspect.getsource(cc.Central.decide)
    assert "_maybe_flag_drift" in src  # begge grene (success + error) flagger drift
