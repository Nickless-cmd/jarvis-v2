def test_routine_repository_creates_owner_scoped_row(isolated_runtime, monkeypatch):
    import core.services.keyring_store as keyring_store
    from core.runtime.db_routines import create_routine, get_routine

    monkeypatch.setattr(keyring_store, "get_user_key", lambda _owner: b"x" * 32)
    created = create_routine(
        owner_user_id="u1",
        access_scope="user_private",
        name="Morgen",
        instruction=b"privat",
        capability_scope="chat",
        trigger_kind="manual",
        trigger_config={},
        permission_policy={},
        delivery_policy={},
        inbox_policy={},
        retention_policy={},
        failure_policy={},
    )
    opened = get_routine(created["routine_id"], decrypt_for="u1")
    assert opened["owner_user_id"] == "u1"
    assert opened["instruction"] == b"privat"
