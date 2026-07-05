from __future__ import annotations
import core.services.central_injection_registry as reg
import core.services.central_injection_units as units


def test_default_units_registered():
    reg._REGISTRY.clear()
    units._REGISTERED = False
    units.register_default_units()
    keys = set(reg.registered_keys())
    assert {"rule_conclusions", "cognitive_state"} <= keys
    # idempotent
    units.register_default_units()
    assert len(reg.registered_keys()) == len(keys)


def test_pilot_units_have_callable_compose():
    reg._REGISTRY.clear(); units._REGISTERED = False
    units.register_default_units()
    for k in ("rule_conclusions", "cognitive_state"):
        u = reg._REGISTRY[k]
        assert callable(u.compose_fn)
        assert u.max_age_s > 0
