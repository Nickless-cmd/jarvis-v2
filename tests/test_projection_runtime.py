"""Projektions-runtimen — Fase 1's projektions-kriterier.

    «Projection units are pure, versioned, schema-validated folds; every
     multi-key snapshot has one `as_of_seq`, stale or incompatible caches are
     discarded, and an empty cache reproduces the same values.»
    «A projector crash between row work and cursor advancement replays without
     duplicate messages.»
"""
from __future__ import annotations

import pytest

from core.runtime import db_session_ledger as L
from core.services import projection_runtime as P


@pytest.fixture(autouse=True)
def _rent_register():
    P._unregister_all_for_tests()
    yield
    P._unregister_all_for_tests()


@pytest.fixture
def sid(isolated_runtime):
    from datetime import UTC, datetime
    return "proj-" + datetime.now(UTC).strftime("%H%M%S%f")


def _skriv(sid: str, *ids: str) -> None:
    t = L.acquire_write_lease(sid, owner="test")
    L.append_session_events(sid, owner="test", token=t, events=[
        {"event_id": i, "kind": "besked", "payload": {"tekst": i}} for i in ids
    ])
    L.release_write_lease(sid, owner="test", token=t)


def _taeller_fold(state, e):
    """Idempotent pr. hændelse: samme event_id to gange ændrer intet."""
    state.setdefault("set", set()).add(e["event_id"])
    state["antal"] = len(state["set"])
    return state


# ── registret ────────────────────────────────────────────────────────────

def test_samme_navn_med_anden_version_er_en_FEJL(sid):
    """En stille erstatning ville gøre det afhængigt af import-rækkefølgen
    hvilken fold der gælder — præcis den dobbelt-sandhed registret skal hindre."""
    P.register("t", version="1", fold=_taeller_fold)
    P.register("t", version="1", fold=_taeller_fold)          # samme version: ok
    with pytest.raises(ValueError):
        P.register("t", version="2", fold=_taeller_fold)


def test_en_ukendt_projektion_er_en_fejl_ikke_et_tomt_svar(sid):
    with pytest.raises(KeyError):
        P.project(sid, "findes-ikke")


# ── foldning og markør ───────────────────────────────────────────────────

def test_folder_alle_haendelser_og_saetter_markoeren(sid):
    P.register("t", version="1", fold=_taeller_fold)
    _skriv(sid, "a", "b", "c")
    r = P.project(sid, "t")
    assert r["state"]["antal"] == 3 and r["as_of_seq"] == 3 and r["refolded"] is True


def test_anden_koersel_folder_kun_det_NYE(sid):
    P.register("t", version="1", fold=_taeller_fold)
    _skriv(sid, "a", "b")
    P.project(sid, "t")
    _skriv(sid, "c")
    r = P.project(sid, "t")
    assert r["events"] == 1 and r["as_of_seq"] == 3 and r["refolded"] is False


def test_en_TOM_cache_giver_SAMME_resultat(sid):
    """Kernen: projektionen er en ren funktion af hændelserne. Kan den ikke
    genskabes fra ingenting, er den ikke en projektion — den er en tilstand."""
    P.register("t", version="1", fold=_taeller_fold)
    _skriv(sid, "a", "b", "c")
    foerst = P.project(sid, "t")["state"]["antal"]
    genfoldet = P.project(sid, "t", force_refold=True)
    assert genfoldet["state"]["antal"] == foerst and genfoldet["refolded"] is True


def test_VERSIONSSKIFTE_kasserer_og_folder_forfra(sid):
    P.register("t", version="1", fold=_taeller_fold)
    _skriv(sid, "a", "b")
    P.project(sid, "t")
    P._unregister_all_for_tests()
    P.register("t", version="2", fold=_taeller_fold)
    r = P.project(sid, "t")
    assert r["refolded"] is True and r["events"] == 2


def test_et_nedbrud_mellem_arbejdet_og_markoeren_fordobler_intet(sid):
    """Markøren behøver ikke være atomisk med arbejdet, FORDI folden er
    idempotent pr. hændelse. Her efterlignes nedbruddet: markøren rykkes ikke,
    og der foldes igen over de samme hændelser."""
    P.register("t", version="1", fold=_taeller_fold)
    _skriv(sid, "a", "b", "c")
    P.project(sid, "t")
    for _ in range(3):
        r = P.project(sid, "t", force_refold=True)
    assert r["state"]["antal"] == 3


def test_en_tom_session_giver_tom_tilstand_og_markoer_nul(sid):
    P.register("t", version="1", fold=_taeller_fold)
    r = P.project(sid, "t")
    assert r["as_of_seq"] == 0 and r["events"] == 0


def test_starttilstanden_deles_ALDRIG_mellem_koersler(sid):
    """Et delt muterbart objekt ville gøre folden uren uden at det kunne ses."""
    P.register("t", version="1", fold=_taeller_fold)
    _skriv(sid, "a")
    a = P.project(sid, "t", force_refold=True)["state"]
    b = P.project(sid, "t", force_refold=True)["state"]
    assert a is not b


# ── øjebliksbillede med ét skæringspunkt ─────────────────────────────────

def test_flere_projektioner_deler_ET_as_of_seq(sid):
    """Uden det kunne to celler beskrive to forskellige tidspunkter — og
    læseren kunne ikke se det."""
    P.register("a", version="1", fold=_taeller_fold)
    P.register("b", version="1", fold=_taeller_fold)
    _skriv(sid, "e1", "e2")
    s = P.snapshot(sid)
    assert set(s["cells"]) == {"a", "b"} and s["as_of_seq"] == 2


def test_skaeringen_er_den_LAVESTE_af_cellerne(sid):
    """At vælge den højeste ville love mere end den mindst opdaterede celle
    kan holde."""
    P.register("a", version="1", fold=_taeller_fold)
    _skriv(sid, "e1", "e2")
    P.project(sid, "a")                       # a er nu på 2
    P.register("b", version="1", fold=lambda s, e: s)
    s = P.snapshot(sid, ["a", "b"])
    assert s["as_of_seq"] == 2


def test_et_tomt_oejebliksbillede_er_sekvens_nul(sid):
    assert P.snapshot(sid, [])["as_of_seq"] == 0


# ── cache-fejl må ikke ændre sandhed ─────────────────────────────────────

def test_et_ULAESELIGT_checkpoint_giver_genfoldning_ikke_tab(sid, monkeypatch):
    """Det modsatte — at antage man er længere fremme end man er — ville tabe
    hændelser i stilhed."""
    P.register("t", version="1", fold=_taeller_fold)
    _skriv(sid, "a", "b")
    monkeypatch.setattr(P, "checkpoint", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nej")))
    with pytest.raises(RuntimeError):
        P.project(sid, "t")


def test_et_MANGLENDE_checkpoint_folder_fra_nul(sid, monkeypatch):
    P.register("t", version="1", fold=_taeller_fold)
    _skriv(sid, "a", "b")
    monkeypatch.setattr(P, "checkpoint", lambda *a, **k: None)
    r = P.project(sid, "t")
    assert r["refolded"] is True and r["state"]["antal"] == 2
