"""Tests for core/skills/voice/tts.py — path resolution and pure helpers."""

import os
from pathlib import Path

import pytest


# --- Constants & path resolution ---

def test_ffmpeg_path_resolved():
    """FFMPEG should resolve via shutil.which or conda fallback."""
    from core.skills.voice.tts import _FFMPEG
    assert isinstance(_FFMPEG, str)
    assert _FFMPEG.endswith("ffmpeg")
    # Path should exist at one of the expected locations
    if os.path.exists(_FFMPEG):
        assert os.access(_FFMPEG, os.X_OK)


def test_paplay_path_resolved():
    """PAPLAY should resolve via shutil.which or conda fallback."""
    from core.skills.voice.tts import _PAPLAY
    assert isinstance(_PAPLAY, str)
    assert _PAPLAY.endswith("paplay") or _PAPLAY.endswith("paplay.exe")


def test_ffplay_path_resolved():
    """FFPLAY should resolve via shutil.which or conda fallback."""
    from core.skills.voice.tts import _FFPLAY
    assert isinstance(_FFPLAY, str)
    assert _FFPLAY.endswith("ffplay") or _FFPLAY.endswith("ffplay.exe")


def test_conda_bin_path():
    """CONDA_BIN should point to expected miniconda env bin."""
    from core.skills.voice.tts import _CONDA_BIN
    assert isinstance(_CONDA_BIN, Path)
    assert "miniconda3" in str(_CONDA_BIN)


def test_edge_voices_configured():
    """EDGE_VOICES should have at least a Danish primary voice."""
    from core.skills.voice.tts import EDGE_VOICES
    assert isinstance(EDGE_VOICES, list)
    assert len(EDGE_VOICES) >= 1
    assert EDGE_VOICES[0].startswith("da-")


def test_elevenlabs_voice_id():
    """ELEVENLABS_VOICE_ID should be a non-empty string."""
    from core.skills.voice.tts import ELEVENLABS_VOICE_ID
    assert isinstance(ELEVENLABS_VOICE_ID, str)
    assert len(ELEVENLABS_VOICE_ID) > 0


# --- Helper functions ---

def test_pipewire_env_contains_runtime_dir():
    """_pipewire_env should include XDG_RUNTIME_DIR set to /run/user/<uid>."""
    from core.skills.voice.tts import _pipewire_env
    env = _pipewire_env()
    assert "XDG_RUNTIME_DIR" in env
    assert env["XDG_RUNTIME_DIR"] == f"/run/user/{os.getuid()}"


def test_pipewire_env_inherits_path():
    """_pipewire_env should inherit PATH from the current environment."""
    from core.skills.voice.tts import _pipewire_env
    env = _pipewire_env()
    assert "PATH" in env
    assert env["PATH"] == os.environ.get("PATH", "")
