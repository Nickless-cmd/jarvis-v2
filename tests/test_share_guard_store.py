from __future__ import annotations


def _rec(did="d1", **kw):
    from core.services.share_guard_store import record_pending
    base = dict(
        decision_id=did, session_id="s1", current_user_id="u-bjorn",
        mentioned_users=["Mikkel"], text_preview="Mikkel sagde hej",
        created_at="2026-06-14T12:00:00Z",
    )
    base.update(kw)
    return record_pending(**base)


def test_record_and_list_pending(isolated_runtime) -> None:
    from core.services.share_guard_store import list_pending

    _rec("d1")
    _rec("d2", mentioned_users=["Mor"])
    pend = list_pending()
    assert {p["id"] for p in pend} == {"d1", "d2"}
    assert pend[0]["status"] == "pending"


def test_resolve_shared_removes_from_pending(isolated_runtime) -> None:
    from core.services.share_guard_store import list_pending, resolve

    _rec("d1")
    assert resolve("d1", shared=True) is True
    assert list_pending() == []


def test_resolve_kept_private(isolated_runtime) -> None:
    from core.services.share_guard_store import list_pending, resolve

    _rec("d1")
    assert resolve("d1", shared=False) is True
    assert list_pending() == []


def test_resolve_unknown_returns_false(isolated_runtime) -> None:
    from core.services.share_guard_store import resolve

    assert resolve("nope", shared=True) is False


def test_record_is_idempotent_on_id(isolated_runtime) -> None:
    from core.services.share_guard_store import list_pending

    _rec("d1", text_preview="første")
    _rec("d1", text_preview="anden")  # samme id → erstat, ikke dublér
    pend = list_pending()
    assert len(pend) == 1
    assert pend[0]["text_preview"] == "anden"
