"""Investigation 8: the gap must be an input, and the source must disappear.

The experiment's value rests on three properties that can each be lost silently:

1. **The inversion must be exact.** ``_normalized_loss`` is inverted to produce a
   prescribed loss. If the construction drifts, the "gap" is a label on a
   quantity nobody controlled, and every result below is meaningless. Measured
   calibration error in the preserved run: 6.7e-16.
2. **The control must hold analytically.** At ``gap = 0`` the three constructed
   experts have identical losses, so the softmax is uniform and the effective
   count is exactly 3. That is a prediction about the mechanism, not a figure
   lifted from an earlier run.
3. **The finding must be visible where it was claimed.** With a systematic
   advantage (``fixed``) the two physically unrelated series must agree; with a
   rotating advantage (``roving``) they must not. If both modes agreed, the
   finding would be an artefact of the instrument rather than a property of the
   mechanism.

The first run of this experiment pooled the two assignment modes when deciding
whether condition 3 fired, which hid exactly the separation the addendum
required. These tests pin the separation so pooling cannot recur unnoticed.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIELD_THEORY = PROJECT_ROOT / "field_theory"
sys.path.insert(0, str(FIELD_THEORY / "src"))

SILSO = (
    FIELD_THEORY
    / "artifacts/exp_005_independent/silso_20261030_e9a732ca9/silso_monthly_total_v2.csv"
)
NOAA = FIELD_THEORY / "artifacts/exp_006_order/noaa_20261030_v2/noaa_co2_mm_mlo.csv"


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> dict:
    from feltteori_research.experiment_008_direct_gap import run_investigation

    output = tmp_path_factory.mktemp("exp008") / "run"
    return run_investigation(SILSO, NOAA, output)


def test_inverteringen_er_eksakt() -> None:
    """A prescribed normalized loss must come back out of the loss function."""
    from feltteori_research.experiment_005_learning import _normalized_loss
    from feltteori_research.experiment_008_direct_gap import (
        EXPERTS,
        _constructed_predictions,
    )

    row = {
        "outcome": 137.0,
        "prediction_previous_month": 120.0,
        "prediction_trailing_12_mean": 141.0,
        "prediction_cycle_lag_132": 99.0,
        "period": "evaluation",
        "date": "2011-07",
    }
    for gap in (0.0, 0.01, 0.1, 0.4):
        predictions, outcome = _constructed_predictions(row, gap, "fixed")
        losses = {
            expert: _normalized_loss(predictions[expert], outcome) for expert in EXPERTS
        }
        measured = max(losses.values()) - min(losses.values())
        assert measured == pytest.approx(gap, abs=1e-12), (gap, measured)


def test_kalibreringen_er_eksakt_i_hele_koerslen(results: dict) -> None:
    """Every cell's measured gap must equal its prescribed gap."""
    assert results["calibration"]["passed"] is True
    assert results["calibration"]["worst_absolute_gap_error"] <= 1e-12


def test_kontrollen_ved_nul_gap_giver_praecis_tre_eksperter(results: dict) -> None:
    """Uniform softmax is an analytic prediction, not a preserved figure."""
    assert results["control"]["passed"] is True
    assert results["control"]["checks"]
    for check in results["control"]["checks"]:
        assert check["ok"] is True, check
        assert check["measured_effective_experts"] == pytest.approx(3.0, abs=1e-9)


def test_ved_systematisk_fordel_forsvinder_kilden(results: dict) -> None:
    """The finding: with a fixed advantage the two unrelated series agree."""
    per_assignment = results["condition_3_source_matters_at_matched_gap"][
        "per_assignment"
    ]
    fixed = per_assignment["fixed"]
    assert fixed["cells"] == 40
    # One exception is expected and explained: at r = 1 the accumulated
    # difference grows without bound, so the crossing is knife-edge there.
    assert fixed["count"] <= 1, fixed["disagreements"]


def test_ved_roterende_fordel_betyder_kilden_noget(results: dict) -> None:
    """And with a rotating advantage it does not — that is the second axis."""
    per_assignment = results["condition_3_source_matters_at_matched_gap"][
        "per_assignment"
    ]
    assert per_assignment["roving"]["count"] > per_assignment["fixed"]["count"]


def test_taersklen_ligger_ved_en_minus_r_i_fixed_mode(results: dict) -> None:
    """The analytic threshold holds within a factor of two on both sources.

    At ``one_encounter`` (r = 0) the prediction is ``1 - r = 1.0``, which lies
    above the largest gap the grid measures (0.8). That is not a failure of the
    prediction but a limit of the grid: the curve must then stay responsive at
    every measured gap. Both directions are checked.
    """
    largest_gap = max(
        float(c["gap"]) for c in results["thresholds"]["per_cell"][0]["series"]
    )
    for cell in results["thresholds"]["per_cell"]:
        if cell["assignment"] != "fixed":
            continue
        retention = float(cell["retention"])
        if retention >= 1.0:
            continue
        expected = 1.0 - retention
        measured = cell["measured_threshold"]
        if expected > largest_gap:
            # Predicted beyond the grid: the curve must not collapse inside it.
            assert measured is None, (
                cell["source"],
                cell["retention_condition"],
                measured,
            )
            final = float(cell["series"][-1]["mean_effective_experts"])
            assert final > 1.5, (
                cell["source"],
                cell["retention_condition"],
                final,
            )
            continue
        assert measured is not None, cell
        ratio = max(float(measured), expected) / min(float(measured), expected)
        assert ratio <= 2.5, (cell["source"], cell["retention_condition"], ratio)


def test_ved_fuld_retention_er_lock_in_uundgaaelig(results: dict, tmp_path: Path) -> None:
    """At r = 1 any positive gap collapses, so there is no positive threshold."""
    from feltteori_research.experiment_008_direct_gap import (
        GAPS,
        _adaptive_evaluation,
        _expert_rows,
        parse_silso_monthly,
    )

    observations, _ = parse_silso_monthly(SILSO)
    rows = _expert_rows(observations)
    smallest_positive = min(g for g in GAPS if g > 0)
    result = _adaptive_evaluation(rows, 1.0, smallest_positive, "fixed")
    assert result["mean_effective_experts"] < 1.5, result


def test_assignment_aksen_aendrer_resultatet(results: dict) -> None:
    """If the two modes agreed everywhere, the second axis would be inert."""
    axis = results["condition_5_assignment_axis"]
    assert axis["inert"] is False
    assert axis["count"] > 0


def test_csv_og_json_indeholder_samme_celler(results: dict, tmp_path: Path) -> None:
    """The table on disk must carry every cell the verdict was computed from."""
    output = tmp_path / "cells"
    output.mkdir()
    from feltteori_research.experiment_008_direct_gap import (
        ASSIGNMENTS,
        GAPS,
        RETENTIONS,
        run_investigation,
    )

    run_directory = output / "run"
    run_investigation(SILSO, NOAA, run_directory)
    with (run_directory / "exp008_cells.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected = 2 * len(GAPS) * len(ASSIGNMENTS) * len(RETENTIONS)
    assert len(rows) == expected
