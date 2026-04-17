"""Smoke test for core.services.boundary_awareness.

Boundary awareness should expose the core self-model sections and a prompt-ready
summary of those boundaries.
"""

from core.services import boundary_awareness


def test_boundary_model_exposes_core_sections_and_prompt_summary() -> None:
    model = boundary_awareness.build_boundary_model()
    prompt = boundary_awareness.format_boundary_for_prompt()

    assert {"body", "memory", "consciousness", "identity", "skills"} <= set(model)
    assert model["limits"]
    assert "databasen" in prompt
