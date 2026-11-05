"""Enhedstests for core/tools/desktop_tools.py.

Værktøjet er ét `jarvis_desktop` med ni handlinger over den DELTE X-session.
Testene bruger en falsk session: de beviser oversættelsen og fejlformen, ikke
at X virker. Den ægte skærm er verificeret mod en kørende Xvfb (5/11-2026).
"""
from __future__ import annotations

import os

from core.tools import desktop_tools as dt


class FalskSession:
    bredde = 1280
    hoejde = 800
    display = ":99"

    def __init__(self) -> None:
        self.kald: list[dict] = []
        self.fejl: dict | None = None

    def cursor(self):
        return self.fejl or {"status": "ok", "x": 10, "y": 20}

    def frame(self):
        return self.fejl or b"\xff\xd8billede"

    def zoom(self, x, y, w, h, faktor=2):
        self.kald.append({"zoom": (x, y, w, h, faktor)})
        return self.fejl or b"\xff\xd8zoom"

    def wait(self, timeout_ms=1500):
        self.kald.append({"wait": timeout_ms})
        return self.fejl or {"status": "ok", "changed": True, "ms": 42}

    def input(self, msg):
        self.kald.append({"input": msg})
        return self.fejl or {"status": "ok"}


def _med(monkeypatch, session: FalskSession) -> FalskSession:
    monkeypatch.setattr(dt, "_session", lambda: session)
    return session


def test_ukendt_action_afvises(monkeypatch):
    _med(monkeypatch, FalskSession())
    r = dt._exec_jarvis_desktop({"action": "teleport"})
    assert r["status"] == "error"
    assert "action" in r["error"]


def test_manglende_action_afvises(monkeypatch):
    _med(monkeypatch, FalskSession())
    assert dt._exec_jarvis_desktop({})["status"] == "error"


def test_status_svarer_med_geometri_og_markor(monkeypatch):
    _med(monkeypatch, FalskSession())
    r = dt._exec_jarvis_desktop({"action": "status"})
    assert r["status"] == "ok"
    assert r["result"]["bredde"] == 1280
    assert r["result"]["markor"] == {"x": 10, "y": 20}


def test_cursor_position_videresendes(monkeypatch):
    _med(monkeypatch, FalskSession())
    r = dt._exec_jarvis_desktop({"action": "cursor_position"})
    assert r["status"] == "ok" and r["result"] == {"status": "ok", "x": 10, "y": 20}


def test_screenshot_svarer_med_en_sti_der_findes(monkeypatch):
    """Et skærmbillede jeg ikke kan SE er ikke et skærmbillede — kun data."""
    _med(monkeypatch, FalskSession())
    r = dt._exec_jarvis_desktop({"action": "screenshot"})
    assert r["status"] == "ok"
    sti = r["result"]["path"]
    assert sti.endswith(".jpg") and os.path.exists(sti)
    with open(sti, "rb") as f:
        assert f.read().startswith(b"\xff\xd8")
    assert r["result"]["bytes"] == len(b"\xff\xd8billede")


def test_zoom_giver_sti_og_videresender_udsnittet(monkeypatch):
    s = _med(monkeypatch, FalskSession())
    r = dt._exec_jarvis_desktop({"action": "zoom", "x": 5, "y": 6, "width": 300, "height": 200, "faktor": 3})
    assert r["status"] == "ok"
    assert r["result"]["path"].endswith(".jpg")
    assert s.kald[0]["zoom"] == (5, 6, 300, 200, 3)


def test_klik_sender_ned_og_op(monkeypatch):
    """Uden «up» hænger knappen nede, og næste klik bliver et træk."""
    s = _med(monkeypatch, FalskSession())
    r = dt._exec_jarvis_desktop({"action": "click", "x": 100, "y": 200, "button": "right"})
    assert r["status"] == "ok"
    kald = [k["input"] for k in s.kald if "input" in k]
    assert len(kald) == 2
    assert kald[0]["kind"] == "down" and kald[0]["button"] == "right"
    assert kald[1]["kind"] == "up"
    assert kald[0]["x"] == 100 and kald[0]["y"] == 200


def test_move_sender_kun_flyt(monkeypatch):
    s = _med(monkeypatch, FalskSession())
    dt._exec_jarvis_desktop({"action": "move", "x": 1, "y": 2})
    kald = [k["input"] for k in s.kald if "input" in k]
    assert kald == [{"t": "mouse", "kind": "move", "x": 1, "y": 2}]


def test_type_og_key_kraever_argument(monkeypatch):
    _med(monkeypatch, FalskSession())
    assert dt._exec_jarvis_desktop({"action": "type"})["status"] == "error"
    assert dt._exec_jarvis_desktop({"action": "key"})["status"] == "error"


def test_key_sender_ned_og_op(monkeypatch):
    s = _med(monkeypatch, FalskSession())
    dt._exec_jarvis_desktop({"action": "key", "key": "Return"})
    kald = [k["input"] for k in s.kald if "input" in k]
    assert [k["kind"] for k in kald] == ["down", "up"]
    assert all(k["key"] == "Return" for k in kald)


def test_wait_videresender_timeout(monkeypatch):
    s = _med(monkeypatch, FalskSession())
    r = dt._exec_jarvis_desktop({"action": "wait", "timeout_ms": 900})
    assert r["status"] == "ok" and r["result"]["changed"] is True
    assert s.kald[0]["wait"] == 900


def test_fejl_fra_sessionen_bliver_til_fejlsvar(monkeypatch):
    s = FalskSession()
    s.fejl = {"status": "error", "code": "DESKTOP_UNAVAILABLE", "error": "desktoppen er ikke startet"}
    _med(monkeypatch, s)
    for action in ("cursor_position", "wait", "screenshot", "zoom", "move", "click"):
        r = dt._exec_jarvis_desktop({"action": action, "x": 1, "y": 1, "width": 10, "height": 10})
        assert r["status"] == "error", action
        assert r["code"] == "DESKTOP_UNAVAILABLE"


def test_doed_session_giver_fejlsvar_frem_for_at_kaste(monkeypatch):
    def eksploder():
        raise RuntimeError("desktoppen kunne ikke startes")

    monkeypatch.setattr(dt, "_session", eksploder)
    r = dt._exec_jarvis_desktop({"action": "status"})
    assert r["status"] == "error"
    assert "startes" in r["error"]


def test_vaerktoejet_er_registreret_for_modellen():
    """Et værktøj der ikke staar i scopingen findes reelt ikke."""
    from core.tools.simple_tools import _TOOL_HANDLERS
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS
    from core.tools import tool_scoping as ts

    assert "jarvis_desktop" in _TOOL_HANDLERS
    assert "jarvis_desktop" in [d["function"]["name"] for d in TOOL_DEFINITIONS]
    assert "jarvis_desktop" in ts.CHAT_MODE_TOOLS_BASE
    assert "jarvis_desktop" in ts.CODE_MODE_TOOLS_BASE


def test_definitionen_annoncerer_de_tre_nye_medlemmer():
    spec = dt.DESKTOP_TOOL_DEFINITIONS[0]["function"]
    enum = spec["parameters"]["properties"]["action"]["enum"]
    for navn in ("wait", "zoom", "cursor_position"):
        assert navn in enum, navn
