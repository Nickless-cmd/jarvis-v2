from apps.api.jarvis_api.routes.account import build_quota_overview


def _fake_check(user_id, kind):
    table = {
        "chat": {"tier": "plus", "used": 5, "limit": None, "remaining": None, "warn": False},
        "code": {"tier": "plus", "used": 30, "limit": 180, "remaining": 150, "warn": False},
        "cowork": {"tier": "plus", "used": 9, "limit": 10, "remaining": 1, "warn": True},
        "agent": {"tier": "plus", "used": 0, "limit": 2, "remaining": 2, "warn": False},
    }
    return table[kind]


def test_overview_collects_all_kinds():
    ov = build_quota_overview("u1", check_quota=_fake_check)
    assert ov["tier"] == "plus"
    kinds = {i["kind"] for i in ov["items"]}
    assert kinds == {"chat", "code", "cowork", "agent"}


def test_overview_item_shape():
    ov = build_quota_overview("u1", check_quota=_fake_check)
    cowork = next(i for i in ov["items"] if i["kind"] == "cowork")
    assert cowork["used"] == 9
    assert cowork["limit"] == 10
    assert cowork["warn"] is True


def test_overview_unlimited_limit_is_none():
    ov = build_quota_overview("u1", check_quota=_fake_check)
    chat = next(i for i in ov["items"] if i["kind"] == "chat")
    assert chat["limit"] is None
