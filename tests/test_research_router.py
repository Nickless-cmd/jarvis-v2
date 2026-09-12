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
    # Fase C2 (13/9-2026): beskeden bærer tre uafhængige signaler
    # (bredde + antal + facetter), så indsats-tabellen giver rækken for 3 —
    # max_tasks/source_target er 5, ikke 6 som før, hvor ALLE orchestratede
    # runs fik samme flade tildeling. Kalderens loft (20) er stadig ikke nået.
    assert decision.max_tasks == 5
    assert decision.source_target == 5
    assert decision.worker_token_budget == 30_000
    assert len(decision.signals) >= 3


def test_one_deep_topic_does_not_fan_out():
    decision = classify_research(
        "Forklar dette ene komplekse bevis grundigt",
        policy=ResearchPolicy(),
    )
    assert decision.tier == "inline"


# --- Fase C2: indsatsen skalerer med signalstyrken (13/9-2026) ---
#
# Anthropic målte at token-forbrug alene forklarer 80% af variansen i
# resultatkvalitet — og at indsats SKAL skaleres. Disse tests holder den
# egenskab fast: flere uafhængige signaler må aldrig give MINDRE indsats.

def _decision_for_signals(independent: int, **policy_kwargs):
    """Byg en besked med præcis N uafhængige signaler."""
    text = "Sammenlign leverandører på pris og sikkerhed — grundig rapport"
    if independent >= 3:
        text = "Sammenlign fem leverandører på pris og sikkerhed — grundig rapport"
    attachments = 3 if independent >= 4 else 0
    return classify_research(text, attachment_count=attachments, policy=ResearchPolicy(**policy_kwargs))


def test_C2_indsatsen_vokser_med_signalantallet():
    two, three, four = (_decision_for_signals(n) for n in (2, 3, 4))
    assert [two.tier, three.tier, four.tier] == ["orchestrated"] * 3
    assert len(two.signals) < len(three.signals) < len(four.signals)
    for field in ("max_workers", "max_tasks", "source_target", "worker_max_turns", "worker_token_budget"):
        values = [getattr(d, field) for d in (two, three, four)]
        assert values == sorted(values), f"{field} skalerer ikke: {values}"
        assert values[0] < values[-1], f"{field} vokser slet ikke: {values}"


def test_C2_workers_overstiger_aldrig_planlagte_tracks():
    """`_plan` laver min(max_tasks, len(facets)) tracks. Flere workers end det
    er ledige hænder — og det var præcis den slags spild C2 skal fjerne."""
    for independent in (2, 3, 4):
        decision = _decision_for_signals(independent)
        assert decision.max_workers <= decision.max_tasks, decision


def test_C2_kalderens_loft_staar_altid():
    """En kalder der strammer policy'en skal kunne det — indsats-tabellen er et
    forslag, ikke en overruling."""
    tight = _decision_for_signals(4, max_workers=1, max_tasks=2, max_tool_calls=5, source_target=2)
    assert tight.max_workers == 1
    assert tight.max_tasks == 2
    assert tight.max_tool_calls == 5
    assert tight.source_target == 2


def test_C2_inline_faar_intet_worker_budget():
    """Inline kører i selve visible-lanen — der er ingen workers at budgettere.
    Et budget her ville være et tal uden en modtager."""
    decision = classify_research("Hvad er seneste WLED version?", policy=ResearchPolicy())
    assert decision.tier == "inline"
    assert decision.worker_token_budget == 0
    assert decision.max_workers == 1
