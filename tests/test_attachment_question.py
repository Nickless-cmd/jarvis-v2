"""Han skal kunne spørge billedet, ikke kun få et resumé (2026-09-05).

Målt samme dag: han HAR øjne — gemma4:31b-cloud via ollama læste både
farvekoder og småtekst korrekt på 0,5 s, gratis. Men vision-prompten var
hårdkodet til «beskriv kortfattet», så ethvert senere spørgsmål blev besvaret
ud fra ét generisk resumé skrevet før spørgsmålet fandtes.
"""
from __future__ import annotations

import pytest

from core.services import attachment_service as AS
from core.tools import simple_tools_native as STN


@pytest.fixture
def image(tmp_path, monkeypatch):
    path = tmp_path / "skaerm.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 40)
    monkeypatch.setattr(AS, "_db_get", lambda _id: {
        "mime_type": "image/png", "local_path": str(path), "filename": "skaerm.png"})
    monkeypatch.setattr(AS, "_vision_model", lambda: "gemma4:31b-cloud")
    seen: dict = {}

    def _vision(b64, *, model, prompt=None):
        seen["prompt"] = prompt
        seen["model"] = model
        return "backup er rød"

    monkeypatch.setattr(AS, "_call_vision", _vision)
    return seen


def test_without_a_question_it_still_describes(image):
    out = AS.read_attachment_content("a1")
    assert out["status"] == "ok" and out["type"] == "image"
    assert image["prompt"] == AS._GENERIC_IMAGE_PROMPT
    assert out["question"] == ""


def test_a_question_reaches_the_pixels(image):
    out = AS.read_attachment_content("a1", question="hvilken række er rød?")
    assert "hvilken række er rød?" in image["prompt"]
    assert "kun ud fra hvad du faktisk kan se" in image["prompt"]
    assert out["question"] == "hvilken række er rød?"


def test_whitespace_only_counts_as_no_question(image):
    AS.read_attachment_content("a1", question="   \n  ")
    assert image["prompt"] == AS._GENERIC_IMAGE_PROMPT


def test_the_tool_passes_the_question_on(monkeypatch):
    seen: dict = {}
    monkeypatch.setattr(
        "core.services.attachment_service.read_attachment_content",
        lambda aid, question="": seen.update(aid=aid, question=question) or {
            "status": "ok", "content": "backup er rød", "type": "image",
            "filename": "skaerm.png", "question": question})
    out = STN._exec_read_attachment(
        {"attachment_id": "a1", "question": "hvilken række er rød?"})
    assert seen == {"aid": "a1", "question": "hvilken række er rød?"}
    assert "spørgsmål: hvilken række er rød?" in out["text"]
    assert "backup er rød" in out["text"]


def test_the_tool_still_works_without_a_question(monkeypatch):
    monkeypatch.setattr(
        "core.services.attachment_service.read_attachment_content",
        lambda aid, question="": {"status": "ok", "content": "et skærmbillede",
                                  "type": "image", "filename": "s.png", "question": ""})
    out = STN._exec_read_attachment({"attachment_id": "a1"})
    assert out["status"] == "ok" and "spørgsmål:" not in out["text"]


def test_the_schema_advertises_the_question():
    """Kan han ikke SE parameteren i sit vaerktoej, findes den ikke for ham."""
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS
    spec = next(t for t in TOOL_DEFINITIONS
                if (t.get("function") or {}).get("name") == "read_attachment")
    props = spec["function"]["parameters"]["properties"]
    assert "question" in props
    assert "attachment_id" in spec["function"]["parameters"]["required"]
    assert "question" not in spec["function"]["parameters"]["required"]


def test_a_non_image_ignores_the_question(tmp_path, monkeypatch):
    path = tmp_path / "note.txt"
    path.write_text("hej", encoding="utf-8")
    monkeypatch.setattr(AS, "_db_get", lambda _id: {
        "mime_type": "text/plain", "local_path": str(path), "filename": "note.txt"})
    out = AS.read_attachment_content("a1", question="hvad er farven?")
    assert out["type"] == "text" and "hej" in out["content"]
