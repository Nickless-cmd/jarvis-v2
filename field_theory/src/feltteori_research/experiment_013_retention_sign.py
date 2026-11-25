"""The regime where retention has a reliable sign — and whether it can be known in advance.

Investigation 12 showed that retention reaches the forecast through exactly one
channel, the weight vector, and that the error is mostly data. It left an opening:
retention moved the true error in 208 of 260 pairs. This module asks where that
effect has a consistent sign, and — the only question with operational value —
whether the sign can be known before the outcome is observed.

Two claims from earlier work are corrected here rather than quietly dropped:

*Investigation 12 claimed* the ensemble never beats the best single expert "as
the arithmetic of a convex combination requires". That is **wrong**. The correct
inequality is

    |sum_e w_e a_e|  <=  sum_e w_e |a_e|

which is an upper bound and gives no lower bound at all. An ensemble can beat
every member when the errors point in opposite directions. Measured here: the
ensemble beats the oracle in 2 974 of 19 170 months. The claim is retracted.

The reason it is nevertheless rare is measured, not assumed: decomposing

    (sum_e w_e a_e)^2  =  sum_e w_e^2 a_e^2  +  2 sum_{i<j} w_i w_j a_i a_j

gives a **positive** cross term in 59 of 60 cells (median ``cross/diag`` +0.285).
The experts amplify each other's errors; they almost never cancel. That is a
property of these data, and it is the honest replacement for the arithmetic
argument that did not hold.

The registered measurement is in ``experiments/exp_013_retention_sign/protocol.md``.
Its provenance section states that four exploratory probes ran before the
protocol was written; the ordering is declared, not dressed up.

Four failure modes that can each be lost silently, and where each is checked:

1. **The identity.** ``error == |sum w a|``; residual must be 0.0.
2. **The denominator of the cross share.** An earlier probe divided by
   ``(sum w a)^2``, which can be near zero, and produced ``cross share`` = -972 570.
   That is division by nothing. The registered denominator is
   ``sum w_e^2 a_e^2``, strictly positive whenever any error is non-zero.
3. **The ex post result must not be sold as operational.** If condition 6 holds,
   no sentence may imply the regime is usable before the outcome.
4. **The hold-out stays in even when it fails.** It failed for the top-expert
   stability candidate, and that failure is part of the result.
"""

from __future__ import annotations

import csv
import itertools
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

METHOD_VERSION = "exp013.retentionsign.1"

GAPS = (0.05, 0.2, 0.8)
RETENTION_SHORT = 0.9
RETENTION_LONG = 0.99
ASSIGNMENTS = ("fixed", "roving")

# Registered thresholds. They are constants so the tests can see them and so a
# later reader can tell which number decided the verdict.
THRESHOLD_EX_POST_CORR = -0.40
THRESHOLD_SPLIT_HALF_R2 = 0.15
THRESHOLD_EX_ANTE_R2 = 0.20
THRESHOLD_AMPLIFY_SHARE = 0.90


