"""Dokument-ruterne: ejerskab, version og det delbare link.

Målt 22/11-2026: ``core.services.artifact_document`` blev leveret med nul
kaldere — et dokument-lag der så ud som om det virkede, men som ingen rute bandt
til Desk. Testene her låser at ruterne binder det, at en andens dokument er 404
(ikke 403, så et gæt ikke kan bekræftes), og at publicering skriver i kalderens
EGEN mappe og signerer det navn den faktisk skrev.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

import core.identity.workspace_context as wc
from apps.api.jarvis_api.routes import chat_documents as R

A, B = "ejer-a", "ejer-b"
S1, S2, SB = "sess-a-1", "sess-a-2", "sess-b-1"


@pytest.fixture
def rt(isolated_runtime, monkeypatch):
    import core.services.chat_sessions as chat_sessions

    ejere = {S1: A, S2: A, SB: B}
    monkeypatch.setattr(chat_sessions, "get_session_owner", lambda sid: ejere.get(sid))

    def som(uid):
        monkeypatch.setattr(wc, "current_user_id", lambda: uid)

    som(A)

    class H:
        som_ = staticmethod(som)

        def http(self, fn, *a, **kw):
            with pytest.raises(HTTPException) as e:
                fn(*a, **kw)
            return e.value.status_code

    yield H()


def _opret(session=S1, titel="Notat", indhold="# Hej"):
    return R.opret_dokument(
        session, R.OpretDokumentBody(title=titel, content=indhold)
    )["document"]


def test_opret_og_list_i_egen_samtale(rt) -> None:
    doc = _opret()
    assert doc["id"].startswith("doc-")
    assert doc["title"] == "Notat"
    assert doc["version"] == 1

    liste = R.list_dokumenter(S1)["documents"]
    assert [d["id"] for d in liste] == [doc["id"]]


def test_dokument_er_usynligt_for_en_anden_ejer(rt) -> None:
    doc = _opret()
    rt.som_(B)
    assert rt.http(R.laes_dokument, doc["id"]) == 404


def test_fremmed_samtale_giver_404_ved_oprettelse(rt) -> None:
    rt.som_(B)
    assert rt.http(R.opret_dokument, S1, R.OpretDokumentBody(title="X")) == 404


def test_opdatering_kraever_rigtig_version(rt) -> None:
    doc = _opret()
    ny = R.opdater_dokument(
        doc["id"], R.OpdaterDokumentBody(content="# Ny", expected_version=1)
    )["document"]
    assert ny["version"] == 2
    assert ny["content"] == "# Ny"

    # Forældet version skal afvises som 409, så klienten henter og prøver igen.
    assert (
        rt.http(
            R.opdater_dokument,
            doc["id"],
            R.OpdaterDokumentBody(content="# Gammel", expected_version=1),
        )
        == 409
    )


def test_en_andens_dokument_kan_ikke_opdateres(rt) -> None:
    doc = _opret()
    rt.som_(B)
    assert (
        rt.http(
            R.opdater_dokument,
            doc["id"],
            R.OpdaterDokumentBody(content="kapret", expected_version=1),
        )
        == 404
    )


def test_publicering_skriver_i_egen_mappe_og_signerer_navnet(rt, monkeypatch, tmp_path) -> None:
    """Signeret navn skal være det SAMME som det der blev skrevet — ellers
    peger linket på en fil der ikke findes, eller på en andens."""
    mappe = tmp_path / "u" / "ejer-a"
    mappe.mkdir(parents=True)
    monkeypatch.setattr(
        "core.runtime.workspace_paths.published_files_dir", lambda opret=False: mappe
    )

    set_navn: list[str] = []

    def falsk_signer(filnavn, *, workspace, levetid_s=0):
        set_navn.append(f"{workspace}|{filnavn}")
        return {"status": "ok", "sig": "abc123", "udloeb": 999, "levetid_s": 3600}

    monkeypatch.setattr("core.services.file_links.signer", falsk_signer)

    doc = _opret(indhold="# Publiceret")
    svar = R.publicer_dokument(doc["id"], R.PublicerBody())

    assert svar["status"] == "ok"
    assert set_navn == [f"ejer-a|{svar['filename']}"]
    skrevet = (mappe / svar["filename"]).read_text(encoding="utf-8")
    assert skrevet == "# Publiceret"
    assert "sig=abc123" in svar["url"]


def test_filnavn_kan_ikke_skrive_uden_for_mappen(rt, monkeypatch, tmp_path) -> None:
    mappe = tmp_path / "u" / "ejer-a"
    mappe.mkdir(parents=True)
    monkeypatch.setattr(
        "core.runtime.workspace_paths.published_files_dir", lambda opret=False: mappe
    )
    monkeypatch.setattr(
        "core.services.file_links.signer",
        lambda f, *, workspace, levetid_s=0: {
            "status": "ok",
            "sig": "s",
            "udloeb": 1,
            "levetid_s": 1,
        },
    )

    doc = _opret()
    svar = R.publicer_dokument(
        doc["id"], R.PublicerBody(filename="../../udenfor.md")
    )
    assert "/" not in svar["filename"]
    assert (mappe / svar["filename"]).is_file()
