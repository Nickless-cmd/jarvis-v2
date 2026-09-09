"""Kompaktering — erstatning, aldrig sletning, og aldrig en løkke.

Fase 2: «compaction advances surface generation atomically or leaves it
unchanged; overflow retries occur only after an advancing replacement».

Uden den regel er overløb en løkke: prompten er for stor → kompaktér →
kompakteringen frigav ingenting → prøv igen → prompten er stadig for stor.
Hvert omløb koster et modelkald.
"""
from __future__ import annotations

import pytest

from core.services import compaction_runtime as C
from core.services.compaction_runtime import (
    NotAdvancing, Node, Policy, Surface, failed, may_retry_after_overflow,
    protected_ids, prune_tool_results, replaceable_range, require_advance,
    summarize,
)


def _flade(n=40, *, hale=5):
    """En overflade med identitet i toppen og en blandet krop."""
    nodes = [Node("sys", "system", 500), Node("id", "identity", 800)]
    for i in range(n):
        nodes.append(Node(f"u{i}", "user", 100))
        nodes.append(Node(f"a{i}", "assistant", 300))
    return Surface(tuple(nodes)), Policy(retained_tail=hale)


# ── hvad der aldrig må erstattes ─────────────────────────────────────────

def test_identitet_og_systemknuder_er_fredet():
    s, p = _flade()
    f = protected_ids(s, p)
    assert "sys" in f and "id" in f


def test_halen_er_fredet():
    """En samtale uden nyere kontekst er en samtale der har glemt hvad den
    handlede om."""
    s, p = _flade(hale=6)
    f = protected_ids(s, p)
    assert {n.node_id for n in s.nodes[-6:]} <= f


def test_brugerens_AKTUELLE_input_er_fredet():
    s, p = _flade()
    assert "u3" in protected_ids(s, p, current_user_input="u3")


def test_et_uafsluttet_vaerktoejspar_roeres_ikke():
    """Erstattes kaldet men ikke resultatet, refererer historikken til noget
    der ikke findes."""
    s = Surface((Node("sys", "system"), Node("c1", "tool_call", 10, pair_id="r1"),
                 Node("r1", "tool_result", 5000), Node("u", "user", 10)))
    f = protected_ids(s, Policy(retained_tail=0))
    assert "c1" in f and "r1" in f


def test_et_kald_UDEN_resultat_er_ogsaa_fredet():
    s = Surface((Node("c1", "tool_call", 10, pair_id="mangler"), Node("u", "user", 10)))
    assert "c1" in protected_ids(s, Policy(retained_tail=0))


# ── beskæring før opsummering ────────────────────────────────────────────

def test_store_vaerktoejsresultater_beskaeres():
    s = Surface((Node("r1", "tool_result", 50_000), Node("u", "user", 10)))
    r = prune_tool_results(s, Policy(retained_tail=0, prune_tool_results_over=2000))
    assert r.advanced is True and r.freed_tokens == 48_000
    assert r.surface.nodes[0].tokens == 2000


def test_beskaering_rykker_generationen():
    s = Surface((Node("r1", "tool_result", 50_000),))
    r = prune_tool_results(s, Policy(retained_tail=0))
    assert r.surface.generation == s.generation + 1


def test_smaa_resultater_roeres_ikke():
    s = Surface((Node("r1", "tool_result", 100),))
    r = prune_tool_results(s, Policy(retained_tail=0, prune_tool_results_over=2000))
    assert r.advanced is False and r.surface is s


def test_INTET_at_beskaere_rykker_ikke_generationen():
    s = Surface((Node("u", "user", 10),))
    r = prune_tool_results(s, Policy(retained_tail=0))
    assert r.advanced is False and r.surface.generation == 0


def test_fredede_resultater_beskaeres_ikke():
    s = Surface((Node("r1", "tool_result", 50_000),))
    r = prune_tool_results(s, Policy(retained_tail=1))
    assert r.advanced is False


# ── ét sammenhængende spænd ──────────────────────────────────────────────

def test_spaendet_er_sammenhaengende():
    """En opsummering af spredte stumper er ikke en opsummering af en samtale
    — den er en liste over hvad der tilfældigvis ikke var fredet."""
    s, p = _flade(n=20, hale=4)
    i, j = replaceable_range(s, p)
    assert i < j
    fredet = protected_ids(s, p)
    assert not any(n.node_id in fredet for n in s.nodes[i:j])


def test_intet_spaend_naar_alt_er_fredet():
    s = Surface((Node("sys", "system"), Node("id", "identity")))
    assert replaceable_range(s, Policy()) == (0, 0)


# ── opsummering ──────────────────────────────────────────────────────────

