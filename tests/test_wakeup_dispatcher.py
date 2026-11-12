"""Unit tests for wakeup_dispatcher.

KONTRAKT (11/11-2026): dispatcheren starter ikke selv et run. Den afleverer
signalet til `wake_gateway.anmod_om_vaekning`; `dispatched=True` betyder
«afleveret til indbakken», og `inbox_idle_waker` vurderer og vækker. Aktiv-
guarden (`_active_turn_blocks`) bor derfor i wakeren, ikke her.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from core.services.wakeup_dispatcher import dispatch_due_wakeups

GATEWAY = "core.services.wake_gateway.anmod_om_vaekning"
_KOEET = {"status": "queued", "grund": ""}


@pytest.fixture(autouse=True)
def _samtalen_er_fri(monkeypatch):
    """Forudsætningen disse tests HAR, men ikke sagde højt.

    20/9-2026 fik dispatcheren to nye betingelser: et wakeup startes ikke hvis
    samtalen har et levende run, og heller ikke inden for ti minutter efter
    brugerens sidste besked (Bjørn: «hvis han selv er i gang må en autonom
    session ikke kunne starte i samme session»).

    Wakeup-posterne her bærer ingen `session_id`, så måltavlen resolves — og i
    en FULD suite lander den på en samtale hvor andre tests har efterladt en
    frisk brugerbesked i den delte test-DB. Så blokerede vagten, og tre tests
    faldt. De passerede hver for sig, hvilket er den værste slags rød.

    Emnet her er «et fyret wakeup dispatches og markeres» — ikke vagten. Den
    har sine egne tests i `test_wakeup_aktiv_samtale_guard.py`. Så siger vi
    forudsætningen højt i stedet for at lade den afhænge af hvad naboen
    efterlod.
    """
    from core.services import chat_sessions, run_event_log
    monkeypatch.setattr(run_event_log, "active_run_for_session", lambda sid: None)
    monkeypatch.setattr(chat_sessions, "recent_chat_session_messages", lambda sid, **k: [])


def test_dispatch_no_fired_returns_zero():
    with patch("core.services.self_wakeup.due_wakeups", return_value=[]):
        result = dispatch_due_wakeups()
    assert result["dispatched"] == 0


def test_dispatch_fires_webchat_and_marks_dispatched():
    # Notification now routes through the nudge system when nudge_system_enabled
    # (the default); send_session_notification is only the disabled-nudge fallback.
    state = [{"wakeup_id": "w1", "prompt": "check confidence", "reason": "test", "status": "fired"}]
    # 17/10-2026: `due_wakeups` returnerer de SAMME record-objekter som den
    # laeste fra lageret. Stubben skal derfor vaere identisk med `state` — den
    # gamle letvaegts-kopi manglede felter som `session_id`/`channel`, saa
    # testen maalte en record der ikke findes i produktion.
    fired = state
    with patch("core.services.self_wakeup.due_wakeups", return_value=fired), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save") as fake_save, \
         patch("core.services.outbound_nudges.push_nudge") as fake_push, \
         patch("core.services.heartbeat_phases.tick_with_phases") as fake_tick, \
         patch(GATEWAY, return_value=_KOEET):
        result = dispatch_due_wakeups()
        _ventende_tick()
    assert result["dispatched"] == 1
    assert "w1" in result["dispatched_ids"]
    fake_push.assert_called_once()
    fake_tick.assert_called_once()
    # Should have set dispatched=True and saved
    assert state[0].get("dispatched") is True
    fake_save.assert_called()


def test_dispatch_hands_wakeup_to_gateway_with_origin_session():
    state = [{
        "wakeup_id": "w1",
        "prompt": "p",
        "reason": "r",
        "status": "fired",
        "channel": "app",
        "session_id": "chat-origin",
    }]
    fired = state
    with patch("core.services.self_wakeup.due_wakeups", return_value=fired), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save"), \
         patch("core.services.outbound_nudges.push_nudge"), \
         patch("core.services.heartbeat_phases.tick_with_phases"), \
         patch(GATEWAY, return_value=_KOEET) as fake_gw:
        result = dispatch_due_wakeups()

    assert result["dispatched"] == 1
    fake_gw.assert_called_once()
    _kwargs = dict(fake_gw.call_args.kwargs)
    # PERMISSIONS-KILDEN (9/11-2026): vækningen skal bære sin oprindelses-
    # samtale, saa niveauet læses der og ikke fra `auto-*`-siloen.
    assert _kwargs["permission_session"] == "chat-origin"
    assert _kwargs["session_id"] == "chat-origin"
    assert _kwargs["kilde"] == "wakeup_dispatcher"
    assert _kwargs["sag"] == "wakeup:w1"
    assert _kwargs["task_id"] == ""


def test_dispatch_skips_already_dispatched():
    state = [{"wakeup_id": "w1", "prompt": "p", "reason": "r", "status": "fired", "dispatched": True}]
    fired = state
    with patch("core.services.self_wakeup.due_wakeups", return_value=fired), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save"), \
         patch("core.services.notification_bridge.send_session_notification") as fake_send:
        result = dispatch_due_wakeups()
    assert result["dispatched"] == 0
    fake_send.assert_not_called()


def test_dispatch_skips_already_skipped_without_repeating_side_effects():
    """Et skip ligger i den durable indbakke og må ikke slå hjertet hvert minut."""
    state = [{
        "wakeup_id": "w1",
        "prompt": "p",
        "reason": "r",
        "status": "fired",
        "dispatch_skipped": True,
        "dispatch_skipped_reason": "session_har_levende_run",
    }]
    with patch("core.services.self_wakeup.due_wakeups", return_value=state), \
         patch("core.services.outbound_nudges.push_nudge") as fake_push, \
         patch("core.services.heartbeat_phases.tick_with_phases") as fake_tick, \
         patch(GATEWAY) as fake_gw:
        result = dispatch_due_wakeups()

    assert result["dispatched"] == 0
    fake_push.assert_not_called()
    fake_tick.assert_not_called()
    fake_gw.assert_not_called()


def test_dispatch_continues_if_webchat_fails():
    state = [{"wakeup_id": "w1", "prompt": "p", "reason": "r", "status": "fired"}]
    fired = state
    with patch("core.services.self_wakeup.due_wakeups", return_value=fired), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save"), \
         patch("core.services.notification_bridge.send_session_notification",
               side_effect=Exception("webchat down")), \
         patch("core.services.heartbeat_phases.tick_with_phases"), \
         patch(GATEWAY, return_value=_KOEET):
        result = dispatch_due_wakeups()
    # Should still mark dispatched even if webchat fails
    assert result["dispatched"] == 1
    assert state[0].get("dispatched") is True


def test_dispatch_handles_multiple_fired():
    state = [
        {"wakeup_id": "w1", "prompt": "p1", "reason": "r1", "status": "fired"},
        {"wakeup_id": "w2", "prompt": "p2", "reason": "r2", "status": "fired"},
    ]
    fired = state
    with patch("core.services.self_wakeup.due_wakeups", return_value=fired), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save"), \
         patch("core.services.notification_bridge.send_session_notification"), \
         patch("core.services.heartbeat_phases.tick_with_phases"), \
         patch(GATEWAY, return_value=_KOEET) as fake_gw:
        result = dispatch_due_wakeups()
    assert result["dispatched"] == 2
    assert [c.kwargs["sag"] for c in fake_gw.call_args_list] == ["wakeup:w1", "wakeup:w2"]


def test_dispatch_carries_task_session_and_permission_through_gateway():
    """Den vigtigste: migreringen må ikke tabe task_id / session / permissions.

    Recorden er booket i `chat-booket` og hører til opgave `opg-7`. Gatewayen
    skal modtage præcis de værdier — ellers mister indbakke-vækkeren dem.
    """
    state = [{
        "wakeup_id": "w1",
        "prompt": "p",
        "reason": "r",
        "status": "fired",
        "channel": "app",
        "session_id": "chat-booket",
        "task_id": "opg-7",
        "user_id": "owner-123",
    }]
    fanget: list[dict] = []

    def _gw(**kwargs):
        fanget.append(kwargs)
        return dict(_KOEET)

    with patch("core.services.self_wakeup.due_wakeups", return_value=state), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save"), \
         patch("core.services.outbound_nudges.push_nudge"), \
         patch("core.services.heartbeat_phases.tick_with_phases"), \
         patch(GATEWAY, side_effect=_gw):
        result = dispatch_due_wakeups()

    assert result["dispatched"] == 1
    assert len(fanget) == 1
    kw = fanget[0]
    assert kw["task_id"] == "opg-7"
    assert kw["session_id"] == "chat-booket"
    assert kw["permission_session"] == "chat-booket"
    assert kw["bruger_id"] == "owner-123"
    assert kw["importance"] == "normal"


def test_dispatch_does_not_mark_delivered_when_gateway_raises():
    state = [{
        "wakeup_id": "w1",
        "prompt": "p",
        "reason": "r",
        "status": "fired",
        "channel": "app",
        "session_id": "chat-origin",
    }]
    fired = state
    with patch("core.services.self_wakeup.due_wakeups", return_value=fired), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save") as fake_save, \
         patch("core.services.outbound_nudges.push_nudge"), \
         patch("core.services.heartbeat_phases.tick_with_phases"), \
         patch(GATEWAY, side_effect=RuntimeError("start failed")):
        result = dispatch_due_wakeups()

    assert result["dispatched"] == 0
    assert state[0].get("dispatched") is not True
    # 12/9-2026: _save SKAL kaldes nu — sporet (dispatch_skipped) efterlades, så
    # awareness-vejen kan skelne «faldt tilbage» fra «kørte planlagt». Før sprang
    # `if not run_started: continue` _save() over, og recorden stod som 'fired'
    # uden forklaring (målt: wake-d07eaea13d). Kernen er uændret: ikke leveret.
    fake_save.assert_called_once()
    assert state[0]["dispatch_skipped"] is True
    assert "run_start_failed" in state[0]["dispatch_skipped_reason"]


# ── Discord-routing-guard (Bjørn 2026-06-13: wakeup landede på Discord) ──
from core.services.wakeup_dispatcher import pick_wakeup_run_target


def _ext(sid):
    """Test-stub: sessioner der starter med 'disc-' er Discord-kanaler."""
    return str(sid).startswith("disc-")


def test_app_wakeup_never_routes_to_discord_via_owner_resolver():
    # owner-resolveren ville vælge en Discord-session, men app-resolveren
    # (guardet) returnerer en app-session → app-wakeup lander i app.
    target = pick_wakeup_run_target(
        channel="app", record_session="",
        app_resolver=lambda: "app-42",
        owner_resolver=lambda: "disc-99",  # ville lække til Discord
        is_external=_ext,
    )
    assert target == "app-42"
    assert not _ext(target)


def test_app_wakeup_rejects_explicit_discord_session():
    # Selv en eksplicit Discord-session_id afvises for app-wakeups.
    target = pick_wakeup_run_target(
        channel="app", record_session="disc-7",
        app_resolver=lambda: "app-1",
        owner_resolver=lambda: "disc-7",
        is_external=_ext,
    )
    assert target == "app-1"
    assert not _ext(target)


def test_app_wakeup_falls_back_to_fresh_when_no_app_session():
    # Ingen app-session findes → None (kalderen opretter en frisk app-session),
    # ALDRIG en Discord-session.
    target = pick_wakeup_run_target(
        channel="app", record_session="",
        app_resolver=lambda: "",
        owner_resolver=lambda: "disc-3",
        is_external=_ext,
    )
    assert target is None


def test_default_channel_is_app_guarded():
    # Tom/ukendt channel behandles som app → guardet.
    target = pick_wakeup_run_target(
        channel="", record_session="disc-x",
        app_resolver=lambda: "app-9",
        owner_resolver=lambda: "disc-x",
        is_external=_ext,
    )
    assert target == "app-9"


def test_explicit_discord_channel_still_allowed():
    # Eksplicit channel=="discord" må stadig levere til Discord (separat kanal).
    target = pick_wakeup_run_target(
        channel="discord", record_session="disc-5",
        app_resolver=lambda: "app-1",
        owner_resolver=lambda: "disc-9",
        is_external=_ext,
    )
    assert target == "disc-5"


# ── Selv-direktivets rapporterings-regel (5/10-2026) ────────────────────────
#
# Her stod «og rapportér resultatet kort til Bjørn» — ubetinget, paa HVER
# vaekning. Det var aarsagen til at han fik 3-5 beskeder pr. svar: mellem hans
# «Check ci» kl. 11:32 og hans klage kl. 14:35 kom fem beskeder, hvoraf én var
# svar paa spoergsmaalet. Instruktionen skabte adfaerden.

def _fang_direktivet() -> str:
    state = [{"wakeup_id": "w1", "prompt": "tjek ci", "reason": "efterkontrol",
              "status": "fired", "channel": "app", "session_id": "chat-origin"}]
    fired = state
    with patch("core.services.self_wakeup.due_wakeups", return_value=fired), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save"), \
         patch("core.services.outbound_nudges.push_nudge"), \
         patch("core.services.heartbeat_phases.tick_with_phases"), \
         patch(GATEWAY, return_value=_KOEET) as fake:
        dispatch_due_wakeups()
    return str(fake.call_args.kwargs["tekst"])


def test_direktivet_beder_IKKE_ubetinget_om_en_rapport():
    """Den ubetingede ordre er vaek — det er hele rettelsen."""
    d = _fang_direktivet()
    assert "rapportér resultatet kort til Bjørn" not in d


def test_direktivet_goer_rapporten_BETINGET():
    d = _fang_direktivet()
    assert "RAPPORTÉR KUN" in d
    assert "noget NYT" in d
    assert "UDEN at skrive" in d, "der skal staa hvad han goer naar der intet er"


def test_direktivet_beder_om_intern_tavs_afslutning_naar_intet_er_nyt():
    """Nudget routes som telemetri og er ikke en leveret chatbesked."""
    d = _fang_direktivet()
    assert "allerede fået besked" not in d
    assert "[wakeup:no-update]" in d
    assert "notify_user" in d


def test_direktivet_forbyder_at_booke_en_ny_naar_intet_aendrede_sig():
    """Kaedens braendstof. Loftet i self_wakeup er bagstopperen; dette er
    instruktionen der goer at den ikke skal bruges."""
    d = _fang_direktivet()
    assert "book ikke en ny kontrol" in d
    assert "kæde" in d


def test_direktivet_beder_stadig_om_mark_wakeup_consumed():
    """Reglen maa ikke fjerne afslutningen — en vaekning der aldrig forbruges
    bliver staaende i awareness og gentager sig."""
    d = _fang_direktivet()
    assert "mark_wakeup_consumed" in d
    assert "w1" in d


def _fanget_eventbus(monkeypatch) -> list[tuple[str, dict]]:
    from core.eventbus.bus import event_bus

    set_: list[tuple[str, dict]] = []
    monkeypatch.setattr(event_bus, "publish", lambda kind, payload=None, **kw: set_.append((kind, payload or {})))
    return set_


def test_afleveringen_til_indbakken_hedder_queued_ikke_dispatched(monkeypatch):
    """Målt 12/11-2026: en vækning blev `dispatched` 18:15:39 og startede først
    18:22:20 — syv minutter hvor eventet påstod noget der ikke var sket. Hand-off
    til indbakken er `queued`; `dispatched` hører til når runnet starter (se
    `inbox_idle_waker`)."""
    publiceret = _fanget_eventbus(monkeypatch)
    state = [{"wakeup_id": "w1", "prompt": "p", "reason": "test", "status": "fired"}]
    with patch("core.services.self_wakeup.due_wakeups", return_value=state), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save"), \
         patch("core.services.outbound_nudges.push_nudge"), \
         patch("core.services.heartbeat_phases.tick_with_phases"), \
         patch(GATEWAY, return_value=_KOEET):
        dispatch_due_wakeups()
    kinds = [k for k, _ in publiceret if k.startswith("self_wakeup.")]
    assert kinds == ["self_wakeup.queued"]
    assert dict(publiceret)["self_wakeup.queued"]["wakeup_id"] == "w1"


# ── En vækning kvitteret UNDER dispatchen må ikke afleveres bagefter ───────────
#
# Målt 12/11-2026 (wake-bd36c1b2ea): fyrede 18:04:29; dispatcheren tog et snapshot
# og startede et heartbeat-tick, der tog 2 min 37 s; Jarvis kvitterede den 18:05:50
# (inbox_done + consumed); dispatcheren genoptog med det GAMLE snapshot og
# afleverede den til indbakken 18:07:22 — og den vækkede ham 18:11:20 til en
# opgave han allerede havde løst. `marker_dispatch` er race-bevidst og var et
# no-op, men afleveringen sker FØR den.
def _fyret_post(**ekstra) -> dict:
    return {"wakeup_id": "w1", "prompt": "p", "reason": "r", "status": "fired", **ekstra}


@pytest.mark.parametrize("status_imens", ["consumed", "cancelled"])
def test_en_vaekning_kvitteret_efter_snapshottet_men_foer_afleveringen_afleveres_ikke(
        monkeypatch, status_imens):
    """Vinduet er nu snapshot → nudge-push → aflevering (og de andre vækninger i
    løkken). Heartbeat-tick'et ligger ikke længere i det."""
    state = [_fyret_post()]
    publiceret = _fanget_eventbus(monkeypatch)

    def _push(**kw):
        state[0]["status"] = status_imens   # Jarvis kvitterer imens

    with patch("core.services.self_wakeup.due_wakeups", return_value=state), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save"), \
         patch("core.services.outbound_nudges.push_nudge", side_effect=_push), \
         patch("core.services.heartbeat_phases.tick_with_phases"), \
         patch(GATEWAY, return_value=_KOEET) as fake_gw:
        result = dispatch_due_wakeups()

    fake_gw.assert_not_called()
    assert result["dispatched"] == 0
    assert result["dispatched_ids"] == []
    assert result["consumed_during"] == ["w1"]
    assert [k for k, _ in publiceret if k.startswith("self_wakeup.")] == []


