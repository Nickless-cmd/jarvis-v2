#!/usr/bin/env python3
"""Post-hoc diagnostic for Investigation 10 — is the *range* the right variable?

NOT part of the frozen protocol and it carries no verdict. It was written after
the run, because the run's own result asked the question: the mean-position drift
predicted the `fixed` threshold to within the grid factor (Q = 3.29-3.54 against
u_crit = 3.13) but missed `roving` by up to 7x (Q up to 22.6).

The candidate explanation is that collapse is driven by the **realised range** of
the accumulated losses, not by the difference of their means. For a deterministic
drift the two coincide; for a churning ranking the range exceeds the
mean-difference, and the mechanism collapses later than the mean predicts.

This script recomputes each cell at its own measured threshold and reports
``LR * (max_e S_e - min_e S_e)`` averaged over the evaluation window, next to
u_crit. If the range is the right variable, that number sits near u_crit for
every cell — including the `roving` cells the formula missed.

Run it from the field_theory directory:

    /opt/conda/envs/ai/bin/python experiments/exp_010_rank_drift/posthoc_range.py \
        --results artifacts/exp_010_rank_drift/run_20261125_v2/results.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from feltteori_research.experiment_005_learning import (  # noqa: E402
    LEARNING_RATE,
    RETENTIONS,
    _normalized_loss,
    parse_silso_monthly,
)
from feltteori_research.experiment_006_order import parse_noaa_monthly  # noqa: E402
from feltteori_research.experiment_009_expert_set import (  # noqa: E402
    EXPERT_SETS,
    THRESHOLD_FRACTION,
    _expert_rows_for,
)
from feltteori_research.experiment_010_rank_drift import (  # noqa: E402
    _critical_argument,
    _orders,
    _prepare,
)

DEFAULT_SILSO = (
    PROJECT_ROOT
    / "artifacts/exp_005_independent/silso_20261030_e9a732ca9/silso_monthly_total_v2.csv"
)
DEFAULT_NOAA = PROJECT_ROOT / "artifacts/exp_006_order/noaa_20261030_v2/noaa_co2_mm_mlo.csv"


def _argument_range(
    prepared: list[dict[str, object]],
    retention: float,
    gap: float,
    orders: list[list[str]],
    experts: tuple[str, ...],
    floor: float,
) -> dict[str, float]:
    """Argument range, collapse occupancy and fluctuation over the evaluation window.

    The range alone is not enough. A constant wide spread and an intermittent one
    can produce the same *mean* effective expert count while meaning completely
    different things, so two distinct statistics are reported next to it:

    ``duty_cycle`` — fraction of evaluation rows below the floor. In ``[0, 1]``.
    ``mean_over_min`` — mean effective count divided by the minimum. ``>= 1``.

    They measure different things and neither implies the other: a count pinned
    above the floor and one pinned below it both give ``mean_over_min`` 1.000,
    while their duty cycles are 0 and 1. Read them together or not at all.
    """
    span = len(experts) - 1
    retained = {expert: 0.0 for expert in experts}
    ranges: list[float] = []
    effective: list[float] = []
    for row, order in zip(prepared, orders):
        minimum = min(retained.values())
        unscaled = {
            expert: math.exp(-LEARNING_RATE * (retained[expert] - minimum))
            for expert in experts
        }
        total = sum(unscaled.values())
        weights = {expert: unscaled[expert] / total for expert in experts}
        if row["period"] == "evaluation":
            ranges.append(LEARNING_RATE * (max(retained.values()) - min(retained.values())))
            effective.append(1.0 / sum(weight * weight for weight in weights.values()))
        deltas = {expert: gap * rank / span for rank, expert in enumerate(order)}
        l_best = float(row["l_best"])  # type: ignore[arg-type]
        # The constructed loss is exactly l_best + delta: the scale factor and the
        # sign cancel inside the normalized loss. Measured in Investigation 8 at
        # 6.7e-16, so it is written directly rather than reconstructed.
        losses = {expert: l_best + deltas[expert] for expert in experts}
        retained = {
            expert: retention * retained[expert] + losses[expert] for expert in experts
        }
    ordered = sorted(effective)
    mean_effective = sum(effective) / len(effective) if effective else 0.0
    min_effective = ordered[0] if ordered else 0.0
    return {
        "mean_range": sum(ranges) / len(ranges) if ranges else 0.0,
        "max_range": max(ranges) if ranges else 0.0,
        "mean_effective": mean_effective,
        "median_effective": ordered[len(ordered) // 2] if ordered else 0.0,
        "min_effective": min_effective,
        "duty_cycle": (
            sum(1 for value in effective if value < floor) / len(effective)
            if effective
            else 0.0
        ),
        "mean_over_min": (mean_effective / min_effective) if min_effective else 0.0,
        "rows": float(len(ranges)),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--silso", default=DEFAULT_SILSO, type=Path)
    parser.add_argument("--noaa", default=DEFAULT_NOAA, type=Path)
    args = parser.parse_args(argv)

    results = json.loads(args.results.read_text(encoding="utf-8"))
    sunspot_observations, _ = parse_silso_monthly(args.silso)
    co2_observations, _ = parse_noaa_monthly(args.noaa)
    observations = {"sunspots": sunspot_observations, "co2": co2_observations}

    cache: dict[tuple[str, str, str], tuple[list[dict[str, object]], list[list[str]]]] = {}
    rows_out: list[dict[str, object]] = []

    for cell in results["thresholds"]:
        measured = cell["measured_threshold"]
        if measured is None:
            continue
        if float(cell["retention"]) >= 1.0:
            continue
        experts = EXPERT_SETS[str(cell["expert_set"])]
        key = (str(cell["source"]), str(cell["expert_set"]), str(cell["assignment"]))
        if key not in cache:
            prepared = _prepare(
                _expert_rows_for(observations[str(cell["source"])], experts), experts
            )
            cache[key] = (prepared, _orders(prepared, experts, str(cell["assignment"])))
        prepared, orders = cache[key]
        floor = THRESHOLD_FRACTION * len(experts)
        measured_range = _argument_range(
            prepared, float(cell["retention"]), float(measured), orders, experts, floor
        )
        u_crit = _critical_argument(len(experts), THRESHOLD_FRACTION)
        rows_out.append(
            {
                "expert_set": cell["expert_set"],
                "experts": len(experts),
                "source": cell["source"],
                "assignment": cell["assignment"],
                "retention_condition": cell["retention_condition"],
                "gap": measured,
                "u_crit": u_crit,
                "mean_range": measured_range["mean_range"],
                "max_range": measured_range["max_range"],
                "ratio_mean": measured_range["mean_range"] / u_crit,
                "mean_effective": measured_range["mean_effective"],
                "min_effective": measured_range["min_effective"],
                "duty_cycle": measured_range["duty_cycle"],
                "invariant_Q": cell["invariant"],
            }
        )

    header = (
        f'{"set":14s} {"src":9s} {"assign":6s} {"cond":22s} {"gap":>8s} '
        f'{"Q":>7s} {"meanR":>7s} {"R/u":>6s} {"meanEff":>8s} {"minEff":>7s} {"duty":>6s}'
    )
    print(header)
    print("-" * len(header))
    for row in rows_out:
        print(
            f'{row["expert_set"]:14s} {row["source"]:9s} {row["assignment"]:6s} '
            f'{row["retention_condition"]:22s} {row["gap"]:8.5f} '
            f'{row["invariant_Q"]:7.3f} {row["mean_range"]:7.3f} {row["ratio_mean"]:6.2f} '
            f'{row["mean_effective"]:8.3f} {row["min_effective"]:7.3f} {row["duty_cycle"]:6.2f}'
        )

    for assignment in ("fixed", "roving"):
        subset = [row for row in rows_out if row["assignment"] == assignment]
        if not subset:
            continue
        duties = [float(row["duty_cycle"]) for row in subset]
        ranges_ratio = [float(row["ratio_mean"]) for row in subset]
        print()
        print(
            f"{assignment}: celler={len(subset)} "
            f"duty_cycle min={min(duties):.2f} max={max(duties):.2f} "
            f"R/u min={min(ranges_ratio):.2f} max={max(ranges_ratio):.2f}"
        )
    print()
    print(
        "laesning: duty_cycle er andelen af evalueringsmaaneder hvor effektive eksperter "
        "ligger under gulvet. Er den ~1.0 i fixed og klart lavere i roving, maaler "
        "'gennemsnitlig effektive eksperter' en ligevagt i det ene tilfaelde og en "
        "arbejdscyklus i det andet — og de to taerskler er ikke samme stoerrelse."
    )


if __name__ == "__main__":
    main()
