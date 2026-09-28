# tests/test_discord_dm_attachments.py
"""`send_discord_dm` skal kunne sende en RIGTIG fil-vedhæftning i en DM.

Målt 27/9-2026: Bjørn bad Discord-selvet sende Michelle et billede. Det kunne
ikke lade sig gøre — DM-vejen bar kun tekst, så billedet måtte sendes som en
URL, og blev derfor ikke vist inline. Jarvis skrev selv i DM'en at værktøjet
«ikke understøtter fil-vedhæftninger direkte».

Disse tests fælder den kode. De fejler hvis `file_path` ikke bæres hele vejen
fra værktøjet, gennem DM-funktionen, til DM-kanalen.

Kæden er: _exec_send_discord_dm → send_dm_to_owner/send_dm_to_user
          → _open_dm_and_send → send_discord_file → outbound-køen.
Selve kø-forbruget (`channel.send(file=...)`) fandtes i forvejen og er
uændret — det var kun vejen HERTIL der manglede.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def gateway_owner(monkeypatch):
    """Gør os til gateway-processen, så kaldene kører lokalt i stedet for HTTP.

    Pytest-vagten i `send_dm_to_owner` — den der forhindrer at en testkørsel
    når Bjørns telefon — fjernes IKKE her. Målt 27/9-2026: pytest sætter
    `PYTEST_CURRENT_TEST` på ny ved starten af hver fase, så en sletning i en
    fixture bliver overskrevet inden test-kroppen kører. Sletningen hører i
    kroppen; se `_uden_testvagt`.
    """
    import core.services.discord_gateway as gw

    monkeypatch.setattr(gw, "_is_gateway_owner", lambda: True)
    return gw


def _uden_testvagt(monkeypatch):
    """Fjern pytest-vagten i `send_dm_to_owner` for denne test-kørsel."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)


def _fang_kald(beholder, svar):
    """Returnér en fake der registrerer sine argumenter og svarer fast."""
    def _fake(*args, **kwargs):
        beholder["args"] = args
        beholder["kwargs"] = kwargs
        return svar
    return _fake


# ---------------------------------------------------------------------------
# DM-funktionerne: bærer de file_path videre?
# ---------------------------------------------------------------------------

def test_send_dm_to_owner_baerer_file_path(gateway_owner, monkeypatch):
    _uden_testvagt(monkeypatch)
    gw = gateway_owner
    fanget: dict = {}
    monkeypatch.setattr(
        gw, "_open_dm_and_send",
        _fang_kald(fanget, {"status": "sent", "channel_id": 1, "with_file": True}),
    )
    monkeypatch.setattr(
        "core.services.discord_config.load_discord_config",
        lambda: {"owner_discord_id": "42"},
    )

    result = gw.send_dm_to_owner("her er den", file_path="/tmp/a.png")

    assert result["status"] == "sent"
    assert fanget["kwargs"]["file_path"] == "/tmp/a.png"
    assert fanget["args"][0] == 42


def test_send_dm_to_owner_uden_fil_sender_tom_sti(gateway_owner, monkeypatch):
    # Regression: den gamle tekst-vej må ikke ændre adfærd.
    _uden_testvagt(monkeypatch)
    gw = gateway_owner
    fanget: dict = {}
    monkeypatch.setattr(
        gw, "_open_dm_and_send",
        _fang_kald(fanget, {"status": "sent", "channel_id": 1}),
    )
    monkeypatch.setattr(
        "core.services.discord_config.load_discord_config",
        lambda: {"owner_discord_id": "42"},
    )

    gw.send_dm_to_owner("bare tekst")

    assert fanget["kwargs"].get("file_path", "") == ""


def test_send_dm_to_user_baerer_file_path(gateway_owner, monkeypatch):
    gw = gateway_owner
    fanget: dict = {}

    class _Bruger:
        discord_id = "99"
        name = "Michelle"

    monkeypatch.setattr("core.identity.users.load_users", lambda: [_Bruger()])
    monkeypatch.setattr(
        gw, "_open_dm_and_send",
        _fang_kald(fanget, {"status": "sent", "channel_id": 2, "with_file": True}),
    )

    result = gw.send_dm_to_user("99", "her er den", file_path="/tmp/a.png")

    assert result["status"] == "sent"
    assert fanget["kwargs"]["file_path"] == "/tmp/a.png"
    assert fanget["args"][0] == 99


