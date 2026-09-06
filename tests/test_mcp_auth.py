"""MCP-auth: tokens, fornyelse og rækkefølgen i resolve_headers.

Tokens er hemmeligheder. Testene her handler mest om at de IKKE lækker ud i
en header de ikke hører til, og at en config kan deles uden at bære et token.
"""
import time

import pytest

from core.services import mcp_auth


@pytest.fixture(autouse=True)
def _egen_fil(tmp_path, monkeypatch):
    monkeypatch.setattr(mcp_auth, "TOKENS_PATH", tmp_path / "mcp_tokens.json")
    yield


def test_gemt_token_kan_laeses_igen():
    mcp_auth.set_token("s", access_token="abc", expires_in=3600)
    rec = mcp_auth.get_token("s")
    assert rec["access_token"] == "abc"
    assert rec["expires_at"] > time.time()


def test_filen_er_kun_laesbar_for_ejeren():
    import os
    mcp_auth.set_token("s", access_token="abc")
    assert oct(os.stat(mcp_auth.TOKENS_PATH).st_mode)[-3:] == "600"


def test_ukendt_server_har_intet_token():
    assert mcp_auth.get_token("findes-ikke") is None


def test_needs_refresh_kun_naar_der_er_udloeb():
    mcp_auth.set_token("uden", access_token="a")
    assert mcp_auth.needs_refresh("uden") is False
    mcp_auth.set_token("snart", access_token="a", expires_in=1)
    assert mcp_auth.needs_refresh("snart") is True, "margin skal fornye FØR udløb"
    mcp_auth.set_token("senere", access_token="a", expires_in=9999)
    assert mcp_auth.needs_refresh("senere") is False


def test_refresh_uden_refresh_token_gaar_ikke_i_gang():
    mcp_auth.set_token("s", access_token="a")
    assert mcp_auth.refresh("s") is False


def test_eksplicit_header_vinder_over_token_lageret():
    mcp_auth.set_token("s", access_token="fra-lageret")
    h = mcp_auth.resolve_headers("s", {"headers": {"Authorization": "Bearer egen"}})
    assert h["Authorization"] == "Bearer egen"


def test_bearer_fra_config_bruges():
    h = mcp_auth.resolve_headers("s", {"auth": {"type": "bearer", "token": "t1"}})
    assert h["Authorization"] == "Bearer t1"


def test_env_udfoldes_saa_en_config_kan_deles_uden_token(monkeypatch):
    monkeypatch.setenv("MIN_MCP_NOEGLE", "hemmelig")
    h = mcp_auth.resolve_headers("s", {"auth": {"type": "bearer",
                                                "token": "${MIN_MCP_NOEGLE}"}})
    assert h["Authorization"] == "Bearer hemmelig"


def test_manglende_env_giver_ingen_authorization():
    """Hellere ingen header end 'Bearer ' med tom vaerdi."""
    h = mcp_auth.resolve_headers("s", {"auth": {"type": "bearer",
                                                "token": "${FINDES_IKKE_XYZ}"}})
    assert "Authorization" not in h


def test_uden_token_og_uden_config_er_der_ingen_headers():
    assert mcp_auth.resolve_headers("s", {}) == {}
