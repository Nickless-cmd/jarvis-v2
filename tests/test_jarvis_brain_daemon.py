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


# --- Task 13: contradiction detection (privacy-routed LLM) ---


class _Stub:
    def __init__(self, visibility, title="t", content="c"):
        self.visibility = visibility
        self.title = title
        self.content = content


def test_contradiction_pair_routes_to_local_for_intimate(monkeypatch):
    """If ANY entry is personal or intimate, free API MUST NOT be called."""
    from core.services import jarvis_brain_daemon as dmn
    free_called = {"n": 0}
    local_called = {"n": 0}

    def fake_free(prompt):
        free_called["n"] += 1
        return {"contradicts": False, "reason": "x"}

    def fake_local(prompt):
        local_called["n"] += 1
        return {"contradicts": False, "reason": "x"}

    monkeypatch.setattr(dmn, "_call_ollamafreeapi", fake_free)
    monkeypatch.setattr(dmn, "_call_local_ollama", fake_local)

    a = _Stub(visibility="intimate", content="a")
    b = _Stub(visibility="public_safe", content="b")
    dmn._llm_contradiction_check(a, b)
    assert free_called["n"] == 0
    assert local_called["n"] == 1


def test_contradiction_pair_uses_free_for_both_public(monkeypatch):
    from core.services import jarvis_brain_daemon as dmn
    free_called = {"n": 0}
    local_called = {"n": 0}

    def fake_free(prompt):
        free_called["n"] += 1
        return {"contradicts": False, "reason": "x"}

    def fake_local(prompt):
        local_called["n"] += 1
        return None

    monkeypatch.setattr(dmn, "_call_ollamafreeapi", fake_free)
    monkeypatch.setattr(dmn, "_call_local_ollama", fake_local)

    a = _Stub(visibility="public_safe", content="a")
    b = _Stub(visibility="public_safe", content="b")
    dmn._llm_contradiction_check(a, b)
    assert free_called["n"] == 1
    assert local_called["n"] == 0


def test_contradiction_personal_pair_also_routes_local(monkeypatch):
    from core.services import jarvis_brain_daemon as dmn
    free_called = {"n": 0}
    local_called = {"n": 0}
    monkeypatch.setattr(dmn, "_call_ollamafreeapi",
                        lambda p: free_called.update(n=free_called["n"] + 1))
    monkeypatch.setattr(dmn, "_call_local_ollama",
                        lambda p: local_called.update(n=local_called["n"] + 1))

    a = _Stub(visibility="personal", content="a")
    b = _Stub(visibility="public_safe", content="b")
    dmn._llm_contradiction_check(a, b)
    assert free_called["n"] == 0
    assert local_called["n"] == 1


# --- Task 14: theme consolidation kill-switch ---


def test_theme_consolidation_pauses_after_3_rejections(isolated, monkeypatch):
    from core.services import jarvis_brain_daemon as dmn
    monkeypatch.setattr(
        dmn, "_state_path",
        lambda: isolated._state_root() / "brain_daemon_state.json",
    )
    for i in range(3):
        dmn.record_proposal_rejection("theme", proposal_id=f"p{i}")
    assert dmn.is_theme_consolidation_paused() is True


def test_theme_consolidation_resets_on_acceptance(isolated, monkeypatch):
    from core.services import jarvis_brain_daemon as dmn
    monkeypatch.setattr(
        dmn, "_state_path",
        lambda: isolated._state_root() / "brain_daemon_state.json",
    )
    dmn.record_proposal_rejection("theme", proposal_id="p1")
    dmn.record_proposal_rejection("theme", proposal_id="p2")
    dmn.record_proposal_acceptance("theme", proposal_id="p3")
    dmn.record_proposal_rejection("theme", proposal_id="p4")
    assert dmn.is_theme_consolidation_paused() is False


def test_theme_consolidation_skipped_when_paused(isolated, monkeypatch):
    from core.services import jarvis_brain_daemon as dmn
    monkeypatch.setattr(
        dmn, "_state_path",
        lambda: isolated._state_root() / "brain_daemon_state.json",
    )
    monkeypatch.setattr(dmn, "is_theme_consolidation_paused", lambda: True)
    called = {"n": 0}
    monkeypatch.setattr(
        dmn, "_run_theme_consolidation_pass",
        lambda: called.update(n=called["n"] + 1) or 0,
    )
    dmn.run_theme_consolidation_if_active()
    assert called["n"] == 0


def test_resume_theme_consolidation_clears_state(isolated, monkeypatch):
    from core.services import jarvis_brain_daemon as dmn
    monkeypatch.setattr(
        dmn, "_state_path",
        lambda: isolated._state_root() / "brain_daemon_state.json",
    )
    for i in range(3):
        dmn.record_proposal_rejection("theme", proposal_id=f"p{i}")
    assert dmn.is_theme_consolidation_paused() is True
    dmn.resume_theme_consolidation()
    assert dmn.is_theme_consolidation_paused() is False


# --- Task 15: summary regeneration ---


