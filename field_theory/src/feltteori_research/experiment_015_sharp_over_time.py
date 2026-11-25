"""Does a sharper weight win on the median over time — or only on its own hits?

Investigation 14 measured the alpha curve on the pooled set: the median ratio
between the ensemble error and the best single expert falls monotonically
with alpha while the mean has an interior minimum. Two aggregates, two answers.
Pooling also hides time.

The trap this module exists to avoid is specific. A median reaches 1.000 when
more than half the months sit at **exactly** 1.000, and a month sits exactly
there when the heaviest expert **is** the oracle. Sharpening raises that share,
so the median falls for a reason that has nothing to do with the mechanism
getting better. A falling median is therefore compatible with a mechanism that
is worse in every month where it does not hit.

Two medians are reported for every alpha:

- **unconditional** over all months — the number one would quote;
- **conditional** over months where the sharpened weight does not land on the
  oracle — the number that can only fall if the mechanism really improves.

A gain that exists only in the first is the hit rate. A gain that survives in
the second is the mechanism.

Six failure modes, each with its check:

1. **The sharpening must be what it is called.** ``w`` is monotone decreasing
   in ``retained``, so ``argmax(w) == argmin(retained)`` exactly. Sharpening to
   the limit is *following the leader*, and a report that calls it "a sharper
   weight" without saying so names an observation after a mechanism it does
   not have. Checked in every month.
2. **The error must come from the real predictions.** Reading ``a`` from the
   constructed predictions cancels the outcome; Investigation 12 established
   that and it is not undone here.
3. **``alpha -> infinity`` must reproduce selection.** A finite alpha only
   approaches the argmax, so the convergence check uses the hard limit.
4. **The conditional set must be reported.** Restricting every alpha to its own
   non-hit months compares different sets. The set size is reported alongside,
   and a shrinking set is itself a result.
5. **The oracle uses hindsight, per month.** No sentence may imply the gap to
   it is closable operationally.
6. **The verdict must be reachable.** Conditions are written as success
   conditions, all in the same polarity, so ``all()`` can be true. Investigation
   12 lost a verdict to a fault condition among success conditions.

The registered measurement is in ``experiments/exp_015_sharp_over_time/protocol.md``.
Its provenance section states that three exploratory probes ran before it.
"""

from __future__ import annotations

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
from feltteori_research.experiment_014_weight_penalty import (
    ASSIGNMENTS,
    GAPS,
    RETENTIONS,
    _argmax_weights,
    _sharpen,
)

METHOD_VERSION = "exp015.sharpover.time.1"

ALPHAS = (2.0, 3.0, 5.0, 10.0)
MODERATE = (2.0, 3.0, 5.0, 10.0)
EXACT = 1e-9
MIN_MONTHS_PER_CELL = 10


