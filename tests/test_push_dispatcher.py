import core.services.push_dispatcher as pd
import core.services.device_tokens as dt
import core.services.run_event_log as rel


def _setup(monkeypatch):
    sent = []
    monkeypatch.setattr(pd, "_fcm_send", lambda token, data: sent.append((token, data)) or (True, "ok"))
    dt._ensure_table()
    from core.runtime.db import connect
    with connect() as c:
        c.execute("DELETE FROM device_tokens")
    return sent


def test_suppressed_when_consumed(monkeypatch):
    sent = _setup(monkeypatch)
    dt.register("bjorn", "tok-A")
    rel.create("run-1", "sess-1")
    rel.mark_consumed("run-1")  # nogen saa det live
    monkeypatch.setattr(pd, "_owner_of_run", lambda run_id: "bjorn")
    pd._dispatch_run_done("run-1")
    assert sent == []  # undertrykt


def test_pushes_data_only_when_answer_exists(monkeypatch):
    sent = _setup(monkeypatch)
    dt.register("bjorn", "tok-A")
    rel.create("run-2", "sess-2")  # ingen subscriber, ikke consumed
    monkeypatch.setattr(pd, "_owner_of_run", lambda run_id: "bjorn")
    monkeypatch.setattr(pd, "_last_assistant_preview", lambda sid: "Hej Bjørn, her er svaret")
    pd._dispatch_run_done("run-2")
    assert len(sent) == 1
    token, data = sent[0]
    assert token == "tok-A"
    assert data["kind"] == "answer_ready"
    assert data["run_id"] == "run-2"
    assert data["session_id"] == "sess-2"
    # preview MEDsendes som fallback-tekst, men INGEN title → forbliver data-only (ingen
    # notification-blok i fcm_gateway) → notifee tap-nav + Direct Reply bevaret.
    assert data["preview"] == "Hej Bjørn, her er svaret"
    assert "title" not in data


def test_skips_push_when_no_answer_text(monkeypatch):
    # Rent autonomt run uden assistant-svar → INGEN tom spam-notifikation.
    sent = _setup(monkeypatch)
    dt.register("bjorn", "tok-A")
    rel.create("run-empty", "sess-empty")
    monkeypatch.setattr(pd, "_owner_of_run", lambda run_id: "bjorn")
    monkeypatch.setattr(pd, "_last_assistant_preview", lambda sid: "")
    pd._dispatch_run_done("run-empty")
    assert sent == []  # sprunget over


def test_last_assistant_preview_truncates_and_picks_latest(monkeypatch):
    from core.services import chat_sessions as cs
    monkeypatch.setattr(cs, "recent_chat_session_messages", lambda sid, limit=6: [
        {"role": "user", "content": "spørgsmål"},
        {"role": "assistant", "content": "gammelt svar"},
        {"role": "assistant", "content": "x" * 300},  # nyeste assistant
    ])
    out = pd._last_assistant_preview("sess-x", width=160)
    assert out.endswith("…") and len(out) == 161 and out.startswith("x")


def test_invalid_token_is_deleted(monkeypatch):
    _setup(monkeypatch)
    monkeypatch.setattr(pd, "_fcm_send", lambda token, data: (False, "invalid"))
    monkeypatch.setattr(pd, "_last_assistant_preview", lambda sid: "et svar")
    # Tving blast-stien (device-awareness fra) så vi tester _push_to_user's invalid-oprydning.
    from core.runtime import settings as st
    monkeypatch.setattr(st, "load_settings",
                        lambda: type("S", (), {"device_awareness_enabled": False})())
    dt.register("bjorn", "tok-dead")
    rel.create("run-3", "sess-3")
    monkeypatch.setattr(pd, "_owner_of_run", lambda run_id: "bjorn")
    pd._dispatch_run_done("run-3")
    assert dt.list_for_user("bjorn") == []  # selv-oprydning


def test_approval_requested_push_carries_navigation_identity(monkeypatch):
    routed = []
    monkeypatch.setattr(
        pd,
        "_route_or_blast",
        lambda uid, data, kind: routed.append((uid, data, kind)) or True,
    )

    assert pd.on_approval_requested(
        "user-a",
        {"request_id": "request-1", "capability_name": "Skriv MEMORY.md"},
    ) is True
    assert routed == [
        (
            "user-a",
            {
                "kind": "approval_requested",
                "request_id": "request-1",
                "title": "Godkendelse kræves",
                "preview": "Skriv MEMORY.md",
                # Fladen turen kom fra; tom her fordi konvolutten ikke bar en.
                "surface": "",
            },
            "approval_requested",
        )
    ]


def test_droppet_push_naevner_at_runnet_er_vaek(monkeypatch, caplog):
    """Et tab der ikke staar i journalen, er et tab ingen kan finde (26/10-2026).

    `session_for_run` laeser en in-memory registry. Er runnet pruned eller
    runtime genstartet, giver den None — og notifikationen faldt foer i et
    TAVST return. Michelles to notifikationer 25/10 forsvandt praecis saadan.
    """
    _setup(monkeypatch)
    dt.register("bjorn", "tok-A")
    monkeypatch.setattr(pd, "_owner_of_run", lambda run_id: None)
    with caplog.at_level("WARNING", logger="core.services.push_dispatcher"):
        pd._dispatch_run_done("run-findes-ikke")
    beskeder = [r.getMessage() for r in caplog.records]
    assert any("DROPPET" in m and "findes ikke i run_event_log" in m for m in beskeder), beskeder


