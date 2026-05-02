"""End-to-end smoke test for Jarvis Brain.

Skriv 5 entries via tool → reindex/embed → search returnerer dem →
salience bumpet → archive virker → summary genereres.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import hashlib
import numpy as np
import pytest


@pytest.fixture
def e2e(tmp_path, monkeypatch):
    from core.services import jarvis_brain
    from core.tools import jarvis_brain_tools
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")

    def fake(text):
        # Hash-based pseudo-embedding so each entry is distinct yet deterministic
        h = hashlib.md5(text.encode()).digest()[:12]
        v = np.frombuffer(h, dtype=np.uint8).astype(np.float32) / 255.0
        return v

    monkeypatch.setattr(jarvis_brain, "_embed_text", fake)
    # Reset rate-limit counters
    jarvis_brain_tools._turn_counts.clear()
    jarvis_brain_tools._day_counts.clear()
    yield jarvis_brain


def test_e2e_full_flow(e2e, monkeypatch):
    """Skriv → indeks → søg → bump → arkiver → summary regen."""
    from core.tools.jarvis_brain_tools import (
        remember_this, search_jarvis_brain, archive_brain_entry,
    )
    from core.services.jarvis_brain_daemon import (
        reindex_once, regenerate_summary,
    )
    from core.services import jarvis_brain

    # 1. Skriv 5 entries
    ids = []
    for i in range(5):
        r = remember_this(
            kind="fakta", title=f"Fakta {i}",
            content=f"Content {i} body text alpha beta gamma",
            visibility="personal", domain="engineering",
            session_id="s_e2e", turn_id=f"t_{i}",
        )
        assert r["status"] == "ok", r
        ids.append(r["id"])

    # 2. Reindex picks up files (already inserted by write_entry but reindex
    # is idempotent + ensures embedding is populated)
    reindex_once()

    # 3. Search returnerer mindst én match
    sr = search_jarvis_brain(
        query="fakta content body",
        session_visibility_ceiling="personal",
        limit=3,
    )
    assert sr["status"] == "ok"
    assert len(sr["results"]) >= 1

    # 4. Salience blev bumpet på de returnerede
    for hit in sr["results"]:
        e = jarvis_brain.read_entry(hit["id"])
        assert e.salience_bumps >= 1

    # 5. Archive en entry
    archive_res = archive_brain_entry(ids[0], reason="e2e archive test")
    assert archive_res["status"] == "ok"
    e0 = jarvis_brain.read_entry(ids[0])
    assert e0.status == "archived"

    # 6. Summary regenerering med stub LLM
    monkeypatch.setattr(
        "core.services.jarvis_brain_daemon._call_local_ollama",
        lambda prompt: {"summary": "**Engineering:** E2E test ran."},
    )
    n = regenerate_summary(target_visibility="personal")
    assert n >= 1
    summary_path = jarvis_brain._state_root() / "jarvis_brain_summary.md"
    assert summary_path.exists()
    assert "Engineering" in summary_path.read_text()


def test_e2e_visibility_gate_prevents_leakage(e2e, monkeypatch):
    """An intimate entry must NOT surface when ceiling is public_safe."""
    from core.tools.jarvis_brain_tools import remember_this, search_jarvis_brain
    from core.services.jarvis_brain_daemon import reindex_once

    r = remember_this(
        kind="fakta", title="Bjørn private", content="alpha intimate detail",
        visibility="intimate", domain="relations",
        session_id="s", turn_id="t1",
    )
    assert r["status"] == "ok"
    reindex_once()

    # Public_safe ceiling — intimate must not appear
    sr = search_jarvis_brain(
        query="alpha intimate",
        session_visibility_ceiling="public_safe",
        limit=5,
    )
    titles = [hit["title"] for hit in sr["results"]]
    assert "Bjørn private" not in titles
    # And hidden_by_visibility should report the masking
    assert sr["hidden_by_visibility"] >= 1


def test_e2e_supersede_chain(e2e):
    """Old entries marked superseded_by new entry; old fall out of active search."""
    from core.tools.jarvis_brain_tools import remember_this, search_jarvis_brain
    from core.services.jarvis_brain_daemon import reindex_once
    from core.services import jarvis_brain

    r1 = remember_this(kind="fakta", title="Old1", content="alpha old fact",
                       visibility="personal", domain="d",
                       session_id="s", turn_id="t1")
    r2 = remember_this(kind="fakta", title="New",
                       content="alpha refined fact, supersedes old",
                       visibility="personal", domain="d",
                       session_id="s", turn_id="t2")
    reindex_once()
    jarvis_brain.supersede(old_ids=[r1["id"]], new_id=r2["id"])

    e = jarvis_brain.read_entry(r1["id"])
    assert e.status == "superseded"
    assert e.superseded_by == r2["id"]

    # Default search (active only) excludes superseded
    sr = search_jarvis_brain(
        query="alpha", session_visibility_ceiling="personal", limit=5,
        include_archived=False,
    )
    ids = [hit["id"] for hit in sr["results"]]
    assert r1["id"] not in ids
