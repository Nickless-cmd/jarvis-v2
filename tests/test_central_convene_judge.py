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
    assert v["roles"] == []              # 15. jul: dommeren foreskriver ALDRIG roller (nudge, ikke ordre)


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


def test_judge_nudges_topic_but_prescribes_no_roles():
    """15. jul (Bjørn): dommeren er en NUDGE — den detekterer bevægelse + emne, men
    FORESKRIVER ALDRIG roller. Jarvis konstruerer selv rollerne per-emne i convene_council
    (Claudes model). Ingen låst signal→rolle-tabel."""
    from core.services import central_convene_judge as j
    surfaces = _surfaces(
        existential_wonder={"latest_wonder": "Hvem er jeg?"},
        conflict={"last_conflict": "spænding"},
    )

    def _read(name):
        return surfaces.get(name, {})

    with _mode("on"), patch(
        "core.services.signal_surface_router.read_surface", side_effect=_read
    ):
        v = j.judge_convene(surfaces=surfaces, top_signals=[], score=0.0)
    assert v["convene"] is True            # bevægelse → tilbud til Jarvis
    assert v["roles"] == []                # men INGEN foreskrevne roller
    assert v["topic_hint"]                 # emne-hint bæres (det nudgen tilbyder)


def test_no_role_derivation_symbols_remain():
    """Tabel-udledningen er fjernet — ingen _derive_roles / _SIGNAL_PERSPECTIVES."""
    from core.services import central_convene_judge as j
    assert not hasattr(j, "_derive_roles")
    assert not hasattr(j, "_SIGNAL_PERSPECTIVES")


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