def test_droppet_push_naevner_session_uden_ejer(monkeypatch, caplog):
    """Den anden aarsag: runnet FINDES, men sessionen kan ikke knyttes til en ejer.

    De to skal kunne skelnes i loggen — ellers peger linjen paa det forkerte sted.
    """
    _setup(monkeypatch)
    dt.register("bjorn", "tok-A")
    rel.create("run-uden-ejer", "sess-uden-ejer")
    monkeypatch.setattr(pd, "_owner_of_run", lambda run_id: None)
    with caplog.at_level("WARNING", logger="core.services.push_dispatcher"):
        pd._dispatch_run_done("run-uden-ejer")
    beskeder = [r.getMessage() for r in caplog.records]
    assert any("DROPPET" in m and "har ingen ejer" in m for m in beskeder), beskeder
    # ... og den maa IKKE paastaa at runnet var vaek.
    assert not any("findes ikke i run_event_log" in m for m in beskeder), beskeder


def _web_setup(monkeypatch, subs, sender):
    """Indsaml push-events uden at roere DB eller netvaerk."""
    from core.services import web_push_subscriptions as wps
    from core.services import web_push_gateway as gw
    indsamlet: list[tuple[str, dict]] = []
    slettede: list[str] = []
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus.publish",
        lambda kind, payload: indsamlet.append((kind, payload)),
    )
    monkeypatch.setattr(wps, "list_for_user", lambda uid: list(subs))
    monkeypatch.setattr(wps, "delete", lambda endpoint: slettede.append(endpoint))
    monkeypatch.setattr(gw, "send", sender)
    return indsamlet, slettede


def test_web_push_success_is_recorded(monkeypatch):
    """En vellykket web-push efterlod FOER intet spor — nu skrives udfaldet.

    Uden dette kunne hverken jeg eller Bjoern svare paa «fik hun den?»: kun fejl
    blev logget, og en leverance og en manglende leverance saa ens ud.
    """
    subs = [{"endpoint": "https://web.push.apple.com/XYZ-hemmelig", "p256dh": "k", "auth": "a"}]
    events, _ = _web_setup(monkeypatch, subs, lambda sub, data: (True, "ok"))

    assert pd._push_to_web("u-1", {"kind": "answer_ready", "run_id": "run-9"}) is True

    assert len(events) == 1
    kind, payload = events[0]
    assert kind == "push.web_sent"
    assert payload["code"] == "ok"
    assert payload["host"] == "web.push.apple.com"
    assert payload["kind"] == "answer_ready"
    assert payload["run_id"] == "run-9"
    assert payload["user_id"] == "u-1"


def test_web_push_endpoint_url_never_enters_the_payload(monkeypatch):
    """Endpoint-URL'en ER adgangen til enheden og maa ikke ligge i events."""
    subs = [{"endpoint": "https://fcm.googleapis.com/fcm/send/HEMMELIGT-TOKEN", "p256dh": "k", "auth": "a"}]
    events, _ = _web_setup(monkeypatch, subs, lambda sub, data: (True, "ok"))

    pd._push_to_web("u-1", {"kind": "initiative"})

    tekst = repr(events)
    assert "HEMMELIGT-TOKEN" not in tekst
    assert "https://" not in tekst


def test_web_push_failure_records_reason_and_drops_dead_subscription(monkeypatch):
    subs = [{"endpoint": "https://web.push.apple.com/DOED", "p256dh": "k", "auth": "a"}]
    events, slettede = _web_setup(monkeypatch, subs, lambda sub, data: (False, "invalid"))

    assert pd._push_to_web("u-1", {"kind": "answer_ready"}) is False

    kind, payload = events[0]
    assert kind == "push.web_failed"
    assert payload["code"] == "invalid"
    assert slettede == ["https://web.push.apple.com/DOED"]


def test_web_push_without_subscription_is_recorded(monkeypatch):
    """Nul abonnementer var HELT tavst — samme spor som en leveret push."""
    events, _ = _web_setup(monkeypatch, [], lambda sub, data: (True, "ok"))

    assert pd._push_to_web("u-uden-abonnement", {"kind": "answer_ready"}) is False

    kind, payload = events[0]
    assert kind == "push.web_skipped"
    assert payload["reason"] == "no_subscription"
    assert payload["user_id"] == "u-uden-abonnement"


def test_push_familien_er_registreret_i_eventbussen():
    """Uden familien i ALLOWED kaster publish — og kaldestedets except sluger det.

    MAALT 6/11-2026: praecis det skete. `_push_to_web` fik events-skrivning, men
    `push` stod ikke i ALLOWED_EVENT_FAMILIES, saa hvert publish kastede
    «Unsupported event family». Koden saa rigtig ud, 12 tests var groenne, og
    mutationstesten faldt korrekt — men NUL raekker naaede events-tabellen.
    Denne test er den vagt der manglede: den maaler at eventet KAN oprettes.
    """
    from core.eventbus.events import ALLOWED_EVENT_FAMILIES, Event

    assert "push" in ALLOWED_EVENT_FAMILIES
    for kind in ("push.web_sent", "push.web_failed", "push.web_skipped"):
        Event.create(kind, {"user_id": "u-1"})  # maa ikke kaste
