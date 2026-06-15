"""Verificér at de un-integrerede ports er tydeligt deprecerings-markeret
(liveness-audit 2026-06-15). Doc-only ændring — denne test fanger hvis markøren
fjernes ved et uheld, så de ikke igen forveksles med live systemer."""
import core.services.epistemics as epistemics
import core.services.missions_pipeline as missions_pipeline
import core.services.negotiation_pipeline as negotiation_pipeline


def test_epistemics_marked_unintegrated():
    assert "UN-INTEGRERET PORT" in (epistemics.__doc__ or "")


def test_missions_marked_unintegrated():
    assert "UN-INTEGRERET PORT" in (missions_pipeline.__doc__ or "")


def test_negotiation_marked_unintegrated():
    assert "UN-INTEGRERET PORT" in (negotiation_pipeline.__doc__ or "")
