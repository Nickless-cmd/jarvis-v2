"""Tests that member-user queries only see their own workspace + Jarvis-shared.

After Task 4, members get filtered results from chronicle, dreams,
initiatives, scheduled_tasks.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest


BJORN_ID = "1246415163603816499"
MIKKEL_ID = "238975101381378048"


@pytest.fixture
def mu_db(isolated_runtime: SimpleNamespace):
    """Multi-user test DB. Piggybacks on isolated_runtime for proper module
    reload chain, then seeds chronicle/scheduled rows with different user_id
    tags so we can test filtering."""
    db = isolated_runtime.db
    cfg_dir = isolated_runtime.config.CONFIG_DIR

    # Seed users.json with Bjørn (owner) and Mikkel (member)
    (cfg_dir / "users.json").write_text(json.dumps({
        "users": [
            {
                "discord_id": BJORN_ID,
                "name": "Bjørn",
                "role": "owner",
                "workspace": "bjorn",
                "created_at": "2026-01-01",
            },
            {
                "discord_id": MIKKEL_ID,
                "name": "Mikkel",
                "role": "member",
                "workspace": "mikkel",
                "created_at": "2026-01-01",
            },
        ]
    }))

    with db.connect() as conn:
        # Discover the actual schema for cognitive_chronicle_entries
        db._ensure_cognitive_chronicle_entries_table(conn)
        cur = conn.execute("PRAGMA table_info(cognitive_chronicle_entries)")
        existing_cols = {r[1] for r in cur.fetchall()}

        # Full set of values covering all known schema variants
        all_values: dict[str, object] = {
            "entry_id": "c1",
            "period": "2026-01",
            "narrative": "general jarvis thought",
            "key_events": "[]",
            "lessons": "[]",
            "affective_signature": "",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "relevant_to_users": None,
        }

        cols_to_use = [c for c in all_values if c in existing_cols]
        placeholders = ",".join(["?"] * len(cols_to_use))
        col_list = ",".join(cols_to_use)

        def _insert_chronicle(entry_id: str, narrative: str, relevant_to_users: object) -> None:
            all_values["entry_id"] = entry_id
            all_values["narrative"] = narrative
            all_values["relevant_to_users"] = relevant_to_users
            values = tuple(all_values[c] for c in cols_to_use)
            try:
                conn.execute(
                    f"INSERT INTO cognitive_chronicle_entries ({col_list}) VALUES ({placeholders})",
                    values,
                )
            except sqlite3.IntegrityError:
                pass

        _insert_chronicle("c1", "general jarvis thought", None)
        _insert_chronicle("c2", "bjorn-specific", json.dumps([BJORN_ID]))
        _insert_chronicle("c3", "mikkel-specific", json.dumps([MIKKEL_ID]))

        # Seed scheduled_tasks
        db._ensure_scheduled_tasks_table(conn)
        for task_id, focus, user_id in [
            ("t1", "bjorn task", BJORN_ID),
            ("t2", "mikkel task", MIKKEL_ID),
        ]:
            try:
                conn.execute(
                    "INSERT INTO scheduled_tasks "
                    "(task_id, focus, source, status, run_at, created_at, updated_at, "
                    "scheduled_for_user_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (task_id, focus, "jarvis-tool", "pending",
                     "2026-01-01", "2026-01-01", "2026-01-01", user_id),
                )
            except sqlite3.IntegrityError:
                pass

    return db


def test_chronicle_filter_for_member_user(mu_db):
    """Mikkel sees Jarvis-general (NULL) and Mikkel-tagged, not Bjørn-tagged."""
    from core.identity.workspace_context import set_context, reset_context
    from core.services.cognitive_chronicle import query_chronicle_for_user

    token = set_context(workspace_name="mikkel", user_id=MIKKEL_ID)
    try:
        rows = query_chronicle_for_user()
        ids = {r["entry_id"] for r in rows}
        assert "c1" in ids, "missing untagged Jarvis-general entry"
        assert "c3" in ids, "missing Mikkel-tagged entry"
        assert "c2" not in ids, "leaked Bjørn-tagged entry to Mikkel"
    finally:
        reset_context(token)


def test_chronicle_filter_for_owner(mu_db):
    """Bjørn sees Jarvis-general + Bjørn-tagged (not Mikkel's by default)."""
    from core.identity.workspace_context import set_context, reset_context
    from core.services.cognitive_chronicle import query_chronicle_for_user

    token = set_context(workspace_name="bjorn", user_id=BJORN_ID)
    try:
        rows = query_chronicle_for_user()
        ids = {r["entry_id"] for r in rows}
        assert "c1" in ids
        assert "c2" in ids
        assert "c3" not in ids, "Bjørn should not see Mikkel's chronicle in normal context"
    finally:
        reset_context(token)


def test_scheduled_tasks_filtered_by_user(mu_db):
    """Mikkel's scheduled-task list only contains his own."""
    from core.identity.workspace_context import set_context, reset_context
    from core.services.scheduled_tasks import list_pending_for_current_user

    token = set_context(workspace_name="mikkel", user_id=MIKKEL_ID)
    try:
        tasks = list_pending_for_current_user()
        task_ids = {t["task_id"] for t in tasks}
        assert "t2" in task_ids
        assert "t1" not in task_ids
    finally:
        reset_context(token)


def test_initiatives_filtered_by_relevant_to_users(mu_db):
    """Mikkel only sees untagged initiatives and his own — not Bjørn's."""
    import json
    from core.identity.workspace_context import set_context, reset_context

    db = mu_db
    with db.connect() as conn:
        db._ensure_runtime_initiatives_table(conn)
        # Run the multiuser column migration so relevant_to_users exists
        db._ensure_multiuser_columns(conn)

        for initiative_id, focus, relevant_to_users in [
            ("i1", "jarvis-general initiative", None),
            ("i2", "bjorn initiative", json.dumps([BJORN_ID])),
            ("i3", "mikkel initiative", json.dumps([MIKKEL_ID])),
        ]:
            try:
                conn.execute(
                    "INSERT INTO runtime_initiatives "
                    "(initiative_id, focus, detected_at, updated_at, relevant_to_users) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (initiative_id, focus, "2026-01-01T00:00:00Z",
                     "2026-01-01T00:00:00Z", relevant_to_users),
                )
            except Exception:
                pass  # row already exists

    token = set_context(workspace_name="mikkel", user_id=MIKKEL_ID)
    try:
        rows = db.list_runtime_initiatives(limit=50)
        ids = {r["initiative_id"] for r in rows}
        assert "i1" in ids, "missing untagged Jarvis-general initiative"
        assert "i3" in ids, "missing Mikkel-tagged initiative"
        assert "i2" not in ids, "leaked Bjørn-tagged initiative to Mikkel"
    finally:
        reset_context(token)
