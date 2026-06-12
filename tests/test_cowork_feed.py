from core.services import cowork_feed


def test_build_queue_includes_pending_initiatives(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_initiative_items", lambda: [
        {"id": "init-1", "title": "Ryd op i logs", "user_id": "owner", "status": "pending"},
    ])
    monkeypatch.setattr(cowork_feed, "_capability_items", lambda: [])
    items = cowork_feed.build_queue(user_id="owner", is_owner=True)
    assert any(i["id"] == "init-1" and i["kind"] == "initiative" for i in items)
    one = next(i for i in items if i["id"] == "init-1")
    assert set(one) >= {"id", "kind", "title", "detail", "source"}


def test_build_queue_owner_sees_all_users(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_initiative_items", lambda: [
        {"id": "a", "title": "x", "user_id": "mikkel", "status": "pending"},
    ])
    monkeypatch.setattr(cowork_feed, "_capability_items", lambda: [])
    assert len(cowork_feed.build_queue(user_id="owner", is_owner=True)) == 1


def test_build_queue_member_sees_only_own(monkeypatch):
    monkeypatch.setattr(cowork_feed, "_initiative_items", lambda: [
        {"id": "a", "title": "x", "user_id": "mikkel", "status": "pending"},
        {"id": "b", "title": "y", "user_id": "owner", "status": "pending"},
    ])
    monkeypatch.setattr(cowork_feed, "_capability_items", lambda: [])
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
