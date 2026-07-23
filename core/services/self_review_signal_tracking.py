"""Self-review signal tracking — migrated onto signal_tracking_framework.

The public surface is unchanged (byte-identical behaviour): the three functions
below delegate the shared lifecycle scaffolding (persist / refresh-to-stale /
surface bucketing / event publishing) to :mod:`signal_tracking_framework`, while
the self-review-specific cross-layer candidate derivation and domain-key mapping
stay here — that is the part unique to self-review.

This is an X-family variant: it composes many layers (focus / goal / recurrence /
witness / reflection / open-loop / internal-opposition) into multi-candidate
readings, using the same ``high if >=3 source items else medium`` confidence rule
reflection uses — but *without* reflection's early-retire window or ``.settled``
event. It is a plain ``{active,softening}`` S-family surface (no ``recent_history``).
"""
from __future__ import annotations

from core.services import signal_tracking_framework as _stf
from core.services.signal_tracking_framework import SignalTrackingSpec, make_candidate
from core.services.internal_opposition_signal_tracking import (
    build_runtime_internal_opposition_signal_surface,
)
from core.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_reflection_signals,
    list_runtime_self_review_signals,
    list_runtime_temporal_recurrence_signals,
    list_runtime_witness_signals,
    supersede_runtime_self_review_signals_for_domain,
    update_runtime_self_review_signal_status,
    upsert_runtime_self_review_signal,
)

_STALE_AFTER_DAYS = 14


# ── public surface (thin delegates; signatures unchanged) ─────────────────────
def track_runtime_self_review_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    return _stf.track_for_visible_turn(_SPEC, session_id=session_id, run_id=run_id)


def refresh_runtime_self_review_signal_statuses() -> dict[str, int]:
    return _stf.refresh_statuses(_SPEC)


def build_runtime_self_review_signal_surface(*, limit: int = 8) -> dict[str, object]:
    return _stf.build_surface(_SPEC, limit=limit)


