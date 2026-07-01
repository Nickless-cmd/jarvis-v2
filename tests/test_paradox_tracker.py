"""paradox_tracker — Fase C: surface delegerer til paradoxes_capture (ægte detektion)."""
import inspect
import core.services.paradox_tracker as m


def test_surface_delegates_to_capture():
    src = inspect.getsource(m.build_paradox_surface)
    assert "paradoxes_capture" in src
    out = m.build_paradox_surface()
    assert isinstance(out, dict) and "active" in out
