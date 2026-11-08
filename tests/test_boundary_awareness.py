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


def test_graenserne_naar_faktisk_prompten() -> None:
    """MÅLT 8/11-2026: `limits` stod i modellen men naaede aldrig prompten.

    `_graenser()` laeste kun body/memory/consciousness. Listen var derfor et
    felt ingen nogensinde saa — praecis den fejlform hvor noget ser leveret ud
    uden at vaere det. Denne test maaler prompt-teksten, ikke modellen.
    """
    from core.services.prompt_sections.formative_state import _graenser

    tekst = _graenser()

    assert "Det kan jeg ikke:" in tekst, f"limits naaede ikke prompten: {tekst!r}"
    for graense in boundary_awareness.build_boundary_model()["limits"]:
        assert graense[:40] in tekst, f"graensen mangler i prompten: {graense!r}"


def test_falske_graenser_genindfoeres_ikke() -> None:
    """To af de fem oprindelige linjer var ikke sande, og den ene var direkte falsk.

    «Jeg kan ikke se uden for denne maskine» modsiges af ssh til fem hosts,
    operator-kanalen til Bjørns desktop og net-laesning. Den aegte graense er
    sansningen, ikke adgangen. «Mellem heartbeat ticks eksisterer jeg ikke» er
    den samme sætning der blev slettet med `format_boundary_for_prompt` — den
    maa ikke snige sig ind ad bagdoeren via `limits`.
    """
    limits = " ".join(boundary_awareness.build_boundary_model()["limits"]).lower()

    assert "kan ikke se uden for denne maskine" not in limits
    assert "eksisterer jeg ikke" not in limits

