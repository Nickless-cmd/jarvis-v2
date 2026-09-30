"""Tests for habits_pipeline — tærskel-gating og forslags-livscyklus.

Tilføjet 2026-10-01 ifm. at forslags-tærsklen blev hævet 2→8
(prop-f644b92a13a94734). Baggrund: tærsklen 2 gav 6.773 forslag på
5½ måned, alle `pending`, ingen nogensinde læst — `accept_suggestion`
havde nul kaldesteder i hele repoet.

Testen pinner at tærsklen faktisk gater, så den ikke kan skride tilbage
uden at en test ser det. Den dokumenterer OGSÅ at friction-vejen har sin
egen, lavere tærskel — så man ikke tror loftet løste hele støjen.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pytest


@pytest.fixture()
def habits_db(tmp_path, monkeypatch):
    """Isolér habits_pipeline mod en temp-DB — rører ALDRIG prod-DB'en."""
    from core.services import habits_pipeline as hp

    db_path = tmp_path / "habits.db"

    @contextmanager
    def _connect():
        con = sqlite3.connect(str(db_path))
        con.row_factory = sqlite3.Row
        try:
            yield con
        finally:
            con.close()

    monkeypatch.setattr(hp, "connect", _connect)
    return hp


def test_taersklen_er_8(habits_db):
    """Pin tærsklen — den stod på 2 og gav 6.773 døde forslag."""
    assert habits_db._HABIT_SUGGEST_THRESHOLD == 8


def test_normalize_signature_er_ren_og_stabil(habits_db):
    """Signaturer normaliseres (lowercase, tegn fjernet) og er stabile."""
    assert habits_db._normalize_signature("   ") == ""
    assert habits_db._normalize_signature("") == ""
    # Samme besked i forskellig form → samme signatur (det er pointen).
    assert habits_db._normalize_signature("Kør   DE 3!!") == habits_db._normalize_signature("kør de 3")
    # æøå bevares, tegnsætning fjernes.
    assert habits_db._normalize_signature("Kør de 3!!").startswith("kør de 3:")


def test_ingen_habit_forslag_under_taersklen(habits_db):
    """7 gentagelser må IKKE give et habit-forslag (tærsklen er 8)."""
    for _ in range(7):
        habits_db.record_habit_signal(message="gentag mig syv gange")
    forslag = habits_db.list_suggestions(status="pending")
    habit_forslag = [s for s in forslag if s["source_type"] == "habit"]
    assert habit_forslag == []


def test_habit_forslag_ved_taersklen(habits_db):
    """8. gentagelse giver præcis ét habit-forslag — ikke et pr. kald."""
    events: list[dict] = []
    for _ in range(8):
        events.extend(habits_db.record_habit_signal(message="gentag mig otte gange"))
    oprettede = [
        e for e in events
        if e["type"] == "automation_suggestion_created" and e["source_type"] == "habit"
    ]
    assert len(oprettede) == 1


def test_friction_vejen_har_sin_egen_lavere_taerskel(habits_db):
    """Dokumenterer at habit-loftet (8) IKKE stopper alle forslag.

    Friction-vejen fyrer når `inefficiency_score >= 0.75`, og scoren er
    `repetition / 3.0` — altså ved 3. gentagelse. Det er værd at vide, før
    man tror tærskel-ændringen fjernede hele støjen.
    """
    for _ in range(3):
        habits_db.record_habit_signal(message="friktions-besked")
    forslag = habits_db.list_suggestions(status="pending")
    friction_forslag = [s for s in forslag if s["source_type"] == "friction"]
    assert len(friction_forslag) == 1


def test_accept_og_reject_aendrer_status(habits_db):
    """Aktøren virker: forslag kan lukkes — og ukendt id giver None, ikke crash."""
    for _ in range(8):
        habits_db.record_habit_signal(message="accepter mig")
    forslag = habits_db.list_suggestions(status="pending")
    assert forslag, "forventede mindst ét forslag efter 8 gentagelser"
    sid = forslag[0]["id"]

    accepteret = habits_db.accept_suggestion(suggestion_id=sid)
    assert accepteret is not None
    assert accepteret["status"] == "accepted"
    # Det accepterede forslag er ude af pending-køen. Der kan ligge ANDRE —
    # friction-vejen har sin egen, lavere tærskel og fyrer allerede ved 3.
    pending_ids = [s["id"] for s in habits_db.list_suggestions(status="pending")]
    assert sid not in pending_ids

    # Ukendt id → None (ikke en exception).
    assert habits_db.accept_suggestion(suggestion_id="findes-ikke") is None
    assert habits_db.reject_suggestion(suggestion_id="findes-ikke") is None
