"""Owner-beskyttede ruter for Jarvis' flaggede sideopgaver (spec desk-sideopgaver)."""
import asyncio

import pytest
from fastapi import HTTPException

import apps.api.jarvis_api.routes.cowork as cw
from core.services import side_tasks


@pytest.fixture
def lager(monkeypatch):
    state: list = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _key, _default: list(state))
    monkeypatch.setattr(side_tasks, "save_json", lambda _key, items: state.__setitem__(slice(None), items))
    return state


def test_owner_ser_aabne_opgaver(monkeypatch, lager):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    a = side_tasks.flag(title="A", prompt="gør A")["side_task_id"]
    b = side_tasks.flag(title="B", prompt="gør B")["side_task_id"]
    side_tasks.resolve(b, decision="dismissed")
    res = asyncio.run(cw.cowork_side_tasks())
    assert res["count"] == 1 and [t["side_task_id"] for t in res["side_tasks"]] == [a]


def test_owner_afslutter_opgave(monkeypatch, lager):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    a = side_tasks.flag(title="A", prompt="gør A")["side_task_id"]
    res = asyncio.run(cw.cowork_side_task_status(a, {"status": "completed"}))
    assert res["status"] == "ok" and res["new_status"] == "completed"
    assert asyncio.run(cw.cowork_side_tasks())["count"] == 0


@pytest.mark.parametrize("kald", ["liste", "status"])
def test_andre_end_owner_afvises(monkeypatch, lager, kald):
    # Prompten kan rumme privat kontekst — kun ejeren ser og ændrer feedet.
    monkeypatch.setattr(cw, "_role_owner", lambda: (False, "u_m"))
    with pytest.raises(HTTPException) as ei:
        if kald == "liste":
            asyncio.run(cw.cowork_side_tasks())
        else:
            asyncio.run(cw.cowork_side_task_status("side-x", {"status": "completed"}))
    assert ei.value.status_code == 403


@pytest.mark.parametrize("status", ["activated", "pending", "bogus", ""])
def test_ugyldig_status_er_400(monkeypatch, lager, status):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    with pytest.raises(HTTPException) as ei:
        asyncio.run(cw.cowork_side_task_status("side-x", {"status": status}))
    assert ei.value.status_code == 400
