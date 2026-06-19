import core.tools.companion_push_tools as cpt


def test_exec_requires_message():
    r = cpt._exec_send_push_notification({"message": "  "})
    assert r["status"] == "error"


def test_exec_routes_to_current_user(monkeypatch):
    sent = {}
    import core.identity.workspace_context as wc
    monkeypatch.setattr(wc, "current_user_id", lambda: "1246415163603816499")
    import core.services.push_dispatcher as pd
    monkeypatch.setattr(pd, "send_companion_push",
                        lambda uid, msg, title="Jarvis": sent.update(uid=uid, msg=msg, title=title) or True)
    r = cpt._exec_send_push_notification({"message": "Kaffen er klar", "title": "Jarvis"})
    assert r["status"] == "ok"
    assert sent == {"uid": "1246415163603816499", "msg": "Kaffen er klar", "title": "Jarvis"}


def test_exec_no_user(monkeypatch):
    import core.identity.workspace_context as wc
    monkeypatch.setattr(wc, "current_user_id", lambda: "")
    r = cpt._exec_send_push_notification({"message": "hej"})
    assert r["status"] == "error"


def test_tool_registered_in_definitions():
    from core.tools.simple_tools import get_tool_definitions
    names = set()
    for d in get_tool_definitions():
        n = d.get("function", {}).get("name") if "function" in d else d.get("name")
        if n:
            names.add(n)
    assert "send_push_notification" in names
