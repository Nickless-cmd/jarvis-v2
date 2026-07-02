"""Tests for core/services/central_notation.py — model-frit bevis (Centralen regner på sine tanker)."""
from __future__ import annotations

from core.services import central_notation as nt
from core.services import central_hypothesis_generator as gen


def test_parse_relation():
    p = nt.parse("kontinuitet → vægt")
    assert p == {"antecedent": "kontinuitet", "operator": "→", "consequent": "vægt"}
    assert nt.parse("!grænse") == {"antecedent": "", "operator": "!", "consequent": "grænse"}
    assert nt.parse("volapyk uden operator") is None


def test_dedup_collapses_identical():
    out = nt.dedup(["pres → fokus", "pres  →  fokus", "ro → vægt"])
    assert set(out) == {"pres → fokus", "ro → vægt"}


def test_correlate_by_antecedent():
    items = [
        {"hyp_id": "a", "notation_il": "pres → fokus"},
        {"hyp_id": "b", "notation_il": "pres → vægt"},     # samme antecedent 'pres'
        {"hyp_id": "c", "notation_il": "ro → vægt"},
    ]
    groups = nt.correlate_by_antecedent(items)
    assert set(groups["pres"][0].keys()) >= {"hyp_id", "notation_il"}
    assert {it["hyp_id"] for it in groups["pres"]} == {"a", "b"}
    assert {it["hyp_id"] for it in groups["ro"]} == {"c"}


def test_model_free_analysis_end_to_end(isolated_runtime):
    """NORDSTJERNE: hypoteser med notation → dedup + korrelation UDEN model."""
    gen.ensure_schema()
    # to hypoteser med samme antecedent (memory→...) + én duplikat
    for child in ("somatic", "cognition"):
        gen.register_governed_hypothesis(gen.formulate_correlation_hypothesis(
            {"parent_family": "memory", "child_family": child, "count": 4, "cursor": 1}))
    res = nt.model_free_analysis()
    assert res["model_used"] is False
    assert res["total_with_notation"] >= 2
    # 'kontinuitet' (memory) er antecedent for begge → en korrelation
    assert any(len(ids) >= 2 for ids in res["correlations"].values())
