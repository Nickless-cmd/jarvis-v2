"""Tests for core/services/central_brain_link.py — Tråd 5: jarvis-brain dybt koblet (scope-hærdet)."""
from __future__ import annotations

import contextlib

import pytest

from core.services import central_brain_link as bl


@pytest.fixture
def _owner_ctx(monkeypatch):
    """Giv recall en resolveret owner + en no-op user_context (users.json findes ikke i test)."""
    monkeypatch.setattr(bl, "_owner_uid", lambda: "1246415163603816499")
    @contextlib.contextmanager
    def _fake_ctx(**kw):
        yield None
    monkeypatch.setattr("core.identity.workspace_context.user_context", _fake_ctx)


def _seed_resolved(hyp_id="h1", outcome="supported", statement="memory forudsiger somatic"):
    from core.runtime.db import connect
    from core.services import central_hypothesis_generator as gen
    gen.ensure_schema()
    with connect() as c:
        c.execute(
            "INSERT INTO central_hypotheses (hyp_id, source, statement, prediction, null_hypothesis, "
            "success_criterion, sample_size, ttl_seconds, provenance_json, confidence, status, outcome, "
            "grounded_samples, created_at, resolved_at, notation_il) "
            "VALUES (?,?,?,?,?,?,?,?,?,?, 'resolved', ?, 5, '2026-07-02T00:00:00Z', "
            "'2026-07-02T01:00:00Z', ?)",
            (hyp_id, "causal_convergence", statement, "p", "n", "sc", 5, 3600, "{}", 0.8, outcome,
             "kontinuitet → krop"))
        c.commit()


# ── M1: recall er scope-BUNDET (hård exit-gate) ──────────────────────────────────────
def test_m1_scope_bounded(isolated_runtime, monkeypatch, _owner_ctx):
    """RÅDETS HÅRDE GRÆNSE: cadence-recall spørger ALDRIG private_brain — kun workspace+chronicle."""
    captured = {}
    def _fake_recall(*, query, sources, total_limit, with_mood):
        captured["sources"] = list(sources)
        return {"results": [{"source": "workspace", "text": "noget"}]}
    monkeypatch.setattr("core.services.memory_recall_engine.multi_signal_recall", _fake_recall)
    bl.recall_context("en formodning")
    assert "private_brain" not in captured["sources"]
    assert set(captured["sources"]) == {"workspace", "chronicle"}


def test_m1_no_recall_without_owner(isolated_runtime, monkeypatch):
    """SCOPE-GATE: uden resolveret owner sker INTET recall (aldrig ambient/ukendt kontekst)."""
    monkeypatch.setattr(bl, "_owner_uid", lambda: "")
    called = []
    monkeypatch.setattr("core.services.memory_recall_engine.multi_signal_recall",
                        lambda **k: called.append(1) or {"results": []})
    assert bl.recall_context("q") == []
    assert not called                             # recall-motoren blev end ikke kaldt


def test_m1_defense_in_depth_filters_private_brain(isolated_runtime, monkeypatch, _owner_ctx):
    """Selv HVIS en private_brain-række slap igennem, filtrerer recall_context den bort (dobbelt-værn)."""
    def _leaky(*, query, sources, total_limit, with_mood):
        return {"results": [{"source": "private_brain", "text": "hemmelig"},
                            {"source": "workspace", "text": "ok"}]}
    monkeypatch.setattr("core.services.memory_recall_engine.multi_signal_recall", _leaky)
    out = bl.recall_context("q")
    assert all(r["source"] != "private_brain" for r in out)


# ── M2: write er owner-scopet (hård exit-gate) ───────────────────────────────────────
def test_m2_write_scoped_refuses_without_owner(isolated_runtime, monkeypatch):
    """Ingen resolverbar owner → INGEN skrivning (cross-user-skrivning er værre end -læsning)."""
    monkeypatch.setattr(bl, "_owner_uid", lambda: "")
    out = bl.remember_resolved_hypothesis({"hyp_id": "h1", "statement": "x", "outcome": "supported"})
    assert out is None


def test_m2_write_happens_with_owner(isolated_runtime, monkeypatch):
    """Med resolveret owner → læringen skrives til jarvis_brain med source:brain_memory-markør."""
    monkeypatch.setattr(bl, "_owner_uid", lambda: "1246415163603816499")
    new_id = bl.remember_resolved_hypothesis(
        {"hyp_id": "h42", "statement": "memory forudsiger somatic", "outcome": "supported",
         "source": "causal_convergence", "notation_il": "kontinuitet → krop"})
    assert new_id
    assert bl.already_remembered("h42") is True
    # markøren er sat (så en fremtidig sampler kan sætte triggered_by=hyp_id, ikke world)
    from core.services.jarvis_brain import connect_index
    conn = connect_index()
    try:
        row = conn.execute("SELECT tags FROM brain_index WHERE id=?", (new_id,)).fetchone()
    finally:
        conn.close()
    assert "source:brain_memory" in row[0] and "central_hyp:h42" in row[0]


def test_m2_idempotent(isolated_runtime, monkeypatch):
    """Samme hypotese huskes ikke to gange (idempotens via tag)."""
    monkeypatch.setattr(bl, "_owner_uid", lambda: "owner1")
    h = {"hyp_id": "h7", "statement": "s", "outcome": "supported"}
    assert bl.remember_resolved_hypothesis(h)
    assert bl.remember_resolved_hypothesis(h) is None   # anden gang = no-op


# ── tick + surface ───────────────────────────────────────────────────────────────────
def test_tick_remembers_resolved(isolated_runtime, monkeypatch):
    monkeypatch.setattr(bl, "_owner_uid", lambda: "owner1")
    monkeypatch.setattr(bl, "recall_context", lambda q, **k: [])   # isolér M2 fra recall
    _seed_resolved(hyp_id="hz", outcome="supported")
    res = bl.run_brain_link_tick()
    assert res["status"] == "ok" and res["remembered"] >= 1
    surf = bl.build_brain_link_surface()
    assert surf["central_learnings_in_brain"] >= 1


def test_tick_self_safe_without_owner(isolated_runtime, monkeypatch):
    """Uden owner skriver ticken intet, men kaster ikke (observe-only, self-safe)."""
    monkeypatch.setattr(bl, "_owner_uid", lambda: "")
    _seed_resolved(hyp_id="hq")
    res = bl.run_brain_link_tick()
    assert res["status"] == "ok" and res["remembered"] == 0


def test_tick_caps_writes_per_tick(isolated_runtime, monkeypatch):
    """En batch nye resolutioner må ikke skrive mere end _MAX_WRITES_PER_TICK (timeout-værn)."""
    monkeypatch.setattr(bl, "_owner_uid", lambda: "owner1")
    monkeypatch.setattr(bl, "recall_context", lambda q, **k: [])
    # gør write billig+tællende så vi tester CAP-logikken, ikke embedding-latens
    writes: list = []
    def _fake_write(hyp):
        writes.append(hyp.get("hyp_id"))
        return "id-" + str(hyp.get("hyp_id"))
    monkeypatch.setattr(bl, "remember_resolved_hypothesis", _fake_write)
    for i in range(5):
        _seed_resolved(hyp_id=f"hc{i}")
    res = bl.run_brain_link_tick()
    assert res["remembered"] == bl._MAX_WRITES_PER_TICK   # cap'et
    assert len(writes) == bl._MAX_WRITES_PER_TICK          # loopet brød ved cap
