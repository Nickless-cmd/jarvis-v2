"""`drive_download` — hent en Drive-fil, og eksportér Google-native formater.

## Hvorfor testen findes

Målt 27/10-2026 (Bjørn): der fandtes `drive_search`, men intet værktøj der
kunne hente filen NED. Jarvis måtte kalde Drive-API'et i hånden med brugerens
token for at læse en PDF — en omvej uden om værktøjsfladen, som ingen anden
tur ville gentage korrekt.

## Den fælde testen værner

Google Docs/Sheets/Slides har **ingen bytes**. `alt=media` på en Docs giver
400, og det ser ud som en forbindelsesfejl. De skal EKSPORTERES. En test der
kun dækker den almindelige fil ville være grøn mens hver eneste Docs-fil
fejlede i produktion.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.services import google_connector as gc

UID = "1246415163603816499"


@pytest.fixture()
def gemt_fil(monkeypatch, tmp_path):
    """Fang hvor filen lander, uden at røre den rigtige filmappe."""
    skrevet: dict[str, bytes] = {}

    def _sti(navn, user_id=None, *, opret_mappe=False):
        return tmp_path / Path(str(navn)).name

    monkeypatch.setattr("core.runtime.workspace_paths.published_file_path", _sti)
    return skrevet


def _meta(mime: str, navn: str = "fil"):
    return {"status": "ok", "data": {"id": "x", "name": navn, "mimeType": mime, "size": "10"}}


class _Svar:
    def __init__(self, indhold: bytes = b"data", status: int = 200):
        self.content = indhold
        self.status_code = status


def test_almindelig_fil_hentes_som_bytes(monkeypatch, gemt_fil):
    """En PDF har bytes — den skal hentes med alt=media, ikke eksporteres."""
    monkeypatch.setattr(gc, "_get", lambda *a, **k: _meta("application/pdf", "brev"))
    monkeypatch.setattr(gc, "get_fresh_token", lambda *a, **k: {"access_token": "t"})
    kaldt: dict = {}

    def _get_http(url, **kw):
        kaldt["url"] = url
        kaldt["params"] = kw.get("params")
        return _Svar(b"%PDF-1.4 indhold")

    import httpx
    monkeypatch.setattr(httpx, "get", _get_http)

    r = gc.drive_download(UID, "x")
    assert r["status"] == "ok", r
    assert r["filename"] == "brev.pdf"
    assert r["size_bytes"] == len(b"%PDF-1.4 indhold")
    assert kaldt["params"]["alt"] == "media"
    assert "export" not in kaldt["url"]
    assert r["exported_from"] == ""


def test_google_docs_eksporteres_ikke_hentes(monkeypatch, gemt_fil):
    """Docs har ingen bytes. Uden eksport-grenen ville hver Docs give 400."""
    monkeypatch.setattr(gc, "_get", lambda *a, **k: _meta(
        "application/vnd.google-apps.document", "notat"))
    monkeypatch.setattr(gc, "get_fresh_token", lambda *a, **k: {"access_token": "t"})
    kaldt: dict = {}

    def _get_http(url, **kw):
        kaldt["url"] = url
        kaldt["params"] = kw.get("params")
        return _Svar(b"PK-docx-indhold")

    import httpx
    monkeypatch.setattr(httpx, "get", _get_http)

    r = gc.drive_download(UID, "x")
    assert r["status"] == "ok", r
    assert kaldt["url"].endswith("/export"), kaldt["url"]
    assert "wordprocessingml" in kaldt["params"]["mimeType"]
    assert r["filename"] == "notat.docx"
    assert r["exported_from"] == "application/vnd.google-apps.document"


def test_export_as_pdf_tvinger_format(monkeypatch, gemt_fil):
    """`export_as='pdf'` skal virke for alle tre Google-native typer."""
    monkeypatch.setattr(gc, "_get", lambda *a, **k: _meta(
        "application/vnd.google-apps.spreadsheet", "ark"))
    monkeypatch.setattr(gc, "get_fresh_token", lambda *a, **k: {"access_token": "t"})
    kaldt: dict = {}

    def _get_http(url, **kw):
        kaldt["params"] = kw.get("params")
        return _Svar(b"%PDF")

    import httpx
    monkeypatch.setattr(httpx, "get", _get_http)

    r = gc.drive_download(UID, "x", export_as="pdf")
    assert r["status"] == "ok", r
    assert kaldt["params"]["mimeType"] == "application/pdf"
    assert r["filename"] == "ark.pdf"


def test_manglende_file_id_er_kalderens_fejl():
    r = gc.drive_download(UID, "   ")
    assert r["status"] == "error"
    assert "file_id" in r["error"]


def test_dødt_token_siger_not_connected(monkeypatch, gemt_fil):
    """401 skal give `drive_not_connected` — ikke en tom fil."""
    monkeypatch.setattr(gc, "_get", lambda *a, **k: _meta("application/pdf"))
    monkeypatch.setattr(gc, "get_fresh_token", lambda *a, **k: {"access_token": "t"})

    import httpx
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Svar(b"", status=401))

    r = gc.drive_download(UID, "x")
    assert r["status"] == "error"
    assert r["error"] == "drive_not_connected"


def test_vaerktoejet_er_i_katalog_og_i_connector_registret():
    """Et værktøj der findes men ikke kan nås er den fejlklasse der kostede
    fire runder 27/10-2026 (vis_graf, git_log, publish_file, pdf_read).

    Scope-porten måles IKKE her: den åbner connector-værktøjer ud fra hvem der
    faktisk har et token, og en test-database har ikke Bjørns Google-token.
    Det statiske led — at navnet står i registret OG har en definition — er
    det der kan gå galt i en commit. Selve åbne-mekanikken værnes af
    `tests/test_connector_tools_in_scope.py`.
    """
    from core.services.connectors import _CATALOG
    from core.tools.simple_tools import get_tool_definitions

    navne = {(d.get("function") or {}).get("name") for d in (get_tool_definitions() or [])}
    assert "drive_download" in navne, "drive_download mangler i kataloget"

    drive = next((c for c in _CATALOG if c.get("id") == "google-drive"), None)
    assert drive is not None, "google-drive-connectoren findes ikke"
    assert "drive_download" in (drive.get("tools") or []), \
        "drive_download står ikke i connector-registret — så åbner scope-porten den aldrig"
