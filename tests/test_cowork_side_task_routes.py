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
    side_tasks.resolve(b, decision="dismissed", reason="ikke laengere relevant")
    res = asyncio.run(cw.cowork_side_tasks())
    assert res["count"] == 1 and [t["side_task_id"] for t in res["side_tasks"]] == [a]


def test_owner_afslutter_opgave(monkeypatch, lager):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    a = side_tasks.flag(title="A", prompt="gør A")["side_task_id"]
    res = asyncio.run(cw.cowork_side_task_status(a, {"status": "completed", "bevis": "A blev gjort"}))
    assert res["status"] == "ok" and res["new_status"] == "completed"
    assert asyncio.run(cw.cowork_side_tasks())["count"] == 0


@pytest.mark.parametrize("kald", ["liste", "status", "skjul"])
def test_andre_end_owner_afvises(monkeypatch, lager, kald):
    # Prompten kan rumme privat kontekst — kun ejeren ser og ændrer feedet.
    monkeypatch.setattr(cw, "_role_owner", lambda: (False, "u_m"))
    with pytest.raises(HTTPException) as ei:
        if kald == "liste":
            asyncio.run(cw.cowork_side_tasks())
        elif kald == "skjul":
            asyncio.run(cw.cowork_side_task_skjul("side-x", {"skjult": True}))
        else:
            asyncio.run(cw.cowork_side_task_status("side-x", {"status": "completed"}))
    assert ei.value.status_code == 403


def test_start_fra_kortet_markerer_i_gang(monkeypatch, lager):
    # Kortets «Start …»-handlinger saetter opgaven i gang; den bliver staaende
    # (aaben) til nogen afslutter den.
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    a = side_tasks.flag(title="A", prompt="gør A")["side_task_id"]
    assert asyncio.run(cw.cowork_side_task_status(a, {"status": "activated"}))["new_status"] == "activated"
    liste = asyncio.run(cw.cowork_side_tasks())["side_tasks"]
    assert [t["status"] for t in liste] == ["activated"]


def test_koe_og_arbejds_run_bindes_gennem_samme_statusrute(monkeypatch, lager):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    tid = side_tasks.flag(title="A", prompt="gør A")["side_task_id"]
    assert asyncio.run(cw.cowork_side_task_status(tid, {"status": "queued"}))["new_status"] == "queued"
    assert asyncio.run(cw.cowork_side_task_status(
        tid, {"status": "activated", "session": "chat-1", "run_id": "run-1"},
    ))["new_status"] == "activated"
    item = asyncio.run(cw.cowork_side_tasks())["side_tasks"][0]
    assert item["arbejds_session"] == "chat-1" and item["arbejds_run_id"] == "run-1"


@pytest.mark.parametrize("status", ["pending", "bogus", ""])
def test_ugyldig_status_er_400(monkeypatch, lager, status):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    with pytest.raises(HTTPException) as ei:
        asyncio.run(cw.cowork_side_task_status("side-x", {"status": status}))
    assert ei.value.status_code == 400


# ── Skjul i chatten — blødt, ikke terminalt (8/10-2026) ─────────────────────
# Bjørn: «sørg for X'et ikk sletter dem men bare fjerner dem fra chatview».
# Før kaldte krydset statusruten med 'dismissed', som er TERMINAL — `resolve`
# nægter at genåbne, og der fandtes ingen genåbnings-rute. Fire klik i et
# hjørne afskrev fire opgaver for altid. Skjul er den reversible modsætning,
# og forskellen er hele pointen med ruten.


def test_skjul_tager_den_ud_af_kortet_men_bevarer_opgaven(monkeypatch, lager):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    a = side_tasks.flag(title="A", prompt="gør A")["side_task_id"]
    b = side_tasks.flag(title="B", prompt="gør B")["side_task_id"]

    assert asyncio.run(cw.cowork_side_task_skjul(a, {"skjult": True}))["status"] == "ok"

    # Kortet (scope=open) viser den ikke mere …
    kort = asyncio.run(cw.cowork_side_tasks())["side_tasks"]
    assert [t["side_task_id"] for t in kort] == [b]

    # … men den er stadig ÅBEN og findes i den fulde liste.
    alle = asyncio.run(cw.cowork_side_tasks(scope="all"))["side_tasks"]
    skjult = next(t for t in alle if t["side_task_id"] == a)
    assert skjult["status"] == "pending"
    assert skjult["skjult_i_chat"] is True

    # Og Jarvis' prompt skal stadig kende den: skjult for øjet er ikke droppet.
    assert a in [t["side_task_id"] for t in side_tasks.list_open()]


