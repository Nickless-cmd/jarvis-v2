from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from core.services.decision_weight import classify_decision_weight


def test_read_operations_are_trivial():
    result = classify_decision_weight("read memory file")
    assert result["weight"] == 1
    assert result["label"] == "trivial"


def test_workspace_file_edit_is_moderate():
    result = classify_decision_weight("edit workspace/default/MEMORY.md")
    assert result["weight"] == 2
    assert result["label"] == "moderate"


def test_identity_change_is_significant():
    result = classify_decision_weight("modify identity soul file")
    assert result["weight"] == 3
    assert result["label"] == "significant"


def test_irreversible_action_is_critical():
    result = classify_decision_weight("permanently delete all memory irreversible")
    assert result["weight"] == 4
    assert result["label"] == "critical"


def test_returns_reason():
    result = classify_decision_weight("read file")
    assert isinstance(result["reason"], str)
    assert len(result["reason"]) > 0


def test_unknown_action_defaults_to_moderate():
    result = classify_decision_weight("do something completely unknown xyz")
    assert result["weight"] == 2
    assert result["label"] == "moderate"


def test_proposal_is_significant():
    result = classify_decision_weight("file autonomy proposal to promote memory")
    assert result["weight"] >= 3


def test_search_is_trivial():
    result = classify_decision_weight("search chat history for keywords")
    assert result["weight"] == 1
