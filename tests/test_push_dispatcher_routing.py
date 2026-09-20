import core.services.push_dispatcher as pd


def test_dispatch_run_done_routes_when_enabled(monkeypatch):
    calls = {"route": []}
    monkeypatch.setattr(pd, "_route_or_blast", lambda uid, data, kind: calls["route"].append((uid, kind)))
    monkeypatch.setattr(pd, "_owner_of_run", lambda rid: "bjorn")
    import core.services.run_event_log as rel
    monkeypatch.setattr(rel, "was_consumed_or_active", lambda rid: False)
    monkeypatch.setattr(rel, "session_for_run", lambda rid: "s1")
    monkeypatch.setattr(pd, "_last_assistant_preview", lambda sid: "et svar")
    pd._dispatch_run_done("run-1")
    assert calls["route"] == [("bjorn", "answer_ready")]


def test_route_or_blast_respects_killswitch(monkeypatch):
    seen = {"router": 0, "blast": 0}
    import core.services.notification_router as prr
    monkeypatch.setattr(prr, "route_device_aware", lambda uid, data, kind: seen.__setitem__("router", seen["router"] + 1))
    monkeypatch.setattr(pd, "_push_to_user", lambda uid, data: seen.__setitem__("blast", seen["blast"] + 1))
    from core.runtime import settings as st
    monkeypatch.setattr(st, "load_settings", lambda: type("S", (), {"device_awareness_enabled": False})())
    pd._route_or_blast("bjorn", {"kind": "reminder"}, "reminder")
    assert seen == {"router": 0, "blast": 1}  # flag OFF → gammel blast


def test_route_or_blast_routes_when_enabled(monkeypatch):
    seen = {"router": 0, "blast": 0}
    import core.services.notification_router as prr
    monkeypatch.setattr(prr, "route_device_aware", lambda uid, data, kind: seen.__setitem__("router", seen["router"] + 1))
    monkeypatch.setattr(pd, "_push_to_user", lambda uid, data: seen.__setitem__("blast", seen["blast"] + 1))
    from core.runtime import settings as st
    monkeypatch.setattr(st, "load_settings", lambda: type("S", (), {"device_awareness_enabled": True})())
    pd._route_or_blast("bjorn", {"kind": "reminder"}, "reminder")
    assert seen == {"router": 1, "blast": 0}


# ── Pushet bærer fladen turen blev skrevet fra (Bjørn 20/9-2026) ─────────────
def test_answer_ready_carries_the_runs_surface(monkeypatch):
    seen = {}
    monkeypatch.setattr(pd, "_route_or_blast", lambda uid, data, kind: seen.update(data))
    monkeypatch.setattr(pd, "_owner_of_run", lambda rid: "bjorn")
    import core.services.run_event_log as rel
    monkeypatch.setattr(rel, "was_consumed_or_active", lambda rid: False)
    monkeypatch.setattr(rel, "session_for_run", lambda rid: "s1")
    monkeypatch.setattr(rel, "surface_for_run", lambda rid: "desk")
    monkeypatch.setattr(pd, "_last_assistant_preview", lambda sid: "et svar")
    pd._dispatch_run_done("run-1")
    assert seen["surface"] == "desk"


def test_approval_push_carries_the_envelopes_surface(monkeypatch):
    seen = {}
    monkeypatch.setattr(pd, "_route_or_blast", lambda uid, data, kind: seen.update(data) or True)
    pd.on_approval_requested("bjorn", {"request_id": "a1", "capability_name": "Skriv fil",
                                       "surface": "desk"})
    assert seen["surface"] == "desk"
    seen.clear()
    pd.on_approval_requested("bjorn", {"request_id": "a2"})  # ukendt flade → tom
    assert seen["surface"] == ""
