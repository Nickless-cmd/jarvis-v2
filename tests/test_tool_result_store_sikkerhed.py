"""Værktøjsresultater: privat rod, hash-tjekkede handles, link-sikker oprydning.

Fase 3, K8 og K11.

Den alvorlige del blev MÅLT 9/9-2026: `_result_path` byggede stien som
`TOOL_RESULTS_DIR / f"{result_id}.json"` uden validering, og `result_id` kommer
fra MODELLENS eget værktøjskald (`read_tool_result`). `get_tool_result(
"../hemmelig")` læste en fil uden for roden — verificeret, ikke formodet.
"""
from __future__ import annotations

import json
import os
import pathlib
import tempfile

import pytest

import core.services.tool_result_store as T
from core.services.tool_result_store import UnsafeResultId


@pytest.fixture
def store(monkeypatch):
    d = pathlib.Path(tempfile.mkdtemp())
    monkeypatch.setattr(T, "TOOL_RESULTS_DIR", d / "results")
    return d


# ── sti-traverseringen ───────────────────────────────────────────────────

@pytest.mark.parametrize("ond", [
    "../hemmelig", "../../etc/passwd", "a/b", "a\\b", ".", "..", "",
    "/absolut", "tool-result-x/../../y",
])
def test_en_result_id_der_kan_pege_ud_AFVISES(store, ond):
    with pytest.raises(UnsafeResultId):
        T._result_path(ond)


def test_traverseringen_virker_ikke_laengere(store):
    """Præcis det kald der lykkedes før rettelsen."""
    T._sikr_privat_rod()
    hemmelig = store / "hemmelig.json"
    hemmelig.write_text(json.dumps({"result": "NOEGLE-abc123"}))
    assert T.get_tool_result("../hemmelig") is None


def test_afvisningen_er_ikke_TAVS(store, caplog):
    """Modellen skriver selv denne streng — et forsøg er et signal."""
    import logging
    T._sikr_privat_rod()
    with caplog.at_level(logging.WARNING):
        T.get_tool_result("../noget")
    assert "afviste hentning" in caplog.text


def test_et_gyldigt_id_gaar_igennem(store):
    rid = T.save_tool_result("bash", {"command": "ls"}, "output")
    assert T.get_tool_result(rid) is not None


def test_den_oploeste_sti_skal_ligge_i_roden(store):
    """Andet lag: også hvis mønsteret en dag løsnes."""
    T._sikr_privat_rod()
    p = T._result_path("tool-result-abc")
    assert p.parent == T.TOOL_RESULTS_DIR.resolve()


# ── privat rod og ejer-only filer ────────────────────────────────────────

def test_roden_er_0700(store):
    T._sikr_privat_rod()
    assert T.TOOL_RESULTS_DIR.stat().st_mode & 0o077 == 0


def test_en_for_aaben_rod_strammes(store):
    T.TOOL_RESULTS_DIR.mkdir(parents=True)
    T.TOOL_RESULTS_DIR.chmod(0o755)
    T._sikr_privat_rod()
    assert T.TOOL_RESULTS_DIR.stat().st_mode & 0o077 == 0


def test_filen_er_ejer_only(store):
    rid = T.save_tool_result("bash", {}, "hemmeligt output")
    assert T._result_path(rid).stat().st_mode & 0o077 == 0


# ── hash-tjekkede handles ────────────────────────────────────────────────

def test_resultatet_baerer_en_digest(store):
    rid = T.save_tool_result("bash", {}, "output")
    assert str(T.get_tool_result(rid)["digest"]).startswith("sha256:")


def test_uroert_indhold_verificerer(store):
    rid = T.save_tool_result("bash", {}, "output")
    assert T.get_tool_result(rid)["verified"] is True


def test_AENDRET_indhold_fanges(store, caplog):
    """En handle der kun slås OP, beviser ingenting om det den leverer."""
    import logging
    rid = T.save_tool_result("bash", {}, "det ægte output")
    p = T._result_path(rid)
    d = json.loads(p.read_text())
    d["result"] = "noget helt andet"
    p.write_text(json.dumps(d))
    with caplog.at_level(logging.WARNING):
        r = T.get_tool_result(rid)
    assert r["verified"] is False and "digest passer IKKE" in caplog.text


def test_digesten_daekker_det_GEMTE_ikke_originalen(store, monkeypatch):
    """Et digest over noget der blev klippet væk, ville bevise en ting og
    udlevere en anden."""
    monkeypatch.setattr(T, "_MAX_STORED_CHARS", 50)
    rid = T.save_tool_result("bash", {}, "x" * 500)
    r = T.get_tool_result(rid)
    assert r["complete"] is False and r["verified"] is True


def test_en_gammel_post_UDEN_digest_er_UKENDT_ikke_forfalsket(store):
    """Et manglende digest må ikke læses som «forfalsket»."""
    rid = T.save_tool_result("bash", {}, "output")
    p = T._result_path(rid)
    d = json.loads(p.read_text()); d.pop("digest")
    p.write_text(json.dumps(d))
    assert T.get_tool_result(rid)["verified"] is None


# ── link-sikker oprydning ────────────────────────────────────────────────

def test_oprydningen_foelger_ikke_et_SYMLINK_ud_af_storen(store):
    """En sletning man ikke bad om, udført af en rutine der kører af sig selv."""
    T._sikr_privat_rod()
    udenfor = store / "vigtig.json"
    udenfor.write_text(json.dumps({"created_at": "2000-01-01T00:00:00+00:00"}))
    link = T.TOOL_RESULTS_DIR / "tool-result-link.json"
    os.symlink(udenfor, link)
    T.cleanup_old_results(max_age_days=0)
    assert udenfor.exists(), "oprydningen slettede en fil UDEN FOR storen"


def test_oprydningen_sletter_stadig_aegte_gamle_poster(store):
    """Værnet må ikke gøre oprydningen tandløs."""
    T._sikr_privat_rod()
    rid = T.save_tool_result("bash", {}, "gammel",
                             created_at="2000-01-01T00:00:00+00:00")
    assert T.cleanup_old_results(max_age_days=0) == 1
    assert T.get_tool_result(rid) is None
