"""Tests for db_governance_ledger — persistent governance mutation log."""
from __future__ import annotations

import json
from unittest.mock import patch

import core.runtime.db_governance_ledger as ledger


# ─── record_mutation + read_ledger ──────────────────────────────────────────

def test_record_and_read_roundtrip():
    """record_matement → read_ledger skal roundtrippe."""
    fake_db = []
    with patch.object(ledger, "_ensure_table"):
        with patch.object(ledger, "connect") as mock_connect:
            mock_conn = mock_connect.return_value.__enter__.return_value
            mock_conn.execute.side_effect = lambda sql, params=(): fake_db.append(
                {"sql": sql, "params": params}
            )
            ledger.record_mutation("governance", "test_flag", True)
    assert len(fake_db) == 1
    assert "INSERT INTO governance_ledger" in fake_db[0]["sql"]
    assert fake_db[0]["params"][0] == "governance"
    assert fake_db[0]["params"][1] == "test_flag"
    assert json.loads(fake_db[0]["params"][2]) is True


def test_record_mutation_serializes_complex_value():
    """Værdier som dicts skal JSON-serialiseres."""
    with patch.object(ledger, "_ensure_table"):
        with patch.object(ledger, "connect") as mock_connect:
            mock_conn = mock_connect.return_value.__enter__.return_value
            mock_conn.execute.side_effect = lambda sql, params=(): None
            ledger.record_mutation("healing", "config", {"nested": [1, 2, 3]})
    # Hvis ingen exception kastes, er testen bestået


def test_record_mutation_swallows_errors():
    """record_mutation må ALDRIG kaste — selv ved DB-fejl."""
    with patch.object(ledger, "_ensure_table", side_effect=RuntimeError("boom")):
        ledger.record_mutation("governance", "x", True)  # skal ikke kaste


# ─── read_ledger ─────────────────────────────────────────────────────────────

def test_read_ledger_returns_empty_on_error():
    """read_ledger skal returnere [] ved fejl, ikke kaste."""
    with patch.object(ledger, "_ensure_table", side_effect=RuntimeError("boom")):
        result = ledger.read_ledger()
    assert result == []


def test_read_ledger_with_area_filter():
    """read_ledger med area skal filtrere."""
    with patch.object(ledger, "_ensure_table"):
        with patch.object(ledger, "connect") as mock_connect:
            mock_conn = mock_connect.return_value.__enter__.return_value
            mock_conn.execute.return_value.fetchall.return_value = []
            ledger.read_ledger(area="governance", limit=10)
    sql_arg = mock_conn.execute.call_args[0][0]
    assert "WHERE area = ?" in sql_arg


def test_read_ledger_without_area():
    """read_ledger uden area skal hente alle."""
    with patch.object(ledger, "_ensure_table"):
        with patch.object(ledger, "connect") as mock_connect:
            mock_conn = mock_connect.return_value.__enter__.return_value
            mock_conn.execute.return_value.fetchall.return_value = []
            ledger.read_ledger(limit=50)
    sql_arg = mock_conn.execute.call_args[0][0]
    assert "WHERE area" not in sql_arg


# ─── summary ─────────────────────────────────────────────────────────────────

def test_summary_returns_empty_on_error():
    """summary skal returnere {} ved fejl."""
    with patch.object(ledger, "_ensure_table", side_effect=RuntimeError("boom")):
        result = ledger.summary()
    assert result == {}


# ─── _ensure_table ────────────────────────────────────────────────────────────

def test_ensure_table_swallows_errors():
    """_ensure_table må ikke kaste ved DB-fejl."""
    with patch.object(ledger, "connect", side_effect=RuntimeError("no db")):
        ledger._ensure_table()  # skal ikke kaste