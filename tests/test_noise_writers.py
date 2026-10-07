"""Task 3 (memory repair 2026-09-04): the noise writers are gated at the source."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

TEMPLATE_HMM = "I should keep carrying what helped around hmm. It still feels mere stabilt nu."
REAL = "I should keep carrying what helped around pfsense-nøglen flyttet til .env via env_override. It still feels mere stabilt nu."


# ── private layer promotion ─────────────────────────────────────────────


def test_record_private_retained_memory_record_skips_template():
    from core.runtime import db_private_signals as m

    fake_connect = MagicMock()
    with patch.object(m, "connect", fake_connect):
        m.record_private_retained_memory_record(
            record_id="r", source="s", run_id="run", work_id="w",
            retained_value=TEMPLATE_HMM, retained_kind="reinforced pattern",
            retention_scope="development", retention_horizon="persistent",
            confidence="high", created_at=datetime.now(UTC).isoformat(),
        )
    assert not fake_connect.called


def test_record_private_retained_memory_record_persists_real():
    from core.runtime import db_private_signals as m

    fake_connect = MagicMock()
    with patch.object(m, "connect", fake_connect), \
         patch.object(m, "get_private_retained_memory_record", return_value=None):
        m.record_private_retained_memory_record(
            record_id="r", source="s", run_id="run", work_id="w",
            retained_value=REAL, retained_kind="reinforced pattern",
            retention_scope="development", retention_horizon="persistent",
            confidence="high", created_at=datetime.now(UTC).isoformat(),
        )
    assert fake_connect.called


# ── MEMORY.md update proposals ──────────────────────────────────────────


def test_sentence_like_domain_keys_are_dropped():
    from core.services import memory_md_update_proposal_tracking as t

    assert t._looks_like_sentence("nej-check-lige-github-der-skulle-v-re-leake") is True
    assert t._looks_like_sentence("project-anchor") is False
    assert t._looks_like_sentence("repo-context") is False

    witness = {"items": [{
        "status": "fresh", "canonical_key": "witness:stable-context:det-er-fordi-du-prompt-er-rodet",
        "summary": "x", "confidence": "high", "support_summary": "", "signal_type": "witness",
    }]}
    with patch.object(t, "build_runtime_open_loop_signal_surface", return_value={"items": []}), \
         patch.object(t, "build_runtime_remembered_fact_signal_surface", return_value={"items": []}), \
         patch.object(t, "build_runtime_witness_signal_surface", return_value=witness):
        proposals = t._extract_memory_md_update_proposals()
    assert not [p for p in proposals if p.get("proposal_type") == "stable-context-update"]


def test_foldningen_afvaebner_saetnings_vagten_hvis_den_maales_bagefter():
    """Selve årsagen, pinnet uafhængigt af kaldestedet.

    `_domain_from_canonical_key` folder halen gennem `normalize_candidate_domain`
    for at samle to formuleringer af samme opgave i ét domæne — helt rimeligt for
    DET formål. Men foldningen fjerner småordene, og det er præcis dem
    `_looks_like_sentence` tæller på. Målt 2/10-2026:

        raa hale  det-er-fordi-du-prompt-er-rodet   7 dele → sætning
        foldet    fordi-prompt-rodet                3 dele → ikke sætning

    En hel brugerbesked slap derfor gennem vagten og blev et
    stabilt-kontekst-forslag. Denne test siger hvorfor rækkefølgen betyder noget,
    så den næste der folder noget opstrøms ikke genindfører hullet i stilhed.
    """
    from core.services import memory_md_update_proposal_tracking as t

    canonical = "witness:stable-context:det-er-fordi-du-prompt-er-rodet"
    raa = t._raw_tail_from_canonical_key(canonical)
    foldet = t._domain_from_canonical_key(canonical)

    assert raa == "det-er-fordi-du-prompt-er-rodet", raa
    assert len([p for p in foldet.split("-") if p]) < len([p for p in raa.split("-") if p]), (
        "foldningen fjerner ikke længere dele — så er præmissen for denne test væk"
    )
    assert t._looks_like_sentence(raa) is True, "vagten ser ikke sætningen i den rå hale"
    assert t._looks_like_sentence(foldet) is False, (
        "foldningen skjuler ikke længere sætningen — tjek om tærsklen er ændret"
    )


def test_refresh_marks_old_fresh_proposals_stale():
    from core.services import memory_md_update_proposal_tracking as t

    now = datetime.now(UTC)
    old = {"proposal_id": "old", "status": "fresh", "updated_at": (now - timedelta(days=8)).isoformat()}
    recent = {"proposal_id": "recent", "status": "fresh", "updated_at": (now - timedelta(days=3)).isoformat()}
    updated: list[str] = []

    def _update(pid, **kw):
        updated.append(pid)
        return {"proposal_id": pid, "status": kw.get("status")}

    with patch.object(t, "list_runtime_memory_md_update_proposals", return_value=[old, recent]), \
         patch.object(t, "update_runtime_memory_md_update_proposal_status", side_effect=_update), \
         patch.object(t.event_bus, "publish", lambda *a, **k: None):
        out = t.refresh_runtime_memory_md_update_proposal_statuses()
    assert updated == ["old"]
    assert out["stale_marked"] == 1


# ── generalized policies ────────────────────────────────────────────────


# ── experiential memories ───────────────────────────────────────────────


def test_experiential_memory_requires_a_lesson():
    from core.services import experiential_memory as em

    with patch.object(em, "insert_cognitive_experiential_memory") as ins, \
         patch.object(em.event_bus, "publish", lambda *a, **k: None):
        out = em.create_experiential_memory_from_run(
            run_id="r", user_message="check jarvis_bare experiment runner",
            assistant_response="ok", outcome_status="completed", user_mood="neutral",
        )
        assert out is None
        ins.assert_not_called()
        em.create_experiential_memory_from_run(
            run_id="r2", user_message="check jarvis_bare experiment runner",
            assistant_response="ok", outcome_status="failed", user_mood="neutral",
        )
        ins.assert_called_once()


# ── partner knowledge facts ─────────────────────────────────────────────


def test_theory_of_mind_skips_assistant_facts_in_autonomous_sessions_and_caps():
    from core.services import theory_of_mind as tom

    with patch.object(tom, "record_fact", return_value={"status": "inserted"}) as rf, \
         patch.object(tom, "_split_factual_sentences", return_value=["a b c d", "e f g h", "i j k l", "m n o p"]):
        assert tom.record_message(role="assistant", content="x", session_id="auto-heartbeat-20260904") == []
        rf.assert_not_called()
        out = tom.record_message(role="assistant", content="x", session_id="chat-abc")
        assert len(out) == 3
        assert rf.call_count == 3


# ── semantic indexer ────────────────────────────────────────────────────


def test_semantic_indexer_skips_released_private_brain():
    from core.services import semantic_indexer as si

    with patch("core.runtime.db.get_private_brain_record", return_value={"status": "released", "summary": "x y z"}), \
         patch("core.services.semantic_memory.index_memory") as idx:
        si._handle_private_brain({"record_id": "pb-1"})
        idx.assert_not_called()
    with patch("core.runtime.db.get_private_brain_record", return_value={"status": "active", "summary": "x y z"}), \
         patch("core.services.semantic_memory.index_memory") as idx:
        si._handle_private_brain({"record_id": "pb-2"})
        idx.assert_called_once()


def test_backfill_query_excludes_released():
    import inspect

    from core.services import semantic_memory as sm

    src = inspect.getsource(sm.backfill_all)
    assert "NOT IN ('released', 'archived', 'superseded', 'deleted')" in src


# ── continuity text ─────────────────────────────────────────────────────


def test_scrub_continuity_text_drops_telemetry():
    from core.services.session_distillation import _scrub_continuity_text

    raw = 'Diary synthesis: du har pfsense api key i din runtime + "stor hele" - "Current conductor mode: clarify" - "Most salient item: Visible run completed after tools: dbquery" - "tick quality trend: st" + No active runtime loop'
    out = _scrub_continuity_text(raw)
    assert "pfsense" in out
    assert "conductor" not in out
    assert "salient" not in out
    assert "No active runtime loop" in out
    assert _scrub_continuity_text("Current conductor mode: clarify") == ""
