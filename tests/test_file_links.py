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
    r = file_links.signer("rapport.pdf", workspace="bjorn", nu=1000.0)
    assert r["status"] == "ok"
    assert file_links.verificer("rapport.pdf", r["udloeb"], r["sig"], nu=1000.0, workspace="bjorn") is True


def test_linket_kan_IKKE_hente_en_anden_fil():
    """Uden filnavnet i signaturen ville ét gyldigt link åbne alle 158 filer
    i den delte mappe."""
    r = file_links.signer("min-egen.pdf", workspace="bjorn", nu=1000.0)
    assert file_links.verificer("en-andens.pdf", r["udloeb"], r["sig"], nu=1000.0, workspace="bjorn") is False


def test_udloebet_kan_IKKE_skrues_op_i_URLen():
    """Udløbet er signeret MED. Ellers er «kortlivet» en tekst i en
    querystring frem for en egenskab."""
    r = file_links.signer("rapport.pdf", workspace="bjorn", levetid_s=60, nu=1000.0)
    assert file_links.verificer("rapport.pdf", int(r["udloeb"]) + 86400,
                                r["sig"], workspace="bjorn", nu=1000.0) is False


def test_et_udloebet_link_afvises():
    r = file_links.signer("rapport.pdf", workspace="bjorn", levetid_s=60, nu=1000.0)
    assert file_links.verificer("rapport.pdf", r["udloeb"], r["sig"], nu=1061.0, workspace="bjorn") is False
    # Og præcis PÅ sekundet er det stadig gyldigt — grænsen skal være et
    # defineret sted, ikke et sted man opdager.
    assert file_links.verificer("rapport.pdf", r["udloeb"], r["sig"], nu=1060.0, workspace="bjorn") is True


def test_levetiden_har_et_LOFT_kalderen_ikke_kan_haeve():
    r = file_links.signer("rapport.pdf", workspace="bjorn", levetid_s=99999, nu=0.0)
    assert r["levetid_s"] == file_links.MAKS_LEVETID_S
    assert int(r["udloeb"]) == file_links.MAKS_LEVETID_S


@pytest.mark.parametrize("ondt", [
    "../../etc/passwd", "/etc/passwd", "mappe/fil.pdf", "..", ".", "", "   ",
])
def test_en_sti_kan_ikke_signeres(ondt):
    """Både signering og verifikation renser med `Path(x).name`. Var det kun
    det ene sted, kunne `../../etc/passwd` signeres som sig selv og
    verificeres som `passwd`."""
    assert file_links.signer(ondt, workspace="bjorn")["status"] == "fejl"
    assert file_links.verificer(ondt, 9_999_999_999, "a" * 64, workspace="bjorn") is False


def test_uden_secret_udstedes_og_verificeres_INTET(monkeypatch):
    """Fail-closed. Et manglende secret må ikke blive «alle links gælder»."""
    gyldig = file_links.signer("rapport.pdf", workspace="bjorn", nu=1000.0)
    import core.runtime.secrets as s
    monkeypatch.setattr(s, "read_runtime_key", lambda *a, **k: "")
    assert file_links.signer("rapport.pdf", workspace="bjorn")["status"] == "fejl"
    assert file_links.verificer("rapport.pdf", gyldig["udloeb"], gyldig["sig"],
                               nu=1000.0, workspace="bjorn") is False


def test_en_ANDEN_noegle_verificerer_ikke(monkeypatch):
    """Roteres system-tokenet, dør de gamle links. Det er med vilje."""
    gyldig = file_links.signer("rapport.pdf", workspace="bjorn", nu=1000.0)
    import core.runtime.secrets as s
    monkeypatch.setattr(s, "read_runtime_key", lambda *a, **k: "et-helt-andet")
    assert file_links.verificer("rapport.pdf", gyldig["udloeb"], gyldig["sig"],
                               nu=1000.0, workspace="bjorn") is False


@pytest.mark.parametrize("skrald", ["", "   ", "ikke-hex", None, "0" * 64])
def test_en_forkert_signatur_afvises(skrald):
    r = file_links.signer("rapport.pdf", workspace="bjorn", nu=1000.0)
    assert file_links.verificer("rapport.pdf", r["udloeb"], skrald, nu=1000.0, workspace="bjorn") is False


@pytest.mark.parametrize("skrald", ["", "senere", None, "1e9", "1000.5"])
def test_et_malformet_udloeb_afvises(skrald):
    r = file_links.signer("rapport.pdf", workspace="bjorn", nu=1000.0)
    assert file_links.verificer("rapport.pdf", skrald, r["sig"], nu=1000.0, workspace="bjorn") is False


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


# ── Workspacet i signaturen (4/10-2026, da filer blev per bruger) ───────────

def test_et_link_kan_IKKE_hente_en_anden_brugers_fil_med_samme_navn():
    """Det afgørende nye led. Da alt lå i én mappe, kunne et filnavn kun
    betyde én fil, og workspacet ville have været pynt. Nu kan `rapport.pdf`
    findes hos to brugere — og så er workspacet hele forskellen."""
    r = file_links.signer("rapport.pdf", workspace="lotte", nu=1000.0)
    assert file_links.verificer("rapport.pdf", r["udloeb"], r["sig"],
                                workspace="bjorn", nu=1000.0) is False
    assert file_links.verificer("rapport.pdf", r["udloeb"], r["sig"],
                                workspace="lotte", nu=1000.0) is True


@pytest.mark.parametrize("ondt", ["../bjorn", "a/b", "..", ".", "", "   ", "/bjorn"])
def test_et_workspace_der_er_en_STI_afvises(ondt):
    """Et workspace er en MAPPE. `..` og skråstreger er lige så farlige her
    som i filnavnet."""
    assert file_links.signer("x.pdf", workspace=ondt)["status"] == "fejl"
    assert file_links.verificer("x.pdf", 9_999_999_999, "a" * 64,
                                workspace=ondt) is False


def test_workspace_er_PAAKRAEVET_ikke_valgfrit():
    """En default ville betyde at en kalder der glemmer det får et link der
    peger ét sted — det samme sted for alle. Nu er det en TypeError."""
    with pytest.raises(TypeError):
        file_links.signer("x.pdf")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        file_links.verificer("x.pdf", 1, "a")  # type: ignore[call-arg]
