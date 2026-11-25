"""Investigation 11: four measures, and two of them turned out to be one.

The experiment's value rests on four properties that can each be lost silently:

1. **The three first measures must stay bound.** ``O = P/(P+R)`` is not an
   empirical regularity, it is an identity. If a future edit breaks it, the three
   measures have become independent and the finding in the report is wrong. The
   test pins the residual at floating-point zero.

2. **An undefined measure must never become zero.** 101 of 132 cells have
   occupancy 0 or 1, and on those persistence or recovery does not exist. The
   distinction between "never collapses" and "always collapsed" is the exact one
   Investigation 10 lost when ``mean_over_min`` read 1.000 for both.

3. **Dominance share must keep separating what identity stability merges.** The
   frozen definition divides by the window length and so shrinks with it. If a
   future edit replaces ``dominance_share`` with ``identity_stability`` in the
   pair test, the fourth measure stops carrying an axis and the test below fails.

4. **The mechanism must be Investigation 10's.** Occupancy here must equal its
   ``duty_cycle`` on every shared cell, or the two investigations are measuring
   different things and cannot be compared.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

RUN = (
    Path(__file__).resolve().parents[1]
    / "artifacts/exp_011_four_measures/run_20261125_v2/results.json"
)


@pytest.fixture(scope="module")
def results() -> dict:
    if not RUN.exists():
        pytest.skip(f"preserved run not present: {RUN}")
    return json.loads(RUN.read_text(encoding="utf-8"))


def test_kontrollerne_bestaar(results: dict) -> None:
    """No measure may carry a verdict unless every control passed."""
    assert results["controls_passed"] is True, results["control"]
    assert results["control"]["occupancy"]["passed"] is True
    assert results["control"]["series_reconstructs"]["passed"] is True
    assert results["control"]["runs_maximal"]["passed"] is True


def test_occupancy_er_investigation_10s_duty_cycle(results: dict) -> None:
    """The new series must measure the same mechanism as the aggregate it replaces."""
    for cell in results["cells"]:
        assert cell["occupancy_difference"] <= 1e-12, cell


def test_identiteten_holder_paa_hver_maalt_celle(results: dict) -> None:
    """P/(P+R) = O*K'/(O*K'+(1-O)*K) — the general form, every cell with both defined."""
    checked = 0
    for cell in results["cells"]:
        occupancy = float(cell["occupancy"])
        persistence = cell["persistence"]
        recovery = cell["recovery"]
        if persistence is None or recovery is None:
            continue
        collapse_runs = int(cell["collapse_runs"])
        healthy_runs = int(cell["healthy_runs"])
        left = persistence / (persistence + recovery)
        right = (occupancy * healthy_runs) / (
            occupancy * healthy_runs + (1.0 - occupancy) * collapse_runs
        )
        assert abs(left - right) <= 1e-12, cell
        checked += 1
    assert checked >= 20, f"too few cells exercised the identity: {checked}"


def test_den_snaevre_form_holder_hvor_kaederne_er_lip(results: dict) -> None:
    """Where K = K' the identity reduces to O = P/(P+R), exactly."""
    checked = 0
    for cell in results["cells"]:
        if cell["identity_residual"] is None:
            continue
        assert float(cell["identity_residual"]) <= 1e-12, cell
        checked += 1
    assert checked >= 5, f"too few cells exercised the narrow form: {checked}"


def test_runs_er_maksimale_og_taeller_rigtigt() -> None:
    """Run counting: contiguous blocks, in order, boundaries respected."""
    from feltteori_research.experiment_011_four_measures import _runs

    assert _runs([]) == []
    assert _runs([True]) == [(True, 1)]
    assert _runs([True, True, False, True]) == [(True, 2), (False, 1), (True, 1)]
    assert _runs([False, False, False]) == [(False, 3)]
    # A single transition must not be merged into one run.
    assert len(_runs([False, True])) == 2


