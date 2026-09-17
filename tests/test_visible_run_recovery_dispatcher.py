"""Én forladt opgave genoptages præcis én gang — og kun af API-processen.

Opgave 4. To dispatchere, eller en dispatcher i begge processer, ville enten
starte den samme opgave to gange eller lade den ligge. Testene her holder de
tre ting fast: præcis én start, ingen dispatch i runtime-processen, og at et
krav gives tilbage når starten fejler.
"""
from __future__ import annotations

import pytest

from core.services import in_flight_runs as ifr
from core.services import visible_run_recovery_dispatcher as D


@pytest.fixture(autouse=True)
def _isolerede_poster(monkeypatch):
    poster: dict[str, dict] = {}
    monkeypatch.setattr(ifr, "_load", lambda: {k: dict(v) for k, v in poster.items()})
    monkeypatch.setattr(ifr, "_save", lambda v: (poster.clear(),
                                                 poster.update({k: dict(x) for k, x in v.items()})))
    monkeypatch.setattr(ifr, "owner_still_alive", lambda owner: False)
    monkeypatch.delenv("JARVIS_ENABLE_RUNTIME_SERVICES", raising=False)
    return poster


@pytest.fixture
def spawn(monkeypatch):
    kald: list[dict] = []

    def _start(**kw):
        kald.append(kw)
        return f"visible-{len(kald)}"

    monkeypatch.setattr(
        "core.services.visible_runs_sections.detached_run.start_user_run_detached", _start)
    return kald


def _forladt_opgave(run_id: str = "task-1", *, besked: str = "ret cheap lane") -> None:
    ifr.mark_started(run_id=run_id, session_id="chat-1", user_message=besked)
    ifr.settle_recovering(run_id, reason="shutdown", summary="shutdown")


def test_en_forladt_opgave_genoptages_praecis_EN_gang(spawn):
    _forladt_opgave()
    assert D.recover_due_once()["started"] == 1
    assert D.recover_due_once()["started"] == 0
    assert len(spawn) == 1
    assert spawn[0]["session_id"] == "chat-1"
    assert spawn[0]["message"] == "ret cheap lane"
    assert spawn[0]["recovery_task_id"] == "task-1"
    assert spawn[0]["recovery_generation"] == 1


def test_to_dispatchere_kan_ikke_tage_den_samme_opgave(spawn):
    """Kravet er atomisk: den anden finder ingenting, ikke den samme opgave."""
    _forladt_opgave()
    foerste = D.recover_due_once(owner="100:1")
    anden = D.recover_due_once(owner="200:2")
    assert foerste["started"] == 1 and anden["started"] == 0
    assert len(spawn) == 1


def test_runtime_processen_dispatcher_ikke(monkeypatch):
    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES", "1")
    assert D.start_recovery_dispatcher() is False


def test_api_processen_starter_EN_dispatcher(monkeypatch):
    monkeypatch.setattr(D, "_loop", lambda: None)
    try:
        assert D.start_recovery_dispatcher() is True
        assert D.start_recovery_dispatcher() is True   # idempotent
    finally:
        D.stop_recovery_dispatcher()


def test_en_mislykket_start_giver_kravet_tilbage(monkeypatch):
    _forladt_opgave()

    def _boom(**kw):
        raise RuntimeError("ingen plads til flere kørsler")

    monkeypatch.setattr(
        "core.services.visible_runs_sections.detached_run.start_user_run_detached", _boom)
    svar = D.recover_due_once()
    assert svar["started"] == 0 and svar["released"] == 1
    post = ifr._load()["task-1"]
    assert post["status"] == "recovering", "opgaven skal kunne tages igen"
    assert post["next_attempt_at"], "og først efter en pause"


def test_en_opgave_uden_session_startes_ikke(spawn):
    """En fortsættelse uden samtale ville lande et tilfældigt sted."""
    ifr.mark_started(run_id="task-2", session_id="", user_message="noget")
    ifr.settle_recovering("task-2", reason="shutdown")
    svar = D.recover_due_once()
    assert svar["started"] == 0 and svar["released"] == 1 and not spawn


def test_intet_forfaldent_giver_ingen_stoej(spawn):
    assert D.recover_due_once() == {"started": 0, "released": 0, "claimed": ""}
    assert not spawn
