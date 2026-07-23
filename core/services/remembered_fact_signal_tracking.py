"""Remembered-fact signal tracking — migrated onto signal_tracking_framework.

The public surface is unchanged (byte-identical behaviour): the three functions
below delegate the shared lifecycle scaffolding (persist / refresh-to-stale /
surface bucketing / event publishing) to :mod:`signal_tracking_framework`, while
the remembered-fact-specific candidate derivation (explicit user-name / project-
anchor / working-context extraction) and the small runtime/surface view
enrichment stay here — that is the part unique to this signal.

Supersede grouping is by ``dimension_key`` (the fact dimension). Persisted
``summary`` comes from the candidate's ``fact_summary`` (falling back to
``summary``), and the read surface carries ``current_signal_type`` /
``current_signal_confidence`` on top of the standard counts — both expressed via
the framework's hooks so nothing leaks and nothing is lost.
"""
from __future__ import annotations

import re

from core.services.chat_sessions import get_chat_session
from core.services import signal_tracking_framework as _stf
from core.services.signal_tracking_framework import SignalTrackingSpec
from core.runtime.db import (
    list_runtime_remembered_fact_signals,
    supersede_runtime_remembered_fact_signals_for_dimension,
    update_runtime_remembered_fact_signal_status,
    upsert_runtime_remembered_fact_signal,
)
from core.services.text_clip import clip_text

_CONFIDENCE_RANKS = {"low": 1, "medium": 2, "high": 3}
_STALE_AFTER_DAYS = 14
_NAME_PATTERNS = (
    re.compile(r"\bmit navn er ([A-Za-zÆØÅæøå][A-Za-zÆØÅæøå' -]{0,40})", re.IGNORECASE),
    re.compile(r"\bjeg hedder ([A-Za-zÆØÅæøå][A-Za-zÆØÅæøå' -]{0,40})", re.IGNORECASE),
    re.compile(r"\bmy name is ([A-Za-z][A-Za-z' -]{0,40})", re.IGNORECASE),
    re.compile(r"\bi am called ([A-Za-z][A-Za-z' -]{0,40})", re.IGNORECASE),
)


# ── public surface (thin delegates; signatures unchanged) ─────────────────────
def track_runtime_remembered_fact_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
    user_message: str,
) -> dict[str, object]:
    # Keep the original empty-evidence guard and the 2-arg runtime-view
    # enrichment (needs the originating candidate) while delegating the
    # upsert/supersede/event scaffolding to the framework.
    normalized_session_id = str(session_id or "").strip()
    normalized_message = " ".join(str(user_message or "").split()).strip()
    if not normalized_message and not normalized_session_id:
        return {
            "created": 0,
            "updated": 0,
            "items": [],
            "summary": "No bounded remembered-fact evidence was available.",
        }

    signals = _extract_remembered_fact_candidates(
        user_message=normalized_message,
        session_id=normalized_session_id,
    )
    for signal in signals:
        signal["summary"] = str(signal.get("fact_summary") or signal.get("summary") or "")

    persisted = _stf.persist_signals(
        _SPEC, signals=signals, session_id=normalized_session_id, run_id=run_id
    )
    items = [_with_runtime_view(item, signal) for item, signal in zip(persisted, signals)]
    return {
        "created": len([item for item in items if item.get("was_created")]),
        "updated": len([item for item in items if item.get("was_updated")]),
        "items": items,
        "summary": (
            f"Tracked {len(items)} bounded remembered-fact signals."
            if items
            else "No bounded remembered-fact signal warranted tracking."
        ),
    }


def refresh_runtime_remembered_fact_signal_statuses() -> dict[str, int]:
    return _stf.refresh_statuses(_SPEC)


def build_runtime_remembered_fact_signal_surface(*, limit: int = 8) -> dict[str, object]:
    return _stf.build_surface(_SPEC, limit=limit)


def _extract_remembered_fact_candidates(
    *,
    user_message: str,
    session_id: str,
) -> list[dict[str, object]]:
    messages = _recent_user_messages(session_id=session_id, current_message=user_message)
    if not messages:
        return []

    signals = [
        _explicit_user_name_fact(messages),
        _explicit_project_anchor_fact(messages),
        _explicit_working_context_fact(messages),
    ]

    deduped: dict[str, dict[str, object]] = {}
    for signal in signals:
        if not signal:
            continue
        canonical_key = str(signal.get("canonical_key") or "")
        if not canonical_key:
            continue
        current = deduped.get(canonical_key)
        if current is None:
            deduped[canonical_key] = signal
            continue
        if _rank_confidence(str(signal.get("confidence") or "")) >= _rank_confidence(
            str(current.get("confidence") or "")
        ):
            deduped[canonical_key] = signal
    return list(deduped.values())[:4]


