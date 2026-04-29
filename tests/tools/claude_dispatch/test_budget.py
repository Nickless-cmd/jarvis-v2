from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from core.tools.claude_dispatch.budget import (
    BudgetTracker, BudgetExceeded,
    MAX_DISPATCHES_PER_HOUR, MAX_TOKENS_PER_HOUR,
)


def _frozen_now():
    return datetime(2026, 4, 29, 14, 30, 0, tzinfo=timezone.utc)


def test_check_and_reserve_increments_count(tmp_dispatch_db):
    bt = BudgetTracker()
    with patch("core.tools.claude_dispatch.budget._now", _frozen_now):
        bt.check_and_reserve()
        bt.check_and_reserve()
        assert bt.current_dispatch_count() == 2


def test_check_and_reserve_blocks_after_max(tmp_dispatch_db):
    bt = BudgetTracker()
    with patch("core.tools.claude_dispatch.budget._now", _frozen_now):
        for _ in range(MAX_DISPATCHES_PER_HOUR):
            bt.check_and_reserve()
        with pytest.raises(BudgetExceeded, match="dispatches/hour"):
            bt.check_and_reserve()


def test_record_usage_blocks_when_token_quota_exceeded(tmp_dispatch_db):
    bt = BudgetTracker()
    with patch("core.tools.claude_dispatch.budget._now", _frozen_now):
        bt.check_and_reserve()
        bt.record_usage(MAX_TOKENS_PER_HOUR)
        with pytest.raises(BudgetExceeded, match="tokens/hour"):
            bt.check_and_reserve()