def test_udefineret_maal_er_ikke_nul() -> None:
    """A cell that never collapses has no persistence — None, never 0.0."""
    from feltteori_research.experiment_011_four_measures import _four_measures

    never = _four_measures(
        {"effective": [3.0, 3.0, 3.0], "dominant": ["a", "a", "a"], "floor": 2.0, "rows": 3}
    )
    assert never["occupancy"] == 0.0
    assert never["persistence"] is None
    assert never["recovery"] is not None

    always = _four_measures(
        {"effective": [1.0, 1.0, 1.0], "dominant": ["a", "a", "a"], "floor": 2.0, "rows": 3}
    )
    assert always["occupancy"] == 1.0
    assert always["recovery"] is None
    assert always["persistence"] is not None


def test_handregnet_eksempel_giver_de_fire_maal() -> None:
    """One sequence, four measures, computed by hand.

    E = [3, 3, 1, 1, 3] with floor 2. Collapsed flags: F F T T F.
    occupancy 2/5 = 0.4; collapse runs = one of length 2 -> persistence 2.0;
    healthy runs = 2 and 1 -> recovery 1.5; dominants all 'a' -> stability 1.0.
    """
    from feltteori_research.experiment_011_four_measures import _four_measures

    measures = _four_measures(
        {
            "effective": [3.0, 3.0, 1.0, 1.0, 3.0],
            "dominant": ["a", "a", "a", "a", "a"],
            "floor": 2.0,
            "rows": 5,
        }
    )
    assert measures["occupancy"] == pytest.approx(0.4)
    assert measures["persistence"] == pytest.approx(2.0)
    assert measures["recovery"] == pytest.approx(1.5)
    assert measures["identity_stability"] == pytest.approx(1.0)
    assert measures["collapse_runs"] == 1
    assert measures["healthy_runs"] == 2
    assert measures["longest_collapse"] == 2
    assert measures["identity_residual"] is None  # K != K', so not asserted


def test_dominance_share_skelner_hvor_identitet_ikke_goer(results: dict) -> None:
    """The finding itself: same occupancy, different continuity.

    The frozen measure reads the two cells below as nearly identical (0.950 vs
    1.000). Dominance share separates them completely (0.525 vs 1.000). If this
    test fails, the fourth measure has stopped carrying an axis and condition 6
    must be reported as fired.
    """
    pair = results["condition_6_dominance_share"]["best_pair"]
    assert pair is not None
    assert pair["occupancy_gap"] <= 0.05
    assert pair["share_gap"] >= 0.30
    a, b = pair["a"], pair["b"]
    assert max(a["dominance_share"], b["dominance_share"]) == pytest.approx(1.0)
    assert min(a["dominance_share"], b["dominance_share"]) <= 0.6
    # And the frozen measure does NOT separate them by the same margin.
    assert abs(a["identity_stability"] - b["identity_stability"]) < 0.30


def test_identity_stability_skrumper_med_vinduet_men_share_goer_ikke() -> None:
    """The defect in the frozen definition, pinned so it cannot come back silently.

    The same 50/50 rotation repeated over twice the window keeps dominance share
    at 0.5 while identity stability drifts — because it divides by T-1.
    """
    from feltteori_research.experiment_011_four_measures import _four_measures

    short = ["a"] * 10 + ["b"] * 10
    long = short + short
    short_measures = _four_measures(
        {"effective": [1.0] * len(short), "dominant": short, "floor": 2.0, "rows": len(short)}
    )
    long_measures = _four_measures(
        {"effective": [1.0] * len(long), "dominant": long, "floor": 2.0, "rows": len(long)}
    )
    assert short_measures["dominance_share"] == pytest.approx(0.5)
    assert long_measures["dominance_share"] == pytest.approx(0.5)
    assert short_measures["identity_stability"] > long_measures["identity_stability"]


def test_fixed_er_identitetsstabil(results: dict) -> None:
    """In fixed the rank order never changes, so the dominant expert never changes."""
    condition = results["condition_4_fixed_stability"]
    assert condition["cells_checked"] >= 40
    assert condition["unstable"] == []


def test_ingen_udefineret_maal_rapporteret_som_nul(results: dict) -> None:
    """Condition 5 must not fire: undefined stays undefined."""
    assert results["condition_5_undefined"]["fired"] is False
    assert results["condition_5_undefined"]["offenders"] == []
