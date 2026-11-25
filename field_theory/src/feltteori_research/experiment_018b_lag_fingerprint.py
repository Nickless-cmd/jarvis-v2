"""Investigation 18b — a principled fingerprint: the lag structure of a series.

The registered fingerprint in :mod:`experiment_018_detect_shift` used three shape
features (jaggedness, autocorrelation, ties). Its own control, C4, rejected it:
the reference could not identify a name against itself in 34 of 40 cells. The
control did its job — reporting "detection is impossible" on that basis would
have been reporting a feature-design failure as a property of the world.

This module is the **exploratory** repair, and its evidence is weaker for exactly
that reason: it was written after seeing the registered run fail.

The repair is principled rather than tuned. An expert is *defined* by its lag
structure: `previous_month` is the observation one month back, `trailing_12_mean`
is a flat average over lags 1-12, `cycle_lag_132` is the observation 132 months
back. Correlating each name's prediction stream against the observation series at
lags 1..132 recovers that structure directly.

Crucially this stays ex ante. Detecting a shift at month ``t`` uses outcomes at
indices **strictly below** ``t`` and the predictions at ``t``. The outcome of
month ``t`` is never read, which control C1' below enforces by mutating every
outcome at and after a probe month and requiring the answer at that month to be
bit-identical.
"""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

from .experiment_005_learning import parse_silso_monthly
from .experiment_006_order import parse_noaa_monthly
from .experiment_009_expert_set import EXPERT_SETS, _expert_rows_for
from .experiment_017_regime_shift import prepare_swapped
from .experiment_018_detect_shift import (
    GAP,
    RETENTION,
    _evaluation_indices,
    apply_stats,
    assign,
    feature_stats,
    identity,
    true_permutation,
)

METHOD_VERSION = "exp_018b_lag_fingerprint/1"

LAGS = (1, 2, 3, 6, 12, 24, 66, 132)
LAG_FEATURES = tuple(f"lag{lag}" for lag in LAGS)
WINDOWS = (24, 36, 60, 120)
ASSIGNMENT = "roving"
STABLE_SHARE = 0.9
EXACT = 1e-12


def _corr(left: list[float], right: list[float]) -> float:
    """Pearson correlation; zero when either side is constant."""
    n = len(left)
    if n < 3:
        return 0.0
    mean_left = statistics.mean(left)
    mean_right = statistics.mean(right)
    numerator = sum(
        (left[i] - mean_left) * (right[i] - mean_right) for i in range(n)
    )
    var_left = sum((value - mean_left) ** 2 for value in left)
    var_right = sum((value - mean_right) ** 2 for value in right)
    if var_left <= 0.0 or var_right <= 0.0:
        return 0.0
    return numerator / math.sqrt(var_left * var_right)


def lag_fingerprint(
    real_rows: list[dict[str, float]],
    outcomes: list[float],
    experts: tuple[str, ...],
    window: int,
    lags: tuple[int, ...] = LAGS,
) -> dict[str, dict[str, float]] | None:
    """Correlate each name's prediction stream with the observation at each lag.

    ``real_rows`` and ``outcomes`` are aligned and end at the current month. The
    sample is the trailing ``window`` months; for lag ``k`` the prediction at
    month ``i`` is paired with the outcome at ``i - k``, which is always in the
    past.
    """
    n = len(real_rows)
    if window < 4 or n < window + max(lags):
        return None
    indices = list(range(n - window, n))
    out: dict[str, dict[str, float]] = {}
    for expert in experts:
        features: dict[str, float] = {}
        for lag in lags:
            paired_outcome = [float(outcomes[i - lag]) for i in indices]
            paired_prediction = [float(real_rows[i][expert]) for i in indices]
            features[f"lag{lag}"] = _corr(paired_prediction, paired_outcome)
        out[expert] = features
    return out


def _reference(
    real_rows: list[dict[str, float]],
    outcomes: list[float],
    experts: tuple[str, ...],
    window: int,
    up_to: int,
) -> tuple[dict[str, dict[str, float]], dict[str, tuple[float, float]]] | None:
    reference = lag_fingerprint(
        real_rows[:up_to], outcomes[:up_to], experts, window
    )
    if reference is None:
        return None
    return reference, feature_stats(reference, experts, LAG_FEATURES)


