from core.services import cowork_feed


def test_build_queue_includes_pending_initiatives(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_initiative_items", lambda: [
        {"id": "init-1", "title": "Ryd op i logs", "user_id": "owner", "status": "pending"},
    ])
    monkeypatch.setattr(cowork_feed, "_capability_items", lambda: [])
    monkeypatch.setattr(cowork_feed, "_proposal_items", lambda: [])
    items = cowork_feed.build_queue(user_id="owner", is_owner=True)
    assert any(i["id"] == "init-1" and i["kind"] == "initiative" for i in items)
    one = next(i for i in items if i["id"] == "init-1")
    assert set(one) >= {"id", "kind", "title", "detail", "source"}


def test_build_queue_owner_sees_all_users(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_initiative_items", lambda: [
        {"id": "a", "title": "x", "user_id": "mikkel", "status": "pending"},
    ])
    monkeypatch.setattr(cowork_feed, "_capability_items", lambda: [])
    monkeypatch.setattr(cowork_feed, "_proposal_items", lambda: [])
    assert len(cowork_feed.build_queue(user_id="owner", is_owner=True)) == 1


def test_build_queue_member_sees_only_own(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_initiative_items", lambda: [
        {"id": "a", "title": "x", "user_id": "mikkel", "status": "pending"},
        {"id": "b", "title": "y", "user_id": "owner", "status": "pending"},
    ])
    monkeypatch.setattr(cowork_feed, "_capability_items", lambda: [])
    monkeypatch.setattr(cowork_feed, "_proposal_items", lambda: [])
    items = cowork_feed.build_queue(user_id="mikkel", is_owner=False)
    assert [i["id"] for i in items] == ["a"]


def test_build_queue_normalizes_file_edit_with_diff(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_initiative_items", lambda: [])
    monkeypatch.setattr(cowork_feed, "_capability_items", lambda: [
        {"id": "c1", "capability_name": "write_file", "target_path": "core/x.py",
         "user_id": "owner", "diff": "-a\n+b"},
    ])
    items = cowork_feed.build_queue(user_id="owner", is_owner=True)
    one = next(i for i in items if i["id"] == "c1")
    assert one["kind"] == "file_edit" and one["diff"] == "-a\n+b"


def test_list_plans_member_filters_to_own(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_all_plans", lambda: [
        {"plan_id": "p1", "title": "A", "user_id": "mikkel", "steps_done": 1, "steps_total": 3},
        {"plan_id": "p2", "title": "B", "user_id": "owner", "steps_done": 0, "steps_total": 2},
    ])
    plans = cowork_feed.list_plans(user_id="mikkel", is_owner=False)
    assert [p["id"] for p in plans] == ["p1"]
    assert plans[0]["steps_done"] == 1 and plans[0]["steps_total"] == 3


def test_channel_status_returns_list(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_raw_channels", lambda: {"discord": {"online": True, "unread": 2}})
    chans = cowork_feed.channel_status()
    assert any(c["name"] == "discord" and c["online"] is True for c in chans)


def test_list_todos_feed_owner_aggregates(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_all_todos", lambda: [
        {"id": "t1", "content": "Byg cowork", "status": "in_progress"},
        {"id": "", "content": "tom", "status": "pending"},
    ])
    todos = cowork_feed.list_todos_feed(user_id="owner", is_owner=True)
    assert [t["id"] for t in todos] == ["t1"]


def test_list_todos_feed_member_empty(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_all_todos", lambda: [{"id": "t1", "content": "x", "status": "pending"}])
    assert cowork_feed.list_todos_feed(user_id="mikkel", is_owner=False) == []


def test_channel_status_includes_webchat(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_raw_channels", lambda: {"webchat": {"online": True, "unread": 0}})
    names = [c["name"] for c in cowork_feed.channel_status()]
    assert "webchat" in names


def test_build_queue_includes_proposals(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_proposal_items", lambda: [
        {"proposal_id": "prop-abc", "kind": "commit", "title": "Commit X", "rationale": "fordi"},
    ])
    monkeypatch.setattr(cowork_feed, "_initiative_items", lambda: [])
    monkeypatch.setattr(cowork_feed, "_capability_items", lambda: [])
    items = cowork_feed.build_queue(user_id="owner", is_owner=True)
    one = next(i for i in items if i["id"] == "prop-abc")
    assert one["kind"] == "proposal" and one["source"] == "proposal"


def test_list_active_agents_shape(monkeypatch) -> None:
    from core.services import cowork_feed
    fake_rows = [
        {"agent_id": "a1", "role": "researcher", "goal": "x" * 200,
         "status": "active", "parent_agent_id": "jarvis", "tokens_burned": 42},
    ]
    monkeypatch.setattr(
        "core.runtime.db.list_agent_registry_entries",
        lambda status="", limit=50: fake_rows,
    )
    agents = cowork_feed.list_active_agents()
    assert len(agents) == 1
    a = agents[0]
    assert a["agent_id"] == "a1" and a["role"] == "researcher"
    assert a["status"] == "active" and a["parent"] == "jarvis"
    assert a["tokens_burned"] == 42
    assert a["goal"].endswith("…")            # trunkeret til 160


def test_list_active_agents_handles_error(monkeypatch) -> None:
    from core.services import cowork_feed
    def _boom(*a, **k):
        raise RuntimeError("db down")
    monkeypatch.setattr("core.runtime.db.list_agent_registry_entries", _boom)
    assert cowork_feed.list_active_agents() == []
