from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ApprovalMode = Literal["none", "proposal_only", "visible_approval_required"]
ExecutionLane = Literal["heartbeat", "visible", "either"]


@dataclass(frozen=True, slots=True)
class RuntimeActionSpec:
    action_id: str
    title: str
    description: str
    lane: ExecutionLane
    approval_mode: ApprovalMode
    allowed_when_visible_active: bool
    allowed_when_idle: bool
    max_per_hour: int
    requires_capability: str | None = None


_ACTION_SPECS: tuple[RuntimeActionSpec, ...] = (
    RuntimeActionSpec(
        action_id="refresh_memory_context",
        title="Refresh Memory Context",
        description="Refresh the bounded operational memory snapshot before larger moves.",
        lane="heartbeat",
        approval_mode="none",
        allowed_when_visible_active=False,
        allowed_when_idle=True,
        max_per_hour=4,
    ),
    RuntimeActionSpec(
        action_id="follow_open_loop",
        title="Follow Open Loop",
        description="Inspect the highest-pressure open loop and produce a bounded next step.",
        lane="either",
        approval_mode="proposal_only",
        allowed_when_visible_active=True,
        allowed_when_idle=True,
        max_per_hour=6,
    ),
    RuntimeActionSpec(
        action_id="inspect_repo_context",
        title="Inspect Repo Context",
        description="Run a bounded repository inspection to clarify the next internal move.",
        lane="heartbeat",
        approval_mode="none",
        allowed_when_visible_active=False,
        allowed_when_idle=True,
        max_per_hour=4,
        requires_capability="project_grep",
    ),
    RuntimeActionSpec(
        action_id="review_recent_conversations",
        title="Review Recent Conversations",
        description="Read recent visible interactions and extract bounded carry-forward context.",
        lane="heartbeat",
        approval_mode="none",
        allowed_when_visible_active=False,
        allowed_when_idle=True,
        max_per_hour=3,
    ),
    RuntimeActionSpec(
        action_id="write_internal_work_note",
        title="Write Internal Work Note",
        description="Write a small internal note about what the runtime is carrying or noticing.",
        lane="heartbeat",
        approval_mode="none",
        allowed_when_visible_active=False,
        allowed_when_idle=True,
        max_per_hour=6,
    ),
    RuntimeActionSpec(
        action_id="bounded_self_check",
        title="Bounded Self Check",
        description="Pause and evaluate contradictions, gates, or approval pressure before acting.",
        lane="heartbeat",
        approval_mode="none",
        allowed_when_visible_active=True,
        allowed_when_idle=True,
        max_per_hour=6,
    ),
    RuntimeActionSpec(
        action_id="propose_next_user_step",
        title="Propose Next User Step",
        description="Offer a bounded next-step proposal to the visible lane instead of acting silently.",
        lane="visible",
        approval_mode="proposal_only",
        allowed_when_visible_active=True,
        allowed_when_idle=False,
        max_per_hour=8,
    ),
    RuntimeActionSpec(
        action_id="promote_initiative_to_visible_lane",
        title="Promote Initiative To Visible Lane",
        description="Surface a queued initiative into the visible lane as a concrete suggested action.",
        lane="either",
        approval_mode="proposal_only",
        allowed_when_visible_active=True,
        allowed_when_idle=True,
        max_per_hour=6,
    ),
)


def list_runtime_action_specs() -> list[RuntimeActionSpec]:
    return list(_ACTION_SPECS)


def get_runtime_action_spec(action_id: str) -> RuntimeActionSpec | None:
    normalized = str(action_id or "").strip()
    if not normalized:
        return None
    for spec in _ACTION_SPECS:
        if spec.action_id == normalized:
            return spec
    return None