def test_regenerate_summary_creates_file(isolated, monkeypatch):
    from core.services.jarvis_brain_daemon import regenerate_summary
    # Stub LLMs so the test is deterministic
    monkeypatch.setattr(
        "core.services.jarvis_brain_daemon._call_local_ollama",
        lambda prompt: {"summary": "**Engineering:** Jeg ved noget.\n"},
    )
    monkeypatch.setattr(
        "core.services.jarvis_brain_daemon._call_ollamafreeapi",
        lambda prompt: {"summary": "**Engineering:** Public version.\n"},
    )
    isolated.write_entry(kind="fakta", title="X", content="y",
                          visibility="personal", domain="engineering")
    n = regenerate_summary(target_visibility="personal")
    assert n >= 1
    out = isolated._state_root() / "jarvis_brain_summary.md"
    assert out.exists()
    assert "Engineering" in out.read_text(encoding="utf-8")


def test_summary_skipped_when_no_active_entries(isolated, monkeypatch):
    from core.services.jarvis_brain_daemon import regenerate_summary
    monkeypatch.setattr(
        "core.services.jarvis_brain_daemon._call_local_ollama",
        lambda prompt: pytest.fail("should not be called"),
    )
    n = regenerate_summary(target_visibility="personal")
    assert n == 0  # No entries → skip


def test_summary_routes_personal_to_local_ollama(isolated, monkeypatch):
    """personal target_visibility → local LLM only (privacy)."""
    from core.services.jarvis_brain_daemon import regenerate_summary
    free_called = {"n": 0}
    local_called = {"n": 0}
    monkeypatch.setattr(
        "core.services.jarvis_brain_daemon._call_local_ollama",
        lambda p: local_called.update(n=local_called["n"] + 1) or
                  {"summary": "**X:** y\n"},
    )
    monkeypatch.setattr(
        "core.services.jarvis_brain_daemon._call_ollamafreeapi",
        lambda p: free_called.update(n=free_called["n"] + 1) or
                  {"summary": "**X:** y\n"},
    )
    isolated.write_entry(kind="fakta", title="X", content="y",
                          visibility="personal", domain="d")
    regenerate_summary(target_visibility="personal")
    assert local_called["n"] == 1
    assert free_called["n"] == 0


def test_summary_filters_above_target_visibility(isolated, monkeypatch):
    """Intimate entries must NOT be in personal-targeted summary."""
    from core.services.jarvis_brain_daemon import regenerate_summary
    captured_prompts = []
    monkeypatch.setattr(
        "core.services.jarvis_brain_daemon._call_local_ollama",
        lambda p: captured_prompts.append(p) or {"summary": "x"},
    )
    monkeypatch.setattr(
        "core.services.jarvis_brain_daemon._call_ollamafreeapi",
        lambda p: {"summary": "x"},
    )
    isolated.write_entry(kind="fakta", title="public_thing", content="x",
                          visibility="public_safe", domain="d")
    isolated.write_entry(kind="fakta", title="intimate_thing", content="y",
                          visibility="intimate", domain="d")
    regenerate_summary(target_visibility="personal")
    assert len(captured_prompts) == 1
    prompt_text = captured_prompts[0]
    assert "public_thing" in prompt_text
    assert "intimate_thing" not in prompt_text


# --- Task 16: auto-archive + telemetry ---


def test_auto_archive_archives_old_low_salience(isolated, monkeypatch):
    from core.services.jarvis_brain_daemon import auto_archive_low_salience
    eid = isolated.write_entry(kind="observation", title="O", content="c",
                                visibility="personal", domain="d")
    # Patch compute_effective_salience → very low
    monkeypatch.setattr(isolated, "compute_effective_salience",
                        lambda e, now: 0.01)
    # Force last_used_at far back so days_low ≥ 90
    conn = isolated.connect_index()
    conn.execute(
        "UPDATE brain_index SET last_used_at = ? WHERE id = ?",
        ((datetime.now(timezone.utc) - timedelta(days=120)).isoformat(), eid),
    )
    conn.commit()
    conn.close()
    # And also set last_used_at in the file itself (read_entry uses file)
    e = isolated.read_entry(eid)
    e.last_used_at = datetime.now(timezone.utc) - timedelta(days=120)
    md = isolated.render_entry_markdown(e)
    fpath = isolated._workspace_root() / isolated._index_path_for(eid)
    isolated._atomic_write(fpath, md)

    n = auto_archive_low_salience()
    assert n == 1
    e2 = isolated.read_entry(eid)
    assert e2.status == "archived"


def test_auto_archive_skips_references(isolated, monkeypatch):
    from core.services.jarvis_brain_daemon import auto_archive_low_salience
    isolated.write_entry(kind="reference", title="R", content="c",
                          visibility="personal", domain="d")
    monkeypatch.setattr(isolated, "compute_effective_salience",
                        lambda e, now: 0.001)
    n = auto_archive_low_salience()
    assert n == 0


def test_auto_archive_skips_recent_entries(isolated, monkeypatch):
    from core.services.jarvis_brain_daemon import auto_archive_low_salience
    isolated.write_entry(kind="observation", title="O", content="c",
                          visibility="personal", domain="d")
    # Low salience but recent (created today) → days_low < 90 → skip
    monkeypatch.setattr(isolated, "compute_effective_salience",
                        lambda e, now: 0.01)
    n = auto_archive_low_salience()
    assert n == 0
