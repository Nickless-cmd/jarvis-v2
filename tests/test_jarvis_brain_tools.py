"""Tests for core/tools/jarvis_brain_tools.py — visible Jarvis' brain tools."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import pytest


@pytest.fixture
def isolated_brain(tmp_path, monkeypatch):
    """Isolate brain storage to tmp_path; reset rate-limit counters."""
    from core.services import jarvis_brain
    from core.tools import jarvis_brain_tools
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    # Reset module-level counters
    jarvis_brain_tools._turn_counts.clear()
    jarvis_brain_tools._day_counts.clear()
    yield jarvis_brain


def test_remember_this_creates_entry(isolated_brain):
    from core.tools.jarvis_brain_tools import remember_this
    res = remember_this(
        kind="fakta", title="X", content="Y", visibility="personal",
        domain="engineering", session_id="s1", turn_id="t1",
    )
    assert res["status"] == "ok"
    assert res["id"].startswith("brn_")


def test_remember_this_rejects_invalid_kind(isolated_brain):
    from core.tools.jarvis_brain_tools import remember_this
    res = remember_this(kind="WRONG", title="X", content="Y",
                        visibility="personal", domain="d",
                        session_id="s1", turn_id="t1")
    assert res["status"] == "error"
    assert "kind" in res.get("details", "")


def test_remember_this_rejects_invalid_visibility(isolated_brain):
    from core.tools.jarvis_brain_tools import remember_this
    res = remember_this(kind="fakta", title="X", content="Y",
                        visibility="WRONG", domain="d",
                        session_id="s1", turn_id="t1")
    assert res["status"] == "error"


def test_remember_this_rejects_empty_title(isolated_brain):
    from core.tools.jarvis_brain_tools import remember_this
    res = remember_this(kind="fakta", title="   ", content="Y",
                        visibility="personal", domain="d",
                        session_id="s1", turn_id="t1")
    assert res["status"] == "error"


def test_remember_this_rejects_oversize_content(isolated_brain):
    from core.tools.jarvis_brain_tools import remember_this
    res = remember_this(kind="fakta", title="X", content="x" * 5000,
                        visibility="personal", domain="d",
                        session_id="s1", turn_id="t1")
    assert res["status"] == "error"


def test_remember_this_per_turn_rate_limit(isolated_brain):
    from core.tools.jarvis_brain_tools import remember_this
    for i in range(5):
        r = remember_this(kind="fakta", title=f"T{i}", content=f"c{i}",
                          visibility="personal", domain="d",
                          session_id="s1", turn_id="t1")
        assert r["status"] == "ok"
    r6 = remember_this(kind="fakta", title="T6", content="c6",
                      visibility="personal", domain="d",
                      session_id="s1", turn_id="t1")
    assert r6["status"] == "error"
    assert r6["error"] == "rate_limit_turn"


def test_remember_this_per_day_rate_limit(isolated_brain, monkeypatch):
    from core.tools import jarvis_brain_tools
    base = datetime(2026, 5, 2, 10, 0, tzinfo=timezone.utc)
    # Simulate 4 turns same day, 5 each = 20 total
    for turn in range(4):
        for i in range(5):
            ts = base + timedelta(minutes=turn * 10 + i)
            monkeypatch.setattr(jarvis_brain_tools, "_now", lambda ts=ts: ts)
            r = jarvis_brain_tools.remember_this(
                kind="fakta", title=f"T{turn}-{i}", content="c",
                visibility="personal", domain="d",
                session_id="s1", turn_id=f"t{turn}",
            )
            assert r["status"] == "ok"
    # 21st call: day cap
    monkeypatch.setattr(jarvis_brain_tools, "_now",
                        lambda: base + timedelta(hours=2))
    r = jarvis_brain_tools.remember_this(
        kind="fakta", title="overflow", content="c",
        visibility="personal", domain="d",
        session_id="s1", turn_id="t99",
    )
    assert r["status"] == "error"
    assert r["error"] == "rate_limit_day"


# --- Task 9: search + read tools ---


@pytest.fixture
def stubbed_embedder(monkeypatch):
    import numpy as np
    from core.services import jarvis_brain

    def fake(text):
        if "alpha" in text.lower():
            return np.array([1.0, 0.0, 0.0], dtype=np.float32)
        if "beta" in text.lower():
            return np.array([0.0, 1.0, 0.0], dtype=np.float32)
        return np.array([0.0, 0.0, 1.0], dtype=np.float32)

    monkeypatch.setattr(jarvis_brain, "_embed_text", fake)


def test_search_jarvis_brain_returns_excerpts(isolated_brain, stubbed_embedder):
    from core.tools.jarvis_brain_tools import remember_this, search_jarvis_brain
    from core.services import jarvis_brain
    remember_this(kind="fakta", title="Alpha", content="alpha details here",
                  visibility="personal", domain="d", session_id="s", turn_id="t1")
    remember_this(kind="fakta", title="Beta", content="beta details here",
                  visibility="public_safe", domain="d", session_id="s", turn_id="t2")
    jarvis_brain.embed_pending_entries()

    res = search_jarvis_brain(
        query="alpha lookup", session_visibility_ceiling="personal", limit=3,
    )
    assert res["status"] == "ok"
    assert len(res["results"]) >= 1
    assert res["results"][0]["title"] == "Alpha"
    assert "excerpt" in res["results"][0]


def test_search_jarvis_brain_reports_hidden_count(isolated_brain, stubbed_embedder):
    from core.tools.jarvis_brain_tools import remember_this, search_jarvis_brain
    from core.services import jarvis_brain
    remember_this(kind="fakta", title="Alpha", content="alpha details",
                  visibility="intimate", domain="d", session_id="s", turn_id="t1")
    jarvis_brain.embed_pending_entries()

    res = search_jarvis_brain(
        query="alpha lookup", session_visibility_ceiling="public_safe", limit=5,
    )
    assert res["hidden_by_visibility"] >= 1


def test_read_brain_entry_returns_full_content(isolated_brain):
    from core.tools.jarvis_brain_tools import remember_this, read_brain_entry
    r = remember_this(kind="indsigt", title="Long",
                      content="The full body text here.",
                      visibility="personal", domain="d",
                      session_id="s", turn_id="t1")
    out = read_brain_entry(r["id"])
    assert out["status"] == "ok"
    assert out["entry"]["content"] == "The full body text here."


def test_read_brain_entry_returns_not_found(isolated_brain):
    from core.tools.jarvis_brain_tools import read_brain_entry
    out = read_brain_entry("brn_DOES_NOT_EXIST")
    assert out["status"] == "error"
    assert out["error"] == "not_found"
