"""Deterministic, inspectable quality gates for research synthesis."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from core.services.research_contract import ResearchSource


@dataclass(frozen=True)
class ResearchQualityResult:
    passed: bool
    gates: dict[str, bool]
    failures: tuple[str, ...]


def evaluate_research_report(
    report: str,
    sources: list[ResearchSource],
    requested_facets: list[str],
    *,
    contradictions: list[str] | None = None,
    requires_freshness: bool = False,
    tool_calls: int | None = None,
    max_tool_calls: int | None = None,
) -> ResearchQualityResult:
    text = str(report or "")
    citations = [int(value) for value in re.findall(r"\[(\d+)\]", text)]
    citation_validity = bool(sources) and bool(citations) and all(1 <= n <= len(sources) for n in citations)
    lowered = text.lower()
    coverage = all(str(facet).lower() in lowered for facet in requested_facets)
    source_quality = all(bool(source.canonical_url) for source in sources) and bool(sources)
    conflicts = contradictions or []
    calibrated_words = ("uncertain", "usikker", "conflict", "uenig", "cannot verify", "kunne ikke verificere")
    calibration = not conflicts or any(word in lowered for word in calibrated_words)
    contradiction_handling = not conflicts or calibration
    dated_sources = []
    for source in sources:
        if not source.published_at:
            continue
        try:
            dated_sources.append(datetime.fromisoformat(source.published_at.replace("Z", "+00:00")))
        except ValueError:
            continue
    freshness = not requires_freshness or any(
        (datetime.now(UTC) - value.astimezone(UTC)).days <= 365 for value in dated_sources
    )
    tool_efficiency = tool_calls is None or max_tool_calls is None or tool_calls <= max_tool_calls
    gates = {
        "citation_validity": citation_validity,
        "coverage": coverage,
        "source_quality": source_quality,
        "contradiction_handling": contradiction_handling,
        "freshness": freshness,
        "calibration": calibration,
        "tool_efficiency": tool_efficiency,
    }
    failures = tuple(name for name, passed in gates.items() if not passed)
    return ResearchQualityResult(not failures, gates, failures)
