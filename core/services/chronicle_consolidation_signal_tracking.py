"""Chronicle/consolidation signal tracking — migrated onto signal_tracking_framework.

The public surface is unchanged (byte-identical behaviour): the three functions
below delegate the shared lifecycle scaffolding (persist / refresh-to-stale /
surface bucketing / event publishing) to :mod:`signal_tracking_framework`, while
the chronicle-specific candidate derivation (drawing on other subsystem read
surfaces) and the chronicle-projection enrichment stay here — that is the part
unique to this signal.

This is a ``_for_domain`` S-family variant with a longer 14-day stale window and a
bounded chronicle projection (``chronicle_type`` / ``chronicle_weight`` … plus the
``authority`` / ``layer_role`` / ``writeback_state`` control keys) on both the read
surface and the persist return. The read surface uses ``item_view_fn`` +
``surface_extra_fn``; the persist return applies the 2-arg ``_with_runtime_view``
(zipped with the originating candidates) in the thin ``track`` wrapper.
"""
from __future__ import annotations

from core.services import signal_tracking_framework as _stf
from core.services.signal_tracking_framework import SignalTrackingSpec
from core.services.executive_contradiction_signal_tracking import (
    build_runtime_executive_contradiction_signal_surface,
)
from core.services.private_state_snapshot_tracking import (
    build_runtime_private_state_snapshot_surface,
)
from core.services.private_temporal_promotion_signal_tracking import (
    build_runtime_private_temporal_promotion_signal_surface,
)
from core.services.remembered_fact_signal_tracking import (
    build_runtime_remembered_fact_signal_surface,
)
from core.services.self_review_cadence_signal_tracking import (
    build_runtime_self_review_cadence_signal_surface,
)
from core.services.self_review_outcome_tracking import (
    build_runtime_self_review_outcome_surface,
)
from core.runtime.db import (
    list_runtime_chronicle_consolidation_signals,
    supersede_runtime_chronicle_consolidation_signals_for_domain,
    update_runtime_chronicle_consolidation_signal_status,
    upsert_runtime_chronicle_consolidation_signal,
)

_STALE_AFTER_DAYS = 14
_CONFIDENCE_RANKS = {"low": 0, "medium": 1, "high": 2}


# ── public surface (thin delegates; signatures unchanged) ─────────────────────
def track_runtime_chronicle_consolidation_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    # Delegate the upsert/supersede/event scaffolding to the framework, but keep
    # the original 2-arg runtime-view enrichment (needs the originating candidate)
    # on the returned items — matching the pre-migration output exactly.
    normalized_session_id = str(session_id or "").strip()
    signals = _extract_chronicle_consolidation_candidates(run_id=run_id)
    persisted = _stf.persist_signals(
        _SPEC, signals=signals, session_id=normalized_session_id, run_id=run_id
    )
    items = [_with_runtime_view(item, signal) for item, signal in zip(persisted, signals)]
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded chronicle/consolidation signals."
            if items
            else "No bounded chronicle/consolidation signal warranted tracking."
        ),
    }


def refresh_runtime_chronicle_consolidation_signal_statuses() -> dict[str, int]:
    return _stf.refresh_statuses(_SPEC)


def build_runtime_chronicle_consolidation_signal_surface(*, limit: int = 8) -> dict[str, object]:
    return _stf.build_surface(_SPEC, limit=limit)


