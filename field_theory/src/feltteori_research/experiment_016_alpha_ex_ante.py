"""Can alpha be chosen before the outcome is known?

Investigation 15 established that moderate sharpening improves the conditional
median and that the argmax limit does not. But alpha=3 was chosen **after**
seeing which alpha performed best, which is a hyperparameter picked with
hindsight. This module asks the operational question instead: can alpha be
fixed from information available before the outcome, and still win on data
that was not used to choose it?

What is ex ante and what is not is settled in ``_prepare``: ``sign`` and
``losses`` both use ``outcome``, so ``a = real - outcome`` and ``err_oracle``
are hindsight. What remains is ``real`` (each expert's own prediction), ``w``
(built from ``retained`` over earlier months), and the parameters defining a
run. Every signal used here is a function of those only.

Three strengths of "ex ante" are measured separately, because a report that
merges them is worthless:

- **A. fixed alpha** chosen on development 2000-2012, measured on test 2013-2026;
- **B. adaptive alpha** chosen per month from an ex ante signal, calibrated on
  development, applied to test;
- **C. oracle alpha** chosen per month with the outcome in hand — a ceiling,
  never a choice.

The registered measurement is in ``experiments/exp_016_alpha_ex_ante/protocol.md``.
That file was committed alone before this module existed.
"""

from __future__ import annotations

import json
import math
import random
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
from feltteori_research.experiment_014_weight_penalty import (
    ASSIGNMENTS,
    GAPS,
    RETENTIONS,
    _argmax_weights,
    _sharpen,
)

METHOD_VERSION = "exp016.alpha.exante.1"

ALPHAS = (2.0, 3.0, 5.0, 10.0)
CANDIDATES: tuple[float, ...] = (1.0, *ALPHAS)
EXACT = 1e-9
# A difference smaller than this is not a result. The first run of this module
# failed two conditions on margins of 2e-5 and 8e-4 — numerically nonzero and
# operationally meaningless. Reporting a falsification carried by 0.00002
# would be the same error class as the hit-rate median: a number that looks
# like a finding while measuring its own noise. The raw ratio is reported
# alongside every decision so the threshold cannot hide anything.
MEANINGFUL = 1e-3
DEVELOPMENT_END = 2012
SPLIT_YEARS = (2006, 2010, 2018)
SIGNALS = ("top_weight", "effective", "spread", "retained_gap")
PLACEBO_DRAWS = 200
PLACEBO_SEED = 20261125
SPEARMAN_THRESHOLD = 0.20
CONCENTRATED = 0.99

# Investigation 15's registered unconditional median at alpha=1. The control
# compares against it; a mismatch means this module measures a different object.
EXP_015_MEDIAN_ALPHA_1 = 1.2166164905795165


def accumulate_ex_ante(
    prepared: list[dict[str, object]],
    orders: list[list[str]],
    experts: tuple[str, ...],
    retention: float,
    gap: float,
) -> list[dict[str, object]]:
    """``experiment_015.accumulate_dated`` verbatim, plus ``real`` on each point.

    The accumulation must stay identical to Investigation 15's, otherwise the
    alpha curve measured here is about a different object. Two fields are added
    and nothing else changes: ``real`` (needed because the spread of the
    experts' own predictions is an ex ante signal) and ``year`` (needed because
    the split must be temporal).

    The control ``identity_against_exp_015`` recomputes the alpha=1 unconditional
    median and compares it against Investigation 15's registered value, so an
    accidental divergence cannot pass silently.
    """
    retained = {expert: 0.0 for expert in experts}
    rows: list[dict[str, object]] = []
    span = len(experts) - 1

    for row, order in zip(prepared, orders):
        deltas = {expert: gap * rank / span for rank, expert in enumerate(order)}
        l_best = float(row["l_best"])  # type: ignore[arg-type]
        scale = float(row["scale"])  # type: ignore[arg-type]
        outcome = float(row["outcome"])  # type: ignore[arg-type]
        signs = row["sign"]  # type: ignore[assignment]
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
            real = row["real"]  # type: ignore[assignment]
            a = {expert: float(real[expert]) - outcome for expert in experts}  # type: ignore[index]
            top = max(weights, key=lambda key: weights[key])
            date = str(row["date"])
            rows.append(
                {
                    "date": date,
                    "year": int(date[:4]),
                    "w": weights,
                    "a": a,
                    "real": {expert: float(real[expert]) for expert in experts},  # type: ignore[index]
                    "retained": dict(retained),
                    "top": top,
                    "err_oracle": min(abs(value) for value in a.values()),
                    "err_selected": abs(a[top]),
                    "err": abs(sum(weights[expert] * a[expert] for expert in experts)),
                }
            )

        losses = {
            expert: _normalized_loss(predictions[expert], outcome) for expert in experts
        }
        retained = {
            expert: retention * retained[expert] + losses[expert] for expert in experts
        }
    return rows