def _match(
    real_rows: list[dict[str, float]],
    outcomes: list[float],
    experts: tuple[str, ...],
    window: int,
    up_to: int,
    stats: dict[str, tuple[float, float]],
    reference_z: dict[str, dict[str, float]],
    excluded: str | None = None,
) -> dict[str, str] | None:
    observed = lag_fingerprint(real_rows[:up_to], outcomes[:up_to], experts, window)
    if observed is None:
        return None
    observed_z = apply_stats(observed, stats, experts, LAG_FEATURES)
    mapping, _ = assign(
        observed_z, reference_z, experts, excluded=excluded, features=LAG_FEATURES
    )
    return mapping


def measure_cell(
    rows: list[dict[str, object]],
    experts: tuple[str, ...],
    source: str,
    set_name: str,
) -> dict[str, object]:
    """Detect the shift from lag structure alone, using no current outcome."""
    evaluation = _evaluation_indices(rows)
    if len(evaluation) < 40:
        raise ValueError("too few evaluation months to split")
    swap_position = len(evaluation) // 2
    swap_at = evaluation[swap_position]
    swap_date = str(rows[swap_at]["date"])

    plain = prepare_swapped(rows, experts, swap_at, shifted=False)
    shifted = prepare_swapped(rows, experts, swap_at, shifted=True)

    # The lag features index the *full* row history, because a lag of 132 months
    # from the first evaluated month reaches back into the development period.
    control_real = [point["real"] for point in plain]
    shift_real = [point["real"] for point in shifted]
    outcomes = [float(row["outcome"]) for row in rows]  # type: ignore[arg-type]

    evaluation_rows = _evaluation_indices(rows)
    shift_row = evaluation_rows[swap_position]

    permutation = true_permutation(experts)
    identity_mapping = identity(experts)

    windows: dict[str, object] = {}
    for window in WINDOWS:
        reference_pack = _reference(
            shift_real, outcomes, experts, window, shift_row
        )
        if reference_pack is None:
            windows[str(window)] = {"skipped": "reference window too short"}
            continue
        reference, stats = reference_pack
        reference_z = apply_stats(reference, stats, experts, LAG_FEATURES)

        # ---- C4: the reference identifies a name against itself ----------
        half = shift_row // 2
        first = lag_fingerprint(shift_real[:half], outcomes[:half], experts, window)
        second = lag_fingerprint(
            shift_real[half:shift_row], outcomes[half:shift_row], experts, window
        )
        reference_is_stable = False
        if first is not None and second is not None:
            stats_second = feature_stats(second, experts, LAG_FEATURES)
            self_mapping, _ = assign(
                apply_stats(first, stats_second, experts, LAG_FEATURES),
                apply_stats(second, stats_second, experts, LAG_FEATURES),
                experts,
                features=LAG_FEATURES,
            )
            reference_is_stable = self_mapping == identity_mapping

        # ---- H2/H3: detection, month by month ---------------------------
        hits: list[bool] = []
        for offset in range(swap_position, len(evaluation_rows)):
            row_index = evaluation_rows[offset]
            mapping = _match(
                shift_real,
                outcomes,
                experts,
                window,
                row_index + 1,
                stats,
                reference_z,
            )
            hits.append(mapping == permutation)

        detection_delay = len(hits)
        for index in range(len(hits)):
            remaining = hits[index:]
            if hits[index] and sum(remaining) / len(remaining) >= STABLE_SHARE:
                detection_delay = index
                break

        scored = [hit for index, hit in enumerate(hits) if index + 1 >= window]
        accuracy = sum(scored) / len(scored) if scored else 0.0

        # ---- H4: the unshifted control must return the identity ---------
        control_identity = 0
        control_total = 0
        for offset in range(swap_position, len(evaluation_rows)):
            row_index = evaluation_rows[offset]
            mapping = _match(
                control_real,
                outcomes,
                experts,
                window,
                row_index + 1,
                stats,
                reference_z,
            )
            if mapping is None:
                continue
            control_total += 1
            if mapping == identity_mapping:
                control_identity += 1
        control_identity_rate = (
            control_identity / control_total if control_total else 0.0
        )

        # ---- H5: held-out reference, and whether distance separates ------
        held_distances: list[float] = []
        true_distances: list[float] = []
        held_wrong = 0
        held_total = 0
        settled = lag_fingerprint(
            shift_real, outcomes, experts, window
        )
        if settled is not None:
            settled_z = apply_stats(settled, stats, experts, LAG_FEATURES)
            for expert in experts:
                excluded = permutation[expert]
                _, held = assign(
                    settled_z,
                    reference_z,
                    experts,
                    excluded=excluded,
                    features=LAG_FEATURES,
                )
                _, matched = assign(
                    settled_z, reference_z, experts, features=LAG_FEATURES
                )
                held_distances.append(held[expert])
                true_distances.append(matched[expert])
                held_total += 1
                if held[expert] != excluded:
                    held_wrong += 1

        windows[str(window)] = {
            "accuracy": accuracy,
            "detection_delay": detection_delay,
            "post_shift_months": len(hits),
            "control_identity_rate": control_identity_rate,
            "reference_is_stable": reference_is_stable,
            "held_out_median_distance": (
                statistics.median(held_distances) if held_distances else float("nan")
            ),
            "true_match_median_distance": (
                statistics.median(true_distances) if true_distances else float("nan")
            ),
            "held_out_wrong": held_wrong,
            "held_out_total": held_total,
        }

    return {
        "source": source,
        "expert_set": set_name,
        "experts": list(experts),
        "swap_date": swap_date,
        "swap_position": swap_position,
        "evaluation_months": len(evaluation),
        "permutation": permutation,
        "windows": windows,
    }


