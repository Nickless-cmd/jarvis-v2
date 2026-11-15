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


def test_list_active_runs_finds_kørsler_på_tværs_af_rutiner(isolated_runtime, monkeypatch):
    """«Kører nu» i sidebaren skal vise ALT der er i gang — ikke ét opslag pr. rutine.

    Målt 15/11-2026: 10 synlige rutiner ville kræve 10 kald. Her er det ét.
    Navnet skal være dekrypteret, fordi blokken viser menneskets eget ord.
    """
    import core.services.keyring_store as keyring_store
    from core.runtime.db_routines import create_routine, create_run, list_active_runs

    monkeypatch.setattr(keyring_store, "get_user_key", lambda _owner: b"x" * 32)

    def _rutine(navn: str) -> dict:
        return create_routine(
            owner_user_id="u1",
            access_scope="user_private",
            name=navn,
            instruction=b"x",
            capability_scope="chat",
            trigger_kind="manual",
            trigger_config={},
            permission_policy={},
            delivery_policy={},
            inbox_policy={},
            retention_policy={},
            failure_policy={},
        )

    a = _rutine("A")
    b = _rutine("B")
    create_run(routine_id=a["routine_id"], idempotency_key="k1")
    create_run(routine_id=b["routine_id"], idempotency_key="k2")

    aktive = list_active_runs(owner_user_id="u1")
    assert {r["routine_id"] for r in aktive} == {a["routine_id"], b["routine_id"]}
    assert {r["name"] for r in aktive} == {"A", "B"}
    assert all(r["status"] in ("queued", "running") for r in aktive)

    # En anden ejer må ikke se dem — blokken er personlig, ikke global.
    assert list_active_runs(owner_user_id="u2") == []
    # Tom ejer giver tom liste frem for et kald der fejler.
    assert list_active_runs(owner_user_id="") == []


def test_list_origin_sessions_rammer_kun_den_ene_oprindelse(isolated_runtime):
    """En system-rutine har nul `routine_runs`; dens spor er `auto-{origin}-{dato}`.

    Uden dette opslag står «System · heartbeat»'s Kørsler-fane tom, og det ser
    ud som om rutinen aldrig har kørt (Bjørn 15/11-2026).
    """
    from core.runtime.db_routines import list_origin_sessions
    from core.services.autonomous_sessions import resolve_autonomous_session

    resolve_autonomous_session("heartbeat")
    resolve_autonomous_session("dream")

    hjerte = list_origin_sessions("heartbeat")
    assert len(hjerte) == 1
    assert hjerte[0]["session_id"].startswith("auto-heartbeat-")
    assert hjerte[0]["title"]

    # Drømme må ikke blande sig i hjerteslag — det var hele pointen.
    droemme = list_origin_sessions("dream")
    assert len(droemme) == 1
    assert droemme[0]["session_id"].startswith("auto-dream-")

    assert list_origin_sessions("wakeup") == []
    assert list_origin_sessions("") == []
