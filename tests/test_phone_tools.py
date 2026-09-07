"""Telefon-vaerktoejer — samme bro, andre organer.

Kernen i testene er ikke at wrapperne kalder videre (det er tyndt), men at
et ``phone_*``-kald lander paa TELEFONEN naar baade computer og telefon er
forbundet. Det var hele grunden til at capability-routing blev bygget.
"""

from __future__ import annotations

import asyncio

import pytest

from core.tools import phone_tools as P


def test_definitioner_og_handlere_daekker_samme_navne():
    """Tre lister maa ikke kunne glide fra hinanden.

    Navnene staar i PHONE_TOOL_NAMES, definitionerne og exec-tabellen. Skrev
    man et vaerktoej ind ét sted og glemte de andre, ville det enten blive
    annonceret uden at kunne kaldes, eller kunne kaldes uden at nogen ved det
    findes — begge dele tavse.
    """
    fra_def = {d["function"]["name"] for d in P.PHONE_TOOL_DEFINITIONS}
    assert fra_def == set(P.PHONE_TOOL_NAMES)
    assert set(P.PHONE_TOOL_EXECUTORS) == set(P.PHONE_TOOL_NAMES)


def test_vaerktoejerne_er_registreret_i_runtime():
    """De skal kunne kaldes, ikke bare defineres.

    [[built_but_not_connected]] er det hyppigste moenster i dette repo: koden
    er korrekt, men ingen kalder den. Testen holder baade annoncering og
    handler-tabel fast.
    """
    from core.tools.simple_tools import get_tool_definitions, _TOOL_HANDLERS

    annonceret = {(d.get("function") or d).get("name") for d in get_tool_definitions()}
    assert set(P.PHONE_TOOL_NAMES) <= annonceret
    assert set(P.PHONE_TOOL_NAMES) <= set(_TOOL_HANDLERS)


def test_kaldet_lander_paa_telefonen_ikke_computeren():
    """Hele pointen: routing paa capabilities, ikke paa user_id alene.

    Foer 7/9 routede dispatch() kun paa user_id, saa et telefon-kald ville
    ryge til den bro der tilfaeldigvis var registreret — computeren.
    """
    from core.services.jarvisx_bridge import bridge_registry, BridgeConnection

    bridge_registry.clear()
    desk = BridgeConnection(user_id="u1", client="jarvisx-electron", client_id="desk",
                            capabilities=["operator_bash", "operator_screenshot"])
    tlf = BridgeConnection(user_id="u1", client="jarvis-mobile", client_id="mobil",
                           capabilities=list(P.PHONE_TOOL_NAMES))
    bridge_registry.register(desk)
    bridge_registry.register(tlf)

    assert bridge_registry.get_bridge("u1", tool="phone_location") is tlf
    assert bridge_registry.get_bridge("u1", tool="operator_bash") is desk
    bridge_registry.clear()


def test_en_sovende_telefon_vaekkes_foer_kaldet(monkeypatch):
    """Skaermen er slukket det meste af tiden — uden vaekning ville et
    telefon-kald fejle naesten altid.

    Maalt 7/9: broen registrerede sig 15:13:51 og afmeldte sig 15:14:24, da
    telefonen blev lagt fra sig. Android kapper forbindelsen; vaekningen er
    svaret paa det, ikke en omgaaelse af det.
    """
    kaldt: list[str] = []

    from core.services import phone_wake
    monkeypatch.setattr(phone_wake, "telefon_er_forbundet", lambda uid: False)
    monkeypatch.setattr(phone_wake, "vaek_og_vent",
                        lambda uid, **kw: kaldt.append(uid) or True)

    async def fake_dispatch(**kw):
        return {"status": "ok", "result": {"breddegrad": 55.6}}

    from core.services.jarvisx_bridge import bridge_registry
    monkeypatch.setattr(bridge_registry, "dispatch", fake_dispatch)

    r = asyncio.run(P.phone_location_async(user_id="u1"))
    assert kaldt == ["u1"]
    assert r["breddegrad"] == 55.6


def test_en_vaagen_telefon_vaekkes_ikke(monkeypatch):
    """Vaekning er en FCM-levering og en app-opstart. Er den der, lad vaere."""
    from core.services import phone_wake
    monkeypatch.setattr(phone_wake, "telefon_er_forbundet", lambda uid: True)
    monkeypatch.setattr(phone_wake, "vaek_og_vent",
                        lambda uid, **kw: pytest.fail("maatte ikke vaekke"))

    async def fake_dispatch(**kw):
        return {"status": "ok", "result": {}}

    from core.services.jarvisx_bridge import bridge_registry
    monkeypatch.setattr(bridge_registry, "dispatch", fake_dispatch)
    asyncio.run(P.phone_location_async(user_id="u1"))


