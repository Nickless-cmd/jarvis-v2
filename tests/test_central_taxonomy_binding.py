"""Tests for Spec B / Fase B0 — taksonomi-binding (S1: hele det operationelle vokabular sigeligt)."""
from __future__ import annotations

from core.services import central_lexicon as lx


def test_taxonomy_names_cover_clusters_and_families():
    """Taksonomien = clusters (CLUSTER_PRIORITY) + operationelle familier (FAMILY_ROUTES)."""
    names = set(lx._taxonomy_names())
    # et par kendte fra hver kilde skal være med
    assert {"auth", "truth", "loop", "memory", "system"} <= names       # clusters
    assert {"runtime", "tool", "cost", "channel", "anomaly"} <= names   # familier


def test_known_taxonomy_names_are_bound():
    """De ærlige seed-bindinger skal faktisk binde de operationelle kerne-navne."""
    for name, term in [("auth", "grænse"), ("loop", "rytme"), ("system", "krop"),
                       ("tools", "handling"), ("anomaly", "stød"), ("cost", "vægt"),
                       ("channel", "relation"), ("review", "spejl")]:
        assert lx.to_term(name) == term, (name, lx.to_term(name))


def test_genuinely_new_concepts_stay_unbound():
    """ÆRLIGHED: begreber uden sandt eksisterende ord forbliver ubundet → ceremoni (ikke tvunget match)."""
    cov = lx.taxonomy_coverage()
    unbound = set(cov["unbound_names"])
    # disse 6 er genuint nye begreber (sandhed/forandring/evne/råd/heling/handel)
    assert {"truth", "mutation", "skill", "council", "self_repair", "trading"} <= unbound
    # og de er IKKE tvunget ind på et forkert eksisterende ord
    for n in ["truth", "mutation", "skill", "council", "self_repair", "trading"]:
        assert lx.to_term(n) is None


def test_coverage_ratio_is_high_but_honest():
    """Dækning skal være høj (det meste sigeligt) men < 1.0 (ærlige huller tilbage til ceremoni)."""
    cov = lx.taxonomy_coverage()
    assert cov["total"] >= 25
    assert cov["bound"] == cov["total"] - cov["unbound"]
    assert 0.7 <= cov["ratio"] < 1.0


def test_bind_taxonomy_surfaces_word_needs():
    """bind_taxonomy leverer de ubundne som word-needs (Bjørn-ceremoni-kandidater)."""
    rep = lx.bind_taxonomy()
    need_names = {w["name"] for w in rep["word_needs"]}
    assert {"truth", "council"} <= need_names
    # bundne navne dukker ALDRIG op som word-needs
    assert "auth" not in need_names and "loop" not in need_names


def test_no_forced_bad_mapping_runtime_stays_puls():
    """Regression: taksonomi-bindingen må ikke overskrive ægte eksisterende bindinger."""
    assert lx.to_term("runtime") == "puls"        # familie, uændret
    assert lx.to_term("memory") == "kontinuitet"  # både cluster OG familie — samme term, konsistent


def test_reasoning_tick_records_taxonomy_ratio(isolated_runtime):
    """Notation-cadence (sprog-ticken) rapporterer nu taksonomi-dækning (S1-fremdrift plotbar)."""
    from core.services import central_notation as nt
    out = nt.run_notation_reasoning_tick()
    assert out["status"] == "ok"
    assert out["taxonomy_ratio"] is not None and 0.0 <= out["taxonomy_ratio"] <= 1.0
