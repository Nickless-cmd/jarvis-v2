"""F4c udfylder denne; i F4b er notifikationen en no-op og maa aldrig kaste."""
from __future__ import annotations

from core.services import agent_approval_notify as N


def test_on_requested_is_a_safe_noop_for_now():
    assert N.on_requested({"approval_id": "appr-x"}) is None
