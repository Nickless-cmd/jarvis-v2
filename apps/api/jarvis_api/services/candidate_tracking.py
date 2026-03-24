from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import upsert_runtime_contract_candidate


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

    candidates = [
        *_preference_candidates(normalized_message),
        *_memory_candidates(normalized_message),
    ]
    if not candidates:
        return {
            "created": 0,
            "preference_updates": 0,
            "memory_promotions": 0,
            "items": [],
        }

    persisted: list[dict[str, object]] = []
    preference_count = 0
    memory_count = 0
    now = _now_iso()
    for candidate in candidates:
        persisted_candidate = upsert_runtime_contract_candidate(
            candidate_id=f"candidate-{uuid4().hex}",
            candidate_type=str(candidate["candidate_type"]),
            target_file=str(candidate["target_file"]),
            status="proposed",
            source_kind=str(candidate["source_kind"]),
            source_mode="visible_chat",
            actor="runtime:visible-chat",
            session_id=str(session_id or ""),
            run_id=run_id,
            canonical_key=str(candidate["canonical_key"]),
            summary=str(candidate["summary"]),
            reason=str(candidate["reason"]),
            evidence_summary=str(candidate["evidence_summary"]),
            support_summary=str(candidate["support_summary"]),
            confidence=str(candidate["confidence"]),
            created_at=now,
            updated_at=now,
            status_reason="Candidate proposed from visible chat evidence.",
            proposed_value=str(candidate.get("proposed_value") or ""),
            write_section=str(candidate.get("write_section") or ""),
        )
        persisted.append(persisted_candidate)
        if persisted_candidate["candidate_type"] == "preference_update":
            preference_count += 1
        if persisted_candidate["candidate_type"] == "memory_promotion":
            memory_count += 1
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
            },
        )

    return {
        "created": len(persisted),
        "preference_updates": preference_count,
        "memory_promotions": memory_count,
        "items": persisted,
    }


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

    concise_markers = ("kort", "concise", "short", "kortfattet")
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
