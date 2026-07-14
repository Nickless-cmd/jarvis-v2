from core.runtime.db import connect, init_db


def test_costs_table_has_user_id_column():
    # init_db() runs the additive schema migration (CREATE/ALTER-if-missing,
    # idempotent) against the real runtime DB, same pattern as
    # tests/test_credit_assignment.py. The additive column must be present.
    init_db()
    with connect() as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(costs)")}
    assert "user_id" in cols