# ---------------------------------------------------------------------------
# _open_dm_and_send: køer den filen i stedet for tekst?
# ---------------------------------------------------------------------------

def _klar_dm_aabning(gw, monkeypatch):
    """Fake en åben DM-kanal uden et rigtigt Discord-loop."""
    class _FakeFuture:
        def result(self, timeout=None):
            return 4242

    def _fake_run(coro, loop):
        coro.close()  # undgå "coroutine was never awaited"
        return _FakeFuture()

    monkeypatch.setattr(gw.asyncio, "run_coroutine_threadsafe", _fake_run)
    monkeypatch.setattr(gw, "_status", {"connected": True})
    monkeypatch.setattr(gw, "_client", object())
    monkeypatch.setattr(gw, "_loop", object())


def test_open_dm_and_send_koer_filen_naar_sti_er_sat(gateway_owner, monkeypatch):
    gw = gateway_owner
    _klar_dm_aabning(gw, monkeypatch)

    fil_kald: list = []
    tekst_kald: list = []
    monkeypatch.setattr(
        gw, "send_discord_file",
        # **kw bærer `wait=True` — uden den ville _open_dm_and_send ikke
        # kunne vente på at Discord faktisk har taget imod (28/9-2026).
        lambda ch, t, p, **kw: (fil_kald.append((ch, t, p)), {"status": "sent", "files": 1})[1],
    )
    monkeypatch.setattr(
        gw, "send_discord_message",
        lambda ch, t: tekst_kald.append((ch, t)),
    )

    result = gw._open_dm_and_send(7, "her er den", 5.0, file_path="/tmp/a.png")

    assert result["status"] == "sent"
    assert result["with_file"] is True
    assert fil_kald == [(4242, "her er den", "/tmp/a.png")]
    # Filen må IKKE også gå som ren tekst-besked — så ville den blive sendt to gange.
    assert tekst_kald == []


def test_open_dm_and_send_afviser_fil_der_ikke_maa_sendes(gateway_owner, monkeypatch):
    gw = gateway_owner
    _klar_dm_aabning(gw, monkeypatch)
    monkeypatch.setattr(
        gw, "send_discord_file",
        lambda ch, t, p, **kw: {"status": "error", "reason": "not-allowed"},
    )

    result = gw._open_dm_and_send(7, "x", 5.0, file_path="/etc/passwd")

    assert result["status"] == "error"
    assert "file-send-rejected" in result["reason"]
    assert "not-allowed" in result["reason"]


# ---------------------------------------------------------------------------
# Værktøjet
# ---------------------------------------------------------------------------

def test_vaerktoejet_afviser_sti_udenfor_graensen():
    from core.tools.simple_tools_native import _exec_send_discord_dm

    r = _exec_send_discord_dm({"content": "hej", "file_path": "/etc/passwd"})

    assert r["status"] == "error"
    assert "rejected" in r["text"]


def test_vaerktoejet_videresender_file_path(monkeypatch):
    import core.services.attachment_service as svc
    import core.services.discord_gateway as gw
    from core.tools.simple_tools_native import _exec_send_discord_dm

    monkeypatch.setattr(svc, "validate_send_path", lambda p: (True, ""))
    fanget: dict = {}
    monkeypatch.setattr(
        gw, "send_dm_to_owner",
        lambda content, file_path="": (
            fanget.update(content=content, file_path=file_path),
            {"status": "sent", "channel_id": 5, "with_file": True},
        )[1],
    )

    r = _exec_send_discord_dm({"content": "her", "file_path": "/tmp/a.png"})

    assert r["status"] == "ok"
    assert "med fil" in r["text"]
    # Værktøjet normaliserer til en LISTE, så resten af kæden kun kender én
    # form — og så flere filer kan følge samme besked (28/9-2026).
    assert fanget["file_path"] == ["/tmp/a.png"]


def test_vaerktoejet_tillader_fil_uden_tekst(monkeypatch):
    # Et billede skal kunne sendes alene — uden en ledsagende sætning.
    import core.services.attachment_service as svc
    import core.services.discord_gateway as gw
    from core.tools.simple_tools_native import _exec_send_discord_dm

    monkeypatch.setattr(svc, "validate_send_path", lambda p: (True, ""))
    monkeypatch.setattr(
        gw, "send_dm_to_owner",
        lambda content, file_path="": {"status": "sent", "channel_id": 5, "with_file": True},
    )

    r = _exec_send_discord_dm({"file_path": "/tmp/a.png"})

    assert r["status"] == "ok"


