"""Broadcast Daemon — detects emergent coherence across daemons (Experiment 3: GWT).

Runs every 2 minutes. Groups workspace entries by topic similarity (Jaccard > 0.4).
When 3+ unique sources cluster on same topic → broadcasts workspace.broadcast event.

Metric: workspace_coherence = broadcast events with 3+ sources / total (rolling 24h).
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import uuid4

logger = logging.getLogger(__name__)

_EXPERIMENT_ID = "global_workspace"
_COHERENCE_THRESHOLD = 3  # min unique sources for broadcast
_JACCARD_THRESHOLD = 0.4  # min topic similarity to cluster


def tick_broadcast_daemon() -> dict[str, object]:
    """Run one coherence analysis pass. Returns dict with broadcast_count/coherence."""
    from core.runtime.db import get_experiment_enabled
    if not get_experiment_enabled(_EXPERIMENT_ID):
        return {"generated": False, "reason": "disabled"}

    from apps.api.jarvis_api.services.global_workspace import get_workspace_snapshot
    entries = list(get_workspace_snapshot())

    # Supplement with active emotion concepts
    try:
        from apps.api.jarvis_api.services.emotion_concepts import get_active_emotion_concepts
        for concept in get_active_emotion_concepts()[:3]:
            entries.append({
                "source": "emotion_concepts",
                "topic": str(concept.get("concept", "")),
                "signal_type": "emotion_concept.active",
                "payload_summary": f"intensity={concept.get('intensity', 0):.2f}",
                "timestamp": datetime.now(UTC).isoformat(),
            })
    except Exception:
        pass

    if not entries:
        return {"generated": False, "reason": "empty_workspace", "broadcast_count": 0}

    clusters = _cluster_by_topic(entries)

    broadcast_count = 0
    for cluster in clusters:
        unique_sources = list({e["source"] for e in cluster})
        if len(unique_sources) >= _COHERENCE_THRESHOLD:
            topic_cluster = _representative_topic(cluster)
            _fire_broadcast(cluster, unique_sources, topic_cluster)
            broadcast_count += 1

    coherence = _compute_coherence()

    return {
        "generated": broadcast_count > 0,
        "broadcast_count": broadcast_count,
        "workspace_coherence": coherence,
        "entries_analyzed": len(entries),
    }


def build_workspace_surface() -> dict[str, object]:
    """MC surface for global workspace experiment."""
    from core.runtime.db import get_experiment_enabled, list_broadcast_events
    from apps.api.jarvis_api.services.global_workspace import get_workspace_snapshot

    enabled = get_experiment_enabled(_EXPERIMENT_ID)
    snapshot = get_workspace_snapshot()
    recent_broadcasts = list_broadcast_events(limit=5)

    topics = list(dict.fromkeys(e["topic"] for e in snapshot[-20:] if e.get("topic")))[:5]

    return {
        "active": enabled,
        "enabled": enabled,
        "buffer_size": len(snapshot),
        "active_topics": topics,
        "workspace_coherence": round(_compute_coherence(), 3),
        "recent_broadcasts": recent_broadcasts[:5],
        "last_broadcast_at": recent_broadcasts[0]["created_at"] if recent_broadcasts else "",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _cluster_by_topic(entries: list[dict]) -> list[list[dict]]:
    """Group entries into clusters where Jaccard similarity of topics >= threshold."""
    from apps.api.jarvis_api.services.global_workspace import _topic_jaccard
    clusters: list[list[dict]] = []
    for entry in entries:
        placed = False
        for cluster in clusters:
            rep_topic = _representative_topic(cluster)
            if _topic_jaccard(entry["topic"], rep_topic) >= _JACCARD_THRESHOLD:
                cluster.append(entry)
                placed = True
                break
        if not placed:
            clusters.append([entry])
    return clusters


def _representative_topic(cluster: list[dict]) -> str:
    """Return the most common meaningful words across all topics in cluster."""
    all_words: list[str] = []
    for entry in cluster:
        all_words.extend(w.lower() for w in str(entry.get("topic", "")).split() if len(w) > 3)
    if not all_words:
        return ""
    return " ".join(w for w, _ in Counter(all_words).most_common(3))


def _fire_broadcast(
    cluster: list[dict],
    unique_sources: list[str],
    topic_cluster: str,
) -> None:
    """Persist broadcast event and publish to eventbus."""
    event_id = f"bc-{uuid4().hex[:10]}"
    payload_summary = f"Coherent cluster: {len(cluster)} signals from {len(unique_sources)} sources"
    try:
        from core.runtime.db import insert_broadcast_event
        insert_broadcast_event(
            event_id=event_id,
            topic_cluster=topic_cluster,
            sources=json.dumps(unique_sources),
            source_count=len(unique_sources),
            payload_summary=payload_summary,
        )
    except Exception:
        pass
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("workspace.broadcast", {
            "topic_cluster": topic_cluster,
            "sources": unique_sources,
            "source_count": len(unique_sources),
        })
    except Exception:
        pass


def _compute_coherence() -> float:
    """workspace_coherence = broadcast events with 3+ sources / total events (rolling 24h)."""
    try:
        from core.runtime.db import list_broadcast_events
        since_iso = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
        events = list_broadcast_events(limit=200)
        # Filter to last 24h manually (our list_broadcast_events doesn't support since_iso)
        events = [e for e in events if e.get("created_at", "") >= since_iso]
        if not events:
            return 0.0
        coherent = sum(1 for e in events if int(e.get("source_count", 0)) >= _COHERENCE_THRESHOLD)
        return coherent / len(events)
    except Exception:
        return 0.0
