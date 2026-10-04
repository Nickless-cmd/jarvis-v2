"""Signerede fil-links — Bjørns tredje punkt 4/10-2026.

Testene er skrevet om de steder en signatur plejer at svigte: et link der
peger på en ANDEN fil, et udløb der skrues op i URL'en, et manglende secret,
og en sti der snydes gennem `..`.
"""
from __future__ import annotations

import pytest

from core.services import file_links


@pytest.fixture(autouse=True)
def noegle(monkeypatch):
    """Fast signerings-grundlag. Uden den læser modulet Bjørns RIGTIGE
    `system_api_token` fra `~/.jarvis-v2/config/runtime.json` — og så ville
    testen måle hvilken maskine den kørte på, og i CI slet ikke kunne køre."""
    import core.runtime.secrets as s
    monkeypatch.setattr(s, "read_runtime_key", lambda *a, **k: "test-grundlag-123")
    return "test-grundlag-123"


def test_et_signeret_link_verificerer():
    r = file_links.signer("rapport.pdf", nu=1000.0)
    assert r["status"] == "ok"
    assert file_links.verificer("rapport.pdf", r["udloeb"], r["sig"], nu=1000.0) is True


def test_linket_kan_IKKE_hente_en_anden_fil():
    """Uden filnavnet i signaturen ville ét gyldigt link åbne alle 158 filer
    i den delte mappe."""
    r = file_links.signer("min-egen.pdf", nu=1000.0)
    assert file_links.verificer("en-andens.pdf", r["udloeb"], r["sig"], nu=1000.0) is False


def test_udloebet_kan_IKKE_skrues_op_i_URLen():
    """Udløbet er signeret MED. Ellers er «kortlivet» en tekst i en
    querystring frem for en egenskab."""
    r = file_links.signer("rapport.pdf", levetid_s=60, nu=1000.0)
    assert file_links.verificer("rapport.pdf", int(r["udloeb"]) + 86400,
                                r["sig"], nu=1000.0) is False


def test_et_udloebet_link_afvises():
    r = file_links.signer("rapport.pdf", levetid_s=60, nu=1000.0)
    assert file_links.verificer("rapport.pdf", r["udloeb"], r["sig"], nu=1061.0) is False
    # Og præcis PÅ sekundet er det stadig gyldigt — grænsen skal være et
    # defineret sted, ikke et sted man opdager.
    assert file_links.verificer("rapport.pdf", r["udloeb"], r["sig"], nu=1060.0) is True


def test_levetiden_har_et_LOFT_kalderen_ikke_kan_haeve():
    r = file_links.signer("rapport.pdf", levetid_s=99999, nu=0.0)
    assert r["levetid_s"] == file_links.MAKS_LEVETID_S
    assert int(r["udloeb"]) == file_links.MAKS_LEVETID_S


@pytest.mark.parametrize("ondt", [
    "../../etc/passwd", "/etc/passwd", "mappe/fil.pdf", "..", ".", "", "   ",
])
def test_en_sti_kan_ikke_signeres(ondt):
    """Både signering og verifikation renser med `Path(x).name`. Var det kun
    det ene sted, kunne `../../etc/passwd` signeres som sig selv og
    verificeres som `passwd`."""
    assert file_links.signer(ondt)["status"] == "fejl"
    assert file_links.verificer(ondt, 9_999_999_999, "a" * 64) is False


def test_uden_secret_udstedes_og_verificeres_INTET(monkeypatch):
    """Fail-closed. Et manglende secret må ikke blive «alle links gælder»."""
    gyldig = file_links.signer("rapport.pdf", nu=1000.0)
    import core.runtime.secrets as s
    monkeypatch.setattr(s, "read_runtime_key", lambda *a, **k: "")
    assert file_links.signer("rapport.pdf")["status"] == "fejl"
    assert file_links.verificer("rapport.pdf", gyldig["udloeb"], gyldig["sig"],
                               nu=1000.0) is False


def test_en_ANDEN_noegle_verificerer_ikke(monkeypatch):
    """Roteres system-tokenet, dør de gamle links. Det er med vilje."""
    gyldig = file_links.signer("rapport.pdf", nu=1000.0)
    import core.runtime.secrets as s
    monkeypatch.setattr(s, "read_runtime_key", lambda *a, **k: "et-helt-andet")
    assert file_links.verificer("rapport.pdf", gyldig["udloeb"], gyldig["sig"],
                               nu=1000.0) is False


@pytest.mark.parametrize("skrald", ["", "   ", "ikke-hex", None, "0" * 64])
def test_en_forkert_signatur_afvises(skrald):
    r = file_links.signer("rapport.pdf", nu=1000.0)
    assert file_links.verificer("rapport.pdf", r["udloeb"], skrald, nu=1000.0) is False


@pytest.mark.parametrize("skrald", ["", "senere", None, "1e9", "1000.5"])
def test_et_malformet_udloeb_afvises(skrald):
    r = file_links.signer("rapport.pdf", nu=1000.0)
    assert file_links.verificer("rapport.pdf", skrald, r["sig"], nu=1000.0) is False


def test_noeglen_er_IKKE_system_tokenet_selv(noegle):
    """Domæne-separation: en lækket fil-nøgle må ikke kunne bruges til at
    forfalske noget andet i huset."""
    import hashlib
    import hmac
    assert file_links._noegle() != noegle.encode()
    assert file_links._noegle() == hmac.new(
        noegle.encode(), b"jarvis-fil-link-v1", hashlib.sha256).digest()


def test_signaturen_sammenlignes_i_konstant_tid():
    """Kilde-vagt. En `==` paa en signatur afslutter ved foerste forskellige
    tegn, og den forskel er maalbar over mange forsoeg. AST, ikke grep:
    docstringen naevner `compare_digest` med vilje."""
    import ast
    import pathlib
    traeet = ast.parse(pathlib.Path("core/services/file_links.py").read_text())
    fn = next(n for n in ast.walk(traeet)
              if isinstance(n, ast.FunctionDef) and n.name == "verificer")
    kald = {x.func.attr for x in ast.walk(fn)
            if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute)}
    assert "compare_digest" in kald, "signaturen sammenlignes ikke i konstant tid"
    for x in ast.walk(fn):
        if isinstance(x, ast.Compare) and any(isinstance(o, ast.Eq) for o in x.ops):
            kilde = ast.unparse(x)
            assert "sig" not in kilde, f"signaturen sammenlignes med ==: {kilde}"
