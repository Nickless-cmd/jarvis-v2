import core.services.agent_todos as at


def _reset(monkeypatch):
    store: dict = {}
    monkeypatch.setattr(at, "_load_all", lambda: {k: list(v) for k, v in store.items()})
    monkeypatch.setattr(at, "_save_all", lambda data: store.update({k: list(v) for k, v in data.items()}))
    return store


def test_paused_is_valid_status(monkeypatch):
    _reset(monkeypatch)
    at.add_cowork_todo("x")
    tid = at.list_todos(at.COWORK_SESSION)[0]["id"]
    res = at.update_todo_status_anywhere(tid, "paused")
    assert res["status"] == "ok"
    assert at.list_todos(at.COWORK_SESSION)[0]["status"] == "paused"


def test_effective_status_expired_when_past():
    t = {"status": "pending", "expires_at": "2000-01-01T00:00:00+00:00"}
    assert at.effective_status(t, "2026-06-15T00:00:00+00:00") == "expired"


def test_effective_status_not_expired_when_future():
    t = {"status": "pending", "expires_at": "2099-01-01T00:00:00+00:00"}
    assert at.effective_status(t, "2026-06-15T00:00:00+00:00") == "pending"


def test_effective_status_completed_never_expires():
    t = {"status": "completed", "expires_at": "2000-01-01T00:00:00+00:00"}
    assert at.effective_status(t, "2026-06-15T00:00:00+00:00") == "completed"


def test_set_expiry_anywhere(monkeypatch):
    _reset(monkeypatch)
    at.add_cowork_todo("x")
    tid = at.list_todos(at.COWORK_SESSION)[0]["id"]
    at.set_todo_expiry_anywhere(tid, "2099-01-01T00:00:00+00:00")
    assert at.list_todos(at.COWORK_SESSION)[0]["expires_at"] == "2099-01-01T00:00:00+00:00"
    at.set_todo_expiry_anywhere(tid, None)
    assert at.list_todos(at.COWORK_SESSION)[0].get("expires_at") in (None, "")


def test_prompt_section_hides_paused_and_expired(monkeypatch):
    _reset(monkeypatch)
    at.add_todo("s", "synlig opgave")
    at.add_todo("s", "pauset opgave")
    at.add_todo("s", "udløbet opgave")
    items = at.list_todos("s")
    at.update_todo_status_anywhere(items[1]["id"], "paused")
    at.set_todo_expiry_anywhere(items[2]["id"], "2000-01-01T00:00:00+00:00")
    section = at.todos_prompt_section("s")
    assert "synlig opgave" in section
    assert "pauset opgave" not in section
    assert "udløbet opgave" not in section
