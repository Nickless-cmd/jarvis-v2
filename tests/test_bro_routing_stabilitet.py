"""Broen valgte den klient der forsvinder — og kørslen blev stående.

## Hvad der skete (14/9-2026)

Bjørn: «Ham svare ikk». Hans telefon var registreret som udfører, og
dispatch-loggen viste `operator_bash` hvert tredje sekund indtil 20:37:18.
Otte sekunder senere:

    jarvisx_bridge: unregistered user=… client=mobil-2j1dxlnh

og alt arbejde stoppede dødt. Desk-appen (`jarvisx-electron`) sad forbundet
hele tiden — den stod i `andre=[…]` på samme linje.

## Hvorfor telefonen vandt

`get_bridge` valgte den nyest forbundne blandt dem der kan værktøjet:

    # Melder BEGGE enheder vaerktoejet, vinder den nyest forbundne —
    # den Bjoern sidst har haft i haanden.
    return max(kan, key=lambda c: c.reg_seq)

Telefonen gen-registrerer konstant, så dens `reg_seq` er altid højest. Og
Bjørn: «det sker ikk kun når skærmen går i sort men også når man bar går ud af
appen» — altså ved hvert eneste app-skift.

## To ændringer, og de gør hver sit

1. **Kan FLERE klienter værktøjet, vælges den der ikke kan forsvinde.**
   Reglen om «sidst i hånden» er stadig rigtig for enheds-specifikke værktøjer
   — men dér melder kun ÉN klient værktøjet, så den gren er urørt.

2. **Forsvinder udføreren midt i et kald, prøves en anden.** Det er den
   generelle regel: Bjørn — «Et run må aldrig dø». En præference kan gætte
   forkert; en fail-over retter sig selv.
"""
from __future__ import annotations

import asyncio

import pytest

from core.services.jarvisx_bridge import BridgeConnection, BridgeRegistry


def _bro(client: str, platform: str, caps: list[str], ws=None) -> BridgeConnection:
    return BridgeConnection(
        user_id="u1", client=client, client_id=client,
        platform=platform, capabilities=list(caps), ws=ws,
    )


# ─────────────────────────────────────────────────── valget mellem klienter

def test_naar_BEGGE_kan_vaerktoejet_vinder_den_der_ikke_forsvinder():
    """Det ægte fund. Telefonen var nyest og vandt — og gik så ud af appen."""
    r = BridgeRegistry()
    desk = _bro("jarvisx-electron", "linux-x64", ["operator_bash"])
    r.register(desk)
    mobil = _bro("jarvis-mobile", "android", ["operator_bash"])
    r.register(mobil)          # nyest — vandt før
    assert r.get_bridge("u1", tool="operator_bash") is desk


def test_et_ENHEDS_specifikt_vaerktoej_gaar_stadig_til_telefonen():
    """«Sidst i hånden»-reglen er rigtig når kun én kan det. `phone_location`
    kan desk umuligt udføre, og et ærligt valg her er hele pointen."""
    r = BridgeRegistry()
    r.register(_bro("jarvisx-electron", "linux-x64", ["operator_bash"]))
    mobil = _bro("jarvis-mobile", "android", ["phone_location"])
    r.register(mobil)
    assert r.get_bridge("u1", tool="phone_location") is mobil


def test_er_telefonen_ALENE_faar_den_kaldet():
    """En præference må ikke blive et forbud. Er desk væk, er telefonen det
    bedste vi har, og et «ingen bro» ville være værre."""
    r = BridgeRegistry()
    mobil = _bro("jarvis-mobile", "android", ["operator_bash"])
    r.register(mobil)
    assert r.get_bridge("u1", tool="operator_bash") is mobil


def test_to_STABILE_klienter_afgoeres_stadig_af_hvem_der_er_nyest():
    """Inden for samme stabilitet står den gamle regel ved magt."""
    r = BridgeRegistry()
    r.register(_bro("desk-a", "linux-x64", ["operator_bash"]))
    ny = _bro("desk-b", "darwin-arm64", ["operator_bash"])
    r.register(ny)
    assert r.get_bridge("u1", tool="operator_bash") is ny


def test_to_TELEFONER_afgoeres_ogsaa_af_hvem_der_er_nyest():
    r = BridgeRegistry()
    r.register(_bro("mobil-a", "android", ["operator_bash"]))
    ny = _bro("mobil-b", "ios", ["operator_bash"])
    r.register(ny)
    assert r.get_bridge("u1", tool="operator_bash") is ny


def test_ukendt_platform_regnes_som_STABIL():
    """En klient der ikke siger hvad den er, skal opføre sig som før. At
    behandle tavshed som «kan forsvinde» ville flytte rundt på ældre broer
    uden belæg."""
    r = BridgeRegistry()
    r.register(_bro("gammel", "", ["operator_bash"]))
    mobil = _bro("jarvis-mobile", "android", ["operator_bash"])
    r.register(mobil)
    assert r.get_bridge("u1", tool="operator_bash").client == "gammel"


# ─────────────────────────────────────── naar udfoereren forsvinder MIDT i et kald

class _FakeWS:
    """En websocket der enten svarer eller lader som om den er væk."""

    def __init__(self, svar: dict | None = None, doed: bool = False):
        self.svar = svar
        self.doed = doed
        self.sendte: list = []

    async def send_json(self, m):
        if self.doed:
            raise RuntimeError("websocket lukket")
        self.sendte.append(m)


@pytest.mark.asyncio
async def test_forsvinder_udfoereren_proeves_den_ANDEN_klient():
    """Bjørn: «Et run må aldrig dø». En præference kan gætte forkert; en
    fail-over retter sig selv.

    Her er det DESK der er død — altså den præferencen valgte. Så prøver vi
    den anden. Første udgave af testen gjorde telefonen død og tvang valget
    hen på den; den målte derfor ikke fail-overen, men præferencen én gang til.
    """
    r = BridgeRegistry()
    desk = _bro("jarvisx-electron", "linux-x64", ["operator_bash"], ws=_FakeWS(doed=True))
    r.register(desk)
    mobil = _bro("jarvis-mobile", "android", ["operator_bash"], ws=_FakeWS())
    r.register(mobil)
    assert r.get_bridge("u1", tool="operator_bash") is desk   # den doede vaelges

    async def _svar_snart():
        for _ in range(60):
            await asyncio.sleep(0.02)
            for cid in list(mobil._pending):
                # `deliver_result` sidder paa FORBINDELSEN, ikke paa registret,
                # er async og tager noegleord. Foerste udgave kaldte den som en
                # synkron registry-metode — og testen timede ud paa sin egen
                # fejl i stedet for paa koden.
                await mobil.deliver_result(
                    correlation_id=cid, status="ok", result="det virkede")
                return

    opgave = asyncio.create_task(_svar_snart())
    ud = await r.dispatch(user_id="u1", tool="operator_bash", args={},
                          timeout_s=3.0, allow_cross_process=False)
    await opgave
    assert ud["status"] == "ok", ud
    assert mobil.ws.sendte, "den anden klient blev aldrig proevet"


@pytest.mark.asyncio
async def test_er_der_INGEN_anden_klient_fejler_kaldet_aerligt():
    """Et ærligt «ingen bro» er bedre end en uendelig runde forsøg."""
    r = BridgeRegistry()
    r.register(_bro("jarvis-mobile", "android", ["operator_bash"], ws=_FakeWS(doed=True)))
    ud = await r.dispatch(user_id="u1", tool="operator_bash", args={},
                          timeout_s=1.0, allow_cross_process=False)
    assert ud["status"] == "error"
