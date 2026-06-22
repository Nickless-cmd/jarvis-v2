"""Paritet for prompt_mutation_loop._check_target efter Mutation-cluster-routing.

_check_target rutes nu gennem gate_mutation (Centralen) for empty/traversal/protected/
whitelist; eksistens-tjek bliver lokalt. Eksakte fejlbeskeder bevaret. Listerne er
re-eksporteret fra den kanoniske kilde.
"""
from __future__ import annotations

import pytest

from core.services import prompt_mutation_loop as pml


def test_check_target_protected_raises():
    with pytest.raises(pml.PromptMutationError, match="protected"):
        pml._check_target("SOUL.md")


def test_check_target_not_evolvable_raises():
    with pytest.raises(pml.PromptMutationError, match="evolvable whitelist"):
        pml._check_target("RANDOM.md")


def test_check_target_empty_raises():
    with pytest.raises(pml.PromptMutationError, match="empty"):
        pml._check_target("")


def test_check_target_path_traversal_raises():
    with pytest.raises(pml.PromptMutationError, match="bare filename"):
        pml._check_target("../etc/passwd")


def test_lists_are_canonical_single_source():
    from core.services import gate_mutation as gm
    assert pml._PROTECTED_FILES is gm.PROTECTED_IDENTITY_FILES
    assert pml._EVOLVABLE_FILES is gm.EVOLVABLE_FILES