def test_spaendet_erstattes_af_EN_opsummering():
    s, p = _flade(n=20, hale=4)
    foer = len(s.nodes)
    r = summarize(s, p, summary_text="kort", summary_tokens=200)
    assert r.advanced is True and len(r.surface.nodes) < foer
    assert any(n.node_id.startswith("summary-") for n in r.surface.nodes)


def test_opsummeringen_frigiver_tokens():
    s, p = _flade(n=20, hale=4)
    r = summarize(s, p, summary_text="kort", summary_tokens=200)
    assert r.freed_tokens > 0 and r.surface.tokens() < s.tokens()


def test_en_opsummering_der_ikke_er_MINDRE_rykker_ikke_generationen():
    """Ellers ville et genforsøg være tilladt uden at der var frigivet noget."""
    s, p = _flade(n=20, hale=4)
    r = summarize(s, p, summary_text="x", summary_tokens=10_000_000)
    assert r.advanced is False and r.surface.generation == 0


def test_identitet_overlever_opsummeringen():
    s, p = _flade(n=20, hale=4)
    r = summarize(s, p, summary_text="kort", summary_tokens=200)
    ids = {n.node_id for n in r.surface.nodes}
    assert "sys" in ids and "id" in ids


# ── atomisk eller slet ikke ──────────────────────────────────────────────

def test_en_FEJLET_kompaktering_lader_generationen_staa():
    s, p = _flade()
    r = failed(s, "opsummeringsmodellen svarede ikke")
    assert r.advanced is False and r.surface.generation == s.generation
    assert r.surface is s


def test_den_oprindelige_fejl_BEVARES():
    """Erstattes den med «kompakteringen fejlede», mister man hvorfor der
    skulle kompakteres."""
    r = failed(_flade()[0], "kontekst-overløb: 190k af 180k")
    assert "190k" in r.error


def test_en_fejl_afregnes_som_started_plus_failed():
    assert failed(_flade()[0], "x").events == (C.STARTED, C.FAILED)


def test_et_lykkedes_afregnes_som_started_plus_ended():
    s = Surface((Node("r1", "tool_result", 50_000),))
    assert prune_tool_results(s, Policy(retained_tail=0)).events == (C.STARTED, C.ENDED)


# ── LØKKEN der ikke må opstå ─────────────────────────────────────────────

def test_overloeb_maa_KUN_proeves_igen_naar_generationen_rykkede():
    s = Surface((Node("r1", "tool_result", 50_000),))
    r = prune_tool_results(s, Policy(retained_tail=0))
    assert may_retry_after_overflow(s, r) is True


def test_overloeb_maa_IKKE_proeves_igen_naar_intet_blev_frigivet():
    """Prompten er stadig for stor. Et genforsøg ville være samme kald med
    samme udfald — i en løkke der koster et modelkald pr. omgang."""
    s = Surface((Node("u", "user", 10),))
    r = prune_tool_results(s, Policy(retained_tail=0))
    assert may_retry_after_overflow(s, r) is False


def test_en_fejlet_kompaktering_giver_ikke_lov_til_genforsoeg():
    s, _ = _flade()
    assert may_retry_after_overflow(s, failed(s, "fejl")) is False


def test_require_advance_KASTER_frem_for_at_loekke():
    s = Surface((Node("u", "user", 10),))
    r = prune_tool_results(s, Policy(retained_tail=0))
    with pytest.raises(NotAdvancing, match="samme kald med samme udfald"):
        require_advance(s, r)


def test_require_advance_slipper_en_aegte_kompaktering_igennem():
    s = Surface((Node("r1", "tool_result", 50_000),))
    r = prune_tool_results(s, Policy(retained_tail=0))
    assert require_advance(s, r) is r


def test_fejlbeskeden_siger_hvilken_generation_der_staar_stille():
    s = Surface((Node("u", "user", 10),), generation=7)
    with pytest.raises(NotAdvancing, match="står stadig på 7"):
        require_advance(s, prune_tool_results(s, Policy(retained_tail=0)))


# ── overfladen ændres aldrig i stedet for at erstattes ───────────────────

def test_den_gamle_overflade_roeres_ikke():
    """Kompaktering er ERSTATNING, ikke mutation: den gamle generation skal
    stadig kunne læses."""
    s = Surface((Node("r1", "tool_result", 50_000),))
    r = prune_tool_results(s, Policy(retained_tail=0))
    assert s.nodes[0].tokens == 50_000 and r.surface is not s


def test_hvert_udfald_siger_HVILKEN_regel_der_afgjorde_det():
    s, p = _flade()
    for r in (prune_tool_results(s, p), summarize(s, p, summary_text="x", summary_tokens=200),
              failed(s, "x")):
        assert r.rule
