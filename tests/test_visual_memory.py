"""Tests for core.services.visual_memory — coarse age bucketing."""

from core.services.visual_memory import _coarse_age_label


def test_lige_nu():
    assert _coarse_age_label(0) == "(lige nu)"
    assert _coarse_age_label(4) == "(lige nu)"


def test_få_min():
    assert _coarse_age_label(5) == "(for få min siden)"
    assert _coarse_age_label(14) == "(for få min siden)"


def test_sidste_time():
    assert _coarse_age_label(15) == "(inden for sidste time)"
    assert _coarse_age_label(59) == "(inden for sidste time)"


def test_par_timer():
    assert _coarse_age_label(60) == "(for et par timer siden)"
    assert _coarse_age_label(179) == "(for et par timer siden)"


def test_tidligere_i_dag():
    assert _coarse_age_label(180) == "(tidligere i dag)"
    assert _coarse_age_label(719) == "(tidligere i dag)"


def test_et_stykke_tid():
    assert _coarse_age_label(720) == "(for et stykke tid siden)"
    assert _coarse_age_label(1439) == "(for et stykke tid siden)"


def test_dage():
    assert _coarse_age_label(1440) == "(for 1 dag siden)"
    assert _coarse_age_label(2880) == "(for 2 dage siden)"


def test_over_en_uge():
    assert _coarse_age_label(7 * 1440) == "(for over en uge siden)"


def test_cache_stability_window():
    """Within a single bucket, the label must NOT change. Critical for
    prompt-cache prefix stability — see commit message."""
    # 3-12h bucket: every value should produce same label
    labels = {_coarse_age_label(m) for m in range(180, 720, 30)}
    assert labels == {"(tidligere i dag)"}
    # 12-24h bucket
    labels = {_coarse_age_label(m) for m in range(720, 1440, 60)}
    assert labels == {"(for et stykke tid siden)"}
