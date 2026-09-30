"""Tests for habits_pipeline — tærskel-gating og forslags-livscyklus.

Tilføjet 2026-10-01 ifm. at forslags-tærsklen blev hævet 2→8
(prop-f644b92a13a94734). Baggrund: tærsklen 2 gav 6.773 forslag på
5½ måned, alle `pending`, ingen nogensinde læst — `accept_suggestion`
havde nul kaldesteder i hele repoet.

Fase 3 (samme dag): OGSÅ friction-vejen var for lav — scoren var
`repetition / 3.0` og tærsklen 0.75, så den fyrede ved 3. gentagelse.
Da begge veje fodres af samme besked, gav ét mønster to forslag. Nu
rammer begge tærskler 8 gentagelser.

Testen pinner at tærsklerne faktisk gater, så de ikke kan skride tilbage
uden at en test ser det.
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


def test_friction_vejen_fyrer_ved_samme_taerskel_som_habit(habits_db):
    """Fase 3 (2026-10-01): friction fyrer ved 8 gentagelser — ikke ved 3.

    Før: scoren var `repetition / 3.0` klippet til max 1.0, og tærsklen stod
    på 0.75 — så den fyrede ved 3. gentagelse. Da begge veje fodres af SAMME
    besked i `record_habit_signal`, gav ét mønster to forslag.
    """
    # 7 gentagelser: scoren er 7/8 = 0.875 < 1.0 → intet friction-forslag.
    for _ in range(7):
        habits_db.record_habit_signal(message="friktions-besked")
    forslag = habits_db.list_suggestions(status="pending")
    assert [s for s in forslag if s["source_type"] == "friction"] == []

    # 8. gentagelse rammer loftet 1.0 → præcis ét friction-forslag.
    habits_db.record_habit_signal(message="friktions-besked")
    forslag = habits_db.list_suggestions(status="pending")
    friction_forslag = [s for s in forslag if s["source_type"] == "friction"]
    assert len(friction_forslag) == 1


def test_friction_skalaen_rammer_loftet_ved_otte(habits_db):
    """Pin at loftet nås ved 8.

    Fælden denne test vogter imod: scoren er klippet til max 1.0, så en
    fremtidig 'hæv tærsklen til 2.0'-rettelse ville gøre den UOPNÅELIG og
    friction-vejen ville tie for evigt. Skalaen skal ændres, ikke tærsklen.
    """
    assert habits_db._FRICTION_SCALE == 8.0
    assert habits_db._FRICTION_SUGGEST_THRESHOLD <= 1.0

    habits_db._ensure_tables()
    sig = habits_db._normalize_signature("skala-test")
    fid, repetition, ineff = habits_db._upsert_friction(sig, habits_db._now_iso())
    assert (repetition, ineff) == (1, 0.125)
    for _ in range(7):
        fid, repetition, ineff = habits_db._upsert_friction(sig, habits_db._now_iso())
    assert repetition == 8
    assert ineff == 1.0


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
    # friction-vejen har sin egen kilde og fyrer nu ved samme tærskel (8).
    pending_ids = [s["id"] for s in habits_db.list_suggestions(status="pending")]
    assert sid not in pending_ids

    # Ukendt id → None (ikke en exception).
    assert habits_db.accept_suggestion(suggestion_id="findes-ikke") is None
    assert habits_db.reject_suggestion(suggestion_id="findes-ikke") is None


def test_format_pending_suggestions_tom_naar_der_intet_er(habits_db):
    """Ingen ventende forslag → tom streng, så heartbeat-linjen udelades."""
    assert habits_db.format_pending_suggestions_for_heartbeat() == ""


def test_format_pending_suggestions_viser_id_og_signatur(habits_db):
    """Fase 2: linjen bærer id'et (så forslaget KAN lukkes) og den FAKTISKE
    signatur — ikke forslagets konstante suggestion_text."""
    for _ in range(8):
        habits_db.record_habit_signal(message="ryd op i rodet")
    linje = habits_db.format_pending_suggestions_for_heartbeat()
    assert linje, "forventede en linje efter 8 gentagelser"
    # Signaturen skal stå i klartekst — det er hele pointen med opslaget.
    assert "ryd op i rodet" in linje
    # Mindst ét ventende forslags id skal være med, så det kan lukkes.
    ids = [s["id"] for s in habits_db.list_suggestions(status="pending")]
    assert any(i in linje for i in ids)
    # Den konstante tekst må IKKE være det man ser.
    assert "scheduled workflow" not in linje


def test_format_pending_suggestions_respekterer_max_items(habits_db):
    """max_items gater antallet af viste forslag."""
    for i in range(10):
        for _ in range(8):
            habits_db.record_habit_signal(message=f"unikt moenster nummer {i}")
    assert habits_db.format_pending_suggestions_for_heartbeat(max_items=1).count("[") == 1
    assert habits_db.format_pending_suggestions_for_heartbeat(max_items=3).count("[") == 3
