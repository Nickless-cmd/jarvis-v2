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


def test_transitive_inference_model_free():
    """KRONJUVELEN: fra A→B og B→C udled A→C — en NY tanke, model-frit."""
    items = [
        {"hyp_id": "1", "notation_il": "strid → drøm"},
        {"hyp_id": "2", "notation_il": "drøm → fokus"},
    ]
    derived = nt.infer_transitive(items)
    notas = {d["notation"] for d in derived}
    assert "strid → fokus" in notas            # udledt: konflikt → (drøm) → fokus
    d = next(d for d in derived if d["notation"] == "strid → fokus")
    assert d["via"] == "drøm" and d["chain"] == "strid → drøm → fokus"


def test_transitive_skips_known_and_selfloops():
    items = [
        {"hyp_id": "1", "notation_il": "pres → fokus"},
        {"hyp_id": "2", "notation_il": "fokus → pres"},   # ville give pres→pres (selv-løkke) — skip
        {"hyp_id": "3", "notation_il": "pres → ro"},       # allerede kendt hvis fokus→ro? nej
    ]
    derived = nt.infer_transitive(items)
    assert not any(d["notation"] == "pres → pres" for d in derived)


def test_contradiction_detection():
    items = [
        {"hyp_id": "1", "notation_il": "pres → ro"},
        {"hyp_id": "2", "notation_il": "pres → !ro"},      # samme antecedent, modsat
    ]
    con = nt.detect_notation_contradictions(items)
    assert con and con[0]["antecedent"] == "pres" and con[0]["term"] == "ro"


def test_model_free_reasoning_end_to_end(isolated_runtime):
    from core.services import central_hypothesis_generator as gen
    from core.runtime.db import connect
    gen.ensure_schema()
    # to kæde-hypoteser med notation → transitiv inferens
    with connect() as c:
        for i, nota in enumerate(["strid → drøm", "drøm → fokus"]):
            c.execute(
                "INSERT INTO central_hypotheses (hyp_id, source, statement, prediction, "
                "null_hypothesis, success_criterion, sample_size, ttl_seconds, provenance_json, "
                "confidence, status, grounded_samples, created_at, notation_il) "
                "VALUES (?,?,?,?,?,?,?,?,?,?, 'active', 0, '2026-07-02T00:00:00Z', ?)",
                (f"h{i}", "causal_convergence", "s", "p", "n", "sc", 5, 3600, "{}", 0.3, nota))
        c.commit()
    r = nt.model_free_reasoning()
    assert r["model_used"] is False
    assert any(d["notation"] == "strid → fokus" for d in r["derived_inferences"])


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
