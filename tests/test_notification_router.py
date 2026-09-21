"""Tests for notification_router (Phase 2): preferences, quiet hours, routing."""
import pytest

import core.runtime.db as db
import core.runtime.db_core as db_core
import core.services.notification_router as nr


def _fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    db.init_db()


# ── Pure logic ──────────────────────────────────────────────────────────────
def test_resolve_channel_priority():
    prefs = {"global": "desktop", "team_invite": "mobile", "briefing": None}
    assert nr.resolve_channel(prefs, "team_invite") == "mobile"   # type override vinder
    assert nr.resolve_channel(prefs, "briefing") == "desktop"     # falder til global
    assert nr.resolve_channel({"global": "auto"}, "reminder") == "auto"


def test_is_quiet_hours_normal_and_wrap():
    p = {"quiet_start": "23:00", "quiet_end": "07:00"}  # wrapper over midnat
    assert nr.is_quiet_hours(p, "23:30") is True
    assert nr.is_quiet_hours(p, "03:00") is True
    assert nr.is_quiet_hours(p, "12:00") is False
    p2 = {"quiet_start": "09:00", "quiet_end": "17:00"}  # samme dag
    assert nr.is_quiet_hours(p2, "12:00") is True
    assert nr.is_quiet_hours(p2, "20:00") is False
    assert nr.is_quiet_hours({"quiet_start": "08:00", "quiet_end": "08:00"}, "08:00") is False