def test_vaerktoejet_naegter_helt_tomt_kald():
    from core.tools.simple_tools_native import _exec_send_discord_dm

    r = _exec_send_discord_dm({})

    assert r["status"] == "error"
    assert "file_path" in r["text"] or "content" in r["text"]


# ---------------------------------------------------------------------------
# Kryds-proces-leddet: dispatch-endpointet
# ---------------------------------------------------------------------------

class _FakeRequest:
    class client:
        host = "127.0.0.1"
    headers: dict = {}


def test_dispatch_videresender_file_path(monkeypatch):
    """Værktøjer kører i api-processen; gatewayen i runtime-processen.

    Uden file_path i dispatch-payloaden ville filen forsvinde på tværs af
    proces-grænsen — og kun virke når begge dele tilfældigvis var samme proces.
    """
    from apps.api.jarvis_api.middleware import internal_discord as mw

    monkeypatch.setattr(mw, "_is_gateway_owner", lambda: True)
    fanget: dict = {}
    monkeypatch.setattr(
        mw, "send_dm_to_user",
        lambda rid, text, timeout, file_path="": (
            fanget.update(recipient=rid, file_path=file_path),
            {"status": "sent"},
        )[1],
    )

    req = mw.DispatchRequest(
        action="send_dm_to_user",
        args={"recipient_discord_id": "99", "text": "hej", "file_path": "/tmp/a.png"},
    )
    mw.dispatch(req, _FakeRequest())

    assert fanget["file_path"] == "/tmp/a.png"


def test_dispatch_videresender_file_path_til_ejer(monkeypatch):
    from apps.api.jarvis_api.middleware import internal_discord as mw

    monkeypatch.setattr(mw, "_is_gateway_owner", lambda: True)
    fanget: dict = {}
    monkeypatch.setattr(
        mw, "send_dm_to_owner",
        lambda text, timeout, file_path="": (
            fanget.update(file_path=file_path),
            {"status": "sent"},
        )[1],
    )

    req = mw.DispatchRequest(
        action="send_dm_to_owner",
        args={"text": "hej", "file_path": "/tmp/a.png"},
    )
    mw.dispatch(req, _FakeRequest())

    assert fanget["file_path"] == "/tmp/a.png"


# ---------------------------------------------------------------------------
# Schemaet: kan modellen overhovedet SE parameteren?
# ---------------------------------------------------------------------------

def test_schemaet_annoncerer_file_path():
    """Et værktøj modellen ikke kan se, kalder den ikke.

    Samme fejlklasse som «mekanismen findes — kalderen mangler»: her er det
    parameteren der findes i koden men ikke i det annoncerede schema.
    """
    from core.tools.simple_tools import get_tool_definitions

    defs = get_tool_definitions(role="owner", scope="")
    dm = next(
        (d for d in defs if d.get("function", {}).get("name") == "send_discord_dm"),
        None,
    )

    assert dm is not None, "send_discord_dm findes ikke i tool-definitionerne"
    props = dm["function"]["parameters"]["properties"]
    assert "file_path" in props
    assert "content" in props


def test_schemaet_tillader_en_liste_af_stier():
    """Schemaet skal annoncere at file_path kan være en liste.

    Uden det i schemaet ville modellen aldrig prøve at sende tre billeder i
    én besked — parameteren ville kun virke for den der læste koden.
    """
    from core.tools.simple_tools import get_tool_definitions

    defs = get_tool_definitions(role="owner", scope="")
    dm = next(
        d for d in defs if d.get("function", {}).get("name") == "send_discord_dm"
    )
    fp = dm["function"]["parameters"]["properties"]["file_path"]

    assert "oneOf" in fp
    typer = [v.get("type") for v in fp["oneOf"]]
    assert "string" in typer
    assert "array" in typer


# ---------------------------------------------------------------------------
# Flere filer i ÉN besked — Discord tillader op til 10 vedhæftninger
# ---------------------------------------------------------------------------

def test_send_discord_file_tager_en_liste(gateway_owner, monkeypatch):
    """Tre billeder skal kunne følge SAMME besked, ikke tre separate."""
    gw = gateway_owner
    monkeypatch.setattr(gw, "_validate_send_path", lambda p: (True, ""))
    queued: list = []
    monkeypatch.setattr(gw._outbound_queue, "put_nowait", lambda item: queued.append(item))

    result = gw.send_discord_file(1, "her", ["/a.png", "/b.png", "/c.png"])

    assert result["status"] == "queued"
    assert queued[0]["file_paths"] == ["/a.png", "/b.png", "/c.png"]


