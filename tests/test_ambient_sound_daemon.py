"""Tests for core.services.ambient_sound_daemon — coarse age via shared helper."""

from core.services.visual_memory import _coarse_age_label


def test_ambient_sound_uses_shared_bucket_helper():
    """ambient_sound_daemon.get_latest_ambient_sound_for_prompt() reuses the
    same _coarse_age_label() from visual_memory so both sensorial sections
    roll on identical bucket boundaries — keeping the prompt-cache prefix
    stable across both. Regression-guard against future drift."""
    import core.services.ambient_sound_daemon as asd
    src = open(asd.__file__).read()
    assert "_coarse_age_label" in src, (
        "ambient_sound_daemon must import _coarse_age_label from visual_memory; "
        "without it, per-minute/per-hour rolls invalidate ~10k tokens of "
        "cacheable prefix every time."
    )


def test_coarse_label_round_trip():
    # Sanity: helper is callable and gives stable strings
    assert _coarse_age_label(30).startswith("(")
    assert _coarse_age_label(500) == "(tidligere i dag)"
