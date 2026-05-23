"""Tests for spatial_entity_ledger.py (Step D.v1).

Lexicon-based entity extraction from visual sensory descriptions +
co-occurrence ledger. No geometry — just "what's in the room with what".
"""
import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = Path(tmp.name)
    import core.services.spatial_entity_ledger as mod
    monkeypatch.setattr(mod, "DB_PATH", path)
    yield path
    path.unlink(missing_ok=True)


# ── Extraction ───────────────────────────────────────────────────────────


def test_extracts_room_furniture():
    from core.services.spatial_entity_ledger import extract_entities
    text = "En person sidder i sofaen og kigger på skærmen ved skrivebordet."
    found = extract_entities(text)
    assert "sofa" in found
    assert "skærm" in found
    assert "skrivebord" in found
    assert "person" in found


def test_lemmatizes_definite_suffixes():
    """vinduet → vindue, døren → dør, etc."""
    from core.services.spatial_entity_ledger import extract_entities
    text = "Lyset strømmer ind fra vinduet. Døren er åben."
    found = extract_entities(text)
    assert "vindue" in found
    assert "dør" in found
    assert "vinduet" not in found  # lemmatized away
    assert "døren" not in found


def test_drops_atmosphere_words():
    """'rum', 'stemning', 'atmosfære' are not entities."""
    from core.services.spatial_entity_ledger import extract_entities
    text = "Rummet har en tung atmosfære og en kølig stemning."
    found = extract_entities(text)
    assert "rum" not in found
    assert "atmosfære" not in found
    assert "stemning" not in found


def test_empty_text_no_entities():
    from core.services.spatial_entity_ledger import extract_entities
    assert extract_entities("") == set()
    assert extract_entities("Bare en tekst uden møbler eller folk.") == set()


# ── record_observation ──────────────────────────────────────────────────


def test_record_observation_inserts(tmp_db):
    from core.services.spatial_entity_ledger import (
        record_observation, list_observed_entities,
    )
    record_observation("En person sidder i sofaen ved skrivebordet.")
    entities = list_observed_entities()
    labels = {e["entity_label"] for e in entities}
    assert {"sofa", "skrivebord", "person"} <= labels


def test_record_observation_increments_count(tmp_db):
    from core.services.spatial_entity_ledger import (
        record_observation, list_observed_entities,
    )
    record_observation("Personen sidder ved skærmen.")
    record_observation("Skærmen viser kode.")
    entities = list_observed_entities()
    skærm = next(e for e in entities if e["entity_label"] == "skærm")
    assert skærm["observation_count"] == 2


def test_co_occurrence_tracked(tmp_db):
    from core.services.spatial_entity_ledger import (
        record_observation, co_entities_for,
    )
    record_observation("Personen sidder i sofaen ved vinduet.")
    record_observation("En person læser ved vinduet i sofaen.")
    co = co_entities_for("sofa")
    co_dict = dict(co)
    # sofa co-occurs with vindue both times
    assert co_dict.get("vindue", 0) >= 2
    assert co_dict.get("person", 0) >= 2


def test_empty_observation_records_nothing(tmp_db):
    from core.services.spatial_entity_ledger import (
        record_observation, list_observed_entities,
    )
    result = record_observation("Tom sky med ingen objekter.")
    assert result["recorded"] == 0
    assert list_observed_entities() == []


# ── Awareness surface ───────────────────────────────────────────────────


def test_section_quiet_when_few_entities(tmp_db):
    from core.services.spatial_entity_ledger import (
        record_observation, room_entities_section,
    )
    record_observation("En kop står på bordet.")
    # only 2 entities (kop, bord) — below threshold of 3
    assert room_entities_section() is None


def test_section_surfaces_when_enough_data(tmp_db):
    from core.services.spatial_entity_ledger import (
        record_observation, room_entities_section,
    )
    record_observation(
        "Personen sidder i sofaen ved skrivebordet med en kop "
        "kaffe og kigger på skærmen."
    )
    section = room_entities_section()
    assert section is not None
    assert "Rummets faste entiteter" in section
    assert "sofa" in section


# ── Backfill ─────────────────────────────────────────────────────────────


def test_backfill_processes_historical_rows(tmp_db, monkeypatch):
    """Backfill should pull visual rows from sensory_memories and count
    entities. We create a fake sensory_memories table in the tmp db."""
    from core.services.spatial_entity_ledger import (
        backfill_from_existing, list_observed_entities,
    )
    with sqlite3.connect(str(tmp_db)) as conn:
        conn.execute(
            """CREATE TABLE sensory_memories (
                id INTEGER PRIMARY KEY,
                modality TEXT, content TEXT, timestamp TEXT
            )"""
        )
        conn.execute(
            "INSERT INTO sensory_memories(modality, content, timestamp) "
            "VALUES ('visual', 'Personen sidder i sofaen ved vinduet.', "
            "'2026-05-23T10:00:00+00:00'), "
            "('visual', 'Skærmen viser tekst på skrivebordet.', "
            "'2026-05-23T11:00:00+00:00'), "
            "('audio', 'Lyden af regn.', '2026-05-23T12:00:00+00:00')"
        )
        conn.commit()
    out = backfill_from_existing()
    # Both visual rows have ≥1 entity each
    assert out["processed_observations"] == 2
    labels = {e["entity_label"] for e in list_observed_entities()}
    assert "sofa" in labels
    assert "skærm" in labels
    # audio rows ignored — no audio-only entities expected
