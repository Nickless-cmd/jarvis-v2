from datetime import UTC, datetime, timedelta


def _ensure_events_table():
    from core.runtime.db import connect
    with connect() as c:
        c.execute(
            "CREATE TABLE IF NOT EXISTS events ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, "
            "payload_json TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        c.commit()


def _insert_event(created_at: str, kind: str = "runtime.test_ret"):
    from core.runtime.db import connect
    with connect() as c:
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
            (kind, "{}", created_at),
        )
        c.commit()


def test_prunes_old_keeps_recent(isolated_runtime):
    from core.services.events_retention import prune_old_events
    from core.runtime.db import connect
    _ensure_events_table()
    now = datetime.now(UTC)
    old = (now - timedelta(days=40)).isoformat()
    recent = (now - timedelta(days=1)).isoformat()
    for _ in range(3):
        _insert_event(old, kind="runtime.test_ret_old")
    for _ in range(2):
        _insert_event(recent, kind="runtime.test_ret_new")

    res = prune_old_events(max_age_days=14)
    assert res["deleted"] == 3  # exactly the 3 old ones (fresh isolated DB)

    with connect() as c:
        old_left = c.execute(
            "SELECT COUNT(*) n FROM events WHERE kind='runtime.test_ret_old'"
        ).fetchone()["n"]
        new_left = c.execute(
            "SELECT COUNT(*) n FROM events WHERE kind='runtime.test_ret_new'"
        ).fetchone()["n"]
    assert old_left == 0      # old pruned
    assert new_left == 2      # recent kept


def test_cap_limits_deletion_per_call(isolated_runtime):
    from core.services.events_retention import prune_old_events
    _ensure_events_table()
    now = datetime.now(UTC)
    old = (now - timedelta(days=40)).isoformat()
    for _ in range(10):
        _insert_event(old, kind="runtime.test_ret_cap")
    res = prune_old_events(max_age_days=14, max_delete=4, batch_size=2)
    assert res["deleted"] == 4  # capped, not all 10


def test_self_safe_returns_dict(isolated_runtime):
    from core.services.events_retention import prune_old_events
    _ensure_events_table()
    res = prune_old_events(max_age_days=9999)  # cutoff far in past → deletes nothing
    assert isinstance(res, dict) and "deleted" in res and res["deleted"] == 0


def test_prune_table_by_age_rejects_bad_identifier(isolated_runtime):
    from core.services.events_retention import prune_table_by_age
    res = prune_table_by_age("events; DROP TABLE events", "created_at", max_age_days=1)
    assert res["deleted"] == 0 and res.get("error") == "invalid identifier"


def test_prune_telemetry_tables_self_safe(isolated_runtime):
    # Missing telemetry tables in the fresh DB → each entry errors softly, no raise.
    from core.services.events_retention import prune_telemetry_tables
    res = prune_telemetry_tables()
    assert isinstance(res, dict) and "daemon_output_log" in res
