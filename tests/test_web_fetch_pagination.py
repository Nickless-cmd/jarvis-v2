from __future__ import annotations

import contextlib

import core.tools.simple_tools_web as web


def test_html_to_text_preserves_paragraphs():
    html = "<html><body><h1>Titel</h1><p>Første afsnit.</p><p>Andet afsnit.</p>" \
           "<script>junk()</script><style>.x{}</style></body></html>"
    out = web._html_to_text(html)
    assert "Titel" in out
    assert "Første afsnit." in out
    assert "Andet afsnit." in out
    assert "junk()" not in out and ".x{}" not in out
    # afsnit adskilt af linjeskift (ikke kollapset til én linje)
    assert "\n" in out


def test_html_to_text_self_safe_on_garbage():
    assert web._html_to_text(None) == ""
    assert isinstance(web._html_to_text("<p>hej"), str)


class _FakeResp:
    def __init__(self, body: str):
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _patch_fetch(monkeypatch, html: str):
    monkeypatch.setattr(web.urllib_request, "urlopen", lambda req, timeout=15: _FakeResp(html))


def test_web_fetch_paginates_long_page(monkeypatch):
    # Byg en side markant længere end vinduet, med unikt indhold i MIDTEN.
    limit = web.MAX_WEB_FETCH_CHARS
    body = "<p>" + ("A" * limit) + "</p><p>MIDTMARKØR</p><p>" + ("B" * limit) + "</p>"
    _patch_fetch(monkeypatch, body)

    first = web._exec_web_fetch({"url": "http://x"})
    assert first["status"] == "ok"
    assert first["offset"] == 0
    assert first["has_more"] is True
    assert first["next_offset"] == first["returned"]
    assert first["total_chars"] > limit
    assert "offset=" in first["text"]  # fortsættelses-hint

    # Side-blad videre til midten — MIDTMARKØR må kunne nås (ikke tabt).
    seen = first["text"]
    off = first["next_offset"]
    for _ in range(10):
        nxt = web._exec_web_fetch({"url": "http://x", "offset": off})
        seen += nxt["text"]
        if not nxt["has_more"]:
            break
        off = nxt["next_offset"]
    assert "MIDTMARKØR" in seen


def test_web_fetch_short_page_no_pagination(monkeypatch):
    _patch_fetch(monkeypatch, "<p>kort side</p>")
    r = web._exec_web_fetch({"url": "http://x"})
    assert r["has_more"] is False
    assert r["next_offset"] is None
    assert "kort side" in r["text"]
    assert "offset=" not in r["text"]


def test_web_fetch_offset_past_end(monkeypatch):
    _patch_fetch(monkeypatch, "<p>lille</p>")
    r = web._exec_web_fetch({"url": "http://x", "offset": 999999})
    assert r["status"] == "ok"
    assert r["returned"] == 0
    assert "forbi sidens slut" in r["text"]


def test_web_fetch_bad_offset_defaults_to_zero(monkeypatch):
    _patch_fetch(monkeypatch, "<p>hej</p>")
    r = web._exec_web_fetch({"url": "http://x", "offset": "garbage"})
    assert r["offset"] == 0
    assert "hej" in r["text"]
