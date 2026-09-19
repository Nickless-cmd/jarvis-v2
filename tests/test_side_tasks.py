from core.services import side_tasks


def test_flagged_task_stays_visible_when_activated_until_completed(monkeypatch):
    state = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _key, _default: list(state))
    monkeypatch.setattr(side_tasks, "save_json", lambda _key, items: state.__setitem__(slice(None), items))

    task_id = side_tasks.flag(title="Ryd op", prompt="Ryd op i dokumenterne")["side_task_id"]
    assert [item["side_task_id"] for item in side_tasks.list_open()] == [task_id]

    side_tasks.resolve(task_id, decision="activated")
    assert [item["side_task_id"] for item in side_tasks.list_open()] == [task_id]
    assert task_id in side_tasks.side_tasks_prompt_section()

    side_tasks.resolve(task_id, decision="completed")
    assert side_tasks.list_open() == []
    assert side_tasks.side_tasks_prompt_section() is None
    assert side_tasks.resolve(task_id, decision="activated")["status"] == "error"
    assert state[0]["status"] == "completed"


def test_dismiss_tool_preserves_old_default_and_can_complete(monkeypatch):
    state = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _key, _default: list(state))
    monkeypatch.setattr(side_tasks, "save_json", lambda _key, items: state.__setitem__(slice(None), items))

    first = side_tasks.flag(title="Én", prompt="Gør én ting")["side_task_id"]
    second = side_tasks.flag(title="To", prompt="Gør en anden ting")["side_task_id"]
    assert side_tasks._exec_dismiss_side_task({"side_task_id": first})["new_status"] == "dismissed"
    assert side_tasks._exec_dismiss_side_task({"side_task_id": second, "decision": "completed"})["new_status"] == "completed"
    assert side_tasks.list_open() == []


def test_dismiss_tool_rejects_unknown_decision_and_lists_open_only(monkeypatch):
    state = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _key, _default: list(state))
    monkeypatch.setattr(side_tasks, "save_json", lambda _key, items: state.__setitem__(slice(None), items))

    tid = side_tasks.flag(title="Tre", prompt="Gør en tredje ting")["side_task_id"]
    # «activated» er ikke en afslutning — værktøjet må ikke kunne bruges til det.
    assert side_tasks._exec_dismiss_side_task({"side_task_id": tid, "decision": "activated"})["status"] == "error"
    side_tasks.resolve(tid, decision="activated")
    listed = side_tasks._exec_list_side_tasks({})
    assert listed["count"] == 1 and listed["side_tasks"][0]["status"] == "activated"
    assert "(i gang)" in side_tasks.side_tasks_prompt_section()
