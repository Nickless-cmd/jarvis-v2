from __future__ import annotations


def build_private_operational_preference(
    *,
    private_initiative_tension: dict[str, object] | None,
    private_temporal_curiosity_state: dict[str, object] | None,
    private_relation_state: dict[str, object] | None,
) -> dict[str, object]:
    tension = private_initiative_tension or {}
    curiosity = private_temporal_curiosity_state or {}
    relation = private_relation_state or {}

    if not (tension or curiosity or relation):
        return {
            "active": False,
            "current": None,
        }

    preferred_lane = _preferred_lane(
        tension=tension,
        curiosity=curiosity,
        relation=relation,
    )
    created_at = (
        tension.get("created_at")
        or curiosity.get("created_at")
        or relation.get("created_at")
    )

    return {
        "active": True,
        "current": {
            "preference_id": (
                "private-operational-preference:"
                f"{tension.get('signal_id') or curiosity.get('signal_id') or relation.get('relation_id') or 'current'}"
            ),
            "source": (
                "private-initiative-tension+private-temporal-curiosity-state+"
                "private-relation-state"
            ),
            "preferred_lane": preferred_lane,
            "preference_reason": _preference_reason(
                preferred_lane=preferred_lane,
                tension=tension,
                curiosity=curiosity,
                relation=relation,
            ),
            "confidence": _confidence(
                preferred_lane=preferred_lane,
                tension=tension,
                curiosity=curiosity,
                relation=relation,
            ),
            "created_at": created_at,
        },
    }


def _preferred_lane(
    *,
    tension: dict[str, object],
    curiosity: dict[str, object],
    relation: dict[str, object],
) -> str:
    interaction_mode = str(relation.get("interaction_mode") or "").strip()
    tension_kind = str(tension.get("tension_kind") or "").strip()
    curiosity_carry = str(curiosity.get("curiosity_carry") or "").strip()

    if interaction_mode == "user-tool-work":
        return "coding"
    if tension_kind == "curiosity-pull" and curiosity_carry in {"carried", "held"}:
        return "coding"
    return "cheap"


def _preference_reason(
    *,
    preferred_lane: str,
    tension: dict[str, object],
    curiosity: dict[str, object],
    relation: dict[str, object],
) -> str:
    interaction_mode = str(relation.get("interaction_mode") or "").strip()
    if preferred_lane == "coding" and interaction_mode == "user-tool-work":
        return "user-tool-work"
    if preferred_lane == "coding":
        return str(curiosity.get("curiosity_carry") or tension.get("tension_kind") or "curiosity-pull")[
            :64
        ]
    return str(relation.get("relation_pull") or tension.get("reason") or "respond-current-user")[
        :64
    ]


def _confidence(
    *,
    preferred_lane: str,
    tension: dict[str, object],
    curiosity: dict[str, object],
    relation: dict[str, object],
) -> str:
    if preferred_lane == "coding":
        return str(
            tension.get("confidence") or curiosity.get("confidence") or relation.get("confidence") or "low"
        )[:32]
    return str(
        relation.get("confidence") or tension.get("confidence") or curiosity.get("confidence") or "low"
    )[:32]
