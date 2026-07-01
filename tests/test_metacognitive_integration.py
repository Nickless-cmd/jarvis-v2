"""metacognitive_integration — Fase D graderet egress-fri kognitiv tier honorerer cognitive-flaget."""
import inspect
import core.services.metacognitive_integration as m


def test_tiered_autonomy_gate_present():
    src = inspect.getsource(m)
    # egress-fri kognitiv tier: skal honorere BÅDE fulde flag OG cognitive-flaget
    assert "generative_autonomy_cognitive_enabled" in src
    assert "generative_autonomy_enabled" in src


def test_module_imports():
    assert m is not None
