from __future__ import annotations

import sqlite3

import pytest


@pytest.fixture(autouse=True)
def deterministic_user_keys(monkeypatch):
    import core.services.keyring_store as keyring_store

    monkeypatch.setattr(
        keyring_store,
        "get_user_key",
        lambda user_id: (str(user_id).encode("utf-8") + (b"x" * 32))[:32],
    )


@pytest.fixture
def routine_row(isolated_runtime):
    from core.runtime.db_routines import create_routine

    return create_routine(
        owner_user_id="u1",
        access_scope="user_private",
        name="Morgen",
        instruction=b"hemmelig instruktion",
        capability_scope="chat",
        trigger_kind="manual",
        trigger_config={"timezone": "Europe/Copenhagen"},
        permission_policy={"tools": []},
        delivery_policy={"channel": "desk"},
        inbox_policy={"failed": True},
        retention_policy={"archive_stopped_days": 30},
        failure_policy={"consecutive_failures": 3},
    )


def test_private_fields_are_ciphertext_at_rest(isolated_runtime):
    from core.runtime.db_core import connect
    from core.runtime.db_routines import create_routine, get_routine

    row = create_routine(
        owner_user_id="u1",
        access_scope="user_private",
        name="Morgen",
        instruction=b"hemmelig",
        capability_scope="chat",
        trigger_kind="manual",
        trigger_config={"private": "vaek mig"},
        permission_policy={},
        delivery_policy={},
        inbox_policy={},
        retention_policy={},
        failure_policy={},
    )
    with connect() as conn:
        raw = conn.execute(
            "SELECT instruction_enc, trigger_config_enc FROM routines WHERE routine_id=?",
            (row["routine_id"],),
        ).fetchone()
    assert b"hemmelig" not in bytes(raw[0])
    assert b"vaek mig" not in bytes(raw[1])
    opened = get_routine(row["routine_id"], decrypt_for="u1")
    assert opened["instruction"] == b"hemmelig"
    assert opened["trigger_config"] == {"private": "vaek mig"}


def test_wrong_owner_cannot_open_private_fields(routine_row):
    from core.services.encryption import DecryptionError
    from core.runtime.db_routines import get_routine

    with pytest.raises(DecryptionError):
        get_routine(routine_row["routine_id"], decrypt_for="u2")


def test_idempotent_trigger_key_creates_one_run(isolated_runtime, routine_row):
    from core.runtime.db_routines import create_run

    first = create_run(routine_id=routine_row["routine_id"], idempotency_key="tick:1")
    second = create_run(routine_id=routine_row["routine_id"], idempotency_key="tick:1")
    assert second["run_id"] == first["run_id"]


def test_schema_contains_every_routine_table(isolated_runtime, routine_row):
    from core.runtime.db_core import connect

    expected = {
        "routines",
        "routine_versions",
        "routine_runs",
        "routine_run_events",
        "routine_deliveries",
        "routine_legacy_links",
        "routine_migration_quarantine",
        "routine_inbox_preferences",
        "routine_tombstones",
    }
    with connect() as conn:
        found = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'routine%'"
            ).fetchall()
        }
    assert expected <= found


@pytest.mark.parametrize("table", ["routines", "routine_runs", "routine_deliveries"])
def test_invalid_status_is_rejected_by_sqlite(isolated_runtime, routine_row, table):
    from core.runtime.db_core import connect

    identifiers = {
        "routines": ("routine_id", routine_row["routine_id"]),
        "routine_runs": (
            "run_id",
            __import__("core.runtime.db_routines", fromlist=["create_run"])
            .create_run(routine_id=routine_row["routine_id"], idempotency_key="invalid-status")["run_id"],
        ),
        "routine_deliveries": (
            "delivery_id",
            __import__("core.runtime.db_routines", fromlist=["create_delivery"])
            .create_delivery(
                run_id=__import__("core.runtime.db_routines", fromlist=["create_run"])
                .create_run(routine_id=routine_row["routine_id"], idempotency_key="delivery-status")["run_id"],
                channel="desk",
            )["delivery_id"],
        ),
    }
    column, value = identifiers[table]
    with connect() as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute(f"UPDATE {table} SET status='not-a-state' WHERE {column}=?", (value,))


def test_routine_version_is_monotonic_and_snapshotted(routine_row):
    from core.runtime.db_routines import get_routine, transition_routine

    first = transition_routine(
        routine_row["routine_id"],
        to_status="paused",
        expected_version=1,
    )
    assert first["version"] == 2
    with pytest.raises(ValueError, match="stale routine version"):
        transition_routine(
            routine_row["routine_id"],
            to_status="active",
            expected_version=1,
        )
    assert get_routine(routine_row["routine_id"])["version"] == 2


def test_run_has_only_one_terminal_event(routine_row):
    from core.runtime.db_core import connect
    from core.runtime.db_routines import append_run_event, create_run

    run = create_run(routine_id=routine_row["routine_id"], idempotency_key="terminal:1")
    first = append_run_event(
        run_id=run["run_id"], kind="succeeded", payload={"result": "ok"}, terminal=True
    )
    second = append_run_event(
        run_id=run["run_id"], kind="failed", payload={"error": "late"}, terminal=True
    )
    assert second["event_id"] == first["event_id"]
    with connect() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM routine_run_events WHERE run_id=? AND terminal=1",
            (run["run_id"],),
        ).fetchone()[0]
    assert count == 1


def test_claim_is_fenced_and_idempotent_for_holder(routine_row):
    from core.runtime.db_routines import claim_run, create_run

    run = create_run(routine_id=routine_row["routine_id"], idempotency_key="claim:1")
    first = claim_run(run["run_id"], holder="worker-a")
    again = claim_run(run["run_id"], holder="worker-a")
    assert first["lease_generation"] == again["lease_generation"] == 1
    assert claim_run(run["run_id"], holder="worker-b") is None
