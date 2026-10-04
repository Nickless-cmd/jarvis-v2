"""Ruten og middleware-fritagelsen for signerede fil-links (4/10-2026).

To lag, og de måles hver for sig:

* **Ruten** udsteder kun for en fil der findes, og kun med auth.
* **Middlewaren** slipper kun en GET af præcis den fil forbi, kun mens
  signaturen lever.

Lag-1-dækning skjuler lag-2-huller — målt fire gange i dette hus samme døgn —
så fritagelsen testes mod middleware-funktionen selv, ikke kun gennem ruten.
"""
from __future__ import annotations

import pytest

from core.services import file_links


@pytest.fixture(autouse=True)
def noegle(monkeypatch):
    import core.runtime.secrets as s
    monkeypatch.setattr(s, "read_runtime_key", lambda *a, **k: "test-grundlag-123")


@pytest.fixture
def filmappe(monkeypatch, tmp_path):
    """En RIGTIG mappe. Ruten slår filen op på disken, så en mock ville måle
    sin egen stub frem for betingelsen «filen skal findes først»."""
    import apps.api.jarvis_api.routes.files as r
    monkeypatch.setattr(r, "FILES_DIR", tmp_path)
    (tmp_path / "rapport.pdf").write_bytes(b"%PDF-1.4 ...")
    return tmp_path


def _foresp(sti: str, metode: str = "GET", query: str = ""):
    """En minimal Request. `Request` er en tynd indpakning om ASGI-scope, så
    den kan bygges direkte — en mock med `.url`/`.method` ville kun måle
    mockens egen form."""
    from starlette.requests import Request
    return Request({
        "type": "http", "method": metode, "path": sti, "raw_path": sti.encode(),
        "query_string": query.encode(), "headers": [], "scheme": "http",
        "server": ("test", 80), "root_path": "", "http_version": "1.1",
    })


# ── Ruten ──────────────────────────────────────────────────────────────────

def test_ruten_udsteder_et_brugbart_link(filmappe):
    from apps.api.jarvis_api.routes.files import LinkOenske, udsted_link
    r = udsted_link(LinkOenske(filename="rapport.pdf"))
    assert r["status"] == "ok"
    assert r["url"].startswith("/files/rapport.pdf?udloeb=")
    assert "&sig=" in r["url"]
    assert r["levetid_s"] == file_links.STANDARD_LEVETID_S


def test_ruten_udsteder_IKKE_for_en_fil_der_ikke_findes(filmappe):
    """Ellers kunne ruten bruges til at gætte filnavne: et gyldigt link til
    noget der ikke findes er et svar om at det ikke findes."""
    from fastapi import HTTPException

    from apps.api.jarvis_api.routes.files import LinkOenske, udsted_link
    with pytest.raises(HTTPException) as e:
        udsted_link(LinkOenske(filename="findes-ikke.pdf"))
    assert e.value.status_code == 404


@pytest.mark.parametrize("ondt", ["../../etc/passwd", "mappe/fil.pdf", "", "   "])
def test_ruten_afviser_en_sti(filmappe, ondt):
    from fastapi import HTTPException

    from apps.api.jarvis_api.routes.files import LinkOenske, udsted_link
    with pytest.raises(HTTPException) as e:
        udsted_link(LinkOenske(filename=ondt))
    assert e.value.status_code == 400


def test_uden_signering_svarer_ruten_503_ikke_500(filmappe, monkeypatch):
    """Ruten virker; signeringen er ikke konfigureret. De to er forskellige
    tilstande og skal kunne skelnes i en log."""
    from fastapi import HTTPException

    import core.runtime.secrets as s
    monkeypatch.setattr(s, "read_runtime_key", lambda *a, **k: "")
    from apps.api.jarvis_api.routes.files import LinkOenske, udsted_link
    with pytest.raises(HTTPException) as e:
        udsted_link(LinkOenske(filename="rapport.pdf"))
    assert e.value.status_code == 503


# ── Middleware-fritagelsen ─────────────────────────────────────────────────

