"""Investigation 17: what retention costs when the world shifts.

The experiment's value rests on five properties that can each be lost silently:

1. **The shift is a permutation.** If the swap changed the multiset of
   prediction series, the cell would be a data change rather than a regime
   shift and every number in the report would be about a different object.

2. **The unshifted path is unchanged.** ``prepare_swapped(shifted=False)`` must
   reproduce ``experiment_010._prepare`` exactly, otherwise the shifted and the
   control run diverge before the shift even happens.

3. **Retention 0 remembers exactly one month.** The protocol assumed it
   remembers nothing. It does not: ``retained <- 0*retained + loss`` rebuilds
   the memory from the previous month's loss every step. That is why the
   protocol's first clause fails, and the control that pins it down is what
   turns the failure from a mystery into a measurement.

4. **The mechanism learns from the constructed loss, not the real one.** The
   accumulation updates ``retained`` from ``predictions``, so what moves the
   weight is the imposed gap. Stated here because it is the shared mechanism's
   property and a reader should not have to discover it.

5. **The verdict names a broken control before a hypothesis.** A run whose
   control failed must not be readable as a run whose hypothesis failed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from feltteori_research.experiment_010_rank_drift import _prepare
from feltteori_research.experiment_017_regime_shift import (
    half_life,
    measure_cell,
    prepare_swapped,
)

ARTIFACT = (
    Path(__file__).resolve().parents[1]
    / "artifacts/exp_017_regime_shift/run_20261125_v3/results.json"
)


@pytest.fixture(scope="module")
def results() -> dict:
    with ARTIFACT.open(encoding="utf-8") as handle:
        return json.load(handle)


def _tiny_rows(count: int = 24) -> tuple[list[dict[str, object]], tuple[str, ...]]:
    """Two experts, one clearly better, in the row form ``_prepare`` expects."""
    experts = ("a", "b")
    rows: list[dict[str, object]] = []
    for index in range(count):
        outcome = 100.0 + float(index % 5)
        rows.append(
            {
                "date": f"2000-{index + 1:02d}",
                "period": "evaluation",
                "outcome": outcome,
                "prediction_a": outcome + 1.0,
                "prediction_b": outcome - 2.0,
            }
        )
    return rows, experts


# ---------------------------------------------------------------- code guards


def test_uskiftet_sti_er_identisk_med_prepare() -> None:
    """The control path must be ``_prepare`` byte for byte."""
    rows, experts = _tiny_rows()
    assert prepare_swapped(rows, experts, len(rows) // 2, False) == _prepare(
        rows, experts
    )


def test_skiftet_aendrer_serierne_efter_midten() -> None:
    """Before the swap nothing moves; after it the series are exchanged."""
    rows, experts = _tiny_rows()
    plain = prepare_swapped(rows, experts, len(rows) // 2, False)
    shifted = prepare_swapped(rows, experts, len(rows) // 2, True)
    assert shifted[0]["real"] == plain[0]["real"]
    assert shifted[-1]["real"] != plain[-1]["real"]
    # expert "a" now carries what "b" carried, and the other way round
    assert shifted[-1]["real"]["a"] == plain[-1]["real"]["b"]
    assert shifted[-1]["real"]["b"] == plain[-1]["real"]["a"]


def test_swappet_er_en_permutation() -> None:
    """The multiset of series must be unchanged — otherwise it is a data change."""
    rows, experts = _tiny_rows()
    cell = measure_cell(rows, experts, 0.9, 0.05, "fixed")
    assert cell["permutation_worst"] == pytest.approx(0.0, abs=1e-15)


def test_retention_nul_husker_praecis_en_maaned() -> None:
    """The control that replaced the protocol's false premise.

    At retention 0 the weight for month t is built from month t-1's loss. The
    control recomputes that loss from the constructed prediction and compares.
    """
    rows, experts = _tiny_rows()
    cell = measure_cell(rows, experts, 0.0, 0.05, "fixed")
    assert cell["zero_memory_worst"] == pytest.approx(0.0, abs=1e-12)


def test_skiftet_koster_noget() -> None:
    """A swap that changed nothing would make every excess zero.

    This is the guard that fails if the swap is silently dropped: a mutation
    that makes ``prepare_swapped`` ignore ``shifted`` leaves the excess at zero.
    """
    rows, experts = _tiny_rows()
    cell = measure_cell(rows, experts, 0.9, 0.2, "fixed")
    assert abs(cell["accumulated_excess"]) > 1e-6


def test_identiteten_holder_paa_den_lille_raekke() -> None:
    rows, experts = _tiny_rows()
    cell = measure_cell(rows, experts, 0.9, 0.2, "fixed")
    assert cell["identity_worst"] == pytest.approx(0.0, abs=1e-12)


def test_halveringstid_formel() -> None:
    """``ln(0.5)/ln(r)``: 6.58 months at 0.9, 68.97 at 0.99."""
    assert half_life(0.0) == 0.0
    assert half_life(0.9) == pytest.approx(6.5788, abs=1e-3)
    assert half_life(0.99) == pytest.approx(68.9676, abs=1e-3)
    assert half_life(1.0) == float("inf")


# ------------------------------------------------------------ artefact guards


def test_alle_kontroller_er_groenne(results: dict) -> None:
    controls = results["controls"]
    assert controls["identity_holds"] is True
    assert controls["identity_worst_residual"] == pytest.approx(0.0, abs=1e-12)
    assert controls["swap_is_permutation"] is True
    assert controls["no_swap_is_fixed_point"] is True
    assert controls["zero_retention_remembers_one_month"] is True
    assert controls["zero_retention_memory_residual"] == pytest.approx(0.0, abs=1e-12)


def test_protokollens_foerste_klausul_faldt_og_det_er_resultatet(
    results: dict,
) -> None:
    """The protocol said retention 0 costs exactly nothing. It costs a little.

    The clause is reported as failed rather than quietly repaired, and the
    ordering it stood in for is tested separately as 1b.
    """
    assert results["conditions"]["1_cost_monotone_in_retention"] is False
    assert float(results["retention_medians"]["0.0"]) > 0.0
    assert results["conditions"]["1b_cost_strictly_increasing"] is True


def test_kosten_er_strengt_stigende_i_retention(results: dict) -> None:
    medians = results["retention_medians"]
    assert float(medians["0.0"]) < float(medians["0.9"]) < float(medians["0.99"])


def test_forsinkelsen_vokser_med_retention(results: dict) -> None:
    delays = results["delay_medians"]
    assert float(delays["0.0"]) < float(delays["0.9"]) < float(delays["0.99"])


def test_forsinkelsen_ligger_taet_paa_halveringstiden(results: dict) -> None:
    """H3 held: the measured delay is within a factor of two of the formula."""
    assert results["conditions"]["3_delay_predictable_from_retention"] is True
    assert 0.5 <= float(results["h3_median_ratio"]) <= 2.0


def test_diversitet_reducerer_skaden_men_forlaenger_genopretningen(
    results: dict,
) -> None:
    """H4 failed on its second clause, and the failure is the interesting part.

    Four experts accumulate less excess loss than two, yet take longer to get
    back to the control's rolling error. Both halves are asserted so a later
    run cannot quietly report only the flattering one.
    """
    diversity = results["diversity"]
    assert float(diversity["four_experts_excess"]) < float(
        diversity["two_experts_excess"]
    )
    assert float(diversity["four_experts_recovery"]) > float(
        diversity["two_experts_recovery"]
    )
    assert results["conditions"]["4_diversity_shortens_recovery"] is False


def test_stort_regimeskift_koster_mindre_end_lille(results: dict) -> None:
    """H5 failed in the opposite direction from the prediction.

    The high-contrast half of the cells carries the *smaller* excess loss: a
    large shift is easier to notice than a small one. Asserted as measured, not
    as predicted.
    """
    split = results["contrast_split"]
    assert float(split["high_median"]) < float(split["low_median"])
    assert results["conditions"]["5_contrast_drives_cost"] is False


def test_verdict_navngiver_hypoteser_ikke_kontroller(results: dict) -> None:
    verdict = str(results["verdict"])
    assert verdict.startswith("partial:")
    assert "control_failed" not in verdict
    for name in results["conditions_failed"]:
        assert name in verdict
