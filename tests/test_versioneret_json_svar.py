"""Svaret på GET /chat/sessions/{id}: samme indhold, men serialiseret én gang
pr. version og gzip'et når klienten beder om det (21,5 MB → 6,5 MB, målt
19/9-2026). Den farlige fejl er et forældet svar — derfor testes versionen."""
from __future__ import annotations

import gzip
import json

import pytest

from core.services import central_projection_cache as cpc
from core.services.versioneret_json_svar import _vil_have_gzip, versioneret_json_svar


@pytest.fixture(autouse=True)
def _tom_cache():
    cpc._VERSIONED.clear()
    yield
    cpc._VERSIONED.clear()


def _svar(version="v1", enc="gzip, deflate", indhold=None):
    return versioneret_json_svar(
        noegle="t:s1", version=version, etag=f'W/"{version}"', accept_encoding=enc,
        indhold=indhold or (lambda: {"session": {"id": "s1", "messages": ["hej"] * 50}}))


def test_gzip_naar_klienten_beder_om_det():
    r = _svar()
    assert r.headers["content-encoding"] == "gzip"
    assert json.loads(gzip.decompress(r.body)) == {"session": {"id": "s1", "messages": ["hej"] * 50}}
    assert r.headers["etag"] == 'W/"v1"'
    assert r.headers["vary"] == "Accept-Encoding"


def test_ren_json_uden_gzip():
    r = _svar(enc=None)
    assert "content-encoding" not in r.headers
    assert json.loads(r.body)["session"]["id"] == "s1"


def test_indholdet_bygges_kun_en_gang_pr_version():
    kald = []
    def indhold():
        kald.append(1)
        return {"n": len(kald)}
    _svar(indhold=indhold)
    _svar(indhold=indhold, enc=None)
    _svar(indhold=indhold)
    assert len(kald) == 1


def test_ny_version_giver_nyt_indhold_ogsaa_komprimeret():
    _svar(version="v1", indhold=lambda: {"x": "gammel"})
    r = _svar(version="v2", indhold=lambda: {"x": "ny"})
    assert json.loads(gzip.decompress(r.body)) == {"x": "ny"}, "gzip-udgaven var forældet"


@pytest.mark.parametrize("hoved,forventet", [
    ("gzip", True), ("br, gzip;q=0.8", True), ("GZIP", True),
    ("gzip;q=0", False), ("identity", False), ("", False), (None, False), ("x-gzip-ish", False),
])
def test_accept_encoding_laeses_rigtigt(hoved, forventet):
    assert _vil_have_gzip(hoved) is forventet
