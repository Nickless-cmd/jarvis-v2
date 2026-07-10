"""Tests for runtime contract candidate workflow.

Dækker eligibility-gates for auto-apply af MEMORY.md candidates.
Tilføjet 2026-06-09 ifm. åbning af gate'en for high-confidence
single_session_pattern proposals (98% af proposed candidates var
gated bort fra dette specifikke filter).
"""
from __future__ import annotations


def _make_candidate(**overrides):
    base = {
        "target_file": "MEMORY.md",
        "candidate_type": "memory_promotion",
        "status": "proposed",
        "confidence": "high",
        "canonical_key": "workspace-memory:remembered-fact:llm-fact-abc123",
        "source_mode": "end_of_run_memory_consolidation",
        "source_kind": "runtime-derived-support",
        "evidence_class": "single_session_pattern",
        "candidate_id": "cand-test",
        "proposed_value": "- Test fact",
        "summary": "Test summary",
    }
    base.update(overrides)
    return base


def test_high_confidence_single_session_pattern_is_eligible(monkeypatch) -> None:
    """2026-06-09 fix: åbnede gate for høj-confidence single_session_pattern."""
    from core.identity.candidate_workflow import _memory_candidate_eligible_for_auto_apply
    from core.identity import candidate_workflow

    # Stub readiness — single_session_pattern proposals returnerer factual-memory
    # via _with_apply_readiness, men selve gate'n tjekker ikke readiness for
    # disse — duplicate-check er den eneste yderligere gate.
    monkeypatch.setattr(
        candidate_workflow,
        "candidate_apply_readiness",
        lambda c: {"apply_readiness": "medium", "apply_reason": "factual-memory"},
    )
    monkeypatch.setattr(
        candidate_workflow,
        "list_runtime_contract_candidates",
        lambda **kwargs: [],
    )

    candidate = _make_candidate()
    assert _memory_candidate_eligible_for_auto_apply(candidate) is True


def test_low_confidence_single_session_pattern_not_eligible(monkeypatch) -> None:
    """Lavere confidence forbliver gated — vi vil ikke flushe larm."""
    from core.identity.candidate_workflow import _memory_candidate_eligible_for_auto_apply
    from core.identity import candidate_workflow

    monkeypatch.setattr(
        candidate_workflow,
        "candidate_apply_readiness",
        lambda c: {"apply_readiness": "medium", "apply_reason": "factual-memory"},
    )
    monkeypatch.setattr(
        candidate_workflow,
        "list_runtime_contract_candidates",
        lambda **kwargs: [],
    )

    candidate = _make_candidate(confidence="low")
    assert _memory_candidate_eligible_for_auto_apply(candidate) is False


def test_high_confidence_runtime_support_only_not_eligible(monkeypatch) -> None:
    """runtime_support_only er stadig gated — for løs evidens."""
    from core.identity.candidate_workflow import _memory_candidate_eligible_for_auto_apply
    from core.identity import candidate_workflow

    monkeypatch.setattr(
        candidate_workflow,
        "candidate_apply_readiness",
        lambda c: {"apply_readiness": "medium", "apply_reason": "factual-memory"},
    )
    monkeypatch.setattr(
        candidate_workflow,
        "list_runtime_contract_candidates",
        lambda **kwargs: [],
    )

    candidate = _make_candidate(evidence_class="runtime_support_only")
    assert _memory_candidate_eligible_for_auto_apply(candidate) is False


def test_non_llm_canonical_key_not_eligible_via_new_gate(monkeypatch) -> None:
    """Den nye gate kræver llm-* prefix — andre keys følger eksisterende paths."""
    from core.identity.candidate_workflow import _memory_candidate_eligible_for_auto_apply
    from core.identity import candidate_workflow

    monkeypatch.setattr(
        candidate_workflow,
        "candidate_apply_readiness",
        lambda c: {"apply_readiness": "low", "apply_reason": "other"},
    )
    monkeypatch.setattr(
        candidate_workflow,
        "list_runtime_contract_candidates",
        lambda **kwargs: [],
    )

    candidate = _make_candidate(
        canonical_key="workspace-memory:remembered-fact:hand-crafted-fact",
    )
    # Falls into the whitelist branch which it's not in → False
    assert _memory_candidate_eligible_for_auto_apply(candidate) is False


def test_duplicate_proposed_candidate_blocks_eligibility(monkeypatch) -> None:
    """Hvis en anden proposed/approved candidate har samme canonical_key,
    bliver den nye blokeret — undgår dobbelt-skriv."""
    from core.identity.candidate_workflow import _memory_candidate_eligible_for_auto_apply
    from core.identity import candidate_workflow

    monkeypatch.setattr(
        candidate_workflow,
        "candidate_apply_readiness",
        lambda c: {"apply_readiness": "medium", "apply_reason": "factual-memory"},
    )

    candidate = _make_candidate(candidate_id="cand-new")
    duplicate = _make_candidate(candidate_id="cand-existing", status="proposed")
    monkeypatch.setattr(
        candidate_workflow,
        "list_runtime_contract_candidates",
        lambda **kwargs: [duplicate],
    )

    assert _memory_candidate_eligible_for_auto_apply(candidate) is False


def test_memory_md_promotion_routes_to_curated_topic(isolated_runtime):
    """Vækst-værn (2026-07-10): MEMORY.md-linje-appends routes til curated-memory-
    topic'en, IKKE MEMORY.md — så identitets-kernen ikke vokser ukontrolleret."""
    from core.identity.candidate_workflow import _append_workspace_contract_line
    from core.memory.memory_topic_store import curated_path_for, read_topic_index
    from core.identity.workspace_bootstrap import workspace_memory_paths

    r = _append_workspace_contract_line(
        target_file="MEMORY.md", section_heading="## Curated Memory",
        content_line="En runtime-promoveret note.",
    )
    assert r["write_status"] == "written"
    assert r["path"].endswith("curated/curated-memory.md")
    # MEMORY.md selv er urørt
    mem = workspace_memory_paths()["curated_memory"]
    assert not (mem.exists() and "En runtime-promoveret note." in mem.read_text())
    # topic + index har den
    assert "En runtime-promoveret note." in curated_path_for("curated-memory").read_text()
    assert "curated/curated-memory.md" in read_topic_index()


def test_user_md_still_writes_directly(isolated_runtime):
    """Identitets-/præference-filer (USER.md) routes IKKE — kun MEMORY.md."""
    from core.identity.candidate_workflow import _append_workspace_contract_line
    r = _append_workspace_contract_line(
        target_file="USER.md", section_heading="## Durable Preferences",
        content_line="Foretrækker korte svar.",
    )
    assert r["path"].endswith("USER.md")
    assert r["write_status"] == "written"
