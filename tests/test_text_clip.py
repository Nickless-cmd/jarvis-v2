"""Tests for core/services/text_clip.py — ord-sikker klipning (mod død ved tusinde snit)."""
from __future__ import annotations

from core.services.text_clip import clip_text, clip_words


def test_short_text_unchanged_no_ellipsis():
    assert clip_text("kort", limit=100) == "kort"       # ingen ellipsis når intet klippes


def test_never_cuts_mid_word():
    s = "Jeg bærer stadig på den uafsluttede udforskning af selvmodellen endnu"
    out = clip_text(s, limit=40)
    assert out.endswith("…")
    # sidste rigtige token før ellipsis må være et HELT ord (ikke afhugget)
    core = out.rstrip("…").strip()
    assert s.startswith(core)                            # præfiks-match = intet ord blev hugget


def test_prefers_sentence_boundary():
    s = "Første sætning her. Anden sætning der fortsætter et godt stykke videre endnu."
    # limit=24: sætnings-slut (idx 18) ligger sent nok (>60%) → klip ved sætnings-grænse, rent
    out = clip_text(s, limit=24)
    assert out == "Første sætning her."


def test_whitespace_normalized():
    assert clip_text("  a   b\n c  ", limit=100) == "a b c"


def test_hard_respects_byte_budget():
    s = "et to tre fire fem seks syv otte ni ti elleve tolv"
    out = clip_text(s, limit=20, hard=True)
    assert len(out) <= 20                                # hård grænse inkl. ellipsis


def test_single_giant_word_falls_back():
    out = clip_text("supercalifragilisticexpialidocious", limit=10)
    assert out.endswith("…") and len(out) <= 11


def test_clip_words():
    assert clip_words("en to tre fire fem", max_words=3) == "en to tre …"
    assert clip_words("en to", max_words=5) == "en to"


def test_self_safe_on_none():
    assert clip_text(None, limit=10) == ""
    assert clip_words(None, max_words=3) == ""
