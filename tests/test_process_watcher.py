"""Minimal smoke for process_watcher (coverage-gate + daemon_health-wiring)."""
from __future__ import annotations


def test_module_imports():
    from core.services import process_watcher as pw
    assert hasattr(pw, "start_watcher_daemon")
    assert hasattr(pw, "_watcher_loop")


def test_watcher_loop_error_notes_daemon_health(monkeypatch):
    import core.services.process_watcher as pw
    monkeypatch.setattr(pw, "_evaluate_watches_once",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    noted = {}
    import core.services.daemon_health as dh
    monkeypatch.setattr(dh, "note_error", lambda d, e, **k: noted.update({"daemon": d}))
    def _wait(t):
        pw._DAEMON_STOP.set()
        return True
    pw._DAEMON_STOP.clear()
    monkeypatch.setattr(pw._DAEMON_STOP, "wait", _wait)
    pw._watcher_loop()
    assert noted.get("daemon") == "process_watcher"
