"""PDF-connector: læs/ekstraher (blank PDF-fixture + fejlstier)."""
from __future__ import annotations

import io

import core.services.pdf_connector as pc


def _blank_pdf(pages: int = 2) -> bytes:
    from pypdf import PdfWriter
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def test_read_pdf_from_path(tmp_path):
    p = tmp_path / "t.pdf"
    p.write_bytes(_blank_pdf(3))
    res = pc.read_pdf(str(p), max_pages=2)
    assert res["status"] == "ok"
    assert res["total_pages"] == 3
    assert res["pages_read"] == 2
    assert res["truncated"] is True  # 2 < 3
    assert isinstance(res["text"], str)


def test_source_required():
    assert pc.read_pdf("")["error"] == "source_required"


def test_file_not_found(tmp_path):
    assert pc.read_pdf(str(tmp_path / "nope.pdf"))["error"] == "file_not_found"


def test_url_fetch(monkeypatch):
    import httpx

    class _R:
        status_code = 200
        content = _blank_pdf(1)

    monkeypatch.setattr(httpx, "get", lambda *a, **k: _R())
    res = pc.read_pdf("https://x/y.pdf")
    assert res["status"] == "ok" and res["total_pages"] == 1


def test_url_http_error(monkeypatch):
    import httpx

    class _R:
        status_code = 404
        content = b""

    monkeypatch.setattr(httpx, "get", lambda *a, **k: _R())
    assert pc.read_pdf("https://x/missing.pdf")["error"] == "fetch_http_404"
