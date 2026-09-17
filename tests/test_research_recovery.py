"""Et afbrudt research-run tager kun de UAFSLUTTEDE spor op igen.

Opgave 6. Før startede en genoptagelse forfra: sporene der allerede havde
leveret evidens blev kørt igen — dyrt, og kilderne kom ind to gange. Og et run
uden ét eneste færdigt spor må sige det højt i stedet for at aflevere en
rapport uden grundlag.
"""
from __future__ import annotations

import pytest

from core.services import research_store as store
from core.services.research_orchestrator import (
    ResearchRecoverableError,
    resume_research_run,
)
from core.services.research_contract import ResearchTask


@pytest.fixture()
def isolated_store(tmp_path, monkeypatch):
    """Egen database pr. test — samme mønster som `test_research_store.py`."""
    import sqlite3

    path = tmp_path / "research.db"

    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(store, "connect", connect)
    return store


@pytest.fixture
def run(isolated_store):
    r = store.create_run(session_id="s1", original_query="sammenlign", tier="orchestrated")
    opgaver = store.create_tasks(r["id"], [
        ResearchTask(title="faerdig", objective="evidens der kom ind", ordinal=1),
        ResearchTask(title="mangler", objective="evidens der mangler", ordinal=2),
    ])
    store.start_task(opgaver[0]["id"])
    store.complete_task(opgaver[0]["id"], {"text": "et fund", "findings": []})
    store.start_task(opgaver[1]["id"])          # kørte da segmentet døde
    return r


async def _hent(gen):
    return [event async for event in gen]


@pytest.mark.asyncio
async def test_kun_de_uafsluttede_spor_koeres_igen(run):
    klar = store.prepare_recovery(run["id"], warning="research-wall-time-exceeded")
    assert [int(t["ordinal"]) for t in klar["unfinished"]] == [2]

    koert: list[int] = []

    async def worker(*, run_id, task):
        koert.append(int(task["ordinal"]))
        return {"text": "genfundet evidens", "findings": []}

    events = await _hent(resume_research_run(run["id"], visible_run_id="v1",
                                             worker_factory=worker))
    assert koert == [2], "et færdigt spor blev kørt igen"
    assert any("research_completed" in e for e in events)
    assert store.get_run(run["id"])["status"] == "completed"


@pytest.mark.asyncio
async def test_uden_evidens_beder_den_foraelderen_om_hjaelp(run):
    # Ingen færdige spor: nulstil det ene der nåede at blive færdigt.
    for t in store.list_tasks(run["id"]):
        store.prepare_recovery(run["id"], warning="x")
    tom = store.create_run(session_id="s2", original_query="tom", tier="orchestrated")
    store.create_tasks(tom["id"], [ResearchTask(title="a", objective="b", ordinal=1)])
    store.prepare_recovery(tom["id"], warning="research-wall-time-exceeded")
    with pytest.raises(ResearchRecoverableError) as fejl:
        await _hent(resume_research_run(tom["id"], visible_run_id="v1"))
    assert fejl.value.evidence_count == 0
    assert fejl.value.run_id == tom["id"]


@pytest.mark.asyncio
async def test_et_spor_der_fejler_igen_staar_ikke_i_vejen_for_rapporten(run):
    store.prepare_recovery(run["id"], warning="x")

    async def worker(*, run_id, task):
        raise RuntimeError("udbyderen svarede ikke")

    events = await _hent(resume_research_run(run["id"], visible_run_id="v1",
                                             worker_factory=worker))
    assert any("research_warning" in e for e in events)
    # Der ER evidens fra før afbrydelsen — den skal stadig blive til en rapport.
    assert any("research_completed" in e for e in events)


@pytest.mark.asyncio
async def test_et_afbrudt_spor_bliver_pending_igen(run):
    """Et spor der stod som «kørende» da processen døde, kører ikke længere.
    Ingen har dets resultat, så det skal kunne startes igen."""
    klar = store.prepare_recovery(run["id"], warning="shutdown")
    statusser = {int(t["ordinal"]): t["status"] for t in store.list_tasks(run["id"])}
    assert statusser == {1: "completed", 2: "pending"}
    assert klar["completed_tasks"] == 1