def test_telefon_der_ikke_kom_giver_en_laeselig_grund(monkeypatch):
    """Kom den ikke EFTER en vaekning, er «den sover» ikke laengere svaret.

    Beskeden skal pege paa det der saa faktisk kan vaere galt — og paa
    ADB-vejen, som ikke rammes af baggrundsproblemet.
    """
    from core.services import phone_wake
    monkeypatch.setattr(phone_wake, "telefon_er_forbundet", lambda uid: False)
    monkeypatch.setattr(phone_wake, "vaek_og_vent", lambda uid, **kw: False)

    async def fake_dispatch(**kw):
        return {"status": "error", "error": "bridge_not_connected"}

    from core.services.jarvisx_bridge import bridge_registry
    monkeypatch.setattr(bridge_registry, "dispatch", fake_dispatch)

    with pytest.raises(RuntimeError) as ei:
        asyncio.run(P.phone_location_async(user_id="u1"))
    besked = str(ei.value)
    assert "phone_not_connected" in besked
    assert "vaekning" in besked and "phone_adb_" in besked


def test_en_vaekning_der_kaster_stopper_ikke_kaldet(monkeypatch):
    """FCM nede maa ikke betyde at en VAAGEN telefon ikke kan naas."""
    from core.services import phone_wake

    def eksploder(uid):
        raise RuntimeError("fcm nede")

    monkeypatch.setattr(phone_wake, "telefon_er_forbundet", eksploder)

    async def fake_dispatch(**kw):
        return {"status": "ok", "result": {"ok": True}}

    from core.services.jarvisx_bridge import bridge_registry
    monkeypatch.setattr(bridge_registry, "dispatch", fake_dispatch)
    assert asyncio.run(P.phone_location_async(user_id="u1")) == {"ok": True}


def test_en_aegte_fejl_forveksles_ikke_med_en_sovende_telefon(monkeypatch):
    """Modstykket: en rigtig fejl maa ikke forsvinde i «telefonen sover»."""
    async def fake_dispatch(**kw):
        return {"status": "error", "error": "camera_permission_denied"}

    from core.services.jarvisx_bridge import bridge_registry
    monkeypatch.setattr(bridge_registry, "dispatch", fake_dispatch)

    with pytest.raises(RuntimeError) as ei:
        asyncio.run(P.phone_photo_async(user_id="u1"))
    assert "phone_not_connected" not in str(ei.value)
    assert "camera_permission_denied" in str(ei.value)


def test_optagelsens_timeout_foelger_dens_laengde(monkeypatch):
    """En fast timeout ville skaere en lang optagelse over.

    60 sekunders lyd kan ikke hentes hjem inden for en 45-sekunders default.
    """
    set_timeout: list[float] = []

    async def fake_dispatch(**kw):
        set_timeout.append(kw["timeout_s"])
        return {"status": "ok", "result": {}}

    from core.services.jarvisx_bridge import bridge_registry
    monkeypatch.setattr(bridge_registry, "dispatch", fake_dispatch)

    asyncio.run(P.phone_record_audio_async(user_id="u1", sekunder=60))
    assert set_timeout[0] > 60


@pytest.mark.parametrize("sekunder,forventet", [(0, 0.5), (999, 120.0), (5, 5.0)])
def test_optagelsens_laengde_klippes_til_noget_rimeligt(monkeypatch, sekunder, forventet):
    """Nul sekunder er ikke en optagelse, og en time er ikke en note."""
    set_args: list[dict] = []

    async def fake_dispatch(**kw):
        set_args.append(kw["args"])
        return {"status": "ok", "result": {}}

    from core.services.jarvisx_bridge import bridge_registry
    monkeypatch.setattr(bridge_registry, "dispatch", fake_dispatch)

    asyncio.run(P.phone_record_audio_async(user_id="u1", sekunder=sekunder))
    assert set_args[0]["sekunder"] == forventet


def test_kameraets_forgrundskrav_staar_i_beskrivelsen():
    """Begraensningen skal kunne laeses FOER kaldet, ikke opdages efter en timeout.

    Kameraet kan ikke aabnes fra baggrunden paa Android. Position og lyd kan,
    og det staar der ogsaa — forskellen er det der goer valget muligt.
    """
    ved_navn = {d["function"]["name"]: d["function"]["description"]
                for d in P.PHONE_TOOL_DEFINITIONS}
    assert "forgrunden" in ved_navn["phone_photo"]
    assert "baggrunden" in ved_navn["phone_location"]
    assert "baggrunden" in ved_navn["phone_record_audio"]


def test_deling_lover_ikke_at_sende_noget():
    """``phone_share`` aabner et ark — den sender ikke selv.

    Forskellen betyder noget: et vaerktoej der «deler» lyder som om Jarvis
    kan sende noget ud af huset paa egen haand. Det kan han ikke her, og
    beskrivelsen skal ikke antyde det.
    """
    d = {x["function"]["name"]: x["function"]["description"]
         for x in P.PHONE_TOOL_DEFINITIONS}["phone_share"]
    assert "ÅBNER" in d and "sender ikke selv" in d


# ── porten: vaerktoejerne findes kun naar telefonen goer ─────────────────


