"""Tests for initiative_accumulator.py"""
import pytest
from datetime import timedelta

from core.services.initiative_accumulator import (
    accumulate_wants,
    get_top_want,
    get_wants_by_type,
    format_wants_for_prompt,
    clear_wants_by_type,
    reset_initiative_accumulator,
    get_initiative_accumulator_state,
    build_initiative_accumulator_surface,
)


def setup_function():
    reset_initiative_accumulator()


def test_accumulate_wants_short_duration():
    result = accumulate_wants(timedelta(minutes=1))
    assert result["accumulated"] == 0


def test_accumulate_wants_dreaming_phase():
    result = accumulate_wants(timedelta(minutes=5))
    assert "life_phase" in result
    assert "total_wants" in result


def test_get_top_want_none():
    want = get_top_want()
    assert want is None


def test_format_wants_for_prompt_empty():
    result = format_wants_for_prompt()
    assert result == ""


def test_get_initiative_accumulator_state():
    state = get_initiative_accumulator_state()
    assert "want_count" in state
    assert "top_want" in state


def test_build_initiative_accumulator_surface():
    surface = build_initiative_accumulator_surface()
    assert "active" in surface
    assert "want_count" in surface


def test_reset_initiative_accumulator():
    accumulate_wants(timedelta(minutes=5))
    reset_initiative_accumulator()
    state = get_initiative_accumulator_state()
    assert state["want_count"] == 0


def test_clear_wants_by_type(monkeypatch):
    # accumulate_wants() branches on life_phase: dreaming→insight,
    # awakening→meaning, deep_work→growth, reflection→clarity.
    # Test was non-deterministic — passed only when phase==reflection.
    # Pin to reflection so clear_wants_by_type('clarity') actually
    # targets the want that was created.
    import core.services.initiative_accumulator as ia
    monkeypatch.setattr(ia, "determine_life_phase", lambda: {"phase": "reflection"})
    accumulate_wants(timedelta(minutes=5))
    clear_wants_by_type("clarity")
    state = get_initiative_accumulator_state()
    assert state["want_count"] == 0


# ── Varig tilstand og udloeb (25/9-2026) ────────────────────────────────────
#
# `/mc/runtime` paa CT105 sagde «Ingen oensker» mens runtime-processen ophobede
# dem: modul-globalen er per proces. Med disken foelger udloebet, for listen er
# haardt begraenset til tre og en type blokerer for sig selv.

from datetime import UTC, datetime, timedelta as _td

from core.services.initiative_accumulator import Want


def _laeg_oenske_ind(*, alder_timer: float, want_type: str = "insight") -> None:
    """Skriv ét oenske direkte i den delte fil med en valgt alder."""
    import core.services.initiative_accumulator as ia

    skabt = datetime.now(UTC) - _td(hours=alder_timer)
    ia._wants = [
        Want(
            want_id="want-proeve",
            want_type=want_type,
            topic="proeve",
            strength=0.5,
            created_at=skabt.isoformat(),
            life_phase="deep_work",
        )
    ]
    ia._gem()


def test_oensker_overlever_at_modulet_indlaeses_forfra():
    import importlib

    import core.services.initiative_accumulator as ia

    _laeg_oenske_ind(alder_timer=1)

    frisk = importlib.reload(ia)
    try:
        assert frisk.get_initiative_accumulator_state()["want_count"] == 1
    finally:
        reset_initiative_accumulator()
        importlib.reload(ia)


def test_et_oenske_aeldre_end_et_doegn_taeller_ikke_med():
    """Samme levetid som `initiative_queue._EXPIRE_MINUTES_LOW` (24*60)."""
    _laeg_oenske_ind(alder_timer=25)

    assert get_top_want() is None
    assert get_initiative_accumulator_state()["want_count"] == 0
    assert build_initiative_accumulator_surface()["active"] is False


def test_et_oenske_yngre_end_et_doegn_taeller_med():
    _laeg_oenske_ind(alder_timer=23)

    top = get_top_want()
    assert top is not None
    assert top.want_type == "insight"


def test_et_udloebet_oenske_blokerer_ikke_sin_egen_type(monkeypatch):
    """Uden udloeb ville ét oenske fra i forgaars lukke sin type for altid.

    Fasen pinnes: `accumulate_wants` skaber kun et `growth`-oenske i
    `deep_work`, saa uden pin ville testen maale klokkeslaettet.
    """
    import core.services.initiative_accumulator as ia

    monkeypatch.setattr(
        ia, "determine_life_phase", lambda: {"phase": "deep_work"}
    )

    _laeg_oenske_ind(alder_timer=48, want_type="growth")
    assert get_initiative_accumulator_state()["want_count"] == 0

    ia.accumulate_wants(_td(seconds=600))

    oensker = get_initiative_accumulator_state()["all_wants"]
    assert [w["want_type"] for w in oensker] == ["growth"]
    assert "want-proeve" not in {w.want_id for w in ia._wants}
