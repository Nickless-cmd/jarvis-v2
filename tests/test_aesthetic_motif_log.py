"""Tests for aesthetic_motif_log DB operations."""
from __future__ import annotations

import sqlite3
from unittest.mock import patch, MagicMock

import pytest


def _make_in_memory_db():
    """Create an in-memory SQLite DB for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


class TestAestheticMotifLogTable:
    def test_insert_creates_row(self) -> None:
        from core.runtime import db
        conn = _make_in_memory_db()
        with patch.object(db, "connect") as mock_connect:
            mock_connect.return_value.__enter__ = lambda s: conn
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)
            db.aesthetic_motif_log_insert(source="somatic", motif="clarity", confidence=0.6)
        rows = conn.execute("SELECT * FROM aesthetic_motif_log").fetchall()
        assert len(rows) == 1
        assert rows[0]["source"] == "somatic"
        assert rows[0]["motif"] == "clarity"
        assert rows[0]["confidence"] == 0.6

    def test_unique_motifs_returns_distinct(self) -> None:
        from core.runtime import db
        conn = _make_in_memory_db()
        with patch.object(db, "connect") as mock_connect:
            mock_connect.return_value.__enter__ = lambda s: conn
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)
            db.aesthetic_motif_log_insert(source="somatic", motif="clarity", confidence=0.6)
            db.aesthetic_motif_log_insert(source="irony", motif="clarity", confidence=0.4)
            db.aesthetic_motif_log_insert(source="thought_stream", motif="craft", confidence=0.5)
            result = db.aesthetic_motif_log_unique_motifs()
        assert sorted(result) == ["clarity", "craft"]

    def test_unique_motifs_empty_when_no_data(self) -> None:
        from core.runtime import db
        conn = _make_in_memory_db()
        with patch.object(db, "connect") as mock_connect:
            mock_connect.return_value.__enter__ = lambda s: conn
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)
            # Force table creation
            db._ensure_aesthetic_motif_log_table(conn)
            result = db.aesthetic_motif_log_unique_motifs()
        assert result == []

    def test_summary_groups_by_motif(self) -> None:
        from core.runtime import db
        conn = _make_in_memory_db()
        with patch.object(db, "connect") as mock_connect:
            mock_connect.return_value.__enter__ = lambda s: conn
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)
            db.aesthetic_motif_log_insert(source="somatic", motif="clarity", confidence=0.6)
            db.aesthetic_motif_log_insert(source="irony", motif="clarity", confidence=0.8)
            db.aesthetic_motif_log_insert(source="thought_stream", motif="craft", confidence=0.5)
            result = db.aesthetic_motif_log_summary()
        assert len(result) == 2
        clarity = [r for r in result if r["motif"] == "clarity"][0]
        assert clarity["count"] == 2
        assert abs(clarity["avg_confidence"] - 0.7) < 0.01

    def test_summary_ordered_by_count_desc(self) -> None:
        from core.runtime import db
        conn = _make_in_memory_db()
        with patch.object(db, "connect") as mock_connect:
            mock_connect.return_value.__enter__ = lambda s: conn
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)
            db.aesthetic_motif_log_insert(source="a", motif="craft", confidence=0.5)
            for _ in range(3):
                db.aesthetic_motif_log_insert(source="b", motif="clarity", confidence=0.6)
            result = db.aesthetic_motif_log_summary()
        assert result[0]["motif"] == "clarity"
        assert result[1]["motif"] == "craft"
