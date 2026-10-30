"""Guards for experiment 006: the transfer test and its frozen verdict.

The point of these tests is not that the numbers are pretty. It is that the
falsification thresholds stay the ones that were frozen in the protocol before
the run, and that the verdict is derived from them rather than asserted.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from feltteori_research.experiment_006_order import (
    FALSIFY_MAX_MAE_GAP_FRACTION,
    FALSIFY_MIN_EFFECTIVE_EXPERTS,
    FALSIFY_MIN_WEIGHT_CHANGE,
    _judge,
    parse_noaa_monthly,
)

RUN = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "exp_006_order"
    / "noaa_20261030"
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


@pytest.mark.skipif(not RUN.exists(), reason="preserved run not present")
def test_continued_and_reset_were_indistinguishable_on_this_source() -> None:
    """The second result: reset removed nothing the mechanism was still using."""
    rows = list(
        csv.DictReader((RUN / "exp006_trace.csv").open(encoding="utf-8"))
    )
    by_mechanism: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_mechanism.setdefault(row["mechanism"], []).append(row)
    for base in (
        "one_encounter",
        "short_continuity",
        "long_continuity",
        "cumulative_continuity",
    ):
        continued = by_mechanism[f"{base}_continued"]
        reset = by_mechanism[f"{base}_reset"]
        assert len(continued) == len(reset)
        differences = sum(
            1
            for left, right in zip(continued, reset)
            if abs(float(left["prediction"]) - float(right["prediction"])) > 1e-12
        )
        assert differences == 0, f"{base}: reset changed {differences} predictions"