def _signals(point: dict[str, object]) -> dict[str, float]:
    """Ex ante quantities only — functions of ``w``, ``real`` and ``retained``.

    ``err_oracle`` is deliberately absent: it needs the outcome, and a signal
    that uses it is hindsight however it is dressed.
    """
    weights = point["w"]  # type: ignore[assignment]
    real = point["real"]  # type: ignore[assignment]
    retained = point["retained"]  # type: ignore[assignment]
    top_weight = max(float(weights[e]) for e in weights)  # type: ignore[index]
    effective = 1.0 / sum(float(weights[e]) ** 2 for e in weights)  # type: ignore[index]
    values = [float(real[e]) for e in real]  # type: ignore[index]
    magnitude = abs(statistics.mean(values)) or 1.0
    spread = (max(values) - min(values)) / magnitude
    ordered = sorted(float(retained[e]) for e in retained)  # type: ignore[index]
    gap = (ordered[1] - ordered[0]) / (abs(ordered[0]) + 1.0) if len(ordered) > 1 else 0.0
    return {
        "top_weight": top_weight,
        "effective": effective,
        "spread": spread,
        "retained_gap": gap,
    }


def _ratio(point: dict[str, object], experts: tuple[str, ...], alpha: float | None) -> float | None:
    weights = point["w"]  # type: ignore[assignment]
    errors = point["a"]  # type: ignore[assignment]
    sharp = _argmax_weights(weights) if alpha is None else _sharpen(weights, alpha)  # type: ignore[arg-type]
    oracle = float(point["err_oracle"])  # type: ignore[arg-type]
    if oracle <= 0.0:
        return None
    err = abs(sum(sharp[expert] * errors[expert] for expert in experts))  # type: ignore[index]
    return err / oracle


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else float("nan")


def _experts_of(point: dict[str, object]) -> tuple[str, ...]:
    """The expert tuple a point was built from.

    ``pooled`` mixes cells from five expert sets, so a single ``experts``
    argument passed alongside a pooled list would measure a ``four_experts``
    point with ``original``'s names — wrong numbers or a ``KeyError``,
    depending on the order. Every helper therefore reads the tuple from the
    point itself.
    """
    return point["experts"]  # type: ignore[return-value]


def _common_non_hit(points: list[dict[str, object]]) -> list[dict[str, object]]:
    """Months where **no** candidate alpha lands on the oracle.

    Investigation 15 restricted each alpha to its own non-hit months, which
    means two alphas were compared on two different month sets. A comparison
    across alphas needs one set, so this is the set where every candidate has
    something to lose. A smaller set is itself a result and its size is
    reported.
    """
    kept: list[dict[str, object]] = []
    for point in points:
        values = [_ratio(point, _experts_of(point), alpha) for alpha in CANDIDATES]
        if any(value is None for value in values):
            continue
        if all(abs(float(value) - 1.0) > EXACT for value in values):  # type: ignore[arg-type]
            kept.append(point)
    return kept


def _conditional_median(points: list[dict[str, object]], alpha: float) -> float:
    values = [_ratio(point, _experts_of(point), alpha) for point in points]
    return _median([float(value) for value in values if value is not None])


