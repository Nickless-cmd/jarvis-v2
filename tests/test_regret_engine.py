"""Task 5 (memory repair 2026-09-04): a regret with a lesson reaches the lessons store."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_open_or_update_regret_records_lesson():
    from core.services import regret_engine as re_

    captured: list[tuple[list[str], str]] = []
    fake_conn = MagicMock()
    fake_conn.__enter__.return_value = fake_conn
    fake_conn.execute.return_value.fetchone.return_value = None
    fake_conn.execute.return_value.lastrowid = 1
    with patch.object(re_, "_ensure_table", lambda: None), \
         patch.object(re_, "compute_regret_level", lambda **kw: 0.95), \
         patch.object(re_, "connect", lambda: fake_conn), \
         patch("core.services.lessons.record_review_lessons", lambda lessons, source: captured.append((list(lessons), source))):
        try:
            re_.open_or_update_regret(
                decision_id="d1", expected_outcome="deploy uden fejl", actual_outcome="crash ved boot",
                lesson="Verificér HEAD på CT105 før deploy",
            )
        except Exception:
            pass  # persistence details are mocked; the hook must have fired before them
    assert captured, "lesson hook not called"
    lessons, source = captured[0]
    assert source == "regret"
    assert "Verificér HEAD" in lessons[0] and "crash ved boot" in lessons[0]


def test_open_or_update_regret_without_lesson_records_nothing():
    from core.services import regret_engine as re_

    captured: list = []
    fake_conn = MagicMock()
    fake_conn.__enter__.return_value = fake_conn
    fake_conn.execute.return_value.fetchone.return_value = None
    with patch.object(re_, "_ensure_table", lambda: None), \
         patch.object(re_, "compute_regret_level", lambda **kw: 0.95), \
         patch.object(re_, "connect", lambda: fake_conn), \
         patch("core.services.lessons.record_review_lessons", lambda lessons, source: captured.append(1)):
        try:
            re_.open_or_update_regret(decision_id="d2", expected_outcome="a", actual_outcome="b", lesson="")
        except Exception:
            pass
    assert not captured
