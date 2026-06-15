import core.services.agent_todos as at


def _reset(monkeypatch):
    store: dict = {}
    monkeypatch.setattr(at, "_load_all", lambda: {k: list(v) for k, v in store.items()})
    monkeypatch.setattr(at, "_save_all", lambda data: store.update({k: list(v) for k, v in data.items()}))
    return store


def test_add_cowork_todo_lands_in_cowork_session(monkeypatch):
    _reset(monkeypatch)
    res = at.add_cowork_todo("ring til mekanikeren")
    assert res["status"] == "ok"
    todos = at.list_todos(at.COWORK_SESSION)
    assert len(todos) == 1
    assert todos[0]["content"] == "ring til mekanikeren"
    assert todos[0]["status"] == "pending"


def test_update_status_anywhere_finds_todo_in_any_session(monkeypatch):
    _reset(monkeypatch)
    at.add_todo("sess-A", "opgave fra chat")
    tid = at.list_todos("sess-A")[0]["id"]
    res = at.update_todo_status_anywhere(tid, "completed")
    assert res["status"] == "ok"
    assert at.list_todos("sess-A")[0]["status"] == "completed"


def test_update_status_anywhere_unknown_id(monkeypatch):
    _reset(monkeypatch)
    res = at.update_todo_status_anywhere("td-nope", "completed")
    assert res["status"] == "error"


def test_remove_anywhere_deletes_from_owning_session(monkeypatch):
    _reset(monkeypatch)
    at.add_cowork_todo("slet mig")
    tid = at.list_todos(at.COWORK_SESSION)[0]["id"]
    res = at.remove_todo_anywhere(tid)
    assert res["status"] == "ok"
    assert at.list_todos(at.COWORK_SESSION) == []
