"""Smoke test for core.services.boundary_awareness.

Boundary awareness should expose the core self-model sections.

MÅLT 8/11-2026: `format_boundary_for_prompt` blev slettet. Den havde nul
produktionskaldere — kun denne test — og dens tekst var hardcodet
identitetsprosa, inklusive «Mellem ticks eksisterer du ikke», som ikke kan
maales. Den slags saetning hoerer ikke i en prompt som om den var sand.
Modulet selv lever: `build_boundary_awareness_surface` bruges af
`prompt_sections/formative_state.py` og af en API-rute.
"""

from core.services import boundary_awareness


def test_boundary_model_exposes_core_sections() -> None:
    model = boundary_awareness.build_boundary_model()

    assert {"body", "memory", "consciousness", "identity", "skills"} <= set(model)
    assert model["limits"]


def test_ingen_doed_prompt_funktion_genindfoeres() -> None:
    """Vagten: hardcodet identitetsprosa maa ikke snige sig ind som leverance."""
    assert not hasattr(boundary_awareness, "format_boundary_for_prompt")
