"""Guards for experiment 006: the transfer test and its frozen verdict.

The point of these tests is not that the numbers are pretty. It is that the
falsification thresholds stay the ones that were frozen in the protocol before
the run, and that the verdict is derived from them rather than asserted.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from feltteori_research.experiment_006_order import (
    FALSIFY_MAX_MAE_GAP_FRACTION,
    FALSIFY_MIN_EFFECTIVE_EXPERTS,
    FALSIFY_MIN_WEIGHT_CHANGE,
    EXPERTS,
    MonthlyObservation,
    _adaptive_trace,
    _judge,
    parse_noaa_monthly,
)

RUN = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "exp_006_order"
    / "noaa_20261030"
)

RUN_V2 = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "exp_006_order"
    / "noaa_20261030_v2"
)


def test_thresholds_match_the_frozen_protocol() -> None:
    """The protocol file is the source of truth; the constants must agree."""
    protocol = (
        Path(__file__).resolve().parents[1]
        / "experiments"
        / "exp_006_order"
        / "PROTOCOL.md"
    ).read_text(encoding="utf-8")
    assert "effective experts > 1.5" in protocol
    assert "> 0.05" in protocol
    assert "0.5 %" in protocol
    assert FALSIFY_MIN_EFFECTIVE_EXPERTS == 1.5
    assert FALSIFY_MIN_WEIGHT_CHANGE == 0.05
    assert FALSIFY_MAX_MAE_GAP_FRACTION == 0.005


def test_parser_skips_comments_and_missing_values(tmp_path: Path) -> None:
    source = tmp_path / "sample.csv"
    source.write_text(
        "# a comment\n"
        "year,month,decimal date,average,deseasonalized,ndays,sdev,unc\n"
        "1958,3,1958.2027,315.71,314.44,-1,-9.99,-0.99\n"
        "1958,4,1958.2877,-1,315.16,-1,-9.99,-0.99\n"
        "1958,5,1958.3699,317.45,316.00,20,0.5,0.1\n",
        encoding="utf-8",
    )
    observations, excluded = parse_noaa_monthly(source)
    assert [row.date for row in observations] == ["1958-03", "1958-05"]
    assert excluded["missing"] == 1


def test_judge_fires_when_effective_experts_stay_high() -> None:
    summaries = [
        {"mechanism": "long_continuity_continued", "mae": 1.0,
         "mean_effective_experts": 1.9, "mean_weight_change": 0.001},
        {"mechanism": "cumulative_continuity_continued", "mae": 1.0,
         "mean_effective_experts": 1.0, "mean_weight_change": 0.001},
    ]
    verdicts = _judge(summaries, fixed_mae=1.0)
    assert verdicts["long_continuity_continued"]["falsifies_transfer"] is True
    assert verdicts["cumulative_continuity_continued"]["falsifies_transfer"] is False


def test_judge_does_not_fire_when_lock_in_reproduces() -> None:
    summaries = [
        {"mechanism": "long_continuity_continued", "mae": 1.0,
         "mean_effective_experts": 1.0, "mean_weight_change": 0.0},
        {"mechanism": "cumulative_continuity_continued", "mae": 1.0,
         "mean_effective_experts": 1.0, "mean_weight_change": 0.0},
    ]
    verdicts = _judge(summaries, fixed_mae=1.0)
    assert not any(v["falsifies_transfer"] for v in verdicts.values())


@pytest.mark.skipif(not RUN.exists(), reason="preserved run not present")
def test_preserved_run_records_a_falsified_transfer() -> None:
    results = json.loads((RUN / "exp006_results.json").read_text(encoding="utf-8"))
    assert results["constants_inherited_from"] == "exp005.learning.1"
    assert results["falsification"]["transfer_falsified"] is True
    long_row = next(
        row
        for row in results["mechanism_summaries"]
        if row["mechanism"] == "long_continuity_continued"
    )
    assert long_row["mean_effective_experts"] > FALSIFY_MIN_EFFECTIVE_EXPERTS


def _synthetic_series() -> list[MonthlyObservation]:
    """Months from 1985-01 to 2001-12: 132 warmup + 48 dev + 24 evaluation."""
    rows: list[MonthlyObservation] = []
    year, month = 1985, 1
    for step in range(204):
        rows.append(
            MonthlyObservation(
                year=year,
                month=month,
                decimal_date=year + (month - 0.5) / 12.0,
                value=100.0 + 40.0 * math.sin(step / 7.0) + step * 0.3,
            )
        )
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return rows


def test_reset_fires_exactly_once_at_the_evaluation_boundary() -> None:
    """The guard the previous version lacked: a reset must actually reset.

    Measured 2026-10-30: the first implementation gated the reset on an empty
    trace, which is never true at the boundary. The old test asserted that
    continued and reset were identical — that assertion was the fault wearing
    a guard's clothes. This test asserts the opposite for a retention that can
    still carry history, and checks the reset is not applied repeatedly.
    """
    observations = _synthetic_series()
    continued = _adaptive_trace(observations, 0.99, reset_at_evaluation=False)
    reset = _adaptive_trace(observations, 0.99, reset_at_evaluation=True)

    first_eval = next(i for i, row in enumerate(continued) if row["period"] == "evaluation")
    second_eval = first_eval + 1

    for expert in EXPERTS:
        key = f"weight_{expert}"
        assert float(reset[first_eval][key]) == pytest.approx(1 / 3, abs=1e-12), (
            f"reset did not restart {expert} at uniform weight"
        )
        assert float(continued[first_eval][key]) != pytest.approx(1 / 3, abs=1e-6), (
            "continued must keep its development history, not restart"
        )

    assert any(
        abs(float(continued[first_eval][f"weight_{e}"]) - float(reset[first_eval][f"weight_{e}"]))
        > 1e-12
        for e in EXPERTS
    ), "reset and continued must diverge at the boundary"

    # Fired once, not every evaluation row: the second evaluation weights are
    # no longer uniform because one loss update has already been applied.
    assert any(
        float(reset[second_eval][f"weight_{e}"]) != pytest.approx(1 / 3, abs=1e-6)
        for e in EXPERTS
    ), "reset appears to fire on every evaluation row"


def test_zero_retention_reset_changes_only_the_boundary_row() -> None:
    """Control: with retention 0 the history is one row deep.

    So reset changes exactly the boundary prediction — the single row where
    `retained` still carries the last development loss — and nothing after it.
    This pins the mechanism precisely instead of assuming indifference.
    """
    observations = _synthetic_series()
    continued = _adaptive_trace(observations, 0.0, reset_at_evaluation=False)
    reset = _adaptive_trace(observations, 0.0, reset_at_evaluation=True)
    differing = [
        index
        for index, (left, right) in enumerate(zip(continued, reset))
        if abs(float(left["prediction"]) - float(right["prediction"])) > 1e-12
    ]
    assert len(differing) == 1, f"expected the boundary row only, got {len(differing)}"
    assert continued[differing[0]]["period"] == "evaluation"


@pytest.mark.skipif(not RUN_V2.exists(), reason="corrected run not present")
def test_corrected_run_separates_reset_and_keeps_the_falsification() -> None:
    """The fixed run: continued untouched, reset actually executing."""
    results = json.loads((RUN_V2 / "exp006_results.json").read_text(encoding="utf-8"))
    assert results["falsification"]["transfer_falsified"] is True

    by_name = {row["mechanism"]: row for row in results["mechanism_summaries"]}

    # The bug never touched this branch, so it must reproduce to the digit.
    assert by_name["long_continuity_continued"]["mean_effective_experts"] == (
        pytest.approx(1.8857, abs=1e-4)
    )
    assert by_name["long_continuity_continued"]["mae"] == pytest.approx(
        1.3024, abs=1e-4
    )

    # Reset now runs, and on this source it costs accuracy and flattens weights.
    for base in ("short_continuity", "long_continuity", "cumulative_continuity"):
        assert by_name[f"{base}_reset"]["mae"] > by_name[f"{base}_continued"]["mae"], (
            f"{base}: reset should cost accuracy on this source"
        )
    assert by_name["cumulative_continuity_reset"]["mean_effective_experts"] > (
        by_name["cumulative_continuity_continued"]["mean_effective_experts"]
    )
