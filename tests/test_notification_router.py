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


# ── Routeren foder feeden (opgave "routeren-foeder", 2026-09-22) ────────────
# `route_proactive_notification()` kalder sin egen docstring "ÉT indgangspunkt
# — som ALLE proaktive kilder kalder". De seks router-ejede slags (reach_out,
# central_flag, membrane_breach, infra_security, keymaker_key_earned,
# moltbook_mention) gik hidtil KUN gennem push — ingen af dem endte i
# notifikations-feeden. Fra nu af foder routeren selv feeden for enhver
# slags den ikke allerede faar leveret en raekke af `notifikations_emittere`
# (som lægger sin række FØR den kalder routeren, og derfor sender feed=False).
def test_aegte_reach_out_giver_push_OG_en_feed_raekke(isolated_runtime, monkeypatch) -> None:
    """Den AEGTE route_proactive_notification() — kun transportlaget mockes."""
    from core.services import notifikationer as lager

    delivered = []
    monkeypatch.setattr(nr, "_deliver_to_channel", lambda *a, **k: delivered.append(a) or True)
    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)

    res = nr.route_proactive_notification(
        "bjorn", "reach_out", {"preview": "hej", "body": "Jeg har fundet noget"},
        importance="normal")

    assert res["delivered"] is True
    assert delivered, "pushet skulle stadig forsøges"
    raekker = lager.aabne("bjorn", er_owner=True)
    assert len(raekker) == 1, f"forventede én feed-række, fik {len(raekker)}"
    assert raekker[0]["slags"] == "reach_out"
    assert raekker[0]["tekst"] == "Jeg har fundet noget"


def test_feedens_egne_slags_giver_stadig_kun_EEN_raekke(isolated_runtime, monkeypatch) -> None:
    """`notifikations_emittere._foed()` lægger rækken selv OG kalder routeren
    for pushet — routeren må ikke lægge en ANDEN oveni, nu hvor den selv føder
    ukendte slags. Ellers ville approval/run_failed/run_done/release/incident/
    quota alle dubleres af denne opgave."""
    from core.services import notifikationer as lager
    from core.services import notifikations_emittere as e

    monkeypatch.setattr(nr, "_deliver_to_channel", lambda *a, **k: True)
    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)

    e.paa_godkendelse("a-1", user_id="bjorn", session_id="s-1", vaerktoej="bash_session")

    raekker = lager.aabne("bjorn", er_owner=True)
    assert len(raekker) == 1, f"forventede én række, fik {len(raekker)}"


def test_fejlende_feed_skrivning_stopper_ikke_pushet(isolated_runtime, monkeypatch) -> None:
    """Routeren er den varme sti; feed-rækken er tilbehøret — en fejl i
    feed-fødslen må aldrig forhindre et push i at blive leveret."""
    delivered = []
    monkeypatch.setattr(nr, "_deliver_to_channel", lambda *a, **k: delivered.append(a) or True)
    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)

    def sprang(*a, **k):
        raise RuntimeError("db er væk")
    monkeypatch.setattr(nr, "_foed_feed_raekke", sprang)

    # "reach_out": STANDARD siger "auto" (leverer altid) — "central_flag" ville
    # med STANDARDs egen "ingen" allerede stoppe FØR feed-skrivningen overhovedet
    # naaes, og saa ville testen intet bevise.
    res = nr.route_proactive_notification("bjorn", "reach_out", {"title": "x", "body": "y"})

    assert res["delivered"] is True
    assert delivered, "pushet skulle stadig gennemføres selvom feed-skrivningen fejlede"


def test_genudsendt_fra_stille_koe_dobler_ikke_feed_raekken(isolated_runtime, monkeypatch) -> None:
    """En notifikation der lægges i quiet-hours-køen er allerede født i
    feeden ved kø-tidspunktet — den udsatte genudsendelse (_skip_quiet=True,
    fra fire_due_delayed) må ikke lægge en ny.

    23/9-2026: kaldet sker nu PÅ rækkens eget tidspunkt. Før ramte "12:00"
    også en række der ventede til 23:59; med deliver_after-værnet skal testen
    ramme det tidspunkt hvor genudsendelsen faktisk sker — ellers beviser den
    intet (den passede før fordi rækken aldrig fyrede)."""
    from core.services import notifikationer as lager

    monkeypatch.setattr(nr, "_deliver_to_channel", lambda *a, **k: True)
    nr.set_preferences("bjorn", **{"quiet_start": "00:00", "quiet_end": "12:00"})

    # Uret maa ikke afgoere om testen bestaar. `is_quiet_hours()` laeser
    # datetime.now() naar den ikke faar et tidspunkt, saa "00:00-12:00" betoed
    # at testen KUN kunne bestaa foer middag. Den blev skrevet kl. 10:56 og har
    # vaeret roed siden kl. 12 samme dag (maalt 23/9-2026 kl. 16:26).
    # Anden halvdel patchede allerede det samme kald; nu goer foerste ogsaa.
    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: True)
    res = nr.route_proactive_notification("bjorn", "reach_out", {"body": "hej"}, importance="normal")
    assert res["channel"] == "queued"
    assert len(lager.aabne("bjorn", er_owner=True)) == 1

    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)
    udfald = nr.fire_due_delayed("12:00")
    assert udfald["leveret"] == 1, "genudsendelsen skulle være sket — ellers beviser testen intet"
    assert len(lager.aabne("bjorn", er_owner=True)) == 1


