"""Thin coverage test for core.tools.mic_listen_tool.

Import-smoke + assert the egress-free Central observation (record_private) is
wired at the perception point. Does NOT capture audio or hit the network.
"""
from __future__ import annotations

import inspect

import numpy as np


def test_import_smoke():
    import core.tools.mic_listen_tool as mod
    assert hasattr(mod, "listen_and_transcribe")
    assert hasattr(mod, "MIC_LISTEN_TOOL_DEFINITIONS")


def test_source_wires_record_private():
    import core.tools.mic_listen_tool as mod
    src = inspect.getsource(mod)
    assert "record_private" in src


# ── Enhedsvalg (målt 16/10-2026) ──────────────────────────────────────
#
# Baggrund: værktøjet pegede på en PipeWire-kilde (`alsa_input.usb-NOS_X500_…`)
# gennem `parec`. Begge dele var døde — enheden findes ikke, og der kører ingen
# lyd-daemon i containeren. Fallback'en kaldte `sd.rec()` uden enhed og ramte
# ALSA `default`, som også er tavs. Resultatet var et værktøj der meldte
# succes mens det optog digital stilhed. Disse tests låser at enheden nu
# VÆLGES, og at valget ikke kan falde tilbage til stilhed uden at sige det.

class _FakeSD:
    """Minimal sounddevice-attrap: kun det `_pick_input_device` rører."""

    def __init__(self, devices, default_in=20):
        self._devices = devices
        self.default = type("D", (), {"device": (default_in, 0)})()

    def query_devices(self):
        return self._devices


def _dev(name, channels=1, rate=44100):
    return {"name": name, "max_input_channels": channels, "default_samplerate": rate}


def test_enhed_vaelges_ved_navn_ikke_indeks():
    """Indekser flytter sig når hardware skiftes — navnet gør ikke."""
    from core.tools import mic_listen_tool as m
    sd = _FakeSD([
        _dev("HDA Intel PCH: ALCS1200A Analog (hw:0,0)", channels=2),
        _dev("BUA-200M: USB Audio (hw:4,0)", rate=16000),
        _dev("PRO: USB Audio (hw:5,0)"),
    ])
    idx, name, rate = m._pick_input_device(sd)
    assert "PRO: USB Audio" in name, "Logitech PRO er den eneste målt med signal"
    assert idx == 2
    assert rate == 44100, "native rate skal følge med, ikke antages at være 16k"


def test_enhed_uden_indgang_springes_over():
    """HDMI-kort har 0 input-kanaler og må aldrig vælges."""
    from core.tools import mic_listen_tool as m
    sd = _FakeSD([
        _dev("HDA NVidia: HDMI 0 (hw:1,3)", channels=0),
        _dev("PRO: USB Audio (hw:5,0)"),
    ])
    idx, name, _ = m._pick_input_device(sd)
    assert idx == 1 and "PRO" in name


def test_ingen_brugbar_enhed_giver_none():
    """Ingen kandidat → None, så kalderen kan fejle HØJT i stedet for tavst."""
    from core.tools import mic_listen_tool as m
    sd = _FakeSD([_dev("HDA NVidia: HDMI 0 (hw:1,3)", channels=0)], default_in=0)
    idx, name, _ = m._pick_input_device(sd)
    assert idx is None and name == ""


def test_env_override_vinder(monkeypatch):
    """JARVIS_MIC_DEVICE skal kunne tvinge en anden enhed igennem."""
    from core.tools import mic_listen_tool as m
    monkeypatch.setenv(m._MIC_DEVICE_ENV, "BUA-200M")
    sd = _FakeSD([
        _dev("PRO: USB Audio (hw:5,0)"),
        _dev("BUA-200M: USB Audio (hw:4,0)", rate=16000),
    ])
    idx, name, rate = m._pick_input_device(sd)
    assert "BUA-200M" in name and idx == 1 and rate == 16000


