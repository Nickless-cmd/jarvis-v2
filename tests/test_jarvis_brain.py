"""Tests for core/services/jarvis_brain.py — kerne CRUD-laget."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
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


# --- Task 3: SQLite schema + write_entry/read_entry ---


def test_brain_paths_resolves_from_workspace(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path)
    p = jarvis_brain.brain_dir()
    assert p == tmp_path / "default" / "jarvis_brain"


def test_ensure_index_creates_tables(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path)
    conn = jarvis_brain.connect_index()
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = {r[0] for r in rows}
    assert "brain_index" in names
    assert "brain_relations" in names
    assert "brain_proposals" in names
    conn.close()


def test_write_and_read_entry_roundtrip(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    new_id = jarvis_brain.write_entry(
        kind="fakta",
        title="Test fakta",
        content="En kort fakta.",
        visibility="personal",
        domain="engineering",
        trigger="spontaneous",
        related=[],
        source_url=None,
    )
    assert new_id.startswith("brn_")

    e = jarvis_brain.read_entry(new_id)
    assert e.title == "Test fakta"
    assert e.kind == "fakta"
    assert e.visibility == "personal"
    # File on disk in expected location
    p = tmp_path / "ws" / "default" / "jarvis_brain" / "fakta"
    md_files = list(p.glob("*.md"))
    assert len(md_files) == 1
    assert new_id[-8:] in md_files[0].name  # id_short in filename


def test_write_entry_inserts_relations(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    a = jarvis_brain.write_entry(
        kind="fakta", title="A", content="a", visibility="personal", domain="d",
    )
    b = jarvis_brain.write_entry(
        kind="fakta", title="B", content="b", visibility="personal", domain="d",
        related=[a],
    )
    conn = jarvis_brain.connect_index()
    rows = conn.execute(
        "SELECT from_id, to_id FROM brain_relations"
    ).fetchall()
    conn.close()
    assert (b, a) in rows


# --- Task 4: decay formula + bump_salience ---


def _make_entry(kind="fakta", bumps=0, base=1.0, last_used_days_ago=None):
    from core.services.jarvis_brain import BrainEntry
    now = datetime(2026, 5, 2, tzinfo=timezone.utc)
    last = (
        None
        if last_used_days_ago is None
        else now - timedelta(days=last_used_days_ago)
    )
    created = now - timedelta(days=last_used_days_ago or 0)
    return BrainEntry(
        id="brn_T", kind=kind, visibility="personal", domain="x",
        title="t", content="c",
        created_at=created, updated_at=now, last_used_at=last,
        salience_base=base, salience_bumps=bumps, related=[],
        trigger="spontaneous", status="active", superseded_by=None,
        source_chronicle=None, source_url=None,
    )


def test_effective_salience_no_decay_for_reference():
    from core.services.jarvis_brain import compute_effective_salience
    e = _make_entry(kind="reference", last_used_days_ago=3650)
    now = datetime(2026, 5, 2, tzinfo=timezone.utc)
    s = compute_effective_salience(e, now)
    assert s == pytest.approx(1.0, abs=0.01)


def test_effective_salience_observation_decays_by_e_at_14_days():
    from core.services.jarvis_brain import compute_effective_salience
    e = _make_entry(kind="observation", last_used_days_ago=14)
    now = datetime(2026, 5, 2, tzinfo=timezone.utc)
    s = compute_effective_salience(e, now)
    # exp(-14/14) = 1/e ≈ 0.368
    assert s == pytest.approx(0.368, abs=0.01)


def test_effective_salience_floor_never_below_002():
    from core.services.jarvis_brain import compute_effective_salience
    e = _make_entry(kind="observation", last_used_days_ago=10000)
    now = datetime(2026, 5, 2, tzinfo=timezone.utc)
    s = compute_effective_salience(e, now)
    assert s >= 0.02


def test_effective_salience_bumps_amplify_modestly():
    from core.services.jarvis_brain import compute_effective_salience
    now = datetime(2026, 5, 2, tzinfo=timezone.utc)
    e0 = _make_entry(kind="fakta", bumps=0, last_used_days_ago=0)
    e3 = _make_entry(kind="fakta", bumps=3, last_used_days_ago=0)
    s0 = compute_effective_salience(e0, now)
    s3 = compute_effective_salience(e3, now)
    # 3 bumps: 1 + 0.3*log2(4) = 1 + 0.6 = 1.6
    assert s3 / s0 == pytest.approx(1.6, abs=0.05)


def test_bump_salience_updates_index_and_file(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    new_id = jarvis_brain.write_entry(
        kind="fakta", title="X", content="y", visibility="personal",
        domain="d", trigger="spontaneous",
    )
    now = datetime(2026, 5, 2, 13, 0, tzinfo=timezone.utc)
    jarvis_brain.bump_salience(new_id, now=now)
    e = jarvis_brain.read_entry(new_id)
    assert e.salience_bumps == 1
    assert e.last_used_at is not None


# --- Task 5: embedding-based search ---


@pytest.fixture
def populated_brain(tmp_path, monkeypatch):
    """3 entries with deterministic stub embeddings (3-dim)."""
    import numpy as np
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")

    def fake_embed(text: str) -> np.ndarray:
        if "alpha" in text.lower():
            return np.array([1.0, 0.0, 0.0], dtype=np.float32)
        if "beta" in text.lower():
            return np.array([0.0, 1.0, 0.0], dtype=np.float32)
        return np.array([0.0, 0.0, 1.0], dtype=np.float32)
    monkeypatch.setattr(jarvis_brain, "_embed_text", fake_embed)

    a = jarvis_brain.write_entry(kind="fakta", title="Alpha thing",
                                  content="alpha details", visibility="personal", domain="x")
    b = jarvis_brain.write_entry(kind="fakta", title="Beta thing",
                                  content="beta details", visibility="public_safe", domain="x")
    c = jarvis_brain.write_entry(kind="indsigt", title="Gamma insight",
                                  content="gamma reflections", visibility="personal", domain="x")
    jarvis_brain.embed_pending_entries()
    return {"a": a, "b": b, "c": c}


def test_search_brain_returns_top_match_by_similarity(populated_brain):
    from core.services import jarvis_brain
    hits = jarvis_brain.search_brain(
        query_text="alpha lookup",
        kinds=["fakta"],
        visibility_ceiling="personal",
        limit=2,
    )
    assert len(hits) >= 1
    assert hits[0].id == populated_brain["a"]


def test_search_brain_filters_visibility(populated_brain):
    from core.services import jarvis_brain
    hits = jarvis_brain.search_brain(
        query_text="alpha lookup",
        kinds=["fakta"],
        visibility_ceiling="public_safe",
        limit=5,
    )
    # Alpha is personal → must NOT be in results
    ids = [h.id for h in hits]
    assert populated_brain["a"] not in ids
    assert populated_brain["b"] in ids


def test_search_brain_filters_kind(populated_brain):
    from core.services import jarvis_brain
    hits = jarvis_brain.search_brain(
        query_text="gamma",
        kinds=["fakta"],   # excludes indsigt
        visibility_ceiling="intimate",
        limit=5,
    )
    ids = [h.id for h in hits]
    assert populated_brain["c"] not in ids
