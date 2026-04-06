"""Adaptive attention economy — bounded context budgeting for prompt assembly.

Provides budget profiles for different prompt paths (visible compact, visible
full, heartbeat) and a budget-aware section selector that chooses what context
to include within char/item constraints.

Design constraints:
- Deterministic selection, no randomness
- All omissions are traced and observable
- No external action, no fake claims
- Compact output suitable for lean prompt paths
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Budget profiles
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SectionBudget:
    """Budget for a single prompt section."""
    max_chars: int = 300
    max_items: int = 3
    must_include: bool = False  # always include even if empty
    priority: int = 5  # 1 = highest priority, 10 = lowest


@dataclass(frozen=True, slots=True)
class AttentionBudget:
    """Complete attention budget for a prompt assembly path."""
    profile: str
    total_char_target: int
    cognitive_frame: SectionBudget
    private_brain: SectionBudget
    self_knowledge: SectionBudget
    self_report: SectionBudget
    support_signals: SectionBudget
    inner_visible_bridge: SectionBudget
    continuity: SectionBudget
    liveness: SectionBudget
    capability_truth: SectionBudget
    cognitive_state: SectionBudget = SectionBudget(max_chars=0, max_items=0, must_include=False, priority=9)


# Pre-defined budget profiles

BUDGET_VISIBLE_COMPACT = AttentionBudget(
    profile="visible_compact",
    total_char_target=1850,
    cognitive_frame=SectionBudget(max_chars=180, max_items=2, must_include=True, priority=1),
    private_brain=SectionBudget(max_chars=0, max_items=0, must_include=False, priority=9),
    self_knowledge=SectionBudget(max_chars=0, max_items=0, must_include=False, priority=9),
    self_report=SectionBudget(max_chars=400, max_items=4, must_include=False, priority=3),
    support_signals=SectionBudget(max_chars=200, max_items=2, must_include=False, priority=6),
    inner_visible_bridge=SectionBudget(max_chars=120, max_items=1, must_include=False, priority=4),
    continuity=SectionBudget(max_chars=220, max_items=2, must_include=False, priority=5),
    liveness=SectionBudget(max_chars=0, max_items=0, must_include=False, priority=9),
    capability_truth=SectionBudget(max_chars=700, max_items=8, must_include=True, priority=2),
    cognitive_state=SectionBudget(max_chars=250, max_items=3, must_include=False, priority=3),
)

BUDGET_VISIBLE_FULL = AttentionBudget(
    profile="visible_full",
    total_char_target=3500,
    cognitive_frame=SectionBudget(max_chars=500, max_items=4, must_include=True, priority=2),
    private_brain=SectionBudget(max_chars=0, max_items=0, must_include=False, priority=9),
    self_knowledge=SectionBudget(max_chars=0, max_items=0, must_include=False, priority=9),
    self_report=SectionBudget(max_chars=600, max_items=6, must_include=False, priority=3),
    support_signals=SectionBudget(max_chars=400, max_items=4, must_include=False, priority=5),
    inner_visible_bridge=SectionBudget(max_chars=200, max_items=2, must_include=False, priority=4),
    continuity=SectionBudget(max_chars=420, max_items=4, must_include=False, priority=6),
    liveness=SectionBudget(max_chars=0, max_items=0, must_include=False, priority=9),
    capability_truth=SectionBudget(max_chars=900, max_items=10, must_include=True, priority=1),
    cognitive_state=SectionBudget(max_chars=500, max_items=6, must_include=False, priority=3),
)

BUDGET_HEARTBEAT = AttentionBudget(
    profile="heartbeat",
    total_char_target=2800,
    cognitive_frame=SectionBudget(max_chars=500, max_items=4, must_include=True, priority=2),
    private_brain=SectionBudget(max_chars=400, max_items=4, must_include=False, priority=3),
    self_knowledge=SectionBudget(max_chars=350, max_items=5, must_include=False, priority=4),
    self_report=SectionBudget(max_chars=0, max_items=0, must_include=False, priority=9),
    support_signals=SectionBudget(max_chars=0, max_items=0, must_include=False, priority=9),
    inner_visible_bridge=SectionBudget(max_chars=0, max_items=0, must_include=False, priority=9),
    continuity=SectionBudget(max_chars=300, max_items=3, must_include=False, priority=5),
    liveness=SectionBudget(max_chars=300, max_items=3, must_include=False, priority=5),
    capability_truth=SectionBudget(max_chars=300, max_items=4, must_include=True, priority=1),
    cognitive_state=SectionBudget(max_chars=400, max_items=5, must_include=False, priority=3),
)

_PROFILES: dict[str, AttentionBudget] = {
    "visible_compact": BUDGET_VISIBLE_COMPACT,
    "visible_full": BUDGET_VISIBLE_FULL,
    "heartbeat": BUDGET_HEARTBEAT,
}


def get_attention_budget(profile: str) -> AttentionBudget:
    """Get a named attention budget profile."""
    return _PROFILES.get(profile, BUDGET_VISIBLE_FULL)


# ---------------------------------------------------------------------------
# Budget-aware section selection
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SectionResult:
    """Result of attempting to include a section under budget."""
    name: str
    included: bool
    chars_used: int = 0
    items_used: int = 0
    trimmed: bool = False
    omission_reason: str = ""


@dataclass(slots=True)
class AttentionTrace:
    """Observable trace of what was included/omitted and why."""
    profile: str = ""
    total_char_target: int = 0
    total_chars_used: int = 0
    sections: list[SectionResult] = field(default_factory=list)
    # Authority tracking
    authority_mode: str = "budgeted"  # "budgeted" or "fallback_passthrough"
    fallback_reason: str = ""  # machine-readable reason or empty
    # Overshoot tracking (must-include sections can exceed total budget)
    budget_overshoot: bool = False
    overshoot_chars: int = 0

    @property
    def included_sections(self) -> list[str]:
        return [s.name for s in self.sections if s.included]

    @property
    def omitted_sections(self) -> list[str]:
        return [s.name for s in self.sections if not s.included]

    @property
    def trimmed_sections(self) -> list[str]:
        return [s.name for s in self.sections if s.trimmed]

    def summary(self) -> dict[str, object]:
        return {
            "profile": self.profile,
            "authority_mode": self.authority_mode,
            "fallback_reason": self.fallback_reason or None,
            "total_char_target": self.total_char_target,
            "total_chars_used": self.total_chars_used,
            "char_utilization": round(self.total_chars_used / max(self.total_char_target, 1), 2),
            "budget_overshoot": self.budget_overshoot,
            "overshoot_chars": self.overshoot_chars,
            "included": self.included_sections,
            "omitted": self.omitted_sections,
            "trimmed": self.trimmed_sections,
            "section_details": [
                {
                    "name": s.name,
                    "included": s.included,
                    "chars": s.chars_used,
                    "items": s.items_used,
                    "trimmed": s.trimmed,
                    "reason": s.omission_reason,
                }
                for s in self.sections
            ],
        }


def apply_section_budget(
    *,
    name: str,
    content: str | None,
    budget: SectionBudget,
) -> tuple[str | None, SectionResult]:
    """Apply a section budget to content.

    Returns (possibly trimmed content or None, result trace).
    """
    if content is None or not content.strip():
        if budget.must_include:
            return None, SectionResult(
                name=name,
                included=False,
                omission_reason="no-content-available (must-include section)",
            )
        return None, SectionResult(
            name=name,
            included=False,
            omission_reason="no-content-available",
        )

    if budget.max_chars <= 0:
        return None, SectionResult(
            name=name,
            included=False,
            omission_reason=f"zero-budget (priority={budget.priority})",
        )

    content_stripped = content.strip()
    chars = len(content_stripped)

    if chars <= budget.max_chars:
        return content_stripped, SectionResult(
            name=name,
            included=True,
            chars_used=chars,
        )

    # Trim to budget
    trimmed = content_stripped[: budget.max_chars]
    # Try to cut at last newline to avoid mid-line truncation
    last_nl = trimmed.rfind("\n")
    if last_nl > budget.max_chars // 2:
        trimmed = trimmed[:last_nl]

    return trimmed, SectionResult(
        name=name,
        included=True,
        chars_used=len(trimmed),
        trimmed=True,
        omission_reason=f"trimmed from {chars} to {len(trimmed)} chars",
    )


# ---------------------------------------------------------------------------
# Micro cognitive frame for compact paths
# ---------------------------------------------------------------------------

def build_micro_cognitive_frame() -> str | None:
    """Build a ~150 char micro cognitive frame for compact visible prompts.

    This ensures compact prompts still carry a minimal mental context:
    - current mode
    - top salient item
    - top constraint/gate if active
    """
    try:
        from apps.api.jarvis_api.services.runtime_cognitive_conductor import (
            build_cognitive_frame,
        )
        frame = build_cognitive_frame()
    except Exception:
        return None

    mode = frame.get("mode", {})
    mode_name = mode.get("mode", "watch")
    salient = frame.get("salient_items") or []
    continuity_pressure = str(frame.get("continuity_pressure") or "low")
    constraints = frame.get("active_constraints") or []

    parts: list[str] = []
    parts.append(f"[mind:{mode_name}]")

    if salient:
        top = salient[0]
        summary = str(top.get("summary") or "")[:60]
        parts.append(f"salient: {summary}")

    if continuity_pressure in {"medium", "high"}:
        parts.append(f"carry:{continuity_pressure}")

    if constraints:
        parts.append(f"constraint: {constraints[0][:40]}")

    result = " | ".join(parts)
    return result[:180] if result else None


# ---------------------------------------------------------------------------
# Budget-aware prompt section assembly
# ---------------------------------------------------------------------------

def select_sections_under_budget(
    *,
    budget: AttentionBudget,
    sections: dict[str, str | None],
) -> tuple[dict[str, str | None], AttentionTrace]:
    """Select and trim sections to fit within the attention budget.

    Args:
        budget: The attention budget profile to use.
        sections: Map of section_name -> content (None = not available).

    Returns:
        (selected_sections, attention_trace)
    """
    trace = AttentionTrace(
        profile=budget.profile,
        total_char_target=budget.total_char_target,
    )
    result: dict[str, str | None] = {}
    total_chars = 0

    # Map section names to their budgets
    section_budgets = {
        "cognitive_frame": budget.cognitive_frame,
        "private_brain": budget.private_brain,
        "self_knowledge": budget.self_knowledge,
        "self_report": budget.self_report,
        "support_signals": budget.support_signals,
        "inner_visible_bridge": budget.inner_visible_bridge,
        "continuity": budget.continuity,
        "liveness": budget.liveness,
        "capability_truth": budget.capability_truth,
        "cognitive_state": budget.cognitive_state,
    }

    # Sort by priority (lowest number = highest priority)
    sorted_names = sorted(
        section_budgets.keys(),
        key=lambda n: section_budgets[n].priority,
    )

    for name in sorted_names:
        sb = section_budgets[name]
        content = sections.get(name)

        # Check total budget
        if total_chars >= budget.total_char_target and not sb.must_include:
            trace.sections.append(SectionResult(
                name=name,
                included=False,
                omission_reason="total-budget-exhausted",
            ))
            result[name] = None
            continue

        remaining = budget.total_char_target - total_chars
        effective_max = min(sb.max_chars, remaining) if not sb.must_include else sb.max_chars

        effective_budget = SectionBudget(
            max_chars=effective_max,
            max_items=sb.max_items,
            must_include=sb.must_include,
            priority=sb.priority,
        )

        trimmed_content, section_result = apply_section_budget(
            name=name,
            content=content,
            budget=effective_budget,
        )

        trace.sections.append(section_result)
        result[name] = trimmed_content
        total_chars += section_result.chars_used

    trace.total_chars_used = total_chars
    if total_chars > budget.total_char_target:
        trace.budget_overshoot = True
        trace.overshoot_chars = total_chars - budget.total_char_target
    return result, trace
