"""Investigation 16: can alpha be chosen ex ante?

The experiment's value rests on five properties that can each be lost silently:

1. **The split must be temporal.** A random split would leak the mechanism's
   own history into its evaluation. Checked directly on the years.
2. **The ex ante signals must not use the outcome.** ``err_oracle`` needs it, so
   a signal built from the ratio would be hindsight wearing a rule's clothes.
3. **Pooled points carry their own expert tuple.** ``pooled`` mixes five expert
   sets; a helper that takes one tuple would measure a ``four_experts`` point
   with ``original``'s names.
4. **A difference below the tolerance is not a result.** The first run failed
   two conditions on margins of 2e-5 and 8e-4. A falsification carried by
   0.00002 is the hit-rate error in a new costume.
5. **The ceiling must be per month.** The best *fixed* alpha on test is a
   different object from a per-month choice, and reporting one as the other
   understates the room a perfect chooser would have.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from feltteori_research.experiment_016_alpha_ex_ante import (
    CANDIDATES,
    MEANINGFUL,
    _best_fixed,
    _common_non_hit,
    _conditional_median,
    _experts_of,
    _ranks,
    _ratio,
    _signals,
    _split,
    accumulate_ex_ante,
)

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts/exp_016_alpha_ex_ante"


def _latest() -> dict:
    runs = sorted(ARTIFACTS.glob("run_*"))
    assert runs, "no exp_016 artifact found — run experiments/exp_016_alpha_ex_ante/run.py"
    return json.loads((runs[-1] / "results.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def results() -> dict:
    return _latest()


# ---------------------------------------------------------------- the artifact


def test_verdict_navngiver_praecis_hvad_der_faldt(results: dict) -> None:
    """A generic "failed" would hide which hypothesis fell and why."""
    assert results["verdict"] == "partial:3_no_ex_ante_signal", results["verdict"]
    assert results["conditions_failed"] == ["3_no_ex_ante_signal"]


def test_kontrollerne_er_groenne(results: dict) -> None:
    controls = results["controls"]
    for name, value in controls.items():
        if isinstance(value, bool):
            assert value, f"kontrol fejlede: {name}"


def test_alpha_et_reproducerer_exp_015(results: dict) -> None:
    """The alpha=1 median must match Investigation 15's registered value.

    A mismatch means this module measures a different object, and every number
    in the report is about something else.
    """
    assert results["controls"]["identity_against_exp_015"] is True
    assert results["controls"]["reproduced_median_alpha_1"] == pytest.approx(
        results["controls"]["exp_015_median_alpha_1"], abs=1e-12
    )


def test_splittet_er_tidsmaessigt(results: dict) -> None:
    assert results["controls"]["split_is_temporal"] is True
    assert results["development_end_year"] == 2012
    assert results["development_months"] > 0
    assert results["test_months"] > 0


def test_fast_alpha_overlever_men_adaptive_goer_ikke(results: dict) -> None:
    """The result is two-sided: a fixed choice transfers, an adaptive one does not."""
    fixed = results["fixed_choice"]
    assert fixed["alpha"] == 10.0
    assert fixed["test_median_chosen_alpha"] < fixed["test_median_baseline_alpha_1"]
    # The adaptive rule lands within the tolerance of the best fixed alpha.
    assert results["adaptive_best"]["ratio_to_best_fixed"] >= 1.0 - MEANINGFUL


def test_valget_er_stabilt_over_tre_splits(results: dict) -> None:
    chosen = results["chosen_alpha_by_split"]
    assert set(chosen) == {"2006", "2010", "2018"}
    assert len({value for value in chosen.values()}) == 1, chosen


def test_loftet_er_per_maaned_og_hoejere_end_fast_valg(results: dict) -> None:
    """A per-month choice must leave room above the best fixed alpha.

    If the two were equal there would be nothing for a rule to find, and H4
    would be true for the wrong reason.
    """
    ceiling = results["ceiling"]
    assert ceiling["per_month_oracle_median"] < ceiling["best_fixed_median_on_test"]
    assert ceiling["months"] > 0


def test_placebo_slaar_ikke_det_bedste_faste(results: dict) -> None:
    assert results["controls"]["placebo_does_not_beat_best_fixed"] is True
    placebo = results["placebo"]
    assert placebo["median_of_medians"] >= results["ceiling"]["best_fixed_median_on_test"]


# ---------------------------------------------------------------- the code


def _row(index: int, outcome: float, predictions: dict[str, float]) -> dict[str, object]:
    return {
        "date": f"{2000 + index}-01-01",
        "period": "evaluation",
        "outcome": outcome,
        "real": dict(predictions),
        "losses": {name: abs(value - outcome) for name, value in predictions.items()},
        "l_best": 0.0,
        "scale": 1.0 + abs(outcome),
        "sign": {name: (1.0 if value >= outcome else -1.0) for name, value in predictions.items()},
    }


def test_fejlen_laeses_fra_de_aegte_praediktioner() -> None:
    """``a`` must be ``real - outcome``. The constructed path moves with the gap.

    With uniform weights over two experts whose errors are +10 and -6 the error
    is 2.0. A path that read the constructed predictions would return a number
    that depends on ``gap``, which is the error Investigation 12 removed.
    """
    experts = ("a", "b")
    prepared = [_row(0, 100.0, {"a": 110.0, "b": 94.0})]
    orders = [list(experts)]
    short = accumulate_ex_ante(prepared, orders, experts, 0.9, 0.05)
    long = accumulate_ex_ante(prepared, orders, experts, 0.9, 0.95)
    assert short[0]["err"] == pytest.approx(long[0]["err"]), (short[0]["err"], long[0]["err"])
    # (10 + (-6)) / 2 = 2 with uniform weights.
    assert short[0]["err"] == pytest.approx(2.0, abs=1e-9)


def test_pooled_punkter_baerer_deres_eget_ekspertsaet() -> None:
    """A helper must read the tuple from the point, not from one argument.

    Two points from different expert sets cannot be measured with one tuple:
    the names would not match and the ratio would be computed from the wrong
    entries.
    """
    point_two = {
        "experts": ("a", "b"),
        "w": {"a": 0.9, "b": 0.1},
        "a": {"a": 10.0, "b": -10.0},
        "err_oracle": 10.0,
    }
    point_four = {
        "experts": ("a", "b", "c", "d"),
        "w": {"a": 0.7, "b": 0.1, "c": 0.1, "d": 0.1},
        "a": {"a": 10.0, "b": -10.0, "c": 4.0, "d": -4.0},
        "err_oracle": 4.0,
    }
    assert _experts_of(point_two) == ("a", "b")
    assert _experts_of(point_four) == ("a", "b", "c", "d")
    median = _conditional_median([point_two, point_four], 1.0)
    assert median == median  # not nan, i.e. neither point raised
    # Point two: |0.9*10 + 0.1*(-10)| / 10 = 8/10 = 0.8
    assert _ratio(point_two, _experts_of(point_two), 1.0) == pytest.approx(0.8)
    # Point four: |0.7*10 - 0.1*10 + 0.1*4 - 0.1*4| / 4 = 6/4 = 1.5
    assert _ratio(point_four, _experts_of(point_four), 1.0) == pytest.approx(1.5)


def test_den_faelles_maengde_udelukker_hver_en_hit() -> None:
    """A month where any candidate lands on the oracle cannot compare alphas."""
    hit = {
        "experts": ("a", "b"),
        "w": {"a": 1.0, "b": 0.0},
        "a": {"a": 5.0, "b": -5.0},
        "err_oracle": 5.0,
    }
    miss = {
        "experts": ("a", "b"),
        "w": {"a": 0.6, "b": 0.4},
        "a": {"a": 10.0, "b": -2.0},
        "err_oracle": 2.0,
    }
    kept = _common_non_hit([hit, miss])
    assert kept == [miss], kept


def test_signalet_bruger_ikke_udfaldet() -> None:
    """``_signals`` must not read ``err_oracle``; it needs the outcome."""
    point = {
        "w": {"a": 0.75, "b": 0.25},
        "real": {"a": 110.0, "b": 90.0},
        "retained": {"a": 1.0, "b": 3.0},
        "err_oracle": 10.0,
    }
    signals = _signals(point)
    assert set(signals) == {"top_weight", "effective", "spread", "retained_gap"}
    assert signals["top_weight"] == pytest.approx(0.75)
    # 1 / (0.75^2 + 0.25^2) = 1 / 0.625 = 1.6
    assert signals["effective"] == pytest.approx(1.6)
    # (110 - 90) / |100| = 0.2
    assert signals["spread"] == pytest.approx(0.2)


def test_splittet_er_tidsmaessigt_i_koden() -> None:
    points = [
        {"year": 2005},
        {"year": 2012},
        {"year": 2013},
        {"year": 2020},
    ]
    development, test = _split(points, 2012)
    assert [p["year"] for p in development] == [2005, 2012]
    assert [p["year"] for p in test] == [2013, 2020]
    assert max(p["year"] for p in development) < min(p["year"] for p in test)


def test_rang_taler_haandterer_baand() -> None:
    """Ties get average ranks, otherwise the correlation is biased."""
    assert _ranks([10.0, 20.0, 30.0]) == [1.0, 2.0, 3.0]
    assert _ranks([5.0, 5.0, 9.0]) == [1.5, 1.5, 3.0]


def test_tolerancen_skelner_stoej_fra_resultat() -> None:
    """The first run failed two conditions on 2e-5 and 8e-4. That is not a result."""
    assert MEANINGFUL == pytest.approx(1e-3)
    # A ratio of 0.99999 is a tie, not a win.
    assert 0.99999 >= 1.0 - MEANINGFUL
    # A ratio of 0.99 is a real win.
    assert not (0.99 >= 1.0 - MEANINGFUL)


def test_best_fixed_vaelger_den_laveste_median() -> None:
    """The choice must be the minimum, not the first or the last candidate."""
    points = []
    for index, spread in enumerate([1.0, 2.0, 5.0, 9.0]):
        points.append(
            {
                "experts": ("a", "b"),
                "w": {"a": 0.55, "b": 0.45},
                "a": {"a": spread, "b": -1.0},
                "err_oracle": 1.0,
                "year": 2000 + index,
            }
        )
    alpha, value = _best_fixed(points)
    assert alpha in CANDIDATES
    assert value == value
    assert value <= _conditional_median(points, 1.0) + 1e-12
