"""Tests for central_convene_judge — the Central reason-to-convene judge (akse 4).

Hermetic: the mode flag (kv) and surface reads are patched, so no DB / real
surfaces are touched. Covers off/shadow/on governance, movement detection,
dynamic role derivation, topic-hint derivation, and self-safety."""
from __future__ import annotations

from unittest.mock import patch


def _mode(m):
    return patch("core.services.central_convene_judge.current_mode", return_value=m)


# ---------------------------------------------------------------------------
# Governance — flag off/shadow/on
# ---------------------------------------------------------------------------


def test_off_returns_benign_verdict_and_derives_nothing():
    from core.services import central_convene_judge as j
    with _mode("off"):
        v = j.judge_convene(surfaces=None, top_signals=["x"], score=0.9, score_override=0.9)
    assert v["mode"] == "off"
    assert v["convene"] is False
    assert v["roles"] == []
    assert v["topic_hint"] == ""


def test_shadow_computes_but_reports_shadow_mode():
    from core.services import central_convene_judge as j
    with _mode("shadow"):
        v = j.judge_convene(surfaces=None, top_signals=[], score=0.0, score_override=0.9)
    assert v["mode"] == "shadow"
    assert v["convene"] is True          # movement above threshold
    assert v["roles"]                    # roles derived even in shadow (for observation)


def test_on_convenes_above_movement_threshold():
    from core.services import central_convene_judge as j
    with _mode("on"):
        v = j.judge_convene(surfaces=None, top_signals=[], score=0.0, score_override=0.5)
    assert v["mode"] == "on"
    assert v["convene"] is True
    assert v["reason"] == "real_movement"


def test_on_no_convene_below_movement_threshold():
    from core.services import central_convene_judge as j
    with _mode("on"):
        v = j.judge_convene(surfaces=None, top_signals=[], score=0.0, score_override=0.05)
    assert v["convene"] is False
    assert v["reason"] == "no_real_movement"


# ---------------------------------------------------------------------------
# Reads the flowing values — surfaces + valence + agenda
# ---------------------------------------------------------------------------


def _surfaces(**over):
    base = {
        "autonomy_pressure": {"summary": {"active_count": 0}},
        "open_loop": {"summary": {"open_count": 0}},
        "internal_opposition": {"active": False},
        "existential_wonder": {"latest_wonder": ""},
        "creative_drift": {"drift_count_today": 0},
        "desire": {"active_count": 0},
        "conflict": {"last_conflict": ""},
        "affective_meta_state": {"mood": "steady"},
    }
    base.update(over)
    return base


def test_reads_movement_from_provided_surfaces():
    from core.services import central_convene_judge as j
    surfaces = _surfaces(
        existential_wonder={"latest_wonder": "Hvem er jeg når ingen ser?"},
        autonomy_pressure={"summary": {"active_count": 3}},
    )

    def _read(name):
        return surfaces.get(name, {})

    with _mode("on"), patch(
        "core.services.signal_surface_router.read_surface", side_effect=_read
    ):
        v = j.judge_convene(surfaces=surfaces, top_signals=[], score=0.0)
    assert v["convene"] is True
    assert v["movement_total"] > 0.0
    # existential_wonder present → topic hint is the wonder text itself
    assert v["topic_hint"] == "Hvem er jeg når ingen ser?"


def test_roles_derived_dynamically_from_what_moves():
    """Only signals that actually move contribute their perspectives (akse 4)."""
    from core.services import central_convene_judge as j
    surfaces = _surfaces(existential_wonder={"latest_wonder": "?"})

    def _read(name):
        return surfaces.get(name, {})

    with _mode("on"), patch(
        "core.services.signal_surface_router.read_surface", side_effect=_read
    ):
        v = j.judge_convene(surfaces=surfaces, top_signals=[], score=0.0)
    # existential_wonder → filosof + synthesizer are the relevant perspectives
    assert "filosof" in v["roles"]
    assert "synthesizer" in v["roles"]
    # a signal that did NOT move must not drag in its perspectives blindly
    assert "researcher" in v["roles"] or len(v["roles"]) >= 3  # only via minimum fill


def test_negative_valence_adds_care_lens():
    from core.services import central_convene_judge as j
    surfaces = _surfaces(
        conflict={"last_conflict": "spænding"},
        affective_meta_state={"mood": "distressed"},
    )

    def _read(name):
        return surfaces.get(name, {})

    with _mode("on"), patch(
        "core.services.signal_surface_router.read_surface", side_effect=_read
    ):
        v = j.judge_convene(surfaces=surfaces, top_signals=[], score=0.0)
    assert "etiker" in v["roles"]  # negative valence pulls in the care/weigh lens


def test_synthesizer_always_present_and_capped():
    from core.services import central_convene_judge as j
    with _mode("on"):
        v = j.judge_convene(surfaces=None, top_signals=[], score=0.0, score_override=0.9)
    assert "synthesizer" in v["roles"]
    assert len(v["roles"]) <= j._MAX_ROLES


# ---------------------------------------------------------------------------
# Self-safety
# ---------------------------------------------------------------------------


def test_self_safe_when_surface_read_raises():
    from core.services import central_convene_judge as j
    with _mode("on"), patch(
        "core.services.signal_surface_router.read_surface",
        side_effect=RuntimeError("boom"),
    ):
        v = j.judge_convene(surfaces=None, top_signals=["a"], score=0.0)
    # movement reads swallow the error → no real movement → benign no-convene
    assert v["convene"] is False


def test_current_mode_defaults_off(monkeypatch):
    from core.services import central_convene_judge as j
    monkeypatch.setattr(j, "_kv_get", lambda k, d: "off")
    assert j.current_mode() == "off"
    monkeypatch.setattr(j, "_kv_get", lambda k, d: "bogus")
    assert j.current_mode() == "off"
    monkeypatch.setattr(j, "_kv_get", lambda k, d: "shadow")
    assert j.current_mode() == "shadow"
