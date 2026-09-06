"""Vedhæftninger som blokke på brugerens besked.

Billeder forsvandt ved genindlæsning: filen lå på disken, men intet knyttede
den til en BESTEMT besked (channel_attachments har session_id, ikke message_id).
Referencerne lægges derfor i beskedens egen content_json.
"""
from __future__ import annotations

import json

from core.services.attachment_blocks import (
    build_attachment_blocks,
    user_message_content_json,
)


def test_billede_og_fil_faar_hver_sin_type():
    out = build_attachment_blocks([
        {"id": "a1", "filename": "foto.jpg", "mime_type": "image/jpeg", "size_bytes": 12},
        {"id": "z1", "filename": "ting.zip", "mime_type": "application/zip"},
    ])
    assert [b["type"] for b in out] == ["image", "file"]
    assert out[0]["attachment_id"] == "a1"
    assert out[0]["size_bytes"] == 12
    # En zip har intet billede at rendere — den skal ikke kunne blive 'image'.
    assert out[1]["type"] == "file"


def test_blokken_baerer_kun_en_reference():
    """Billeddata må ALDRIG ligge i beskeden: hentning går over det user-scopede
    /attachments/image/{id}, og data i beskeden ville omgå den adgangskontrol."""
    out = build_attachment_blocks([
        {"id": "a1", "filename": "f.png", "mime_type": "image/png"},
    ])
    assert set(out[0]) <= {"type", "attachment_id", "filename", "mime_type", "size_bytes"}


def test_poster_uden_id_springes_over():
    """En halv reference er værre end ingen — klienten ville tegne et hul den
    aldrig kan fylde."""
    out = build_attachment_blocks([{"filename": "uden id"}, {"id": "", "filename": "tom"}])
    assert out == []


def test_ukendt_mime_bliver_fil_med_fornuftig_default():
    out = build_attachment_blocks([{"id": "x", "filename": "noget"}])
    assert out[0]["type"] == "file"
    assert out[0]["mime_type"] == "application/octet-stream"


def test_rakkefolge_bevares():
    out = build_attachment_blocks([
        {"id": "1", "filename": "a", "mime_type": "image/png"},
        {"id": "2", "filename": "b", "mime_type": "image/png"},
        {"id": "3", "filename": "c", "mime_type": "image/png"},
    ])
    assert [b["attachment_id"] for b in out] == ["1", "2", "3"]


def test_intet_at_gemme_giver_none_ikke_tom_array():
    """None beholder beskedens hidtidige form; en tom array ville klienten
    skulle skelne fra «ingen blokke»."""
    assert user_message_content_json([]) is None
    assert user_message_content_json([{"filename": "uden id"}]) is None


def test_serialiseringen_er_gyldig_json():
    raw = user_message_content_json([
        {"id": "a1", "filename": "æøå.jpg", "mime_type": "image/jpeg"},
    ])
    parsed = json.loads(raw)
    assert parsed[0]["filename"] == "æøå.jpg"


def test_taaler_skrald_i_listen():
    assert build_attachment_blocks([None, "streng", 42, {"id": "ok", "filename": "f"}]) == [
        {"type": "file", "attachment_id": "ok", "filename": "f",
         "mime_type": "application/octet-stream"}
    ]
