from __future__ import annotations
import core.services.central_injection_registry as reg


def _use_store(monkeypatch):
    """Isolér kv i en dict så tests ikke rører rigtig runtime-state."""
    store: dict = {}
    monkeypatch.setattr(reg, "_kv_get", lambda k, d: store.get(k, d))
    monkeypatch.setattr(reg, "_kv_set", lambda k, v: store.update({k: v}))
    return store


def test_register_and_read_empty_when_never_composed(monkeypatch):
    _use_store(monkeypatch)
    reg._REGISTRY.clear()
    unit = reg.InjectionUnit(key="demo", source_nerves=(), threshold=0.1,
                             max_age_s=120.0, compose_fn=lambda: "hej")
    reg.register(unit)
    assert "demo" in reg.registered_keys()
    # Aldrig komponeret → hot-path læser tom streng (ALDRIG et compose-kald på læse-stien)
    assert reg.read_injection("demo") == ""
    assert reg.read_injection("ukendt") == ""
