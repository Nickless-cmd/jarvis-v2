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


def test_pushes_when_not_consumed(monkeypatch):
    sent = _setup(monkeypatch)
    dt.register("bjorn", "tok-A")
    rel.create("run-2", "sess-2")  # ingen subscriber, ikke consumed
    monkeypatch.setattr(pd, "_owner_of_run", lambda run_id: "bjorn")
    pd._dispatch_run_done("run-2")
    assert len(sent) == 1
    token, data = sent[0]
    assert token == "tok-A"
    assert data["kind"] == "answer_ready"
    assert data["run_id"] == "run-2"


def test_invalid_token_is_deleted(monkeypatch):
    _setup(monkeypatch)
    monkeypatch.setattr(pd, "_fcm_send", lambda token, data: (False, "invalid"))
    dt.register("bjorn", "tok-dead")
    rel.create("run-3", "sess-3")
    monkeypatch.setattr(pd, "_owner_of_run", lambda run_id: "bjorn")
    pd._dispatch_run_done("run-3")
    assert dt.list_for_user("bjorn") == []  # selv-oprydning
