"""Transparent discrete measurements used by the first exploration."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Hashable, Sequence


def entropy(values: Sequence[Hashable]) -> float:
    """Return plug-in Shannon entropy in bits."""
    if not values:
        return 0.0
    counts = Counter(values)
    total = len(values)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def mutual_information(xs: Sequence[Hashable], ys: Sequence[Hashable]) -> float:
    """Return plug-in mutual information in bits for paired discrete values."""
    if len(xs) != len(ys):
        raise ValueError("paired measurements must have the same length")
    if not xs:
        return 0.0
    return max(0.0, entropy(xs) + entropy(ys) - entropy(list(zip(xs, ys, strict=True))))


def perspective_metrics(rows: list[dict[str, int | str]]) -> dict[str, float]:
    outcomes = [int(row["outcome"]) for row in rows]
    cues = [int(row["cue"]) for row in rows]
    contexts = [int(row["context"]) for row in rows]
    joint_context = list(zip(cues, contexts, strict=True))
    return {
        "outcome_only": mutual_information(outcomes[:-1], outcomes[1:]),
        "cue_access": mutual_information(cues, outcomes),
        "cue_context_access": mutual_information(joint_context, outcomes),
    }
