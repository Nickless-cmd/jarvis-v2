"""Tests for central_affect.classify_affect — struktur-deterministisk affekt-tagging.

Rådets #4: hver nerve-observation bærer en affektiv farve (tryk/varme/uro/ro).
Classifieren er self-safe: skør input → neutral ro, aldrig kast.
"""
from __future__ import annotations

from core.services.central_affect import (build_affect_surface,
                                          classify_affect)


def test_flag_maps_to_uro():
    a = classify_affect("agent", "run_error", "flag", 1, flagged=True)
    assert a["affect"] == "uro"
    assert 0.0 <= a["intensity"] <= 1.0


def test_error_nerve_maps_to_uro():
    a = classify_affect("tool", "exec_failure", "observe", 1.0)
    assert a["affect"] == "uro"


def test_incident_cluster_maps_to_uro():
    a = classify_affect("incident", "whatever", "observe", 1.0)
    assert a["affect"] == "uro"


def test_high_value_scalar_maps_to_tryk():
    a = classify_affect("cost", "daily", "observe", 42.0)
    assert a["affect"] == "tryk"


def test_pressure_nerve_maps_to_tryk():
    a = classify_affect("loop", "loop_pressure", "observe", 1.0)
    assert a["affect"] == "tryk"


def test_growth_nerve_maps_to_tryk():
    a = classify_affect("system", "growth_capacity", "observe", 1.0)
    assert a["affect"] == "tryk"


def test_gratitude_nerve_maps_to_varme():
    a = classify_affect("cognition", "gratitude_felt", "observe", 1.0)
    assert a["affect"] == "varme"


def test_cognition_stable_maps_to_varme():
    # positiv/stabil tilstand i et sjæls-cluster med lav skalar
    a = classify_affect("soul", "flourish", "observe", 0.0)
    assert a["affect"] == "varme"


def test_quiet_liveness_maps_to_ro():
    a = classify_affect("heartbeat", "liveness", "observe", 1.0)
    assert a["affect"] == "ro"


def test_self_safe_on_garbage_input():
    # ingen af argumenterne har den forventede type
    a = classify_affect(None, None, None, object())  # type: ignore[arg-type]
    assert a["affect"] == "ro"
    assert a["intensity"] == 0.0


def test_intensity_is_clamped_0_1():
    a = classify_affect("cost", "daily", "observe", 10_000_000.0)
    assert 0.0 <= a["intensity"] <= 1.0
    b = classify_affect("cost", "daily", "observe", -500.0)
    assert 0.0 <= b["intensity"] <= 1.0


def test_flag_intensity_default_half_when_non_numeric():
    a = classify_affect("agent", "err", "flag", "boom", flagged=True)
    assert a["intensity"] == 0.5


def test_observe_intensity_default_when_non_numeric():
    a = classify_affect("heartbeat", "liveness", "observe", "steady")
    assert a["intensity"] == 0.2


def test_return_shape_always_has_keys():
    a = classify_affect("x", "y", "observe", None)
    assert set(a.keys()) == {"affect", "intensity"}


# ── build_affect_surface ────────────────────────────────────────────────

def test_affect_surface_shape():
    surf = build_affect_surface()
    for k in ("tryk", "varme", "uro", "ro", "dominant"):
        assert k in surf
    assert isinstance(surf["dominant"], str)


def test_affect_surface_self_safe_on_records():
    # feeding explicit records computes a distribution + dominant
    recs = [
        {"affect": "uro"}, {"affect": "uro"}, {"affect": "ro"},
        {"affect": "varme"},
    ]
    surf = build_affect_surface(records=recs)
    assert surf["uro"] == 2
    assert surf["ro"] == 1
    assert surf["varme"] == 1
    assert surf["dominant"] == "uro"


def test_affect_surface_dominant_ro_when_empty():
    surf = build_affect_surface(records=[])
    assert surf["dominant"] == "ro"
    assert surf["tryk"] == surf["varme"] == surf["uro"] == surf["ro"] == 0