def test_en_vaekning_der_stadig_er_fyret_efter_ticket_afleveres_som_for(monkeypatch):
    state = [_fyret_post()]
    with patch("core.services.self_wakeup.due_wakeups", return_value=state), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save"), \
         patch("core.services.outbound_nudges.push_nudge"), \
         patch("core.services.heartbeat_phases.tick_with_phases"), \
         patch(GATEWAY, return_value=_KOEET) as fake_gw:
        result = dispatch_due_wakeups()

    fake_gw.assert_called_once()
    assert (result["dispatched"], result["consumed_during"]) == (1, [])


def test_kan_lageret_ikke_laeses_afleveres_vaekningen_hellere_end_at_forsvinde(monkeypatch):
    """Fail-open som resten af dispatcheren: en vækning må ikke forsvinde på en læsefejl."""
    state = [_fyret_post()]
    kald = {"n": 0}

    def _load_foerste_gang_fejler():
        kald["n"] += 1
        if kald["n"] == 1:          # det er den re-læsning FØR afleveringen
            raise RuntimeError("væk")
        return state

    with patch("core.services.self_wakeup.due_wakeups", return_value=state), \
         patch("core.services.self_wakeup._save"), \
         patch("core.services.outbound_nudges.push_nudge"), \
         patch("core.services.heartbeat_phases.tick_with_phases"), \
         patch("core.services.self_wakeup._load", side_effect=_load_foerste_gang_fejler), \
         patch(GATEWAY, return_value=_KOEET) as fake_gw:
        result = dispatch_due_wakeups()

    fake_gw.assert_called_once()
    assert result["dispatched"] == 1


