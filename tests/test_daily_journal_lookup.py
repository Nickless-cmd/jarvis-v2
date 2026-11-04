"""Opslag på dato: «hvad skete der 2. november» er et eksakt opslag, ikke et semantisk gæt.

Målt 4/11-2026: en dagbogs EGEN overskrift som søgning lå uden for top 200 af ca. 19.000
poster (hel-dags-tekst giver en udvandet embedding; observation har vigtighed 0,4), og
værktøjets relevansgulv (min_cosine 0,5) holder dem ude endnu mere.
"""
from __future__ import annotations

import pytest

from core.services import daily_journal_entry as je
from core.services import jarvis_brain
from core.tools import jarvis_brain_tools as tools


@pytest.fixture
def hjerne(tmp_path, monkeypatch):
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    obs = jarvis_brain.brain_dir() / "observation"
    obs.mkdir(parents=True)
    for d, tekst in (("2026-11-01", "Mandag handlede om cachen."), ("2026-11-02", "Tirsdag: toasten og klokken."),
                     ("2026-11-03", "Onsdag: dream-action."), ("2026-12-01", "Langt væk.")):
        (obs / f"{d}-daily.md").write_text(
            f"# Daily journal — {d}\n\n_Synthesized {d}T20:00:00+00:00 — 3 chat-msgs, 0 carries._\n\n{tekst}\n",
            encoding="utf-8")
    je.backfill()
    jarvis_brain.rebuild_index_from_files()
    return obs


@pytest.fixture(autouse=True)
def recall_slaaet_til(monkeypatch):
    from core.services import scoped_recall_policy
    monkeypatch.setattr(scoped_recall_policy, "recall_enabled", lambda: True)


@pytest.fixture
def som_ejer(monkeypatch):
    monkeypatch.setattr(tools, "_bound_visibility_ceiling", lambda: "intimate")


@pytest.fixture
def som_medlem(monkeypatch):
    monkeypatch.setattr(tools, "_bound_visibility_ceiling", lambda: "public_safe")


def _datoer(res):
    return [r["date"] for r in res["results"]]


def test_en_dato_giver_netop_den_dagbog_uden_query(hjerne, som_ejer):
    res = tools.search_jarvis_brain(query="", date="2026-11-02")
    assert res["status"] == "ok" and _datoer(res) == ["2026-11-02"]
    assert res["results"][0]["title"] == "Daily journal — 2026-11-02"
    assert "toasten og klokken" in res["results"][0]["excerpt"]
    assert res["hidden_by_visibility"] == 0


def test_et_interval_giver_dagbøgerne_i_rækkefølge(hjerne, som_ejer):
    res = tools.search_jarvis_brain(query="", date="2026-11-01..2026-11-03")
    assert _datoer(res) == ["2026-11-01", "2026-11-02", "2026-11-03"]


def test_en_dag_uden_dagbog_giver_tom_liste_ikke_fejl(hjerne, som_ejer):
    assert tools.search_jarvis_brain(query="", date="2026-11-09") == {
        "status": "ok", "results": [], "hidden_by_visibility": 0, "date": "2026-11-09"}


def test_et_medlem_faar_ingen_dagbog_men_ser_at_noget_er_skjult(hjerne, som_medlem):
    res = tools.search_jarvis_brain(query="", date="2026-11-01..2026-11-03")
    assert res["results"] == [] and res["hidden_by_visibility"] == 3


def test_en_arkiveret_dagbog_findes_stadig_paa_dato(hjerne, som_ejer):
    conn = jarvis_brain.connect_index()
    try:
        eid = conn.execute("SELECT id FROM brain_index WHERE path LIKE '%2026-11-02-daily.md'").fetchone()[0]
    finally:
        conn.close()
    jarvis_brain.archive_entry(eid, reason="test")
    assert _datoer(tools.search_jarvis_brain(query="", date="2026-11-02")) == ["2026-11-02"]


@pytest.mark.parametrize("dato", ["i går", "2026-13-01", "2026-11-03..2026-11-01", "2026-01-01..2026-12-31", "2026-11-0x"])
def test_ugyldig_dato_eller_for_stort_interval_afvises_med_en_grund(hjerne, som_ejer, dato):
    res = tools.search_jarvis_brain(query="", date=dato)
    assert res["status"] == "error" and res["error"] == "invalid_date" and res["details"]


def test_uden_query_og_uden_dato_er_en_fejl_ikke_en_tom_soegning(hjerne, som_ejer):
    res = tools.search_jarvis_brain(query="")
    assert res["status"] == "error" and res["error"] == "query_or_date_required"


def test_executoren_sender_date_videre_og_kraever_ikke_query(hjerne, som_ejer):
    res = tools._exec_search_jarvis_brain({"date": "2026-11-03"})
    assert _datoer(res) == ["2026-11-03"]


def test_en_almindelig_soegning_er_uaendret_af_date_parameteren(hjerne, som_ejer, monkeypatch):
    kald = {}
    monkeypatch.setattr(jarvis_brain, "search_brain", lambda **kw: kald.update(kw) or [])
    res = tools.search_jarvis_brain(query="cache", limit=3)
    assert res == {"status": "ok", "results": [], "hidden_by_visibility": 0}
    assert kald["query_text"] == "cache" and kald["limit"] == 3


def test_skemaet_goer_query_valgfri_og_dokumenterer_date():
    schema = next(t for t in tools.JARVIS_BRAIN_TOOL_DEFINITIONS
                  if t["function"]["name"] == "search_jarvis_brain")["function"]["parameters"]
    assert "date" in schema["properties"] and "query" not in schema.get("required", [])


def test_opslaget_respekterer_recall_kontakten(hjerne, som_ejer, monkeypatch):
    """Samme kill-switch som den semantiske søgning: slukket recall = ingen dagbøger heller."""
    from core.services import scoped_recall_policy
    monkeypatch.setattr(scoped_recall_policy, "recall_enabled", lambda: False)
    res = tools.search_jarvis_brain(query="", date="2026-11-02")
    assert res["status"] == "disabled" and not res.get("results") and "toasten" not in str(res)
