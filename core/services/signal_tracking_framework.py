"""Spec-driven framework for the ``*_signal_tracking`` family.

Background
----------
~35 ``core/services/*_signal_tracking.py`` modules (~20k lines) share the same
6-function skeleton — ``track_..._for_visible_turn`` → ``refresh_..._statuses``
→ ``build_..._surface`` + ``_extract`` / ``_build_candidate`` / ``_persist`` — but
the **only truly unique part is candidate extraction** (~40%). The remaining
scaffolding (persist, refresh-to-stale, surface-bucketing, event publishing)
varies only along a bounded set of *knobs*.

This module centralises that scaffolding **without leaking any one file's
behaviour into the others**. Every behavioural difference the 35 files exhibit
is a first-class field on :class:`SignalTrackingSpec`:

* status sets (refreshable, surface order) — vary widely (``{active,softening}``
  is the mode; reflection's ``{active,integrating,settled}`` is atypical),
* stale window + optional early-retire predicate (only 3 files early-retire),
* supersede grouping convention (``_for_domain``/``_for_focus``/… or none),
* which status events are published, plus extra ones (``.settled`` reflection-only,
  ``.completed`` goal-only, ``.carried``/``.fading`` witness-only) and their payloads,
* confidence rank table, canonical-key format, per-signal summary strings.

Candidate extraction and candidate construction stay in the per-signal module and
are injected as callables. The framework NEVER hardcodes reflection's defaults.

Fail-safety mirrors the originals: persist/refresh publish best-effort and never
raise into the caller's visible turn.

The util helpers (:func:`parse_dt`, :func:`merge_fragments`) are provided as
**configurable supersets** — the originals were NOT byte-identical (12/17 variants
with semantic tz/Z differences), so each is toggle-driven; a call site opts into
exactly the behaviour it had before.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus


# ── configurable superset utils ──────────────────────────────────────────────
def parse_dt(value: Any, *, z_normalize: bool = True, tz_normalize: bool = False) -> datetime | None:
    """ISO → datetime, superset of the 12 original variants.

    ``z_normalize`` maps a trailing ``Z`` to ``+00:00`` (present in ~half the
    originals). ``tz_normalize`` forces the result to UTC (only autonomy_pressure
    and open_loop did this — dropping it would break their tz-aware staleness).
    Returns ``None`` on any parse failure (never raises).
    """
    try:
        text = str(value or "")
        if z_normalize:
            text = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
    except (ValueError, TypeError):
        return None
    if tz_normalize and parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def merge_fragments(*parts: Any, cap: int = 4, sep: str = " | ") -> str:
    """De-duplicated, whitespace-normalised join of text fragments (capped)."""
    merged: list[str] = []
    seen: set[str] = set()
    for part in parts:
        normalized = " ".join(str(part or "").split()).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
        if len(merged) >= cap:
            break
    return sep.join(merged)


# ── spec ─────────────────────────────────────────────────────────────────────
def _default_early_retire(_item: dict[str, object]) -> bool:
    return False


@dataclass(frozen=True)
class SignalTrackingSpec:
    """Everything the framework needs to run one signal's lifecycle.

    Only ``name``/``slug``/the DB callables/``extract_fn`` are required; every
    other field defaults to the *majority* behaviour (S-family: flat 7-day window,
    ``{active,softening}`` statuses, the 4 standard events, no early-retire). A
    richer file (reflection, witness, goal) overrides the specific knobs it needs.
    """

    # identity / naming
    name: str                                   # "reflection", "attachment_topology"
    slug: str                                   # canonical-key prefix, "reflection-signal"
    signal_id_prefix: str = ""                  # defaults to name if empty
    event_prefix: str = ""                      # defaults to f"{name}_signal" if empty
    default_signal_type: str = ""               # persisted fallback signal_type

    # DB bindings (names are NOT uniform — inject the callables)
    list_fn: Callable[..., list[dict[str, object]]] = None  # type: ignore[assignment]
    upsert_fn: Callable[..., dict[str, object]] = None      # type: ignore[assignment]
    update_status_fn: Callable[..., dict[str, object] | None] = None  # type: ignore[assignment]
    supersede_fn: Callable[..., int] | None = None
    supersede_group_field: str | None = "domain_key"        # key on the candidate dict
    supersede_group_kw: str = "domain_key"                  # kwarg name on supersede_fn

    # candidate extraction + construction (the unique part)
    extract_fn: Callable[["SignalTrackingSpec", dict[str, object]], list[dict[str, object]]] = None  # type: ignore[assignment]

    # lifecycle windows / statuses
    stale_after_days: int = 7
    early_retire_days: int | None = None                    # only reflection/dream/goal
    early_retire_predicate: Callable[[dict[str, object]], bool] = _default_early_retire
    refresh_scan_limit: int = 3000
    refreshable_statuses: frozenset[str] = frozenset({"active", "softening"})
    stale_status_name: str = "stale"
    stale_status_reason: str = "Marked stale after bounded signal inactivity window."

    # surface
    surface_status_order: Sequence[str] = ("active", "softening", "stale", "superseded")
    surface_active_statuses: frozenset[str] = frozenset({"active", "softening"})
    surface_history_cap: int = 6
    history_item_fn: Callable[[dict[str, object]], dict[str, object]] | None = None
    summary_fn: Callable[[dict[str, object]], dict[str, object]] | None = None
    empty_current_label: str = "No active signal"

    # events: which standard ones fire + extras keyed by status
    publish_created: bool = True
    publish_updated: bool = True
    publish_stale: bool = True
    publish_superseded: bool = True
    extra_status_events: dict[str, str] = field(default_factory=dict)  # status -> event name
    stale_payload_extra: tuple[str, ...] = ()      # extra keys copied onto the .stale payload
    superseded_payload_extra: tuple[str, ...] = ()

    # track() shape
    takes_user_message: bool = False
    track_summary_fn: Callable[[list[dict[str, object]], str], str] | None = None

    def ev(self, leaf: str) -> str:
        return f"{self.event_prefix or (self.name + '_signal')}.{leaf}"

    def new_signal_id(self) -> str:
        from uuid import uuid4
        return f"{self.signal_id_prefix or self.name}-{uuid4().hex}"


# ── generic lifecycle ────────────────────────────────────────────────────────
def track_for_visible_turn(
    spec: SignalTrackingSpec,
    *,
    session_id: str | None,
    run_id: str,
    user_message: str = "",
    context: dict[str, object] | None = None,
) -> dict[str, object]:
    """Extract candidates for this turn and persist them. Never raises."""
    normalized_session_id = str(session_id or "").strip()
    normalized_message = " ".join(str(user_message or "").split()).strip()
    ctx: dict[str, object] = dict(context or {})
    if spec.takes_user_message:
        ctx["user_message"] = normalized_message

    candidates = list(spec.extract_fn(spec, ctx) or [])
    items = persist_signals(
        spec, signals=candidates, session_id=normalized_session_id, run_id=run_id
    )
    if spec.track_summary_fn is not None:
        summary = spec.track_summary_fn(items, normalized_message)
    else:
        summary = (
            f"Tracked {len(items)} bounded {spec.name} signals."
            if items
            else f"No bounded {spec.name} signal warranted tracking."
        )
    return {
        "created": len([i for i in items if i.get("was_created")]),
        "updated": len([i for i in items if i.get("was_updated")]),
        "items": items,
        "summary": summary,
    }


def refresh_statuses(spec: SignalTrackingSpec) -> dict[str, int]:
    """Mark long-inactive signals stale. Preserves each spec's exact window +
    optional early-retire branch (default: none)."""
    now = datetime.now(UTC)
    refreshed = 0
    for item in spec.list_fn(limit=spec.refresh_scan_limit):
        if str(item.get("status") or "") not in spec.refreshable_statuses:
            continue
        updated_at = parse_dt(str(item.get("updated_at") or item.get("created_at") or ""))
        if updated_at is None:
            continue
        stale_after = spec.stale_after_days
        if spec.early_retire_days is not None and spec.early_retire_predicate(item):
            stale_after = spec.early_retire_days
        if updated_at > now - timedelta(days=stale_after):
            continue
        refreshed_item = spec.update_status_fn(
            str(item.get("signal_id") or ""),
            status=spec.stale_status_name,
            updated_at=now.isoformat(),
            status_reason=spec.stale_status_reason,
        )
        if refreshed_item is None:
            continue
        refreshed += 1
        if spec.publish_stale:
            payload = {
                "signal_id": refreshed_item.get("signal_id"),
                "signal_type": refreshed_item.get("signal_type"),
                "status": refreshed_item.get("status"),
                "summary": refreshed_item.get("summary"),
            }
            for k in spec.stale_payload_extra:
                payload[k] = refreshed_item.get(k)
            _publish(spec.ev("stale"), payload)
    return {"stale_marked": refreshed}


def build_surface(spec: SignalTrackingSpec, *, limit: int = 8) -> dict[str, object]:
    """Refresh, list, bucket by status, summarise — the read surface."""
    refresh_statuses(spec)
    items = spec.list_fn(limit=max(limit, 1))
    buckets: dict[str, list[dict[str, object]]] = {
        s: [i for i in items if str(i.get("status") or "") == s]
        for s in spec.surface_status_order
    }
    ordered: list[dict[str, object]] = []
    for s in spec.surface_status_order:
        ordered.extend(buckets[s])
    active = any(buckets[s] for s in spec.surface_status_order if s in spec.surface_active_statuses)
    latest = next(iter(ordered), None)
    summary: dict[str, object] = {f"{s}_count": len(buckets[s]) for s in spec.surface_status_order}
    summary["current_signal"] = str((latest or {}).get("title") or spec.empty_current_label)
    summary["current_status"] = str((latest or {}).get("status") or "none")
    history_src = items[: min(max(limit, 1), spec.surface_history_cap)]
    recent_history = (
        [spec.history_item_fn(i) for i in history_src]
        if spec.history_item_fn is not None
        else history_src
    )
    surface: dict[str, object] = {
        "active": bool(active),
        "items": ordered,
        "recent_history": recent_history,
        "summary": summary,
    }
    if spec.summary_fn is not None:
        surface = spec.summary_fn(surface)  # type: ignore[assignment]
    return surface


def persist_signals(
    spec: SignalTrackingSpec,
    *,
    signals: list[dict[str, object]],
    session_id: str,
    run_id: str,
) -> list[dict[str, object]]:
    """Upsert candidates, supersede same-group siblings, publish events."""
    now = datetime.now(UTC).isoformat()
    persisted: list[dict[str, object]] = []
    for signal in signals:
        item = spec.upsert_fn(
            signal_id=spec.new_signal_id(),
            signal_type=str(signal.get("signal_type") or spec.default_signal_type or spec.name),
            canonical_key=str(signal.get("canonical_key") or ""),
            status=str(signal.get("status") or "active"),
            title=str(signal.get("title") or ""),
            summary=str(signal.get("summary") or ""),
            rationale=str(signal.get("rationale") or ""),
            source_kind=str(signal.get("source_kind") or "runtime-derived-support"),
            confidence=str(signal.get("confidence") or "low"),
            evidence_summary=str(signal.get("evidence_summary") or ""),
            support_summary=str(signal.get("support_summary") or ""),
            support_count=int(signal.get("support_count") or 1),
            session_count=int(signal.get("session_count") or 1),
            created_at=now,
            updated_at=now,
            status_reason=str(signal.get("status_reason") or ""),
            run_id=run_id,
            session_id=session_id,
        )
        _supersede_and_publish(spec, signal=signal, item=item, now=now)
        _publish_lifecycle(spec, item=item)
        persisted.append(item)
    return persisted


def _supersede_and_publish(
    spec: SignalTrackingSpec, *, signal: dict[str, object], item: dict[str, object], now: str
) -> None:
    if spec.supersede_fn is None or spec.supersede_group_field is None:
        return
    group_val = str(signal.get(spec.supersede_group_field) or "")
    if not group_val:
        return
    count = spec.supersede_fn(
        **{spec.supersede_group_kw: group_val},
        exclude_signal_id=str(item.get("signal_id") or ""),
        updated_at=now,
        status_reason=f"Superseded by newer bounded {spec.name} signal {item.get('signal_id')}.",
    )
    if count and spec.publish_superseded:
        payload = {
            "signal_id": item.get("signal_id"),
            "signal_type": item.get("signal_type"),
            "superseded_count": count,
            "summary": item.get("summary"),
        }
        for k in spec.superseded_payload_extra:
            payload[k] = item.get(k)
        _publish(spec.ev("superseded"), payload)


def _publish_lifecycle(spec: SignalTrackingSpec, *, item: dict[str, object]) -> None:
    created = bool(item.get("was_created"))
    updated = bool(item.get("was_updated"))
    base = {
        "signal_id": item.get("signal_id"),
        "signal_type": item.get("signal_type"),
        "status": item.get("status"),
        "summary": item.get("summary"),
    }
    if created and spec.publish_created:
        _publish(spec.ev("created"), base)
    elif updated and spec.publish_updated:
        _publish(spec.ev("updated"), base)
    if created or updated:
        status = str(item.get("status") or "")
        leaf = spec.extra_status_events.get(status)
        if leaf:
            _publish(leaf if "." in leaf else spec.ev(leaf), base)


# ── candidate construction helper (called from per-signal extract logic) ──────
_CONF_RANKS_LO = {"low": 0, "medium": 1, "high": 2}


def make_candidate(
    spec: SignalTrackingSpec,
    *,
    signal_type: str,
    discriminator: str,
    key: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    status_reason: str,
    source_items: Iterable[dict[str, object] | None] = (),
    confidence: str | None = None,
    group_value: str | None = None,
    source_kind: str = "multi-signal-runtime-derivation",
    fragment_cap: int = 4,
) -> dict[str, object]:
    """Build a candidate dict with a spec-formatted canonical_key.

    ``canonical_key`` = ``f"{spec.slug}:{discriminator}:{key}"`` (drop the middle
    by passing ``discriminator=""``). ``confidence`` may be supplied by the caller
    (per-family rules differ); if omitted it's ``high`` when ≥3 source items else
    ``medium``. ``group_value`` seeds the supersede-grouping field.
    """
    items = [i for i in source_items if i]
    if confidence is None:
        confidence = "high" if len(items) >= 3 else "medium"
    support_count = max([int(i.get("support_count") or 1) for i in items], default=1)
    session_count = max([int(i.get("session_count") or 1) for i in items], default=1)
    canonical = ":".join(p for p in (spec.slug, discriminator, key) if p != "")
    candidate: dict[str, object] = {
        "signal_type": signal_type,
        "canonical_key": canonical,
        "status": status,
        "title": title,
        "summary": summary,
        "rationale": rationale,
        "source_kind": source_kind,
        "confidence": confidence,
        "evidence_summary": merge_fragments(
            *[str(i.get("evidence_summary") or "") for i in items], cap=fragment_cap
        ),
        "support_summary": merge_fragments(
            *[str(i.get("support_summary") or "") for i in items], cap=fragment_cap
        ),
        "support_count": support_count,
        "session_count": session_count,
        "status_reason": status_reason,
    }
    if spec.supersede_group_field is not None:
        candidate[spec.supersede_group_field] = group_value if group_value is not None else key
    return candidate


def stronger_confidence(*values: str, ranks: dict[str, int] | None = None) -> str:
    """Highest-ranked confidence among ``values`` (S-family merge)."""
    table = ranks or _CONF_RANKS_LO
    best = "low"
    best_rank = -1
    for v in values:
        r = table.get(str(v or "").strip().lower(), -1)
        if r > best_rank:
            best_rank, best = r, str(v or "low")
    return best


def _publish(event_name: str, payload: dict[str, object]) -> None:
    try:
        event_bus.publish(event_name, payload)
    except Exception:
        pass