# ── Quiet-hours-køen TØMMES (23/9-2026) ──────────────────────────────────────
# Funktionen havde nul kaldere uden for tests; alt der ramte quiet hours blev
# spist i stilhed (1.542 rækker, 0 leveret, ældste 2. juli). Nu kaldes den fra
# heartbeat-poll'en. En kø der har stået i månedsvis må ikke tømmes naivt, så
# tømningen har tre værn — hvert sit test herunder.
def _indsaet_koe(uid: str, ntype: str, body: str, *, timer_gammel: float = 0.0,
                 deliver_after: str = "07:00") -> None:
    """Læg en række direkte i køen med en valgt alder."""
    import json
    from datetime import datetime, timedelta, timezone
    from core.runtime.db import connect

    created = (datetime.now(timezone.utc) - timedelta(hours=timer_gammel)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    with connect() as conn:
        conn.execute(
            "INSERT INTO delayed_notifications "
            "(user_id, notif_type, payload_json, importance, deliver_after, created_at, delivered) "
            "VALUES (?,?,?,?,?,?,0)",
            (uid, ntype, json.dumps({"body": body}), "normal", deliver_after, created),
        )


def _kasseret() -> int:
    """Antal rækker der er markeret forældet (delivered = 2)."""
    from core.runtime.db import connect
    with connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM delayed_notifications WHERE delivered = 2").fetchone()[0]


def test_foraeldet_raekke_kasseres_frem_for_at_fyre(isolated_runtime, monkeypatch) -> None:
    """En række over sin levetid er ikke 'forsinket', den er forældet — en
    'brute_force BLOKERET af pfSense' fra juli er ikke en nyhed i september."""
    monkeypatch.setattr(nr, "_deliver_to_channel", lambda *a, **k: True)
    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)

    _indsaet_koe("bjorn", "infra_security", "gammel", timer_gammel=48)
    _indsaet_koe("bjorn", "infra_security", "frisk", timer_gammel=1)

    udfald = nr.fire_due_delayed("12:00")

    assert udfald["foraeldet"] == 1
    assert udfald["leveret"] == 1
    assert _kasseret() == 1


def test_approval_har_kortere_levetid_end_andre(isolated_runtime, monkeypatch) -> None:
    """Et godkendelses-kort der ikke blev set mens handlingen skete, kan ikke
    besvares bagefter — derfor 2t, ikke de 24t andre slags får."""
    monkeypatch.setattr(nr, "_deliver_to_channel", lambda *a, **k: True)
    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)

    _indsaet_koe("bjorn", "approval", "gammel godkendelse", timer_gammel=3)
    _indsaet_koe("bjorn", "infra_security", "samme alder", timer_gammel=3)

    udfald = nr.fire_due_delayed("12:00")

    assert udfald["foraeldet"] == 1  # approval: 3t > 2t
    assert udfald["leveret"] == 1    # infra_security: 3t < 24t


def test_koeen_toemmes_i_batch_ikke_som_byge(isolated_runtime, monkeypatch) -> None:
    """En ophobning må ikke lande på én gang — højst _MAX_PR_RUN pr. kald,
    ældste først, så resten kommer i de næste poll."""
    monkeypatch.setattr(nr, "_deliver_to_channel", lambda *a, **k: True)
    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)

    for i in range(8):
        _indsaet_koe("bjorn", "reach_out", f"nr{i}", timer_gammel=1)

    første = nr.fire_due_delayed("12:00")
    assert første["leveret"] == nr._MAX_PR_RUN
    assert første["tilbage"] == 8 - nr._MAX_PR_RUN

    anden = nr.fire_due_delayed("12:00")
    assert anden["leveret"] == 3


def test_raekke_fyrer_ikke_foer_sit_eget_tidspunkt(isolated_runtime, monkeypatch) -> None:
    """En række venter til sin EGEN deliver_after, ikke til quiet hours er
    ovre — de to kan falde sammen, men er ikke det samme løfte."""
    monkeypatch.setattr(nr, "_deliver_to_channel", lambda *a, **k: True)
    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)

    _indsaet_koe("bjorn", "reach_out", "venter", timer_gammel=1, deliver_after="07:00")

    for tid in ("06:00", "06:59"):
        assert nr.fire_due_delayed(tid)["leveret"] == 0, f"fyrede for tidligt ved {tid}"

    assert nr.fire_due_delayed("07:00")["leveret"] == 1


def test_titel_og_tekst_oversaetter_alle_payload_former(isolated_runtime, monkeypatch) -> None:
    """Payloads er ikke ens (title+body, title+preview+body, title+message,
    kun text) — én oversættelse med fald-tilbage, brugt for alle seks."""
    assert nr._feed_titel_og_tekst("moltbook_mention", {"text": "Nogen nævnte dig"}) == (
        "Moltbook", "Nogen nævnte dig")
    assert nr._feed_titel_og_tekst("central_flag", {"title": "Flag", "message": "detaljer"}) == (
        "Flag", "detaljer")
    assert nr._feed_titel_og_tekst("reach_out", {"title": None, "body": "hej"})[1] == "hej"
    titel, _ = nr._feed_titel_og_tekst("reach_out", {"body": "hej"})
    assert titel  # aldrig tom


def test_lav_importance_flooder_ikke_feeden(isolated_runtime, monkeypatch) -> None:
    """Defensiv gulv for fremtidige kilder: 'low' skriver ikke i feeden (ingen
    af de seks nuværende kilder bruger den i dag — målt i koden, se rapport)."""
    from core.services import notifikationer as lager

    monkeypatch.setattr(nr, "_deliver_to_channel", lambda *a, **k: True)
    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)

    nr.route_proactive_notification("bjorn", "central_flag", {"title": "x", "message": "y"},
                                    importance="low")
    assert lager.aabne("bjorn", er_owner=True) == []