def accumulate_dated(
    prepared: list[dict[str, object]],
    orders: list[list[str]],
    experts: tuple[str, ...],
    retention: float,
    gap: float,
) -> list[dict[str, object]]:
    """``experiment_014.accumulate`` verbatim, except the date is carried through.

    The accumulation must stay identical to Investigation 14's, otherwise the
    alpha curve measured here is about a different object. Only the ``date``
    field is added, and it is read from the prepared row.
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
            rows.append(
                {
                    "date": str(row["date"]),
                    "w": weights,
                    "a": a,
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


def _ratio(point: dict[str, object], experts: tuple[str, ...], alpha: float | None) -> float | None:
    weights = point["w"]  # type: ignore[assignment]
    errors = point["a"]  # type: ignore[assignment]
    sharp = _argmax_weights(weights) if alpha is None else _sharpen(weights, alpha)
    oracle = float(point["err_oracle"])  # type: ignore[arg-type]
    if oracle <= 0.0:
        return None
    err = abs(sum(sharp[expert] * errors[expert] for expert in experts))
    return err / oracle


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else float("nan")


def _mean(values: list[float]) -> float:
    return statistics.mean(values) if values else float("nan")


def _label(alpha: float | str | None) -> str:
    """``inf`` is carried both as ``None`` and as the string ``"inf"``.

    ``None`` is what ``_ratio`` takes for the hard argmax; ``"inf"`` is the key
    used in the summary dict so the limit survives a JSON round trip as a name
    rather than as a float. Both must label the same way.
    """
    if alpha is None or alpha == "inf":
        return "inf"
    return str(float(alpha))


def _two_medians(pairs: list[tuple[float, float]]) -> dict[str, float]:
    """``(base, sharp)`` per month -> the two medians that must not be confused.

    The unconditional median is taken over every month and is what one would
    quote. The conditional median is taken only over months where the sharpened
    weight does not land on the oracle, so it can only fall if the mechanism
    improves rather than if it hits.

    Keeping this in one function is not tidiness: the two numbers differ by
    construction, and a mutation that swaps them must be catchable by a test
    that does not read the frozen artifact.
    """
    if not pairs:
        return {
            "unconditional_median": float("nan"),
            "conditional_median_base": float("nan"),
            "conditional_median_sharp": float("nan"),
            "hit_share": 0.0,
            "conditional_months": 0,
        }
    non_hit = [(base, sharp) for base, sharp in pairs if abs(sharp - 1.0) > EXACT]
    return {
        "unconditional_median": _median([sharp for _, sharp in pairs]),
        "conditional_median_base": _median([base for base, _ in non_hit]),
        "conditional_median_sharp": _median([sharp for _, sharp in non_hit]),
        "hit_share": (len(pairs) - len(non_hit)) / len(pairs),
        "conditional_months": len(non_hit),
    }


def run_investigation(
    silso_path: Path,
    noaa_path: Path,
    output_directory: Path,
) -> dict[str, object]:
    """Measure the six registered hypotheses."""
    if output_directory.exists():
        raise FileExistsError(output_directory)
    output_directory.mkdir(parents=True)

    sunspots, _ = parse_silso_monthly(silso_path)
    co2, _ = parse_noaa_monthly(noaa_path)
    observations = {"sunspots": sunspots, "co2": co2}

    # key -> alpha -> ratio
    table: dict[tuple[str, str], dict[object, float]] = {}
    cells: list[dict[str, object]] = []
    controls_leader = 0
    controls_total = 0
    controls_selection_gap = 0.0
    controls_identity = 0.0

    for source, rows in observations.items():
        for set_name, experts in EXPERT_SETS.items():
            subset = _expert_rows_for(rows, experts)
            prepared = _prepare(subset, experts)
            for assignment in ASSIGNMENTS:
                orders = _orders(prepared, experts, assignment)
                for retention in RETENTIONS:
                    for gap in GAPS:
                        cell_id = f"{source}|{set_name}|{assignment}|r{retention:g}|g{gap:g}"
                        points = accumulate_dated(prepared, orders, experts, retention, gap)
                        ratios: dict[str, dict[object, float]] = {}
                        for index, point in enumerate(points):
                            key = (str(point["date"]), f"{cell_id}#{index}")
                            per_alpha: dict[object, float] = {}
                            base = _ratio(point, experts, 1.0)
                            if base is not None:
                                per_alpha[1.0] = base
                            for alpha in ALPHAS:
                                value = _ratio(point, experts, alpha)
                                if value is not None:
                                    per_alpha[alpha] = value
                            limit = _ratio(point, experts, None)
                            if limit is not None:
                                per_alpha["inf"] = limit
                            table[key] = per_alpha

                            controls_total += 1
                            weights = point["w"]  # type: ignore[assignment]
                            retained = point["retained"]  # type: ignore[assignment]
                            top = max(weights, key=lambda k: weights[k])
                            leader = min(retained, key=lambda k: retained[k])
                            if top == leader:
                                controls_leader += 1
                            controls_identity = max(
                                controls_identity,
                                abs(
                                    abs(sum(weights[e] * point["a"][e] for e in experts))  # type: ignore[index]
                                    - float(point["err"])  # type: ignore[arg-type]
                                ),
                            )
                            sharp_err = abs(
                                sum(
                                    _argmax_weights(weights)[e] * point["a"][e]  # type: ignore[index]
                                    for e in experts
                                )
                            )
                            controls_selection_gap = max(
                                controls_selection_gap,
                                abs(sharp_err - float(point["err_selected"])),  # type: ignore[arg-type]
                            )
                            ratios[point["date"]] = per_alpha  # type: ignore[index]

                        cells.append(
                            {
                                "cell": cell_id,
                                "months": len(points),
                                "ratios": ratios,
                            }
                        )

    keys = [key for key in table if 1.0 in table[key]]
    alphas: list[object] = [1.0, *ALPHAS, "inf"]

    # ---- the two medians -------------------------------------------------
    summary: dict[str, dict[str, object]] = {}
    for alpha in alphas:
        unconditional = [table[key][alpha] for key in keys if alpha in table[key]]
        pairs = [
            (table[key][1.0], table[key][alpha])
            for key in keys
            if alpha in table[key] and 1.0 in table[key]
        ]
        medians = _two_medians(pairs)
        non_hit_count = int(medians["conditional_months"])
        summary[_label(alpha)] = {
            "months": len(unconditional),
            "unconditional_median": medians["unconditional_median"],
            "unconditional_mean": _mean(unconditional),
            "hit_months": len(keys) - non_hit_count,
            "hit_share": medians["hit_share"],
            "conditional_months": non_hit_count,
            "conditional_median_base": medians["conditional_median_base"],
            "conditional_median_sharp": medians["conditional_median_sharp"],
            "conditional_mean_base": _mean(
                [base for base, sharp in pairs if abs(sharp - 1.0) > EXACT]
            ),
            "conditional_mean_sharp": _mean(
                [sharp for base, sharp in pairs if abs(sharp - 1.0) > EXACT]
            ),
        }

    # ---- H1: the aggregate conflict --------------------------------------
    by_unconditional = min(
        (a for a in alphas),
        key=lambda a: summary[_label(a)]["unconditional_median"],  # type: ignore[arg-type,return-value]
    )
    by_mean = min(
        (a for a in alphas),
        key=lambda a: summary[_label(a)]["unconditional_mean"],  # type: ignore[arg-type,return-value]
    )
    h1 = _label(by_unconditional) != _label(by_mean)

    # ---- H2: moderate sharpening improves the conditional median ---------
    moderate_gains = {
        _label(alpha): summary[_label(alpha)]["conditional_median_base"]
        - summary[_label(alpha)]["conditional_median_sharp"]
        for alpha in MODERATE
    }
    best_moderate = max(moderate_gains, key=lambda label: moderate_gains[label])
    h2 = moderate_gains[best_moderate] > 1e-6

    # ---- H3: the limit wins only through hits ----------------------------
    limit_gain_unconditional = (
        summary["1.0"]["unconditional_median"] - summary["inf"]["unconditional_median"]
    )
    limit_gain_conditional = (
        summary["inf"]["conditional_median_base"] - summary["inf"]["conditional_median_sharp"]
    )
    h3 = limit_gain_unconditional > 1e-6 and limit_gain_conditional <= 1e-6

    # ---- H4: stable within every calendar year ---------------------------
    years = sorted({key[0][:4] for key in keys})
    per_year: list[dict[str, object]] = []
    for year in years:
        year_keys = [key for key in keys if key[0][:4] == year]
        row: dict[str, object] = {"year": year, "months": len(year_keys)}
        for label in ("1.0", best_moderate):
            values = [table[key][float(label)] for key in year_keys if float(label) in table[key]]
            row[f"median_alpha_{label}"] = _median(values)
        row["sharp_wins"] = float(row[f"median_alpha_{best_moderate}"]) <= float(  # type: ignore[arg-type]
            row["median_alpha_1.0"]
        ) + EXACT
        per_year.append(row)
    h4 = all(bool(row["sharp_wins"]) for row in per_year)

    # ---- H5: not carried by a minority of cells --------------------------
    per_cell: list[dict[str, object]] = []
    best_moderate_alpha = float(best_moderate)
    for cell in cells:
        ratios = cell["ratios"]  # type: ignore[assignment]
        base: list[float] = []
        sharp: list[float] = []
        for per_alpha in ratios.values():  # type: ignore[union-attr]
            if best_moderate_alpha not in per_alpha or 1.0 not in per_alpha:
                continue
            if abs(per_alpha[best_moderate_alpha] - 1.0) <= EXACT:
                continue
            base.append(per_alpha[1.0])
            sharp.append(per_alpha[best_moderate_alpha])
        if len(base) < MIN_MONTHS_PER_CELL:
            continue
        per_cell.append(
            {
                "cell": cell["cell"],
                "months_conditional": len(base),
                "median_base": _median(base),
                "median_sharp": _median(sharp),
                "delta": _median(sharp) - _median(base),
            }
        )
    improved = sum(1 for row in per_cell if float(row["delta"]) < -EXACT)  # type: ignore[arg-type]
    h5 = improved > len(per_cell) / 2

    # ---- H6: the per-month win rate is below one half --------------------
    win_rates: dict[str, dict[str, object]] = {}
    for alpha in (2.0, 3.0, "inf"):
        wins = 0
        ties = 0
        total = 0
        for key in keys:
            if alpha not in table[key]:
                continue
            total += 1
            delta = table[key][alpha] - table[key][1.0]
            if delta < -EXACT:
                wins += 1
            elif abs(delta) <= EXACT:
                ties += 1
        win_rates[_label(alpha)] = {
            "wins": wins,
            "ties": ties,
            "months": total,
            "win_rate": wins / total if total else 0.0,
        }
    h6 = all(entry["win_rate"] < 0.5 for entry in win_rates.values())  # type: ignore[operator]

    # ---- the argmax limit per cell, conditional --------------------------
    limit_per_cell = {"improved": 0, "worsened": 0}
    for cell in cells:
        ratios = cell["ratios"]  # type: ignore[assignment]
        base: list[float] = []
        sharp: list[float] = []
        for per_alpha in ratios.values():  # type: ignore[union-attr]
            if "inf" not in per_alpha or 1.0 not in per_alpha:
                continue
            if abs(per_alpha["inf"] - 1.0) <= EXACT:
                continue
            base.append(per_alpha[1.0])
            sharp.append(per_alpha["inf"])
        if len(base) < MIN_MONTHS_PER_CELL:
            continue
        delta = _median(sharp) - _median(base)
        if delta < -EXACT:
            limit_per_cell["improved"] += 1
        elif delta > EXACT:
            limit_per_cell["worsened"] += 1

    # ---- controls and verdict -------------------------------------------
    controls = {
        "leader_equals_argmin": controls_leader == controls_total,
        "leader_months": controls_leader,
        "leader_total": controls_total,
        "identity_holds": controls_identity < 1e-12,
        "identity_worst_residual": controls_identity,
        "limit_reproduces_selection": controls_selection_gap < 1e-12,
        "limit_worst_gap": controls_selection_gap,
    }

    conditions = {
        "1_aggregate_conflict_is_real": h1,
        "2_moderate_sharpening_improves_conditional_median": h2,
        "3_limit_wins_only_through_hits": h3,
        "4_gain_stable_in_every_year": h4,
        "5_gain_not_carried_by_minority": h5,
        "6_win_rate_below_one_half": h6,
    }
    failed = [name for name, value in conditions.items() if not value]

    if not controls["leader_equals_argmin"]:
        verdict = "sharpening_is_not_leader_following"
    elif not controls["identity_holds"] or not controls["limit_reproduces_selection"]:
        verdict = "control_failed"
    elif not failed:
        verdict = "moderate_sharpening_wins_over_time_limit_does_not"
    elif not h3:
        verdict = "limit_also_improves_the_months_it_misses"
    elif not h2:
        verdict = "sharpening_never_improves_the_conditional_median"
    else:
        verdict = "partly_reproduced_" + "_".join(name.split("_")[0] for name in failed)

    results: dict[str, object] = {
        "method_version": METHOD_VERSION,
        "verdict": verdict,
        "conditions": conditions,
        "conditions_failed": failed,
        "controls": controls,
        "summary": summary,
        "aggregate_choice": {
            "best_by_unconditional_median": _label(by_unconditional),
            "best_by_unconditional_mean": _label(by_mean),
            "same": _label(by_unconditional) == _label(by_mean),
        },
        "moderate_gains": moderate_gains,
        "best_moderate": best_moderate,
        "limit_gain_unconditional": limit_gain_unconditional,
        "limit_gain_conditional": limit_gain_conditional,
        "limit_per_cell_conditional": limit_per_cell,
        "per_year": per_year,
        "per_cell_improved": improved,
        "per_cell_total": len(per_cell),
        "win_rates": win_rates,
        "parameters": {
            "alphas": list(ALPHAS),
            "retentions": list(RETENTIONS),
            "gaps": list(GAPS),
            "assignments": list(ASSIGNMENTS),
            "expert_sets": list(EXPERT_SETS),
        },
    }

    with (output_directory / "results.json").open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, sort_keys=True)

    with (output_directory / "summary.csv").open("w", encoding="utf-8") as handle:
        handle.write(
            "alpha,months,unconditional_median,unconditional_mean,hit_share,"
            "conditional_months,conditional_median_base,conditional_median_sharp\n"
        )
        for label in [_label(alpha) for alpha in alphas]:
            entry = summary[label]
            handle.write(
                f"{label},{entry['months']},{entry['unconditional_median']},"
                f"{entry['unconditional_mean']},{entry['hit_share']},"
                f"{entry['conditional_months']},{entry['conditional_median_base']},"
                f"{entry['conditional_median_sharp']}\n"
            )

    with (output_directory / "per_cell.csv").open("w", encoding="utf-8") as handle:
        handle.write("cell,months_conditional,median_base,median_sharp,delta\n")
        for row in per_cell:
            handle.write(
                f"{row['cell']},{row['months_conditional']},{row['median_base']},"
                f"{row['median_sharp']},{row['delta']}\n"
            )

    with (output_directory / "per_year.csv").open("w", encoding="utf-8") as handle:
        handle.write(f"year,months,median_alpha_1.0,median_alpha_{best_moderate},sharp_wins\n")
        for row in per_year:
            handle.write(
                f"{row['year']},{row['months']},{row['median_alpha_1.0']},"
                f"{row[f'median_alpha_{best_moderate}']},{row['sharp_wins']}\n"
            )

    return results
