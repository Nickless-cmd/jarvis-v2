"""Task 5 (memory repair 2026-09-04): the lessons store."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from core.runtime import db_lessons as L


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "lessons.sqlite"

    def _connect():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(L, "connect", _connect)
    return path


def test_signature_key_normalizes():
    assert L.signature_key("Correction: PfSense-nøglen, i .env!") == L.signature_key("correction pfsense nøglen env")
    assert L.signature_key("og i at det") == ""


def test_upsert_twice_same_signature_reinforces_and_activates(db):
    a = L.upsert_lesson(signature="tool_error: bash: command not found", lesson="Bash fejlede: command not found", source=L.SOURCE_TOOL_ERROR)
    assert a["outcome"] == "created" and a["status"] == "proposed" and a["evidence_count"] == 1
    b = L.upsert_lesson(signature="tool_error: bash: command not found", lesson="Bash fejlede igen", source=L.SOURCE_TOOL_ERROR)
    assert b["outcome"] == "reinforced" and b["status"] == "active" and b["evidence_count"] == 2
    assert L.count_lessons() == 1


def test_repeat_on_active_lesson_counts_closure(db):
    L.upsert_lesson(signature="correction: pfsense nøgle", lesson="Bjørn rettede mig", source=L.SOURCE_CORRECTION)
    r = L.upsert_lesson(signature="correction: pfsense nøgle", lesson="Bjørn rettede mig igen", source=L.SOURCE_CORRECTION)
    assert r["outcome"] == "repeated"
    assert r["repeated_count"] == 1 and r["evidence_count"] == 2
    assert r["last_repeated_at"]


def test_correction_is_active_immediately(db):
    r = L.upsert_lesson(signature="correction: mic gain", lesson="…", source=L.SOURCE_CORRECTION)
    assert r["status"] == "active"


def test_fuzzy_signature_match(db):
    L.upsert_lesson(signature="tool_error: web_fetch: timeout after 30s on api.srvlab.dk", lesson="x", source=L.SOURCE_TOOL_ERROR)
    r = L.upsert_lesson(signature="tool_error: web_fetch: timeout after 30s on api.srvlab.dk retry", lesson="y", source=L.SOURCE_TOOL_ERROR)
    assert r["outcome"] == "reinforced"
    assert L.count_lessons() == 1


def test_list_and_find_similar(db):
    L.upsert_lesson(signature="correction: pfsense nøgle env", lesson="Bjørn rettede mig: pfsense-nøglen bor i .env, ikke i koden", source=L.SOURCE_CORRECTION)
    L.upsert_lesson(signature="correction: mikrofon gain", lesson="Bjørn rettede mig: mikrofonens gain må ikke dumpes ved TTS", source=L.SOURCE_CORRECTION)
    L.upsert_lesson(signature="self_review: verificér", lesson="Verificér før jeg påstår", source=L.SOURCE_SELF_REVIEW)
    active = L.list_lessons(status="active")
    assert {l["signature"] for l in active} == {"correction: pfsense nøgle env", "correction: mikrofon gain"}
    sim = L.find_similar_lessons("hvor ligger pfsense nøglen?", limit=1)
    assert sim and "pfsense" in sim[0]["lesson"]


def test_retire_stale_keeps_corrections(db):
    old = (datetime.now(UTC) - timedelta(days=40)).isoformat()
    L.upsert_lesson(signature="self_review: gammel", lesson="gammel lektie uden evidens", source=L.SOURCE_SELF_REVIEW, now=old)
    L.upsert_lesson(signature="correction: gammel rettelse", lesson="rettelse", source=L.SOURCE_CORRECTION, now=old)
    n = L.retire_stale(days=30)
    assert n == 1
    assert L.count_lessons(status="retired") == 1
    assert L.list_lessons(status="active")[0]["source"] == L.SOURCE_CORRECTION
