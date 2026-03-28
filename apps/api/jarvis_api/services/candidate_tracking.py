from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from apps.api.jarvis_api.services.chat_sessions import get_chat_session
from apps.api.jarvis_api.services.chat_sessions import list_chat_sessions
from apps.api.jarvis_api.services.self_authored_prompt_proposal_tracking import (
    build_runtime_self_authored_prompt_proposal_surface,
)
from apps.api.jarvis_api.services.selfhood_proposal_tracking import (
    build_runtime_selfhood_proposal_surface,
)
from apps.api.jarvis_api.services.memory_md_update_proposal_tracking import (
    build_runtime_memory_md_update_proposal_surface,
)
from apps.api.jarvis_api.services.user_md_update_proposal_tracking import (
    build_runtime_user_md_update_proposal_surface,
)
from core.eventbus.bus import event_bus
from core.identity.candidate_workflow import (
    auto_apply_safe_memory_md_candidates,
    auto_apply_safe_user_md_candidates,
)
from core.runtime.db import list_runtime_contract_candidates
from core.runtime.db import upsert_runtime_contract_candidate

_CONFIDENCE_RANKS = {"low": 1, "medium": 2, "high": 3}
_EVIDENCE_CLASS_RANKS = {
    "weak_signal": 1,
    "runtime_support_only": 2,
    "single_session_pattern": 3,
    "explicit_user_statement": 4,
    "repeated_cross_session": 5,
}


def track_runtime_contract_candidates_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
    user_message: str,
    assistant_message: str,
) -> dict[str, object]:
    del assistant_message
    normalized_message = " ".join(str(user_message or "").split()).strip()
    if not normalized_message:
        return {
            "created": 0,
            "preference_updates": 0,
            "memory_promotions": 0,
            "items": [],
        }

    candidates = _extract_candidates_from_messages(
        [normalized_message],
        session_id=str(session_id or ""),
    )
    return _persist_candidates(
        candidates=candidates,
        session_id=str(session_id or ""),
        run_id=run_id,
        source_mode="visible_chat",
        actor="runtime:visible-chat",
        status_reason="Candidate proposed from visible chat evidence.",
    )


