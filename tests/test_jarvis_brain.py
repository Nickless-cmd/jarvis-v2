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


# --- Task 2: frontmatter parse + atomic write ---


def test_parse_frontmatter_extracts_yaml_and_body(tmp_path):
    from core.services.jarvis_brain import parse_frontmatter
    p = tmp_path / "x.md"
    p.write_text(
        "---\nid: brn_X\nkind: fakta\ntitle: Test\n---\n\nThe body.\n",
        encoding="utf-8",
    )
    fm, body = parse_frontmatter(p)
    assert fm["id"] == "brn_X"
    assert fm["kind"] == "fakta"
    assert body.strip() == "The body."


def test_parse_frontmatter_raises_on_missing_delimiter(tmp_path):
    from core.services.jarvis_brain import parse_frontmatter
    p = tmp_path / "bad.md"
    p.write_text("no frontmatter here\n", encoding="utf-8")
    with pytest.raises(ValueError, match="frontmatter"):
        parse_frontmatter(p)


def test_atomic_write_creates_file(tmp_path):
    from core.services.jarvis_brain import _atomic_write
    p = tmp_path / "out.md"
    _atomic_write(p, "hello\n")
    assert p.read_text() == "hello\n"
    # tmp file is gone
    assert not (tmp_path / "out.md.tmp").exists()


def test_render_frontmatter_round_trips(tmp_path):
    from core.services.jarvis_brain import (
        BrainEntry,
        render_entry_markdown,
        parse_frontmatter,
        entry_from_frontmatter,
    )
    e = BrainEntry(
        id="brn_RT",
        kind="indsigt",
        visibility="personal",
        domain="engineering",
        title="Round Trip",
        content="The content body.",
        created_at=datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc),
        last_used_at=None,
        salience_base=1.0,
        salience_bumps=0,
        related=["brn_OTHER"],
        trigger="spontaneous",
        status="active",
        superseded_by=None,
        source_chronicle=None,
        source_url=None,
    )
    md = render_entry_markdown(e)
    p = tmp_path / "rt.md"
    p.write_text(md, encoding="utf-8")
    fm, body = parse_frontmatter(p)
    e2 = entry_from_frontmatter(fm, body)
    assert e2.id == e.id
    assert e2.related == ["brn_OTHER"]
    assert e2.content.strip() == "The content body."