def _explicit_user_name_fact(messages: list[str]) -> dict[str, object] | None:
    for message in messages:
        fact_value = _extract_name_value(message)
        if not fact_value:
            continue
        return {
            "signal_type": "explicit-user-fact",
            "canonical_key": "remembered-fact:explicit-user-fact:user-name",
            "dimension_key": "user-name",
            "status": "active",
            "title": "Remembered fact: user name",
            "fact_summary": f"User explicitly stated their name as {fact_value}.",
            "rationale": "An explicit self-identifying name statement is a small factual memory cue, not a broad profile.",
            "source_kind": "user-explicit",
            "confidence": "high",
            "evidence_summary": _quote(message),
            "support_summary": _merge_fragments(
                "A recent user message explicitly stated the user's name.",
                _source_anchor(message),
            ),
            "support_count": 1,
            "session_count": 1,
            "status_reason": "An explicit self-identifying statement supports an active remembered-fact signal.",
            "fact_kind": "user-name",
            "source_anchor": _source_anchor(message),
            "signal_confidence": "high",
        }
    return None


def _explicit_project_anchor_fact(messages: list[str]) -> dict[str, object] | None:
    matched = [message for message in messages if _is_project_anchor_fact(message)]
    if not matched:
        return None
    source_message = matched[0]
    return {
        "signal_type": "explicit-project-fact",
        "canonical_key": "remembered-fact:explicit-project-fact:project-anchor",
        "dimension_key": "project-anchor",
        "status": "active",
        "title": "Remembered fact: shared project anchor",
        "fact_summary": "The user explicitly framed the work as building Jarvis together.",
        "rationale": "A direct project-anchor statement is a bounded factual continuity cue for workspace memory.",
        "source_kind": "user-explicit",
        "confidence": "high",
        "evidence_summary": _quote(source_message),
        "support_summary": _merge_fragments(
            f"{len(matched)} recent message(s) explicitly framed the collaboration as building Jarvis together.",
            _source_anchor(source_message),
        ),
        "support_count": len(matched),
        "session_count": 1,
        "status_reason": "An explicit shared-project statement supports an active remembered-fact signal.",
        "fact_kind": "project-anchor",
        "source_anchor": _source_anchor(source_message),
        "signal_confidence": "high",
    }


def _explicit_working_context_fact(messages: list[str]) -> dict[str, object] | None:
    matched = [message for message in messages if _is_working_context_fact(message)]
    if not matched:
        return None
    source_message = matched[0]
    confidence = "high" if len(matched) > 1 else "medium"
    return {
        "signal_type": "explicit-working-context-fact",
        "canonical_key": "remembered-fact:explicit-working-context-fact:repo-context",
        "dimension_key": "repo-context",
        "status": "active" if confidence == "high" else "softening",
        "title": "Remembered fact: working context",
        "fact_summary": "The user explicitly located the current collaboration in the Jarvis v2 repo.",
        "rationale": "A direct working-context statement is bounded memory-worthy context, not a user profile trait.",
        "source_kind": "user-explicit",
        "confidence": confidence,
        "evidence_summary": _quote(source_message),
        "support_summary": _merge_fragments(
            f"{len(matched)} recent message(s) explicitly named the Jarvis v2 repo as the current working context.",
            _source_anchor(source_message),
        ),
        "support_count": len(matched),
        "session_count": 1,
        "status_reason": "An explicit working-context statement supports a bounded remembered-fact signal.",
        "fact_kind": "repo-context",
        "source_anchor": _source_anchor(source_message),
        "signal_confidence": confidence,
    }


