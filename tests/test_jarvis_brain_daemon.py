"""Tests for core/services/jarvis_brain_daemon.py — background loops."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import pytest


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    yield jarvis_brain


def test_reindex_picks_up_new_file(isolated):
    from core.services.jarvis_brain_daemon import reindex_once
    fakta_dir = isolated.brain_dir() / "fakta"
    fakta_dir.mkdir(parents=True, exist_ok=True)
    eid = isolated.new_brain_id()
    md = (
        "---\n"
        f"id: {eid}\n"
        "kind: fakta\nvisibility: personal\ndomain: d\n"
        "title: Manual\ncreated_at: 2026-05-02T10:00:00+00:00\n"
        "updated_at: 2026-05-02T10:00:00+00:00\n"
        "salience_base: 1.0\nsalience_bumps: 0\nstatus: active\n"
        "trigger: spontaneous\n"
        "---\n\nbody\n"
    )
    (fakta_dir / "manual.md").write_text(md, encoding="utf-8")
    n = reindex_once()
    assert n >= 1
    e = isolated.read_entry(eid)
    assert e.title == "Manual"


def test_reindex_idempotent(isolated):
    from core.services.jarvis_brain_daemon import reindex_once
    isolated.write_entry(kind="fakta", title="X", content="y",
                          visibility="personal", domain="d")
    reindex_once()
    n = reindex_once()  # second pass: no file changes
    assert n == 0


def test_reindex_embeds_pending(isolated, monkeypatch):
    import numpy as np
    from core.services.jarvis_brain_daemon import reindex_once
    monkeypatch.setattr(isolated, "_embed_text",
                        lambda t: np.array([1.0, 2.0, 3.0], dtype=np.float32))
    isolated.write_entry(kind="fakta", title="X", content="y",
                          visibility="personal", domain="d")
    reindex_once()
    conn = isolated.connect_index()
    row = conn.execute(
        "SELECT embedding, embedding_dim FROM brain_index"
    ).fetchone()
    assert row[0] is not None
    assert row[1] == 3
    conn.close()


# --- Task 12: duplicate detection (consolidation phase 1) ---


def test_dedup_detects_high_similarity(isolated, monkeypatch):
    import numpy as np
    from core.services.jarvis_brain_daemon import find_duplicate_proposals

    def fake(text):
        if "alpha" in text.lower():
            return np.array([1.0, 0.0, 0.0], dtype=np.float32)
        if "beta" in text.lower():
            return np.array([0.99, 0.05, 0.0], dtype=np.float32)  # cos~0.997
        return np.array([0.0, 0.0, 1.0], dtype=np.float32)

    monkeypatch.setattr(isolated, "_embed_text", fake)
    a = isolated.write_entry(kind="fakta", title="Alpha", content="alpha details",
                              visibility="personal", domain="d")
    b = isolated.write_entry(kind="fakta", title="Beta", content="beta details",
                              visibility="personal", domain="d")
    isolated.embed_pending_entries()
    pairs = find_duplicate_proposals(threshold=0.92)
    assert len(pairs) == 1
    assert {pairs[0][0], pairs[0][1]} == {a, b}


def test_dedup_skips_low_similarity(isolated, monkeypatch):
    import numpy as np
    from core.services.jarvis_brain_daemon import find_duplicate_proposals

    def fake(text):
        if "alpha" in text.lower():
            return np.array([1.0, 0.0, 0.0], dtype=np.float32)
        return np.array([0.0, 1.0, 0.0], dtype=np.float32)

    monkeypatch.setattr(isolated, "_embed_text", fake)
    isolated.write_entry(kind="fakta", title="Alpha", content="alpha",
                          visibility="personal", domain="d")
    isolated.write_entry(kind="fakta", title="Beta", content="beta",
                          visibility="personal", domain="d")
    isolated.embed_pending_entries()
    pairs = find_duplicate_proposals(threshold=0.92)
    assert pairs == []


def test_dedup_only_compares_within_target_kinds(isolated, monkeypatch):
    """Indsigt + reference er for individuelle — kun fakta og observation som default."""
    import numpy as np
    from core.services.jarvis_brain_daemon import find_duplicate_proposals

    def fake(text):
        return np.array([1.0, 0.0, 0.0], dtype=np.float32)

    monkeypatch.setattr(isolated, "_embed_text", fake)
    # Two indsigter — should NOT be flagged as dupes by default
    isolated.write_entry(kind="indsigt", title="A", content="a",
                          visibility="personal", domain="d")
    isolated.write_entry(kind="indsigt", title="B", content="b",
                          visibility="personal", domain="d")
    isolated.embed_pending_entries()
    pairs = find_duplicate_proposals(threshold=0.5)
    assert pairs == []