def test_resampling_bevarer_laengde_og_dtype():
    """44,1 kHz → 16 kHz: længden skal skaleres, dtype forblive int16."""
    from core.tools import mic_listen_tool as m
    src = (np.sin(np.linspace(0, 100, 44100)) * 8000).astype(np.int16)
    out = m._resample_to_16k(src, 44100)
    assert out.dtype == np.int16
    assert abs(len(out) - 16000) <= 2, f"forventet ~16000 samples, fik {len(out)}"


def test_resampling_er_no_op_ved_16k():
    """Er enheden allerede 16 kHz må der ikke røres ved signalet."""
    from core.tools import mic_listen_tool as m
    src = np.arange(16000, dtype=np.int16)
    out = m._resample_to_16k(src, 16000)
    assert out is src


def test_parec_er_fjernet_fra_capture_vejen():
    """`parec` kræver en daemon der ikke findes i containeren.

    Den må ikke snige sig ind igen som 'første forsøg' — den kunne kun fejle,
    og dens tilstedeværelse fik fejlen til at se ud som et enhedsproblem.
    """
    import core.tools.mic_listen_tool as mod
    src = inspect.getsource(mod)
    assert "_capture_parec" not in src
    assert "subprocess" not in src


# ── Koblingen: valget skal FAKTISK bruges ────────────────────────────
#
# Målt 16/10-2026: de første syv tests bestod OGSÅ med den gamle adfærd
# genindført. De testede `_pick_input_device` isoleret, men ikke at
# `_capture_sounddevice` bruger resultatet. En test der dækker funktionen men
# ikke koblingen fanger ikke den fejl den blev skrevet for. Denne test lukker
# hullet: den fanger hvad der reelt sendes til `sd.rec`.

class _RecorderSD:
    """Attrap der registrerer kaldet til `sd.rec` i stedet for at optage."""

    def __init__(self, devices):
        self._devices = devices
        self.default = type("D", (), {"device": (20, 0)})()
        self.rec_kwargs: dict = {}

    def query_devices(self):
        return self._devices

    def rec(self, frames, **kw):
        self.rec_kwargs = {"frames": frames, **kw}
        return np.zeros((frames, 1), dtype=np.int16)


def test_capture_sender_valgt_enhed_og_native_rate(monkeypatch):
    """Det valgte indeks og den native rate skal nå helt frem til `sd.rec`."""
    import sys
    import core.tools.mic_listen_tool as m

    sd = _RecorderSD([
        _dev("HDA Intel PCH: ALCS1200A Analog (hw:0,0)", channels=2),
        _dev("PRO: USB Audio (hw:5,0)", rate=44100),
    ])
    monkeypatch.setitem(sys.modules, "sounddevice", sd)

    raw, desc = m._capture_sounddevice(2.0)

    assert raw is not None, f"capture fejlede: {desc}"
    assert sd.rec_kwargs.get("device") == 1, "det valgte indeks skal sendes videre"
    assert sd.rec_kwargs.get("samplerate") == 44100, "native rate, ikke 16k"
    assert sd.rec_kwargs.get("frames") == 2 * 44100, "frames skal regnes ved native rate"
    assert "PRO" in desc and "44100" in desc, "beskrivelsen skal navngive enheden"


def test_capture_uden_enhed_fejler_hoejt(monkeypatch):
    """Ingen brugbar enhed → None + grund. Aldrig tavs 'succes'."""
    import sys
    import core.tools.mic_listen_tool as m

    sd = _RecorderSD([_dev("HDA NVidia: HDMI 0 (hw:1,3)", channels=0)])
    monkeypatch.setitem(sys.modules, "sounddevice", sd)

    raw, desc = m._capture_sounddevice(1.0)
    assert raw is None
    assert desc == "no-input-device"
    assert sd.rec_kwargs == {}, "der må ikke optages når der ikke er en enhed"
