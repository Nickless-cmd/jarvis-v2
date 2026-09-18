"""Stable identity carried across Cheap Lane attempts and fallbacks."""
from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import uuid4


@dataclass(frozen=True)
class CheapLaneTraceContext:
    correlation_id: str
    daemon: str = ""
    task_kind: str = "default"
    attempt: int = 1
    retry_parent_id: str = ""
    fallback_parent_id: str = ""

    @classmethod
    def create(
        cls,
        *,
        correlation_id: str = "",
        daemon: str = "",
        task_kind: str = "default",
        attempt: int = 1,
        retry_parent_id: str = "",
        fallback_parent_id: str = "",
    ) -> "CheapLaneTraceContext":
        return cls(
            correlation_id=(correlation_id or "").strip() or str(uuid4()),
            daemon=(daemon or "").strip(),
            task_kind=(task_kind or "default").strip().lower(),
            attempt=max(1, int(attempt)),
            retry_parent_id=(retry_parent_id or "").strip(),
            fallback_parent_id=(fallback_parent_id or "").strip(),
        )

    def next_fallback(self, parent_id: str) -> "CheapLaneTraceContext":
        return replace(
            self,
            attempt=self.attempt + 1,
            retry_parent_id="",
            fallback_parent_id=parent_id,
        )


def candidate_slot_id(candidate: dict[str, object]) -> str:
    explicit = str(candidate.get("slot_id") or "").strip()
    if explicit:
        return explicit
    provider = str(candidate.get("provider") or "").strip()
    model = str(candidate.get("model") or "").strip()
    profile = str(candidate.get("auth_profile") or "default").strip() or "default"
    return f"{provider}::{model}::{profile}"
