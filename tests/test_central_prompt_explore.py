"""Tests for DEN MODIGE DEL — Tråd 2 prompt-relevans eksplorations-arm (ablation kontrol-arm)."""
from __future__ import annotations

import pytest

from core.services import central_prompt_explore as ex
from core.services import central_hypothesis_governance as gov


@pytest.fixture(autouse=True)
def _reset(isolated_runtime):
    gov._ANCHORED_BASELINES.clear()
    ex._kv_set(ex._EXPLORE_FLAG, False)
    ex._kv_set(ex._STATE_KEY, {})
    ex._kv_set(ex._WEIGHTS_KEY, {})
    ex._kv_set(ex._SHADOW_KEY, {})
    yield


# ── SIKKERHED: shadow-default + frosne ───────────────────────────────────────────────
def test_shadow_default_never_omits():
    """KERNE: uden flag udelader eksplorations-armen ALDRIG noget (should_omit == False)."""
    ex._kv_set(ex._STATE_KEY, ex._new_state("kode", "inner voice context"))
    assert ex.is_explore_live() is False
    assert ex.should_omit("kode", "inner voice context") is False


def test_frozen_never_omitted_even_live():
    """Frosne sektioner udelades ALDRIG — heller ikke live, heller ikke hvis de matcher forsøget."""
    ex._kv_set(ex._EXPLORE_FLAG, True)
    ex._kv_set(ex._STATE_KEY, ex._new_state("kode", "pinned identity context"))  # 'identity' = frossen
    assert ex.should_omit("kode", "pinned identity context") is False


def test_live_absent_arm_omits_matching_section():
    ex._kv_set(ex._EXPLORE_FLAG, True)
    ex._kv_set(ex._STATE_KEY, ex._new_state("kode", "mood context"))    # absent-arm default
    assert ex.should_omit("kode", "mood context") is True
    assert ex.should_omit("kode", "anden sektion") is False            # kun kandidaten
    assert ex.should_omit("samtale", "mood context") is False         # kun matchende tur-type


def test_present_arm_does_not_omit():
    ex._kv_set(ex._EXPLORE_FLAG, True)
    st = ex._new_state("kode", "mood context"); st["arm"] = "present"
    ex._kv_set(ex._STATE_KEY, st)
    assert ex.should_omit("kode", "mood context") is False            # present-armen inkluderer


# ── KONTROL-ARMEN: tælling, arm-skift, dom ───────────────────────────────────────────
def test_record_trial_tallies_and_flips_arm():
    ex._kv_set(ex._EXPLORE_FLAG, True)                 # tælling sker kun live (data-integritet)
    st = ex._new_state("kode", "mood context"); st["left"] = 1
    ex._kv_set(ex._STATE_KEY, st)
    # absent-arm: sektionen er IKKE i included_labels (den blev udeladt) → tælles korrekt
    ex.record_trial("kode", ["andet"], "completed")   # 1 good, left→0 → flip til present
    now = ex._kv_get(ex._STATE_KEY, {})
    assert now["arm"] == "present" and now["absent_total"] == 1 and now["absent_good"] == 1


def test_record_trial_ignored_in_shadow():
    """Data-integritet: i shadow udelades intet → intet A/B-data tælles (ellers forurenet)."""
    st = ex._new_state("kode", "mood context")
    ex._kv_set(ex._STATE_KEY, st)                       # flag er OFF (fixture)
    ex.record_trial("kode", ["andet"], "completed")
    assert ex._kv_get(ex._STATE_KEY, {})["absent_total"] == 0   # intet talt


def test_record_trial_rejects_contaminated_arm():
    """Absent-arm men sektionen VAR med (inkonsistent) → forurener ikke tællingen."""
    ex._kv_set(ex._EXPLORE_FLAG, True)
    st = ex._new_state("kode", "mood context")
    ex._kv_set(ex._STATE_KEY, st)
    ex.record_trial("kode", ["mood context", "andet"], "completed")  # sektionen VAR med i absent-arm
    assert ex._kv_get(ex._STATE_KEY, {})["absent_total"] == 0        # afvist (ikke forurenet)