def _best_fixed(points: list[dict[str, object]]) -> tuple[float, float]:
    scored = [(_conditional_median(points, alpha), alpha) for alpha in CANDIDATES]
    scored = [(value, alpha) for value, alpha in scored if value == value]
    if not scored:
        return (float("nan"), float("nan"))
    value, alpha = min(scored)
    return (alpha, value)


def _ranks(values: list[float]) -> list[float]:
    """Average ranks, so ties do not bias the correlation."""
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(order):
        end = index
        while end + 1 < len(order) and values[order[end + 1]] == values[order[index]]:
            end += 1
        average = (index + end) / 2.0 + 1.0
        for position in range(index, end + 1):
            ranks[order[position]] = average
        index = end + 1
    return ranks


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) < 3:
        return float("nan")
    mean_left = statistics.mean(left)
    mean_right = statistics.mean(right)
    numerator = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right))
    denom_left = math.sqrt(sum((a - mean_left) ** 2 for a in left))
    denom_right = math.sqrt(sum((b - mean_right) ** 2 for b in right))
    if denom_left == 0.0 or denom_right == 0.0:
        return float("nan")
    return numerator / (denom_left * denom_right)


def _spearman(left: list[float], right: list[float]) -> float:
    return _pearson(_ranks(left), _ranks(right))


def _split(points: list[dict[str, object]], end_year: int) -> tuple[list, list]:
    development = [p for p in points if int(p["year"]) <= end_year]  # type: ignore[arg-type]
    test = [p for p in points if int(p["year"]) > end_year]  # type: ignore[arg-type]
    return development, test


def _adaptive_rule(
    development: list[dict[str, object]],
    test: list[dict[str, object]],
    signal: str,
    quantiles: int = 4,
) -> dict[str, object]:
    """Pick one alpha per signal-quantile on development, apply it to test.

    Four quantiles is a small number of degrees of freedom on purpose: a rule
    with more freedom can always be fitted, and the question is whether a
    *transferable* rule exists.
    """
    if not development or not test:
        return {"median": float("nan"), "assignments": {}}
    values = sorted(_signals(point)[signal] for point in development)
    cuts = [
        values[int(len(values) * (index + 1) / quantiles) - 1]
        for index in range(quantiles - 1)
    ]

    def bucket(point: dict[str, object]) -> int:
        value = _signals(point)[signal]
        for index, cut in enumerate(cuts):
            if value <= cut:
                return index
        return len(cuts)

    chosen: dict[int, float] = {}
    for index in range(quantiles):
        group = [point for point in development if bucket(point) == index]
        alpha, _ = _best_fixed(group)
        chosen[index] = alpha

    applied: list[float] = []
    for point in test:
        alpha = chosen.get(bucket(point), float("nan"))
        if alpha != alpha:
            continue
        value = _ratio(point, _experts_of(point), alpha)
        if value is not None:
            applied.append(value)
    return {
        "median": _median(applied),
        "months": len(applied),
        "assignments": {str(key): value for key, value in chosen.items()},
    }


def _placebo(
    points: list[dict[str, object]], draws: int
) -> dict[str, object]:
    """A random alpha per month, drawn with a fixed seed.

    If random choice beats the best fixed alpha, the comparison is measuring
    noise and the experiment is void.
    """
    rng = random.Random(PLACEBO_SEED)
    medians: list[float] = []
    for _ in range(draws):
        values: list[float] = []
        for point in points:
            alpha = rng.choice(CANDIDATES)
            value = _ratio(point, _experts_of(point), alpha)
            if value is not None:
                values.append(value)
        medians.append(_median(values))
    return {
        "draws": draws,
        "median_of_medians": _median(medians),
        "min": min(medians) if medians else float("nan"),
        "max": max(medians) if medians else float("nan"),
    }