def _with_runtime_view(item: dict[str, object], signal: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["fact_kind"] = str(signal.get("fact_kind") or "")
    enriched["fact_summary"] = str(signal.get("fact_summary") or item.get("summary") or "")
    enriched["signal_confidence"] = str(signal.get("signal_confidence") or signal.get("confidence") or "low")
    enriched["source_anchor"] = str(signal.get("source_anchor") or "")
    return enriched


def _with_surface_view(item: dict[str, object]) -> dict[str, object]:
    enriched = dict(item)
    enriched["fact_kind"] = _dimension_from_canonical_key(str(item.get("canonical_key") or ""))
    enriched["fact_summary"] = str(item.get("summary") or "")
    enriched["signal_confidence"] = str(item.get("confidence") or "low")
    enriched["source_anchor"] = _source_anchor_from_support_summary(str(item.get("support_summary") or ""))
    return enriched


def _remembered_fact_surface_extra(
    summary: dict[str, object], latest: dict[str, object] | None
) -> dict[str, object]:
    current = latest or {}
    return {
        "summary_extra": {
            "current_signal_type": str(current.get("signal_type") or "none"),
            "current_signal_confidence": str(current.get("signal_confidence") or "low"),
        },
    }


def _recent_user_messages(*, session_id: str, current_message: str) -> list[str]:
    messages: list[str] = []
    seen: set[str] = set()

    normalized_current = " ".join(str(current_message or "").split()).strip()
    if normalized_current:
        seen.add(normalized_current)
        messages.append(normalized_current)

    if session_id:
        session = get_chat_session(session_id)
        for item in reversed((session or {}).get("messages") or []):
            if str(item.get("role") or "") != "user":
                continue
            text = " ".join(str(item.get("content") or "").split()).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            messages.append(text)
            if len(messages) >= 6:
                break
    return messages[:6]


def _extract_name_value(message: str) -> str:
    text = " ".join(str(message or "").split()).strip()
    for pattern in _NAME_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        candidate = " ".join(match.group(1).split()).strip(" .,!?:;\"'")
        if not candidate:
            continue
        return candidate[:48]
    return ""


def _is_project_anchor_fact(message: str) -> bool:
    lower = message.lower()
    return _contains_any(
        lower,
        (
            "vi bygger jarvis sammen",
            "we are building jarvis together",
            "jarvis og jeg bygger det sammen",
            "you and i are building jarvis together",
        ),
    )


def _is_working_context_fact(message: str) -> bool:
    lower = message.lower()
    if not _contains_any(
        lower,
        (
            "jarvis v2-repoet",
            "jarvis v2 repoet",
            "jarvis v2-repo",
            "jarvis v2 repo",
            "jarvis-v2",
            "/media/projects/jarvis-v2",
            "~/.jarvis-v2/shared",
            ".jarvis-v2/shared",
            "~/.jarvis-v2/workspaces/default",
            ".jarvis-v2/workspaces/default",
        ),
    ):
        return False
    return _contains_any(
        lower,
        (
            "du arbejder i",
            "you are working in",
            "du arbejder på",
            "we are in",
            "repo",
            "repoet",
            "workspace",
            "sti",
            "path",
        ),
    )


def _dimension_from_canonical_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    if len(parts) < 3:
        return ""
    return parts[-1]


def _source_anchor(text: str) -> str:
    quoted = _quote(text)
    return f"Visible user anchor: {quoted}" if quoted else ""


def _source_anchor_from_support_summary(summary: str) -> str:
    for fragment in str(summary or "").split(" | "):
        if fragment.startswith("Visible user anchor:"):
            return fragment
    return ""


def _quote(text: str, *, limit: int = 160) -> str:
    normalized = " ".join(str(text or "").split()).strip()
    if not normalized:
        return ""
    if len(normalized) <= limit:
        return normalized
    return clip_text(normalized, limit=limit)


def _merge_fragments(*parts: str) -> str:
    seen: set[str] = set()
    merged: list[str] = []
    for part in parts:
        normalized = " ".join(str(part or "").split()).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return " | ".join(merged[:4])


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _rank_confidence(confidence: str) -> int:
    return _CONFIDENCE_RANKS.get(str(confidence or "").lower(), 0)


# ── spec: dimension-grouped supersede + surface hooks made explicit ───────────
_SPEC = SignalTrackingSpec(
    name="remembered-fact",
    slug="remembered-fact",
    signal_id_prefix="remembered-fact",
    event_prefix="remembered_fact_signal",
    default_signal_type="explicit-project-fact",
    list_fn=list_runtime_remembered_fact_signals,
    upsert_fn=upsert_runtime_remembered_fact_signal,
    update_status_fn=update_runtime_remembered_fact_signal_status,
    supersede_fn=supersede_runtime_remembered_fact_signals_for_dimension,
    supersede_group_field="dimension_key",
    supersede_group_kw="dimension_key",
    extract_fn=lambda spec, ctx: _extract_remembered_fact_candidates(
        user_message=str(ctx.get("user_message") or ""),
        session_id=str(ctx.get("session_id") or ""),
    ),
    stale_after_days=_STALE_AFTER_DAYS,
    refresh_scan_limit=40,
    refreshable_statuses=frozenset({"active", "softening"}),
    stale_status_reason="Marked stale after bounded remembered-fact inactivity window.",
    surface_status_order=("active", "softening", "stale", "superseded"),
    surface_active_statuses=frozenset({"active", "softening"}),
    empty_current_label="No active remembered-fact signal",
    item_view_fn=_with_surface_view,
    surface_extra_fn=_remembered_fact_surface_extra,
    omit_recent_history=True,
    stale_payload_extra=("status_reason",),
)