def test_evaluate_dispensable_when_absent_not_worse():
    st = {"tt": "kode", "sec": "mood context", "absent_good": 9, "absent_total": 10,
          "present_good": 8, "present_total": 10}
    v = ex.evaluate_ablation(st)
    assert v["dispensable"] is True            # absent (0.9) ≥ present (0.8) → undværlig


def test_evaluate_load_bearing_when_absent_worse():
    st = {"tt": "kode", "sec": "somatic body", "absent_good": 4, "absent_total": 10,
          "present_good": 9, "present_total": 10}
    v = ex.evaluate_ablation(st)
    assert v["dispensable"] is False           # absent (0.4) < present (0.9) → load-bearing, behold


# ── ANVENDELSE: shadow vs live + §8-gate ─────────────────────────────────────────────
def _finish_with(dispensable_state, *, live: bool):
    ex._kv_set(ex._EXPLORE_FLAG, live)
    ex._finish_ablation(dict(dispensable_state))


def test_dispensable_shadow_records_but_does_not_cut_live():
    """Undværlig + SHADOW → forslag i shadow-key, men live-vægte URØRT (intet skæres)."""
    st = {"tt": "kode", "sec": "mood context", "absent_good": 9, "absent_total": 10,
          "present_good": 8, "present_total": 10}
    _finish_with(st, live=False)
    assert ex._kv_get(ex._SHADOW_KEY, {}).get("kode|mood context") == ex._CUT_WEIGHT
    assert ex._kv_get(ex._WEIGHTS_KEY, {}) == {}          # live URØRT


def test_dispensable_live_cuts_weight():
    """Undværlig + LIVE + §8-gate ok → live-vægt skrevet (< threshold → composer skærer den)."""
    st = {"tt": "kode", "sec": "mood context", "absent_good": 9, "absent_total": 10,
          "present_good": 8, "present_total": 10}
    _finish_with(st, live=True)
    assert ex._kv_get(ex._WEIGHTS_KEY, {}).get("kode|mood context") == ex._CUT_WEIGHT
    # og composeren ville nu skære den (vægt < 0.3, live-flag styres separat)
    from core.services import central_prompt_composer as c
    assert c.get_weight("kode", "mood context") == ex._CUT_WEIGHT


def test_load_bearing_never_cut():
    """Load-bearing → hverken shadow eller live røres (sektionen er vigtig)."""
    st = {"tt": "kode", "sec": "somatic body", "absent_good": 3, "absent_total": 10,
          "present_good": 9, "present_total": 10}
    _finish_with(st, live=True)
    assert ex._kv_get(ex._WEIGHTS_KEY, {}) == {}
    assert ex._kv_get(ex._SHADOW_KEY, {}) == {}


def test_s8_gate_rolls_back_over_budget():
    """§8: for mange lærte snit (> _MAX_CUTS) → gate rollback → INTET nyt live-snit (drift-bound)."""
    # forfyld live med _MAX_CUTS eksisterende snit → næste ville overskride budgettet
    over = {f"tt{i}|sec{i}": 0.2 for i in range(ex._MAX_CUTS)}
    ex._kv_set(ex._WEIGHTS_KEY, dict(over))
    st = {"tt": "kode", "sec": "mood context", "absent_good": 9, "absent_total": 10,
          "present_good": 8, "present_total": 10}
    _finish_with(st, live=True)
    live = ex._kv_get(ex._WEIGHTS_KEY, {})
    assert "kode|mood context" not in live       # gate blokerede det nye snit
    assert len(live) == ex._MAX_CUTS             # uændret


def test_state_cleared_after_finish():
    st = {"tt": "kode", "sec": "mood context", "absent_good": 5, "absent_total": 10,
          "present_good": 5, "present_total": 10}
    _finish_with(st, live=False)
    assert not ex._kv_get(ex._STATE_KEY, {}).get("tt")   # ryddet → nyt forsøg kan starte


def test_tick_is_self_safe():
    out = ex.run_prompt_explore_tick()
    assert out["status"] == "ok" and out["mode"] == "shadow"
