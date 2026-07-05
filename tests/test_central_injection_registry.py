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


def test_is_dirty_rules(monkeypatch):
    store = _use_store(monkeypatch)
    reg._REGISTRY.clear()
    nerves = {"cognition:affect": 1.0}
    monkeypatch.setattr(reg, "_nerve_latest", lambda n: nerves.get(n))
    unit = reg.InjectionUnit(key="u", source_nerves=("cognition:affect",),
                             threshold=0.5, max_age_s=100.0, compose_fn=lambda: "x")
    reg.register(unit)

    now = 1000.0
    # (a) aldrig komponeret → dirty
    assert reg.is_dirty(unit, now) is True

    store[reg._CACHE_PREFIX + "u"] = {"text": "x", "composed_at": now,
                                      "source_snapshot": {"cognition:affect": 1.0}}
    # (b) intet ændret, inden for max-alder → ren
    assert reg.is_dirty(unit, now + 10) is False
    # (c) over max-alder → dirty
    assert reg.is_dirty(unit, now + 101) is True
    # (d) nerve flytter sig over tærskel → dirty
    nerves["cognition:affect"] = 1.8   # delta 0.8 > 0.5
    assert reg.is_dirty(unit, now + 10) is True
    # (e) nerve flytter sig under tærskel → ren
    nerves["cognition:affect"] = 1.2   # delta 0.2 < 0.5
    assert reg.is_dirty(unit, now + 10) is False


def test_refresh_composes_and_caches(monkeypatch):
    store = _use_store(monkeypatch)
    reg._REGISTRY.clear()
    monkeypatch.setattr(reg, "_nerve_latest", lambda n: 2.0)
    calls = {"n": 0}
    def compose():
        calls["n"] += 1
        return f"tekst-{calls['n']}"
    unit = reg.InjectionUnit(key="u", source_nerves=("cognition:affect",),
                             threshold=0.5, max_age_s=100.0, compose_fn=compose)
    reg.register(unit)

    reg.refresh_dirty(now=1000.0)          # aldrig komponeret → komponér
    assert calls["n"] == 1
    assert reg.read_injection("u") == "tekst-1"
    blob = store[reg._CACHE_PREFIX + "u"]
    assert blob["source_snapshot"] == {"cognition:affect": 2.0}

    reg.refresh_dirty(now=1005.0)          # intet ændret, inden for max-alder → INGEN re-compose
    assert calls["n"] == 1


def test_refresh_is_self_safe_on_compose_error(monkeypatch):
    _use_store(monkeypatch)
    reg._REGISTRY.clear()
    monkeypatch.setattr(reg, "_nerve_latest", lambda n: None)
    def boom():
        raise RuntimeError("compose nede")
    reg.register(reg.InjectionUnit(key="bad", source_nerves=(), threshold=0.1,
                                   max_age_s=1.0, compose_fn=boom))
    reg.refresh_dirty(now=1.0)             # må ALDRIG kaste
    assert reg.read_injection("bad") == ""  # forblev tom


def test_injection_live_flag_defaults_off(monkeypatch):
    store = _use_store(monkeypatch)
    # Default OFF = hot-path bruger direkte build (sikker under udrulning)
    assert reg.injection_live("rule_conclusions") is False
    reg.set_injection_live("rule_conclusions", True)
    assert reg.injection_live("rule_conclusions") is True
    assert store[reg._LIVE_PREFIX + "rule_conclusions"] is True
    reg.set_injection_live("rule_conclusions", False)
    assert reg.injection_live("rule_conclusions") is False