def no_look_ahead(
    rows: list[dict[str, object]],
    experts: tuple[str, ...],
    probes: int = 8,
) -> float:
    """C1' — mutate every outcome at and after a probe month.

    The answer at that month must be bit-identical. A detector that read the
    current outcome, or any later one, would move.
    """
    evaluation = _evaluation_indices(rows)
    swap_position = len(evaluation) // 2
    swap_at = evaluation[swap_position]
    shifted = prepare_swapped(rows, experts, swap_at, shifted=True)
    real = [point["real"] for point in shifted]
    outcomes = [float(row["outcome"]) for row in rows]  # type: ignore[arg-type]

    post = evaluation[swap_position:]
    step = max(len(post) // probes, 1)
    worst = 0.0
    window = 36
    for probe in post[::step]:
        reference_pack = _reference(real, outcomes, experts, window, swap_at)
        if reference_pack is None:
            continue
        reference, stats = reference_pack
        reference_z = apply_stats(reference, stats, experts, LAG_FEATURES)
        clean = _match(
            real, outcomes, experts, window, probe + 1, stats, reference_z
        )
        mutated_outcomes = [
            value if index < probe else value * 1.7 + 3.0
            for index, value in enumerate(outcomes)
        ]
        dirty = _match(
            real, mutated_outcomes, experts, window, probe + 1, stats, reference_z
        )
        if clean is None or dirty is None:
            worst = max(worst, 1.0)
            continue
        for expert in experts:
            if clean[expert] != dirty[expert]:
                worst = max(worst, 1.0)
    return worst


def run_investigation(
    silso_path: Path,
    noaa_path: Path,
    output_directory: Path,
) -> dict[str, object]:
    """Measure the exploratory lag fingerprint."""
    if output_directory.exists():
        raise FileExistsError(output_directory)
    output_directory.mkdir(parents=True)

    sunspots, sunspots_excluded = parse_silso_monthly(silso_path)
    co2, co2_excluded = parse_noaa_monthly(noaa_path)
    observations = {"sunspots": sunspots, "co2": co2}

    cells: list[dict[str, object]] = []
    look_ahead_worst = 0.0
    for source, rows_in in observations.items():
        for set_name in EXPERT_SETS:
            experts = EXPERT_SETS[set_name]
            expert_rows = _expert_rows_for(rows_in, experts)  # type: ignore[arg-type]
            cells.append(measure_cell(expert_rows, experts, source, set_name))
            look_ahead_worst = max(
                look_ahead_worst, no_look_ahead(expert_rows, experts)
            )

    # C4 is a per-cell validity check, not a global verdict. A cell whose
    # reference cannot identify a name against itself is not a measurement, and
    # including it would average noise into the result. The exclusion is on the
    # control alone — it never looks at the shift — so it is not selection on the
    # outcome. The count is reported because the exclusions are themselves a
    # finding.
    valid: list[tuple[str, dict[str, object]]] = []
    invalid: list[tuple[str, str]] = []
    for cell in cells:
        for key, window in cell["windows"].items():  # type: ignore[union-attr]
            if "accuracy" not in window:
                continue
            if bool(window.get("reference_is_stable", False)):
                valid.append((key, window))
            else:
                invalid.append((str(cell["source"]), key))

    invalid_by_source: dict[str, int] = {}
    for source_name, _ in invalid:
        invalid_by_source[source_name] = invalid_by_source.get(source_name, 0) + 1

    controls = {
        "no_look_ahead": look_ahead_worst <= EXACT,
        "no_look_ahead_worst": look_ahead_worst,
        "valid_cells": len(valid),
        "invalid_cells": len(invalid),
        "invalid_by_source": invalid_by_source,
        "invalid_reason": (
            "C4: the reference could not identify a name against itself, so the "
            "cell is not a measurement of detection"
        ),
    }

    aggregates: dict[str, dict[str, float]] = {}
    for window in WINDOWS:
        key = str(window)
        entries = [entry for entry_key, entry in valid if entry_key == key]
        if not entries:
            continue
        aggregates[key] = {
            "cells": float(len(entries)),
            "accuracy_median": statistics.median(
                float(entry["accuracy"]) for entry in entries
            ),
            "delay_median": statistics.median(
                float(entry["detection_delay"]) for entry in entries
            ),
            "control_identity_median": statistics.median(
                float(entry["control_identity_rate"]) for entry in entries
            ),
            "held_out_distance_median": statistics.median(
                float(entry["held_out_median_distance"]) for entry in entries
            ),
            "true_distance_median": statistics.median(
                float(entry["true_match_median_distance"]) for entry in entries
            ),
        }

    h2 = any(entry["accuracy_median"] >= 0.9 for entry in aggregates.values())
    ordered = [aggregates[str(w)] for w in WINDOWS if str(w) in aggregates]
    h3 = (
        len(ordered) >= 2
        and all(
            ordered[i]["delay_median"] <= ordered[i + 1]["delay_median"]
            for i in range(len(ordered) - 1)
        )
        and all(
            ordered[i]["accuracy_median"] <= ordered[i + 1]["accuracy_median"]
            for i in range(len(ordered) - 1)
        )
    )
    h4 = bool(aggregates) and all(
        entry["control_identity_median"] >= 0.9 for entry in aggregates.values()
    )
    h5 = bool(aggregates) and all(
        entry["held_out_distance_median"] > entry["true_distance_median"]
        for entry in aggregates.values()
    )

    conditions = {
        "2_recognition_works": bool(h2),
        "3_frontier_is_monotone": bool(h3),
        "4_control_returns_identity": bool(h4),
        "5_held_out_distance_separates": bool(h5),
    }
    failed = [name for name, ok in conditions.items() if not ok]
    if not controls["no_look_ahead"]:
        verdict = "control_failed:look_ahead"
    elif not valid:
        verdict = "control_failed:no_valid_cells"
    elif not failed:
        verdict = "lag_fingerprint_detects_the_shift_ex_ante"
    else:
        verdict = "partial:" + ",".join(failed)

    results: dict[str, object] = {
        "method_version": METHOD_VERSION,
        "exploratory": True,
        "why_exploratory": (
            "written after the registered shape fingerprint failed its own C4; "
            "the lag features were chosen on principle (an expert is defined by "
            "its lag structure) but the timing makes the evidence weaker"
        ),
        "verdict": verdict,
        "conditions": conditions,
        "conditions_failed": failed,
        "controls": controls,
        "windows": {str(w): aggregates.get(str(w), {}) for w in WINDOWS},
        "parameters": {
            "windows": list(WINDOWS),
            "lags": list(LAGS),
            "assignment": ASSIGNMENT,
            "retention": RETENTION,
            "gap": GAP,
            "stable_share": STABLE_SHARE,
        },
        "excluded": {"sunspots": sunspots_excluded, "co2": co2_excluded},
        "cells": cells,
    }

    (output_directory / "results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True), encoding="utf-8"
    )
    return results