# ── Aflever FØRST, heartbeat-tick BAGEFTER (Bjørn 12/11-2026) ─────────────────
#
# Tick'et (`tick_with_phases`) lå INDE i løkken FØR afleveringen, under
# `_dispatch_lock`. Målt: 2 min 37 s for wake-bd36c1b2ea, og 57/59/173 s fyret →
# afleveret for de tre vækninger vi har tal for. Tick'et skal reagere på en
# vækning, ikke bestemme hvornår den starter.
def _ventende_tick():
    from core.services import wakeup_dispatcher as wd

    traad = wd._tick_traad
    if traad is not None:
        traad.join(timeout=5.0)


def test_afleveringen_sker_foer_heartbeat_tick(monkeypatch):
    raekkefoelge: list[str] = []
    state = [_fyret_post()]
    with patch("core.services.self_wakeup.due_wakeups", return_value=state), \
         patch("core.services.self_wakeup._load", return_value=state), \
         patch("core.services.self_wakeup._save"), \
         patch("core.services.outbound_nudges.push_nudge"), \
         patch("core.services.heartbeat_phases.tick_with_phases",
               side_effect=lambda **kw: raekkefoelge.append("tick")), \
         patch(GATEWAY, side_effect=lambda **kw: raekkefoelge.append("gateway") or _KOEET):
        dispatch_due_wakeups()
        _ventende_tick()

    assert raekkefoelge == ["gateway", "tick"]


