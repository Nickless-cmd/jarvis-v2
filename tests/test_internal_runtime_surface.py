"""Tests for internal_runtime_surface — Fase C light builders (§24.4).

Verifies:
  - the 4 new Fase C builders are registered in _BUILDERS.
  - _light produces ONLY scalars (bool/int/float) + `_count`/`_keys`-tællere,
    never raw list/dict/text CONTENT → no private self-content can egress.
  - _light is self-safe on empty/non-dict input.
"""
from __future__ import annotations

import apps.api.jarvis_api.routes.internal_runtime_surface as irs


def test_phase_c_builders_registered():
    for name in ("open_loops", "runtime_awareness",
                 "runtime_self_knowledge", "counterfactual"):
        assert name in irs._BUILDERS, f"missing builder {name}"
        assert callable(irs._BUILDERS[name])


def test_light_only_scalars_and_counters():
    surface = {
        "active": True,
        "flag": False,
        "count": 7,
        "ratio": 0.5,
        "open_loops": [{"goal": "RAW SECRET GOAL"}, {"goal": "x"}],
        "signals": ("a", "b", "c"),
        "map": {"k1": "RAW", "k2": "RAW"},
        "text": "RAW PRIVATE TEXT",
    }
    light = irs._light(surface)
    assert light["liveness"] is True
    summary = light["summary"]

    # scalars kept as-is
    assert summary["active"] is True
    assert summary["flag"] is False
    assert summary["count"] == 7
    assert summary["ratio"] == 0.5
    # lists/tuples → count only
    assert summary["open_loops_count"] == 2
    assert summary["signals_count"] == 3
    # dict → key-count only
    assert summary["map_keys"] == 2
    # raw text string is DROPPED entirely (str is neither scalar-kept nor counted)
    assert "text" not in summary

    # EVERY value is a scalar — no raw content anywhere
    for v in summary.values():
        assert isinstance(v, (bool, int, float)), f"non-scalar leaked: {v!r}"
    flat = str(light)
    for leak in ("RAW SECRET GOAL", "RAW PRIVATE TEXT", "RAW"):
        assert leak not in flat, f"raw content leaked: {leak}"


def test_light_liveness_from_active_flag():
    assert irs._light({"active": True})["liveness"] is True
    assert irs._light({"active": False})["liveness"] is False
    # no explicit active → truthy default for a non-empty surface
    assert irs._light({"count": 1})["liveness"] is True


def test_light_self_safe_on_empty():
    assert irs._light({}) == {"liveness": False, "summary": {}}
    assert irs._light(None) == {"liveness": False, "summary": {}}  # type: ignore[arg-type]
    assert irs._light("nope") == {"liveness": False, "summary": {}}  # type: ignore[arg-type]