def test_vis_igen_henter_den_tilbage_til_kortet(monkeypatch, lager):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    a = side_tasks.flag(title="A", prompt="gør A")["side_task_id"]
    asyncio.run(cw.cowork_side_task_skjul(a, {"skjult": True}))
    assert asyncio.run(cw.cowork_side_tasks())["count"] == 0
    assert asyncio.run(cw.cowork_side_task_skjul(a, {"skjult": False}))["status"] == "ok"
    assert asyncio.run(cw.cowork_side_tasks())["count"] == 1


def test_skjul_af_terminal_opgave_afvises(monkeypatch, lager):
    # En lukket opgave vises ikke i kortet i forvejen; et skjul-flag på den
    # ville være en løgn om hvorfor den er væk.
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    a = side_tasks.flag(title="A", prompt="gør A")["side_task_id"]
    side_tasks.resolve(a, decision="dismissed", reason="ikke laengere relevant")
    res = asyncio.run(cw.cowork_side_task_skjul(a, {"skjult": True}))
    assert res["status"] == "error"
    assert "dismissed" in res["error"]


def test_skjul_roerer_ikke_status(monkeypatch, lager):
    # Hele fejlen: krydset afskrev opgaven. Det må ikke kunne ske igen.
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    a = side_tasks.flag(title="A", prompt="gør A")["side_task_id"]
    asyncio.run(cw.cowork_side_task_skjul(a, {"skjult": True}))
    assert side_tasks.get(a)["status"] == "pending"


# ── Opret fra Desk (15/10-2026) ─────────────────────────────────────────────
# Bjørn: «jeg mangler et sted i desk jeg kan oprette side-opgaver selv». Indtil
# da kunne KUN Jarvis flagge en opgave, så en ting han selv bemærkede midt i
# noget andet måtte igennem en samtale for at blive skrevet ned — præcis den
# omvej sideopgaven findes for at undgå. Ruten er den del af fladen der ikke
# fandtes på serveren.


def test_owner_opretter_opgave(monkeypatch, lager):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    res = asyncio.run(cw.cowork_side_task_opret(
        {"title": "Ret badgen", "prompt": "README viser et gammelt workflow"},
    ))
    assert res["status"] == "ok" and res["side_task_id"].startswith("side-")
    # Den er en rigtig opgave: den står ÅBEN i den liste kortet og panelet læser.
    liste = asyncio.run(cw.cowork_side_tasks())["side_tasks"]
    assert [t["title"] for t in liste] == ["Ret badgen"]
    assert liste[0]["status"] == "pending"


def test_opret_klipper_ikke_men_afviser_tomme_felter(monkeypatch, lager):
    # Blanke felter er ikke udfyldte felter. Uden dette ville en opgave uden
    # titel kunne oprettes og stå som en tom linje i panelet.
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    for payload in ({}, {"title": "A"}, {"prompt": "gør A"}, {"title": "  ", "prompt": "gør A"}):
        with pytest.raises(HTTPException) as ei:
            asyncio.run(cw.cowork_side_task_opret(payload))
        assert ei.value.status_code == 400


def test_kun_owner_kan_oprette(monkeypatch, lager):
    # Samme grund som de øvrige sideopgave-ruter: opgavens prompt er
    # selvstændige instruktioner og kan rumme privat kontekst.
    monkeypatch.setattr(cw, "_role_owner", lambda: (False, "u_m"))
    with pytest.raises(HTTPException) as ei:
        asyncio.run(cw.cowork_side_task_opret({"title": "A", "prompt": "gør A"}))
    assert ei.value.status_code == 403


def test_oprettet_opgave_kan_afsluttes_og_skjules_som_enhver_anden(monkeypatch, lager):
    # Den nye vej må ikke lave en opgave i en anden form end Jarvis' egen —
    # så skulle resten af fladen kende to slags opgaver.
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    a = asyncio.run(cw.cowork_side_task_opret({"title": "A", "prompt": "gør A"}))["side_task_id"]
    assert asyncio.run(cw.cowork_side_task_skjul(a, {"skjult": True}))["status"] == "ok"
    assert asyncio.run(cw.cowork_side_task_status(a, {"status": "completed", "bevis": "A blev gjort"}))["new_status"] == "completed"
    assert side_tasks.get(a)["lukket_af"] == "desk"


