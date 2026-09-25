"""Tests for boredom_curiosity_bridge.py"""
import pytest
from datetime import timedelta

from core.services.boredom_curiosity_bridge import (
    add_boredom,
    should_spawn_curiosity,
    get_curiosity_prompt,
    get_active_curiosities,
    clear_curiosities,
    reset_boredom_curiosity_bridge,
    get_boredom_curiosity_state,
    build_boredom_curiosity_bridge_surface,
)


def setup_function():
    reset_boredom_curiosity_bridge()


def test_add_boredom_short():
    result = add_boredom(timedelta(minutes=1))
    assert "boredom_level" in result


def test_add_boredom_long():
    result = add_boredom(timedelta(minutes=30))
    assert result["boredom_level"] > 0


def test_should_spawn_curiosity_low():
    result = should_spawn_curiosity()
    assert result is False


def test_get_curiosity_prompt_empty():
    prompt = get_curiosity_prompt()
    assert prompt is None


def test_get_active_curiosities_empty():
    curiosities = get_active_curiosities()
    assert curiosities == []


def test_get_boredom_curiosity_state():
    state = get_boredom_curiosity_state()
    assert "boredom_level" in state
    assert "curiosity_count" in state
    assert "can_spawn" in state


def test_build_boredom_curiosity_bridge_surface():
    surface = build_boredom_curiosity_bridge_surface()
    assert "active" in surface
    assert "boredom_level" in surface
    assert "curiosity_count" in surface


def test_reset_boredom_curiosity_bridge():
    add_boredom(timedelta(minutes=30))
    reset_boredom_curiosity_bridge()
    state = get_boredom_curiosity_state()
    assert state["boredom_level"] == 0.0
    assert state["curiosity_count"] == 0


def test_clear_curiosities():
    add_boredom(timedelta(minutes=30))
    clear_curiosities()
    state = get_boredom_curiosity_state()
    assert state["curiosity_count"] == 0


# ── Varig tilstand og udloeb (25/9-2026) ────────────────────────────────────
#
# Kedsomheden laa i en modul-global: taerskelen er 2,0 og hvert tik laegger en
# broekdel til, men genstarten satte den paa nul. `/mc/runtime` paa CT105 viste
# baade `boredom_level: 0` og `curiosity_count: 0`.
#
# Udloebet foelger med disken: `clear_curiosities()` har ingen kaldere, saa
# listen ville ellers vokse for evigt — hidtil skjult af genstarten.

from datetime import UTC, datetime, timedelta as _td

from core.services.boredom_curiosity_bridge import Curiosity


def _laeg_nysgerrighed_ind(*, alder_timer: float) -> None:
    import core.services.boredom_curiosity_bridge as bcb

    skabt = datetime.now(UTC) - _td(hours=alder_timer)
    bcb._curiosities = [
        Curiosity(
            curiosity_id="curiosity-proeve",
            curiosity_type="pattern_hunt",
            prompt="Er der et mønster jeg overser?",
            strength=0.5,
            created_at=skabt.isoformat(),
        )
    ]
    bcb._gem()


def test_kedsomheden_overlever_at_modulet_indlaeses_forfra():
    """Ophobningen er hele pointen — den maa ikke starte forfra hver genstart."""
    import importlib

    import core.services.boredom_curiosity_bridge as bcb

    add_boredom(_td(seconds=900))
    foer = get_boredom_curiosity_state()["boredom_level"]
    assert foer > 0

    frisk = importlib.reload(bcb)
    try:
        assert frisk.get_boredom_curiosity_state()["boredom_level"] == foer
    finally:
        reset_boredom_curiosity_bridge()
        importlib.reload(bcb)


def test_en_nysgerrighed_aeldre_end_et_doegn_taeller_ikke_med():
    """Samme levetid som den `low`-post den skubbes til i `initiative_queue`."""
    _laeg_nysgerrighed_ind(alder_timer=25)

    assert get_curiosity_prompt() is None
    assert get_active_curiosities() == []
    assert get_boredom_curiosity_state()["curiosity_count"] == 0


def test_en_nysgerrighed_yngre_end_et_doegn_taeller_med():
    _laeg_nysgerrighed_ind(alder_timer=23)

    assert get_curiosity_prompt() == "Er der et mønster jeg overser?"
    assert len(get_active_curiosities()) == 1


def test_nulstilling_rydder_ogsaa_disken():
    import importlib

    import core.services.boredom_curiosity_bridge as bcb

    add_boredom(_td(seconds=900))
    reset_boredom_curiosity_bridge()

    frisk = importlib.reload(bcb)
    try:
        assert frisk.get_boredom_curiosity_state()["boredom_level"] == 0.0
    finally:
        importlib.reload(bcb)
