import core.services.proactive_router as pr
import core.services.device_presence as dp


def _setup(monkeypatch):
    sent = {"fcm": [], "desk": []}
    monkeypatch.setattr(pr, "_arm_timer", lambda notif_id: None)
    monkeypatch.setattr(pr, "_send_fcm", lambda uid, key, data: sent["fcm"].append((key, data)))
    monkeypatch.setattr(pr, "_send_desktop", lambda uid, item: sent["desk"].append(item))
    monkeypatch.setattr(pr, "_fallback_blast", lambda uid, data: sent.setdefault("blast", []).append(data))
    monkeypatch.setattr(pr, "_new_id", lambda: "nid-1")
    pr.reset()
    return sent


def test_route_sends_to_best_desktop(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=True)
    dp.record_ping("bjorn", "mob", "mobile", foreground=False, awake=True, network="home")
    sent = _setup(monkeypatch)
    pr.route("bjorn", {"kind": "answer_ready", "session_id": "s1"}, "answer_ready")
    assert len(sent["desk"]) == 1 and sent["desk"][0]["notif_id"] == "nid-1"
    assert sent["fcm"] == []
    assert "nid-1" in pr._PENDING


def test_route_empty_presence_falls_back_to_blast(monkeypatch):
    monkeypatch.setattr(dp, "_now", lambda: 1000.0)
    dp.reset()  # ingen enheder
    sent = _setup(monkeypatch)
    pr.route("bjorn", {"kind": "reminder", "preview": "hej"}, "reminder")
    assert sent.get("blast") == [{"kind": "reminder", "preview": "hej"}]
    assert pr._PENDING == {}


def test_escalate_sends_to_next_then_ack_stops(monkeypatch):
    box = {"t": 1000.0}
    monkeypatch.setattr(dp, "_now", lambda: box["t"])
    dp.reset()
    dp.record_ping("bjorn", "desk", "desktop", foreground=True, awake=True, network="home", interaction=True)
    dp.record_ping("bjorn", "mob", "mobile", foreground=False, awake=True, network="home")
    sent = _setup(monkeypatch)
    pr.route("bjorn", {"kind": "answer_ready", "session_id": "s1"}, "answer_ready")
    assert len(sent["desk"]) == 1 and sent["fcm"] == []
    # simulér timer-fyring (ingen ack fra desktop):
    pr._escalate("nid-1")
    assert len(sent["fcm"]) == 1                # eskaleret til mobil
    assert sent["fcm"][0][0] == "mob"
    # ack stopper videre eskalering + rydder pending:
    pr.ack("nid-1")
    assert "nid-1" not in pr._PENDING
    pr._escalate("nid-1")                       # no-op efter ack
    assert len(sent["fcm"]) == 1
