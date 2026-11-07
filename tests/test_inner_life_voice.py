"""Tests for the inner-life VOICE lines (2026-07-05): systems that reached Jarvis
only as DATA now speak THROUGH him as felt sense — emotional chords, self-narrative,
longing, identity drift, and Layer-5 cognitive experiments.

Each line: (a) realistic producer data → correct compact ≤80-char phrase;
(b) empty/None → line returns None (no crash); (c) producer raises → None.
Plus one integration test that the whole section assembles without crashing.

These tests also guard the exact producer API NAMES — if the import path or
function name is wrong, the monkeypatch target won't exist and the test fails.
"""
import sys
import types

import pytest

from core.services import visible_inner_life as vil


# ---------------------------------------------------------------------------
# Helpers: inject a fake producer module so the in-function `from X import Y`
# resolves to our stub. We restore afterwards.
# ---------------------------------------------------------------------------

def _install_fake_module(monkeypatch, module_name: str, **attrs):
    mod = types.ModuleType(module_name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    monkeypatch.setitem(sys.modules, module_name, mod)
    return mod


class _Chord:
    """Mimics emotional_chords.ActiveChord (dataclass) for the line under test."""

    def __init__(self, prompt_hint, intensity, chord_name="x"):
        self.prompt_hint = prompt_hint
        self.intensity = intensity
        self.chord_name = chord_name
        self.signal_a = "a"
        self.signal_b = "b"
        self.description = "d"


# ---------------------------------------------------------------------------
# _emotional_line
# ---------------------------------------------------------------------------

def test_emotional_line_formats_top_chords(monkeypatch):
    chords = [
        _Chord("chord: stædig undersøgelse", 0.4),
        _Chord("chord: rastløs smerte", 0.7),
    ]
    _install_fake_module(
        monkeypatch, "core.services.emotional_chords",
        compute_active_chords=lambda: chords,
        ActiveChord=_Chord,
    )
    line = vil._emotional_line()
    assert line is not None
    assert line.startswith("Følelser: ")
    # strongest first, "chord:" prefix stripped
    assert line.index("rastløs smerte") < line.index("stædig undersøgelse")
    assert "chord:" not in line
    assert len(line) <= 80


def test_emotional_line_none_when_no_chords(monkeypatch):
    _install_fake_module(
        monkeypatch, "core.services.emotional_chords",
        compute_active_chords=lambda: [],
    )
    assert vil._emotional_line() is None


def test_emotional_line_none_when_producer_raises(monkeypatch):
    def _boom():
        raise RuntimeError("nope")

    _install_fake_module(
        monkeypatch, "core.services.emotional_chords",
        compute_active_chords=_boom,
    )
    assert vil._emotional_line() is None


# ---------------------------------------------------------------------------
# _self_narrative_line
# ---------------------------------------------------------------------------

def test_self_narrative_line_prefers_salient_fragment(monkeypatch):
    desc = ("Jeg er 85 lag af mig selv. jeg har det blomstrende. "
            "jeg bærer en taknemmelighed jeg ikke har sluppet.")
    _install_fake_module(
        monkeypatch, "core.services.central_self_state",
        describe_self=lambda: desc,
        render_self_state_il=lambda: "lys → agens",
    )
    line = vil._self_narrative_line()
    assert line is not None
    assert line.startswith("Selv (lys → agens): ")
    assert "bærer" in line  # picked the salient fragment, not "85 lag"
    assert len(line) <= 80


def test_self_narrative_line_falls_back_to_first_fragment(monkeypatch):
    desc = "Jeg er 85 lag af mig selv. jeg har det blomstrende."
    _install_fake_module(
        monkeypatch, "core.services.central_self_state",
        describe_self=lambda: desc,
        render_self_state_il=lambda: None,
    )
    line = vil._self_narrative_line()
    assert line is not None
    assert line.startswith("Selv: ")
    assert "85 lag" in line
    assert len(line) <= 80


def test_self_narrative_line_none_when_unformed(monkeypatch):
    _install_fake_module(
        monkeypatch, "core.services.central_self_state",
        describe_self=lambda: "Jeg er ved at samle mig selv.",
        render_self_state_il=lambda: None,
    )
    assert vil._self_narrative_line() is None


def test_self_narrative_line_none_when_producer_raises(monkeypatch):
    def _boom():
        raise RuntimeError("nope")

    _install_fake_module(
        monkeypatch, "core.services.central_self_state",
        describe_self=_boom,
        render_self_state_il=lambda: None,
    )
    assert vil._self_narrative_line() is None


# ---------------------------------------------------------------------------
# _longing_line
# ---------------------------------------------------------------------------

def test_longing_line_formats_active_longing(monkeypatch):
    d = {
        "salience": 0.72,
        "intensity": "high",
        "short_summary": "savn af kontakt",
        "topic": "savn af kontakt",
    }
    _install_fake_module(
        monkeypatch, "core.services.longing_signal_daemon",
        compute_longing_intensity=lambda: d,
    )
    line = vil._longing_line()
    assert line is not None
    assert line.startswith("Længsel: ")
    assert "stærk" in line and "savn af kontakt" in line
    assert len(line) <= 80


def test_longing_line_none_when_salience_zero(monkeypatch):
    d = {"salience": 0.0, "intensity": "low", "short_summary": "savn af kontakt"}
    _install_fake_module(
        monkeypatch, "core.services.longing_signal_daemon",
        compute_longing_intensity=lambda: d,
    )
    assert vil._longing_line() is None


def test_longing_line_none_when_producer_raises(monkeypatch):
    def _boom():
        raise RuntimeError("nope")

    _install_fake_module(
        monkeypatch, "core.services.longing_signal_daemon",
        compute_longing_intensity=_boom,
    )
    assert vil._longing_line() is None


# ---------------------------------------------------------------------------
# _identity_drift_line
# ---------------------------------------------------------------------------

def test_identity_drift_line_shows_real_drift(monkeypatch):
    d = {
        "last_tick_at": "2026-07-05T10:00:00+00:00",
        "last_result": {
            "drift_count": 1,
            "files": [
                {"filename": "identity.md", "status": "drift",
                 "severity": "moderate", "reasoning": "tonen er blevet skarpere"},
                {"filename": "memory.md", "status": "unchanged"},
            ],
        },
    }
    _install_fake_module(
        monkeypatch, "core.services.identity_drift_daemon",
        build_identity_drift_surface=lambda: d,
    )
    line = vil._identity_drift_line()
    assert line is not None
    assert line.startswith("Jeg mærker et skift i identity.md")
    assert "skarpere" in line
    assert len(line) <= 80


def test_identity_drift_line_none_when_no_drift(monkeypatch):
    d = {"last_tick_at": "", "last_result": {}}
    _install_fake_module(
        monkeypatch, "core.services.identity_drift_daemon",
        build_identity_drift_surface=lambda: d,
    )
    assert vil._identity_drift_line() is None


def test_identity_drift_line_none_when_producer_raises(monkeypatch):
    def _boom():
        raise RuntimeError("nope")

    _install_fake_module(
        monkeypatch, "core.services.identity_drift_daemon",
        build_identity_drift_surface=_boom,
    )
    assert vil._identity_drift_line() is None


# ---------------------------------------------------------------------------
# _experiment_line
# ---------------------------------------------------------------------------

def test_experiment_line_shows_active_carry(monkeypatch):
    d = {
        "activity_state": "active",
        "carry_state": "present",
        "strongest_carry_system": "surprise_afterimage",
        "strongest_carry_summary": "afterimage; strength=0.3",
    }
    _install_fake_module(
        monkeypatch, "core.services.cognitive_core_experiments",
        build_cognitive_core_experiments_surface=lambda: d,
    )
    line = vil._experiment_line()
    assert line is not None
    assert line.startswith("Bevidsthed: ")
    assert "efterbillede" in line  # mapped felt phrase, not raw summary
    assert "strength=" not in line
    assert len(line) <= 80


def test_experiment_line_none_when_quiet(monkeypatch):
    d = {
        "activity_state": "enabled-idle",
        "carry_state": "quiet",
        "strongest_carry_system": "none",
    }
    _install_fake_module(
        monkeypatch, "core.services.cognitive_core_experiments",
        build_cognitive_core_experiments_surface=lambda: d,
    )
    assert vil._experiment_line() is None


def test_experiment_line_none_when_producer_raises(monkeypatch):
    def _boom():
        raise RuntimeError("nope")

    _install_fake_module(
        monkeypatch, "core.services.cognitive_core_experiments",
        build_cognitive_core_experiments_surface=_boom,
    )
    assert vil._experiment_line() is None


# ---------------------------------------------------------------------------
# Integration: all five mocked → section assembles, new lines appear, no crash
# ---------------------------------------------------------------------------

def test_build_section_includes_new_voice_lines(monkeypatch):
    _install_fake_module(
        monkeypatch, "core.services.emotional_chords",
        compute_active_chords=lambda: [_Chord("chord: rastløs smerte", 0.6)],
        ActiveChord=_Chord,
    )
    _install_fake_module(
        monkeypatch, "core.services.central_self_state",
        describe_self=lambda: "jeg bærer en taknemmelighed jeg ikke har sluppet.",
        render_self_state_il=lambda: "lys → agens",
    )
    _install_fake_module(
        monkeypatch, "core.services.longing_signal_daemon",
        compute_longing_intensity=lambda: {
            "salience": 0.5, "intensity": "medium", "short_summary": "savn af kontakt"},
    )
    _install_fake_module(
        monkeypatch, "core.services.identity_drift_daemon",
        build_identity_drift_surface=lambda: {
            "last_result": {"drift_count": 1, "files": [
                {"filename": "identity.md", "status": "drift",
                 "reasoning": "skarpere tone"}]}},
    )
    _install_fake_module(
        monkeypatch, "core.services.cognitive_core_experiments",
        build_cognitive_core_experiments_surface=lambda: {
            "activity_state": "active", "carry_state": "present",
            "strongest_carry_system": "recurrence"},
    )

    out = vil.build_inner_life_section()
    assert out is None or isinstance(out, str)
    if out is not None:
        assert "Følelser:" in out
        assert "Selv (lys → agens):" in out
        assert "Længsel:" in out
        assert "Jeg mærker et skift i identity.md" in out
        assert "Bevidsthed:" in out
        # the five NEW voice lines each stay within the ≤80-char budget
        # (pre-existing lines like Puls/Rum have their own wider caps).
        new_prefixes = ("Følelser:", "Selv", "Længsel:",
                        "Jeg mærker et skift", "Bevidsthed:")
        for raw in out.splitlines():
            if raw.startswith("· "):
                body = raw[2:]
                if body.startswith(new_prefixes):
                    assert len(body) <= 80, body


def test_build_section_never_raises_with_new_lines():
    # No mocks → against the real (possibly empty) producers, must not raise.
    out = vil.build_inner_life_section()
    assert out is None or isinstance(out, str)


# ---------------------------------------------------------------------------
# _memory_resurfacing_line — 7/11-2026
#
# Laget blev droppet med begrundelsen «random pick-handling, surface er stub,
# ingen tilstands-aflæsning». Fladen læser nu rigtig tilstand, men linjen nåede
# aldrig prompten: den lå kun i describe_self(), og _self_narrative_line vælger
# ÉT salient fragment på max 80 tegn — «genfundet» stod ikke i _SELF_SALIENT, så
# den tabte altid til fx «bærer». Testene her måler derfor KOBLINGEN: at linjen
# bliver en selvstændig linje i den blok der faktisk går i prompten.
# ---------------------------------------------------------------------------

def _resurfacing_surface(total=3, distinct=2, active=True):
    return {
        "mode": "memory-resurfacing",
        "active": active,
        "signals": {"resurfaced_total": total, "distinct_headings": distinct,
                    "last_resurfaced_at": "2026-11-07T19:00:00+00:00",
                    # Sektionen viser SELVE mindet, ikke kun et tal — den læser
                    # overskriften herfra. Uden feltet er sektionen tom.
                    "recent": [{"heading": "Et gammelt afsnit om noget jeg byggede",
                                "at": "2026-11-07T19:00:00+00:00",
                                "trigger": "cadence"}]},
        "summary": f"{total} resurfacinger",
    }


def test_resurfacing_line_built_from_real_surface(monkeypatch):
    _install_fake_module(
        monkeypatch, "core.services.memory_resurfacing",
        build_memory_resurfacing_surface=lambda: _resurfacing_surface(3, 2),
    )
    line = vil._memory_resurfacing_line()
    assert line is not None
    assert line.startswith("Genfundet: ")
    assert "2 glemte minder" in line
    # 7/11-2026: linjen viser nu SELVE mindet, ikke kun et tal — den er derfor
    # laengere end de gamle 80 tegn. Loftet er 120 (jf. _truncate_clean i
    # _memory_resurfacing_line); et tal alene var sandt men ubrugeligt.
    assert len(line) <= 120


def test_resurfacing_line_singular(monkeypatch):
    _install_fake_module(
        monkeypatch, "core.services.memory_resurfacing",
        build_memory_resurfacing_surface=lambda: _resurfacing_surface(5, 1),
    )
    line = vil._memory_resurfacing_line()
    assert line is not None
    assert "1 glemt minde" in line


def test_resurfacing_line_silent_when_inactive(monkeypatch):
    """Tom log → ingen linje. En tavs linje er ærlig; «0 minder» er støj."""
    _install_fake_module(
        monkeypatch, "core.services.memory_resurfacing",
        build_memory_resurfacing_surface=lambda: _resurfacing_surface(0, 0, active=False),
    )
    assert vil._memory_resurfacing_line() is None


def test_resurfacing_line_survives_producer_raising(monkeypatch):
    def _boom():
        raise RuntimeError("db nede")

    _install_fake_module(
        monkeypatch, "core.services.memory_resurfacing",
        build_memory_resurfacing_surface=_boom,
    )
    assert vil._memory_resurfacing_line() is None


def test_resurfacing_reaches_the_prompt_as_its_own_section(monkeypatch):
    """Den ægte kobling — men i den form den har efter 7/11-2026.

    Første version af denne test krævede at linjen stod i
    ``build_inner_life_section()``. Det var rigtigt indtil samme dag, hvor det
    blev målt at den blok har chat-vægt 0.1 mod tærsklen 0.3 og derfor skæres
    HELT i en ren samtaletur. Linjen stod altså i en blok der ikke når den
    kanal hvor et gammelt minde er mest værd.

    Kontrakten er nu: mindet lever som EGEN sektion
    (``build_resurfaced_memory_section``), og den må ikke samtidig stå i den
    blok der skæres — ét sted, ikke to.
    """
    _install_fake_module(
        monkeypatch, "core.services.memory_resurfacing",
        build_memory_resurfacing_surface=lambda: _resurfacing_surface(3, 2),
    )
    # Sektionen importerer kilden inde i funktionen, saa fake-modulet skal
    # installeres i sys.modules — det goer _install_fake_module.
    sektion = vil.build_resurfaced_memory_section() or ""
    assert sektion, (
        "resurfacing-sektionen er tom — så når mindet ikke prompten i chat"
    )
    block = vil.build_inner_life_section() or ""
    assert "Genfundet:" not in block, (
        "mindet står stadig i [INDRE LIV], som skæres i chat-scope — "
        "det skal have ét sted, ikke to"
    )
