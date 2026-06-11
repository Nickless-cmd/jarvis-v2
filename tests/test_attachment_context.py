"""apply_attachment_context — delt vision-direktiv-blok (v1 + v2)."""
from __future__ import annotations

from apps.api.jarvis_api.routes import attachments as att


def _register(aid: str, filename: str, mime: str, path: str):
    att._registry[aid] = att.AttachmentMeta(
        id=aid, session_id="s", filename=filename, mime_type=mime,
        size_bytes=1, server_path=path,
    )


def test_no_attachments_returns_message_unchanged():
    assert att.apply_attachment_context("hej", None) == "hej"
    assert att.apply_attachment_context("hej", []) == "hej"


def test_image_prepends_analyze_image_directive():
    _register("a1", "foto.png", "image/png", "/uploads/s/a1_foto.png")
    out = att.apply_attachment_context("Hvad er det?", ["a1"])
    assert "analyze_image(image_path='/uploads/s/a1_foto.png')" in out
    assert "Hvad er det?" in out
    assert out.endswith("Hvad er det?")


def test_nonimage_prepends_read_file_directive():
    _register("a2", "noter.txt", "text/plain", "/uploads/s/a2_noter.txt")
    out = att.apply_attachment_context("", ["a2"])
    assert "read_file(path='/uploads/s/a2_noter.txt')" in out


def test_unknown_id_skipped():
    assert att.apply_attachment_context("hej", ["does-not-exist"]) == "hej"