def _presence(monkeypatch, klienter: dict) -> None:
    """Stil presence op som om de givne klienter er forbundet for owner."""
    from core.services import bridge_presence
    monkeypatch.setattr(
        "core.identity.workspace_context.current_user_id", lambda: "u1",
    )
    monkeypatch.setattr(
        bridge_presence, "all_presence",
        lambda: {"u1": {"process": "api", "clients": klienter}},
    )


def test_ingen_telefon_ingen_telefon_vaerktoejer(monkeypatch):
    """Overfladen udvides ikke naar intet er paret.

    Samme princip som desk-undtagelsen: operator-vaerktoejer dukker kun op i
    chat naar en desk-bro faktisk er forbundet.
    """
    from core.tools import tool_scoping as TS

    _presence(monkeypatch, {"desk": {"capabilities": ["operator_bash"]}})
    assert TS._owner_has_live_phone() is False

    tilladt = TS.allowed_tool_names(
        role="owner", scope="chat", all_names=list(P.PHONE_TOOL_NAMES) + ["operator_bash"],
    )
    assert not (set(P.PHONE_TOOL_NAMES) & tilladt)


def test_forbundet_telefon_giver_telefon_vaerktoejer_i_chat(monkeypatch):
    """Bjoern skriver mest fra mobil-chatten — dér skal de kunne naas.

    Uden det her ville vaerktoejerne vaere registreret, annonceret og
    eksekverbare, men usynlige praecis dér hvor de bruges.
    """
    from core.tools import tool_scoping as TS

    _presence(monkeypatch, {
        "desk": {"capabilities": ["operator_bash"]},
        "mobil": {"capabilities": list(P.PHONE_TOOL_NAMES)},
    })
    assert TS._owner_has_live_phone() is True

    tilladt = TS.allowed_tool_names(
        role="owner", scope="chat", all_names=list(P.PHONE_TOOL_NAMES),
    )
    assert set(P.PHONE_TOOL_NAMES) <= tilladt


def test_porten_kender_telefonen_paa_hvad_den_KAN(monkeypatch):
    """Ikke paa klientnavnet.

    Samme mekanik som routingen bruger, saa porten og valget ikke kan komme
    til at vaere uenige om hvad der er en telefon.
    """
    from core.tools import tool_scoping as TS

    _presence(monkeypatch, {"noget-vi-aldrig-har-set": {"capabilities": ["phone_photo"]}})
    assert TS._owner_has_live_phone() is True

    _presence(monkeypatch, {"jarvis-mobile": {"capabilities": []}})
    assert TS._owner_has_live_phone() is False


def test_aeldre_presence_uden_clients_bryder_ikke(monkeypatch):
    """En proces der endnu ikke har genpubliceret har den flade form.

    Under en rullende genstart koerer de to processer kortvarigt hver sin
    version af presence-formen.
    """
    from core.services import bridge_presence
    from core.tools import tool_scoping as TS

    monkeypatch.setattr("core.identity.workspace_context.current_user_id", lambda: "u1")
    monkeypatch.setattr(
        bridge_presence, "all_presence",
        lambda: {"u1": {"process": "api", "capabilities": ["phone_photo"]}},
    )
    assert TS._owner_has_live_phone() is True


def test_en_erstattet_bro_proeves_igen(monkeypatch):
    """«bridge_replaced» = telefonen er der stadig, forbindelsen blev bare ny.

    Sker typisk fordi Bjoern aabner appen mens et kald er undervejs. At give
    op ville sende en fejl tilbage for noget der lykkes et sekund senere.
    """
    forsoeg: list[int] = []

    async def fake_dispatch(**kw):
        forsoeg.append(1)
        if len(forsoeg) == 1:
            return {"status": "error", "error": "phone_location failed: bridge_replaced"}
        return {"status": "ok", "result": {"breddegrad": 55.6}}

    from core.services import phone_wake
    from core.services.jarvisx_bridge import bridge_registry
    monkeypatch.setattr(phone_wake, "telefon_er_forbundet", lambda uid: True)
    monkeypatch.setattr(bridge_registry, "dispatch", fake_dispatch)

    r = asyncio.run(P.phone_location_async(user_id="u1"))
    assert len(forsoeg) == 2
    assert r["breddegrad"] == 55.6


def test_der_proeves_kun_EEN_gang_igen(monkeypatch):
    """Sker det to gange, er der noget andet galt end en tilfaeldig overlapning."""
    forsoeg: list[int] = []

    async def fake_dispatch(**kw):
        forsoeg.append(1)
        return {"status": "error", "error": "bridge_replaced"}

    from core.services import phone_wake
    from core.services.jarvisx_bridge import bridge_registry
    monkeypatch.setattr(phone_wake, "telefon_er_forbundet", lambda uid: True)
    monkeypatch.setattr(bridge_registry, "dispatch", fake_dispatch)

    with pytest.raises(RuntimeError):
        asyncio.run(P.phone_location_async(user_id="u1"))
    assert len(forsoeg) == 2
