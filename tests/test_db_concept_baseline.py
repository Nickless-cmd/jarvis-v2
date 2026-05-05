from __future__ import annotations


def test_upsert_and_get_concept_stat(isolated_runtime) -> None:
    from core.runtime.db import (
        upsert_concept_baseline_stat,
        get_concept_baseline_stat,
    )

    upsert_concept_baseline_stat(
        concept="joy",
        cluster="JOY_APPROACH",
        total_triggers=5,
        triggers_7d=3,
        triggers_30d=5,
        mean_intensity_7d=0.55,
        last_triggered_at="2026-05-05T10:00:00+00:00",
        first_triggered_at="2026-05-04T08:00:00+00:00",
    )
    row = get_concept_baseline_stat("joy")
    assert row is not None
    assert row["cluster"] == "JOY_APPROACH"
    assert row["total_triggers"] == 5
    assert row["mean_intensity_7d"] == 0.55


def test_increment_concept_total(isolated_runtime) -> None:
    from core.runtime.db import (
        upsert_concept_baseline_stat,
        increment_concept_baseline_total,
        get_concept_baseline_stat,
    )

    upsert_concept_baseline_stat(
        concept="wonder",
        cluster="JOY_APPROACH",
        total_triggers=0,
        triggers_7d=0,
        triggers_30d=0,
    )
    increment_concept_baseline_total(
        concept="wonder",
        intensity=0.4,
        triggered_at="2026-05-05T11:00:00+00:00",
    )
    increment_concept_baseline_total(
        concept="wonder",
        intensity=0.6,
        triggered_at="2026-05-05T11:01:00+00:00",
    )
    row = get_concept_baseline_stat("wonder")
    assert row["total_triggers"] == 2
    assert row["last_triggered_at"] == "2026-05-05T11:01:00+00:00"


def test_list_concept_stats_returns_all(isolated_runtime) -> None:
    from core.runtime.db import (
        upsert_concept_baseline_stat,
        list_concept_baseline_stats,
    )

    for c, cluster in [
        ("joy", "JOY_APPROACH"),
        ("warmth", "SOCIAL_BONDING"),
        ("doubt", "DISTRESS_AVOIDANCE"),
    ]:
        upsert_concept_baseline_stat(
            concept=c, cluster=cluster, total_triggers=1,
            triggers_7d=1, triggers_30d=1,
        )
    rows = list_concept_baseline_stats()
    concepts = sorted(r["concept"] for r in rows)
    assert concepts == ["doubt", "joy", "warmth"]
