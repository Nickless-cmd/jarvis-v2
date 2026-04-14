"""Tests for aesthetic motif accumulation from daemon output."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest


class TestAccumulateFromDaemon:
    def test_detects_and_stores_motifs(self) -> None:
        from apps.api.jarvis_api.services import aesthetic_sense

        mock_insert = MagicMock()
        with patch("core.runtime.db.aesthetic_motif_log_insert", mock_insert):
            signals = aesthetic_sense.accumulate_from_daemon(
                source="somatic",
                text="Alt er klart og roligt. En klar og clean fornemmelse.",
            )

        assert len(signals) >= 1
        assert any(s["motif"] == "clarity" for s in signals)
        assert mock_insert.call_count >= 1
        call_kwargs = mock_insert.call_args_list[0][1]
        assert call_kwargs["source"] == "somatic"

    def test_updates_taste_daemon_accumulated_motifs(self) -> None:
        import apps.api.jarvis_api.services.aesthetic_taste_daemon as atd
        from apps.api.jarvis_api.services import aesthetic_sense

        atd._accumulated_motifs = set()
        mock_insert = MagicMock()
        with patch("core.runtime.db.aesthetic_motif_log_insert", mock_insert):
            aesthetic_sense.accumulate_from_daemon(
                source="irony",
                text="Elegant og polished, vellavet håndværk.",
            )

        assert "craft" in atd._accumulated_motifs

    def test_returns_empty_for_no_motifs(self) -> None:
        from apps.api.jarvis_api.services import aesthetic_sense

        mock_insert = MagicMock()
        with patch("core.runtime.db.aesthetic_motif_log_insert", mock_insert):
            signals = aesthetic_sense.accumulate_from_daemon(
                source="somatic",
                text="Hej verden, jeg er her.",
            )

        assert signals == []
        mock_insert.assert_not_called()

    def test_no_db_write_on_empty_signals(self) -> None:
        from apps.api.jarvis_api.services import aesthetic_sense

        mock_insert = MagicMock()
        with patch("core.runtime.db.aesthetic_motif_log_insert", mock_insert):
            aesthetic_sense.accumulate_from_daemon(
                source="thought_stream",
                text="Zzz qqq xxx yyy.",
            )

        mock_insert.assert_not_called()
