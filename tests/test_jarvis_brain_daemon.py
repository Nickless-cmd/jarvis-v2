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
