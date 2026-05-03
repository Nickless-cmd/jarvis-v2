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


def test_exec_remember_this_requires_runtime_context(isolated_brain):
    from core.tools.jarvis_brain_tools import _exec_remember_this

    res = _exec_remember_this({
        "kind": "fakta",
        "title": "X",
        "content": "Y",
        "visibility": "personal",
        "domain": "engineering",
    })

    assert res["status"] == "error"
    assert res["error"] == "context_missing"
    assert res["written"] is False


def test_exec_remember_this_uses_stable_runtime_turn_for_rate_limit(isolated_brain):
    from core.tools.jarvis_brain_tools import _exec_remember_this

    base_args = {
        "kind": "fakta",
        "content": "Y",
        "visibility": "personal",
        "domain": "engineering",
        "_runtime_session_id": "chat-1",
        "_runtime_turn_id": "run-1",
    }
    for i in range(5):
        res = _exec_remember_this({**base_args, "title": f"X{i}"})
        assert res["status"] == "ok"

    overflow = _exec_remember_this({**base_args, "title": "X6"})

    assert overflow["status"] == "error"
    assert overflow["error"] == "rate_limit_turn"


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


def test_remember_this_rejects_empty_content(isolated_brain):
    from core.tools.jarvis_brain_tools import remember_this
    res = remember_this(kind="fakta", title="X", content="   ",
                        visibility="personal", domain="d",
                        session_id="s1", turn_id="t1")
    assert res["status"] == "error"
    assert "content" in res.get("details", "")


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


# --- Task 10: archive + adopt/discard proposal tools ---


def test_archive_brain_entry_via_tool(isolated_brain):
    from core.tools.jarvis_brain_tools import remember_this, archive_brain_entry
    r = remember_this(kind="observation", title="O", content="c",
                      visibility="personal", domain="d",
                      session_id="s", turn_id="t1")
    res = archive_brain_entry(r["id"], reason="not relevant anymore")
    assert res["status"] == "ok"


def test_archive_brain_entry_returns_not_found(isolated_brain):
    from core.tools.jarvis_brain_tools import archive_brain_entry
    res = archive_brain_entry("brn_NONE", reason="x")
    assert res["status"] == "error"
    assert res["error"] == "not_found"


def _make_pending_proposal(jb, kind="fakta", visibility="personal", domain="d",
                            title="Proposal", content="Proposed body."):
    """Helper: write a pending proposal file + index row, return id."""
    pending_dir = jb.brain_dir() / "_pending"
    pending_dir.mkdir(parents=True, exist_ok=True)
    eid = jb.new_brain_id()
    e = jb.BrainEntry(
        id=eid, kind=kind, visibility=visibility, domain=domain,
        title=title, content=content,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        last_used_at=None, salience_base=1.0, salience_bumps=0,
        related=[], trigger="adopted_proposal", status="active",
        superseded_by=None, source_chronicle=None, source_url=None,
    )
    md = jb.render_entry_markdown(e)
    pending_path = pending_dir / f"{eid[-8:]}.md"
    pending_path.write_text(md, encoding="utf-8")
    conn = jb.connect_index()
    conn.execute(
        "INSERT INTO brain_proposals(id, path, reason, created_at, status) "
        "VALUES (?, ?, ?, ?, 'pending')",
        (eid, str(pending_path.relative_to(jb._workspace_root())),
         "test proposal", datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    return eid, pending_path


def test_adopt_brain_proposal_moves_file(isolated_brain):
    from core.tools.jarvis_brain_tools import adopt_brain_proposal
    eid, pending_path = _make_pending_proposal(isolated_brain)

    res = adopt_brain_proposal(eid)
    assert res["status"] == "ok", res
    # File is moved to fakta/-mappe
    assert not pending_path.exists()
    assert any((isolated_brain.brain_dir() / "fakta").glob("*.md"))


def test_adopt_brain_proposal_already_adopted_rejects(isolated_brain):
    from core.tools.jarvis_brain_tools import adopt_brain_proposal
    eid, _ = _make_pending_proposal(isolated_brain)
    first = adopt_brain_proposal(eid)
    assert first["status"] == "ok"
    second = adopt_brain_proposal(eid)
    assert second["status"] == "error"
    assert second["error"] == "not_pending"


def test_discard_brain_proposal(isolated_brain):
    from core.tools.jarvis_brain_tools import discard_brain_proposal
    eid, pending_path = _make_pending_proposal(isolated_brain)

    res = discard_brain_proposal(eid, reason="not useful")
    assert res["status"] == "ok"
    assert not pending_path.exists()
