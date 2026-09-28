# tests/test_attachment_service.py
from __future__ import annotations
import pytest


# ---------------------------------------------------------------------------
# download_and_store
# ---------------------------------------------------------------------------

def test_download_and_store_returns_ok(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    monkeypatch.setattr(svc, "_UPLOAD_ROOT", tmp_path)

    def fake_download(url, headers):
        return b"fake image data"

    monkeypatch.setattr(svc, "_http_download", fake_download)
    monkeypatch.setattr(svc, "_db_store", lambda **kw: None)

    result = svc.download_and_store(
        url="https://cdn.discord.com/photo.jpg",
        filename="photo.jpg",
        mime_type="image/jpeg",
        size_bytes=100,
        session_id="sess-1",
        channel_type="discord",
    )
    assert result["status"] == "ok"
    assert "attachment_id" in result
    saved = tmp_path / "sess-1" / f"{result['attachment_id']}_photo.jpg"
    assert saved.exists()
    assert saved.read_bytes() == b"fake image data"


def test_download_and_store_rejects_too_large(monkeypatch):
    import core.services.attachment_service as svc
    result = svc.download_and_store(
        url="https://cdn.discord.com/big.zip",
        filename="big.zip",
        mime_type="application/zip",
        size_bytes=svc.MAX_SIZE_BYTES + 1,
        session_id="sess-1",
        channel_type="discord",
    )
    assert result["status"] == "error"
    assert result["reason"] == "too_large"


def test_download_and_store_handles_download_failure(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    monkeypatch.setattr(svc, "_UPLOAD_ROOT", tmp_path)

    def fail_download(url, headers):
        raise OSError("timeout")

    monkeypatch.setattr(svc, "_http_download", fail_download)

    result = svc.download_and_store(
        url="https://cdn.discord.com/photo.jpg",
        filename="photo.jpg",
        mime_type="image/jpeg",
        size_bytes=100,
        session_id="sess-1",
        channel_type="discord",
    )
    assert result["status"] == "error"
    assert result["reason"] == "download_failed"


# ---------------------------------------------------------------------------
# get_attachment / list_attachments
# ---------------------------------------------------------------------------

def test_get_attachment_returns_metadata(monkeypatch):
    import core.services.attachment_service as svc
    fake_row = {
        "attachment_id": "abc-123", "session_id": "sess-1",
        "channel_type": "discord", "filename": "photo.jpg",
        "mime_type": "image/jpeg", "size_bytes": 100,
        "local_path": "/tmp/photo.jpg", "source_url": "", "created_at": "2026-04-23T00:00:00",
    }
    monkeypatch.setattr(svc, "_db_get", lambda attachment_id: fake_row)
    result = svc.get_attachment("abc-123")
    assert result["filename"] == "photo.jpg"


def test_get_attachment_returns_none_for_unknown(monkeypatch):
    import core.services.attachment_service as svc
    monkeypatch.setattr(svc, "_db_get", lambda attachment_id: None)
    assert svc.get_attachment("unknown-id") is None


def test_list_attachments_returns_list(monkeypatch):
    import core.services.attachment_service as svc
    fake_rows = [
        {"attachment_id": "x1", "filename": "a.jpg", "session_id": "sess-1",
         "channel_type": "discord", "mime_type": "image/jpeg", "size_bytes": 1,
         "local_path": "", "source_url": "", "created_at": ""},
    ]
    monkeypatch.setattr(svc, "_db_list", lambda session_id, limit: fake_rows)
    rows = svc.list_attachments("sess-1")
    assert len(rows) == 1
    assert rows[0]["filename"] == "a.jpg"


# ---------------------------------------------------------------------------
# read_attachment_content
# ---------------------------------------------------------------------------

def test_read_attachment_content_unknown_id(monkeypatch):
    import core.services.attachment_service as svc
    monkeypatch.setattr(svc, "_db_get", lambda attachment_id: None)
    result = svc.read_attachment_content("unknown")
    assert result["status"] == "error"
    assert result["reason"] == "not-found"


def test_read_attachment_content_text_file(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    txt = tmp_path / "note.txt"
    txt.write_text("hello world")
    row = {
        "attachment_id": "t1", "filename": "note.txt", "mime_type": "text/plain",
        "local_path": str(txt), "session_id": "s", "channel_type": "discord",
        "size_bytes": 11, "source_url": "", "created_at": "",
    }
    monkeypatch.setattr(svc, "_db_get", lambda aid: row)
    result = svc.read_attachment_content("t1")
    assert result["status"] == "ok"
    assert result["type"] == "text"
    assert "hello world" in result["content"]


def test_read_attachment_content_image_calls_vision(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    img = tmp_path / "pic.jpg"
    img.write_bytes(b"\xff\xd8\xff")
    row = {
        "attachment_id": "i1", "filename": "pic.jpg", "mime_type": "image/jpeg",
        "local_path": str(img), "session_id": "s", "channel_type": "discord",
        "size_bytes": 3, "source_url": "", "created_at": "",
    }
    monkeypatch.setattr(svc, "_db_get", lambda aid: row)
    called = {}
    def fake_vision(b64, *, model, prompt=None):
        called["b64"] = b64
        return "a nice photo"
    monkeypatch.setattr(svc, "_call_vision", fake_vision)
    result = svc.read_attachment_content("i1")
    assert result["status"] == "ok"
    assert result["type"] == "image"
    assert "a nice photo" in result["content"]
    assert "b64" in called


# ---------------------------------------------------------------------------
# validate_send_path
# ---------------------------------------------------------------------------

def test_validate_send_path_rejects_outside_roots(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    monkeypatch.setattr(svc, "_ALLOWED_SEND_ROOTS", [tmp_path / "uploads"])
    ok, err = svc.validate_send_path("/etc/passwd")
    assert not ok
    assert "not-allowed" in err


def test_validate_send_path_rejects_missing_file(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setattr(svc, "_ALLOWED_SEND_ROOTS", [uploads])
    ok, err = svc.validate_send_path(str(uploads / "missing.jpg"))
    assert not ok
    assert "not-found" in err


def test_validate_send_path_accepts_valid_file(tmp_path, monkeypatch):
    import core.services.attachment_service as svc
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    f = uploads / "file.jpg"
    f.write_bytes(b"data")
    monkeypatch.setattr(svc, "_ALLOWED_SEND_ROOTS", [uploads])
    ok, err = svc.validate_send_path(str(f))
    assert ok
    assert err == ""


# ---------------------------------------------------------------------------
# list_image_attachments + attachment_visible_to_user (#6 galleri)
# ---------------------------------------------------------------------------
def _store_attachment(svc, *, aid, sid, filename, mime):
    svc._db_store(
        attachment_id=aid, session_id=sid, channel_type="webchat",
        filename=filename, mime_type=mime, size_bytes=10,
        local_path=f"/tmp/{aid}", source_url="",
    )


def test_list_image_attachments_filters_and_scopes(isolated_runtime):
    import core.services.attachment_service as svc
    from core.services.chat_sessions import create_chat_session, append_chat_message

    s = create_chat_session(title="med billede")
    sid = str(s.get("session_id") or s.get("id"))
    append_chat_message(session_id=sid, role="user", content="se her", user_id="u1")

    _store_attachment(svc, aid="img1", sid=sid, filename="a.png", mime="image/png")
    _store_attachment(svc, aid="doc1", sid=sid, filename="a.pdf", mime="application/pdf")

    # u1 ser kun billedet (ikke pdf'en)
    imgs = svc.list_image_attachments(user_id="u1")
    ids = [r["attachment_id"] for r in imgs]
    assert "img1" in ids and "doc1" not in ids

    # u2 deltog ikke i sessionen → ser intet
    assert svc.list_image_attachments(user_id="u2") == []

    # None (owner/legacy) ser billedet
    assert "img1" in [r["attachment_id"] for r in svc.list_image_attachments(user_id=None)]


def test_attachment_visible_to_user(isolated_runtime):
    import core.services.attachment_service as svc
    from core.services.chat_sessions import create_chat_session, append_chat_message

    s = create_chat_session(title="x")
    sid = str(s.get("session_id") or s.get("id"))
    append_chat_message(session_id=sid, role="user", content="hej", user_id="u1")
    _store_attachment(svc, aid="img9", sid=sid, filename="b.jpg", mime="image/jpeg")

    assert svc.attachment_visible_to_user("img9", "u1") is True
    assert svc.attachment_visible_to_user("img9", "u2") is False
    assert svc.attachment_visible_to_user("img9", None) is True   # owner/legacy
    assert svc.attachment_visible_to_user("findes_ikke", "u1") is False


# ── Medie-agnostisk registrering (28/9-2026) ────────────────────────────────
#
# `register_generated_image` tog `mime_type` som parameter men hed «image», og
# video-vaerktoejet kaldte den slet ikke. Den hedder nu
# `register_generated_media`; det gamle navn staar tilbage som indpakning,
# fordi to vaerktoejer kalder det.


def _fang_raekken(monkeypatch, tmp_path):
    """Fang hvad der ville blive skrevet — uden at roere den rigtige DB."""
    from core.services import attachment_service as A
    gemt: dict = {}
    monkeypatch.setattr(A, "_db_store", lambda **kw: gemt.update(kw))
    monkeypatch.setattr(A, "_send_generated_to_channel", lambda *a, **k: None)
    monkeypatch.setattr("core.services.session_context_resolve.aktiv_session_id",
                        lambda: "sess-1")
    fil = tmp_path / "klip.mp4"
    fil.write_bytes(b"ikke rigtig video, men den findes")
    return gemt, fil


def test_video_kan_registreres_med_sin_egen_mime(monkeypatch, tmp_path):
    from core.services.attachment_service import register_generated_media
    gemt, fil = _fang_raekken(monkeypatch, tmp_path)
    aid = register_generated_media(local_path=str(fil), mime_type="video/mp4")
    assert aid
    assert gemt["mime_type"] == "video/mp4"
    assert gemt["filename"] == "klip.mp4"


def test_det_gamle_navn_giver_SAMME_resultat(monkeypatch, tmp_path):
    """Indpakningen skal vaere en indpakning, ikke en anden funktion."""
    from core.services.attachment_service import (
        register_generated_image, register_generated_media)
    gemt_a, fil = _fang_raekken(monkeypatch, tmp_path)
    register_generated_media(local_path=str(fil), mime_type="image/png",
                             source_url="http://x/y.png")
    a = dict(gemt_a)
    gemt_b, _ = _fang_raekken(monkeypatch, tmp_path)
    register_generated_image(local_path=str(fil), mime_type="image/png",
                             source_url="http://x/y.png")
    b = dict(gemt_b)
    for noegle in ("mime_type", "filename", "source_url", "size_bytes", "local_path"):
        assert a[noegle] == b[noegle], noegle


def test_indpakningen_sender_mime_VIDERE(monkeypatch, tmp_path):
    """Hardkodede den «image/jpeg», ville en PNG blive stemplet forkert — og
    ingen anden test ville se det. openrouter_image sender sin egen mime ind."""
    from core.services.attachment_service import register_generated_image
    gemt, fil = _fang_raekken(monkeypatch, tmp_path)
    register_generated_image(local_path=str(fil), mime_type="image/png")
    assert gemt["mime_type"] == "image/png"


def test_indpakningen_har_stadig_sit_gamle_standardvalg(monkeypatch, tmp_path):
    """Kalderne maa kunne udelade mime. Det gamle navn lovede image/jpeg."""
    from core.services.attachment_service import register_generated_image
    gemt, fil = _fang_raekken(monkeypatch, tmp_path)
    register_generated_image(local_path=str(fil))
    assert gemt["mime_type"] == "image/jpeg"


def test_galleriet_er_STADIG_kun_billeder():
    """Bevidst: begge klienter tegner /attachments/images som <img>. En video
    dér ville blive et tomt felt. Video vises i traaden, ikke i galleriet."""
    import inspect
    from core.services import attachment_service as A
    kilde = inspect.getsource(A.list_image_attachments)
    assert kilde.count("LIKE 'image/%'") == 2, (
        "galleriets to forespoergsler skal begge blive ved billeder")
    assert "video/%" not in kilde
