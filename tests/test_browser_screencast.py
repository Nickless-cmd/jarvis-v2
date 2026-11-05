"""Tests for core/browser/screencast.py og /ws/browser-ruten."""
from __future__ import annotations

import base64
from types import SimpleNamespace

import pytest

from core.browser import screencast as sc


# ── URL- og input-validering (ren logik) ──────────────────────────────────

@pytest.mark.parametrize("url", ["file:///etc/passwd", "javascript:alert(1)", "chrome://settings", "", None, "data:text/html,x"])
def test_normaliser_url_afviser_farlige_skemaer(url):
    assert sc.normaliser_url(url) is None


def test_normaliser_url_tillader_http_og_blank():
    assert sc.normaliser_url("https://example.com/x") == "https://example.com/x"
    assert sc.normaliser_url("about:blank") == "about:blank"
    assert sc.normaliser_url("example.com") == "https://example.com"


@pytest.mark.parametrize("msg", [
    None, "x", {}, {"t": "mouse", "kind": "move", "x": "abc", "y": 1},
    {"t": "mouse", "kind": "move", "x": float("nan"), "y": 1},
    {"t": "mouse", "kind": "down", "x": 1, "y": 1, "button": "evil"},
    {"t": "mouse", "kind": "fly", "x": 1, "y": 1},
    {"t": "key", "kind": "down", "key": ""}, {"t": "key", "kind": "down", "key": "x" * 33},
    {"t": "resize", "w": 5, "h": 500}, {"t": "resize", "w": 99999, "h": 500},
    {"t": "nav", "action": "goto", "url": "file:///etc/passwd"},
    {"t": "tab", "action": "switch", "index": -1},
    {"t": "tab", "action": "new", "url": "javascript:1"},
])
def test_bygg_input_afviser_ugyldigt(msg):
    assert sc.bygg_input(msg) is None


class _Mus:
    def __init__(self): self.kald = []
    def move(self, x, y): self.kald.append(("move", x, y))
    def down(self, button="left"): self.kald.append(("down", button))
    def up(self, button="left"): self.kald.append(("up", button))
    def wheel(self, dx, dy): self.kald.append(("wheel", dx, dy))


def test_bygg_input_mus_og_tastatur_rammer_page():
    mus = _Mus()
    taster = []
    kb = SimpleNamespace(down=lambda k: taster.append(("down", k)), up=lambda k: taster.append(("up", k)),
                         insert_text=lambda t: taster.append(("text", t)))
    ctx = SimpleNamespace(page=SimpleNamespace(mouse=mus, keyboard=kb))
    sc.bygg_input({"t": "mouse", "kind": "down", "x": 10, "y": 20, "button": "right"})(ctx)
    sc.bygg_input({"t": "mouse", "kind": "wheel", "x": 1, "y": 2, "dx": 0, "dy": 120})(ctx)
    sc.bygg_input({"t": "key", "kind": "down", "key": "Enter"})(ctx)
    sc.bygg_input({"t": "text", "text": "hej"})(ctx)
    assert ("down", "right") in mus.kald and ("wheel", 0.0, 120.0) in mus.kald
    assert ("down", "Enter") in taster and ("text", "hej") in taster


# ── Frame-haandtering uden rigtig browser ──────────────────────────────────

def test_on_frame_lagger_jpeg_i_koe_og_noterer_ack():
    s = sc.ScreencastSession(max_queue=2)
    jpeg = b"\xff\xd8\xff\xd9"
    s._on_frame({"data": base64.b64encode(jpeg).decode(), "sessionId": 7})
    assert s.next_frame(0.1) == jpeg
    assert s._acks == [7]


def test_koeen_smider_aeldste_frame_naar_den_er_fuld():
    s = sc.ScreencastSession(max_queue=2)
    for i in range(4):
        s._on_frame({"data": base64.b64encode(bytes([i + 1])).decode(), "sessionId": i})
    assert [s.next_frame(0.05), s.next_frame(0.05)] == [b"\x03", b"\x04"]


# ── Ruten: auth ────────────────────────────────────────────────────────────

def _klient():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.api.jarvis_api.routes import browser_stream
    app = FastAPI()
    app.include_router(browser_stream.router)
    return TestClient(app)


def test_ruten_afviser_uden_token_naar_auth_kraeves(monkeypatch):
    from starlette.websockets import WebSocketDisconnect
    from core.runtime import ws_auth
    monkeypatch.setattr(ws_auth, "kraeves_auth", lambda: True)
    with pytest.raises(WebSocketDisconnect) as e:
        with _klient().websocket_connect("/ws/browser"):
            pass
    assert e.value.code == 1008


def test_ruten_afviser_ikke_ejer(monkeypatch):
    from starlette.websockets import WebSocketDisconnect
    from core.runtime import ws_auth
    monkeypatch.setattr(ws_auth, "verificer", lambda t: {"role": "member"})
    monkeypatch.setattr(ws_auth, "kraeves_auth", lambda: True)
    with pytest.raises(WebSocketDisconnect) as e:
        with _klient().websocket_connect("/ws/browser", subprotocols=[ws_auth.SUBPROTOKOL, "t"]):
            pass
    assert e.value.code == 1008


# ── Ægte bevis: en screencast-frame kommer ud af en rigtig Chromium ────────

def test_rigtig_screencast_leverer_mindst_en_jpeg_frame():
    pytest.importorskip("playwright")
    from core.browser import playwright_session as ps

    s = sc.ScreencastSession()
    try:
        try:
            s.start()
        except Exception as exc:  # ingen brugbar browser i miljoeet
            pytest.skip(f"ingen browser: {exc}")
        ps.run_in_playwright(
            lambda c: c.page.goto("data:text/html,<h1 style='color:red'>hej</h1>"), timeout=30.0)
        frame = None
        for _ in range(40):
            s.pump()
            frame = s.next_frame(0.1)
            if frame:
                break
        assert frame is not None, "ingen screencast-frame modtaget"
        assert frame[:2] == b"\xff\xd8"  # JPEG SOI
    finally:
        s.stop()
        ps.stop_browser_session()
