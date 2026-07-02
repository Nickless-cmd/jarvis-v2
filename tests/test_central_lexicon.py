"""Tests for core/services/central_lexicon.py — sprog-pre-start (lexicon-binding)."""
from __future__ import annotations

from core.services import central_lexicon as lex


def test_reuses_existing_vocabulary():
    # Ét sprog: termerne kommer fra interlanguage_practice, ikke et parallelt sæt
    assert "pres" in lex.active_terms() and "kontinuitet" in lex.active_terms()
    assert "→" in lex.operators() and "!" in lex.operators()


def test_seed_bindings_lookup():
    assert lex.to_term("pressure") == "pres"
    assert lex.to_term("memory") == "kontinuitet"
    assert lex.to_term("gut") == "agens"
    assert lex.to_term("somatic") == "vægt"


def test_unbound_returns_none_honestly():
    # sproget dækker ikke al operationel VVS endnu — det indrømmer vi
    assert lex.to_term("runtime") is None
    assert lex.to_term("trading") is None
    assert lex.to_term("reboot") is None


def test_render_relation():
    assert lex.render_relation("memory", "somatic") == "kontinuitet → vægt"
    # ubundet led → None (kan ikke siges endnu)
    assert lex.render_relation("runtime", "tool") is None


def test_bind_rejects_non_vocabulary_term_without_ceremony(isolated_runtime):
    # ny term uden for det frosne vokabular kan ikke blive 'active' uden ceremoni
    res = lex.bind("konflikt", "konfliktterm", status="active")
    assert res["status"] == "rejected"
    # men kan registreres som kandidat
    res2 = lex.bind("cognitive_counterfactual", "drøm", status="active")  # eksisterende term OK
    assert res2["status"] == "ok"
    assert lex.to_term("cognitive_counterfactual") == "drøm"


def test_unbound_names_lists_candidates():
    names = ["memory", "runtime", "gut", "trading"]
    assert set(lex.unbound_names(names)) == {"runtime", "trading"}
