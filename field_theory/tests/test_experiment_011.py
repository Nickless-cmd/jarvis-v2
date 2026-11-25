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
import math
from pathlib import Path

import pytest

RUN = (
    Path(__file__).resolve().parents[1]
    / "artifacts/exp_011_four_measures/run_20261125_v5/results.json"
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
        {
            "effective": [3.0, 3.0, 3.0],
            "dominant": ["a", "a", "a"],
            "top_weight": [1.0, 1.0, 1.0],
            "top_margin": [1.0, 1.0, 1.0],
            "floor": 2.0,
            "rows": 3,
        }
    )
    assert never["occupancy"] == 0.0
    assert never["persistence"] is None
    assert never["recovery"] is not None

    always = _four_measures(
        {
            "effective": [1.0, 1.0, 1.0],
            "dominant": ["a", "a", "a"],
            "top_weight": [1.0, 1.0, 1.0],
            "top_margin": [1.0, 1.0, 1.0],
            "floor": 2.0,
            "rows": 3,
        }
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
            "top_weight": [1.0] * 5,
            "top_margin": [1.0] * 5,
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

    After the sign correction the pair is stronger than the original: both cells
    come from the same source, the same expert set and the same assignment, so
    only ``gap`` and ``retention`` differ. Occupancy matches to 0.003 while
    dominance share reads 0.453 against 0.921 — the opposite ordering from
    identity stability, which reads 0.738 against 0.937. If this test fails, the
    fourth measure has stopped carrying an axis and condition 6 must be reported
    as fired.
    """
    pair = results["condition_6_dominance_share"]["best_pair"]
    assert pair is not None
    assert pair["occupancy_gap"] <= 0.05
    assert pair["share_gap"] >= 0.30
    a, b = pair["a"], pair["b"]

    # The corrected pair isolates the cells to one source, expert set and assignment.
    assert a["source"] == b["source"]
    assert a["expert_set"] == b["expert_set"]
    assert a["assignment"] == b["assignment"]

    assert max(a["dominance_share"], b["dominance_share"]) > 0.85
    assert min(a["dominance_share"], b["dominance_share"]) < 0.55
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
        {
            "effective": [1.0] * len(short),
            "dominant": short,
            "top_weight": [1.0] * len(short),
            "top_margin": [1.0] * len(short),
            "floor": 2.0,
            "rows": len(short),
        }
    )
    long_measures = _four_measures(
        {
            "effective": [1.0] * len(long),
            "dominant": long,
            "top_weight": [1.0] * len(long),
            "top_margin": [1.0] * len(long),
            "floor": 2.0,
            "rows": len(long),
        }
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


def test_den_dominante_ekspert_er_den_mest_vaegtede() -> None:
    """The sign of ``d_t``: the dominant expert must be the one with the largest weight.

    The frozen protocol said ``argmax_e S_t(e)`` — the largest accumulated loss.
    But the weight is ``exp(-LR * (S_t - min S_t))``, so the expert that governs
    the month is the one with the SMALLEST accumulated loss. Measured on SILSO
    over 3198 months: argmax matched the governing expert in 1 month, argmin in
    3198. Every other test in this file passed while the sign was inverted,
    because they all read the same wrong series.
    """
    from feltteori_research.experiment_011_four_measures import _measure_series
    from feltteori_research.experiment_010_rank_drift import (
        _prepare,
        _orders,
        _expert_rows_for,
        EXPERT_SETS,
    )
    from feltteori_research.experiment_005_learning import (
        _normalized_loss,
        parse_silso_monthly,
    )

    source = Path(__file__).resolve().parents[1] / (
        "artifacts/exp_005_independent/silso_20261030_e9a732ca9/silso_monthly_total_v2.csv"
    )
    experts = EXPERT_SETS["original"]
    prepared = _prepare(_expert_rows_for(parse_silso_monthly(source)[0], experts), experts)
    orders = _orders(prepared, experts, "roving")
    series = _measure_series(prepared, 0.9, 0.1, orders, experts)

    # Replay the accumulation and check the recorded dominant against the weights.
    retained = {expert: 0.0 for expert in experts}
    span = len(experts) - 1
    mismatches = 0
    checked = 0
    for row, order in zip(prepared, orders):
        deltas = {expert: 0.1 * rank / span for rank, expert in enumerate(order)}
        minimum = min(retained.values())
        unscaled = {e: math.exp(-1.0 * (retained[e] - minimum)) for e in experts}
        governing = max(experts, key=lambda e: unscaled[e])
        if row["period"] == "evaluation":
            checked += 1
            if series["dominant"][checked - 1] != governing:
                mismatches += 1
        l_best = float(row["l_best"])
        scale = float(row["scale"])
        outcome = float(row["outcome"])
        signs = row["sign"]
        predictions = {
            e: outcome + signs[e] * (l_best + deltas[e]) * scale for e in experts
        }
        losses = {e: _normalized_loss(predictions[e], outcome) for e in experts}
        retained = {e: 0.9 * retained[e] + losses[e] for e in experts}

    assert checked > 100
    assert mismatches == 0, f"{mismatches} af {checked} maaneder pegede paa den forkerte ekspert"


def test_randleddet_er_en_identitet_ikke_en_konvention() -> None:
    """``K - K' = C1 + CT - 1`` holds for every binary sequence, endpoints equal or not.

    This guards a correction that was itself wrong. The identity was reported as
    valid only when the endpoints differ, with 0 otherwise. The unrestricted form
    has zero violations over all 8190 sequences up to length 12; the restricted
    variant fails on the all-collapse state, where K=1 and K'=0 so the difference
    is +1, not 0.
    """
    import itertools

    from feltteori_research.experiment_011_four_measures import _runs

    def counts(flags: list[bool]) -> tuple[int, int]:
        runs = _runs(flags)
        collapse = sum(1 for value, _ in runs if value)
        healthy = sum(1 for value, _ in runs if not value)
        return collapse, healthy

    total = 0
    for length in range(1, 13):
        for bits in itertools.product([False, True], repeat=length):
            total += 1
            collapse, healthy = counts(list(bits))
            predicted = (1 if bits[0] else 0) + (1 if bits[-1] else 0) - 1
            assert collapse - healthy == predicted, (
                f"{''.join('1' if b else '0' for b in bits)}: "
                f"K-K'={collapse - healthy} men C1+CT-1={predicted}"
            )
    assert total == 8190

    # The restricted variant is wrong precisely here: same state at both ends.
    collapse, healthy = counts([True] * 5)
    assert (collapse, healthy) == (1, 0)
    assert collapse - healthy == 1


def test_retention_former_dominansen_uden_at_roere_occupancy(results: dict) -> None:
    """Retention moves dominance share while occupancy stays put.

    The headline pair changes ``gap`` and ``retention`` together, so it isolates
    neither. The grid does contain pairs where only retention moves: hold ``gap``
    fixed and raise retention from 0.9 to 0.99, and occupancy can stay identical
    while dominance share changes by more than 0.20.
    """
    cells = results["cells"]
    pairs: list[tuple[dict, dict]] = []
    for a in cells:
        for b in cells:
            if a is b:
                continue
            if (a["source"], a["expert_set"], a["assignment"], a["gap"]) != (
                b["source"],
                b["expert_set"],
                b["assignment"],
                b["gap"],
            ):
                continue
            if abs(a["retention"] - 0.9) > 1e-12:
                continue
            if abs(b["retention"] - 0.99) > 1e-12:
                continue
            if a["dominance_share"] is None or b["dominance_share"] is None:
                continue
            pairs.append((a, b))

    assert len(pairs) >= 5, f"kun {len(pairs)} par med fast gap og varierende retention"

    isolating = [
        (a, b)
        for a, b in pairs
        if abs(a["occupancy"] - b["occupancy"]) < 0.05
        and abs(a["dominance_share"] - b["dominance_share"]) > 0.20
    ]
    assert len(isolating) >= 5, (
        f"kun {len(isolating)} par isolerer retention: "
        f"{[(a['source'], a['gap'], a['occupancy'], b['occupancy']) for a, b in pairs]}"
    )

    # Strictest case: occupancy identical to three decimals, one variable moved.
    a, b = max(
        isolating, key=lambda p: abs(p[0]["dominance_share"] - p[1]["dominance_share"])
    )
    assert a["occupancy"] == pytest.approx(b["occupancy"], abs=0.05)
    assert abs(a["dominance_share"] - b["dominance_share"]) > 0.20


def test_rangordenen_er_ikke_magten() -> None:
    """The four measures read a ranking, never a distribution.

    Two systems whose weights are constant at 34/33/33 and 60/20/20 return
    identical values on every rank-based measure, so a report built on them
    alone cannot tell a shared power structure from a concentrated one. The
    continuous series must carry what the ranking discards.
    """
    from feltteori_research.experiment_011_four_measures import _four_measures

    def series(top: float, margin: float) -> dict[str, object]:
        return {
            "effective": [2.0] * 12,
            "dominant": ["a"] * 12,
            "top_weight": [top] * 12,
            "top_margin": [margin] * 12,
            "floor": 1.5,
            "rows": 12,
        }

    spread = _four_measures(series(0.34, 0.01))
    held = _four_measures(series(0.60, 0.40))

    # Identical on every rank-based measure.
    assert spread["occupancy"] == held["occupancy"]
    assert spread["dominance_share"] == held["dominance_share"] == 1.0
    assert spread["identity_stability"] == held["identity_stability"] == 1.0
    assert spread["distinct_dominants"] == held["distinct_dominants"] == 1

    # Separated only by the distribution.
    assert held["mean_top_weight"] - spread["mean_top_weight"] == pytest.approx(0.26)
    assert held["mean_top_margin"] - spread["mean_top_margin"] == pytest.approx(0.39)


def test_stabil_rang_med_delt_magt_findes_i_data(results: dict) -> None:
    """The blind spot is not hypothetical: it is measured on real cells.

    A cell can hold the same expert at rank one for the whole window and still
    distribute the weight almost evenly. Any conclusion drawn from dominance
    share alone would call that cell fully concentrated.
    """
    cells = results["cells"]
    stable_but_split = [
        cell
        for cell in cells
        if cell["distinct_dominants"] == 1 and cell["mean_top_weight"] < 0.5
    ]
    assert stable_but_split, "ingen celle har stabil rang med delt magt"

    worst = min(stable_but_split, key=lambda cell: cell["mean_top_weight"])
    assert worst["dominance_share"] == pytest.approx(1.0)
    assert worst["identity_stability"] == pytest.approx(1.0)
    assert worst["mean_top_weight"] < 0.5
    # The weight is spread while the rank is not.
    assert worst["mean_effective_experts"] > 3.0


def _retention_pairs(cells: list[dict]) -> list[tuple[dict, dict]]:
    """Cells that differ in retention alone — same source, set, assignment, gap."""
    groups: dict[tuple, dict[float, dict]] = {}
    for cell in cells:
        key = (cell["source"], cell["expert_set"], cell["assignment"], cell["gap"])
        groups.setdefault(key, {})[cell["retention"]] = cell
    return [
        (by_retention[0.9], by_retention[0.99])
        for by_retention in groups.values()
        if 0.9 in by_retention and 0.99 in by_retention
    ]


def test_retention_former_magten_mere_end_rangen(results: dict) -> None:
    """The answer is conditional, and both halves must stay pinned.

    Across all pairs that differ in retention alone, the distribution moves and
    the rank order largely does not: median change 0.220 against 0.000. The
    reverse case — rank moves while the distribution stands still — does not
    occur anywhere in the grid.
    """
    pairs = _retention_pairs(results["cells"])
    assert len(pairs) == 66, f"forventede 66 par, fandt {len(pairs)}"

    def delta(a: dict, b: dict, field: str) -> float:
        return float(b[field]) - float(a[field])

    share_moves = [abs(delta(a, b, "dominance_share")) for a, b in pairs]
    weight_moves = [abs(delta(a, b, "mean_top_weight")) for a, b in pairs]

    median = lambda values: sorted(values)[len(values) // 2]  # noqa: E731
    assert median(share_moves) < 0.05
    assert median(weight_moves) > 0.20

    rank_still_power_moves = sum(
        1
        for a, b in pairs
        if abs(delta(a, b, "dominance_share")) < 0.05
        and abs(delta(a, b, "mean_top_weight")) > 0.10
    )
    power_still_rank_moves = sum(
        1
        for a, b in pairs
        if abs(delta(a, b, "mean_top_weight")) < 0.05
        and abs(delta(a, b, "dominance_share")) > 0.10
    )
    assert rank_still_power_moves >= 30
    assert power_still_rank_moves == 0, (
        "magten stod stille mens rangen flyttede — asymmetrien holder ikke"
    )


def test_asymmetrien_vender_naar_intet_kollapser(results: dict) -> None:
    """Without collapse the rank order moves most; with collapse the power does.

    This is what makes the answer conditional rather than a ranking of the two
    measures. On the four pairs where occupancy is 0.000 in both cells — so the
    comparison is free of collapse — the rank order moves by 0.32 to 0.47 while
    the top weight moves by only 0.08 to 0.22.
    """
    pairs = _retention_pairs(results["cells"])
    clean = [
        (a, b)
        for a, b in pairs
        if float(a["occupancy"]) == 0.0 and float(b["occupancy"]) == 0.0
    ]
    assert len(clean) == 4, f"forventede 4 kollapsfri par, fandt {len(clean)}"

    for a, b in clean:
        d_share = float(b["dominance_share"]) - float(a["dominance_share"])
        d_weight = float(b["mean_top_weight"]) - float(a["mean_top_weight"])
        # The rank order moves more than the distribution in every one of them.
        assert d_share > 0.30, (a["expert_set"], a["gap"], d_share)
        assert d_weight < d_share, (a["expert_set"], a["gap"], d_weight, d_share)
        # And the effective count falls: the same rank now carries more weight.
        assert float(b["mean_effective_experts"]) < float(a["mean_effective_experts"])


def test_retention_bevaeger_rang_og_magt_forskelligt_i_mekanikken() -> None:
    """The conditional, measured by calling the mechanism rather than reading a run.

    The two data tests above pin what the preserved artefact says. This one pins
    the code: if ``mean_top_weight`` ever becomes a copy of ``dominance_share``,
    the two deltas become equal and the assertion fails. Measured on SILSO with
    the short-memory set under ``roving`` at gap 0.05, where nothing collapses at
    either retention — so the difference is retention alone.
    """
    from feltteori_research.experiment_011_four_measures import (
        _measure_series,
        _four_measures,
    )
    from feltteori_research.experiment_010_rank_drift import (
        _prepare,
        _orders,
        _expert_rows_for,
        EXPERT_SETS,
    )
    from feltteori_research.experiment_005_learning import parse_silso_monthly

    source = Path(__file__).resolve().parents[1] / (
        "artifacts/exp_005_independent/silso_20261030_e9a732ca9/silso_monthly_total_v2.csv"
    )
    experts = EXPERT_SETS["short_memory"]
    prepared = _prepare(_expert_rows_for(parse_silso_monthly(source)[0], experts), experts)
    orders = _orders(prepared, experts, "roving")

    short_series = _measure_series(prepared, 0.9, 0.05, orders, experts)
    long_series = _measure_series(prepared, 0.99, 0.05, orders, experts)
    short = _four_measures(short_series)
    long = _four_measures(long_series)

    # Nothing collapses at this gap, at either retention: the lowest effective
    # count stays above the floor, so occupancy is zero in both cells.
    assert min(short_series["effective"]) > short_series["floor"]
    assert min(long_series["effective"]) > long_series["floor"]
    # The rank order moves more than the distribution here — the uncontested regime.
    d_share = long["dominance_share"] - short["dominance_share"]
    d_weight = long["mean_top_weight"] - short["mean_top_weight"]
    assert d_share > 0.30, d_share
    assert d_weight > 0.10, d_weight
    assert d_weight < d_share, (d_weight, d_share)
