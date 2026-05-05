"""Concept baseline tracker — Layer 3 of emotion concepts integration.

Tracks concept-trigger frequency over time and aggregates to cluster-level
distributions. Real-time stats updated on each trigger; daily evaluation
runs via governance handler and proposes IDENTITY.md updates through the
existing identity_drift_proposer when stable drift signals are detected.

See docs/superpowers/specs/2026-05-05-emotion-concepts-baseline-integration-design.md
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _cluster_for_concept(concept: str) -> str:
    """Look up cluster for a concept. Falls back to UNKNOWN."""
    try:
        from core.services.emotion_concepts import CONCEPT_CLUSTERS
        for cluster_name, members in CONCEPT_CLUSTERS.items():
            if concept in members:
                return cluster_name
    except Exception:
        pass
    return "UNKNOWN"


def _tracker_enabled() -> bool:
    try:
        from core.runtime.settings import load_settings
        return bool(getattr(load_settings(), "concept_baseline_tracker_enabled", True))
    except Exception:
        return True


def _now() -> datetime:
    return datetime.now(UTC)


def _now_iso() -> str:
    return _now().isoformat()


def record_concept_trigger(
    *,
    concept: str,
    intensity: float,
    triggered_at: str,
    source: str,
) -> None:
    """Real-time: update per-concept stats when a concept fires."""
    if not _tracker_enabled():
        return
    try:
        from core.runtime.db import (
            get_concept_baseline_stat,
            upsert_concept_baseline_stat,
            increment_concept_baseline_total,
        )

        cluster = _cluster_for_concept(str(concept))
        existing = get_concept_baseline_stat(str(concept))
        if existing is None:
            upsert_concept_baseline_stat(
                concept=str(concept),
                cluster=cluster,
                total_triggers=1,
                triggers_7d=1,
                triggers_30d=1,
                mean_intensity_7d=float(intensity),
                last_triggered_at=str(triggered_at),
                first_triggered_at=str(triggered_at),
            )
        else:
            increment_concept_baseline_total(
                concept=str(concept),
                intensity=float(intensity),
                triggered_at=str(triggered_at),
            )
    except Exception as exc:
        logger.warning("concept_baseline_tracker: record failed: %s", exc)


def _aggregate_clusters() -> dict[str, dict[str, object]]:
    """Compute cluster-level share from total_triggers across all concepts."""
    try:
        from core.runtime.db import list_concept_baseline_stats
        stats = list_concept_baseline_stats()
    except Exception:
        return {}

    cluster_totals: dict[str, int] = {}
    cluster_concepts: dict[str, list[dict[str, object]]] = {}
    grand_total = 0
    for s in stats:
        cluster = str(s.get("cluster") or "UNKNOWN")
        total = int(s.get("total_triggers") or 0)
        cluster_totals[cluster] = cluster_totals.get(cluster, 0) + total
        cluster_concepts.setdefault(cluster, []).append(s)
        grand_total += total

    if grand_total == 0:
        return {}

    return {
        cluster: {
            "total": total,
            "share": total / grand_total,
            "concepts": sorted(
                cluster_concepts.get(cluster, []),
                key=lambda c: -int(c.get("total_triggers") or 0),
            ),
        }
        for cluster, total in cluster_totals.items()
    }


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------


_CLUSTER_DOMINANCE_SHARE = 0.55


def _detect_drift(
    cluster_stats: dict[str, dict[str, object]],
    per_concept_stats: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Detect drift signals from current stats."""
    signals: list[dict[str, object]] = []

    for cluster, data in cluster_stats.items():
        share = float(data.get("share") or 0.0)
        if share > _CLUSTER_DOMINANCE_SHARE and cluster != "UNKNOWN":
            confidence = min(1.0, (share - 0.4) * 2.0)
            signals.append({
                "type": "cluster_dominance",
                "cluster": cluster,
                "share": share,
                "confidence": confidence,
                "sustained_days": 1,  # v1: not actually time-tracked yet
            })

    return signals


# ---------------------------------------------------------------------------
# CONCEPT_BASELINE.md writer
# ---------------------------------------------------------------------------


def _workspace_dir():
    """Return path to active workspace directory. Indirected for tests."""
    from pathlib import Path
    from core.runtime.config import WORKSPACES_DIR
    return Path(WORKSPACES_DIR) / "default"


