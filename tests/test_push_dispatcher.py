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
