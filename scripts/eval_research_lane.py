#!/usr/bin/env python3
"""Offline deterministic smoke evaluation for research routing and gates."""

from __future__ import annotations

import json
from pathlib import Path

from core.services.research_contract import ResearchPolicy, normalize_source
from core.services.research_quality import evaluate_research_report
from core.services.research_router import classify_research

DEFAULT_CASES = Path(__file__).parents[1] / "tests/fixtures/research_eval_cases.json"


def evaluate_cases(path: Path = DEFAULT_CASES) -> dict:
    cases = json.loads(path.read_text(encoding="utf-8"))
    failures = []
    source = normalize_source({"url": "https://example.com/source", "title": "Primary"})
    for case in cases:
        decision = classify_research(case["query"], policy=ResearchPolicy())
        report = ". ".join(str(facet) for facet in case["facets"]) + " [1]"
        quality = evaluate_research_report(report, [source], list(case["facets"]))
        if decision.tier != case["tier"] or not quality.passed:
            failures.append({
                "id": case["id"], "expected_tier": case["tier"],
                "actual_tier": decision.tier, "quality_failures": quality.failures,
            })
    return {"cases": len(cases), "passed": len(cases) - len(failures), "failures": failures}


if __name__ == "__main__":
    print(json.dumps(evaluate_cases(), indent=2))
