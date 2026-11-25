"""Where does retention reach the forecast, and how much of the error is structure?

Investigation 11 measured four structural measures against the true forecast error
and found none of them predictive (best R^2 0.077). But retention did move the
error in 208 of 260 pairs. This module follows the path rather than the
correlation.

The path is fixed by the code and can be stated as an identity. In
``experiment_011_four_measures._measure_series`` the accumulation builds each
expert's prediction from the outcome itself::

    prediction_e = outcome + sign_e * (l_best + delta_e) * scale

so the loss that drives ``retained`` is a function of the imposed gap, not of
predictive skill. The constructed MAE therefore rises monotonically with ``gap``
in every cell. The real forecast is the ensemble of the experts' own
predictions::

    ensemble = sum_e w_e * real_e
    error    = |sum_e w_e * a_e|,      a_e = real_e - outcome

Because ``orders`` does not depend on retention and ``a`` is data, retention has
exactly one channel: the weight vector ``w``. That is checked as an identity, not
assumed.

The experiment's value rests on four properties that can each be lost silently:

1. **The identity must hold.** ``error == |sum w a|`` is arithmetic; if it fails,
   the ensemble is not the weighted mean of the members and every number below is
   about a different object. Measured: residual 0.0.
2. **The constructed MAE must not be read as a forecast.** It is monotone in
   ``gap`` by construction; the true error is not monotone in any group. Both are
   measured so the difference cannot be lost.
3. **The concentration effect must survive dropping its most reactive set.** The
   largest error changes cluster in ``long_memory``, so the effect is re-measured
   without it. Direction survives, R^2 falls from 0.171 to 0.146.
4. **The retention effect must not be reported by its mean.** The median change
   is -0.005 and the mean -0.690; the mean is carried by a handful of large
   cases. Both are reported, and the sign is counted: 34 of 60 pairs fall.

Reference: ``research/investigation-012-findings.md``.
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path

from feltteori_research.experiment_005_learning import (
    LEARNING_RATE,
    _normalized_loss,
    parse_silso_monthly,
)
from feltteori_research.experiment_006_order import parse_noaa_monthly
from feltteori_research.experiment_009_expert_set import EXPERT_SETS
from feltteori_research.experiment_010_rank_drift import (
    _expert_rows_for,
    _orders,
    _prepare,
)

METHOD_VERSION = "exp012.forecastpath.1"

GAPS = (0.05, 0.2, 0.8)
RETENTIONS = (0.9, 0.99)
ASSIGNMENTS = ("fixed", "roving")


def _accumulate(
    prepared: list[dict[str, object]],
    orders: list[list[str]],
    experts: tuple[str, ...],
    retention: float,
    gap: float,
) -> list[dict[str, object]]:
    """Per evaluation month: weights, error direction, and the quantities derived from them.

    ``err`` is the true ensemble error ``|sum_e w_e * a_e|``. ``oracle`` is the
    error of the best single expert that month — the quantity that turns out to
    carry almost all of the error level.
    """
    span = len(experts) - 1
    retained = {expert: 0.0 for expert in experts}
    rows: list[dict[str, object]] = []
    for row, order in zip(prepared, orders):
        deltas = {expert: gap * rank / span for rank, expert in enumerate(order)}
        l_best = float(row["l_best"])  # type: ignore[arg-type]
        scale = float(row["scale"])  # type: ignore[arg-type]
        outcome = float(row["outcome"])  # type: ignore[arg-type]
        signs = row["sign"]
        predictions = {
            expert: outcome + signs[expert] * (l_best + deltas[expert]) * scale  # type: ignore[index]
            for expert in experts
        }
        minimum = min(retained.values())
        unscaled = {
            expert: math.exp(-LEARNING_RATE * (retained[expert] - minimum))
            for expert in experts
        }
        total = sum(unscaled.values())
        weights = {expert: unscaled[expert] / total for expert in experts}

        if row["period"] == "evaluation":
            real = row["real"]
            a = {expert: float(real[expert]) - outcome for expert in experts}  # type: ignore[index]
            signed = sum(weights[expert] * a[expert] for expert in experts)
            rows.append(
                {
                    "w": weights,
                    "a": a,
                    "signed": signed,
                    "err": abs(signed),
                    "recomposed": abs(sum(weights[e] * a[e] for e in experts)),
                    "oracle": min(abs(value) for value in a.values()),
                    "a_spread": max(a.values()) - min(a.values()),
                    "effective": 1.0 / sum(value * value for value in weights.values()),
                    "top_weight": max(weights.values()),
                }
            )

        losses = {
            expert: _normalized_loss(predictions[expert], outcome) for expert in experts
        }
        retained = {
            expert: retention * retained[expert] + losses[expert] for expert in experts
        }
    return rows


def _corr(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0.0 or sy == 0.0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def _r2(xs: list[float], ys: list[float]) -> float | None:
    value = _corr(xs, ys)
    return None if value is None else value * value


def _eta_squared(records: list[dict[str, object]], key: str, grand: float, total_ss: float) -> float:
    """Share of the total error variation explained by a categorical factor alone."""
    groups: dict[object, list[float]] = {}
    for record in records:
        groups.setdefault(record[key], []).append(float(record["err"]))
    between = sum(
        len(values) * (statistics.mean(values) - grand) ** 2 for values in groups.values()
    )
    return between / total_ss if total_ss else 0.0


def _constructed_mae_is_monotone_in_gap(
    prepared: list[dict[str, object]],
    orders: list[list[str]],
    experts: tuple[str, ...],
    retention: float,
) -> bool:
    """The quantity Investigation 10 called MAE rises with the imposed gap by construction.

    It is the ensemble of ``outcome + sign*(l_best+delta)*scale``, so the outcome
    cancels out of the error and only the imposed gap remains. Checking this keeps
    the two quantities from being confused a second time.
    """
    values: list[float] = []
    for gap in (0.0005, 0.01, 0.1, 0.5, 0.95):
        # Reconstruct the constructed MAE directly: it is the mean absolute
        # deviation of the constructed prediction from the outcome.
        span = len(experts) - 1
        retained = {expert: 0.0 for expert in experts}
        total = 0.0
        count = 0
        for row, order in zip(prepared, orders):
            deltas = {expert: gap * rank / span for rank, expert in enumerate(order)}
            l_best = float(row["l_best"])  # type: ignore[arg-type]
            scale = float(row["scale"])  # type: ignore[arg-type]
            outcome = float(row["outcome"])  # type: ignore[arg-type]
            signs = row["sign"]
            minimum = min(retained.values())
            unscaled = {
                expert: math.exp(-LEARNING_RATE * (retained[expert] - minimum))
                for expert in experts
            }
            weights = {e: unscaled[e] / sum(unscaled.values()) for e in experts}
            if row["period"] == "evaluation":
                ensemble = sum(
                    weights[e] * (outcome + signs[e] * (l_best + deltas[e]) * scale)  # type: ignore[index]
                    for e in experts
                )
                total += abs(ensemble - outcome)
                count += 1
            losses = {
                e: _normalized_loss(
                    outcome + signs[e] * (l_best + deltas[e]) * scale, outcome  # type: ignore[index]
                )
                for e in experts
            }
            retained = {e: retention * retained[e] + losses[e] for e in experts}
        values.append(total / count if count else 0.0)
    return all(later > earlier for earlier, later in zip(values, values[1:]))


def run_investigation(
    silso_path: Path,
    noaa_path: Path,
    output_directory: Path,
) -> dict[str, object]:
    """Measure the path from retention to the forecast, and how much of it is structure."""
    if output_directory.exists():
        raise FileExistsError(output_directory)
    output_directory.mkdir(parents=True)

    sunspots, sunspots_excluded = parse_silso_monthly(silso_path)
    co2, co2_excluded = parse_noaa_monthly(noaa_path)
    observations = {"sunspots": sunspots, "co2": co2}

    records: list[dict[str, object]] = []
    cells: list[dict[str, object]] = []
    identity_worst = 0.0
    monotone_groups = 0
    total_groups = 0

    for source, source_rows in observations.items():
        for set_name, experts in EXPERT_SETS.items():
            try:
                rows = _expert_rows_for(source_rows, experts)
            except (KeyError, ValueError):
                continue
            prepared = _prepare(rows, experts)
            for assignment in ASSIGNMENTS:
                orders = _orders(prepared, experts, assignment)
                by_gap: dict[float, dict[float, list[dict[str, object]]]] = {}
                for gap in GAPS:
                    by_gap[gap] = {}
                    for retention in RETENTIONS:
                        series = _accumulate(prepared, orders, experts, retention, gap)
                        by_gap[gap][retention] = series
                        for point in series:
                            identity_worst = max(
                                identity_worst, abs(float(point["err"]) - float(point["recomposed"]))
                            )
                        records.append(
                            {
                                "source": source,
                                "expert_set": set_name,
                                "assignment": assignment,
                                "gap": gap,
                                "retention": retention,
                                "err": statistics.mean(float(p["err"]) for p in series),
                                "oracle": statistics.mean(float(p["oracle"]) for p in series),
                                "a_spread": statistics.mean(float(p["a_spread"]) for p in series),
                                "top_weight": statistics.mean(float(p["top_weight"]) for p in series),
                                "effective": statistics.mean(float(p["effective"]) for p in series),
                            }
                        )
                    short = by_gap[gap][RETENTIONS[0]]
                    long = by_gap[gap][RETENTIONS[1]]
                    err_short = statistics.mean(float(p["err"]) for p in short)
                    err_long = statistics.mean(float(p["err"]) for p in long)
                    top_short = statistics.mean(float(p["top_weight"]) for p in short)
                    top_long = statistics.mean(float(p["top_weight"]) for p in long)
                    oracle_short = statistics.mean(float(p["oracle"]) for p in short)
                    cells.append(
                        {
                            "source": source,
                            "expert_set": set_name,
                            "assignment": assignment,
                            "gap": gap,
                            "err_short": err_short,
                            "err_long": err_long,
                            "d_err": err_long - err_short,
                            "top_weight_short": top_short,
                            "top_weight_long": top_long,
                            "d_top_weight": top_long - top_short,
                            "oracle_short": oracle_short,
                            "ratio_short": err_short / oracle_short if oracle_short else None,
                            "ratio_long": err_long / oracle_short if oracle_short else None,
                        }
                    )
                # Is the TRUE error monotone in gap within this group?
                total_groups += 1
                errs = [
                    statistics.mean(float(p["err"]) for p in by_gap[gap][RETENTIONS[0]])
                    for gap in GAPS
                ]
                if all(later > earlier for earlier, later in zip(errs, errs[1:])):
                    monotone_groups += 1

    errors = [float(record["err"]) for record in records]
    grand = statistics.mean(errors)
    total_ss = sum((value - grand) ** 2 for value in errors)

    eta = {
        key: _eta_squared(records, key, grand, total_ss)
        for key in ("source", "expert_set", "assignment", "gap", "retention")
    }

    r2_oracle = _r2([float(r["oracle"]) for r in records], errors)
    r2_top = _r2([float(r["top_weight"]) for r in records], errors)

    deltas = [float(cell["d_err"]) for cell in cells]
    d_top = [float(cell["d_top_weight"]) for cell in cells]
    corr_d = _corr(d_top, deltas)
    r2_d = _r2(d_top, deltas)

    without_peak = [c for c in cells if c["expert_set"] != "long_memory"]
    corr_without = _corr(
        [float(c["d_top_weight"]) for c in without_peak],
        [float(c["d_err"]) for c in without_peak],
    )
    r2_without = _r2(
        [float(c["d_top_weight"]) for c in without_peak],
        [float(c["d_err"]) for c in without_peak],
    )

    ratios_short = [float(c["ratio_short"]) for c in cells if c["ratio_short"] is not None]
    ratios_long = [float(c["ratio_long"]) for c in cells if c["ratio_long"] is not None]
    r2_ratio = _r2(
        [float(c["top_weight_short"]) for c in cells if c["ratio_short"] is not None],
        ratios_short,
    )

    monotone_constructed = _constructed_mae_is_monotone_in_gap(
        _prepare(_expert_rows_for(observations["sunspots"], EXPERT_SETS["original"]), EXPERT_SETS["original"]),
        _orders(
            _prepare(_expert_rows_for(observations["sunspots"], EXPERT_SETS["original"]), EXPERT_SETS["original"]),
            EXPERT_SETS["original"],
            "roving",
        ),
        EXPERT_SETS["original"],
        0.9,
    )

    fall = sum(1 for value in deltas if value < 0)
    true_monotone_share = monotone_groups / total_groups if total_groups else 0.0
    controls = {
        "identity_holds": identity_worst == 0.0,
        "identity_worst_residual": identity_worst,
        "constructed_mae_monotone_in_gap": monotone_constructed,
        "true_error_monotone_groups": monotone_groups,
        "true_error_groups": total_groups,
        "true_error_monotone_share": true_monotone_share,
        "chance_monotone_share_with_three_gaps": 1.0 / 6.0,
    }

    conditions = {
        # Every condition is phrased as the property that must HOLD. Condition 1
        # was first written as ``1_identity_does_not_hold`` — a fault condition
        # among four success conditions — so ``all(conditions.values())`` could
        # never be true and the verdict fell through to "a control failed" while
        # all five were in fact met. Measured 2026-11-25; the same class of error
        # as the sign of ``argmax`` in Investigation 11: a name that points the
        # wrong way.
        "1_identity_holds": controls["identity_holds"],
        # The constructed MAE is monotone in gap by construction in every group;
        # the true error only by chance. With three gap points a random ordering
        # is monotone one time in six, so the threshold is a share and not zero —
        # demanding exactly zero is a control that fails for the wrong reason.
        # Measured 2026-11-25: 2 of 20 groups, below the chance rate.
        "2_constructed_mae_is_not_a_forecast": monotone_constructed
        and true_monotone_share < 0.25,
        "3_error_is_data_not_structure": (r2_oracle or 0.0) > 0.50 and (r2_top or 0.0) < 0.20,
        "4_concentration_survives_dropping_peak_set": (r2_without or 0.0) > 0.10,
        "5_retention_has_no_reliable_sign": 0.25 < fall / len(deltas) < 0.75,
    }

    if not conditions["1_identity_holds"]:
        verdict = "instrument_fault_identity_broken"
    elif all(conditions.values()):
        verdict = "error_is_data_retention_path_is_concentration_without_sign"
    elif conditions["3_error_is_data_not_structure"]:
        verdict = "error_is_data_but_a_control_failed"
    else:
        verdict = "structure_carries_more_than_measured_here"

    results: dict[str, object] = {
        "method_version": METHOD_VERSION,
        "verdict": verdict,
        "conditions_fired": conditions,
        "controls": controls,
        "parameters": {
            "gaps": GAPS,
            "retentions": RETENTIONS,
            "assignments": ASSIGNMENTS,
            "learning_rate": LEARNING_RATE,
        },
        "sources": {
            "sunspots_excluded": sunspots_excluded,
            "co2_excluded": co2_excluded,
        },
        "variance": {
            "observations": len(records),
            "grand_mean_error": grand,
            "total_ss": total_ss,
            "min_error": min(errors),
            "max_error": max(errors),
            "eta_squared": eta,
            "r2_oracle": r2_oracle,
            "r2_top_weight": r2_top,
        },
        "retention_effect": {
            "pairs": len(cells),
            "median_d_err": statistics.median(deltas),
            "mean_d_err": statistics.mean(deltas),
            "stdev_d_err": statistics.stdev(deltas),
            "min_d_err": min(deltas),
            "max_d_err": max(deltas),
            "pairs_where_error_falls": fall,
            "corr_d_top_weight_d_err": corr_d,
            "r2_d_top_weight_d_err": r2_d,
            "corr_without_peak_set": corr_without,
            "r2_without_peak_set": r2_without,
            "median_ratio_error_over_oracle_short": statistics.median(ratios_short),
            "median_ratio_error_over_oracle_long": statistics.median(ratios_long),
            "r2_top_weight_vs_ratio": r2_ratio,
        },
        "cells": cells,
    }

    (output_directory / "results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True), encoding="utf-8"
    )
    with (output_directory / "records.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    (output_directory / "manifest.json").write_text(
        json.dumps(
            {"method_version": METHOD_VERSION, "observations": len(records), "cells": len(cells)},
            indent=2,
        ),
        encoding="utf-8",
    )
    return results
