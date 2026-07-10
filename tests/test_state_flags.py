from __future__ import annotations
from core.tools import state_flag_tools as t
from core.services import state_flag_store as s


def test_set_get_clear_lifecycle(isolated_runtime):
    r = t._exec_set_flag({"key": "review_this", "value": {"id": 42}})
    assert r["status"] == "ok" and r["confirmed"] is True
    g = t._exec_get_flag({"key": "review_this"})
    assert g["found"] is True and g["flag"]["value"] == {"id": 42}
    c = t._exec_clear_flag({"key": "review_this"})
    assert c["confirmed"] is True and c["existed"] is True
    assert t._exec_get_flag({"key": "review_this"})["found"] is False


def test_list_flags(isolated_runtime):
    t._exec_set_flag({"key": "a", "value": 1})
    t._exec_set_flag({"key": "b", "value": 2})
    lst = t._exec_list_flags({})
    assert lst["count"] == 2 and {f["key"] for f in lst["flags"]} == {"a", "b"}


def test_ttl_expiry(isolated_runtime, monkeypatch):
    from datetime import datetime, timedelta, UTC
    s.set_flag("temp", "x", ttl_minutes=5, user_id="default")
    assert s.get_flag("temp", user_id="default") is not None
    # spol tiden 10 min frem → udløbet + pruned
    real_now = s._now()
    monkeypatch.setattr(s, "_now", lambda: real_now + timedelta(minutes=10))
    assert s.get_flag("temp", user_id="default") is None
    assert s.list_flags(user_id="default") == []


def test_registered_in_catalog(isolated_runtime):
    from core.tools.simple_tools import get_tool_definitions
    names = {(d.get("function") or {}).get("name") for d in get_tool_definitions(role="owner")}
    assert {"set_flag", "get_flag", "clear_flag", "list_flags"} <= names
