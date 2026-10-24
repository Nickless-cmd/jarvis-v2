"""Tests for brain_supersession — «den nyere vinder».

Dækker det der kan rådne tavst:
* at en NYERE post ikke væltes af en ældre
* at en ofte-hentet post beskyttes
* at dry_run er standard og intet ændrer
* at supersede faktisk kaldes når man beder om det
* at en fejl i brain ikke kaster videre
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from core.services import brain_supersession as bs


def _entry(eid: str, *, dage_gammel: float = 10, recall: int = 0, status: str = "active"):
    return SimpleNamespace(
        id=eid,
        title=f"post {eid}",
        kind="fakta",
        status=status,
        recall_count=recall,
        created_at=datetime.now(UTC) - timedelta(days=dage_gammel),
    )


@pytest.fixture()
def brain(monkeypatch):
    """Mock brain: søgning returnerer faste kandidater, read_entry slår op i en dict."""
    poster: dict[str, object] = {}
    soegning: list[tuple[float, str]] = []
    kaldt: list[dict] = []

    def fake_search(**kwargs):
        return list(soegning)

    def fake_read(eid):
        return poster[eid]

    def fake_supersede(*, old_ids, new_id):
        kaldt.append({"old_ids": old_ids, "new_id": new_id})

    import core.services.jarvis_brain as jb
    monkeypatch.setattr(jb, "search_brain_scored", fake_search)
    monkeypatch.setattr(jb, "read_entry", fake_read)
    monkeypatch.setattr(jb, "supersede", fake_supersede)
    return SimpleNamespace(poster=poster, soegning=soegning, kaldt=kaldt)


def test_finder_aeldre_post_som_kandidat(brain):
    brain.poster["gammel"] = _entry("gammel", dage_gammel=30)
    brain.soegning.append((0.91, "gammel"))
    k = bs.find_supersession_candidates(new_entry_id="ny", new_text="jeg er ikke vegetar mere")
    assert len(k) == 1
    assert k[0]["entry_id"] == "gammel"
    assert k[0]["score"] == 0.91


def test_nyere_post_vaelter_ikke_aeldre_omvendt(brain):
    """Den nye post må ikke selv blive kandidat, og en post NYERE end nu afvises."""
    brain.poster["fremtidig"] = _entry("fremtidig", dage_gammel=-5)
    brain.soegning.append((0.95, "fremtidig"))
    k = bs.find_supersession_candidates(new_entry_id="ny", new_text="noget")
    assert k == []


def test_ny_post_er_ikke_sin_egen_kandidat(brain):
    brain.poster["ny"] = _entry("ny", dage_gammel=0)
    brain.soegning.append((0.99, "ny"))
    k = bs.find_supersession_candidates(new_entry_id="ny", new_text="noget")
    assert k == []


def test_oft_e_hentet_post_beskyttes(brain):
    brain.poster["vigtig"] = _entry("vigtig", dage_gammel=30, recall=50)
    brain.soegning.append((0.95, "vigtig"))
    k = bs.find_supersession_candidates(new_entry_id="ny", new_text="noget")
    assert k == []


def test_allerede_superseded_post_springes_over(brain):
    brain.poster["doed"] = _entry("doed", dage_gammel=30, status="superseded")
    brain.soegning.append((0.95, "doed"))
    k = bs.find_supersession_candidates(new_entry_id="ny", new_text="noget")
    assert k == []


def test_dry_run_er_standard_og_aendrer_intet(brain):
    brain.poster["gammel"] = _entry("gammel", dage_gammel=30)
    brain.soegning.append((0.91, "gammel"))
    r = bs.supersede_if_confident(new_entry_id="ny", new_text="noget")
    assert r["dry_run"] is True
    assert r["superseded"] == []
    assert len(r["candidates"]) == 1
    assert brain.kaldt == [], "dry_run må ikke kalde supersede"


def test_udfoerer_naar_man_beder_om_det(brain):
    brain.poster["gammel"] = _entry("gammel", dage_gammel=30)
    brain.soegning.append((0.91, "gammel"))
    r = bs.supersede_if_confident(new_entry_id="ny", new_text="noget", dry_run=False)
    assert r["superseded"] == ["gammel"]
    assert brain.kaldt == [{"old_ids": ["gammel"], "new_id": "ny"}]


def test_tom_tekst_giver_ingen_kandidater(brain):
    assert bs.find_supersession_candidates(new_entry_id="ny", new_text="   ") == []


def test_brain_fejl_kaster_ikke_videre(monkeypatch):
    import core.services.jarvis_brain as jb

    def boom(**kwargs):
        raise RuntimeError("brain nede")

    monkeypatch.setattr(jb, "search_brain_scored", boom)
    assert bs.find_supersession_candidates(new_entry_id="ny", new_text="noget") == []


def test_supersede_fejl_rapporteres_som_error(brain, monkeypatch):
    import core.services.jarvis_brain as jb

    brain.poster["gammel"] = _entry("gammel", dage_gammel=30)
    brain.soegning.append((0.91, "gammel"))

    def boom(**kwargs):
        raise RuntimeError("skrivefejl")

    monkeypatch.setattr(jb, "supersede", boom)
    r = bs.supersede_if_confident(new_entry_id="ny", new_text="noget", dry_run=False)
    assert r["status"] == "error"
    assert r["superseded"] == []
