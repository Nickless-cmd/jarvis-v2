"""Minimal smoke for process_watcher (coverage-gate + daemon_health-wiring)."""
from __future__ import annotations


def test_module_imports():
    from core.services import process_watcher as pw
    assert hasattr(pw, "start_watcher_daemon")
    assert hasattr(pw, "_watcher_loop")


# ── process_died EDGE-trigger (fix 2026-07-16: stop uendelig re-fire på død proces) ──
def _patch_procs(monkeypatch, procs):
    import core.services.process_supervisor as ps
    monkeypatch.setattr(ps, "list_processes",
                        lambda include_stopped=True: {"processes": procs})


def test_process_died_fires_once_then_silent_while_dead(monkeypatch):
    from core.services import process_watcher as pw
    cond = {"kind": "process_died", "process_name": "jarvis_bare"}
    rs: dict = {}
    # Proces set levende først → ingen fyring, men re-armes.
    _patch_procs(monkeypatch, [{"name": "jarvis_bare", "status": "running"}])
    assert pw._eval_condition(cond, rs)[0] is False
    # Overgang levende→død → fyrer ÉN gang.
    _patch_procs(monkeypatch, [{"name": "jarvis_bare", "status": "exited", "exit_code": 1}])
    assert pw._eval_condition(cond, rs)[0] is True
    # Stadig død ved næste 3 evalueringer → fyrer IKKE igen (var runaway-bugget).
    for _ in range(3):
        assert pw._eval_condition(cond, rs)[0] is False


def test_process_died_rearms_after_process_returns(monkeypatch):
    from core.services import process_watcher as pw
    cond = {"kind": "process_died", "process_name": "jarvis_bare"}
    rs: dict = {}
    _patch_procs(monkeypatch, [{"name": "jarvis_bare", "status": "running"}])
    pw._eval_condition(cond, rs)
    _patch_procs(monkeypatch, [{"name": "jarvis_bare", "status": "exited"}])
    assert pw._eval_condition(cond, rs)[0] is True     # 1. død
    _patch_procs(monkeypatch, [{"name": "jarvis_bare", "status": "running"}])
    assert pw._eval_condition(cond, rs)[0] is False    # genoplivet → re-arm
    _patch_procs(monkeypatch, [{"name": "jarvis_bare", "status": "exited"}])
    assert pw._eval_condition(cond, rs)[0] is True     # 2. død fyrer igen


def test_process_died_not_in_registry_fires_once(monkeypatch):
    from core.services import process_watcher as pw
    cond = {"kind": "process_died", "process_name": "ghost"}
    rs: dict = {}
    _patch_procs(monkeypatch, [{"name": "other", "status": "running"}])
    assert pw._eval_condition(cond, rs)[0] is True     # ikke i registry = død → fyr én gang
    assert pw._eval_condition(cond, rs)[0] is False    # forbliver væk → ingen spam


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
