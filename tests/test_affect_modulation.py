"""Tests for the condensed affect-modulation section (2026-06-22 round 3)."""
from unittest.mock import patch

from core.services import affect_modulation as am


def test_section_is_compact_single_line():
    with patch.object(
        am, "compute_affect_modulated_params",
        return_value={"max_tool_calls_per_turn": 36},
    ), patch.dict(am.DEFAULTS, {"max_tool_calls_per_turn": 40}, clear=False):
        out = am.affect_modulation_section()
    assert out is not None
    assert "Affect-sat" in out
    assert "max_tool_calls_per_turn=36" in out
    # the verbose "follow as a standing order" preamble is gone
    assert "standing order" not in out
    assert out.count("\n") == 0  # one compact line


def test_section_none_without_overrides():
    with patch.object(am, "compute_affect_modulated_params", return_value={}):
        assert am.affect_modulation_section() is None


def test_section_none_when_nothing_changed():
    with patch.object(
        am, "compute_affect_modulated_params",
        return_value={"max_tool_calls_per_turn": 40},
    ), patch.dict(am.DEFAULTS, {"max_tool_calls_per_turn": 40}, clear=False):
        assert am.affect_modulation_section() is None


def test_default_max_rounds_is_sane_backstop():
    """2026-06-30 (#4): default-cap sænket 100 → 30. Loop-gaten + syntese-pausen
    afslutter normale runs langt tidligere; dette er kun et backstop mod
    runaway-spiraler. Må aldrig krybe tilbage mod 100."""
    budget = am.compute_agentic_loop_budget()
    assert budget["max_rounds"] == 30


def test_resume_and_pressure_cap_below_default():
    """Resume- og pres-modulering skal stadig sænke UNDER default (ikke hæve)."""
    resume = am.compute_agentic_loop_budget(resume_context=True)
    assert resume["max_rounds"] <= 30


# ---------------------------------------------------------------------------
# Kroppen skal regulere adfærden
#
# Målt 2026-09-05: kroppen sanses rigt og når hans bevidsthed, men regulerede
# INTET. Denne governor læste kun fatigue/frustration — følelses-akser fra
# samtalen. I samme øjeblik stod `strain_level: elevated` (13 af 105 GB disk
# fri) OG `max_tool_calls_per_turn: 36`, den høje indstilling, fordi
# confidence >= 0.8 ganger budgettet op til sidst. Maskinen var presset, og
# governoren skruede op.
# ---------------------------------------------------------------------------

import pytest

from core.services import affect_modulation as AM


class _Snapshot:
    def __init__(self, fatigue=0.0, frustration=0.0, confidence=0.9):
        self.fatigue = fatigue
        self.frustration = frustration
        self.confidence = confidence


def _krop(monkeypatch, niveau: str):
    monkeypatch.setattr(
        "core.services.embodied_state.build_embodied_state_surface",
        lambda: {"strain_level": niveau},
    )


def _rolig_affekt(monkeypatch, **kw):
    monkeypatch.setattr(
        "core.services.emotional_controls.read_emotional_snapshot",
        lambda: _Snapshot(**kw),
    )
    monkeypatch.setattr(
        "core.services.emotion_concepts.get_active_emotion_concepts", lambda: [],
    )


def test_krops_pres_oversaettes_til_en_skala(monkeypatch):
    for niveau, forventet in (("low", 0.0), ("easing", 0.2), ("elevated", 0.45),
                              ("high", 0.7), ("critical", 0.9)):
        _krop(monkeypatch, niveau)
        assert AM.body_pressure() == (forventet, niveau)


def test_ulaeselig_krop_bremser_ikke(monkeypatch):
    """Vi må aldrig bremse på grund af et MANGLENDE måltal."""
    monkeypatch.setattr(
        "core.services.embodied_state.build_embodied_state_surface",
        lambda: (_ for _ in ()).throw(RuntimeError("ingen sysfs")),
    )
    assert AM.body_pressure() == (0.0, "unknown")


def test_godt_humoer_kan_ikke_gange_et_krops_loft_vaek(monkeypatch):
    """Præcis den fejl vi målte: confidence 0.9 gav 36 mens disken var fuld."""
    _rolig_affekt(monkeypatch, confidence=0.9)
    _krop(monkeypatch, "high")
    ud = AM.compute_affect_modulated_params()
    assert ud["max_tool_calls_per_turn"] <= 12, (
        "krops-loftet blev ganget væk af confidence-opskruningen — det var "
        "netop rækkefølgefejlen"
    )
    assert ud["body_strain"] == "high"


def test_elevated_daemper_men_stopper_ikke(monkeypatch):
    _rolig_affekt(monkeypatch, confidence=0.9)
    _krop(monkeypatch, "elevated")
    ud = AM.compute_affect_modulated_params()
    assert 12 <= ud["max_tool_calls_per_turn"] <= 21
    assert ud["body_strain"] == "elevated"


def test_rolig_krop_aendrer_intet(monkeypatch):
    _rolig_affekt(monkeypatch, confidence=0.5)
    _krop(monkeypatch, "low")
    ud = AM.compute_affect_modulated_params()
    assert "body_strain" not in ud


def test_presset_krop_giver_faerre_runder(monkeypatch):
    _rolig_affekt(monkeypatch)
    _krop(monkeypatch, "critical")
    b = AM.compute_agentic_loop_budget()
    assert b["max_rounds"] <= 12, "en presset maskin skal give faerre runder"


def test_krop_taeller_selv_uden_foelelses_snapshot(monkeypatch):
    """Affekt-laget kan vaere nede; kroppen maa ikke tabes med det."""
    monkeypatch.setattr(
        "core.services.emotional_controls.read_emotional_snapshot",
        lambda: (_ for _ in ()).throw(RuntimeError("nede")),
    )
    _krop(monkeypatch, "high")
    b = AM.compute_agentic_loop_budget()
    assert b["max_rounds"] <= 12


def test_grunden_staar_i_prompten_ikke_kun_tallet(monkeypatch):
    _rolig_affekt(monkeypatch, confidence=0.9)
    _krop(monkeypatch, "high")
    s = AM.affect_modulation_section() or ""
    assert "maskinen er presset" in s
    assert "high" in s
    assert "body_strain=" not in s, "grunden må ikke stå som en parameter han skal følge"