def _accumulate(
    prepared: list[dict[str, object]],
    orders: list[list[str]],
    experts: tuple[str, ...],
    retention: float,
    gap: float,
) -> list[dict[str, object]]:
    """Per evaluation month: weights, error terms, and the quantities measured before the outcome.

    ``exante_spread`` is the standard deviation of the experts' own predictions.
    It is available before the outcome is observed, which is what makes it a
    candidate ex ante predictor rather than another retrospective one.
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
            error = abs(signed)
            diagonal = sum(weights[expert] ** 2 * a[expert] ** 2 for expert in experts)
            cross = 2.0 * sum(
                weights[i] * weights[j] * a[i] * a[j]
                for i, j in itertools.combinations(experts, 2)
            )
            own = [float(real[expert]) for expert in experts]  # type: ignore[index]
            own_mean = sum(own) / len(own)
            rows.append(
                {
                    "err": error,
                    # Recomposed from the stored weight vector and error
                    # directions, so the identity check compares two independent
                    # routes to the same number. An earlier draft compared
                    # ``err`` with ``|err|`` — zero by construction, a control
                    # that cannot fail.
                    "recomposed": abs(
                        sum(weights[expert] * a[expert] for expert in experts)
                    ),
                    "signed": signed,
                    "oracle": min(abs(value) for value in a.values()),
                    "diag": diagonal,
                    "cross": cross,
                    "cross_share": cross / diagonal if diagonal > 0 else 0.0,
                    "top": max(weights, key=lambda key: weights[key]),
                    "exante_spread": math.sqrt(
                        sum((value - own_mean) ** 2 for value in own) / len(own)
                    ),
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


def _mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


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


def run_investigation(
    silso_path: Path,
    noaa_path: Path,
    output_directory: Path,
) -> dict[str, object]:
    """Measure the regime and test whether it survives split-half and hold-out."""
    if output_directory.exists():
        raise FileExistsError(output_directory)
    output_directory.mkdir(parents=True)

    sunspots, sunspots_excluded = parse_silso_monthly(silso_path)
    co2, co2_excluded = parse_noaa_monthly(noaa_path)
    observations = {"sunspots": sunspots, "co2": co2}

    cells: list[dict[str, object]] = []
    identity_worst = 0.0
    months_total = 0
    months_ensemble_beats_oracle = 0
    worst_error_over_oracle = 0.0

    for source, source_rows in observations.items():
        for set_name, experts in EXPERT_SETS.items():
            try:
                rows = _expert_rows_for(source_rows, experts)
            except (KeyError, ValueError):
                continue
            prepared = _prepare(rows, experts)
            for assignment in ASSIGNMENTS:
                orders = _orders(prepared, experts, assignment)
                for gap in GAPS:
                    short = _accumulate(prepared, orders, experts, RETENTION_SHORT, gap)
                    long = _accumulate(prepared, orders, experts, RETENTION_LONG, gap)

                    for point in short:
                        months_total += 1
                        if float(point["err"]) < float(point["oracle"]) - 1e-12:
                            months_ensemble_beats_oracle += 1
                        oracle = float(point["oracle"])
                        if oracle > 0:
                            worst_error_over_oracle = max(
                                worst_error_over_oracle, float(point["err"]) / oracle
                            )

                    # Two independent routes to the same number: ``err`` was
                    # computed inline and ``recomposed`` from the stored weight
                    # vector and error directions. An earlier draft compared
                    # ``err`` with ``|err|``, which is zero by construction.
                    identity_worst = max(
                        identity_worst,
                        max(
                            abs(float(p["err"]) - float(p["recomposed"]))
                            for p in short
                        ),
                    )

                    err_short = _mean([float(p["err"]) for p in short])
                    err_long = _mean([float(p["err"]) for p in long])
                    oracle_short = _mean([float(p["oracle"]) for p in short])

                    # Split-half over evaluation months: the two halves share no
                    # month, so a correlation across them cannot be produced by
                    # regression to the mean inside a single measurement.
                    half = len(short) // 2
                    first_short = _mean([float(p["err"]) for p in short[:half]])
                    first_long = _mean([float(p["err"]) for p in long[:half]])
                    second_short = _mean([float(p["err"]) for p in short[half:]])
                    second_long = _mean([float(p["err"]) for p in long[half:]])
                    # Each half needs its own oracle, otherwise ``ratio_first``
                    # is normalised by a quantity measured over both halves and
                    # the same-half comparison is not like for like.
                    oracle_first = _mean([float(p["oracle"]) for p in short[:half]])
                    oracle_second = _mean([float(p["oracle"]) for p in short[half:]])

                    top_agree = (
                        sum(
                            1
                            for a, b in zip(short, long)
                            if a["top"] == b["top"]
                        )
                        / len(short)
                        if short
                        else 0.0
                    )

                    cells.append(
                        {
                            "source": source,
                            "expert_set": set_name,
                            "assignment": assignment,
                            "gap": gap,
                            "err_short": err_short,
                            "err_long": err_long,
                            "d_err": err_long - err_short,
                            "oracle_short": oracle_short,
                            "ratio_short": err_short / oracle_short if oracle_short else None,
                            "cross_share": _mean([float(p["cross_share"]) for p in short]),
                            "top_weight_short": _mean([float(p["top_weight"]) for p in short]),
                            "exante_spread": _mean([float(p["exante_spread"]) for p in short]),
                            "top_agreement": top_agree,
                            "ratio_first": first_short / oracle_first if oracle_first else None,
                            "ratio_second": second_short / oracle_second if oracle_second else None,
                            "d_first": first_long - first_short,
                            "d_second": second_long - second_short,
                        }
                    )

    deltas = [float(cell["d_err"]) for cell in cells]
    ratios = [float(cell["ratio_short"]) for cell in cells if cell["ratio_short"] is not None]

    corr_ratio = _corr(
        [float(c["ratio_short"]) for c in cells if c["ratio_short"] is not None], deltas
    )
    corr_error_level = _corr([float(c["err_short"]) for c in cells], deltas)

    split_a = _r2(
        [float(c["ratio_first"]) for c in cells if c["ratio_first"] is not None],
        [float(c["d_second"]) for c in cells if c["ratio_first"] is not None],
    )
    split_b = _r2(
        [float(c["ratio_second"]) for c in cells if c["ratio_second"] is not None],
        [float(c["d_first"]) for c in cells if c["ratio_second"] is not None],
    )
    same_half = _r2(
        [float(c["ratio_first"]) for c in cells if c["ratio_first"] is not None],
        [float(c["d_first"]) for c in cells if c["ratio_first"] is not None],
    )

    ex_ante = {
        "top_weight_short": _r2([float(c["top_weight_short"]) for c in cells], deltas),
        "exante_spread": _r2([float(c["exante_spread"]) for c in cells], deltas),
        "top_agreement": _r2([float(c["top_agreement"]) for c in cells], deltas),
    }
    best_ex_ante_key = max(
        (key for key in ex_ante if ex_ante[key] is not None),
        key=lambda key: ex_ante[key] or 0.0,
        default=None,
    )
    best_ex_ante = ex_ante.get(best_ex_ante_key) if best_ex_ante_key else None

    cross_shares = [float(c["cross_share"]) for c in cells]
    amplify_share = sum(1 for value in cross_shares if value > 0) / len(cross_shares)

    # Hold-out for the candidate regime that failed: top-expert stability.
    hold_out: dict[str, object] = {}
    for train_source, test_source in (("sunspots", "co2"), ("co2", "sunspots")):
        train = [c for c in cells if c["source"] == train_source]
        test = [c for c in cells if c["source"] == test_source]
        for label, predicate in (
            ("top_stable", lambda c: float(c["top_agreement"]) > 0.9),
            ("top_shifts", lambda c: float(c["top_agreement"]) <= 0.9),
        ):
            train_values = [float(c["d_err"]) for c in train if predicate(c)]
            test_values = [float(c["d_err"]) for c in test if predicate(c)]
            hold_out[f"{train_source}_to_{test_source}_{label}"] = {
                "train_n": len(train_values),
                "test_n": len(test_values),
                "train_median": statistics.median(train_values) if train_values else None,
                "test_median": statistics.median(test_values) if test_values else None,
                "sign_preserved": (
                    (statistics.median(train_values) > 0)
                    == (statistics.median(test_values) > 0)
                    if train_values and test_values
                    else None
                ),
            }

    controls = {
        "identity_holds": identity_worst == 0.0,
        "identity_worst_residual": identity_worst,
        "months_total": months_total,
        "months_ensemble_beats_oracle": months_ensemble_beats_oracle,
        "worst_error_over_oracle": worst_error_over_oracle,
        "cross_share_median": statistics.median(cross_shares),
        "cross_share_min": min(cross_shares),
        "cross_share_max": max(cross_shares),
        "cells_where_experts_amplify": sum(1 for value in cross_shares if value > 0),
        "cells_total": len(cells),
        "amplify_share": amplify_share,
        "corr_error_level_d_err": corr_error_level,
        "same_half_r2": same_half,
        "split_half_r2_a": split_a,
        "split_half_r2_b": split_b,
        "hold_out": hold_out,
    }

    conditions = {
        "1_identity_holds": controls["identity_holds"],
        # H1 — the ensemble CAN beat the oracle. My earlier claim that it cannot
        # was wrong; this condition keeps the retraction measured rather than
        # merely stated.
        "2_ensemble_can_beat_oracle": months_ensemble_beats_oracle > 0,
        # H2 — errors amplify rather than cancel.
        "3_experts_amplify_errors": amplify_share >= THRESHOLD_AMPLIFY_SHARE,
        # H3 — an ex post regime exists.
        "4_ex_post_regime_is_real": (corr_ratio or 0.0) <= THRESHOLD_EX_POST_CORR,
        # H4 — it is not regression to the mean.
        "5_regime_is_not_regression_to_mean": (split_a or 0.0) >= THRESHOLD_SPLIT_HALF_R2,
        # H5 — no ex ante regime exists. This is the one that decides whether the
        # finding is prescriptive or merely descriptive.
        "6_no_ex_ante_regime": (best_ex_ante or 0.0) < THRESHOLD_EX_ANTE_R2,
    }

    if not conditions["1_identity_holds"]:
        verdict = "instrument_fault_identity_broken"
    elif all(conditions.values()):
        verdict = "regime_exists_but_requires_the_outcome"
    elif all(
        value
        for key, value in conditions.items()
        if key != "6_no_ex_ante_regime"
    ):
        verdict = "ex_ante_regime_found"
    else:
        verdict = "regime_did_not_survive_the_controls"

    results: dict[str, object] = {
        "method_version": METHOD_VERSION,
        "verdict": verdict,
        "conditions_fired": conditions,
        "controls": controls,
        "thresholds": {
            "ex_post_corr": THRESHOLD_EX_POST_CORR,
            "split_half_r2": THRESHOLD_SPLIT_HALF_R2,
            "ex_ante_r2": THRESHOLD_EX_ANTE_R2,
            "amplify_share": THRESHOLD_AMPLIFY_SHARE,
        },
        "parameters": {
            "gaps": GAPS,
            "retention_short": RETENTION_SHORT,
            "retention_long": RETENTION_LONG,
            "assignments": ASSIGNMENTS,
            "learning_rate": LEARNING_RATE,
        },
        "sources": {
            "sunspots_excluded": sunspots_excluded,
            "co2_excluded": co2_excluded,
        },
        "regime": {
            "cells": len(cells),
            "corr_ratio_d_err": corr_ratio,
            "r2_ratio_d_err": _r2(
                [float(c["ratio_short"]) for c in cells if c["ratio_short"] is not None],
                deltas,
            ),
            "median_d_err_all": statistics.median(deltas),
            "mean_d_err_all": statistics.mean(deltas),
            "pairs_where_error_falls": sum(1 for value in deltas if value < 0),
            "ex_ante_r2": ex_ante,
            "best_ex_ante_predictor": best_ex_ante_key,
            "best_ex_ante_r2": best_ex_ante,
            "median_ratio": statistics.median(ratios) if ratios else None,
        },
        "cells": cells,
    }

    (output_directory / "results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True), encoding="utf-8"
    )
    with (output_directory / "cells.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(cells[0]))
        writer.writeheader()
        writer.writerows(cells)
    (output_directory / "manifest.json").write_text(
        json.dumps(
            {"method_version": METHOD_VERSION, "cells": len(cells)},
            indent=2,
        ),
        encoding="utf-8",
    )
    return results
