"""negotiation_engine — Fase C: surface delegerer til DB-backed negotiation_pipeline."""
import inspect
import core.services.negotiation_engine as m


def test_surface_delegates_to_pipeline():
    src = inspect.getsource(m.build_negotiation_surface)
    assert "negotiation_pipeline" in src  # delegering til den levende pipeline
    out = m.build_negotiation_surface()
    assert isinstance(out, dict) and "active" in out
