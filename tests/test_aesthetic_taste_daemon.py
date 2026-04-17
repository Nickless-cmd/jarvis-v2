"""Tests for aesthetic taste daemon — motif-based activation."""
from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import core.services.aesthetic_taste_daemon as atd


def _reset():
    atd._accumulated_motifs = set()
    atd._seeded = False
    atd._latest_insight = ""
    atd._insight_history.clear()
    atd._last_insight_at = None
    atd._choice_log.clear()
    atd._choices_since_insight = 0


class TestMotifGate:
    def test_no_generate_with_fewer_than_3_motifs(self) -> None:
        _reset()
        atd._seeded = True
        atd._accumulated_motifs = {"clarity", "craft"}
        result = atd.tick_taste_daemon()
        assert result["generated"] is False

    def test_generates_with_3_or_more_motifs(self) -> None:
        _reset()
        atd._seeded = True
        atd._accumulated_motifs = {"clarity", "craft", "calm-focus"}
        with patch.object(atd, "_generate_insight", return_value="Jeg foretrækker klarhed."):
            with patch.object(atd, "_store_insight"):
                result = atd.tick_taste_daemon()
        assert result["generated"] is True

    def test_time_gate_blocks_within_30_min(self) -> None:
        _reset()
        atd._seeded = True
        atd._accumulated_motifs = {"clarity", "craft", "calm-focus"}
        atd._last_insight_at = datetime.now(UTC) - timedelta(minutes=10)
        result = atd.tick_taste_daemon()
        assert result["generated"] is False

    def test_time_gate_allows_after_30_min(self) -> None:
        _reset()
        atd._seeded = True
        atd._accumulated_motifs = {"clarity", "craft", "calm-focus"}
        atd._last_insight_at = datetime.now(UTC) - timedelta(minutes=35)
        with patch.object(atd, "_generate_insight", return_value="Smag ændrer sig."):
            with patch.object(atd, "_store_insight"):
                result = atd.tick_taste_daemon()
        assert result["generated"] is True


class TestSeedFromDB:
    def test_seed_loads_motifs(self) -> None:
        _reset()
        with patch("core.runtime.db.aesthetic_motif_log_unique_motifs", return_value=["clarity", "craft", "density"]):
            atd._seed_from_db()
        assert atd._accumulated_motifs == {"clarity", "craft", "density"}
        assert atd._seeded is True

    def test_seed_only_runs_once(self) -> None:
        _reset()
        atd._seeded = True
        atd._accumulated_motifs = {"clarity"}
        with patch("core.runtime.db.aesthetic_motif_log_unique_motifs", return_value=["a", "b", "c"]) as mock_db:
            atd._seed_from_db()
        mock_db.assert_not_called()
        assert atd._accumulated_motifs == {"clarity"}


class TestTasteSurface:
    def test_surface_includes_motif_data(self) -> None:
        _reset()
        atd._accumulated_motifs = {"clarity", "craft"}
        atd._last_insight_at = datetime(2026, 4, 13, 20, 30, tzinfo=UTC)
        with patch("core.runtime.db.aesthetic_motif_log_summary", return_value=[]):
            surface = atd.build_taste_surface()
        assert surface["unique_motif_count"] == 2
        assert "last_insight_at" in surface


class TestRecordChoiceRetained:
    def test_record_choice_still_works(self) -> None:
        _reset()
        atd.record_choice("work-steady", ["short", "direct"])
        assert len(atd._choice_log) == 1


class TestPrivateBrainRecord:
    def test_private_brain_record_written_on_store(self) -> None:
        _reset()
        atd._accumulated_motifs = {"clarity", "craft", "calm-focus"}
        with patch("core.services.aesthetic_taste_daemon.insert_private_brain_record") as mock_insert:
            atd._store_insight("Jeg vælger det kompakte.")
        mock_insert.assert_called_once()
        kwargs = mock_insert.call_args[1]
        assert kwargs["record_type"] == "taste-insight"
        assert kwargs["summary"] == "Jeg vælger det kompakte."
