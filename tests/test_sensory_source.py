"""Tests for sensory_source — kilde-navnene skal være et endeligt sæt.

Kernen i testen er den beslutning der er let at tage fejl af: at et *ukendt*
kildenavn ikke må forsvinde. Vi kan ikke gætte hvad det var, men vi må ikke
tabe det — derfor skal `source_raw` bære den rå streng videre.
"""
from __future__ import annotations

import json

import pytest

from core.services.sensory_source import (
    CANONICAL_SOURCES,
    canonical_source,
    normalize_metadata,
)


def test_kanoniske_navne_er_et_lukket_saet():
    assert "ukendt" in CANONICAL_SOURCES
    assert len(CANONICAL_SOURCES) == len(set(CANONICAL_SOURCES))
    # Ethvert navn der kommer ud af normaliseringen skal ligge i sættet.
    for raa in ("nightly_dive", "syntese", "manual_test", "look_around"):
        assert canonical_source(raa) in CANONICAL_SOURCES


@pytest.mark.parametrize(
    "raa,forventet",
    [
        # De tre stavemåder af samme nat-dyk skal mødes på ét navn.
        ("nightly_dive", "dybdesession"),
        ("natlig_dyk", "dybdesession"),
        ("natligt-dyk", "dybdesession"),
        ("natlig dyk", "dybdesession"),
        ("deep-dive-session", "dybdesession"),
        ("nocturnal_dive_synthesis", "synthesis"),
        # Syntesen
        ("syntese", "synthesis"),
        ("synthesis_visual_audio_context", "synthesis"),
        # Rutinen
        ("night_routine", "natrutine"),
        ("evening_routine", "natrutine"),
        # Udledt
        ("extrapolated (mic unavailable)", "ekstrapoleret"),
        ("mic_listen_failed", "ekstrapoleret"),
        # Test-støj
        ("manual_test", "test"),
        ("verification-test", "test"),
        # Uændrede
        ("visual_memory_daemon", "visual_memory_daemon"),
        ("look_around", "look_around"),
    ],
)
def test_varianter_moedes(raa, forventet):
    assert canonical_source(raa) == forventet


def test_sammensat_streng_tager_den_forste_producent():
    # «look_around + mic_listen» er ikke en kilde men en begivenhed.
    assert canonical_source("look_around + mic_listen") == "look_around"
    assert canonical_source("mic_listen + ambient_sound_daemon") == "mic_listen"
    assert canonical_source("night_routine+look_around") == "natrutine"
    assert canonical_source("mic_listen/arecord") == "mic_listen"


def test_tom_og_none_bliver_ukendt():
    assert canonical_source(None) == "ukendt"
    assert canonical_source("") == "ukendt"
    assert canonical_source("   ") == "ukendt"


def test_ukendt_navn_tabes_ikke():
    meta = normalize_metadata({"source": "en_helt_ny_daemon", "location": "stuen"})
    assert meta["source"] == "ukendt"
    assert meta["source_raw"] == "en_helt_ny_daemon"
    # Andre nøgler røres ikke.
    assert meta["location"] == "stuen"


def test_kendt_navn_faar_ikke_source_raw():
    meta = normalize_metadata({"source": "look_around"})
    assert meta["source"] == "look_around"
    assert "source_raw" not in meta


def test_normalize_metadata_roerer_ikke_input():
    raa = {"source": "nightly_dive"}
    ud = normalize_metadata(raa)
    assert raa["source"] == "nightly_dive"  # kalderens dict er urørt
    assert ud["source"] == "dybdesession"


def test_normalize_metadata_taaler_none():
    assert normalize_metadata(None)["source"] == "ukendt"
    assert normalize_metadata({})["source"] == "ukendt"


def test_skrivevejen_normaliserer_kilden(monkeypatch):
    """_record er choke-pointet — kilden skal være kanonisk inden den gemmes."""
    from core.services import sensory_archive

    fanget = {}

    def falsk_insert(**kwargs):
        fanget.update(kwargs)
        return {"id": "x", "timestamp": "2026-09-28T00:00:00Z"}

    monkeypatch.setattr(sensory_archive, "insert_sensory_memory", falsk_insert)
    monkeypatch.setattr(sensory_archive.event_bus, "publish", lambda *a, **k: None)

    sensory_archive.record_visual(
        "Lyset faldt diagonalt over skrivebordet i eftermiddagen.",
        metadata={"source": "natligt_dyk"},
    )
    assert fanget["metadata"]["source"] == "dybdesession"
    assert fanget["metadata"]["source_raw"] == "natligt_dyk"
    assert json.dumps(fanget["metadata"])  # stadig JSON-serialiserbar
