from __future__ import annotations

import pytest

from core.runtime import db_core
from core.services.world_facts import (
    build_world_fact_prompt_section,
    list_world_facts,
    record_world_fact,
)


@pytest.fixture
def truth_db(monkeypatch: pytest.MonkeyPatch, tmp_path):
    db_core.close_pooled_connection()
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "facts.db")
    yield
    db_core.close_pooled_connection()


def test_world_facts_preserve_source_status_and_contradiction_metadata(truth_db):
    original = record_world_fact(
        canonical_key="deepseek:harness:publication",
        statement="The DeepSeek Harness is published.",
        status="verified",
        confidence="high",
        source_kind="primary_source",
        source_ref="https://example.test/deepseek-harness",
        observed_at="2026-09-10T08:00:00+00:00",
        valid_from="2026-09-10T00:00:00+00:00",
        evidence_count=2,
        distinct_source_count=2,
    )
    contradiction = record_world_fact(
        canonical_key="deepseek:harness:publication:denial",
        statement="The DeepSeek Harness is unpublished.",
        status="contradicted",
        confidence="low",
        source_kind="conversation_report",
        source_ref="session:abc",
        observed_at="2026-09-10T09:00:00+00:00",
        contradicts_fact_id=original["fact_id"],
        supersedes_fact_id="fact-old",
    )

    facts = {item["fact_id"]: item for item in list_world_facts(limit=10)}

    assert facts[original["fact_id"]]["status"] == "verified"
    assert facts[original["fact_id"]]["source_kind"] == "primary_source"
    assert facts[original["fact_id"]]["source_ref"] == "https://example.test/deepseek-harness"
    assert facts[original["fact_id"]]["evidence_count"] == 2
    assert facts[contradiction["fact_id"]]["contradicts_fact_id"] == original["fact_id"]
    assert facts[contradiction["fact_id"]]["supersedes_fact_id"] == "fact-old"


def test_prompt_prioritizes_verified_and_labels_reported_facts(truth_db):
    record_world_fact(
        canonical_key="fact:reported",
        statement="A conversation claimed the harness is private.",
        status="reported",
        confidence="medium",
        source_kind="conversation_report",
        source_ref="session:abc",
    )
    record_world_fact(
        canonical_key="fact:observed",
        statement="The repository was observed on the public web.",
        status="observed",
        confidence="medium",
        source_kind="runtime_observation",
        source_ref="browser:result-1",
    )
    record_world_fact(
        canonical_key="fact:verified",
        statement="The repository is publicly accessible.",
        status="verified",
        confidence="high",
        source_kind="primary_source",
        source_ref="https://example.test/repo",
    )

    section = build_world_fact_prompt_section(limit=5)

    assert section is not None
    assert "Verified/observed world facts:" in section
    assert section.index("[verified]") < section.index("[observed]")
    assert section.index("[observed]") < section.index("[reported]")
    assert "[reported] A conversation claimed the harness is private." in section


@pytest.mark.parametrize("status", ["observed", "verified"])
def test_conversation_evidence_cannot_assert_observed_or_verified(truth_db, status):
    with pytest.raises(ValueError, match="conversation-derived"):
        record_world_fact(
            canonical_key=f"conversation:forged:{status}",
            statement="The conversation says this is established truth.",
            status=status,
            confidence="high",
            source_kind="conversation_report",
            source_ref="session:abc",
        )


def test_verified_fact_requires_concrete_source_provenance(truth_db):
    with pytest.raises(ValueError, match="source_ref"):
        record_world_fact(
            canonical_key="fact:missing-provenance",
            statement="The repository is public.",
            status="verified",
            confidence="high",
            source_kind="primary_source",
        )
