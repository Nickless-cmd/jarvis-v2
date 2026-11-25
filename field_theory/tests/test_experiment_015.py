"""Investigation 15: sharpening on the median over time.

The experiment's value rests on five properties that can each be lost silently:

1. **The sharpening must be leader-following.** ``argmax(w) == argmin(retained)``
   in every month. If it fails, "a sharper weight" is not the object being
   measured and the whole report is about something else.
2. **The conditional median must be reported.** A median that reaches 1.000
   because most months sit at exactly 1.000 is a property of the target. The
   conditional median is the only number that can only fall if the mechanism
   improves, and it must be present in the result for every alpha.
3. **The limit must be checked at the hard argmax.** A finite alpha only
   approaches the argmax, so a convergence check at alpha=50 would fail for
   arithmetic reasons and hide a real error.
4. **The error must come from the real predictions.** Reading ``a`` from the
   constructed predictions cancels the outcome. The code test below builds a
   row where the two disagree, so a mutation that swaps them is caught.
5. **The verdict must be reachable.** All conditions are success conditions in
   the same polarity, so ``all()`` can be true.

The last two tests are code tests rather than artifact tests: the frozen
artifact cannot see a code mutation, and Investigation 13 learned that the
hard way.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from feltteori_research.experiment_015_sharp_over_time import (
    _label,
    _ratio,
    _two_medians,
    accumulate_dated,
)

ARTIFACT = (
    Path(__file__).resolve().parents[1]
    / "artifacts/exp_015_sharp_over_time/run_20261125_v1/results.json"
)


@pytest.fixture(scope="module")
def results() -> dict:
    with ARTIFACT.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_skarpningen_er_foelg_den_foerende(results: dict) -> None:
    """argmax(w) == argmin(retained) in every month, or the object is wrong."""
    controls = results["controls"]
    assert controls["leader_equals_argmin"] is True
    assert controls["leader_months"] == controls["leader_total"]
    assert controls["leader_total"] > 30000


def test_identiteten_og_graensen_holder(results: dict) -> None:
    """The error is the weighted mean of its members, and the limit is selection."""
    controls = results["controls"]
    assert controls["identity_holds"] is True
    assert controls["identity_worst_residual"] < 1e-12
    assert controls["limit_reproduces_selection"] is True
    assert controls["limit_worst_gap"] < 1e-12


def test_to_medianer_rapporteres_for_hvert_alpha(results: dict) -> None:
    """The unconditional median alone is the number that can lie."""
    summary = results["summary"]
    assert set(summary) == {"1.0", "2.0", "3.0", "5.0", "10.0", "inf"}
    for entry in summary.values():
        assert entry["conditional_months"] > 0
        assert entry["conditional_median_base"] > 0
        assert entry["conditional_median_sharp"] > 0
        # The conditional set shrinks with alpha. That is itself a result.
        assert entry["conditional_months"] <= entry["months"]


def test_plet_rammerne_stiger_med_skarpheden(results: dict) -> None:
    """The hit share is why the unconditional median falls. It must be reported."""
    summary = results["summary"]
    shares = [summary[label]["hit_share"] for label in ("1.0", "2.0", "3.0", "5.0", "10.0", "inf")]
    assert shares == sorted(shares), shares
    assert shares[0] < 0.10
    assert shares[-1] > 0.55


def test_graensen_vinder_kun_gennem_plet_rammer(results: dict) -> None:
    """The central finding: the limit wins unconditionally and loses conditionally."""
    assert results["limit_gain_unconditional"] > 0.0
    assert results["limit_gain_conditional"] < 0.0
    per_cell = results["limit_per_cell_conditional"]
    assert per_cell["worsened"] > per_cell["improved"], per_cell


def test_moderat_skarpning_forbedrer_den_betingede_median(results: dict) -> None:
    """A gain that survives removing the hits is the mechanism, not the hit rate."""
    gains = results["moderate_gains"]
    assert all(value > 0.0 for value in gains.values()), gains
    summary = results["summary"]
    for label in ("2.0", "3.0", "5.0", "10.0"):
        entry = summary[label]
        assert entry["conditional_median_sharp"] < entry["conditional_median_base"], label


def test_aggregat_konflikten_er_aegte(results: dict) -> None:
    """Two aggregates, two answers. The same alpha must not minimise both."""
    choice = results["aggregate_choice"]
    assert choice["same"] is False
    assert choice["best_by_unconditional_median"] == "inf"
    assert choice["best_by_unconditional_mean"] == "3.0"


def test_gevinsten_holder_i_hvert_aar(results: dict) -> None:
    """No single period carries the median gain."""
    per_year = results["per_year"]
    assert len(per_year) > 20
    assert all(row["sharp_wins"] is True for row in per_year), [
        row["year"] for row in per_year if row["sharp_wins"] is not True
    ]


def test_win_raten_er_under_en_halvdel(results: dict) -> None:
    """Sharpening wins less often than it loses, and still improves the median."""
    rates = results["win_rates"]
    for label, entry in rates.items():
        assert entry["win_rate"] < 0.5, (label, entry["win_rate"])
        assert entry["ties"] > 0


def test_verdict_er_naabart_og_navngiver_fundet(results: dict) -> None:
    """All conditions are success conditions, so all() must be able to be true."""
    conditions = results["conditions"]
    assert all(isinstance(value, bool) for value in conditions.values())
    assert all(conditions.values()), results["conditions_failed"]
    assert results["verdict"] == "moderate_sharpening_wins_over_time_limit_does_not"


# ---- code tests: these can see a mutation the artifact cannot -------------


def test_labelen_haandterer_baade_none_og_strengen_inf() -> None:
    """The limit is carried as both None and "inf"; they must label alike.

    This was a real bug: ``f"{alpha:g}"`` raised on the string, and a label
    that disagrees with itself makes every summary lookup a KeyError.
    """
    assert _label(None) == "inf"
    assert _label("inf") == "inf"
    assert _label(1.0) == "1.0"
    assert _label(3.0) == "3.0"


def test_fejlen_laeses_fra_de_aegte_praediktioner() -> None:
    """A hand-built row where the real predictions disagree with the constructed.

    The constructed prediction is ``outcome + sign*(l_best+delta)*scale``, which
    would give an error that depends on the gap. The real predictions are given
    directly, so the error must not move with the gap at all.
    """
    experts = ("a", "b", "c")
    prepared = [
        {
            "date": "2026-01-01",
            "period": "evaluation",
            "outcome": 10.0,
            "real": {"a": 20.0, "b": 4.0, "c": 13.0},
            "l_best": 0.0,
            "scale": 11.0,
            "sign": {"a": 1.0, "b": 1.0, "c": 1.0},
        }
    ]
    orders = [list(experts)]

    errors = []
    for gap in (0.0, 0.5):
        rows = accumulate_dated(prepared, orders, experts, 0.9, gap)
        errors.append(float(rows[0]["err"]))

    # a = real - outcome = (+10, -6, +3); the constructed path would move with
    # the gap because delta scales with it. The real path does not.
    assert errors[0] == pytest.approx(errors[1]), errors
    assert errors[0] > 0.0


def test_ratio_ved_alpha_et_er_den_uskarpede_vaegt() -> None:
    """alpha=1 must reproduce the unsharpened weight, otherwise the baseline moves."""
    experts = ("a", "b")
    point = {
        "w": {"a": 0.75, "b": 0.25},
        "a": {"a": 2.0, "b": -2.0},
        "err_oracle": 2.0,
    }
    value = _ratio(point, experts, 1.0)
    assert value == pytest.approx(abs(0.75 * 2.0 + 0.25 * -2.0) / 2.0)


def test_ratio_ved_graensen_er_argmax() -> None:
    """The limit must pick the heaviest expert exactly, not approximately."""
    experts = ("a", "b")
    point = {
        "w": {"a": 0.51, "b": 0.49},
        "a": {"a": 2.0, "b": 6.0},
        "err_oracle": 2.0,
    }
    assert _ratio(point, experts, None) == pytest.approx(2.0 / 2.0)


def test_de_to_medianer_er_forskellige_og_ikke_byttet_om() -> None:
    """The unconditional and the conditional median must not be the same number.

    Three of five months sit exactly on the oracle, so the unconditional median
    is 1.0 by construction. The conditional median, over the two months that
    miss, must be 2.5 — not 1.0. A mutation that computes the conditional
    median from the unconditional set is caught here and nowhere else.
    """
    pairs = [(1.0, 1.0), (1.0, 1.0), (1.0, 1.0), (5.0, 2.0), (5.0, 3.0)]
    medians = _two_medians(pairs)
    assert medians["unconditional_median"] == pytest.approx(1.0)
    assert medians["conditional_median_base"] == pytest.approx(5.0)
    assert medians["conditional_median_sharp"] == pytest.approx(2.5)
    assert medians["conditional_months"] == 2
    assert medians["hit_share"] == pytest.approx(0.6)
    # The two numbers must differ, otherwise the test above proves nothing.
    assert medians["conditional_median_sharp"] != medians["unconditional_median"]
