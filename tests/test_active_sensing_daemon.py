"""Tests for the 2026-09-13 Sansernes-Arkiv fixes.

Three fixes, all rooted in the same 31-hour silent archive outage
(11. sep 23:00 → 13. sep ~08:00Z, 99 'database is locked' errors):

1. ``_sense_audio`` never archived — it delegated to ambient_sound's tick and
   relied on that daemon's side-effect. Now it captures its own metadata sample
   and writes via ``record_audio``.
2. Silent ``except Exception: pass`` in ``_sense_atmosphere`` / ``_sense_mixed``
   (and ``logger.debug`` in ambient's ``_archive_sensory``) swallowed the real
   failure. Now logged at WARNING so the next outage is visible.
3. ``ambient_sound`` was not in the daemon registry → ``is_enabled`` returned
   True for the unknown name, the tick-site ran ungated, and
   ``record_daemon_tick`` was a no-op (so it looked like it never ran). Now
   registered → gated, visible and toggleable.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime


def _now() -> datetime:
    return datetime.now(UTC)


# ── Fix 1: _sense_audio archives its own impression ──────────────────────────


def test_sense_audio_archives_to_sensory_archive(monkeypatch):
    import core.services.active_sensing_daemon as asd
    import core.services.sensory_archive as sa

    monkeypatch.setattr(
        "core.services.ambient_sound_daemon._capture_sample",
        lambda **kw: ("talk", 0.021, 0.011, None),
    )

    captured: dict = {}

    def fake_record_audio(content, **kw):
        captured["content"] = content
        captured["metadata"] = kw.get("metadata")
        return {"id": "x", "modality": "audio"}

    monkeypatch.setattr(sa, "record_audio", fake_record_audio)

    result = asd._sense_audio({}, _now())

    assert result["reason"] == "audio_talk"
    assert captured["content"].startswith("Jeg lyttede til rummet")
    assert captured["metadata"]["source"] == "active_sensing_daemon"
    assert captured["metadata"]["category"] == "talk"


def test_sense_audio_no_device_returns_cleanly(monkeypatch):
    import core.services.active_sensing_daemon as asd

    monkeypatch.setattr(
        "core.services.ambient_sound_daemon._capture_sample",
        lambda **kw: (None, 0.0, 0.0, None),
    )
    result = asd._sense_audio({}, _now())
    assert result["reason"] == "audio_no_device"


def test_sense_audio_archive_failure_is_logged_not_swallowed(monkeypatch, caplog):
    """The sensing still succeeds, but the archive failure must be VISIBLE."""
    import core.services.active_sensing_daemon as asd
    import core.services.sensory_archive as sa

    monkeypatch.setattr(
        "core.services.ambient_sound_daemon._capture_sample",
        lambda **kw: ("silence", 0.0, 0.0, None),
    )

    def boom(*_a, **_k):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(sa, "record_audio", boom)

    with caplog.at_level(logging.WARNING, logger="core.services.active_sensing_daemon"):
        result = asd._sense_audio({}, _now())

    assert result["reason"] == "audio_silence"
    assert any("audio archive failed" in r.message for r in caplog.records)


# ── Fix 2: silent excepts now warn ───────────────────────────────────────────


def test_sense_atmosphere_archive_failure_is_logged(monkeypatch, caplog):
    import core.services.active_sensing_daemon as asd
    import core.services.sensory_archive as sa

    monkeypatch.setattr(
        "core.services.visual_memory.look_around_now",
        lambda **kw: {"status": "captured", "description": "et roligt, køligt rum"},
    )

    def boom(*_a, **_k):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(sa, "record_atmosphere", boom)

    with caplog.at_level(logging.WARNING, logger="core.services.active_sensing_daemon"):
        result = asd._sense_atmosphere({}, _now())

    assert result["reason"] == "atmosphere_captured"
    assert any("atmosphere archive failed" in r.message for r in caplog.records)


def test_sense_mixed_archive_failure_is_logged(monkeypatch, caplog):
    import core.services.active_sensing_daemon as asd
    import core.services.sensory_archive as sa

    monkeypatch.setattr(
        "core.services.visual_memory.look_around_now",
        lambda **kw: {"status": "captured", "description": "et roligt rum"},
    )
    monkeypatch.setattr(
        "core.services.ambient_sound_daemon._capture_sample",
        lambda **kw: ("silence", 0.0, 0.0, None),
    )

    def boom(*_a, **_k):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(sa, "record_mixed", boom)

    with caplog.at_level(logging.WARNING, logger="core.services.active_sensing_daemon"):
        result = asd._sense_mixed({}, _now())

    assert result["reason"] == "mixed_captured"
    assert any("mixed archive failed" in r.message for r in caplog.records)


# ── Fix 3: ambient_sound is a first-class registered daemon ──────────────────


def test_ambient_sound_is_registered(monkeypatch):
    from core.services import daemon_manager as dm

    assert "ambient_sound" in dm._REGISTRY
    entry = dm._REGISTRY["ambient_sound"]
    assert entry["module"] == "core.services.ambient_sound_daemon"
    assert entry["default_enabled"] is True


def test_ambient_sound_is_toggleable(monkeypatch, isolated_runtime):
    """Before registration set_daemon_enabled('ambient_sound') raised
    (unknown name) and is_enabled() fell back to True for any unknown name."""
    from core.services import daemon_manager as dm

    try:
        dm.set_daemon_enabled("ambient_sound", False)
        assert dm.is_enabled("ambient_sound") is False
        dm.set_daemon_enabled("ambient_sound", True)
        assert dm.is_enabled("ambient_sound") is True
    finally:
        dm.set_daemon_enabled("ambient_sound", True)


def test_ambient_record_daemon_tick_now_persists(monkeypatch, isolated_runtime):
    """record_daemon_tick was a no-op for the unregistered name; now it writes."""
    from core.services import daemon_manager as dm

    dm.record_daemon_tick("ambient_sound", {"generated": True, "category": "silence"})
    entry = dm._get_daemon_state("ambient_sound")
    assert entry.get("last_run_at")
    assert "generated" in str(entry.get("last_result_summary", ""))


# ── Fix 1 helper: save_wav=False skips the temp-WAV write ────────────────────


def test_capture_sample_save_wav_false_skips_wav(monkeypatch):
    import core.services.ambient_sound_daemon as asd

    called = {"save": 0}

    class _FakeSamples:
        def flatten(self):
            return self

        def mean(self):
            return 0.0

        def std(self):
            return 0.0

        def max(self):
            return 0.0

    import sys
    import types

    fake_np = types.ModuleType("numpy")
    fake_np.abs = lambda x: x  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "numpy", fake_np)

    fake_sd = types.ModuleType("sounddevice")
    fake_sd.rec = lambda *a, **k: _FakeSamples()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sd)

    monkeypatch.setattr(asd, "_save_wav", lambda s: called.__setitem__("save", called["save"] + 1) or "/tmp/x.wav")

    asd._capture_sample(save_wav=False)
    assert called["save"] == 0, "save_wav=False must not write a temp WAV"
