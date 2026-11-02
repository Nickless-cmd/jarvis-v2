from core.services.research_contract import normalize_source
from core.services.research_quality import evaluate_research_report


def test_missing_citation_source_fails_critical_gate():
    result = evaluate_research_report("Claim [1]", sources=[], requested_facets=["price"])
    assert result.passed is False
    assert "citation_validity" in result.failures


def test_supported_cited_facets_pass():
    sources = [normalize_source({"url": "https://example.com", "title": "Example"})]
    result = evaluate_research_report(
        "Price is documented [1]. Security remains uncertain.",
        sources=sources,
        requested_facets=["price", "security"],
    )
    assert result.gates["citation_validity"] is True
    assert result.gates["coverage"] is True


def test_conflicting_language_requires_calibration():
    sources = [normalize_source({"url": "https://example.com"})]
    result = evaluate_research_report(
        "Sources conflict about the release date [1].",
        sources=sources,
        requested_facets=[],
        contradictions=["release date"],
    )
    assert result.gates["calibration"] is True


def test_authority_is_a_real_gate_not_just_a_url():
    unknown = [normalize_source({"url": "https://example.com/post"})]
    official = [normalize_source({
        "url": "https://example.com/docs",
        "authority": "official",
        "source_type": "documentation",
    })]
    assert evaluate_research_report("Claim [1]", unknown, []).gates["source_authority"] is False
    assert evaluate_research_report("Claim [1]", official, []).gates["source_authority"] is True


def test_freshness_gate_rejects_undated_evidence_when_required():
    sources = [normalize_source({"url": "https://example.com/latest"})]
    result = evaluate_research_report(
        "Latest release is X [1].",
        sources,
        [],
        requires_freshness=True,
    )
    assert result.gates["freshness"] is False
