"""Tests for cross-proces trace-tee — lukker hullet hvor runtime-processens fyringer
var usynlige for owner-feed'et (kun api-processen blev set)."""
from __future__ import annotations

from core.services import central_xproc as xp


def test_process_role_from_env(monkeypatch):
    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES", "0")
    assert xp.process_role() == "api"
    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES", "1")
    assert xp.process_role() == "runtime"
    monkeypatch.delenv("JARVIS_ENABLE_RUNTIME_SERVICES", raising=False)
    assert xp.process_role() == "runtime"  # default = runtime


def test_publish_then_foreign_read_roundtrip(isolated_runtime, monkeypatch):
    # simulér runtime-processen: fyr en nerve i trace-sinken, publicér, læs som 'api'
    from core.services import central_trace
    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES", "1")  # vi ER runtime
    central_trace.sink().record(central_trace.TraceRecord(
        run_id="r1", session_id="s1", cluster="autonomous", nerve="dream_run",
        kind="observe", decision="green", reason="natlig drøm"))
    xp._publish_now()  # publicér runtime-feed til shared_cache
    # api-processen læser de FREMMEDE feeds (alt der ikke er 'api')
    foreign = xp.foreign_feeds("api")
    assert any(f["nerve"] == "dream_run" and f["process"] == "runtime" for f in foreign)
    # egen rolle ekskluderes
    assert xp.foreign_feeds("runtime") == [] or all(
        f["process"] != "runtime" for f in xp.foreign_feeds("runtime"))


def test_health_published_and_readable(isolated_runtime, monkeypatch):
    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES", "1")
    xp._publish_now()
    health = xp.all_health()
    assert any(h.get("process") == "runtime" for h in health)


def test_maybe_publish_is_throttled(isolated_runtime, monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(xp, "_publish_now", lambda: calls.__setitem__("n", calls["n"] + 1))
    xp._last_publish = 0.0
    xp.maybe_publish()          # første → publicerer
    xp.maybe_publish()          # straks efter → throttlet væk
    assert calls["n"] == 1


def test_all_self_safe_on_broken_cache(monkeypatch):
    # shared_cache nede → ingen kast, tomme lister
    import core.services.shared_cache as sc
    monkeypatch.setattr(sc, "get", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    monkeypatch.setattr(sc, "set", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    assert xp.foreign_feeds("api") == []
    assert xp.all_health() == []
    xp._publish_now()  # må ikke kaste
