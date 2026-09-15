"""Udbyderen holdt forbindelsen åben og sendte intet. Nu prøver vi igen.

## Målt 14/9-2026

Seks af Bjørns kørsler døde efter 906–940 sekunder uden ét tegn på skærmen.
`py-spy` fandt tråden i `ssl.read`; `ss -tin` viste at der KOM bytes — ca. 41
hvert 8. sekund. Sporet sagde hvad de var:

    [firstpass-trace] FIRST item efter 905.6s: VisibleModelStreamDone

En strøm der lukkede helt uden indhold. Keepalive, ikke tekst.

**httpx' læse-timeout så de bytes og var tilfreds. Den måler om der kommer
BYTES. Ingen målte om der kom INDHOLD.**

## Hvorfor et genforsøg og ikke en ærlig fejl

Bjørn leverede selv beviset kl. 22:27: han sendte det samme spørgsmål igen og
fik svar på fem sekunder, mens det første forsøg stadig hang i baggrunden.
Fejlen er tilfældig, ikke vedvarende.

## Hvorfor kun før første event

Er der allerede streamet tekst til skærmen, ville et genforsøg gentage den.
Derfor rejses `STALL_KODE` udelukkende når strøm-funktionen ikke har sendt ét
eneste event — og den kode er dermed også beviset for at intet er nået frem.
"""
from __future__ import annotations

import pathlib

import httpx
import pytest

from core.services import visible_run_firstpass as vf
from core.services.cheap_provider_runtime import CheapProviderError
from core.services import cheap_provider_runtime_streaming as st


class _Svar:
    """En httpx-agtig strøm vi selv bestemmer linjerne i."""

    def __init__(self, linjer, status: int = 200):
        self._linjer = linjer
        self.status_code = status
        self.headers: dict = {}

    def __enter__(self): return self
    def __exit__(self, *a): return False
    def iter_lines(self):
        yield from self._linjer
    def iter_bytes(self):
        yield b""


def _kald(monkeypatch, linjer, tider):
    import time as _t
    it = iter(tider)
    sidste = [0.0]

    def _nu():
        try:
            sidste[0] = next(it)
        except StopIteration:
            pass
        return sidste[0]

    monkeypatch.setattr(_t, "monotonic", _nu)
    monkeypatch.setattr(httpx, "stream", lambda *a, **k: _Svar(linjer))

    # Legitimationen hentes FOER stroemmen aabnes. Foerste udgave af testen
    # udskiftede et navn jeg havde gaettet paa, og maalte derfor «auth-not-ready»
    # i stedet for vagten.
    class _Facade:
        def _require_credentials(self, **k):
            # Vaerdien er ordet «proeve». detect-secrets ser noeglenavnet,
            # ikke indholdet, saa den maa markeres — ikke staves udenom.
            return {"api_key": "proeve"}  # pragma: allowlist secret
        def provider_runtime_defaults(self, p):
            return {"base_url": "https://x/v1"}

    monkeypatch.setattr(st, "_facade", lambda: _Facade())
    return list(st._iter_openai_compatible_chat_events(
        provider="deepseek", model="deepseek-v4-flash",
        auth_profile="p", base_url="https://x/v1",
        messages=[{"role": "user", "content": "Ja"}],
    ))


# ─────────────────────────────────────────────────────────── stilheds-vagten

def test_keepalive_uden_indhold_giver_STALL_kode():
    """Aftenens fejl: linjer der ikke er `data:` blev bare sprunget over,
    uendeligt. Nu har de et ur på."""
    assert vf.STALL_KODE == "stalled-before-first-event"
    assert vf.STALL_UDEN_DATA_S == 60.0


def test_stall_taersklen_ligger_under_det_ydre_loft():
    """Ellers ville bagstoppet dræbe kørslen før vagten nåede at reagere, og
    så var vagten pyntegenstand."""
    assert vf.STALL_UDEN_DATA_S < vf.FOERSTE_ELEMENT_LOFT_S


def test_der_er_praecis_ÉT_genforsoeg():
    """En løkke kunne gøre et dødt kald til en runde af timeouts."""
    assert vf.MAKS_GENFORSOEG == 1


# ───────────────────────────────────────────── vagten i selve læse-loopet

def test_keepalive_i_lang_tid_rejser_stall(monkeypatch):
    linjer = [": keep-alive"] * 12
    # Uret: aabning paa 0, derefter forbi 60 s.
    with pytest.raises(CheapProviderError) as ei:
        _kald(monkeypatch, linjer, [0.0, 0.0, 10.0, 10.0, 70.0, 70.0, 70.0])
    assert ei.value.code == vf.STALL_KODE


def test_indhold_FOER_taersklen_slaar_vagten_fra(monkeypatch):
    """Kommer der rigtigt indhold, må en senere stille periode aldrig kunne
    udløse et genforsøg — det ville gentage tekst brugeren har set."""
    linjer = [
        'data: {"choices":[{"delta":{"content":"Hej"}}]}',
        ": keep-alive", ": keep-alive", ": keep-alive",
        "data: [DONE]",
    ]
    ud = _kald(monkeypatch, linjer, [0.0, 0.0, 1.0, 900.0, 900.0, 900.0, 900.0])
    assert any(e.get("kind") == "delta" for e in ud), ud


# ───────────────────────────────────────────── og KALDER adapteren genforsoeget?

def test_adapteren_proever_igen_paa_stall_koden():
    """Aftenens lektie: en mekanisme ingen kalder er død kode. Her er koblingen
    i en 190-linjers try-blok inde i en 320-linjers funktion, så dette er en
    kilde-vagt — svagere end en ægte kørsel, og det skal siges."""
    import ast
    import pathlib
    kilde = pathlib.Path("core/services/visible_model_adapters.py").read_text()
    for n in ast.walk(ast.parse(kilde)):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "_stream_openai_compatible_model":
            tekst = ast.unparse(n)
            assert "STALL_KODE" in tekst, "genforsoeget spoerger ikke paa koden"
            assert "MAKS_GENFORSOEG" in tekst, "der er intet loft paa antal forsoeg"
            assert "for _forsoeg in range" in tekst, "der er ingen loekke at proeve igen i"
            return
    raise AssertionError("_stream_openai_compatible_model findes ikke laengere")


def test_genforsoeget_staar_FOER_bogfoeringen_i_centralen():
    """Ellers ville et vellykket genforsøg efterlade en fejl-observation for
    noget der gik godt — og en observation der lyver er værre end ingen."""
    kilde = pathlib.Path(__file__).parent.parent / "core/services/visible_model_adapters.py"
    t = kilde.read_text()
    i_continue = t.index("[stille-udbyder]")
    i_observe = t.index('"cluster": "stream"')
    assert i_continue < i_observe