def _write_concept_baseline_md(
    cluster_stats: dict[str, dict[str, object]],
    per_concept_stats: list[dict[str, object]],
) -> None:
    """Write auto-managed CONCEPT_BASELINE.md to workspace dir."""
    try:
        ws = _workspace_dir()
        ws.mkdir(parents=True, exist_ok=True)
        md_path = ws / "CONCEPT_BASELINE.md"

        lines = [
            "# Emotional Baseline (auto-tracked)",
            f"> Auto-managed by concept_baseline_tracker. Last updated: {_now_iso()}.",
            "> Manual edits will be overwritten. For narrative changes to who I am, see IDENTITY.md.",
            "",
            "## Cluster distribution",
        ]

        for cluster, data in sorted(
            cluster_stats.items(),
            key=lambda kv: -float(kv[1].get("share") or 0.0),
        ):
            share = float(data.get("share") or 0.0)
            concept_summary = ", ".join(
                f"{c['concept']} {int(c.get('total_triggers') or 0)}"
                for c in (data.get("concepts") or [])[:5]
            )
            lines.append(f"- {cluster}: {share*100:.0f}% ({concept_summary})")

        lines += ["", "## Most active concepts", ""]
        lines.append("| Concept | Triggers | Last seen |")
        lines.append("|---------|----------|-----------|")
        for s in per_concept_stats[:10]:
            lines.append(
                f"| {s['concept']} | {s.get('total_triggers') or 0} | "
                f"{s.get('last_triggered_at') or '-'} |"
            )

        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as exc:
        logger.warning("concept_baseline_tracker: md write failed: %s", exc)


# ---------------------------------------------------------------------------
# Identity drift proposer integration
# ---------------------------------------------------------------------------


def _propose_identity_update(signal: dict[str, object]) -> dict[str, object]:
    """Forward a drift signal to identity_drift_proposer."""
    try:
        from core.services.identity_drift_proposer import propose_identity_update_if_drifted
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish(
                "concept_baseline.drift_signal_proposed",
                {
                    "signal_type": signal.get("type"),
                    "cluster": signal.get("cluster"),
                    "concept": signal.get("concept"),
                    "confidence": signal.get("confidence"),
                    "share": signal.get("share"),
                    "sustained_days": signal.get("sustained_days"),
                },
            )
        except Exception:
            pass
        return propose_identity_update_if_drifted()
    except Exception as exc:
        logger.warning(
            "concept_baseline_tracker: identity proposer failed: %s", exc,
        )
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# Daily evaluation
# ---------------------------------------------------------------------------


def evaluate_baseline_drift() -> dict[str, object]:
    """Daily: compute stats, write MD, propose drift updates if stable."""
    if not _tracker_enabled():
        return {"evaluated_at": _now_iso(), "skipped": True, "reason": "disabled"}

    try:
        from core.runtime.db import list_concept_baseline_stats
        from core.runtime.settings import load_settings
        s = load_settings()
        min_confidence = float(getattr(s, "concept_baseline_drift_min_confidence", 0.7))
        min_sustained = int(getattr(s, "concept_baseline_drift_min_sustained_days", 14))
    except Exception:
        return {"evaluated_at": _now_iso(), "skipped": True, "reason": "settings-load-failed"}

    cluster_stats = _aggregate_clusters()
    per_concept_stats = list_concept_baseline_stats()
    drift_signals = _detect_drift(cluster_stats, per_concept_stats)

    try:
        _write_concept_baseline_md(cluster_stats, per_concept_stats)
    except Exception as exc:
        logger.warning("concept_baseline_tracker: md write in evaluate failed: %s", exc)

    proposals_filed: list[dict[str, object]] = []
    for signal in drift_signals:
        confidence = float(signal.get("confidence") or 0.0)
        sustained = int(signal.get("sustained_days") or 0)
        if confidence >= min_confidence and sustained >= min_sustained:
            try:
                proposer_result = _propose_identity_update(signal)
                proposals_filed.append({"signal": signal, "result": proposer_result})
            except Exception as exc:
                logger.warning(
                    "concept_baseline_tracker: proposer call failed for %s: %s",
                    signal, exc,
                )

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "concept_baseline.evaluated",
            {
                "cluster_count": len(cluster_stats),
                "drift_signals_count": len(drift_signals),
                "proposals_filed": len(proposals_filed),
            },
        )
    except Exception:
        pass

    return {
        "evaluated_at": _now_iso(),
        "cluster_stats": cluster_stats,
        "drift_signals": drift_signals,
        "proposals_filed": proposals_filed,
    }


def build_concept_baseline_surface() -> dict[str, object]:
    """Read-only: return current state for Mission Control consumption."""
    try:
        from core.runtime.db import list_concept_baseline_stats
        per_concept = list_concept_baseline_stats()
    except Exception:
        per_concept = []
    return {
        "enabled": _tracker_enabled(),
        "concept_count": len(per_concept),
        "cluster_stats": _aggregate_clusters(),
        "top_concepts": per_concept[:10],
    }
