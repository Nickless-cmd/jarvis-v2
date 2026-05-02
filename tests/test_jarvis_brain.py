"""Tests for core/services/jarvis_brain.py — kerne CRUD-laget."""
from __future__ import annotations
from datetime import datetime, timezone
import pytest


def test_brain_entry_required_fields():
    from core.services.jarvis_brain import BrainEntry
    e = BrainEntry(
        id="brn_TEST",
        kind="fakta",
        visibility="personal",
        domain="engineering",
        title="t",
        content="c",
        created_at=datetime(2026, 5, 2, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 2, tzinfo=timezone.utc),
        last_used_at=None,
        salience_base=1.0,
        salience_bumps=0,
        related=[],
        trigger="spontaneous",
        status="active",
        superseded_by=None,
        source_chronicle=None,
        source_url=None,
    )
    assert e.id == "brn_TEST"
    assert e.kind == "fakta"


def test_brain_entry_kind_enum_validated():
    from core.services.jarvis_brain import BrainEntry
    with pytest.raises(ValueError):
        BrainEntry(
            id="brn_X", kind="WRONG", visibility="personal", domain="x",
            title="t", content="c",
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
            last_used_at=None, salience_base=1.0, salience_bumps=0, related=[],
            trigger="spontaneous", status="active", superseded_by=None,
            source_chronicle=None, source_url=None,
        )


def test_brain_entry_visibility_enum_validated():
    from core.services.jarvis_brain import BrainEntry
    with pytest.raises(ValueError):
        BrainEntry(
            id="brn_X", kind="fakta", visibility="WRONG", domain="x",
            title="t", content="c",
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
            last_used_at=None, salience_base=1.0, salience_bumps=0, related=[],
            trigger="spontaneous", status="active", superseded_by=None,
            source_chronicle=None, source_url=None,
        )


def test_new_brain_id_format_and_uniqueness():
    from core.services.jarvis_brain import new_brain_id
    a = new_brain_id()
    b = new_brain_id()
    assert a.startswith("brn_")
    # Fallback gives 10 time chars + 16 random = 26; python-ulid's str is 26.
    assert len(a) == len("brn_") + 26
    assert a != b