# ── self-review-specific cross-layer candidate derivation (unique ~40%) ───────
def _extract_self_review_candidates(*_args, **_kwargs) -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for focus in list_runtime_development_focuses(limit=18):
        if str(focus.get("status") or "") != "active":
            continue
        domain_key = _focus_domain_key(str(focus.get("canonical_key") or ""))
        if domain_key:
            snapshots.setdefault(domain_key, {})["active_focus"] = focus

    for goal in list_runtime_goal_signals(limit=18):
        status = str(goal.get("status") or "")
        if status not in {"active", "blocked"}:
            continue
        domain_key = _goal_domain_key(str(goal.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "blocked":
            bucket["blocked_goal"] = goal
        else:
            bucket["active_goal"] = goal

    for recurrence in list_runtime_temporal_recurrence_signals(limit=18):
        status = str(recurrence.get("status") or "")
        if status not in {"active", "softening"}:
            continue
        domain_key = _temporal_domain_key(str(recurrence.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "active":
            bucket["active_recurrence"] = recurrence
        else:
            bucket["softening_recurrence"] = recurrence

    for witness in list_runtime_witness_signals(limit=18):
        status = str(witness.get("status") or "")
        if status not in {"fresh", "carried"}:
            continue
        domain_key = _witness_domain_key(str(witness.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "fresh":
            bucket["fresh_witness"] = witness
        else:
            bucket["carried_witness"] = witness

    for reflection in list_runtime_reflection_signals(limit=18):
        status = str(reflection.get("status") or "")
        if status not in {"integrating", "settled"}:
            continue
        domain_key = _reflection_domain_key(str(reflection.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "integrating":
            bucket["integrating_reflection"] = reflection
        else:
            bucket["settled_reflection"] = reflection

    for item in build_runtime_open_loop_signal_surface(limit=12).get("items", []):
        status = str(item.get("status") or "")
        if status not in {"open", "softening"}:
            continue
        domain_key = _open_loop_domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "open":
            bucket["open_loop"] = item
        else:
            bucket["softening_loop"] = item

    for item in build_runtime_internal_opposition_signal_surface(limit=12).get("items", []):
        status = str(item.get("status") or "")
        if status not in {"active", "softening"}:
            continue
        domain_key = _internal_opposition_domain_key(str(item.get("canonical_key") or ""))
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "active":
            bucket["active_opposition"] = item
        else:
            bucket["softening_opposition"] = item

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        active_focus = snapshot.get("active_focus")
        active_goal = snapshot.get("active_goal")
        blocked_goal = snapshot.get("blocked_goal")
        active_recurrence = snapshot.get("active_recurrence")
        softening_recurrence = snapshot.get("softening_recurrence")
        fresh_witness = snapshot.get("fresh_witness")
        carried_witness = snapshot.get("carried_witness")
        integrating_reflection = snapshot.get("integrating_reflection")
        settled_reflection = snapshot.get("settled_reflection")
        open_loop = snapshot.get("open_loop")
        softening_loop = snapshot.get("softening_loop")
        active_opposition = snapshot.get("active_opposition")
        softening_opposition = snapshot.get("softening_opposition")
        title_suffix = _domain_title(domain_key)

        if open_loop and active_opposition and (active_recurrence or integrating_reflection):
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="review-pressure",
                    status="active",
                    title=f"Self-review needed: {title_suffix}",
                    summary=f"This bounded thread around {title_suffix.lower()} now looks like it should enter explicit self-review.",
                    rationale="An unresolved open loop is now paired with active internal opposition and continuing recurrence or integration pressure.",
                    status_reason="Open-loop pressure and active internal challenge make this domain a bounded self-review candidate.",
                    source_items=[open_loop, active_opposition, active_recurrence, integrating_reflection, active_focus, active_goal, blocked_goal],
                )
            )
            continue

        if active_recurrence and (open_loop or active_opposition) and (active_focus or active_goal or blocked_goal):
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="review-due-by-recurrence",
                    status="active",
                    title=f"Review by recurrence: {title_suffix}",
                    summary=f"This bounded thread around {title_suffix.lower()} keeps returning strongly enough that it now looks review-worthy.",
                    rationale="Repeated recurrence is still present while unresolved pressure or internal opposition remains live around the same domain.",
                    status_reason="Recurring tension plus live direction/opposition makes bounded self-review look due.",
                    source_items=[active_recurrence, open_loop, active_opposition, active_focus, active_goal, blocked_goal],
                )
            )
            continue

        if (fresh_witness or carried_witness) and (softening_loop or softening_opposition or softening_recurrence) and (active_focus or active_goal or blocked_goal or settled_reflection):
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="review-carried-thread",
                    status="softening",
                    title=f"Review carried thread: {title_suffix}",
                    summary=f"This bounded thread around {title_suffix.lower()} looks calmer, but still seems worth a small self-review before it fully drops out of focus.",
                    rationale="A carried or freshly witnessed lesson is still coupled to softening loop/opposition/recurrence evidence, so the domain looks review-worthy even without sharp pressure.",
                    status_reason="A carried lesson remains visible enough that bounded self-review still looks relevant, though the pressure is softening.",
                    source_items=[fresh_witness, carried_witness, softening_loop, softening_opposition, softening_recurrence, active_focus, active_goal, blocked_goal, settled_reflection],
                )
            )

    return candidates[:4]


def _build_candidate(
    *,
    domain_key: str,
    signal_type: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    status_reason: str,
    source_items: list[dict[str, object] | None],
) -> dict[str, object]:
    # canonical_key = "self-review:{signal_type}:{domain_key}"; confidence high
    # when >=3 source layers else medium (make_candidate's default) — matches the
    # original exactly. source_kind is the file's own "runtime-derived-support".
    return make_candidate(
        _SPEC,
        signal_type=signal_type,
        discriminator=signal_type,
        key=domain_key,
        status=status,
        title=title,
        summary=summary,
        rationale=rationale,
        status_reason=status_reason,
        source_items=source_items,
        source_kind="runtime-derived-support",
        group_value=domain_key,
    )


# ── spec: standard S-family knobs + _for_domain supersede ──────────────────────
_SPEC = SignalTrackingSpec(
    name="self-review",
    slug="self-review",
    signal_id_prefix="self-review",
    event_prefix="self_review_signal",
    default_signal_type="self-review-signal",
    list_fn=list_runtime_self_review_signals,
    upsert_fn=upsert_runtime_self_review_signal,
    update_status_fn=update_runtime_self_review_signal_status,
    supersede_fn=supersede_runtime_self_review_signals_for_domain,
    supersede_group_field="domain_key",
    supersede_group_kw="domain_key",
    extract_fn=_extract_self_review_candidates,
    stale_after_days=_STALE_AFTER_DAYS,
    refresh_scan_limit=40,
    refreshable_statuses=frozenset({"active", "softening"}),
    stale_status_reason="Marked stale after bounded self-review inactivity window.",
    surface_status_order=("active", "softening", "stale", "superseded"),
    surface_active_statuses=frozenset({"active", "softening"}),
    empty_current_label="No active self-review signal",
    omit_recent_history=True,
    stale_payload_extra=("status_reason",),
)


# ── self-review-specific domain-key mapping + labels (unique) ──────────────────
def _focus_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _goal_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 2 else ""


def _temporal_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _witness_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _reflection_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _open_loop_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _internal_opposition_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _domain_title(domain_key: str) -> str:
    text = str(domain_key or "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Self-review"