def test_et_gyldigt_link_slipper_forbi_auth():
    from apps.api.jarvis_api.middleware.jarvisx_user_routing import (
        _er_signeret_filhentning,
    )
    r = file_links.signer("rapport.pdf")
    assert _er_signeret_filhentning(_foresp(
        "/files/rapport.pdf", query=f"udloeb={r['udloeb']}&sig={r['sig']}")) is True


def test_UDEN_signatur_slipper_INTET_forbi():
    from apps.api.jarvis_api.middleware.jarvisx_user_routing import (
        _er_signeret_filhentning,
    )
    assert _er_signeret_filhentning(_foresp("/files/rapport.pdf")) is False


def test_signaturen_gaelder_KUN_den_signerede_fil():
    from apps.api.jarvis_api.middleware.jarvisx_user_routing import (
        _er_signeret_filhentning,
    )
    r = file_links.signer("min-egen.pdf")
    assert _er_signeret_filhentning(_foresp(
        "/files/en-andens.pdf",
        query=f"udloeb={r['udloeb']}&sig={r['sig']}")) is False


def test_en_POST_slipper_ALDRIG_forbi_paa_en_signatur():
    """En signatur er ret til at LÆSE én fil. Slap en POST igennem, var
    linket en skrivenøgle."""
    from apps.api.jarvis_api.middleware.jarvisx_user_routing import (
        _er_signeret_filhentning,
    )
    r = file_links.signer("rapport.pdf")
    assert _er_signeret_filhentning(_foresp(
        "/files/rapport.pdf", metode="POST",
        query=f"udloeb={r['udloeb']}&sig={r['sig']}")) is False


def test_LISTNINGEN_slipper_ikke_forbi_paa_et_fil_link():
    """`/files/` lister hele mappen — 158 filer målt 4/10. En signatur på én
    fil må ikke åbne fortegnelsen over dem alle."""
    from apps.api.jarvis_api.middleware.jarvisx_user_routing import (
        _er_signeret_filhentning,
    )
    r = file_links.signer("rapport.pdf")
    q = f"udloeb={r['udloeb']}&sig={r['sig']}"
    assert _er_signeret_filhentning(_foresp("/files/", query=q)) is False
    assert _er_signeret_filhentning(_foresp("/files/a/b.pdf", query=q)) is False


def test_en_anden_rute_kan_ikke_laane_signaturen():
    from apps.api.jarvis_api.middleware.jarvisx_user_routing import (
        _er_signeret_filhentning,
    )
    r = file_links.signer("rapport.pdf")
    q = f"udloeb={r['udloeb']}&sig={r['sig']}"
    for sti in ("/chat/history", "/api/jobs", "/attachments/rapport.pdf"):
        assert _er_signeret_filhentning(_foresp(sti, query=q)) is False


def test_et_URL_kodet_filnavn_verificerer():
    """Ruten `quote`r navnet, så middlewaren skal `unquote`. Gjorde den ikke,
    ville hver fil med mellemrum eller æøå give 401 — og kun dem."""
    from apps.api.jarvis_api.middleware.jarvisx_user_routing import (
        _er_signeret_filhentning,
    )
    from urllib.parse import quote
    navn = "oktober tal æøå.xlsx"
    r = file_links.signer(navn)
    assert _er_signeret_filhentning(_foresp(
        f"/files/{quote(navn)}",
        query=f"udloeb={r['udloeb']}&sig={r['sig']}")) is True


def test_fritagelsen_fejler_LUKKET_naar_den_ikke_kan_afgoeres(monkeypatch, caplog):
    import logging

    from apps.api.jarvis_api.middleware import jarvisx_user_routing as m
    import core.services.file_links as fl
    def eksploder(*a, **k):
        raise RuntimeError("signerings-laget er nede")
    monkeypatch.setattr(fl, "verificer", eksploder)
    r = {"udloeb": 9_999_999_999, "sig": "a" * 64}
    with caplog.at_level(logging.WARNING):
        assert m._er_signeret_filhentning(_foresp(
            "/files/rapport.pdf", query=f"udloeb={r['udloeb']}&sig={r['sig']}")) is False
    assert any("fil-signatur" in x.message for x in caplog.records), \
        "fritagelsen fejlede TAVST"