def test_send_discord_file_afviser_over_ti(gateway_owner, monkeypatch):
    """Discord tager maks 10 vedhæftninger — 11 skal afvises klart."""
    gw = gateway_owner
    monkeypatch.setattr(gw, "_validate_send_path", lambda p: (True, ""))

    result = gw.send_discord_file(1, "her", [f"/{i}.png" for i in range(11)])

    assert result["status"] == "error"
    assert "for-mange-filer" in result["reason"]


def test_send_discord_file_validerer_hele_listen(gateway_owner, monkeypatch):
    """Én dårlig sti må afvise HELE kaldet — ikke sende de gode alene."""
    gw = gateway_owner
    monkeypatch.setattr(
        gw, "_validate_send_path",
        lambda p: (False, "not-allowed") if p == "/etc/passwd" else (True, ""),
    )
    queued: list = []
    monkeypatch.setattr(gw._outbound_queue, "put_nowait", lambda item: queued.append(item))

    result = gw.send_discord_file(1, "her", ["/a.png", "/etc/passwd"])

    assert result["status"] == "error"
    assert "not-allowed" in result["reason"]
    assert queued == []


def test_send_discord_file_wait_svarer_med_discords_udfald(gateway_owner, monkeypatch):
    """wait=True skal svare med Discord's udfald — ikke «queued».

    Uden den meldte _open_dm_and_send «sent» om en besked der kun lå i køen.
    """
    gw = gateway_owner
    monkeypatch.setattr(gw, "_validate_send_path", lambda p: (True, ""))

    def _put(item):
        # Efterlign kø-forbrugeren: skriv svaret og sæt kvitteringen.
        item["svar"].update({"status": "sent", "channel_id": 1, "files": 1})
        item["ack"].set()

    monkeypatch.setattr(gw._outbound_queue, "put_nowait", _put)
    result = gw.send_discord_file(1, "her", ["/a.png"], wait=True)

    assert result["status"] == "sent"
    assert result["files"] == 1


def test_send_discord_file_wait_timeouter_uden_kvittering(gateway_owner, monkeypatch):
    """Uden kvittering må kaldet fejle ærligt — aldrig melde succes."""
    gw = gateway_owner
    monkeypatch.setattr(gw, "_validate_send_path", lambda p: (True, ""))
    monkeypatch.setattr(gw._outbound_queue, "put_nowait", lambda item: None)

    result = gw.send_discord_file(1, "her", ["/a.png"], wait=True, timeout=0.05)

    assert result["status"] == "error"
    assert "send-timeout" in result["reason"]


def test_vaerktoejet_videresender_en_liste(monkeypatch):
    """Tre stier ind → tre stier videre, og svaret nævner antallet."""
    import core.services.attachment_service as svc
    import core.services.discord_gateway as gw
    from core.tools.simple_tools_native import _exec_send_discord_dm

    monkeypatch.setattr(svc, "validate_send_path", lambda p: (True, ""))
    fanget: dict = {}
    monkeypatch.setattr(
        gw, "send_dm_to_owner",
        lambda content, file_path="": (
            fanget.update(content=content, file_path=file_path),
            {"status": "sent", "channel_id": 5, "with_file": True, "files": 3},
        )[1],
    )

    r = _exec_send_discord_dm(
        {"content": "her", "file_path": ["/a.png", "/b.png", "/c.png"]}
    )

    assert r["status"] == "ok"
    assert "3 filer" in r["text"]
    assert fanget["file_path"] == ["/a.png", "/b.png", "/c.png"]


def test_vaerktoejet_afviser_en_daarlig_sti_i_listen(monkeypatch):
    """Én afvist sti i listen skal give en KLAR fejl — ikke en tavs drop."""
    import core.services.attachment_service as svc
    from core.tools.simple_tools_native import _exec_send_discord_dm

    monkeypatch.setattr(
        svc, "validate_send_path",
        lambda p: (False, "not-allowed") if p == "/etc/passwd" else (True, ""),
    )

    r = _exec_send_discord_dm(
        {"content": "her", "file_path": ["/a.png", "/etc/passwd"]}
    )

    assert r["status"] == "error"
    assert "rejected" in r["text"]
