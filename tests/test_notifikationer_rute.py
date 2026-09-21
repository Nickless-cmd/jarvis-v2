# tests/test_notifikationer_rute.py
from __future__ import annotations

import pytest


@pytest.fixture()
def klient(isolated_runtime, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.api.jarvis_api.routes import notifikationer as rute

    monkeypatch.setattr(rute, "_nuvaerende_bruger", lambda: ("bjorn", True))
    app = FastAPI()
    app.include_router(rute.router)
    return TestClient(app)


def test_feed_returnerer_aabne_med_antal(klient, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import approval_runtime

    n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Husk mælk")
    monkeypatch.setattr(approval_runtime, "state", lambda aid: None)

    svar = klient.get("/notifikationer").json()
    assert svar["antal"] == 1
    assert svar["poster"][0]["titel"] == "Husk mælk"


def test_afgoer_en_godkendelse_kalder_decide(klient, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import approval_runtime

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                  ref="a-1", titel="X")
    kaldt = {}
    monkeypatch.setattr(approval_runtime, "decide",
                        lambda aid, **kw: kaldt.update({"id": aid, **kw}) or {"ok": True})

    svar = klient.post(f"/notifikationer/{nid}/afgoer", json={"approved": True})
    assert svar.json()["ok"] is True
    assert kaldt["id"] == "a-1"
    assert kaldt["approved"] is True
    assert kaldt["answered_by"] == "bjorn"


def test_ruten_lukker_IKKE_raekken_selv(klient, monkeypatch) -> None:
    """Hydreringen bestemmer. Lukkede ruten ogsaa, kunne den lukke en raekke
    hvis ejer stadig venter — og saa var kortet vaek uden at vaere besvaret."""
    from core.services import notifikationer as n
    from core.services import approval_runtime

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="X")
    monkeypatch.setattr(approval_runtime, "decide", lambda aid, **kw: {"ok": True})
    klient.post(f"/notifikationer/{nid}/afgoer", json={"approved": True})
    assert len(n.aabne("bjorn", er_owner=True)) == 1


def test_afgoer_afviser_en_raekke_der_ikke_kan_afgoeres(klient) -> None:
    from core.services import notifikationer as n

    nid = n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="X")
    svar = klient.post(f"/notifikationer/{nid}/afgoer", json={"approved": True}).json()
    assert svar["ok"] is False
    assert "kan ikke" in svar["fejl"]


def test_afgoer_afviser_en_anden_brugers_raekke(klient, monkeypatch) -> None:
    """Ellers kunne et id gaettet fra en anden bruger afgoeres herfra."""
    from core.services import notifikationer as n
    from core.services import approval_runtime

    nid = n.opret(user_id="mikkel", slags="approval", kilde="approval", ref="a-9", titel="X")
    monkeypatch.setattr(approval_runtime, "decide",
                        lambda aid, **kw: pytest.fail("maatte ikke kaldes"))
    svar = klient.post(f"/notifikationer/{nid}/afgoer", json={"approved": True}).json()
    assert svar["ok"] is False


def test_afgoer_laeser_decides_fejl_og_oversaetter_den(klient, monkeypatch) -> None:
    """Kernefejlen: decide() rejser ikke ved almindelige fejl, den returnerer
    {"status": "error", ...} roligt. Ignoreres returvaerdien, faar klienten
    ok=True for et svar der aldrig blev sendt. Denne udgang ("Approval not
    found or expired") er engelsk og skal oversaettes til brugeren."""
    from core.services import notifikationer as n
    from core.services import approval_runtime

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                  ref="a-1", titel="X")
    monkeypatch.setattr(
        approval_runtime, "decide",
        lambda aid, **kw: {"error": "Approval not found or expired", "status": "error"},
    )

    svar = klient.post(f"/notifikationer/{nid}/afgoer", json={"approved": True}).json()
    assert svar["ok"] is False
    assert "engelsk" not in svar["fejl"].lower()
    assert "found or expired" not in svar["fejl"]
    assert "udloebet" in svar["fejl"] or "findes ikke" in svar["fejl"]


