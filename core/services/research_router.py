"""Conservative and explainable inline/orchestrated research routing."""

from __future__ import annotations

import re

from core.services.research_contract import ResearchDecision, ResearchPolicy

_BREADTH = re.compile(r"\b(sammenlign|compare|versus|vs\.?|leverandører|vendors|alternativer|options)\b", re.I)
_MULTI_ENTITY = re.compile(r"\b(tre|fire|fem|seks|3|4|5|6)\b", re.I)
_MULTI_FACET = re.compile(r"\b(pris|price|sikkerhed|security|drift|operations|ydelse|performance|funktioner|features)\b", re.I)
_REPORT = re.compile(r"\b(grundig|omfattende|deep research|rapport|report|landscape|due diligence)\b", re.I)


def classify_research(
    message: str,
    *,
    attachment_count: int = 0,
    policy: ResearchPolicy | None = None,
) -> ResearchDecision:
    policy = policy or ResearchPolicy()
    text = " ".join(str(message or "").split())
    signals: list[str] = []
    if _BREADTH.search(text):
        signals.append("comparative_breadth")
    if _MULTI_ENTITY.search(text):
        signals.append("multiple_entities")
    facets = {match.group(0).lower() for match in _MULTI_FACET.finditer(text)}
    if len(facets) >= 2:
        signals.append("multiple_facets")
    if _REPORT.search(text):
        signals.append("high_depth_output")
    if attachment_count >= 3:
        signals.append("multiple_attachments")

    independent = sum(s in signals for s in (
        "comparative_breadth", "multiple_entities", "multiple_facets", "multiple_attachments",
    ))
    complex_signal = "high_depth_output" in signals or len(text) >= 280
    orchestrated = independent >= 2 and complex_signal
    if orchestrated:
        return ResearchDecision(
            tier="orchestrated",
            signals=tuple(signals),
            max_workers=max(1, min(3, policy.max_workers)),
            max_tasks=max(2, min(6, policy.max_tasks)),
            max_tool_calls=max(1, policy.max_tool_calls),
            wall_time_seconds=max(30, policy.wall_time_seconds),
            source_target=max(3, policy.source_target),
        )
    return ResearchDecision(
        tier="inline",
        signals=tuple(signals),
        max_workers=1,
        max_tasks=1,
        max_tool_calls=min(10, max(1, policy.max_tool_calls)),
        wall_time_seconds=min(240, max(30, policy.wall_time_seconds)),
        source_target=min(6, max(2, policy.source_target)),
    )
