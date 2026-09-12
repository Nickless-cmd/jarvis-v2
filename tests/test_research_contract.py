from core.services.research_contract import (
    ResearchPolicy,
    load_research_contract,
    normalize_source,
)


def test_normalize_source_canonicalizes_url_and_keeps_evidence_fields():
    source = normalize_source({
        "url": "https://EXAMPLE.com/a?utm_source=x&b=2#fragment",
        "title": "  Primary source  ",
        "publisher": "Example",
        "published_at": "2026-09-01",
        "snippet": "Evidence",
    })
    assert source.canonical_url == "https://example.com/a?b=2"
    assert source.title == "Primary source"
    assert source.publisher == "Example"


def test_skill_load_is_explicit_and_has_safe_fallback(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "core.services.skill_engine.get_skill_instructions",
        lambda name: {"status": "error", "error": "missing"},
    )
    monkeypatch.setattr(
        "core.services.skill_engine.record_skill_usage",
        lambda name, **kwargs: calls.append((name, kwargs)),
    )
    contract = load_research_contract("find sources")
    assert contract.policy == ResearchPolicy()
    assert "primary" in contract.instructions.lower()
    assert contract.skill_available is False
    assert calls[0][1]["source"] == "explicit_research_mode"
