from core.runtime.db import connect, init_db


def setup_module(_module):
    init_db()


def test_claude_dispatch_audit_table_exists():
    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='claude_dispatch_audit'"
        ).fetchall()
    assert len(rows) == 1


def test_claude_dispatch_budget_table_exists():
    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='claude_dispatch_budget'"
        ).fetchall()
    assert len(rows) == 1


def test_audit_table_has_required_columns():
    with connect() as conn:
        cols = {r[1] for r in conn.execute(
            "PRAGMA table_info(claude_dispatch_audit)"
        ).fetchall()}
    assert {
        "id", "task_id", "started_at", "ended_at", "spec_json",
        "status", "tokens_used", "exit_code", "diff_summary", "error",
    }.issubset(cols)


def test_budget_table_has_required_columns():
    with connect() as conn:
        cols = {r[1] for r in conn.execute(
            "PRAGMA table_info(claude_dispatch_budget)"
        ).fetchall()}
    assert {"hour_bucket", "dispatch_count", "tokens_used"}.issubset(cols)
