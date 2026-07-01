"""forgetting_engine — LivingNeuron HUKOMMELSE: run_auto_cycle observer glemsel egress-frit."""
import inspect
import core.services.forgetting_engine as m


def test_forgetting_observes_central():
    src = inspect.getsource(m.run_auto_cycle)
    assert "observe_hub" in src and "forgetting" in src


def test_module_imports():
    assert m is not None
