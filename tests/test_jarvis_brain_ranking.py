"""Task 1 (memory repair 2026-09-04): brain ranking must not be hijacked by salience.

Root cause: `search_brain` recomputed effective salience inline WITHOUT the
importance ceiling that `compute_effective_salience` applies, so an entry with
17.794 bumps contributed 1.26 to a score whose cosine part maxes at 0.7 — the
same 11 entries won every query. Auto-inject bumped every turn, closing the loop.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import numpy as np
import pytest


@pytest.fixture
def brain(tmp_path, monkeypatch):
    from core.services import jarvis_brain

    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    return jarvis_brain


def _unit(direction: int) -> np.ndarray:
    v = np.zeros(768, dtype=np.float32)
    v[direction] = 1.0
    return v


def _write(brain, *, title: str, vec: np.ndarray, bumps: int, importance: float) -> str:
    now = datetime.now(timezone.utc)
    with patch.object(brain, "_embed_text", return_value=vec):
        entry_id = brain.write_entry(
            kind="fakta", visibility="personal", domain="test",
            title=title, content=f"{title} content", importance=importance,
        )
        brain.embed_pending_entries()
    conn = brain.connect_index()
    try:
        conn.execute(
            "UPDATE brain_index SET salience_bumps = ?, last_used_at = ? WHERE id = ?",
            (bumps, now.isoformat(), entry_id),
        )
        conn.commit()
    finally:
        conn.close()
    return entry_id


def test_relevant_entry_beats_runaway_salience(brain):
    """A (cos≈0.9, 0 bumps) must outrank B (cos≈0.4, 20 000 bumps, importance 0.8)."""
    q = np.zeros(768, dtype=np.float32)
    q[0] = 0.9
    q[1] = 0.436  # cos(q, e1) ≈ 0.44, cos(q, e0) ≈ 0.9
    a = _write(brain, title="relevant", vec=_unit(0), bumps=0, importance=0.8)
    b = _write(brain, title="runaway", vec=_unit(1), bumps=20_000, importance=0.8)

    with patch.object(brain, "_embed_text", return_value=q):
        results = brain.search_brain(query_text="anything", limit=2, use_temporal_boost=False)

    assert [e.id for e in results] == [a, b]


def test_search_effective_salience_is_capped_by_importance(brain):
    """Even with absurd bumps the salience term can never exceed importance."""
    q = _unit(0)
    _write(brain, title="capped", vec=_unit(0), bumps=50_000, importance=0.3)
    with patch.object(brain, "_embed_text", return_value=q):
        scored = brain.search_brain_scored(query_text="x", limit=1, use_temporal_boost=False)
    score, _eid = scored[0]
    # cos = 1.0 → 0.7 ; salience ≤ 0.3 → 0.09 ; total ≤ 0.79
    assert score <= 0.79 + 1e-6


def test_bump_salience_at_most_once_per_interval(brain):
    entry_id = _write(brain, title="bumpy", vec=_unit(0), bumps=0, importance=0.8)
    now = datetime.now(timezone.utc)
    brain.bump_salience(entry_id, now=now)
    brain.bump_salience(entry_id, now=now + timedelta(minutes=5))
    e = brain.read_entry(entry_id)
    assert e.salience_bumps == 1
    assert e.recall_count == 2
    brain.bump_salience(entry_id, now=now + timedelta(hours=25))
    assert brain.read_entry(entry_id).salience_bumps == 2


def test_tool_search_passes_cosine_floor(brain):
    from core.tools import jarvis_brain_tools

    captured: dict = {}

    def fake_search(**kwargs):
        captured.update(kwargs)
        return []

    with patch.object(brain, "search_brain", side_effect=fake_search):
        jarvis_brain_tools.search_jarvis_brain(query="pfsense nøgle", limit=5)
    assert captured.get("min_cosine") == pytest.approx(0.5)


def test_auto_inject_does_not_bump(brain):
    from unittest.mock import MagicMock

    from core.services.prompt_sections import jarvis_brain_facts as jbf

    fact = MagicMock()
    fact.id = "brn_X"
    fact.title = "t"
    fact.content = "c"
    with patch.object(brain, "search_brain", return_value=[fact]), \
         patch.object(brain, "bump_salience") as bump:
        out = jbf.build_brain_facts_section(user_message="hvad ved du om pfsense", session_id="s")
    assert "t" in out
    bump.assert_not_called()


def test_reset_salience_bumps_caps_file_and_index(brain):
    from scripts.brain_salience_reset import reset_salience_bumps

    hot = _write(brain, title="hot", vec=_unit(0), bumps=17_794, importance=0.8)
    cold = _write(brain, title="cold", vec=_unit(1), bumps=3, importance=0.8)
    # Mirror the bumps into the file (the file is truth) so the reset has to rewrite both.
    for eid, bumps in ((hot, 17_794), (cold, 3)):
        e = brain.read_entry(eid)
        e.salience_bumps = bumps
        brain._atomic_write(brain._workspace_root() / brain._index_path_for(eid),
                            brain.render_entry_markdown(e))

    changed = reset_salience_bumps(cap=20)
    assert changed == 1
    assert brain.read_entry(hot).salience_bumps == 20
    assert brain.read_entry(cold).salience_bumps == 3
    conn = brain.connect_index()
    try:
        row = conn.execute("SELECT salience_bumps FROM brain_index WHERE id = ?", (hot,)).fetchone()
    finally:
        conn.close()
    assert row[0] == 20
