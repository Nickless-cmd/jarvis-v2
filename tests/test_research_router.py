from core.services.research_contract import ResearchPolicy
from core.services.research_router import classify_research


def test_latest_single_lookup_stays_inline():
    decision = classify_research("Hvad er seneste WLED version?", policy=ResearchPolicy())
    assert decision.tier == "inline"
    assert decision.max_workers == 1


def test_multi_entity_multi_facet_report_is_orchestrated_and_bounded():
    decision = classify_research(
        "Sammenlign fem leverandører på pris, sikkerhed og drift i en grundig rapport",
        policy=ResearchPolicy(max_workers=9, max_tasks=20),
    )
    assert decision.tier == "orchestrated"
    assert decision.max_workers == 3
    assert decision.max_tasks == 6
    assert len(decision.signals) >= 3


def test_one_deep_topic_does_not_fan_out():
    decision = classify_research(
        "Forklar dette ene komplekse bevis grundigt",
        policy=ResearchPolicy(),
    )
    assert decision.tier == "inline"
