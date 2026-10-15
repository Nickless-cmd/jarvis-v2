"""Tests for dream_continuum.py"""
import pytest
from datetime import timedelta

from core.services.dream_continuum import (
    evolve_dreams,
    get_dream_thoughts,
    get_top_dream_thought,
    format_dreams_for_prompt,
    get_dream_maturity,
    reset_dream_continuum,
    build_dream_continuum_surface,
    DreamThought,
)
from core.services.dream_carry_over import (
    adopt_dream,
    _ACTIVE_DREAMS,
    _DREAM_ARCHIVE,
)


def setup_function():
    reset_dream_continuum()
    _ACTIVE_DREAMS.clear()
    _DREAM_ARCHIVE.clear()


def test_evolve_dreams_no_dreams():
    result = evolve_dreams(timedelta(minutes=5))
    assert result["evolved_count"] == 0


def test_evolve_dreams_with_dream():
    adopt_dream(dream_id="test-dream-1", content="En drøm om fremtiden")
    result = evolve_dreams(timedelta(minutes=5))
    assert result["evolved_count"] >= 1


def test_get_dream_maturity():
    adopt_dream(dream_id="test-dream-2", content="Test drøm")
    evolve_dreams(timedelta(minutes=5))
    maturity = get_dream_maturity("test-dream-2")
    assert maturity > 0


def test_get_dream_thoughts():
    adopt_dream(dream_id="test-dream-3", content="Test drøm med tanker")
    evolve_dreams(timedelta(minutes=5))
    thoughts = get_dream_thoughts("test-dream-3")
    assert len(thoughts) >= 1


def test_get_top_dream_thought():
    adopt_dream(dream_id="test-dream-4", content="Vigtig drøm")
    evolve_dreams(timedelta(minutes=5))
    top = get_top_dream_thought()
    assert top is not None
    assert len(top) > 0


def test_format_dreams_for_prompt_with_dream():
    adopt_dream(dream_id="test-dream-5", content="En test drøm")
    result = format_dreams_for_prompt()
    assert "DREAM:" in result or "DRØM-TANKER:" in result


def test_build_dream_continuum_surface():
    adopt_dream(dream_id="test-dream-6", content="En test drøm")
    surface = build_dream_continuum_surface()
    assert "dream_count" in surface
    assert "maturity_levels" in surface


def test_reset_dream_continuum():
    adopt_dream(dream_id="test-dream-7", content="Drøm der slettes")
    reset_dream_continuum()
    surface = build_dream_continuum_surface()
    assert surface["dream_count"] >= 0


# ── Punkt 1 + 3 (15/10-2026): luk drømme-carry-over-sløjfen ──────────────
#
# Målt 15/10: systemet LÆSTE men SKREV ikke. `mark_dream_presented` havde nul
# kaldere, så `presented` forblev False og samme drøm blev injiceret hver tur
# for evigt. Og `cognitive_state.dream_*` blev publiceret til ingen.


def test_format_dreams_for_prompt_markerer_droemmen_som_praesenteret():
    """Punkt 1: læse-stien skal ogsaa SKRIVE `presented`.

    Uden markeringen blev samme drøm injiceret hver tur for evigt, og
    `session_carry_count` voksede aldrig — drømmen faldt derfor aldrig for
    `_FADE_AFTER_SESSIONS`."""
    adopt_dream(dream_id="test-dream-presented", content="En drøm der markeres")
    dream = next(d for d in _ACTIVE_DREAMS if d["dream_id"] == "test-dream-presented")
    assert dream["presented"] is False

    format_dreams_for_prompt()

    assert dream["presented"] is True
    assert int(dream["session_carry_count"]) == 1


def test_samme_droem_praesenteres_kun_en_gang():
    """Efter markeringen er drømmen ikke længere præsentabel."""
    adopt_dream(dream_id="test-dream-once", content="Unikt indhold kun én gang")

    foerste = format_dreams_for_prompt()
    assert "Unikt indhold kun én gang" in foerste

    anden = format_dreams_for_prompt()
    assert "Unikt indhold kun én gang" not in anden


def test_adopt_dream_observerer_tilstandsovergangen(monkeypatch):
    """Punkt 3: overgangen skal have en FORBRUGER, ikke kun en publicering."""
    from core.services import dream_carry_over as dco

    kald = []
    monkeypatch.setattr(
        dco, "_observe_dream_signal",
        lambda nerve, **meta: kald.append((nerve, meta)),
    )

    adopt_dream(dream_id="test-dream-observe", content="Observeret")

    assert kald, "adopt_dream skal føre overgangen videre til en forbruger"
    assert kald[0][0] == "dream_adopted"
    assert kald[0][1].get("dream_id") == "test-dream-observe"


def test_reject_dream_observerer_tilstandsovergangen(monkeypatch):
    """Punkt 3: ogsaa afvisning skal have en forbruger."""
    from core.services import dream_carry_over as dco

    kald = []
    monkeypatch.setattr(
        dco, "_observe_dream_signal",
        lambda nerve, **meta: kald.append((nerve, meta)),
    )

    adopt_dream(dream_id="test-dream-reject", content="Skal afvises")
    dco.reject_dream("test-dream-reject")

    assert [k[0] for k in kald] == ["dream_adopted", "dream_rejected"]
