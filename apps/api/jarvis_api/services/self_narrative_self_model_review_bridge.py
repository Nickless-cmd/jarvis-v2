from __future__ import annotations

from apps.api.jarvis_api.services.self_model_signal_tracking import (
    build_runtime_self_model_signal_surface,
)
from apps.api.jarvis_api.services.self_narrative_continuity_signal_tracking import (
    build_runtime_self_narrative_continuity_signal_surface,
)

_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


def build_runtime_self_narrative_self_model_review_bridge_surface(
    *,
    limit: int = 4,
) -> dict[str, object]:
    narrative_surface = build_runtime_self_narrative_continuity_signal_surface(limit=max(limit, 1))
    self_model_surface = build_runtime_self_model_signal_surface(limit=max(limit, 1))

    narrative_items = [
        item
        for item in narrative_surface.get("items", [])
        if str(item.get("status") or "") in {"active", "softening"}
    ]
    self_model_items = [
        item
        for item in self_model_surface.get("items", [])
        if str(item.get("status") or "") in {"active", "uncertain", "corrected"}
    ]

    bridge_items: list[dict[str, object]] = []
    current_self_model = next(iter(self_model_items), None)
    for narrative_item in narrative_items[: max(limit, 1)]:
        bridge_items.append(
            _build_bridge_item(
                narrative_item=narrative_item,
                self_model_item=current_self_model,
            )
        )

    active = bool(bridge_items)
    latest = bridge_items[0] if bridge_items else None
    patterns = [_pattern_view(item) for item in bridge_items]
    latest_pattern = patterns[0] if patterns else None
    return {
        "active": active,
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "review_mode": "read-only-review-support",
        "proposal_state": "not-selfhood-proposal",
        "canonical_identity_state": "not-canonical-identity-truth",
        "items": bridge_items,
        "patterns": patterns,
        "summary": {
            "active_count": len([item for item in bridge_items if str(item.get("status") or "") == "active"]),
            "softening_count": len([item for item in bridge_items if str(item.get("status") or "") == "softening"]),
            "pattern_count": len(patterns),
            "current_bridge": str((latest or {}).get("title") or "No active self-narrative review bridge"),
            "current_pattern": str((latest_pattern or {}).get("pattern_summary") or "No active self-narrative pattern summary"),
            "current_status": str((latest or {}).get("status") or "none"),
            "current_state": str((latest or {}).get("bridge_state") or "none"),
            "current_direction": str((latest or {}).get("bridge_direction") or "steadying"),
            "current_weight": str((latest or {}).get("bridge_weight") or "low"),
            "current_review_state": str((latest or {}).get("review_state") or "no-review-input"),
            "current_confidence": str((latest or {}).get("bridge_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "review_mode": "read-only-review-support",
            "proposal_state": "not-selfhood-proposal",
            "canonical_identity_state": "not-canonical-identity-truth",
        },
    }


def _build_bridge_item(
    *,
    narrative_item: dict[str, object],
    self_model_item: dict[str, object] | None,
) -> dict[str, object]:
    narrative_state = str(narrative_item.get("narrative_state") or "becoming-coherent")
    narrative_direction = str(narrative_item.get("narrative_direction") or "steadying")
    narrative_weight = str(narrative_item.get("narrative_weight") or "low")
    narrative_confidence = str(narrative_item.get("narrative_confidence") or narrative_item.get("confidence") or "low")
    narrative_focus = str(narrative_item.get("title") or "self narrative")

    self_model_status = str((self_model_item or {}).get("status") or "")
    self_model_title = str((self_model_item or {}).get("title") or "").strip()
    review_state = (
        "narrative-and-self-model-visible"
        if self_model_item is not None
        else "narrative-awaiting-self-model-context"
    )
    bridge_state = (
        "self-model-reviewable"
        if self_model_item is not None
        else "narrative-only-reviewable"
    )
    source_anchor = _merge_fragments(
        str(narrative_item.get("source_anchor") or ""),
        self_model_title,
    )
    bridge_confidence = _stronger_confidence(
        narrative_confidence,
        str((self_model_item or {}).get("confidence") or ""),
    )
    status = str(narrative_item.get("status") or "active")
    pattern_type = _pattern_type(
        narrative_state=narrative_state,
        narrative_direction=narrative_direction,
        review_state=review_state,
    )
    pattern_summary = _pattern_summary(
        pattern_type=pattern_type,
        narrative_direction=narrative_direction,
        narrative_weight=narrative_weight,
        self_model_title=self_model_title,
    )

    return {
        "bridge_id": f"self-narrative-review-bridge:{str(narrative_item.get('signal_id') or '')}",
        "signal_id": str(narrative_item.get("signal_id") or ""),
        "status": status,
        "title": f"Self-narrative review bridge: {narrative_focus.replace('Self-narrative support: ', '')}",
        "summary": (
            "Bounded read-only review bridge is exposing self-narrative continuity as possible self-model review input."
        ),
        "bridge_state": bridge_state,
        "bridge_direction": narrative_direction,
        "bridge_weight": narrative_weight,
        "bridge_summary": _bridge_summary(
            narrative_state=narrative_state,
            narrative_direction=narrative_direction,
            self_model_title=self_model_title,
        ),
        "bridge_confidence": bridge_confidence,
        "pattern_type": pattern_type,
        "pattern_direction": narrative_direction,
        "pattern_weight": narrative_weight,
        "pattern_summary": pattern_summary,
        "pattern_confidence": bridge_confidence,
        "source_anchor": source_anchor,
        "review_state": review_state,
        "self_model_signal_title": self_model_title or "No active self-model review input",
        "self_model_signal_status": self_model_status or "none",
        "status_reason": (
            "Bounded self-narrative review bridge remains read-only runtime support only, is not a selfhood proposal, and is not canonical identity truth."
        ),
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "review_mode": "read-only-review-support",
        "proposal_state": "not-selfhood-proposal",
        "canonical_identity_state": "not-canonical-identity-truth",
        "source": "/mc/runtime.self_narrative_self_model_review_bridge",
    }


def _pattern_view(item: dict[str, object]) -> dict[str, object]:
    return {
        "pattern_type": str(item.get("pattern_type") or "no-pattern"),
        "pattern_direction": str(item.get("pattern_direction") or "steadying"),
        "pattern_weight": str(item.get("pattern_weight") or "low"),
        "pattern_summary": str(item.get("pattern_summary") or item.get("bridge_summary") or ""),
        "pattern_confidence": str(item.get("pattern_confidence") or item.get("bridge_confidence") or "low"),
        "review_state": str(item.get("review_state") or "no-review-input"),
        "status": str(item.get("status") or "active"),
    }


def _pattern_type(
    *,
    narrative_state: str,
    narrative_direction: str,
    review_state: str,
) -> str:
    if narrative_state == "becoming-watchful":
        return "watchful-becoming-pattern"
    if narrative_state == "becoming-firm":
        return "firming-pattern"
    if narrative_state == "becoming-open":
        return "opening-pattern"
    if narrative_direction == "deepening":
        return "deepening-pattern"
    if review_state == "narrative-and-self-model-visible":
        return "coherent-review-pattern"
    return "steady-becoming-pattern"


def _pattern_summary(
    *,
    pattern_type: str,
    narrative_direction: str,
    narrative_weight: str,
    self_model_title: str,
) -> str:
    if self_model_title:
        return (
            f"Bounded pattern summary is reading a {narrative_weight} {pattern_type.replace('-', ' ')} "
            f"moving {narrative_direction} while {self_model_title.lower()} stays visible as read-only context."
        )
    return (
        f"Bounded pattern summary is reading a {narrative_weight} {pattern_type.replace('-', ' ')} "
        f"moving {narrative_direction} without active self-model context."
    )


def _bridge_summary(
    *,
    narrative_state: str,
    narrative_direction: str,
    self_model_title: str,
) -> str:
    if self_model_title:
        return (
            f"Bounded read-only bridge sees {narrative_state.replace('-', ' ')} moving {narrative_direction} "
            f"while {self_model_title.lower()} stays available as review context."
        )
    return (
        f"Bounded read-only bridge sees {narrative_state.replace('-', ' ')} moving {narrative_direction} "
        f"but no active self-model review context is currently visible."
    )


def _stronger_confidence(*values: str) -> str:
    strongest = "low"
    strongest_rank = -1
    for value in values:
        normalized = str(value or "").strip()
        rank = _CONFIDENCE_RANKS.get(normalized, -1)
        if rank > strongest_rank:
            strongest = normalized or strongest
            strongest_rank = rank
    return strongest if strongest in _CONFIDENCE_RANKS else "low"


def _merge_fragments(*parts: str) -> str:
    merged: list[str] = []
    for part in parts:
        text = " ".join(str(part or "").split()).strip()
        if not text or text in merged:
            continue
        merged.append(text)
    return " | ".join(merged)
