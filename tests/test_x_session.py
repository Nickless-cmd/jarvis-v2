"""Enhedstests for core/desktop/x_session.py.

Dækker den rene input-oversættelse (ingen X nødvendig), afvisning af farligt
input, og at manglende X-pakker giver en struktureret fejl i stedet for en
exception. Den ægte X-session er verificeret manuelt mod en kørende Xvfb.
"""
from __future__ import annotations

from core.desktop import x_session as xs


def test_mus_flyt_og_klik_oversaettes():
    assert xs.bygg_input({"t": "mouse", "kind": "move", "x": 10, "y": 20}) == [["mousemove", "10", "20"]]
    assert xs.bygg_input({"t": "mouse", "kind": "down", "x": 1, "y": 2, "button": "right"}) == [
        ["mousemove", "1", "2"], ["mousedown", "3"]]
    assert xs.bygg_input({"t": "mouse", "kind": "up", "x": 1, "y": 2}) == [
        ["mousemove", "1", "2"], ["mouseup", "1"]]


def test_koordinater_klemmes():
    r = xs.bygg_input({"t": "mouse", "kind": "move", "x": 99999, "y": -5})
    assert r == [["mousemove", str(xs.BREDDE - 1), "0"]]


def test_hjul_retning():
    assert xs.bygg_input({"t": "mouse", "kind": "wheel", "x": 0, "y": 0, "dy": 50})[1] == ["click", "5"]
    assert xs.bygg_input({"t": "mouse", "kind": "wheel", "x": 0, "y": 0, "dy": -50})[1] == ["click", "4"]
    assert xs.bygg_input({"t": "mouse", "kind": "wheel", "x": 0, "y": 0, "dy": 0}) is None


def test_taster_oversaettes():
    assert xs.bygg_input({"t": "key", "kind": "down", "key": "Enter"}) == [["keydown", "Return"]]
    assert xs.bygg_input({"t": "key", "kind": "up", "key": "a"}) == [["keyup", "a"]]
    assert xs.bygg_input({"t": "key", "kind": "down", "key": "ArrowLeft"}) == [["keydown", "Left"]]


def test_tekst_bruger_dobbelt_bindestreg_og_fjerner_kontroltegn():
    r = xs.bygg_input({"t": "text", "text": "-rf\x00\x1b"})
    assert r == [["type", "--delay", "0", "--", "-rf"]]


def test_farlige_og_ugyldige_input_afvises():
    for d in (
        None, "tekst", [], {}, {"t": "nav", "action": "goto", "url": "x"},
        {"t": "resize", "w": 1, "h": 1}, {"t": "tab", "action": "new"},
        {"t": "mouse", "kind": "move", "x": "a", "y": 1},
        {"t": "mouse", "kind": "move", "x": float("nan"), "y": 1},
        {"t": "mouse", "kind": "move", "x": True, "y": 1},
        {"t": "mouse", "kind": "drop", "x": 1, "y": 1},
        {"t": "mouse", "kind": "down", "x": 1, "y": 1, "button": "9"},
        {"t": "key", "kind": "down", "key": "a; rm -rf /"},
        {"t": "key", "kind": "down", "key": "--help"},
        {"t": "key", "kind": "hold", "key": "a"},
        {"t": "key", "kind": "down", "key": 5},
        {"t": "text", "text": ""},
        {"t": "text", "text": "x" * 10_000},
        {"t": "text", "text": "\x00\x01"},
    ):
        assert xs.bygg_input(d) is None, d


def test_manglende_pakker_giver_struktureret_fejl(monkeypatch):
    monkeypatch.setattr(xs.shutil, "which", lambda _n: None)
    assert xs.mangler_pakker()
    res = xs.XSession().start()
    assert res["status"] == "error"
    assert res["code"] == "DESKTOP_UNAVAILABLE"
    assert res["error"]


def test_frame_og_input_uden_start_kaster_ikke():
    s = xs.XSession()
    f = s.frame()
    assert isinstance(f, dict) and f["code"] == "DESKTOP_UNAVAILABLE"
    i = s.input({"t": "key", "kind": "down", "key": "a"})
    assert i["code"] == "DESKTOP_UNAVAILABLE"


def test_ugyldigt_input_paa_koerende_session_giver_fejl_dict(monkeypatch):
    s = xs.XSession()
    s._kor = True
    kaldt = []
    monkeypatch.setattr(xs.subprocess, "run", lambda *a, **k: kaldt.append(a))
    assert s.input({"t": "key", "kind": "down", "key": "a;b"})["code"] == "INVALID_INPUT"
    assert kaldt == []
    assert s.input({"t": "key", "kind": "down", "key": "a"})["status"] == "ok"
    assert kaldt[0][0] == ["xdotool", "keydown", "a"]


def test_conda_stier_fjernes_fra_x_miljoeet(monkeypatch):
    """Conda-miljoeets libEGL draeber Xvfb med EGL-backtrace (exit 134).

    X-vaerktoejerne er system-binaerer: de skal ikke se condas biblioteker.
    """
    monkeypatch.setenv("LD_LIBRARY_PATH", "/home/bs/miniconda3/envs/ai/lib:/usr/local/lib")
    env = xs.XSession()._env()
    assert "miniconda" not in env.get("LD_LIBRARY_PATH", "")
    assert "/usr/local/lib" in env.get("LD_LIBRARY_PATH", "")
    assert env["DISPLAY"] == xs.DISPLAY


def test_kun_conda_sti_fjerner_variablen_helt(monkeypatch):
    monkeypatch.setenv("LD_LIBRARY_PATH", "/home/bs/miniconda3/envs/ai/lib")
    env = xs.XSession()._env()
    assert "LD_LIBRARY_PATH" not in env
