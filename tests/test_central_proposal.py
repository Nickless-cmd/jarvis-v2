"""Tests for Spec B Fase B3+B4 — sprog-vækst-loop (word_needs) + NotationProposal-kontrakt."""
from __future__ import annotations

from core.services import central_lexicon as lx
from core.services import central_proposal as cp


# ── B3: sprog-vækst-loop ─────────────────────────────────────────────────────────────
def test_word_needs_merges_taxonomy_holes(isolated_runtime):
    """De genuint nye taksonomi-begreber dukker op som ord Centralen mangler (ceremoni-kandidater)."""
    needs = {w["name"] for w in lx.word_needs_for_ceremony()}
    assert {"truth", "council", "mutation"} <= needs      # taksonomi-huller
    assert "auth" not in needs and "memory" not in needs  # bundne udelades


# ── B4: NotationProposal-kontrakt (audit FØR anvendelse) ─────────────────────────────
def test_admissible_proposal_passes(isolated_runtime):
    """En parsebar, sigelig, konsistent notation-mutation er admissible (men IKKE anvendt)."""
    prop = cp.make_proposal(domain="model_router", notation="puls → fokus",
                            rationale="hurtig runtime → bedre fokus", existing=[])
    assert prop["admissible"] is True
    assert prop["applied"] is False                       # audit ≠ anvendelse


def test_unparseable_rejected():
    r = cp.audit_proposal("volapyk uden operator")
    assert r["ok"] is False and "uparsebar" in r["reasons"][0]


def test_unsayable_term_rejected():
    """Rå/ubundet begreb i notationen → afvist (ceremoni først, sproget gætter ikke)."""
    r = cp.audit_proposal("puls → sandhedX", existing=[])   # 'sandhedX' er ikke et kendt ord
    assert r["ok"] is False
    assert any("ikke et kendt ord" in reason for reason in r["reasons"])


def test_contradiction_is_rejected():
    """KERNE-VÆRDI: en mutation der modsiger hvad Centralen allerede tror bliver afvist model-frit."""
    existing = [{"id": "h1", "notation_il": "puls → fokus"}]     # Centralen tror puls → fokus
    r = cp.audit_proposal("puls → !fokus", existing=existing)    # forslag: puls → IKKE fokus
    assert r["ok"] is False
    assert r["new_contradictions"] and "puls" in r["new_contradictions"][0]["contradiction"]


def test_consistent_addition_allowed():
    existing = [{"id": "h1", "notation_il": "puls → fokus"}]
    r = cp.audit_proposal("fokus → ro", existing=existing)       # ingen konflikt
    assert r["ok"] is True and r["new_contradictions"] == []


def test_proposal_carries_domain_for_namespacing():
    """§8: domænet bæres med så en fremtidig gate_self_mutation kan namespaces korrekt."""
    prop = cp.make_proposal(domain="prompt_relevance", notation="kald → fokus", existing=[])
    assert prop["domain"] == "prompt_relevance"
