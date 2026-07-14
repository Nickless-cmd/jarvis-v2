"""Tests for core/runtime/db_core.py — DB-forbindelse + concurrency-hærdning."""
from __future__ import annotations

from core.runtime.db import connect


def test_connect_sets_busy_timeout():
    # Rygrads-fix (1. jul): connect() skal sætte busy_timeout, så en låst DB VENTER
    # i stedet for at fejle øjeblikkeligt (OperationalError) — fixede eventbus-writer-fejl.
    with connect() as conn:
        val = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    assert int(val) >= 5000


def test_connect_row_factory():
    with connect() as conn:
        conn.row_factory  # sat til sqlite3.Row
        row = conn.execute("SELECT 1 AS x").fetchone()
    assert row["x"] == 1  # navngivet kolonne-adgang virker


def test_runtime_state_bool_string_off_reads_false():
    """Regression (2026-07-14, dispatch-master-switch): a boolean flag stored as
    the STRING "off" (fx via en CLI/migrations-sti) blev læst med bool(value).
    bool("off") er True — så agent_tools_enabled stod reelt TÆNDT trods intentionen.
    get_runtime_state_bool skal coerce string-repræsentationer korrekt: "off"/"false"
    /"no"/"0"/"" → False, "on"/"true"/"1"/"yes" → True, ægte bool passerer igennem."""
    from core.runtime.db_core import set_runtime_state_value, get_runtime_state_bool

    for stored, expected in [
        ("off", False), ("false", False), ("no", False), ("0", False), ("", False),
        ("on", True), ("true", True), ("yes", True), ("1", True),
        (True, True), (False, False), (1, True), (0, False),
    ]:
        set_runtime_state_value("_test_bool_flag", stored)
        got = get_runtime_state_bool("_test_bool_flag", False)
        assert got is expected, f"stored={stored!r}: forventede {expected}, fik {got}"

    # ukendt/absent nøgle → default
    assert get_runtime_state_bool("_test_absent_flag_xyz", False) is False
    assert get_runtime_state_bool("_test_absent_flag_xyz", True) is True
