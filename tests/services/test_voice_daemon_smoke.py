"""Smoke test for core.services.voice_daemon.

Starting the daemon with voice disabled should be a safe no-op rather than
spawning a worker thread.
"""

from core.services import voice_daemon


def test_start_voice_daemon_is_noop_when_voice_disabled(monkeypatch) -> None:
    monkeypatch.delenv("JARVIS_VOICE_ENABLED", raising=False)
    monkeypatch.setattr(voice_daemon, "_thread", None)
    voice_daemon._stop_event.set()

    voice_daemon.start_voice_daemon()

    assert voice_daemon._thread is None
