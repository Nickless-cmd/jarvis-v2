"""Tests for attachment upload and serve endpoints."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.jarvis_api.routes.attachments import AttachmentMeta, router, _registry

app = FastAPI()
app.include_router(router)
client = TestClient(app)

FAKE_SESSION = "chat-testsession123"


@pytest.fixture(autouse=True)
def clear_registry():
    _registry.clear()
    yield
    _registry.clear()


@pytest.fixture(autouse=True)
def mock_session_and_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.attachments.get_chat_session",
        lambda sid: {"id": sid} if sid == FAKE_SESSION else None,
    )
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.attachments._UPLOAD_DIR",
        tmp_path / "uploads",
    )


def test_upload_image_success():
    data = b"\x89PNG\r\n" + b"x" * 100
    response = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("photo.png", io.BytesIO(data), "image/png")},
    )
    assert response.status_code == 200
    body = response.json()
    assert "id" in body
    assert body["filename"] == "photo.png"
    assert body["mime_type"] == "image/png"
    assert body["size_bytes"] == len(data)


def test_upload_unknown_session_rejected():
    response = client.post(
        "/attachments/upload",
        data={"session_id": "chat-doesnotexist"},
        files={"file": ("x.txt", io.BytesIO(b"hi"), "text/plain")},
    )
    assert response.status_code == 404


def test_upload_enforces_image_limit():
    for i in range(25):
        _registry[f"fake-{i}"] = AttachmentMeta(
            id=f"fake-{i}", session_id=FAKE_SESSION,
            filename=f"img{i}.jpg", mime_type="image/jpeg",
            size_bytes=100, server_path="/tmp/fake",
        )
    response = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("extra.jpg", io.BytesIO(b"x"), "image/jpeg")},
    )
    assert response.status_code == 400
    assert "25" in response.json()["detail"]


def test_serve_attachment():
    data = b"hello world"
    resp = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("note.txt", io.BytesIO(data), "text/plain")},
    )
    assert resp.status_code == 200
    aid = resp.json()["id"]

    serve_resp = client.get(f"/attachments/{aid}?session_id={FAKE_SESSION}")
    assert serve_resp.status_code == 200
    assert serve_resp.content == data


def test_serve_wrong_session_rejected():
    data = b"secret"
    resp = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("f.txt", io.BytesIO(data), "text/plain")},
    )
    aid = resp.json()["id"]
    resp2 = client.get(f"/attachments/{aid}?session_id=chat-wrongsession")
    assert resp2.status_code == 403


def test_serve_unknown_id():
    resp = client.get(f"/attachments/doesnotexist?session_id={FAKE_SESSION}")
    assert resp.status_code == 404


# ── Sandkasse + scan-politik (2026-09-02) ────────────────────────────────────

def _zip_bytes(entries: dict[str, bytes], *, compress: bool = False) -> bytes:
    import zipfile
    buf = io.BytesIO()
    mode = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    with zipfile.ZipFile(buf, "w", compression=mode) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


@pytest.fixture
def ren_scanner(monkeypatch):
    """Lad som om ClamAV svarer «rent».

    Uden den her rammer arkiv-testene fail-closed-politikken på en maskine uden
    clamscan — hvilket er KORREKT adfærd, men så tester man politikken igen i
    stedet for udpakningen. Fail-closed har sin egen test nedenfor.
    """
    import core.services.gate_execution as ge

    class _OK:
        allowed = True
        classification = "clean"
        reason = ""

    monkeypatch.setattr(ge, "check_upload", lambda *a, **k: _OK())
    return ge


def test_arkiv_er_fail_closed_naar_scanneren_ikke_kan_svare(monkeypatch):
    """En zip vi ikke kunne se ind i, er præcis den vi helst ville have scannet."""
    import core.services.gate_execution as ge

    class _Unavailable:
        allowed = False
        classification = "unavailable"
        reason = "clamscan ikke installeret"

    monkeypatch.setattr(ge, "check_upload", lambda *a, **k: _Unavailable())
    resp = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("b.zip", io.BytesIO(_zip_bytes({"f": b"x"})), "application/zip")},
    )
    assert resp.status_code == 400


def test_zip_pakkes_ud_i_sandkasse_og_er_ikke_eksekverbar(ren_scanner):
    """Et arkiv pakkes ud ved upload, så Jarvis læser fra sandkassen i stedet
    for selv at køre en udpakning uden for værnet."""
    import os
    import stat
    from apps.api.jarvis_api.routes import attachments as att

    payload = _zip_bytes({"noter.txt": b"hej", "under/b.txt": b"verden"})
    resp = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("bundt.zip", io.BytesIO(payload), "application/zip")},
    )
    assert resp.status_code == 200, resp.text
    aid = resp.json()["id"]

    root = att._sandbox_roots.get(aid)
    assert root, "arkivet blev ikke pakket ud"
    extracted = Path(root) / "noter.txt"
    assert extracted.read_bytes() == b"hej"
    assert stat.S_IMODE(os.stat(extracted).st_mode) == 0o600


def test_zip_slip_afvises_ved_upload(ren_scanner):
    """Stien peger ud af sandkassen — arkivet må aldrig nå disken som brugbart."""
    payload = _zip_bytes({"../../flugt.txt": b"nej"})
    resp = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("ond.zip", io.BytesIO(payload), "application/zip")},
    )
    assert resp.status_code == 400
    assert "afvist" in resp.json()["detail"].lower()


def test_uploadet_fil_mister_eksekverbar_bit():
    import os
    import stat
    resp = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("note.txt", io.BytesIO(b"tekst"), "text/plain")},
    )
    assert resp.status_code == 200
    path = Path(resp.json()["server_path"])
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_arkiv_genkendes_selv_naar_navnet_lyver(ren_scanner):
    """Mime og filnavn kommer fra klienten. Signaturen gør ikke."""
    from apps.api.jarvis_api.routes import attachments as att
    payload = _zip_bytes({"f.txt": b"x"})
    resp = client.post(
        "/attachments/upload",
        data={"session_id": FAKE_SESSION},
        files={"file": ("billede.png", io.BytesIO(payload), "image/png")},
    )
    assert resp.status_code == 200
    assert att._sandbox_roots.get(resp.json()["id"]), "forklædt zip blev ikke pakket ud"


def test_eksekverbart_indhold_er_fail_closed_uden_scanner(monkeypatch):
    """Kan scanneren ikke svare, kommer en .exe ikke ind. En .txt gør."""
    from apps.api.jarvis_api.routes import attachments as att
    assert att._is_executable_like("application/octet-stream", "ting.exe") is True
    assert att._is_executable_like("application/octet-stream", "script.sh") is True
    assert att._is_executable_like("text/plain", "note.txt") is False
    assert att._is_executable_like("image/png", "foto.png") is False
