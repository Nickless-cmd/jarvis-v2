"""Minimal smoke for agency_cartographer (coverage-gate + daemon_health-wiring)."""
from __future__ import annotations


def test_module_imports():
    from core.services import agency_cartographer as ac
    assert hasattr(ac, "build_cartographer_snapshot")
    assert hasattr(ac, "start_agency_cartographer_daemon")


def test_loop_error_notes_daemon_health(monkeypatch):
    # når build_cartographer_snapshot kaster, skal _loop melde til daemon_health (uden at kaste)
    import core.services.agency_cartographer as ac
    monkeypatch.setattr(ac, "build_cartographer_snapshot",
                        lambda **k: (_ for _ in ()).throw(RuntimeError("boom")))
    noted = {}
    import core.services.daemon_health as dh
    monkeypatch.setattr(dh, "note_error", lambda d, e, **k: noted.update({"daemon": d}))
    # kør én iteration ved at sætte stop efter første wait
    ac._STOP.set()  # så loopet kører kroppen 0 gange? sæt clear+stop-i-wait i stedet
    ac._STOP.clear()
    calls = {"n": 0}
    orig_wait = ac._STOP.wait
    def _wait(t):
        calls["n"] += 1
        ac._STOP.set()
        return True
    monkeypatch.setattr(ac._STOP, "wait", _wait)
    ac._loop()
    assert noted.get("daemon") == "agency_cartographer"
