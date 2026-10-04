"""Capsulens to defekter — maalt 4/10-2026 og rettet samme dag.

1. ``session_count_today`` stod paa 860. Den blev talt op ved hvert
   session_id-skift og ALDRIG nulstillet, saa tallet betoed intet.
2. ``current_focus`` stod paa «t». Kilden hentede det nyeste goal-signal uden
   statusfilter, og det nyeste var en test-raekke fra 8. juli. Maalt i basen:
   1744 signaler, ALLE 'archived', nul aktive.

En overdragelse der lyver er vaerre end ingen overdragelse.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

import core.services.continuity as c


@pytest.fixture
def capsule_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "CAPSULE_DIR", tmp_path)
    monkeypatch.setattr(c, "CAPSULE_CURRENT", tmp_path / "session_capsule.json")
    monkeypatch.setattr(c, "CAPSULE_PREV", tmp_path / "session_capsule.prev.json")
    monkeypatch.setattr(c, "CAPSULE_OLDER", tmp_path / "session_capsule.older.json")
    return tmp_path


I_DAG = datetime.now(UTC).date().isoformat()


# ── defekt 1: dagstallet ──────────────────────────────────────────────


def test_gammelt_fokus_ryddes_ved_merge_ikke_kun_ved_kilden(capsule_dir):
    """Den tredje vej — og den eneste der virker paa en fil der allerede loej.

    Kilden og visningen blev vogtet 4/10, men capture_state MERGER over den
    forrige capsule: naar den ferske attention er tom, arves den gamle vaerdi
    fremad for evigt. Maalt i drift kl. 17:38 stod filen stadig med
    current_focus='t' EFTER fixet — praecis fordi merge lod den staa.
    """
    gammel = dict(c._EMPTY_CAPSULE)
    gammel["attention"] = {
        "current_focus": "t",
        "active_goal_title": "t",
        "open_thread": None,
    }
    c.write_capsule(gammel)

    # Fersk attention UDEN fokus — praecis som naar statusfilteret nu giver nul
    # aktive signaler. Den gamle 't' maa ikke overleve.
    ny = c.capture_state(attention={"open_thread": None})
    assert ny["attention"].get("current_focus") is None
    assert ny["attention"].get("active_goal_title") is None

    # capture_state BYGGER dict'en; write_capsule GEMMER den. Rensningen skal
    # holde hele vejen — ogsaa naar den er skrevet og laest igen. (Den foerste
    # udgave af denne test antog at capture_state selv skrev; det goer den
    # ikke, og testen fejlede med rette paa sin egen paastand.)
    c.write_capsule(ny)
    fra_disk = c.read_capsule()
    assert fra_disk["attention"].get("current_focus") is None
    assert fra_disk["attention"].get("active_goal_title") is None


def test_et_rigtigt_fokus_overlever_merge(capsule_dir):
    """Vagten maa ikke rydde et aegte fokus. Kun skrald under graensen."""
    gammel = dict(c._EMPTY_CAPSULE)
    gammel["attention"] = {"current_focus": "Railen 1:1 med mockup'en"}
    c.write_capsule(gammel)

    ny = c.capture_state(attention={})
    assert ny["attention"]["current_focus"] == "Railen 1:1 med mockup'en"


def test_skrald_tal_fra_foer_fixet_nulstilles(capsule_dir):
    """Capsulen stod paa 860 uden dato — den skal nulstilles, ikke fortsætte."""
    gammel = dict(c._EMPTY_CAPSULE)
    gammel["relation"] = dict(gammel["relation"])
    gammel["relation"]["session_count_today"] = 860
    gammel["relation"].pop("session_count_date", None)
    c.write_capsule(gammel)

    ny = c.capture_state(session_id="chat-ny")
    assert ny["relation"]["session_count_today"] == 1  # nulstillet, saa optalt
    assert ny["relation"]["session_count_date"] == I_DAG


def test_ny_dag_nulstiller(capsule_dir):
    gammel = dict(c._EMPTY_CAPSULE)
    gammel["relation"] = dict(gammel["relation"])
    gammel["relation"]["session_count_today"] = 42
    gammel["relation"]["session_count_date"] = "2026-10-03"  # i gaar
    c.write_capsule(gammel)

    ny = c.capture_state()
    assert ny["relation"]["session_count_today"] == 0
    assert ny["relation"]["session_count_date"] == I_DAG


def test_samme_dag_taeller_op(capsule_dir):
    c.write_capsule(dict(c._EMPTY_CAPSULE))
    forventet = 0
    sidst = None
    for i in range(4):
        ny = c.capture_state(session_id=f"chat-{i}")
        c.write_capsule(ny)
        forventet += 1
        sidst = ny["relation"]["session_count_today"]
    assert sidst == forventet == 4


def test_samme_session_taeller_ikke_to_gange(capsule_dir):
    """Uden et nyt session_id maa tallet staa stille."""
    c.write_capsule(dict(c._EMPTY_CAPSULE))
    a = c.capture_state(session_id="chat-samme")
    c.write_capsule(a)
    b = c.capture_state(session_id="chat-samme")
    assert b["relation"]["session_count_today"] == a["relation"]["session_count_today"]


def test_datoen_skrives_ind_i_den_nye_capsule(capsule_dir):
    ny = c.capture_state()
    assert ny["relation"]["session_count_date"] == I_DAG


# ── defekt 2: fokus-feltet ────────────────────────────────────────────


def _capsule_med_fokus(fokus: str) -> dict:
    cap = dict(c._EMPTY_CAPSULE)
    cap["attention"] = dict(cap["attention"])
    cap["attention"]["current_focus"] = fokus
    cap["attention"]["active_goal_title"] = fokus
    cap["wake_provenance"] = dict(cap["wake_provenance"])
    return cap


def test_et_bogstav_kommer_ikke_i_blokken(capsule_dir):
    """Praecis den maalte defekt: «Focus: t» maa ikke vises."""
    blok = c.build_wake_up_block(_capsule_med_fokus("t"))
    assert "Focus: t" not in blok
    assert "Focus:" not in blok


def test_tomt_fokus_kommer_ikke_i_blokken(capsule_dir):
    blok = c.build_wake_up_block(_capsule_med_fokus(""))
    assert "Focus:" not in blok


def test_to_bogstaver_afvises_ogsaa(capsule_dir):
    blok = c.build_wake_up_block(_capsule_med_fokus("ab"))
    assert "Focus:" not in blok


def test_rigtigt_fokus_slipper_igennem(capsule_dir):
    blok = c.build_wake_up_block(_capsule_med_fokus("railen 1:1 med mockup'en"))
    assert "Focus: railen 1:1 med mockup'en" in blok


def test_graensen_er_praecis(capsule_dir):
    """MIN_FOCUS_CHARS tegn slipper igennem, eet faerre goer ikke."""
    kort = "x" * (c.MIN_FOCUS_CHARS - 1)
    netop = "x" * c.MIN_FOCUS_CHARS
    assert "Focus:" not in c.build_wake_up_block(_capsule_med_fokus(kort))
    assert "Focus:" in c.build_wake_up_block(_capsule_med_fokus(netop))


def test_fokus_strippes_for_mellemrum(capsule_dir):
    """«  t  » er lige saa tomt som «t»."""
    blok = c.build_wake_up_block(_capsule_med_fokus("  t  "))
    assert "Focus:" not in blok


# ── kilden filtrerer ogsaa ────────────────────────────────────────────


def test_kilden_beder_om_aktive_signaler():
    """visible_runs_memory maa ikke hente arkiverede signaler."""
    from pathlib import Path

    kilde = (
        Path(__file__).resolve().parents[1]
        / "core/services/visible_runs_memory.py"
    ).read_text(encoding="utf-8")
    assert 'list_runtime_goal_signals(status="active"' in kilde


def test_kilden_bruger_laengde_vagten():
    from pathlib import Path

    kilde = (
        Path(__file__).resolve().parents[1]
        / "core/services/visible_runs_memory.py"
    ).read_text(encoding="utf-8")
    assert "MIN_FOCUS_CHARS" in kilde
