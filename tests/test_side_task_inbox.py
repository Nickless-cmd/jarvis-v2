from contextlib import nullcontext

from core.services import inbox_state, inbox_view, side_tasks
from core.services.inbox_view import Kilder, byg_indbakke


def _setup(monkeypatch):
    state = []
    monkeypatch.setattr(side_tasks, "load_json", lambda _key, _default: list(state))
    monkeypatch.setattr(side_tasks, "save_json", lambda _key, items: state.__setitem__(slice(None), items))
    monkeypatch.setattr(side_tasks, "med_laas", lambda _key: nullcontext())
    monkeypatch.setattr(inbox_view, "_ejer_id", lambda: "owner")
    monkeypatch.setattr(inbox_state, "_ejer_id", lambda: "owner")
    return state


def _kilder():
    return Kilder(
        poster=lambda _b: [], vaekninger=lambda _b: [], jobs=lambda _b: [],
        godkendelser=lambda _b: [], planlagte=lambda _b: [],
        gentagende=lambda _b: [], backlog_tal=lambda: 0,
        side_opgaver=lambda _b: side_tasks.list_open(),
    )


def test_side_tasks_are_read_only_projection_and_empty_section_disappears(monkeypatch):
    _setup(monkeypatch)
    k = _kilder()
    assert byg_indbakke("owner", kilder=k)["sideopgaver"] == []
    tid = side_tasks.flag(title="Test første frame", prompt="Verificér hjulets start")["side_task_id"]
    v = byg_indbakke("owner", kilder=k)
    assert [(p["id"], p["status"]) for p in v["sideopgaver"]] == [(tid, "venter")]
    assert not v["sideopgaver"][0]["kraever_handling"]
    assert byg_indbakke("other", kilder=k)["sideopgaver"] == []

    side_tasks.resolve(tid, decision="queued")
    assert byg_indbakke("owner", kilder=k)["sideopgaver"][0]["status"] == "kø"
    side_tasks.resolve(tid, decision="activated", arbejds_session="chat-7", arbejds_run_id="run-8")
    active = byg_indbakke("owner", kilder=k)["sideopgaver"][0]
    assert active["status"] == "i gang" and active["session_id"] == "chat-7"
    assert active["run_id"] == "run-8"
    side_tasks.resolve(tid, decision="completed")
    assert byg_indbakke("owner", kilder=k)["sideopgaver"] == []


def test_inbox_done_and_drop_change_side_task_source_not_a_second_record(monkeypatch):
    state = _setup(monkeypatch)
    first = side_tasks.flag(title="A", prompt="Gør A")["side_task_id"]
    second = side_tasks.flag(title="B", prompt="Gør B")["side_task_id"]
    assert inbox_state.done("other", first)["status"] == "ukendt"
    assert inbox_state.done("owner", first)["status"] == "ok"
    assert inbox_state.drop("owner", second, "ikke relevant")["status"] == "ok"
    assert [(r["status"], r.get("lukket_af")) for r in state] == [
        ("completed", "inbox"), ("dismissed", "inbox"),
    ]
    assert side_tasks.list_open() == []
