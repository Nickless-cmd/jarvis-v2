"""Tests for write_handover — min egen overdragelse ind i CONTINUITY-capsulen.

Den vigtigste påstand her er ikke at feltet kan skrives. Det er at det
OVERLEVER: ``capture_state`` bygger en frisk capsule for hver tur og kopierer
kun de sektioner den selv kender — så uden en eksplicit arve-linje ville
overdragelsen forsvinde efter næste tur, og så var den meningsløs.
"""
from __future__ import annotations

import json

import pytest

import core.services.continuity as c
import core.services.handover_tools as ht


@pytest.fixture
def capsule_dir(tmp_path, monkeypatch):
    """Omdiriger capsule-stierne til en tmp-mappe — rør ikke den rigtige."""
    monkeypatch.setattr(c, "CAPSULE_DIR", tmp_path)
    monkeypatch.setattr(c, "CAPSULE_CURRENT", tmp_path / "session_capsule.json")
    monkeypatch.setattr(c, "CAPSULE_PREV", tmp_path / "session_capsule.prev.json")
    monkeypatch.setattr(c, "CAPSULE_OLDER", tmp_path / "session_capsule.older.json")
    return tmp_path


# ── skrivning ─────────────────────────────────────────────────────────


def test_skriv_og_laes(capsule_dir):
    r = c.write_handover("Midt i rail-arbejdet", "Fem rettelser landet. Test grøn.")
    assert r["status"] == "ok"
    assert r["title"] == "Midt i rail-arbejdet"
    assert r["trunkeret"] is False

    læst = c.read_handover()
    assert læst["title"] == "Midt i rail-arbejdet"
    assert "Test grøn" in læst["text"]
    assert læst["written_by"] == "jarvis"
    assert læst["written_at"]  # tidsstempel sat


def test_tom_tekst_afvises_og_skriver_intet(capsule_dir):
    r = c.write_handover("kun en titel", "   ")
    assert r["status"] == "error"
    assert "tom overdragelse" in r["error"]
    assert c.read_handover() is None  # intet skrevet


def test_trunkerer_ved_loftet(capsule_dir):
    r = c.write_handover("lang", "x" * (c._MAX_HANDOVER_CHARS + 500))
    assert r["status"] == "ok"
    assert r["trunkeret"] is True
    assert r["chars"] == c._MAX_HANDOVER_CHARS
    assert len(c.read_handover()["text"]) == c._MAX_HANDOVER_CHARS


def test_titel_trunkerer_ved_120(capsule_dir):
    c.write_handover("T" * 400, "noget")
    assert len(c.read_handover()["title"]) == 120


def test_overskrivning_erstatter(capsule_dir):
    c.write_handover("foerste", "A")
    c.write_handover("anden", "B")
    læst = c.read_handover()
    assert læst["title"] == "anden"
    assert læst["text"] == "B"


def test_laes_uden_capsule_giver_none(capsule_dir):
    assert c.read_handover() is None


# ── arven fremad — kernen i designet ──────────────────────────────────


def test_overdragelsen_overlever_en_efterfoelgende_tur(capsule_dir):
    """capture_state maa ikke vaske overdragelsen vaek."""
    c.write_handover("vigtig", "denne skal blive")
    # En almindelig tur skriver capsulen igen — uden handover-argumenter.
    ny = c.capture_state(mood={"bearing": "content"}, session_id="chat-x")
    assert ny["handover"]["text"] == "denne skal blive"
    c.write_capsule(ny)
    assert c.read_handover()["text"] == "denne skal blive"


def test_overdragelsen_overlever_mange_ture(capsule_dir):
    c.write_handover("holdbar", "ti ture frem")
    for i in range(10):
        ny = c.capture_state(session_id=f"chat-{i}")
        c.write_capsule(ny)
    assert c.read_handover()["text"] == "ti ture frem"


def test_uden_overdragelse_er_feltet_tomt_ikke_none(capsule_dir):
    ny = c.capture_state(session_id="chat-1")
    assert ny["handover"] == c._EMPTY_CAPSULE["handover"]


# ── visning i prompten ────────────────────────────────────────────────


def test_wake_up_blok_viser_overdragelsen(capsule_dir):
    c.write_handover("Railen", "Fem rettelser. Naeste: udgiv.")
    blok = c.build_wake_up_block()
    assert "OVERDRAGELSE — Railen" in blok
    assert "Fem rettelser. Naeste: udgiv." in blok


def test_wake_up_blok_uden_overdragelse_naevner_den_ikke(capsule_dir):
    c.write_capsule(dict(c._EMPTY_CAPSULE))
    blok = c.build_wake_up_block()
    assert "OVERDRAGELSE" not in blok


def test_overdragelsen_staar_foer_mood_i_blokken(capsule_dir):
    """Den er det eneste ikke-udledte — den skal staa oeverst."""
    c.write_handover("X", "vigtigst")
    blok = c.build_wake_up_block()
    assert blok.index("OVERDRAGELSE") < blok.index("Mood:")


# ── vaerktoejet ───────────────────────────────────────────────────────


def test_skemaet_er_velformet():
    d = ht.HANDOVER_TOOL_DEFINITIONS
    assert len(d) == 1
    fn = d[0]["function"]
    assert fn["name"] == "write_handover"
    assert fn["parameters"]["required"] == ["text"]
    assert set(fn["parameters"]["properties"]) == {"title", "text"}


def test_eksekutor_skriver(capsule_dir):
    r = ht._exec_write_handover({"title": "T", "text": "indhold"})
    assert r["status"] == "ok"
    assert c.read_handover()["text"] == "indhold"


def test_eksekutor_taaler_manglende_argumenter(capsule_dir):
    r = ht._exec_write_handover({})
    assert r["status"] == "error"  # tom tekst, ikke en kast


def test_eksekutor_taaler_none_vaerdier(capsule_dir):
    r = ht._exec_write_handover({"title": None, "text": None})
    assert r["status"] == "error"


# ── kapslens loft ─────────────────────────────────────────────────────


def test_overdragelsen_holder_capsulen_under_loftet(capsule_dir):
    """En maksimal overdragelse maa ikke sprænge capsule-loftet."""
    c.write_handover("stor", "x" * c._MAX_HANDOVER_CHARS)
    raw = (capsule_dir / "session_capsule.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    # Overdragelsen er intakt — truncation rammer recent_activity, ikke den.
    assert len(data["handover"]["text"]) == c._MAX_HANDOVER_CHARS
