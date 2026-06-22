"""Paritet for auto_improvement_proposer._is_safe_target efter Mutation-cluster-routing.

_is_safe_target rutes nu gennem gate_mutation (Centralen); samme bool-svar bevaret.
INFRASTRUCTURE_BLOCKED_MODULES er nu re-eksporteret fra den kanoniske kilde (single-source).
"""
from __future__ import annotations

from core.services import auto_improvement_proposer as aip


def test_is_safe_target_allows_identity_and_tools():
    # identitets-filer rutes via identity_mutation_log → sikre at foreslå her
    assert aip._is_safe_target("update SOUL.md") is True
    assert aip._is_safe_target("modify IDENTITY.md") is True
    assert aip._is_safe_target("change tool description") is True
    assert aip._is_safe_target("core.services.context_window_manager:baz") is True


def test_is_safe_target_blocks_infrastructure():
    assert aip._is_safe_target("core.services.auto_improvement_proposer:foo") is False
    assert aip._is_safe_target("core.services.plan_proposals:bar") is False
    assert aip._is_safe_target("core.services.identity_mutation_log:x") is False
    assert aip._is_safe_target("core.services.approvals:y") is False
    assert aip._is_safe_target("core.runtime.policy:z") is False


def test_is_safe_target_empty_false():
    assert aip._is_safe_target("") is False


def test_infrastructure_list_is_canonical_single_source():
    from core.services import gate_mutation as gm
    assert aip._INFRASTRUCTURE_BLOCKED_MODULES is gm.INFRASTRUCTURE_BLOCKED_MODULES
