"""runtime_cognitive_conductor — LivingNeuron HUB 1: cognitive-frame observe-hub."""
import inspect
import core.services.runtime_cognitive_conductor as m


def test_hub_observe_present():
    # Frame'en fik en cache i 9590482b6; selve bygningen (og observe-kaldet) bor
    # nu i den ucachede funktion, som build_cognitive_frame kalder.
    src = inspect.getsource(m._build_cognitive_frame_uncached)
    assert "observe_hub" in src  # HUB 1 egress-fri central-observe
    assert "cognitive_conductor" in src


def test_module_imports():
    assert m is not None
