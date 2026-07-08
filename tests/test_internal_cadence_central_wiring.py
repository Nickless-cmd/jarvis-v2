"""Tests for central cadence-wiring — verificerer at forventede producers registreres."""
from __future__ import annotations

from core.services import internal_cadence as ic
from core.services import internal_cadence_central_wiring as wiring


def test_registers_self_model_distiller_daily():
    """#4: distilleren registreres som DAGLIG cadence-producer (guard 2: langsom rytme)."""
    wiring.register_central_wiring_producers()
    assert "self_model_distiller" in ic._producers
    assert ic._producers["self_model_distiller"].cooldown_minutes == 1440


def test_wiring_is_idempotent_and_safe():
    """Gentagne kald må ikke kaste; produceren forbliver registreret (self-safe try/except)."""
    wiring.register_central_wiring_producers()
    wiring.register_central_wiring_producers()
    assert "self_model_distiller" in ic._producers
