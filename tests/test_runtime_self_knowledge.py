"""Tests for the runtime self-knowledge service."""
from __future__ import annotations


def test_self_knowledge_map_has_all_categories() -> None:
    """The self-knowledge map must have all five categories."""
    from apps.api.jarvis_api.services.runtime_self_knowledge import (
        build_runtime_self_knowledge_map,
    )

    knowledge = build_runtime_self_knowledge_map()

    assert "active_capabilities" in knowledge
    assert "approval_gated" in knowledge
    assert "passive_inner_forces" in knowledge
    assert "structural_constraints" in knowledge
    assert "unavailable_or_inactive" in knowledge
    assert "summary" in knowledge

    # Each category has items list and label
    for key in ["active_capabilities", "approval_gated", "passive_inner_forces",
                "structural_constraints", "unavailable_or_inactive"]:
        cat = knowledge[key]
        assert "items" in cat
        assert "label" in cat
        assert isinstance(cat["items"], list)


def test_structural_constraints_are_always_populated() -> None:
    """Structural constraints should always have items — they are fixed truths."""
    from apps.api.jarvis_api.services.runtime_self_knowledge import (
        build_runtime_self_knowledge_map,
    )

    knowledge = build_runtime_self_knowledge_map()
    constraints = knowledge["structural_constraints"]["items"]

    assert len(constraints) >= 5  # at least 5 structural truths

    # Verify key constraints exist
    constraint_ids = {item["id"] for item in constraints}
    assert "runtime-truth-outranks" in constraint_ids
    assert "no-hidden-execution" in constraint_ids
    assert "no-free-identity-writes" in constraint_ids
    assert "question-gated-not-execution" in constraint_ids
    assert "workspace-memory-separation" in constraint_ids
    assert "multi-entry-bounded-runtime" in constraint_ids
    assert "standing-orders-authority" in constraint_ids
    assert "tasks-not-flows" in constraint_ids
    assert "layered-memory-distinction" in constraint_ids

    # All constraints must be not-mutable
    for item in constraints:
        assert item["mutability"] == "not-mutable"


def test_active_capabilities_always_includes_core() -> None:
    """Active capabilities should always include at least session distillation."""
    from apps.api.jarvis_api.services.runtime_self_knowledge import (
        build_runtime_self_knowledge_map,
    )

    knowledge = build_runtime_self_knowledge_map()
    active = knowledge["active_capabilities"]["items"]
    active_ids = {item["id"] for item in active}

    assert "session-distillation" in active_ids
    assert "runtime-task-ledger" in active_ids
    assert "runtime-flow-ledger" in active_ids
    assert "runtime-hook-bridge" in active_ids
    assert "layered-memory" in active_ids


def test_approval_gated_includes_soul_identity() -> None:
    """SOUL.md/IDENTITY.md mutation should always be approval-gated."""
    from apps.api.jarvis_api.services.runtime_self_knowledge import (
        build_runtime_self_knowledge_map,
    )

    knowledge = build_runtime_self_knowledge_map()
    gated = knowledge["approval_gated"]["items"]
    gated_ids = {item["id"] for item in gated}

    assert "soul-identity-mutation" in gated_ids


def test_each_item_has_mutability_field() -> None:
    """Every item in every category must have a mutability field."""
    from apps.api.jarvis_api.services.runtime_self_knowledge import (
        build_runtime_self_knowledge_map,
    )

    knowledge = build_runtime_self_knowledge_map()

    for key in ["active_capabilities", "approval_gated", "passive_inner_forces",
                "structural_constraints", "unavailable_or_inactive"]:
        for item in knowledge[key]["items"]:
            assert "mutability" in item, f"Missing mutability in {key}: {item.get('id')}"
            assert item["mutability"] in {
                "usable", "approval-gated", "influential-not-mutable",
                "not-mutable", "not-currently-available",
            }, f"Bad mutability value in {key}: {item}"


def test_prompt_section_is_compact() -> None:
    """The prompt section should be compact and bounded."""
    from apps.api.jarvis_api.services.runtime_self_knowledge import (
        build_self_knowledge_prompt_section,
    )

    section = build_self_knowledge_prompt_section()

    # Should produce something (we always have active capabilities + constraints)
    assert section is not None
    assert "Runtime self-knowledge" in section
    assert "Structural:" in section

    # Should be compact — under 800 chars
    assert len(section) < 800, f"Section too long: {len(section)} chars"


def test_summary_overview_is_readable() -> None:
    """The summary overview should be a readable one-liner."""
    from apps.api.jarvis_api.services.runtime_self_knowledge import (
        build_runtime_self_knowledge_map,
    )

    knowledge = build_runtime_self_knowledge_map()
    overview = knowledge["summary"]["overview"]

    assert isinstance(overview, str)
    assert len(overview) > 0
    # Should contain counts
    assert "active capabilities" in overview or "approval-gated" in overview or "inner forces" in overview
