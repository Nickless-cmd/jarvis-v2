"""Enhedstests for core/browser/screencast.py.

Dækker de rene funktioner og de fejlveje der ikke kræver en browser:
URL-validering, tal-validering, frame-køens opførsel under pres, og
fanelistens robusthed naar en side ikke kan svare.

Den ægte Chromium-frame testes i tests/test_browser_screencast.py.
"""

from __future__ import annotations

import queue

import pytest

from core.browser import screencast as sc


# ── normaliser_url ────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "raa, forventet",
    [
        ("https://example.com/x", "https://example.com/x"),
        ("http://example.com", "http://example.com"),
        ("example.com", "https://example.com"),
        ("  example.com/path  ", "https://example.com/path"),
    ],
)
def test_normaliser_url_tilfoejer_skema(raa, forventet):
    assert sc.normaliser_url(raa) == forventet


@pytest.mark.parametrize(
    "farlig",
    ["file:///etc/passwd", "javascript:alert(1)", "data:text/html,x", "", None, 42],
)
def test_normaliser_url_afviser_farlige_skemaer(farlig):
    assert sc.normaliser_url(farlig) is None


# ── _tal ──────────────────────────────────────────────────────────────────

def test_tal_accepterer_vaerdi_i_interval():
    assert sc._tal("0.5", 0.0, 1.0) == 0.5


@pytest.mark.parametrize("vaerdi", ["abc", None, {}, "nan", "inf"])
def test_tal_afviser_ikke_tal(vaerdi):
    assert sc._tal(vaerdi, 0.0, 1.0) is None


@pytest.mark.parametrize("vaerdi", [-1, 2, 1.5])
def test_tal_afviser_udenfor_interval(vaerdi):
    assert sc._tal(vaerdi, 0.0, 1.0) is None


# ── frame-køen ────────────────────────────────────────────────────────────

def test_next_frame_giver_none_naar_koeen_er_tom():
    sess = sc.ScreencastSession()
    assert sess.next_frame(timeout=0.01) is None


def test_on_frame_laegger_frame_i_koeen():
    sess = sc.ScreencastSession()
    sess._on_frame({"data": "aGVsbG8=", "sessionId": 1})
    assert sess.next_frame(timeout=0.1) == b"hello"


def test_on_frame_med_ugyldig_base64_giver_ingen_frame():
    sess = sc.ScreencastSession()
    sess._on_frame({"data": "!!!ikke-base64!!!", "sessionId": 1})
    assert sess.next_frame(timeout=0.01) is None


def test_on_frame_smidder_aeldste_naar_koeen_er_fuld():
    """Køen må aldrig blokere: klienten skal se det NYESTE billede."""
    sess = sc.ScreencastSession(max_queue=1)
    sess._on_frame({"data": "Zm9ycnN0", "sessionId": 1})  # "først"
    sess._on_frame({"data": "YW5kZW4=", "sessionId": 2})  # "anden"
    assert sess.next_frame(timeout=0.1) == b"anden"


def test_on_frame_uden_data_ack_men_laegger_intet():
    sess = sc.ScreencastSession()
    sess._on_frame({"sessionId": 7})
    assert sess.next_frame(timeout=0.01) is None
    assert sess._acks == [7]


# ── hent_faner ────────────────────────────────────────────────────────────

class _FalskSide:
    def __init__(self, titel_fejler=False, evaluate_fejler=False):
        self.url = "https://example.com"
        self._titel_fejler = titel_fejler
        self._evaluate_fejler = evaluate_fejler

    def title(self):
        if self._titel_fejler:
            raise RuntimeError("side midt i navigation")
        return "Eksempel"

    def evaluate(self, _udtryk):
        if self._evaluate_fejler:
            raise RuntimeError("ingen JS-kontekst")
        return True


class _FalskCtx:
    def __init__(self, sider):
        self._sider = sider
        self.page = sider[0]

    def all_pages(self):
        return self._sider


def test_hent_faner_giver_elektron_broens_form():
    ctx = _FalskCtx([_FalskSide()])
    faner = sc.hent_faner(ctx)
    assert faner == [{
        "id": 0,
        "url": "https://example.com",
        "titel": "Eksempel",
        "aktiv": True,
        "kanTilbage": True,
        "kanFrem": True,
        "henter": False,
    }]


def test_hent_faner_overlever_en_side_der_ikke_svarer():
    """En død side må give tomme felter — ikke dræbe hele fanelisten."""
    ctx = _FalskCtx([_FalskSide(titel_fejler=True, evaluate_fejler=True)])
    faner = sc.hent_faner(ctx)
    assert faner[0]["titel"] == ""
    assert faner[0]["kanTilbage"] is False
    assert faner[0]["url"] == "https://example.com"