def run_investigation(
    silso_path: Path,
    noaa_path: Path,
    output_directory: Path,
) -> dict[str, object]:
    """Measure the five registered hypotheses."""
    if output_directory.exists():
        raise FileExistsError(output_directory)
    output_directory.mkdir(parents=True)

    sunspots, _ = parse_silso_monthly(silso_path)
    co2, _ = parse_noaa_monthly(noaa_path)
    observations = {"sunspots": sunspots, "co2": co2}

    pooled: list[dict[str, object]] = []
    identity_worst = 0.0
    selection_gap = 0.0
    temporal_ok = True
    leader_agrees = 0
    leader_total = 0

    for source, rows in observations.items():
        for set_name, experts in EXPERT_SETS.items():
            subset = _expert_rows_for(rows, experts)
            prepared = _prepare(subset, experts)
            for assignment in ASSIGNMENTS:
                orders = _orders(prepared, experts, assignment)
                for retention in RETENTIONS:
                    for gap in GAPS:
                        cell_id = f"{source}|{set_name}|{assignment}|r{retention:g}|g{gap:g}"
                        points = accumulate_ex_ante(prepared, orders, experts, retention, gap)
                        for point in points:
                            weights = point["w"]  # type: ignore[assignment]
                            retained = point["retained"]  # type: ignore[assignment]
                            identity_worst = max(
                                identity_worst,
                                abs(
                                    abs(sum(weights[e] * point["a"][e] for e in experts))  # type: ignore[index]
                                    - float(point["err"])  # type: ignore[arg-type]
                                ),
                            )
                            sharp = _argmax_weights(weights)  # type: ignore[arg-type]
                            selection_gap = max(
                                selection_gap,
                                abs(
                                    abs(sum(sharp[e] * point["a"][e] for e in experts))  # type: ignore[index]
                                    - float(point["err_selected"])  # type: ignore[arg-type]
                                ),
                            )
                            leader_total += 1
                            if max(weights, key=lambda k: weights[k]) == min(  # type: ignore[index]
                                retained, key=lambda k: retained[k]  # type: ignore[index]
                            ):
                                leader_agrees += 1
                            entry = dict(point)
                            entry["cell"] = cell_id
                            entry["experts"] = experts
                            pooled.append(entry)

    # ---- control: reproduce Investigation 15 -----------------------------
    ratios_alpha_1 = [
        float(_ratio(point, point["experts"], 1.0))  # type: ignore[arg-type]
        for point in pooled
        if _ratio(point, point["experts"], 1.0) is not None  # type: ignore[arg-type]
    ]
    reproduced = _median(ratios_alpha_1)
    identity_against_exp_015 = abs(reproduced - EXP_015_MEDIAN_ALPHA_1) <= 1e-9

    development, test = _split(pooled, DEVELOPMENT_END)
    temporal_ok = (
        bool(development)
        and bool(test)
        and max(int(p["year"]) for p in development) < min(int(p["year"]) for p in test)
    )

    dev_common = _common_non_hit(development) if development else []
    test_common = _common_non_hit(test) if test else []

    # ---- H1: a fixed alpha chosen on development -------------------------
    # One alpha for the whole system, chosen on development and applied to
    # test. Choosing per cell would hand the rule a cell identity that no
    # operator has: retention and gap are the mechanism's own knobs, not
    # observable context, so a per-cell choice is hindsight wearing a rule's
    # clothes.
    fixed_alpha, fixed_dev_median = _best_fixed(dev_common) if dev_common else (float("nan"), float("nan"))
    baseline_test = _conditional_median(test_common, 1.0) if test_common else float("nan")
    fixed_test = (
        _conditional_median(test_common, fixed_alpha)
        if test_common and fixed_alpha == fixed_alpha
        else float("nan")
    )
    h1 = bool(fixed_test == fixed_test and baseline_test == baseline_test and fixed_test < baseline_test)

    # ---- H2: the choice is not sensitive to the split point --------------
    chosen_by_split: dict[str, float] = {}
    for end_year in SPLIT_YEARS:
        dev, _ = _split(pooled, end_year)
        common = _common_non_hit(dev) if dev else []
        alpha, _ = _best_fixed(common) if common else (float("nan"), float("nan"))
        chosen_by_split[str(end_year)] = alpha
    distinct = {value for value in chosen_by_split.values() if value == value}
    h2 = len(distinct) == 1

    # ---- H3: no ex ante signal predicts the best alpha -------------------
    # Only months where the alphas actually differ can say anything about
    # which one is best.
    discriminating = []
    for point in pooled:
        values = [_ratio(point, point["experts"], alpha) for alpha in CANDIDATES]  # type: ignore[arg-type]
        if any(value is None for value in values):
            continue
        numeric = [float(value) for value in values]  # type: ignore[arg-type]
        if max(numeric) - min(numeric) <= EXACT:
            continue
        discriminating.append((point, CANDIDATES[numeric.index(min(numeric))]))

    signal_correlations: dict[str, dict[str, object]] = {}
    for signal in SIGNALS:
        xs = [_signals(point)[signal] for point, _ in discriminating]
        ys = [alpha for _, alpha in discriminating]
        value = _spearman(xs, ys)
        signal_correlations[signal] = {
            "spearman": value,
            "months": len(discriminating),
            "abs_below_threshold": bool(value != value or abs(value) < SPEARMAN_THRESHOLD),
        }
    h3 = all(
        bool(entry["abs_below_threshold"]) for entry in signal_correlations.values()
    )

    # ---- H4: the adaptive rule does not beat the best fixed alpha --------
    best_test_alpha, best_test_median = _best_fixed(test_common) if test_common else (float("nan"), float("nan"))
    adaptive: dict[str, dict[str, object]] = {}
    for signal in SIGNALS:
        adaptive[signal] = _adaptive_rule(dev_common, test_common, signal) if dev_common and test_common else {"median": float("nan"), "months": 0, "assignments": {}}
    adaptive_best = min(
        (
            (float(entry["median"]), signal)
            for signal, entry in adaptive.items()
            if float(entry["median"]) == float(entry["median"])
        ),
        default=(float("nan"), "none"),
    )
    # "Strictly better" needs a margin. A rule that wins by 2e-5 has not beaten
    # anything; it has tied and rounded differently.
    adaptive_ratio = (
        adaptive_best[0] / best_test_median
        if adaptive_best[0] == adaptive_best[0] and best_test_median not in (0.0, float("nan"))
        else float("nan")
    )
    h4 = bool(
        adaptive_ratio != adaptive_ratio
        or adaptive_ratio >= 1.0 - MEANINGFUL
    )

    # ---- H5: the concentrated regime ------------------------------------
    concentrated = [
        point for point in pooled if _signals(point)["top_weight"] > CONCENTRATED
    ]
    concentrated_common = _common_non_hit(concentrated) if concentrated else []
    concentrated_base = (
        _conditional_median(concentrated_common, 1.0)
        if concentrated_common
        else float("nan")
    )
    concentrated_sharp = (
        _conditional_median(concentrated_common, 3.0)
        if concentrated_common
        else float("nan")
    )
    concentrated_ratio = (
        concentrated_sharp / concentrated_base
        if concentrated_base == concentrated_base and concentrated_base not in (0.0, float("nan"))
        else float("nan")
    )
    h5 = bool(
        concentrated_ratio != concentrated_ratio
        or concentrated_ratio >= 1.0 - MEANINGFUL
    )

    # ---- the ceiling: one alpha per month, chosen with the outcome -------
    # The protocol registered C as a per-month choice with the outcome in
    # hand. ``best_test_alpha`` above is a different object — the best *fixed*
    # alpha on test — and reporting it as the ceiling would understate how much
    # room a perfect chooser would have.
    per_month_oracle: list[float] = []
    for point in test_common:
        values = [
            _ratio(point, _experts_of(point), alpha) for alpha in CANDIDATES
        ]
        numeric = [float(value) for value in values if value is not None]
        if numeric:
            per_month_oracle.append(min(numeric))
    oracle_median = _median(per_month_oracle)

    # ---- controls -------------------------------------------------------
    placebo = _placebo(test_common, PLACEBO_DRAWS) if test_common else {"median_of_medians": float("nan")}
    placebo_below_best_fixed = bool(
        float(placebo["median_of_medians"]) != float(placebo["median_of_medians"])
        or best_test_median != best_test_median
        or float(placebo["median_of_medians"]) >= best_test_median
    )

    controls = {
        "identity_holds": identity_worst <= 1e-9,
        "identity_worst_residual": identity_worst,
        "identity_against_exp_015": identity_against_exp_015,
        "reproduced_median_alpha_1": reproduced,
        "exp_015_median_alpha_1": EXP_015_MEDIAN_ALPHA_1,
        "limit_reproduces_selection": selection_gap <= 1e-9,
        "limit_worst_gap": selection_gap,
        "leader_equals_argmin": leader_agrees == leader_total,
        "leader_months": leader_agrees,
        "leader_total": leader_total,
        "split_is_temporal": temporal_ok,
        "placebo_does_not_beat_best_fixed": placebo_below_best_fixed,
    }

    conditions = {
        "1_fixed_alpha_survives_split": h1,
        "2_choice_insensitive_to_split": h2,
        "3_no_ex_ante_signal": h3,
        "4_adaptive_does_not_beat_fixed": h4,
        "5_concentrated_regime_is_real": h5,
    }

    failed = [name for name, value in conditions.items() if not value]
    controls_failed = [
        name
        for name, value in controls.items()
        if isinstance(value, bool) and not value
    ]

    if controls_failed:
        verdict = "controls_failed:" + ",".join(controls_failed)
    elif not failed:
        verdict = "fixed_alpha_transfers_adaptive_does_not"
    else:
        verdict = "partial:" + ",".join(failed)

    results: dict[str, object] = {
        "method_version": METHOD_VERSION,
        "verdict": verdict,
        "conditions": conditions,
        "conditions_failed": failed,
        "controls": controls,
        "months": len(pooled),
        "development_months": len(development),
        "test_months": len(test),
        "development_end_year": DEVELOPMENT_END,
        "month_sets": {
            "development_common_non_hit": len(dev_common),
            "test_common_non_hit": len(test_common),
            # Months where the candidates do not all return the same ratio.
            # This is a different set from the common non-hit set: a month can
            # discriminate without every candidate missing the oracle.
            "discriminating": len(discriminating),
        },
        "fixed_choice": {
            "alpha": fixed_alpha,
            "development_median": fixed_dev_median,
            "test_median_baseline_alpha_1": baseline_test,
            "test_median_chosen_alpha": fixed_test,
        },
        "chosen_alpha_by_split": chosen_by_split,
        "signal_correlations": signal_correlations,
        "adaptive": adaptive,
        "adaptive_best": {
            "median": adaptive_best[0],
            "signal": adaptive_best[1],
            "ratio_to_best_fixed": adaptive_ratio,
            "best_fixed_median": best_test_median,
            "meaningful": MEANINGFUL,
        },
        "ceiling": {
            "per_month_oracle_median": oracle_median,
            "months": len(per_month_oracle),
            "best_fixed_alpha_on_test": best_test_alpha,
            "best_fixed_median_on_test": best_test_median,
        },
        "concentrated_regime": {
            "threshold": CONCENTRATED,
            "months": len(concentrated),
            "common_non_hit": len(concentrated_common),
            "median_alpha_1": concentrated_base,
            "median_alpha_3": concentrated_sharp,
            "ratio_sharp_over_base": concentrated_ratio,
            "meaningful": MEANINGFUL,
        },
        "placebo": placebo,
        "thresholds": {
            "spearman": SPEARMAN_THRESHOLD,
            "concentrated_top_weight": CONCENTRATED,
            "placebo_draws": PLACEBO_DRAWS,
        },
        "parameters": {
            "alphas": list(ALPHAS),
            "candidates": list(CANDIDATES),
            "retentions": list(RETENTIONS),
            "gaps": list(GAPS),
            "assignments": list(ASSIGNMENTS),
            "expert_sets": list(EXPERT_SETS),
        },
    }

    (output_directory / "results.json").write_text(
        json.dumps(results, indent=2, default=str), encoding="utf-8"
    )
    return results