def test_et_langsomt_tick_holder_hverken_dispatchen_eller_laasen_fast():
    import threading
    import time

    from core.services import wakeup_dispatcher as wd

    frigiv = threading.Event()
    state = [_fyret_post()]
    try:
        with patch("core.services.self_wakeup.due_wakeups", return_value=state), \
             patch("core.services.self_wakeup._load", return_value=state), \
             patch("core.services.self_wakeup._save"), \
             patch("core.services.outbound_nudges.push_nudge"), \
             patch("core.services.heartbeat_phases.tick_with_phases",
                   side_effect=lambda **kw: frigiv.wait(30)), \
             patch(GATEWAY, return_value=_KOEET):
            t = time.monotonic()
            result = dispatch_due_wakeups()
            brugt = time.monotonic() - t

            assert result["dispatched"] == 1
            assert brugt < 2.0, f"dispatchen ventede paa tick'et ({brugt:.1f}s)"
            assert not wd._dispatch_lock.locked()
    finally:
        frigiv.set()
        _ventende_tick()


def test_der_koerer_hoejst_eet_heartbeat_tick_ad_gangen():
    import threading

    frigiv = threading.Event()
    tick = patch("core.services.heartbeat_phases.tick_with_phases",
                 side_effect=lambda **kw: frigiv.wait(30))
    state1 = [_fyret_post(wakeup_id="w1")]
    state2 = [_fyret_post(wakeup_id="w2")]
    try:
        with tick as fake_tick, \
             patch("core.services.self_wakeup._save"), \
             patch("core.services.outbound_nudges.push_nudge"), \
             patch(GATEWAY, return_value=_KOEET):
            with patch("core.services.self_wakeup.due_wakeups", return_value=state1), \
                 patch("core.services.self_wakeup._load", return_value=state1):
                dispatch_due_wakeups()
            with patch("core.services.self_wakeup.due_wakeups", return_value=state2), \
                 patch("core.services.self_wakeup._load", return_value=state2):
                dispatch_due_wakeups()
            assert fake_tick.call_count == 1
    finally:
        frigiv.set()
        _ventende_tick()