def test_afgoer_lykkes_svarer_stadig_ok_true(klient, monkeypatch) -> None:
    """Regressionsvaern: en reel succes (status != "error") skal stadig give
    ok=True, som foer denne rettelse."""
    from core.services import notifikationer as n
    from core.services import approval_runtime

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                  ref="a-1", titel="X")
    monkeypatch.setattr(
        approval_runtime, "decide",
        lambda aid, **kw: {"status": "ok", "tool": "bash", "result_text": "1\n",
                           "chat_persisted": True},
    )

    svar = klient.post(f"/notifikationer/{nid}/afgoer", json={"approved": True}).json()
    assert svar["ok"] is True
    assert svar["fejl"] == ""


def test_afgoer_allerede_besvaret_oversaettes(klient, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import approval_runtime

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                  ref="a-1", titel="X")
    monkeypatch.setattr(
        approval_runtime, "decide",
        lambda aid, **kw: {"error": "Approval already resolved", "status": "error"},
    )

    svar = klient.post(f"/notifikationer/{nid}/afgoer", json={"approved": True}).json()
    assert svar["ok"] is False
    assert "already resolved" not in svar["fejl"]
    assert "besvaret" in svar["fejl"]


def test_afgoer_krydsbruger_fejl_vises_uaendret(klient, monkeypatch) -> None:
    """Denne fejltekst er allerede dansk fra resolve_pending_approval() —
    oversaettelses-tabellen skal lade den passere uaendret."""
    from core.services import notifikationer as n
    from core.services import approval_runtime

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                  ref="a-1", titel="X")
    monkeypatch.setattr(
        approval_runtime, "decide",
        lambda aid, **kw: {
            "status": "error",
            "tool": "bash",
            "error": "Den godkendelse tilhoerer en anden bruger.",
            "result_text": "[Godkendelsen tilhoerer en anden bruger]",
            "chat_persisted": False,
        },
    )

    svar = klient.post(f"/notifikationer/{nid}/afgoer", json={"approved": True}).json()
    assert svar["ok"] is False
    assert svar["fejl"] == "Den godkendelse tilhoerer en anden bruger."


def test_afgoer_udloebet_fejl_vises_uaendret(klient, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import approval_runtime

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                  ref="a-1", titel="X")
    monkeypatch.setattr(
        approval_runtime, "decide",
        lambda aid, **kw: {
            "status": "error",
            "tool": "bash",
            "error": "Godkendelsen er udloebet (2.0 timer gammel). Bed om "
                     "handlingen igen, saa laver jeg et nyt kort.",
            "result_text": "[Godkendelsen er udloebet: 2.0 timer gammel]",
            "chat_persisted": False,
        },
    )

    svar = klient.post(f"/notifikationer/{nid}/afgoer", json={"approved": True}).json()
    assert svar["ok"] is False
    assert "udloebet" in svar["fejl"]


def test_afgoer_broen_afviste_fejl_vises_uaendret(klient, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import approval_runtime

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                  ref="a-1", titel="X")
    monkeypatch.setattr(
        approval_runtime, "decide",
        lambda aid, **kw: {
            "status": "error",
            "tool": "bash",
            "error": "Godkendelsen kunne ikke overtages: raekken var laast",
            "result_text": "[Godkendelsen kunne ikke overtages: raekken var laast]",
            "chat_persisted": False,
            "approval_id": "a-1",
        },
    )

    svar = klient.post(f"/notifikationer/{nid}/afgoer", json={"approved": True}).json()
    assert svar["ok"] is False
    assert "kunne ikke overtages" in svar["fejl"]


def test_afgoer_kaldet_aendret_fejl_vises_uaendret(klient, monkeypatch) -> None:
    from core.services import notifikationer as n
    from core.services import approval_runtime

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                  ref="a-1", titel="X")
    monkeypatch.setattr(
        approval_runtime, "decide",
        lambda aid, **kw: {
            "status": "error",
            "tool": "bash",
            "error": "Kaldet har aendret sig siden du godkendte det. Bed om "
                     "handlingen igen.",
            "result_text": "[Kaldet har aendret sig siden godkendelsen]",
            "chat_persisted": False,
        },
    )

    svar = klient.post(f"/notifikationer/{nid}/afgoer", json={"approved": True}).json()
    assert svar["ok"] is False
    assert "aendret sig" in svar["fejl"]


def test_set_lukker_en_uden_handling(klient) -> None:
    from core.services import notifikationer as n

    nid = n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="X")
    assert klient.post(f"/notifikationer/{nid}/set").json()["ok"] is True
    assert n.aabne("bjorn", er_owner=True) == []
