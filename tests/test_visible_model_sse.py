"""SSE-dekoderen: linje-kilden, fallbacken og den haerdede parsning.

Modulet havde ingen egen testfil foer 3/10-2026, hvor linje-kilden blev skilt
fra parsningen for at kunne maale HVOR tiden gaar i streamen. Den aendring
faldt syv tests i `visible_followup_adapters` foerste gang — fordi en
fake-response er iterérbar uden at have `readline`. Testene her daekker netop
den graense, saa det ikke sker igen.
"""
from __future__ import annotations

import pytest

from core.services import delta_trace as dt
from core.services.visible_model_sse import _iter_sse_events, _raa_linjer


class _MedReadline:
    """En response der ligner en aegte HTTPResponse."""

    def __init__(self, linjer):
        self._l = list(linjer)
        self.laest = 0

    def readline(self):
        if not self._l:
            return b""
        self.laest += 1
        return self._l.pop(0)

    def __iter__(self):
        while True:
            x = self.readline()
            if not x:
                return
            yield x


# ── Linje-kilden ──────────────────────────────────────────────────────────

def test_uden_noegle_itereres_der_som_foer():
    linjer = [b"data: {}\n", b"\n"]
    assert list(_raa_linjer(iter(linjer), "")) == linjer


def test_en_response_UDEN_readline_falder_tilbage():
    """Fejlen der faldt syv tests: en eksplicit laese-loekke gav NUL events
    for en simpel iterator. En maaling maa aldrig koste funktionalitet."""
    linjer = [b"data: {\"a\": 1}\n", b"\n"]
    assert list(_raa_linjer(iter(linjer), "en-noegle")) == linjer


def test_med_readline_leveres_de_samme_linjer(monkeypatch):
    monkeypatch.setattr(dt, "taendt", lambda: True)
    dt._laes.clear()
    linjer = [b"data: a\n", b"data: b\n", b"\n"]
    r = _MedReadline(linjer)
    assert list(_raa_linjer(r, "s1")) == linjer
    assert r.laest == 3, "kilden skal bruge readline naar den findes"
    dt._laes.clear()


def test_maalingen_noteres_naar_sporet_er_taendt(monkeypatch):
    monkeypatch.setattr(dt, "taendt", lambda: True)
    dt._laes.clear()
    list(_raa_linjer(_MedReadline([b"a\n", b"b\n", b"c\n"]), "s1"))
    assert dt._laes["s1"]["n"] == 3
    dt._laes.clear()


def test_intet_noteres_naar_sporet_er_slukket(monkeypatch):
    monkeypatch.setattr(dt, "taendt", lambda: False)
    dt._laes.clear()
    list(_raa_linjer(_MedReadline([b"a\n", b"b\n"]), "s1"))
    assert dt._laes == {}


def test_kilden_kaster_ikke_naar_sporet_er_i_stykker(monkeypatch):
    """Et spor maa aldrig vaere grunden til at en stream doer."""
    monkeypatch.setattr(dt, "taendt",
                        lambda: (_ for _ in ()).throw(RuntimeError("i stykker")))
    linjer = [b"data: a\n", b"\n"]
    assert list(_raa_linjer(_MedReadline(linjer), "s1")) == linjer


# ── Parsningen: den haerdede kontrakt ────────────────────────────────────

def test_en_komplet_event_parses():
    r = _MedReadline([b'data: {"choices": [{"delta": {"content": "hej"}}]}\n', b"\n",
                      b"data: [DONE]\n", b"\n"])
    ud = list(_iter_sse_events(r))
    assert len(ud) == 1
    assert ud[0]["choices"][0]["delta"]["content"] == "hej"


def test_en_malformet_blok_draeber_ikke_streamen():
    """A11 pkt. 2: én daarlig event-blok midt i en ellers sund stream skal
    springes over, ikke vaelte generatoren."""
    r = _MedReadline([b"data: {ikke json\n", b"\n",
                      b'data: {"ok": 1}\n', b"\n",
                      b"data: [DONE]\n", b"\n"])
    ud = list(_iter_sse_events(r))
    assert [e.get("ok") for e in ud] == [1]


def test_split_utf8_bliver_til_erstatningstegn_ikke_en_fejl():
    """A11 pkt. 1: et splittet codepoint maa ikke rejse en UnicodeDecodeError
    ud af generatoren midt i et svar."""
    r = _MedReadline([b'data: {"t": "\xc3"}\n', b"\n", b"data: [DONE]\n", b"\n"])
    list(_iter_sse_events(r))  # maa ikke kaste


def test_en_stream_uden_DONE_efter_et_skip_er_retrybar():
    from core.services.visible_model_sse import MalformedStreamPayload
    r = _MedReadline([b"data: {ikke json\n", b"\n"])
    with pytest.raises(MalformedStreamPayload):
        list(_iter_sse_events(r))
