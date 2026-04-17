"""Smoke test for core.services.runtime_action_registry.

The runtime action registry should expose the canonical action specs used by the
executive runtime and allow direct lookup by action id.
"""

from core.services import runtime_action_registry


def test_runtime_action_registry_lists_and_resolves_known_action() -> None:
    specs = runtime_action_registry.list_runtime_action_specs()
    inspect_spec = runtime_action_registry.get_runtime_action_spec(
        "inspect_repo_context"
    )

    assert specs
    assert any(spec.action_id == "inspect_repo_context" for spec in specs)
    assert inspect_spec is not None
    assert inspect_spec.requires_capability == "tool:run-non-destructive-command"