def test_en_opgave_kan_udskydes_og_vaagnes_fra_desk(monkeypatch, lager):
    """Timeren (16/10-2026): Desk skal kunne saette OG rydde tidspunktet.

    Udskydelsen lukker INGEN opgave — den er stadig aaben, den er bare ikke i
    vejen foer tiden er inde. Og en tid der ikke kan bruges skal svare som en
    SYNLIG fejl, ikke som en tavs no-op.
    """
    from datetime import UTC, datetime, timedelta
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    monkeypatch.setattr(side_tasks, "_book_vaekning", lambda *a, **k: "")
    a = side_tasks.flag(title="A", prompt="gør A")["side_task_id"]
    til = (datetime.now(UTC) + timedelta(hours=3)).isoformat()
    assert asyncio.run(cw.cowork_side_task_snooze(a, {"not_before": til}))["status"] == "ok"
    assert side_tasks.sovende(side_tasks.get(a)) is True
    assert side_tasks.get(a)["status"] == "pending"
    assert asyncio.run(cw.cowork_side_task_snooze(a, {"not_before": ""}))["status"] == "ok"
    assert side_tasks.sovende(side_tasks.get(a)) is False
    with pytest.raises(HTTPException) as ei:
        asyncio.run(cw.cowork_side_task_snooze(a, {"not_before": "i morgen"}))
    assert ei.value.status_code == 400
    monkeypatch.setattr(cw, "_role_owner", lambda: (False, "u_m"))
    with pytest.raises(HTTPException) as ei2:
        asyncio.run(cw.cowork_side_task_snooze(a, {"not_before": til}))
    assert ei2.value.status_code == 403


# ── redigering (25/10-2026) ──────────────────────────────────────────────
# Bjørn: «jeg har ikke mulighed for at redigere en eksisterende opgave eller
# saette regler eller autonomi». Ruten er den fjerde mutation paa samme post,
# og den skal svare forskelligt paa «daarlig anmodning» og «laast af et run».

def test_owner_redigerer_opgave(monkeypatch, lager):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    a = side_tasks.flag(title="A", prompt="gør A")["side_task_id"]
    res = asyncio.run(cw.cowork_side_task_rediger(
        a, {"title": "B", "autonomy_mode": "inspect", "max_minutes": 30}))
    assert res["status"] == "ok"
    post = side_tasks.get(a)
    assert post["title"] == "B" and post["autonomy_mode"] == "inspect"
    assert post["max_minutes"] == 30


def test_rediger_uden_felter_afvises_som_daarlig_anmodning(monkeypatch, lager):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    a = side_tasks.flag(title="A", prompt="gør A")["side_task_id"]
    with pytest.raises(HTTPException) as ei:
        asyncio.run(cw.cowork_side_task_rediger(a, {}))
    assert ei.value.status_code == 400


def test_rediger_ukendt_felt_afvises_ikke_tavst_ignoreret(monkeypatch, lager):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    a = side_tasks.flag(title="A", prompt="gør A")["side_task_id"]
    with pytest.raises(HTTPException) as ei:
        asyncio.run(cw.cowork_side_task_rediger(a, {"status": "completed"}))
    assert ei.value.status_code == 400
    assert side_tasks.get(a)["status"] == "pending"


def test_rediger_opgave_i_gang_giver_409_ikke_400(monkeypatch, lager):
    """En laast post er en TILSTANDSKONFLIKT — klienten skal kunne se forskel."""
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    a = side_tasks.flag(title="A", prompt="gør A")["side_task_id"]
    side_tasks.resolve(a, decision="activated", arbejds_session="chat-7",
                       arbejds_run_id="run-8")
    with pytest.raises(HTTPException) as ei:
        asyncio.run(cw.cowork_side_task_rediger(a, {"prompt": "ny"}))
    assert ei.value.status_code == 409
    assert side_tasks.get(a)["prompt"] == "gør A"


def test_kun_owner_kan_redigere(monkeypatch, lager):
    monkeypatch.setattr(cw, "_role_owner", lambda: (True, None))
    a = side_tasks.flag(title="A", prompt="gør A")["side_task_id"]
    monkeypatch.setattr(cw, "_role_owner", lambda: (False, "u_m"))
    with pytest.raises(HTTPException) as ei:
        asyncio.run(cw.cowork_side_task_rediger(a, {"title": "B"}))
    assert ei.value.status_code == 403
    assert side_tasks.get(a)["title"] == "A"