# ── CRUD ──────────────────────────────────────────────────────────────────────
def test_preferences_roundtrip(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    assert nr.get_preferences("u1")["global"] == "auto"  # default
    nr.set_preferences("u1", **{"global": "desktop", "team_invite": "mobile", "quiet_start": "22:00"})
    p = nr.get_preferences("u1")
    assert p["global"] == "desktop"
    assert p["team_invite"] == "mobile"
    assert p["quiet_start"] == "22:00"


def test_set_preferences_rejects_invalid_channel(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        nr.set_preferences("u1", **{"global": "carrier-pigeon"})


# ── Routing ─────────────────────────────────────────────────────────────────
def test_route_queues_during_quiet_hours(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    nr.set_preferences("u1", **{"quiet_start": "00:00", "quiet_end": "23:59"})  # ~altid stille
    delivered = []
    monkeypatch.setattr(nr, "_deliver_to_channel", lambda *a, **k: delivered.append(a) or True)
    # "approval": tester quiet-hours-mekanikken, ikke push-per-slags-valget
    # (task 5) — "briefing" er nu tavs som standard og ville stoppe FØR quiet
    # hours overhovedet bliver tjekket.
    res = nr.route_proactive_notification("u1", "approval", {"preview": "morgen"})
    assert res["channel"] == "queued"
    assert delivered == []  # IKKE leveret — sat i kø


def test_route_critical_bypasses_quiet_hours(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    nr.set_preferences("u1", **{"quiet_start": "00:00", "quiet_end": "23:59"})
    monkeypatch.setattr(nr, "_deliver_to_channel", lambda *a, **k: True)
    # "run_failed": tester critical-bypass af quiet hours, ikke push-per-slags
    # (task 5) — "reminder" er nu tavs som standard og ville stoppe FØR
    # importance overhovedet bliver læst.
    res = nr.route_proactive_notification("u1", "run_failed", {"preview": "BRAND"}, importance="critical")
    assert res["delivered"] is True
    assert res["channel"] != "queued"


def test_route_delivers_to_resolved_channel(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    # quiet_start == quiet_end → ingen quiet hours (deterministisk, ikke ur-afhængig)
    nr.set_preferences("u1", **{"global": "desktop", "quiet_start": "00:00", "quiet_end": "00:00"})
    calls = []
    monkeypatch.setattr(nr, "_deliver_to_channel",
                        lambda uid, ch, p, t: calls.append((uid, ch)) or True)
    # "question": tester global-fallback i resolve_channel, ikke push-per-slags
    # (task 5) — "briefing" er nu tavs som standard.
    res = nr.route_proactive_notification("u1", "question", {"preview": "x"})
    assert res["delivered"] is True
    assert res["channel"] == "desktop"
    assert calls and calls[0][1] == "desktop"


# ── Device-aware levering (inlined fra proactive_router, Phase 5) ───────────────
import core.services.device_presence as dp  # noqa: E402


def _setup_delivery(monkeypatch):
    sent = {"fcm": [], "desk": []}
    monkeypatch.setattr(nr, "_arm_timer", lambda notif_id: None)
    monkeypatch.setattr(nr, "_send_fcm", lambda uid, key, data: sent["fcm"].append((key, data)))
    monkeypatch.setattr(nr, "_send_desktop", lambda uid, item: sent["desk"].append(item))
    monkeypatch.setattr(nr, "_fallback_blast", lambda uid, data: sent.setdefault("blast", []).append(data))
    monkeypatch.setattr(nr, "_new_id", lambda: "nid-1")
    nr.reset_delivery()
    return sent


def test_route_device_aware_sends_to_best_desktop(monkeypatch):
    monkeypatch.setattr(dp, "_now", lambda: 1000.0)
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=True)
    dp.record_ping("bjorn", "mob", "mobile", foreground=False, awake=True, network="home")
    sent = _setup_delivery(monkeypatch)
    nr.route_device_aware("bjorn", {"kind": "answer_ready", "session_id": "s1"}, "answer_ready")
    assert len(sent["desk"]) == 1 and sent["desk"][0]["notif_id"] == "nid-1"
    assert sent["fcm"] == []
    assert "nid-1" in nr._PENDING


def test_route_device_aware_empty_presence_falls_back(monkeypatch):
    monkeypatch.setattr(dp, "_now", lambda: 1000.0)
    dp.reset()
    import core.services.device_tokens as dt
    monkeypatch.setattr(dt, "list_for_user", lambda uid: [])  # ingen registrerede tokens
    sent = _setup_delivery(monkeypatch)
    nr.route_device_aware("bjorn", {"kind": "reminder", "preview": "hej"}, "reminder")
    assert sent.get("blast") == [{"kind": "reminder", "preview": "hej"}]
    assert nr._PENDING == {}


def test_escalate_then_ack_stops(monkeypatch):
    monkeypatch.setattr(dp, "_now", lambda: 1000.0)
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=True)
    dp.record_ping("bjorn", "mob", "mobile", foreground=False, awake=True, network="home")
    sent = _setup_delivery(monkeypatch)
    nr.route_device_aware("bjorn", {"kind": "answer_ready", "session_id": "s1"}, "answer_ready")
    assert len(sent["desk"]) == 1 and sent["fcm"] == []
    nr._escalate("nid-1")
    assert len(sent["fcm"]) == 1 and sent["fcm"][0][0] == "mob"
    nr.ack("nid-1")
    assert "nid-1" not in nr._PENDING
    nr._escalate("nid-1")  # no-op efter ack
    assert len(sent["fcm"]) == 1


# ── Proaktiv indhold-levering (deliver_message) — Bjørn 2026-06-21 ──────────────
def test_deliver_message_auto_picks_app_when_online(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)  # deterministisk, ikke ur-afhængig
    monkeypatch.setattr(nr, "_app_device_live", lambda uid: True)
    posted = {}
    monkeypatch.setattr(nr, "_deliver_content", lambda uid, ch, text: posted.update(ch=ch, text=text) or {"sent": True, "channel": ch})
    r = nr.deliver_message("bjorn", "Godmorgen Bjørn — her er din brief")
    assert posted["ch"] == "webchat"  # online på app → vises i samtalen
    assert r["sent"] is True


def test_deliver_message_auto_falls_back_to_discord(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)  # deterministisk, ikke ur-afhængig
    monkeypatch.setattr(nr, "_app_device_live", lambda uid: False)   # ikke på app
    monkeypatch.setattr(nr, "_discord_connected", lambda: True)
    posted = {}
    monkeypatch.setattr(nr, "_deliver_content", lambda uid, ch, text: posted.update(ch=ch) or {"sent": True, "channel": ch})
    nr.deliver_message("bjorn", "brief")
    assert posted["ch"] == "discord"  # fallback discord


def test_deliver_message_explicit_pref_overrides_auto(tmp_path, monkeypatch):
    _fresh_db(tmp_path, monkeypatch)
    nr.set_preferences("bjorn", **{"reach_out": "discord"})  # eksplicit valg
    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)  # deterministisk, ikke ur-afhængig
    monkeypatch.setattr(nr, "_app_device_live", lambda uid: True)  # selvom online på app
    posted = {}
    monkeypatch.setattr(nr, "_deliver_content", lambda uid, ch, text: posted.update(ch=ch) or {"sent": True, "channel": ch})
    nr.deliver_message("bjorn", "brief")
    assert posted["ch"] == "discord"  # præference vinder over auto


# ── Fladen turen kom fra styrer hvem der får kortet (Bjørn 20/9-2026) ──────────
def test_route_device_aware_follows_surface_to_desk(monkeypatch):
    """Telefonen vinder ranglisten — men turen blev skrevet fra desk.

    Præcis Bjørns symptom: han arbejder i desk, telefonen ligger i lommen med
    appen i forgrunden (+1000 i foreground-bonus), og godkendelses-kortet
    landede dér. Med fladen med går det til desk.
    """
    monkeypatch.setattr(dp, "_now", lambda: 1000.0)
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=False, awake=True, network="home")
    dp.record_ping("bjorn", "mob", "mobile", foreground=True, awake=True, network="home",
                   interaction=True)
    sent = _setup_delivery(monkeypatch)
    # Uden flade: telefonen vinder (det gamle svar).
    nr.route_device_aware("bjorn", {"kind": "approval_requested"}, "approval_requested")
    assert len(sent["fcm"]) == 1 and sent["desk"] == []
    nr.reset_delivery()
    sent["fcm"].clear()
    # Med flade: desk får kortet, telefonen bliver til eskalering.
    nr.route_device_aware("bjorn", {"kind": "approval_requested", "surface": "desk"},
                          "approval_requested")
    assert len(sent["desk"]) == 1 and sent["fcm"] == []
    nr._escalate("nid-1")
    assert len(sent["fcm"]) == 1  # signalet er ikke tabt — telefonen er næste trin


def test_route_device_aware_surface_without_reachable_device_falls_back(monkeypatch):
    """Skrev han fra desk, men desk er slukket: kortet skal STADIG frem."""
    monkeypatch.setattr(dp, "_now", lambda: 1000.0)
    dp.reset()
    dp.record_ping("bjorn", "mob", "mobile", foreground=True, awake=True, network="home",
                   interaction=True)
    sent = _setup_delivery(monkeypatch)
    nr.route_device_aware("bjorn", {"kind": "approval_requested", "surface": "desk"},
                          "approval_requested")
    assert len(sent["fcm"]) == 1 and sent["desk"] == []


def test_route_device_aware_follows_surface_to_mobile(monkeypatch):
    """Skrev han fra telefonen, skal svaret ikke dukke op på desk."""
    monkeypatch.setattr(dp, "_now", lambda: 1000.0)
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home",
                   interaction=True)
    dp.record_ping("bjorn", "mob", "mobile", foreground=False, awake=True, network="home")
    sent = _setup_delivery(monkeypatch)
    nr.route_device_aware("bjorn", {"kind": "answer_ready", "surface": "mobil"}, "answer_ready")
    assert len(sent["fcm"]) == 1 and sent["desk"] == []


def test_ordn_efter_flade_er_en_no_op_uden_flade():
    """Ukendt eller tom flade må aldrig røre ranglisten."""
    ranked = [dp.RankedDevice("mob", "mobile", 1100.0, "fcm"),
              dp.RankedDevice("desk", "desktop", 90.0, "desktop_queue")]
    for flade in ("", "   ", "web", "ukendt"):
        assert nr._ordn_efter_flade(ranked, flade) == ranked


def test_app_device_live_ser_et_frisk_ping(monkeypatch):
    """Navnet stod ubundet, og NameError'en blev slugt → svaret var ALTID nej."""
    monkeypatch.setattr(dp, "_now", lambda: 1000.0)
    dp.reset()
    import core.services.device_tokens as dt
    monkeypatch.setattr(dt, "list_for_user", lambda uid: [])
    assert nr._app_device_live("bjorn") is False        # ingen enheder
    dp.record_ping("bjorn", "mob", "mobile", foreground=True, awake=True,
                   network="home", interaction=True)
    assert nr._app_device_live("bjorn") is True         # frisk ping i forgrunden
