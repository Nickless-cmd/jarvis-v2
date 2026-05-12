from __future__ import annotations

import logging

import pytest


class _FakeSettings:
    unconscious_modulation_enabled = True
    unconscious_modulation_temp_delta = 0.30
    unconscious_modulation_top_p_delta = 0.15
    unconscious_modulation_temp_floor = 0.3
    unconscious_modulation_temp_ceiling = 1.2
    unconscious_modulation_top_p_floor = 0.7
    unconscious_modulation_top_p_ceiling = 1.0


def test_returns_base_when_disabled(monkeypatch):
    from core.services import unconscious_modulation

    class FS(_FakeSettings):
        unconscious_modulation_enabled = False

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: FS())

    result = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=0.7, base_top_p=1.0, workspace_id="default",
    )
    assert result == (0.7, 1.0)


def test_returns_base_when_no_field(monkeypatch):
    from core.services import unconscious_modulation

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field",
        lambda *, workspace_id="default": None,
    )

    result = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=0.7, base_top_p=1.0,
    )
    assert result == (0.7, 1.0)


def test_modulates_negative_valens_lowers_temperature(monkeypatch):
    from core.services import unconscious_modulation

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field",
        lambda *, workspace_id="default": {
            "field_valens": -1.0,
            "field_arousal": 0.0,
            "field_intensity": 1.0,
        },
    )

    mod_temp, mod_top_p = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=0.7, base_top_p=1.0,
    )
    assert mod_temp == pytest.approx(0.40, abs=0.001)
    assert mod_top_p == pytest.approx(1.0, abs=0.001)


def test_modulates_positive_arousal_widens_top_p(monkeypatch):
    from core.services import unconscious_modulation

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field",
        lambda *, workspace_id="default": {
            "field_valens": 0.0,
            "field_arousal": 1.0,
            "field_intensity": 1.0,
        },
    )

    mod_temp, mod_top_p = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=0.85, base_top_p=0.85,
    )
    assert mod_top_p == pytest.approx(1.0, abs=0.001)
    assert mod_temp == pytest.approx(0.85, abs=0.001)


def test_intensity_scales_delta(monkeypatch):
    from core.services import unconscious_modulation

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field",
        lambda *, workspace_id="default": {
            "field_valens": -1.0,
            "field_arousal": 0.0,
            "field_intensity": 0.5,
        },
    )

    mod_temp, _ = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=0.7, base_top_p=1.0,
    )
    assert mod_temp == pytest.approx(0.55, abs=0.001)


def test_clamps_temperature_to_floor(monkeypatch):
    from core.services import unconscious_modulation

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field",
        lambda *, workspace_id="default": {
            "field_valens": -1.0,
            "field_arousal": 0.0,
            "field_intensity": 1.0,
        },
    )

    mod_temp, _ = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=0.35, base_top_p=1.0,
    )
    assert mod_temp == pytest.approx(0.3, abs=0.001)


def test_clamps_top_p_to_ceiling(monkeypatch):
    from core.services import unconscious_modulation

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field",
        lambda *, workspace_id="default": {
            "field_valens": 0.0,
            "field_arousal": 1.0,
            "field_intensity": 1.0,
        },
    )

    _, mod_top_p = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=0.7, base_top_p=0.95,
    )
    assert mod_top_p == pytest.approx(1.0, abs=0.001)


def test_none_base_uses_implicit_defaults(monkeypatch):
    from core.services import unconscious_modulation

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field",
        lambda *, workspace_id="default": {
            "field_valens": -1.0,
            "field_arousal": 0.0,
            "field_intensity": 1.0,
        },
    )

    mod_temp, mod_top_p = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=None, base_top_p=None,
    )
    assert mod_temp == pytest.approx(0.4, abs=0.001)
    assert mod_top_p == pytest.approx(1.0, abs=0.001)


def test_failure_returns_base(monkeypatch):
    from core.services import unconscious_modulation

    monkeypatch.setattr(unconscious_modulation, "load_settings", lambda: _FakeSettings())

    def boom(*, workspace_id="default"):
        raise RuntimeError("nope")
    monkeypatch.setattr(
        "core.services.user_temperature_engine.get_active_field", boom,
    )

    mod_temp, mod_top_p = unconscious_modulation.compute_unconscious_modulation(
        base_temperature=0.7, base_top_p=1.0,
    )
    assert mod_temp == pytest.approx(0.7)
    assert mod_top_p == pytest.approx(1.0)
