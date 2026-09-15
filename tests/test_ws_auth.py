"""Event-socketen streamede hans indre liv til enhver der forbandt.

## Målt 15/9-2026

`/ws` kaldte `await ws.accept()` uden noget tjek. Middlewaren er registreret
som `app.middleware("http")`, så **WebSockets går uden om den helt**. En
forbindelse uden token gav straks rigtige interne events, og Caddy
videresender alle stier på det offentligt nåelige api.srvlab.dk.

Hvad der lå i strømmen (sidste time på bussen, målt før rettelsen):

    thought_stream.fragment_generated        hans indre stemme
    private_brain.continuity_completed
    reasoning.conclusion.captured      1.144
    cognitive_state.somatic_body_updated

Det er ikke telemetri.

## Hvorfor subprotokol og ikke `?token=`

Browsere kan ikke sætte headers på en WebSocket. Den nærliggende udvej er en
query-parameter — og den er forkert her: uvicorns adgangslog skriver hele
stien med query, så hver eneste forbindelse ville lægge et **gyldigt token i
journalen**. `Sec-WebSocket-Protocol` kan browseren sætte, og den logges ikke.

## Hvem bruger den

Web-UI'en (ét sted) og desk (tre steder). Mobilen bruger den ikke — den har
sin egen bro-socket, og **den var allerede beskyttet**.
"""
from __future__ import annotations

import pytest

from core.runtime import ws_auth


# ─────────────────────────────────────────────────── hvor tokenet maa komme fra

def test_headeren_virker_for_klienter_der_kan_saette_den():
    t, sub = ws_auth.token_fra_handshake({"Authorization": "Bearer abc123"})
    assert t == "abc123"
    assert sub is None


def test_subprotokollen_virker_for_browsere():
    t, sub = ws_auth.token_fra_handshake(
        {"sec-websocket-protocol": "jarvis-bearer, abc123"})
    assert t == "abc123"
    assert sub == "jarvis-bearer"


def test_headeren_vinder_over_subprotokollen():
    """En klient der kan sætte headers har ikke brug for omvejen."""
    t, _ = ws_auth.token_fra_handshake({
        "authorization": "Bearer fra-header",
        "sec-websocket-protocol": "jarvis-bearer, fra-sub",
    })
    assert t == "fra-header"


def test_protokol_UDEN_token_er_ikke_legitimation():
    """«jarvis-bearer» alene er et ønske om en protokol, ikke et bevis."""
    t, sub = ws_auth.token_fra_handshake({"sec-websocket-protocol": "jarvis-bearer"})
    assert t == ""
    assert sub == "jarvis-bearer"


def test_en_ukendt_protokol_bekraeftes_ikke():
    """Serveren må ALDRIG vælge en protokol klienten ikke bad om — browseren
    afviser så forbindelsen."""
    t, sub = ws_auth.token_fra_handshake({"sec-websocket-protocol": "noget-andet, x"})
    assert sub is None


def test_ingen_headers_giver_intet():
    t, sub = ws_auth.token_fra_handshake({})
    assert t == ""
    assert sub is None


@pytest.mark.parametrize("v", ["abc123", "bearer", "Basic abc", "Bearer", ""])
def test_kun_en_rigtig_bearer_taeller(v):
    """«Bearer» uden vaerdi, og et bart token uden ordet, er ikke gyldige."""
    t, _ = ws_auth.token_fra_handshake({"authorization": v})
    assert t == ""


# ───────────────────────────────────────────────────────── fejlretningen

def test_et_ugyldigt_token_er_et_NEJ():
    assert ws_auth.verificer("ikke-et-token") is None


def test_et_tomt_token_er_et_NEJ():
    assert ws_auth.verificer("") is None


def test_verificer_kaster_ALDRIG(monkeypatch):
    """En vagt der slipper igennem når den selv brækker, er ingen vagt."""
    import core.runtime.jarvisx_auth as ja
    monkeypatch.setattr(ja, "verify_token", lambda _t: (_ for _ in ()).throw(RuntimeError("i stykker")))
    assert ws_auth.verificer("hvadsomhelst") is None


# ────────────────────────────────────── og er vagten KOBLET paa ruten?

def test_ruten_afviser_uden_legitimation():
    """Husets hyppigste fejl: mekanismen findes, kalderen mangler. Her ville
    den betyde at hele rettelsen var pynt."""
    import ast
    import inspect
    from apps.api.jarvis_api.routes import live

    kilde = inspect.getsource(live.websocket_stream)
    tekst = ast.unparse(ast.parse(kilde.strip()))
    assert "token_fra_handshake" in tekst, "handshaket laeses ikke"
    assert "kraeves_auth" in tekst, "der spoerges ikke om auth er paakraevet"
    assert "auth_required" in tekst, "der lukkes ikke med en grund"
    # accept() maa ikke staa FOER afvisningen.
    assert tekst.index("token_fra_handshake") < tekst.index("accept")


