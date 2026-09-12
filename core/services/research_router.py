"""Conservative and explainable inline/orchestrated research routing."""

from __future__ import annotations

import re

from core.services.research_contract import ResearchDecision, ResearchPolicy

_BREADTH = re.compile(r"\b(sammenlign|compare|versus|vs\.?|leverandører|vendors|alternativer|options)\b", re.I)
_MULTI_ENTITY = re.compile(r"\b(tre|fire|fem|seks|3|4|5|6)\b", re.I)
_MULTI_FACET = re.compile(r"\b(pris|price|sikkerhed|security|drift|operations|ydelse|performance|funktioner|features)\b", re.I)
_REPORT = re.compile(r"\b(grundig|omfattende|deep research|rapport|report|landscape|due diligence)\b", re.I)

# Fase C2 (13/9-2026): indsats efter signalstyrke.
#
# Anthropic målte at token-forbrug alene forklarer 80% af variansen i
# resultatkvalitet — men også at indsats SKAL skaleres: et simpelt spørgsmål må
# ikke få halvtreds søgninger. Tabellen er derfor eksplicit og forklarlig frem
# for en formel; hver række kan læses højt.
#
# Kolonner: (workers, tasks, source_target, worker_max_turns, worker_token_budget)
#
# Workers holdes ≤ tasks: `_plan` laver `min(max_tasks, len(facets))` tracks, så
# flere workers end tracks er bare ledige hænder. Tabellen matcher derfor
# paralleliteten til den faktiske plan i stedet for at sætte den fast.
#
# Token-budgetterne er målt, ikke gættet: researcher brænder i snit 14.561
# tokens (maks 95.882 over 138 kørsler), critic i snit 7.382. Loftet skal give
# luft til det typiske arbejde og samtidig kappe halen.
_EFFORT_BY_SIGNALS: dict[int, tuple[int, int, int, int, int]] = {
    2: (2, 3, 4, 6, 25_000),
    3: (3, 5, 5, 8, 30_000),
    4: (3, 6, 6, 12, 40_000),
}


def _effort(independent: int) -> tuple[int, int, int, int, int]:
    """Indsatsen for N uafhængige signaler — klippet til tabellens rækker."""
    return _EFFORT_BY_SIGNALS[max(2, min(4, independent))]


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
        workers, tasks, sources, turns, budget = _effort(independent)
        return ResearchDecision(
            tier="orchestrated",
            signals=tuple(signals),
            max_workers=max(1, min(workers, policy.max_workers)),
            max_tasks=max(2, min(tasks, policy.max_tasks)),
            # Flere uafhængige signaler → flere kald tilladt. Loftet er stadig
            # policy'ens, så kalderen altid kan stramme den.
            max_tool_calls=max(1, min(policy.max_tool_calls, 8 * independent)),
            # wall_time er maskinbeskyttelse, ikke en indsats-knap — den står.
            wall_time_seconds=max(30, policy.wall_time_seconds),
            source_target=max(2, min(sources, policy.source_target)),
            worker_max_turns=max(2, turns),
            worker_token_budget=max(0, budget),
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
