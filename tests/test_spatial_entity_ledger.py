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


# ── Tavse fald skal efterlade et spor (31/10-2026) ───────────────────────
#
# MAALT 31/10-2026: fire `except` i denne fil returnerede `[]`. For kalderen
# var «ingen entiteter observeret» og «databasen kunne ikke laeses» identiske,
# saa `room_entities_section` tavst forsvandt ud af prompten uden at nogen
# kunne se hvorfor. Fail-soft er bevaret — det der er tilfoejet er et spor.
#
# Vagterne beviser BEGGE ting: at fejlen logger, OG at returvaerdien stadig
# er den tomme liste kalderne forventer. Uden den anden halvdel ville en
# rettelse der kastede videre bestaa testen.


def _braek_connect(monkeypatch, exc: Exception):
    """Erstat `_connect` med noget der kaster."""
    import core.services.spatial_entity_ledger as mod

    def _boom():
        raise exc

    monkeypatch.setattr(mod, "_connect", _boom)


def test_list_observed_entities_logger_men_returnerer_tom(monkeypatch, caplog):
    import logging

    import core.services.spatial_entity_ledger as mod

    _braek_connect(monkeypatch, sqlite3.OperationalError("db locked"))
    with caplog.at_level(logging.WARNING, logger="core.services.spatial_entity_ledger"):
        out = mod.list_observed_entities()
    assert out == []  # fail-soft bevaret
    assert any(
        "kunne ikke liste entiteter" in r.getMessage() for r in caplog.records
    ), "et DB-sammenbrud efterlod intet spor"


def test_co_entities_for_logger_men_returnerer_tom(monkeypatch, caplog):
    import logging

    import core.services.spatial_entity_ledger as mod

    _braek_connect(monkeypatch, sqlite3.OperationalError("db locked"))
    with caplog.at_level(logging.WARNING, logger="core.services.spatial_entity_ledger"):
        out = mod.co_entities_for("sofa")
    assert out == []
    assert any("kunne ikke laese naboer" in r.getMessage() for r in caplog.records)


def test_co_entities_for_logger_ugyldig_json(tmp_db, caplog):
    """Ugyldig co_entities_json er ikke «ingen naboer» — det er korrupt data."""
    import logging

    import core.services.spatial_entity_ledger as mod

    with mod._connect() as conn:
        conn.execute(
            "INSERT INTO room_entity_observations "
            "(entity_label, observation_count, first_seen_at, last_seen_at, "
            " co_entities_json, latest_excerpt) VALUES (?, 1, ?, ?, ?, ?)",
            ("sofa", "2026-10-31T00:00:00+00:00", "2026-10-31T00:00:00+00:00",
             "{ikke json", "en sofa"),
        )
        conn.commit()

    with caplog.at_level(logging.WARNING, logger="core.services.spatial_entity_ledger"):
        out = mod.co_entities_for("sofa")
    assert out == []
    assert any(
        "ugyldig co_entities_json" in r.getMessage() for r in caplog.records
    )


def test_recently_observed_logger_men_returnerer_tom(monkeypatch, caplog):
    import logging

    import core.services.spatial_entity_ledger as mod

    _braek_connect(monkeypatch, sqlite3.OperationalError("db locked"))
    with caplog.at_level(logging.WARNING, logger="core.services.spatial_entity_ledger"):
        out = mod.recently_observed()
    assert out == []
    assert any(
        "kunne ikke laese seneste observationer" in r.getMessage()
        for r in caplog.records
    )


def test_normal_tom_tilstand_stoejer_ikke(tmp_db, caplog):
    """En TOM base er normal drift — den maa ikke fylde loggen.

    Uden denne vagt ville de fire rettelser goere loggen ubrugelig: hver
    tom laesning ved opstart ville se ud som en fejl.
    """
    import logging

    import core.services.spatial_entity_ledger as mod

    with caplog.at_level(logging.WARNING, logger="core.services.spatial_entity_ledger"):
        assert mod.list_observed_entities() == []
        assert mod.recently_observed() == []
        assert mod.co_entities_for("sofa") == []
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == [], (
        "normal tom tilstand loggede som fejl"
    )
