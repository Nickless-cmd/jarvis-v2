"""Coverage anchor for the Routine identity cutover module."""
from __future__ import annotations


def test_canonical_identity_target_is_stable_and_not_the_external_id() -> None:
    from core.services.routine_identity_migration import _canonical_id

    first = _canonical_id("123456789")
    assert first == _canonical_id("123456789")
    assert first != "123456789"