def _extract_chronicle_consolidation_candidates(*, run_id: str) -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for item in build_runtime_self_review_outcome_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["self_review_outcome"] = item

    for item in build_runtime_self_review_cadence_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["self_review_cadence"] = item

    for item in build_runtime_private_state_snapshot_surface(limit=12).get("items", []):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["private_state"] = item

    for item in build_runtime_private_temporal_promotion_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") != "active":
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["temporal_promotion"] = item

    for item in build_runtime_executive_contradiction_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        if str(item.get("run_id") or "") != run_id:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["executive_contradiction"] = item

    for item in build_runtime_remembered_fact_signal_surface(limit=12).get("items", []):
        if str(item.get("status") or "") not in {"active", "softening"}:
            continue
        domain_key = _domain_key(str(item.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["remembered_fact"] = item

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        outcome = snapshot.get("self_review_outcome")
        cadence = snapshot.get("self_review_cadence")
        if outcome is None or cadence is None:
            continue

        private_state = snapshot.get("private_state")
        temporal_promotion = snapshot.get("temporal_promotion")
        executive_contradiction = snapshot.get("executive_contradiction")
        remembered_fact = snapshot.get("remembered_fact")

        cadence_state = str(cadence.get("cadence_state") or "due")
        outcome_type = str(outcome.get("outcome_type") or "bounded-review")
        promotion_type = str((temporal_promotion or {}).get("promotion_type") or "")
        contradiction_pressure = str((executive_contradiction or {}).get("control_pressure") or "")

        chronicle_type = _chronicle_type(
            cadence_state=cadence_state,
            promotion_type=promotion_type,
            has_remembered_fact=remembered_fact is not None,
        )
        status = "active" if cadence_state in {"due", "lingering"} or temporal_promotion else "softening"
        chronicle_weight = _chronicle_weight(
            cadence_state=cadence_state,
            has_promotion=temporal_promotion is not None,
            contradiction_pressure=contradiction_pressure,
            outcome_status=str(outcome.get("status") or ""),
        )
        chronicle_focus = _focus_text(outcome, cadence, domain_key=domain_key)
        chronicle_summary = _merge_fragments(
            str(outcome.get("short_outcome") or outcome.get("summary") or ""),
            str(cadence.get("cadence_reason") or cadence.get("summary") or ""),
            str((private_state or {}).get("state_summary") or ""),
            str((temporal_promotion or {}).get("promotion_summary") or ""),
        )[:220]
        chronicle_confidence = _stronger_confidence(
            str(outcome.get("confidence") or "low"),
            str(cadence.get("confidence") or "low"),
            str((private_state or {}).get("state_confidence") or (private_state or {}).get("confidence") or ""),
            str((temporal_promotion or {}).get("promotion_confidence") or (temporal_promotion or {}).get("confidence") or ""),
            str((remembered_fact or {}).get("signal_confidence") or (remembered_fact or {}).get("confidence") or ""),
            str((executive_contradiction or {}).get("control_confidence") or (executive_contradiction or {}).get("confidence") or ""),
        )
        source_anchor = _merge_fragments(
            _anchor(outcome),
            _anchor(cadence),
            _anchor(private_state),
            _anchor(temporal_promotion),
            _anchor(remembered_fact),
            _anchor(executive_contradiction),
        )
        evidence_summary = _merge_fragments(
            str(outcome.get("evidence_summary") or ""),
            str(cadence.get("evidence_summary") or ""),
            str((private_state or {}).get("evidence_summary") or ""),
            str((temporal_promotion or {}).get("evidence_summary") or ""),
            str((remembered_fact or {}).get("evidence_summary") or ""),
            str((executive_contradiction or {}).get("evidence_summary") or ""),
        )
        support_summary = _merge_fragments(
            "Derived only from self-review outcome, self-review cadence, and optional bounded state/promotion/fact/contradiction support.",
            source_anchor,
        )
        candidates.append(
            {
                "signal_type": "chronicle-consolidation",
                "canonical_key": f"chronicle-consolidation:{chronicle_type}:{domain_key}",
                "domain_key": domain_key,
                "status": status,
                "title": f"Chronicle consolidation support: {chronicle_focus}",
                "summary": _summary_line(
                    chronicle_type=chronicle_type,
                    chronicle_focus=chronicle_focus,
                ),
                "rationale": (
                    "A bounded chronicle/consolidation signal may return only when bounded self-review outcome and cadence already indicate a thread that looks worth carrying or consolidating, without writing to canonical files or becoming a diary engine."
                ),
                "source_kind": "runtime-derived-support",
                "confidence": chronicle_confidence,
                "evidence_summary": evidence_summary,
                "support_summary": support_summary,
                "support_count": 1,
                "session_count": 1,
                "status_reason": (
                    "Bounded chronicle/consolidation support remains non-authoritative runtime support and is not yet writing to chronicle or memory files."
                ),
                "chronicle_type": chronicle_type,
                "chronicle_focus": chronicle_focus,
                "chronicle_weight": chronicle_weight,
                "chronicle_summary": chronicle_summary,
                "chronicle_confidence": chronicle_confidence,
                "source_anchor": source_anchor,
                "grounding_mode": _grounding_mode(
                    has_private_state=private_state is not None,
                    has_temporal_promotion=temporal_promotion is not None,
                    has_remembered_fact=remembered_fact is not None,
                    has_executive_contradiction=executive_contradiction is not None,
                ),
                "writeback_state": "not-writing-to-canonical-files",
            }
        )

    return candidates[:4]


# ── chronicle-projection enrichment (unique — persist return + read surface) ───
def _with_runtime_view(item: dict[str, object], signal: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched.update(
        {
            "chronicle_type": signal.get("chronicle_type"),
            "chronicle_focus": signal.get("chronicle_focus"),
            "chronicle_weight": signal.get("chronicle_weight"),
            "chronicle_summary": signal.get("chronicle_summary"),
            "chronicle_confidence": signal.get("chronicle_confidence"),
            "source_anchor": signal.get("source_anchor"),
            "grounding_mode": signal.get("grounding_mode"),
            "writeback_state": signal.get("writeback_state"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
        }
    )
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    chronicle_type = _value(
        item.get("chronicle_type"),
        _canonical_segment(str(item.get("canonical_key") or ""), index=1),
        default="chronicle-worthy",
    )
    chronicle_focus = _value(item.get("chronicle_focus"), item.get("title"), default="visible thread")
    chronicle_weight = _value(item.get("chronicle_weight"), default="medium")
    chronicle_summary = _value(
        item.get("chronicle_summary"),
        item.get("summary"),
        default="No bounded chronicle/consolidation support.",
    )
    chronicle_confidence = _value(
        item.get("chronicle_confidence"),
        item.get("confidence"),
        default="low",
    )
    enriched = dict(item)
    enriched.update(
        {
            "chronicle_type": chronicle_type,
            "chronicle_focus": chronicle_focus,
            "chronicle_weight": chronicle_weight,
            "chronicle_summary": chronicle_summary,
            "chronicle_confidence": chronicle_confidence,
            "source_anchor": _anchor(item),
            "grounding_mode": _value(item.get("grounding_mode"), default="self-review-outcome+self-review-cadence"),
            "writeback_state": _value(item.get("writeback_state"), default="not-writing-to-canonical-files"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "source": "/mc/runtime.chronicle_consolidation_signal",
            "createdAt": str(item.get("created_at") or ""),
        }
    )
    return enriched


def _chronicle_consolidation_surface_extra(
    summary: dict[str, object], latest: dict[str, object] | None
) -> dict[str, object]:
    current = latest or {}
    return {
        "authority": "non-authoritative",
        "layer_role": "runtime-support",
        "writeback_state": "not-writing-to-canonical-files",
        "summary_extra": {
            "current_chronicle_type": str(current.get("chronicle_type") or "none"),
            "current_weight": str(current.get("chronicle_weight") or "low"),
            "current_confidence": str(current.get("chronicle_confidence") or "low"),
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "writeback_state": "not-writing-to-canonical-files",
        },
    }


def _chronicle_type(
    *,
    cadence_state: str,
    promotion_type: str,
    has_remembered_fact: bool,
) -> str:
    if promotion_type == "carry-forward":
        return "consolidation-worthy"
    if cadence_state == "lingering":
        return "carry-forward-thread"
    if has_remembered_fact:
        return "anchored-thread"
    return "chronicle-worthy"


def _chronicle_weight(
    *,
    cadence_state: str,
    has_promotion: bool,
    contradiction_pressure: str,
    outcome_status: str,
) -> str:
    if contradiction_pressure == "high" or (has_promotion and cadence_state in {"due", "lingering"}):
        return "high"
    if outcome_status in {"fresh", "active"} or cadence_state in {"due", "lingering"}:
        return "medium"
    return "low"


def _focus_text(
    outcome: dict[str, object],
    cadence: dict[str, object],
    *,
    domain_key: str,
) -> str:
    for key in ("review_focus", "chronicle_focus", "title", "summary"):
        value = str(outcome.get(key) or "").strip()
        if value:
            return value[:96]
    value = str(cadence.get("title") or "").strip()
    if value:
        return value[:96]
    return domain_key.replace("-", " ")[:96]


def _summary_line(*, chronicle_type: str, chronicle_focus: str) -> str:
    return (
        f"Bounded chronicle/consolidation support is marking {chronicle_focus.lower()} as {chronicle_type.replace('-', ' ')}."
    )


def _grounding_mode(
    *,
    has_private_state: bool,
    has_temporal_promotion: bool,
    has_remembered_fact: bool,
    has_executive_contradiction: bool,
) -> str:
    parts = ["self-review-outcome", "self-review-cadence"]
    if has_private_state:
        parts.append("private-state")
    if has_temporal_promotion:
        parts.append("temporal-promotion")
    if has_remembered_fact:
        parts.append("remembered-fact")
    if has_executive_contradiction:
        parts.append("executive-contradiction")
    return "+".join(parts)


def _domain_key(canonical_key: str) -> str:
    parts = [part.strip() for part in canonical_key.split(":") if part.strip()]
    if len(parts) >= 3:
        return _slug(parts[-1])
    return ""


def _canonical_segment(value: str, *, index: int) -> str:
    parts = [part.strip() for part in value.split(":") if part.strip()]
    if len(parts) > index:
        return parts[index]
    return ""


def _anchor(item: dict[str, object] | None) -> str:
    if not item:
        return ""
    return str(item.get("source_anchor") or item.get("support_summary") or item.get("summary") or "").strip()[:180]


def _merge_fragments(*parts: str) -> str:
    seen: list[str] = []
    for part in parts:
        normalized = " ".join(str(part or "").split()).strip()
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.append(normalized)
    return " | ".join(seen)


def _stronger_confidence(*values: str) -> str:
    winner = "low"
    best = -1
    for value in values:
        rank = _CONFIDENCE_RANKS.get(str(value or "").strip().lower(), -1)
        if rank > best:
            best = rank
            winner = str(value or "").strip().lower() or "low"
    return winner


def _value(*values: object, default: str = "") -> str:
    for value in values:
        normalized = str(value or "").strip()
        if normalized:
            return normalized
    return default


def _slug(value: str) -> str:
    lowered = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    collapsed = "-".join(part for part in lowered.split("-") if part)
    return collapsed[:64]


# ── spec: standard S-family knobs (14-day window) + _for_domain + surface hooks ─
_SPEC = SignalTrackingSpec(
    name="chronicle-consolidation",
    slug="chronicle-consolidation",
    signal_id_prefix="chronicle-consolidation-signal",
    event_prefix="chronicle_consolidation_signal",
    default_signal_type="chronicle-consolidation",
    list_fn=list_runtime_chronicle_consolidation_signals,
    upsert_fn=upsert_runtime_chronicle_consolidation_signal,
    update_status_fn=update_runtime_chronicle_consolidation_signal_status,
    supersede_fn=supersede_runtime_chronicle_consolidation_signals_for_domain,
    supersede_group_field="domain_key",
    supersede_group_kw="domain_key",
    extract_fn=lambda spec, ctx: _extract_chronicle_consolidation_candidates(run_id=str(ctx.get("run_id") or "")),
    stale_after_days=_STALE_AFTER_DAYS,
    refresh_scan_limit=40,
    refreshable_statuses=frozenset({"active", "softening"}),
    stale_status_reason="Marked stale after bounded chronicle/consolidation inactivity window.",
    surface_status_order=("active", "softening", "stale", "superseded"),
    surface_active_statuses=frozenset({"active", "softening"}),
    empty_current_label="No active chronicle/consolidation support",
    item_view_fn=_with_surface_view,
    surface_extra_fn=_chronicle_consolidation_surface_extra,
    omit_recent_history=True,
    stale_payload_extra=("status_reason",),
)
