"""Redigering af en sideopgave — den vej der ikke fandtes.

Bjørn 25/10-2026: «jeg har ikke mulighed for at redigere en eksisterende
opgave eller sætte regler eller autonomi eller anden.. der er kun title og
beskrivelse».

Testene her værner to ting der er nemme at miste:

* **Grænsen ved `activated`.** Et run læser opgavens prompt lige nu; ændrer vi
  den under fødderne på det, peger beviset ved lukning på en instruks der ikke
  længere findes.
* **At en redigering ikke kan omgå `flag`s validering.** Ellers ville den vej
  der blev bygget for at rette en tastefejl også være den vej der satte
  budgettet til 999 minutter.
"""
from contextlib import nullcontext

import pytest

from core.services import side_tasks


@pytest.fixture
def lager(monkeypatch):
    """Samme fake-lager som de øvrige side-task-tests: en liste i hukommelsen."""
    state: list[dict] = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _key, _default: list(state))
    monkeypatch.setattr(
        side_tasks, "save_json",
        lambda _key, items: state.__setitem__(slice(None), items),
    )
    monkeypatch.setattr(side_tasks, "med_laas", lambda _key: nullcontext())
    return state


def _opgave(**kw) -> str:
    return side_tasks.flag(title=kw.pop("title", "Ret badgen"),
                           prompt=kw.pop("prompt", "Find den og ret den"),
                           **kw)["side_task_id"]


def _post(state: list[dict], sid: str) -> dict:
    return next(r for r in state if r["side_task_id"] == sid)


def test_rediger_titel_og_prompt(lager):
    sid = _opgave()
    res = side_tasks.opdater(sid, title="Ny titel", prompt="Ny instruks")
    assert res["status"] == "ok"
    post = _post(lager, sid)
    assert post["title"] == "Ny titel"
    assert post["prompt"] == "Ny instruks"
    # Redigeringen efterlader et spor — ellers kan man ikke se at posten er
    # aendret efter den blev oprettet.
    assert post["redigeret_at"]


def test_rediger_autonomi_og_budget(lager):
    """Det Bjørn konkret manglede: at saette autonomi paa en eksisterende opgave."""
    sid = _opgave()
    assert _post(lager, sid)["autonomy_mode"] == "none"
    side_tasks.opdater(sid, autonomy_mode="inspect", max_minutes=30, max_tool_calls=20)
    post = _post(lager, sid)
    assert post["autonomy_mode"] == "inspect"
    assert post["max_minutes"] == 30
    assert post["max_tool_calls"] == 20


def test_rediger_afvises_naar_opgaven_er_i_gang(lager):
    """Et run laeser prompten lige nu — den maa ikke aendres under det."""
    sid = _opgave()
    side_tasks.resolve(sid, decision="activated", arbejds_session="chat-7",
                       arbejds_run_id="run-8")
    res = side_tasks.opdater(sid, prompt="Ny instruks")
    assert res["status"] == "error"
    assert "i gang" in res["error"]
    assert _post(lager, sid)["prompt"] == "Find den og ret den"


def test_rediger_afvises_naar_opgaven_er_lukket(lager):
    sid = _opgave()
    side_tasks.resolve(sid, decision="completed",
                       bevis="Badgen blev rettet i commit abc123 og pushet")
    res = side_tasks.opdater(sid, title="Ny titel")
    assert res["status"] == "error"
    assert "allerede" in res["error"]


def test_ukendt_felt_afvises_frem_for_at_blive_ignoreret(lager):
    """En tastefejl der ser ud som en gemt aendring er vaerre end en synlig fejl."""
    sid = _opgave()
    res = side_tasks.opdater(sid, titel="Skrevet paa dansk")
    assert res["status"] == "error"
    assert "titel" in res["error"]
    assert _post(lager, sid)["title"] == "Ret badgen"


def test_status_kan_ikke_redigeres_den_vej(lager):
    """Status har sin egen rute med sine egne krav (bevis/ground)."""
    sid = _opgave()
    res = side_tasks.opdater(sid, status="completed")
    assert res["status"] == "error"
    assert _post(lager, sid)["status"] == "pending"


def test_tom_titel_og_tom_prompt_afvises(lager):
    sid = _opgave()
    assert side_tasks.opdater(sid, title="   ")["status"] == "error"
    assert side_tasks.opdater(sid, prompt="")["status"] == "error"
    post = _post(lager, sid)
    assert post["title"] == "Ret badgen" and post["prompt"] == "Find den og ret den"


def test_ugyldig_autonomi_afvises(lager):
    sid = _opgave()
    res = side_tasks.opdater(sid, autonomy_mode="gud")
    assert res["status"] == "error"
    assert _post(lager, sid)["autonomy_mode"] == "none"


def test_budget_klemmes_til_samme_graenser_som_flag(lager):
    """Redigering maa ikke vaere vejen uden om oprettelsens graenser."""
    sid = _opgave()
    side_tasks.opdater(sid, max_minutes=999, max_tool_calls=1)
    post = _post(lager, sid)
    assert post["max_minutes"] == 60      # loftet
    assert post["max_tool_calls"] == 3    # gulvet


def test_ukendt_opgave_giver_fejl(lager):
    res = side_tasks.opdater("side-findes-ikke", title="X")
    assert res["status"] == "error"
    assert "unknown side_task_id" in res["error"]


def test_tom_redigering_er_lovlig_men_roerer_intet(lager):
    """Ingen aendringer er ikke en fejl paa serviceniveau — ruten afviser den."""
    sid = _opgave()
    foer = dict(_post(lager, sid))
    res = side_tasks.opdater(sid)
    assert res["status"] == "ok"
    efter = _post(lager, sid)
    assert efter["title"] == foer["title"]
    assert efter["prompt"] == foer["prompt"]
