"""Hele kontrolcentrets kæde — fra ét kald til den flade der viser det.

Delene er testet hver for sig i opgave 1-7. Det de IKKE kan vise, er om de
hænger sammen: at det samme kald kan findes igen gennem dashboardet, listen og
detaljen, og at korrelations-id'et er det samme hele vejen. Uden det bånd er
kontrolcentret seks paneler der tilfældigvis står ved siden af hinanden.

Og to ting der ville være dyre at opdage i produktionen:

* en payload må aldrig komme tilbage gennem listen — kun gennem detaljen, hvor
  den er redigeret og bevidst hentet;
* et forkert `expected_revision` skal give 409, ikke en stille overskrivning.
  To mennesker (eller et menneske og en autonom runde) der retter samtidig, må
  ikke kunne overskrive hinanden uden at opdage det.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def klient(isolated_runtime, monkeypatch):
    import apps.api.jarvis_api.routes.cheap_lane_control as routes

    monkeypatch.setattr(routes, "_require_owner", lambda: None)
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


@pytest.fixture
def et_kald():
    """Ét ægte kald med korrelations-id, spor og payload."""
    from core.runtime.db_cheap_provider import record_cheap_provider_invocation
    from core.runtime.db_cheap_lane_control import record_redacted_payload

    række = record_cheap_provider_invocation(
        provider="groq", model="llama-3.3-70b", status="failed",
        input_tokens=120, output_tokens=0, error_code="timeout",
        correlation_id="corr-integration-1",
    )
    record_redacted_payload(
        invocation_id=række["invocation_id"],
        prompt="prompt [REDIGERET]", response="", status="stored",
        expires_at="2099-01-01T00:00:00+00:00",
    )
    return række


def test_samme_kald_kan_findes_gennem_hele_kaeden(klient, et_kald):
    """Dashboard → liste → detalje, bundet af det samme korrelations-id."""
    dashboard = klient.get("/mc/cheap-lane/dashboard?hours=24")
    assert dashboard.status_code == 200
    assert dashboard.json()["schema_version"] == 1

    liste = klient.get("/mc/cheap-lane/logs?correlation_id=corr-integration-1")
    assert liste.status_code == 200
    poster = liste.json()["items"]
    assert poster, "kaldet kunne ikke findes gennem listen"
    assert poster[0]["invocation_id"] == et_kald["invocation_id"]

    detalje = klient.get(f"/mc/cheap-lane/logs/{et_kald['invocation_id']}")
    assert detalje.status_code == 200
    assert detalje.json()["correlation_id"] == "corr-integration-1"


def test_listen_baerer_ALDRIG_en_payload(klient, et_kald):
    """Prompten er det mest private i systemet. Den hentes bevidst, én ad
    gangen, gennem detaljen — aldrig som en gratis del af en liste nogen bare
    bladrer i."""
    krop = klient.get("/mc/cheap-lane/logs?correlation_id=corr-integration-1").text
    assert "prompt [REDIGERET]" not in krop
    assert "request_payload" not in krop


def test_en_forældet_revision_afvises_frem_for_at_overskrive(klient):
    """To der retter samtidig må ikke kunne overskrive hinanden i stilhed."""
    svar = klient.post("/mc/cheap-lane/control", json={
        "action": "lane.pause", "target": "cheap",
        "reason": "integrationsprøve", "expected_revision": "en-revision-der-ikke-findes",
    })
    assert svar.status_code in (404, 409, 422), svar.text


def test_en_handling_efterlader_et_spor(klient):
    svar = klient.post("/mc/cheap-lane/control", json={
        "action": "lane.pause", "target": "cheap", "reason": "integrationsprøve",
    })
    assert svar.status_code == 200, svar.text

    spor = klient.get("/mc/cheap-lane/audit?limit=10")
    assert spor.status_code == 200
    handlinger = [r.get("action") for r in spor.json().get("items", [])]
    assert "lane.pause" in handlinger, "handlingen blev ikke skrevet i sporet"


def test_eksport_baerer_ingen_legitimation(klient, et_kald):
    """Eksporten forlader maskinen. Det er stedet hvor en lækket nøgle ville
    gøre mest skade, og derfor stedet der skal efterprøves."""
    for sti in ("/mc/cheap-lane/logs/export?format=json",
                "/mc/cheap-lane/diagnostics/export?hours=24"):
        krop = klient.get(sti).text.lower()
        for ord_ in ("api_key", "authorization", "bearer ", "sk-"):
            assert ord_ not in krop, f"{sti} bar {ord_}"


# ── routingen maa OBSERVERES, ikke aendres (18/9-2026) ─────────────────────
#
# Kontrolcentret tilfoejede et spor over hvorfor en kandidat blev valgt, og et
# manuelt bias man kan skrue paa. Sporet skal se paa valget — ikke lave det om.
# Maalt paa grenen foer denne rettelse: efter at mistral fejlede, valgte lanen
# `kilo` (en noegleloes offentlig proxy) frem for `groq`, som havde
# legitimation og stod foerst. Et rent `min()` over vaegten havde kasseret den
# raekkefoelge listen var bygget i.

def _to_udbydere(isolated_runtime):
    ap = isolated_runtime.auth_profiles
    pr = isolated_runtime.provider_router
    for navn in ("groq", "mistral"):
        ap.save_provider_credentials(profile=navn, provider=navn,
                                     credentials={"api_key": f"{navn}_key"})
    pr.configure_provider_router_entry(
        provider="groq", model="llama-3.1-8b-instant", auth_mode="api-key",
        auth_profile="groq", base_url="https://api.groq.com/openai/v1",
        api_key="", lane="cheap", set_visible=False)
    pr.configure_provider_router_entry(
        provider="mistral", model="mistral-small-latest", auth_mode="api-key",
        auth_profile="mistral", base_url="https://api.mistral.ai/v1",
        api_key="", lane="cheap", set_visible=False)


def test_en_anonym_proxy_er_sidste_udvej_ogsaa_efter_et_failover(isolated_runtime):
    """Kontrakten: legitimerede udbydere foerst, offentlige proxyer som naadig
    sidste udvej. Den maa et routing-spor ikke kunne aendre."""
    from core.services import cheap_provider_runtime_selection as sel

    _to_udbydere(isolated_runtime)
    maal = sel.select_cheap_lane_target(
        skip_providers=frozenset({"mistral"}), persist_trace=False)
    assert maal["provider"] == "groq", (
        f"valgte {maal['provider']} — en udbyder uden legitimation kom foran "
        "en der har den")


def test_sporet_skrives_uden_at_flytte_valget(isolated_runtime):
    """Samme valg med og uden at sporet persisteres. Gjorde skrivningen en
    forskel, ville observationen vaere blevet til en handling."""
    from core.services import cheap_provider_runtime_selection as sel

    _to_udbydere(isolated_runtime)
    uden = sel.select_cheap_lane_target(persist_trace=False)
    med = sel.select_cheap_lane_target(persist_trace=True)
    assert (uden["provider"], uden["model"]) == (med["provider"], med["model"])