def track_runtime_contract_candidates_for_session_review(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    normalized_session_id = str(session_id or "").strip()
    if not normalized_session_id:
        latest_session = next(iter(list_chat_sessions()), None)
        normalized_session_id = str(latest_session.get("id") or "") if latest_session else ""
    if not normalized_session_id:
        return {
            "created": 0,
            "preference_updates": 0,
            "memory_promotions": 0,
            "items": [],
            "session_id": "",
            "summary": "No chat session is available for heartbeat review.",
        }

    session = get_chat_session(normalized_session_id)
    if session is None:
        return {
            "created": 0,
            "preference_updates": 0,
            "memory_promotions": 0,
            "items": [],
            "session_id": normalized_session_id,
            "summary": "Session not found for heartbeat review.",
        }

    recent_user_messages = [
        " ".join(str(item.get("content") or "").split()).strip()
        for item in reversed(session.get("messages") or [])
        if str(item.get("role") or "") == "user"
    ]
    messages = [message for message in recent_user_messages[:4] if message]
    candidates = _extract_candidates_from_messages(
        messages,
        session_id=normalized_session_id,
    )
    result = _persist_candidates(
        candidates=candidates,
        session_id=normalized_session_id,
        run_id=run_id,
        source_mode="heartbeat",
        actor="runtime:heartbeat",
        status_reason="Candidate proposed from bounded heartbeat session review.",
    )
    return {
        **result,
        "session_id": normalized_session_id,
        "messages_scanned": len(messages),
        "summary": (
            f"Heartbeat reviewed {len(messages)} recent user messages and produced {result['created']} candidates."
            if messages
            else "No recent user messages were available for heartbeat review."
        ),
    }


def track_runtime_contract_candidates_from_user_md_update_proposals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    candidates = _extract_candidates_from_user_md_update_proposals()
    if not candidates:
        return {
            "created": 0,
            "updated": 0,
            "preference_updates": 0,
            "memory_promotions": 0,
            "items": [],
            "summary": "No bounded USER.md update proposal warranted candidate drafting.",
        }
    result = _persist_candidates(
        candidates=candidates,
        session_id=str(session_id or ""),
        run_id=run_id,
        source_mode="runtime_user_md_proposal",
        actor="runtime:user-md-update-bridge",
        status_reason="Candidate drafted from bounded USER.md update proposal.",
    )
    return {
        **result,
        "summary": f"Drafted {result['created']} governed USER.md candidates from bounded proposals.",
    }


def track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    candidates = _extract_candidates_from_memory_md_update_proposals()
    if not candidates:
        return {
            "created": 0,
            "updated": 0,
            "preference_updates": 0,
            "memory_promotions": 0,
            "items": [],
            "summary": "No bounded MEMORY.md update proposal warranted candidate drafting.",
        }
    result = _persist_candidates(
        candidates=candidates,
        session_id=str(session_id or ""),
        run_id=run_id,
        source_mode="runtime_memory_md_proposal",
        actor="runtime:memory-md-update-bridge",
        status_reason="Candidate drafted from bounded MEMORY.md update proposal.",
    )
    return {
        **result,
        "summary": f"Drafted {result['created']} governed MEMORY.md candidates from bounded proposals.",
    }


def track_runtime_contract_candidates_from_self_authored_prompt_proposals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    candidates = _extract_candidates_from_self_authored_prompt_proposals()
    if not candidates:
        return {
            "created": 0,
            "updated": 0,
            "preference_updates": 0,
            "memory_promotions": 0,
            "items": [],
            "summary": "No bounded self-authored prompt proposal warranted candidate drafting.",
        }
    result = _persist_candidates(
        candidates=candidates,
        session_id=str(session_id or ""),
        run_id=run_id,
        source_mode="runtime_self_authored_prompt_proposal",
        actor="runtime:self-authored-prompt-bridge",
        status_reason="Candidate drafted from bounded self-authored prompt proposal.",
    )
    return {
        **result,
        "summary": f"Drafted {result['created']} governed prompt candidates from bounded proposals.",
    }


def track_runtime_contract_candidates_from_selfhood_proposals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    candidates = _extract_candidates_from_selfhood_proposals()
    if not candidates:
        return {
            "created": 0,
            "updated": 0,
            "preference_updates": 0,
            "memory_promotions": 0,
            "canonical_self_updates": 0,
            "items": [],
            "summary": "No bounded selfhood proposal warranted canonical-self candidate drafting.",
        }
    result = _persist_candidates(
        candidates=candidates,
        session_id=str(session_id or ""),
        run_id=run_id,
        source_mode="runtime_selfhood_proposal",
        actor="runtime:selfhood-bridge",
        status_reason="Drafted from bounded canonical-self proposal. Explicit user approval is required before any SOUL.md or IDENTITY.md apply.",
    )
    return {
        **result,
        "summary": f"Drafted {result['created']} governed canonical-self candidates from bounded selfhood proposals.",
    }


def auto_apply_safe_user_md_candidates_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    del session_id, run_id
    return auto_apply_safe_user_md_candidates()


def auto_apply_safe_memory_md_candidates_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    del session_id, run_id
    return auto_apply_safe_memory_md_candidates()


def _preference_candidates(message: str) -> list[dict[str, str]]:
    text = message.lower()
    explicit = any(
        phrase in text
        for phrase in (
            "jeg foretrækker",
            "i prefer",
            "jeg vil gerne have",
            "please remember i prefer",
        )
    )
    candidates: list[dict[str, str]] = []

    if explicit and ("dansk" in text or "danish" in text):
        candidates.append(
            _candidate(
                candidate_type="preference_update",
                target_file="USER.md",
                source_kind="user-explicit",
                canonical_key="user-preference:language:danish",
                summary="User prefers replies in Danish.",
                reason="Explicit durable language preference stated in chat.",
                evidence_summary=_quote(message),
                support_summary="Candidate only. No USER.md write has been applied.",
                proposed_value="- Language preference: replies in Danish by default.",
                write_section="## Durable Preferences",
                confidence="high",
            )
        )

    concise_markers = ("kort", "korte", "concise", "short", "kortfattet")
    technical_markers = ("technical summaries", "tekniske opsummeringer", "technical summary")
    if explicit and any(marker in text for marker in concise_markers):
        if any(marker in text for marker in technical_markers):
            candidates.append(
                _candidate(
                    candidate_type="preference_update",
                    target_file="USER.md",
                    source_kind="user-explicit",
                    canonical_key="user-preference:summaries:concise-technical",
                    summary="User prefers concise technical summaries.",
                    reason="Explicit durable summary-style preference stated in chat.",
                    evidence_summary=_quote(message),
                    support_summary="Candidate only. No USER.md write has been applied.",
                    proposed_value="- Summary preference: concise technical summaries.",
                    write_section="## Durable Preferences",
                    confidence="high",
                )
            )
        else:
            candidates.append(
                _candidate(
                    candidate_type="preference_update",
                    target_file="USER.md",
                    source_kind="user-explicit",
                    canonical_key="user-preference:reply-style:concise",
                    summary="User prefers concise replies.",
                    reason="Explicit durable response-style preference stated in chat.",
                    evidence_summary=_quote(message),
                    support_summary="Candidate only. No USER.md write has been applied.",
                    proposed_value="- Reply preference: concise answers by default.",
                    write_section="## Durable Preferences",
                    confidence="high",
                )
            )

    if "jeg arbejder mest sent om aftenen" in text or "i work mostly late in the evening" in text:
        candidates.append(
            _candidate(
                candidate_type="preference_update",
                target_file="USER.md",
                source_kind="user-explicit",
                canonical_key="user-profile:working-hours:late-evening",
                summary="User works mostly late in the evening.",
                reason="Explicit collaborator work-pattern statement may matter across sessions.",
                evidence_summary=_quote(message),
                support_summary="Candidate only. No USER.md write has been applied.",
                proposed_value="- Work pattern: mostly works late in the evening.",
                write_section="## Durable Preferences",
                confidence="medium",
            )
        )

    return _dedupe_candidates(candidates)


def _extract_candidates_from_user_md_update_proposals() -> list[dict[str, str]]:
    extracted: list[dict[str, str]] = []
    seen: set[str] = set()
    for proposal in build_runtime_user_md_update_proposal_surface(limit=12).get("items", []):
        if str(proposal.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        candidate = _candidate_from_user_md_update_proposal(proposal)
        if candidate is None:
            continue
        canonical_key = str(candidate.get("canonical_key") or "")
        if not canonical_key or canonical_key in seen:
            continue
        if _candidate_already_applied(candidate):
            continue
        seen.add(canonical_key)
        extracted.append(candidate)
    return extracted


def _extract_candidates_from_memory_md_update_proposals() -> list[dict[str, str]]:
    extracted: list[dict[str, str]] = []
    seen: set[str] = set()
    for proposal in build_runtime_memory_md_update_proposal_surface(limit=12).get("items", []):
        if str(proposal.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        candidate = _candidate_from_memory_md_update_proposal(proposal)
        if candidate is None:
            continue
        canonical_key = str(candidate.get("canonical_key") or "")
        if not canonical_key or canonical_key in seen:
            continue
        if _candidate_already_applied(candidate):
            continue
        seen.add(canonical_key)
        extracted.append(candidate)
    return extracted


def _extract_candidates_from_self_authored_prompt_proposals() -> list[dict[str, str]]:
    extracted: list[dict[str, str]] = []
    seen: set[str] = set()
    for proposal in build_runtime_self_authored_prompt_proposal_surface(limit=12).get("items", []):
        if str(proposal.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        candidate = _candidate_from_self_authored_prompt_proposal(proposal)
        if candidate is None:
            continue
        canonical_key = str(candidate.get("canonical_key") or "")
        if not canonical_key or canonical_key in seen:
            continue
        if _candidate_already_applied(candidate):
            continue
        seen.add(canonical_key)
        extracted.append(candidate)
    return extracted


def _extract_candidates_from_selfhood_proposals() -> list[dict[str, str]]:
    extracted: list[dict[str, str]] = []
    seen: set[str] = set()
    for proposal in build_runtime_selfhood_proposal_surface(limit=12).get("items", []):
        if str(proposal.get("status") or "") not in {"fresh", "active", "fading"}:
            continue
        candidate = _candidate_from_selfhood_proposal(proposal)
        if candidate is None:
            continue
        canonical_key = str(candidate.get("canonical_key") or "")
        if not canonical_key or canonical_key in seen:
            continue
        if _candidate_already_applied(candidate):
            continue
        seen.add(canonical_key)
        extracted.append(candidate)
    return extracted


def _memory_candidates(message: str) -> list[dict[str, str]]:
    text = message.lower()
    candidates: list[dict[str, str]] = []
    if ("husk at" in text or "remember that" in text) and "vi bygger jarvis sammen" in text:
        candidates.append(
            _candidate(
                candidate_type="memory_promotion",
                target_file="MEMORY.md",
                source_kind="user-explicit",
                canonical_key="workspace-memory:project-anchor:build-jarvis-together",
                summary="User and Jarvis are building Jarvis together.",
                reason="Explicit stable project anchor phrased as something to remember.",
                evidence_summary=_quote(message),
                support_summary="Candidate only. No MEMORY.md write has been applied.",
                proposed_value="- Project anchor: Jarvis and the user are building Jarvis together.",
                write_section="## Curated Memory",
                confidence="high",
            )
        )
    if "remember that" in text and "we are building jarvis together" in text:
        candidates.append(
            _candidate(
                candidate_type="memory_promotion",
                target_file="MEMORY.md",
                source_kind="user-explicit",
                canonical_key="workspace-memory:project-anchor:build-jarvis-together",
                summary="User and Jarvis are building Jarvis together.",
                reason="Explicit stable project anchor phrased as something to remember.",
                evidence_summary=_quote(message),
                support_summary="Candidate only. No MEMORY.md write has been applied.",
                proposed_value="- Project anchor: Jarvis and the user are building Jarvis together.",
                write_section="## Curated Memory",
                confidence="high",
            )
        )
    return _dedupe_candidates(candidates)


def _candidate_from_user_md_update_proposal(proposal: dict[str, object]) -> dict[str, str] | None:
    proposal_type = str(proposal.get("proposal_type") or "")
    mapping = {
        "preference-update": {
            "canonical_key": "user-preference:reply-style:plain-grounded-concise",
            "summary": "User appears to prefer plain, grounded, and concise replies.",
            "proposed_value": "- Reply preference: plain, grounded, and concise replies by default.",
            "write_section": "## Durable Preferences",
        },
        "workstyle-update": {
            "canonical_key": "user-workstyle:direction:stable-threading",
            "summary": "User appears to prefer keeping direction stable once a thread is active.",
            "proposed_value": "- Workstyle: prefers keeping direction stable once an active thread is underway.",
            "write_section": "## Durable Preferences",
        },
        "cadence-preference-update": {
            "canonical_key": "user-preference:review-style:challenge-before-settling",
            "summary": "User appears to prefer challenge or review before settling too quickly.",
            "proposed_value": "- Review preference: prefers challenge or review before settling too quickly.",
            "write_section": "## Durable Preferences",
        },
        "reminder-worthiness-update": {
            "canonical_key": "user-preference:reminders:assumption-caution",
            "summary": "User-facing reminders may be worth surfacing when assumptions or context look fragile.",
            "proposed_value": "- Reminder worthiness: assumption-fragility or unstable context may deserve explicit reminders.",
            "write_section": "## Durable Preferences",
        },
    }
    candidate_map = mapping.get(proposal_type)
    if candidate_map is None:
        return None
    proposal_reason = str(proposal.get("proposal_reason") or proposal.get("summary") or "").strip()
    source_anchor = str(proposal.get("source_anchor") or "").strip()
    support_summary = " | ".join(
        _unique_nonempty(
            [
                str(proposal.get("support_summary") or ""),
                source_anchor,
                "Candidate only. No USER.md write has been applied.",
            ]
        )[:4]
    )
    return {
        "candidate_type": "preference_update",
        "target_file": "USER.md",
        "source_kind": "runtime-derived-support",
        "canonical_key": str(candidate_map["canonical_key"]),
        "summary": str(candidate_map["summary"]),
        "reason": proposal_reason or "Bounded USER.md proposal now warrants governed candidate drafting.",
        "evidence_summary": " | ".join(
            _unique_nonempty(
                [
                    str(proposal.get("evidence_summary") or ""),
                    proposal_reason,
                ]
            )[:3]
        ),
        "support_summary": support_summary,
        "proposed_value": str(candidate_map["proposed_value"]),
        "write_section": str(candidate_map["write_section"]),
        "confidence": str(proposal.get("proposal_confidence") or proposal.get("confidence") or "low"),
        "evidence_class": "runtime_support_only",
        "support_count": max(int(proposal.get("support_count") or 1), 1),
        "session_count": max(int(proposal.get("session_count") or 1), 1),
    }


def _candidate_from_memory_md_update_proposal(proposal: dict[str, object]) -> dict[str, str] | None:
    proposal_type = str(proposal.get("proposal_type") or "")
    memory_kind = str(proposal.get("memory_kind") or "").strip()
    source_anchor = str(proposal.get("source_anchor") or "").strip()
    domain = _memory_proposal_domain(str(proposal.get("canonical_key") or ""))
    mapping = {
        "open-followup-update": {
            "canonical_key": f"workspace-memory:open-followup:{domain or 'carried-context'}",
            "summary": "A bounded open follow-up may be worth carrying into MEMORY.md.",
            "write_section": "## Curated Memory",
        },
        "carry-forward-thread-update": {
            "canonical_key": f"workspace-memory:carry-forward-thread:{domain or 'carried-context'}",
            "summary": "A bounded carry-forward thread may be worth carrying into MEMORY.md.",
            "write_section": "## Curated Memory",
        },
        "stable-context-update": {
            "canonical_key": f"workspace-memory:stable-context:{domain or 'carried-context'}",
            "summary": "A bounded stable context may be worth carrying into MEMORY.md.",
            "write_section": "## Curated Memory",
        },
        "remembered-fact-update": {
            "canonical_key": f"workspace-memory:remembered-fact:{domain or 'remembered-fact'}",
            "summary": "A bounded remembered fact may be worth carrying into MEMORY.md.",
            "write_section": "## Curated Memory",
        },
    }
    candidate_map = mapping.get(proposal_type)
    if candidate_map is None:
        return None
    proposal_reason = str(proposal.get("proposal_reason") or proposal.get("summary") or "").strip()
    proposed_update = str(proposal.get("proposed_update") or "").strip()
    support_summary = " | ".join(
        _unique_nonempty(
            [
                str(proposal.get("support_summary") or ""),
                source_anchor,
                f"memory-kind:{memory_kind}" if memory_kind else "",
                "Candidate only. No MEMORY.md write has been applied.",
            ]
        )[:4]
    )
    return {
        "candidate_type": "memory_promotion",
        "target_file": "MEMORY.md",
        "source_kind": "runtime-derived-support",
        "canonical_key": str(candidate_map["canonical_key"]),
        "summary": str(candidate_map["summary"]),
        "reason": proposal_reason or "Bounded MEMORY.md proposal now warrants governed candidate drafting.",
        "evidence_summary": " | ".join(
            _unique_nonempty(
                [
                    str(proposal.get("evidence_summary") or ""),
                    proposal_reason,
                ]
            )[:3]
        ),
        "support_summary": support_summary,
        "proposed_value": f"- {proposed_update}" if proposed_update and not proposed_update.startswith("- ") else proposed_update,
        "write_section": str(candidate_map["write_section"]),
        "confidence": str(proposal.get("proposal_confidence") or proposal.get("confidence") or "low"),
        "evidence_class": "runtime_support_only",
        "support_count": max(int(proposal.get("support_count") or 1), 1),
        "session_count": max(int(proposal.get("session_count") or 1), 1),
    }


def _candidate_from_self_authored_prompt_proposal(proposal: dict[str, object]) -> dict[str, str] | None:
    proposal_type = str(proposal.get("proposal_type") or "")
    mapping = {
        "communication-nudge": {
            "canonical_key": "prompt-feedback:communication-style:plain-grounded-calibration",
            "summary": "Prompt framing may need a small communication-style nudge.",
            "proposed_value": "- Communication nudge: keep replies plain, grounded, and slightly more self-calibrating.",
        },
        "focus-nudge": {
            "canonical_key": "prompt-feedback:direction-framing:stable-threading",
            "summary": "Prompt framing may need a small direction-framing nudge.",
            "proposed_value": "- Direction framing nudge: keep future framing pointed at the carried direction instead of reopening scope.",
        },
        "challenge-nudge": {
            "canonical_key": "prompt-feedback:challenge-posture:review-before-settling",
            "summary": "Prompt framing may need a small challenge-posture nudge.",
            "proposed_value": "- Challenge posture nudge: carry a small internal challenge before settling on the current thread.",
        },
        "world-caution-nudge": {
            "canonical_key": "prompt-feedback:world-caution:fragile-context-marker",
            "summary": "Prompt framing may need a small world-caution nudge.",
            "proposed_value": "- World caution nudge: add a small caution marker when world interpretation still looks unstable.",
        },
    }
    candidate_map = mapping.get(proposal_type)
    if candidate_map is None:
        return None
    proposal_reason = str(proposal.get("proposal_reason") or proposal.get("summary") or "").strip()
    influence_anchor = str(proposal.get("influence_anchor") or "").strip()
    support_summary = " | ".join(
        _unique_nonempty(
            [
                str(proposal.get("support_summary") or ""),
                influence_anchor,
                "Candidate only. No prompt mutation has been applied.",
            ]
        )[:4]
    )
    return {
        "candidate_type": "prompt_feedback_update",
        "target_file": "runtime/RUNTIME_FEEDBACK.md",
        "source_kind": "runtime-derived-support",
        "canonical_key": str(candidate_map["canonical_key"]),
        "summary": str(candidate_map["summary"]),
        "reason": proposal_reason or "Bounded prompt proposal now warrants governed candidate drafting.",
        "evidence_summary": " | ".join(
            _unique_nonempty(
                [
                    str(proposal.get("evidence_summary") or ""),
                    proposal_reason,
                ]
            )[:3]
        ),
        "support_summary": support_summary,
        "proposed_value": str(candidate_map["proposed_value"]),
        "write_section": "## Prompt Framing Drafts",
        "confidence": str(proposal.get("proposal_confidence") or proposal.get("confidence") or "low"),
        "evidence_class": "runtime_support_only",
        "support_count": max(int(proposal.get("support_count") or 1), 1),
        "session_count": max(int(proposal.get("session_count") or 1), 1),
    }


def _candidate_from_selfhood_proposal(proposal: dict[str, object]) -> dict[str, str] | None:
    proposal_type = str(proposal.get("proposal_type") or "")
    target_file = str(proposal.get("selfhood_target") or "").strip()
    domain = str(proposal.get("domain") or "").strip()
    proposed_shift = str(proposal.get("proposed_shift") or "").strip()
    source_anchor = str(proposal.get("source_anchor") or "").strip()
    if target_file == "SOUL.md":
        candidate_type = "soul_update"
        canonical_key = f"soul-self:{proposal_type}:{domain or 'canonical-self'}"
        summary = f"Canonical SOUL draft: {proposal_type}"
        write_section = "## Proposed Canonical Self Shifts"
    elif target_file == "IDENTITY.md":
        candidate_type = "identity_update"
        canonical_key = f"identity-self:{proposal_type}:{domain or 'canonical-self'}"
        summary = f"Canonical IDENTITY draft: {proposal_type}"
        write_section = "## Proposed Canonical Self Shifts"
    else:
        return None
    proposal_reason = str(proposal.get("proposal_reason") or proposal.get("summary") or "").strip()
    support_summary = " | ".join(
        _unique_nonempty(
            [
                str(proposal.get("support_summary") or ""),
                source_anchor,
                "Draft only. Explicit user approval is required before any SOUL.md or IDENTITY.md write.",
            ]
        )[:4]
    )
    return {
        "candidate_type": candidate_type,
        "target_file": target_file,
        "source_kind": "runtime-derived-support",
        "canonical_key": canonical_key,
        "summary": summary,
        "reason": proposal_reason or "Bounded canonical-self proposal now warrants governed candidate drafting.",
        "evidence_summary": " | ".join(
            _unique_nonempty(
                [
                    str(proposal.get("evidence_summary") or ""),
                    proposal_reason,
                ]
            )[:3]
        ),
        "support_summary": support_summary,
        "proposed_value": proposed_shift,
        "write_section": write_section,
        "confidence": str(proposal.get("proposal_confidence") or proposal.get("confidence") or "low"),
        "evidence_class": "runtime_support_only",
        "support_count": max(int(proposal.get("support_count") or 1), 1),
        "session_count": max(int(proposal.get("session_count") or 1), 1),
    }


def _extract_candidates_from_messages(
    messages: list[str],
    *,
    session_id: str,
) -> list[dict[str, str]]:
    extracted: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for message in messages:
        if not message:
            continue
        for candidate in [*_preference_candidates(message), *_memory_candidates(message)]:
            key = (candidate["candidate_type"], candidate["canonical_key"])
            if key in seen:
                continue
            enriched = _enrich_candidate_evidence(candidate, session_id=session_id)
            if _candidate_already_applied(enriched):
                continue
            seen.add(key)
            extracted.append(enriched)
    return extracted


def _persist_candidates(
    *,
    candidates: list[dict[str, str]],
    session_id: str,
    run_id: str,
    source_mode: str,
    actor: str,
    status_reason: str,
) -> dict[str, object]:
    if not candidates:
        return {
            "created": 0,
            "preference_updates": 0,
            "memory_promotions": 0,
            "canonical_self_updates": 0,
            "items": [],
        }

    persisted: list[dict[str, object]] = []
    preference_count = 0
    memory_count = 0
    canonical_self_count = 0
    now = _now_iso()
    for candidate in candidates:
        persisted_candidate = upsert_runtime_contract_candidate(
            candidate_id=f"candidate-{uuid4().hex}",
            candidate_type=str(candidate["candidate_type"]),
            target_file=str(candidate["target_file"]),
            status="proposed",
            source_kind=str(candidate["source_kind"]),
            source_mode=source_mode,
            actor=actor,
            session_id=session_id,
            run_id=run_id,
            canonical_key=str(candidate["canonical_key"]),
            summary=str(candidate["summary"]),
            reason=str(candidate["reason"]),
            evidence_summary=str(candidate["evidence_summary"]),
            support_summary=str(candidate["support_summary"]),
            confidence=str(candidate["confidence"]),
            evidence_class=str(candidate["evidence_class"]),
            support_count=int(candidate["support_count"]),
            session_count=int(candidate["session_count"]),
            created_at=now,
            updated_at=now,
            status_reason=status_reason,
            proposed_value=str(candidate.get("proposed_value") or ""),
            write_section=str(candidate.get("write_section") or ""),
        )
        if not bool(persisted_candidate.get("was_created")) and not bool(persisted_candidate.get("was_updated")):
            continue
        persisted.append(persisted_candidate)
        if persisted_candidate["candidate_type"] == "preference_update":
            preference_count += 1
        if persisted_candidate["candidate_type"] == "memory_promotion":
            memory_count += 1
        if persisted_candidate["candidate_type"] in {"soul_update", "identity_update"}:
            canonical_self_count += 1
        event_bus.publish(
            "runtime.contract_candidate_proposed",
            {
                "candidate_id": persisted_candidate["candidate_id"],
                "candidate_type": persisted_candidate["candidate_type"],
                "target_file": persisted_candidate["target_file"],
                "status": persisted_candidate["status"],
                "session_id": persisted_candidate["session_id"],
                "run_id": persisted_candidate["run_id"],
                "summary": persisted_candidate["summary"],
                "source_mode": source_mode,
                "evidence_class": persisted_candidate.get("evidence_class") or "",
                "merge_state": persisted_candidate.get("merge_state") or "",
            },
        )

    return {
        "created": sum(1 for item in persisted if item.get("was_created")),
        "updated": sum(1 for item in persisted if item.get("was_updated") and not item.get("was_created")),
        "preference_updates": preference_count,
        "memory_promotions": memory_count,
        "canonical_self_updates": canonical_self_count,
        "items": persisted,
    }


def _candidate_already_applied(candidate: dict[str, str]) -> bool:
    matches = list_runtime_contract_candidates(
        candidate_type=str(candidate["candidate_type"]),
        target_file=str(candidate["target_file"]),
        limit=20,
    )
    canonical_key = str(candidate["canonical_key"])
    for item in matches:
        if str(item.get("canonical_key") or "") != canonical_key:
            continue
        if str(item.get("status") or "") == "applied":
            return True
    return False


def _memory_proposal_domain(canonical_key: str) -> str:
    parts = [part for part in canonical_key.split(":") if part]
    return parts[-1] if parts else ""


def _enrich_candidate_evidence(
    candidate: dict[str, str],
    *,
    session_id: str,
) -> dict[str, str | int]:
    history = _candidate_history(candidate, session_id=session_id)
    total_occurrences = history["total_occurrences"]
    distinct_sessions = history["distinct_sessions"]
    current_session_occurrences = history["current_session_occurrences"]
    evidence_class = "explicit_user_statement"
    confidence = str(candidate["confidence"])
    source_kind = str(candidate["source_kind"])
    if distinct_sessions >= 2 and total_occurrences >= 2:
        evidence_class = "repeated_cross_session"
        confidence = _stronger_confidence(confidence, "high")
    elif current_session_occurrences >= 2 or total_occurrences >= 2:
        evidence_class = "single_session_pattern"
        confidence = _stronger_confidence(confidence, "high" if source_kind == "user-explicit" else "medium")
        if source_kind != "user-explicit":
            source_kind = "single-session-pattern"

    evidence_bits = [str(candidate["evidence_summary"]).strip()]
    evidence_bits.extend(history["samples"][:2])
    support_parts = [_evidence_class_label(evidence_class)]
    if distinct_sessions >= 2:
        support_parts.append(f"seen in {distinct_sessions} sessions")
    elif current_session_occurrences >= 2:
        support_parts.append(f"seen {current_session_occurrences} times in this session")
    else:
        support_parts.append("single durable signal so far")

    reason = str(candidate["reason"]).strip()
    if evidence_class == "repeated_cross_session":
        reason = f"{reason} Repeated across sessions."
    elif evidence_class == "single_session_pattern" and total_occurrences >= 2:
        reason = f"{reason} Repeated in recent evidence."

    return {
        **candidate,
        "source_kind": source_kind,
        "reason": reason,
        "evidence_summary": " | ".join(_unique_nonempty(evidence_bits)[:3]),
        "support_summary": " | ".join(support_parts),
        "confidence": confidence,
        "evidence_class": evidence_class,
        "support_count": max(total_occurrences, 1),
        "session_count": max(distinct_sessions, 1),
    }


def _candidate_history(candidate: dict[str, str], *, session_id: str) -> dict[str, object]:
    samples: list[str] = []
    distinct_sessions: set[str] = set()
    total_occurrences = 0
    current_session_occurrences = 0
    for message in _recent_user_message_history(limit_sessions=6, per_session_limit=10):
        if not _message_matches_candidate(
            canonical_key=str(candidate["canonical_key"]),
            message=message["content"],
        ):
            continue
        total_occurrences += 1
        distinct_sessions.add(message["session_id"])
        if message["session_id"] == session_id:
            current_session_occurrences += 1
        samples.append(_quote(message["content"]))
    return {
        "samples": _unique_nonempty(samples),
        "total_occurrences": total_occurrences,
        "distinct_sessions": len(distinct_sessions),
        "current_session_occurrences": current_session_occurrences,
    }


def _recent_user_message_history(*, limit_sessions: int, per_session_limit: int) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for summary in list_chat_sessions()[: max(limit_sessions, 1)]:
        session_id = str(summary.get("id") or "").strip()
        if not session_id:
            continue
        session = get_chat_session(session_id)
        if session is None:
            continue
        user_messages = [
            " ".join(str(message.get("content") or "").split()).strip()
            for message in reversed(session.get("messages") or [])
            if str(message.get("role") or "") == "user"
        ][: max(per_session_limit, 1)]
        for content in user_messages:
            if not content:
                continue
            items.append({"session_id": session_id, "content": content})
    return items


def _message_matches_candidate(*, canonical_key: str, message: str) -> bool:
    text = str(message or "").lower()
    if canonical_key == "user-preference:language:danish":
        return any(marker in text for marker in ("jeg foretrækker", "i prefer", "jeg vil gerne have")) and (
            "dansk" in text or "danish" in text
        )
    if canonical_key == "user-preference:reply-style:concise":
        return any(marker in text for marker in ("jeg foretrækker", "i prefer", "jeg vil gerne have")) and any(
            marker in text for marker in ("kort", "concise", "short", "kortfattet")
        )
    if canonical_key == "user-preference:summaries:concise-technical":
        return any(marker in text for marker in ("jeg foretrækker", "i prefer", "please remember i prefer")) and any(
            marker in text for marker in ("technical summaries", "tekniske opsummeringer", "technical summary")
        )
    if canonical_key == "user-profile:working-hours:late-evening":
        return "jeg arbejder mest sent om aftenen" in text or "i work mostly late in the evening" in text
    if canonical_key == "workspace-memory:project-anchor:build-jarvis-together":
        return (
            ("husk at" in text and "vi bygger jarvis sammen" in text)
            or ("remember that" in text and "we are building jarvis together" in text)
        )
    return False


def _evidence_class_label(value: str) -> str:
    mapping = {
        "weak_signal": "weak signal",
        "runtime_support_only": "runtime support only",
        "single_session_pattern": "repeated in one session",
        "explicit_user_statement": "explicit user statement",
        "repeated_cross_session": "repeated across sessions",
    }
    return mapping.get(str(value or ""), "bounded evidence")


def _stronger_confidence(current: str, proposed: str) -> str:
    if _CONFIDENCE_RANKS.get(str(proposed or ""), 0) >= _CONFIDENCE_RANKS.get(str(current or ""), 0):
        return str(proposed or "")
    return str(current or "")


def _unique_nonempty(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = " ".join(str(value or "").split()).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _candidate(
    *,
    candidate_type: str,
    target_file: str,
    source_kind: str,
    canonical_key: str,
    summary: str,
    reason: str,
    evidence_summary: str,
    support_summary: str,
    proposed_value: str,
    write_section: str,
    confidence: str,
) -> dict[str, str]:
    return {
        "candidate_type": candidate_type,
        "target_file": target_file,
        "source_kind": source_kind,
        "canonical_key": canonical_key,
        "summary": summary,
        "reason": reason,
        "evidence_summary": evidence_summary,
        "support_summary": support_summary,
        "proposed_value": proposed_value,
        "write_section": write_section,
        "confidence": confidence,
        "evidence_class": "",
        "support_count": 1,
        "session_count": 1,
    }


def _dedupe_candidates(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in candidates:
        key = (item["candidate_type"], item["canonical_key"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _quote(message: str, *, limit: int = 140) -> str:
    normalized = " ".join(str(message or "").split()).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