def test_alle_desk_kaldesteder_bruger_hjaelperen():
    """Desk har TRE steder. Tre kopier ville drive fra hinanden, og den ene der
    blev glemt ville fejle tavst — socketen falder tilbage til polling, så
    intet ser i stykker ud."""
    import pathlib
    rod = pathlib.Path("apps/jarvis-desk/src")
    raa = []
    for f in rod.rglob("*.ts*"):
        if f.name == "api.ts":
            continue
        for nr, linje in enumerate(f.read_text().split("\n"), 1):
            if "new WebSocket(" in linje:
                raa.append(f"{f.relative_to(rod)}:{nr}")
    assert not raa, f"raa WebSocket uden legitimation: {raa}"


def test_de_tre_navne_er_ENS():
    """Serveren, web-UI'en og desk skal bruge samme protokolnavn. Driver de
    fra hinanden, fejler forbindelsen tavst."""
    import pathlib
    assert ws_auth.SUBPROTOKOL == "jarvis-bearer"
    ui = pathlib.Path("apps/ui/src/lib/auth.js").read_text()
    desk = pathlib.Path("apps/jarvis-desk/src/lib/api.ts").read_text()
    assert f"'{ws_auth.SUBPROTOKOL}'" in ui
    assert f"'{ws_auth.SUBPROTOKOL}'" in desk


# ─────────────────────────── den AEGTE rute, baade afvisning og accept

@pytest.fixture
def klient(monkeypatch):
    """En rigtig ASGI-klient mod selve ruten.

    Enhedstestene ovenfor maaler funktionerne. De kan ikke se om ruten faktisk
    lukker nogen ind — og en vagt der afviser ALLE er lige saa ubrugelig som en
    der afviser ingen. Uden denne test ville et braekket accept-led sende desk
    tilbage til polling og UI'en i tavshed.
    """
    from fastapi import FastAPI
    from starlette.testclient import TestClient
    from apps.api.jarvis_api.routes import live

    app = FastAPI()
    app.include_router(live.router)
    return TestClient(app)


def _kraev_auth(monkeypatch, paa: bool):
    import core.runtime.jarvisx_auth as ja
    monkeypatch.setattr(ja, "auth_required", lambda: paa)


def _tokenet_holder(monkeypatch):
    import core.runtime.jarvisx_auth as ja
    monkeypatch.setattr(ja, "verify_token", lambda raw: {"sub": "u1", "role": "owner"})


def test_ruten_LUKKER_uden_token(klient, monkeypatch):
    from starlette.websockets import WebSocketDisconnect
    _kraev_auth(monkeypatch, True)
    with pytest.raises(WebSocketDisconnect) as ei:
        with klient.websocket_connect("/ws"):
            pass
    assert ei.value.code == 1008


def test_ruten_LUKKER_IND_med_gyldig_subprotokol(klient, monkeypatch):
    """Den positive side. Uden den ville en rettelse der afviser alle se
    fuldstændig korrekt ud i alle andre tests."""
    _kraev_auth(monkeypatch, True)
    _tokenet_holder(monkeypatch)
    with klient.websocket_connect(
        "/ws", subprotocols=[ws_auth.SUBPROTOKOL, "et-gyldigt-token"],
    ) as ws:
        assert ws is not None


def test_ruten_bekraefter_den_protokol_klienten_bad_om(klient, monkeypatch):
    """Vælger serveren en anden — eller én klienten ikke bad om — afviser
    browseren forbindelsen, og det ville se ud som et netværksproblem."""
    _kraev_auth(monkeypatch, True)
    _tokenet_holder(monkeypatch)
    with klient.websocket_connect(
        "/ws", subprotocols=[ws_auth.SUBPROTOKOL, "t"],
    ) as ws:
        valgt = ws.scope.get("subprotocol") if hasattr(ws, "scope") else None
        assert valgt in (None, ws_auth.SUBPROTOKOL), valgt


def test_uden_auth_paakraevet_slipper_alle_ind(klient, monkeypatch):
    """Enkeltbruger-localhost uden auth skal stadig kunne køre — samme udvej
    som bro-socketen har."""
    _kraev_auth(monkeypatch, False)
    with klient.websocket_connect("/ws") as ws:
        assert ws is not None


def test_serveren_vaelger_INGEN_protokol_naar_klienten_ikke_bad_om_én(monkeypatch):
    """Mutationen der overlevede: `accept(subprotocol=SUBPROTOKOL)` altid.

    En browser afviser en forbindelse hvor serveren vælger en protokol klienten
    ikke bad om — og det ville ligne et netværksproblem, ikke en fejl i koden.
    Testen ovenfor tillod både `None` og navnet, så den kunne ikke se det.
    Her måles selve argumentet til `accept()`.
    """
    import asyncio
    from starlette.websockets import WebSocket
    from apps.api.jarvis_api.routes import live

    _kraev_auth(monkeypatch, False)
    valgt: list = []

    async def _falsk_accept(self, subprotocol=None, headers=None):
        valgt.append(subprotocol)
        raise _Stop()

    class _Stop(Exception):
        pass

    monkeypatch.setattr(WebSocket, "accept", _falsk_accept, raising=False)

    class _Ws:
        headers: dict = {}
        client = None
        async def accept(self, subprotocol=None, headers=None):
            valgt.append(subprotocol)
            raise _Stop()
        async def close(self, code=1000, reason=""):
            pass

    with pytest.raises(_Stop):
        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            live.websocket_stream(_Ws()))
    assert valgt == [None], valgt
