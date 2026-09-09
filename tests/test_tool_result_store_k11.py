"""Artefakt-filer: private roedder, ejerskab, redigeret metadata — Fase 3, K11.

Maalt paa produktionen 9/9-2026, 30.650 gemte handles:

    rod-rettigheder                  0700
    filer paa 0644 (laesbare for alle)   30.495
    filer paa 0600                          149
    poster UDEN ejer                 30.640 af 30.640 laesbare
    poster med `_runtime_user_id` i argumenterne   22.207
    mulige hemmeligheder             84 — 62 af dem i ARGUMENTERNE

Det sidste par tal er pointen: oplysningen der skal til for at autorisere en
hentning laa der allerede, i praecis det felt der ikke burde gemmes.
"""
from __future__ import annotations

import json
import logging
import os

import pytest

from core.services import tool_result_store as S

HEMMELIG = "curl -H 'Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345' https://x"


@pytest.fixture(autouse=True)
def _rene(tmp_path, monkeypatch):
    """`TOOL_RESULTS_DIR` bindes ved IMPORT, saa `isolated_runtime` alene
    flytter den ikke — testene skrev i den AEGTE store, og en symlink fra en
    test blev liggende dér. Peg modulet paa tmp, som naboftesten allerede goer.
    """
    monkeypatch.setattr(S, "TOOL_RESULTS_DIR", tmp_path / "tool_results")
    yield


# ── ejerskab loeftes ud af argumenterne ──────────────────────────────────

def test_ejeren_loeftes_ud_af_runtime_noeglerne():
    rid = S.save_tool_result("bash", {"command": "ls",
                                      "_runtime_user_id": "bjorn",
                                      "_runtime_session_id": "s1"}, "ud")
    d = S.get_tool_result(rid)
    assert d["owner_user_id"] == "bjorn" and d["session_id"] == "s1"


def test_runtime_noeglerne_gemmes_IKKE():
    """De er runtime-tilstand, ikke modellens kald — 22.207 poster baerer dem
    rundt uden grund."""
    rid = S.save_tool_result("bash", {"command": "ls",
                                      "_runtime_user_id": "bjorn",
                                      "_runtime_trust_all": True}, "ud")
    args = S.get_tool_result(rid)["arguments"]
    assert args == {"command": "ls"}
    raa = (S.TOOL_RESULTS_DIR / f"{rid}.json").read_text(encoding="utf-8")
    assert "_runtime_trust_all" not in raa


# ── autoriseret hentning ─────────────────────────────────────────────────

def test_ejeren_kan_hente_sin_egen():
    rid = S.save_tool_result("bash", {"_runtime_user_id": "bjorn"}, "ud")
    assert S.get_tool_result(rid, user_id="bjorn") is not None


def test_en_ANDEN_bruger_naegtes(caplog):
    """At kende id'et maa ikke vaere nok."""
    rid = S.save_tool_result("bash", {"_runtime_user_id": "bjorn"}, "hemmeligt")
    with caplog.at_level(logging.WARNING):
        assert S.get_tool_result(rid, user_id="mikkel") is None
    assert "naegtede hentning" in caplog.text


def test_uden_spoerger_tjekkes_der_ikke():
    """Interne kaldere uden bruger-kontekst maa stadig laese."""
    rid = S.save_tool_result("bash", {"_runtime_user_id": "bjorn"}, "ud")
    assert S.get_tool_result(rid) is not None


def test_LEGACY_uden_ejer_slipper_igennem():
    """30.640 poster har ingen ejer. At afvise dem ville goere hele arkivet
    ulaeseligt for at lukke et hul der ikke findes i dem."""
    rid = S.save_tool_result("bash", {"command": "ls"}, "ud")
    assert S.get_tool_result(rid, user_id="hvem_som_helst") is not None


def test_vaerktoejet_giver_den_spoergende_med():
    """Koblingen: uden den er tjekket kun en funktion ingen kalder."""
    from core.tools.file_tools_exec import _exec_read_tool_result
    rid = S.save_tool_result("bash", {"_runtime_user_id": "bjorn"}, "ud")
    assert _exec_read_tool_result({"result_id": rid,
                                   "_runtime_user_id": "bjorn"})["status"] == "ok"
    fremmed = _exec_read_tool_result({"result_id": rid,
                                      "_runtime_user_id": "mikkel"})
    assert fremmed["status"] == "error"


# ── redigeret metadata ───────────────────────────────────────────────────

def test_hemmeligheder_maskeres_i_ARGUMENTERNE():
    """62 af 84 fund laa her — typisk en curl med Authorization-header."""
    rid = S.save_tool_result("bash", {"command": HEMMELIG}, "ud")
    gemt = (S.TOOL_RESULTS_DIR / f"{rid}.json").read_text(encoding="utf-8")
    assert "abcdefghijklmnopqrstuvwxyz012345" not in gemt.split('"result"')[0]


def test_NYTTELASTEN_roeres_ikke():
    """Resultatet er ikke metadata. Jarvis skal kunne laese tilbage praecis
    det vaerktoejet svarede; nyttelasten beskyttes af roden og 0600."""
    rid = S.save_tool_result("bash", {"command": "ls"}, HEMMELIG)
    assert S.get_tool_result(rid)["result"] == HEMMELIG


def test_digesten_passer_stadig_efter_redigering():
    """Digesten er over nyttelasten. Maskeres metadata, maa den stadig holde."""
    rid = S.save_tool_result("bash", {"command": HEMMELIG}, "nyttelast")
    assert S.get_tool_result(rid)["verified"] is True


# ── private roedder og ejer-only filer ───────────────────────────────────

def test_roden_er_0700_og_filen_0600():
    rid = S.save_tool_result("bash", {"command": "ls"}, "ud")
    assert (S.TOOL_RESULTS_DIR.stat().st_mode & 0o777) == 0o700
    assert ((S.TOOL_RESULTS_DIR / f"{rid}.json").stat().st_mode & 0o777) == 0o600


def test_reparationen_saetter_0600_paa_gamle_filer():
    """30.495 laa som 0644. «I praksis daekket af roden» holder kun til nogen
    aabner roden — eller tager en backup der bevarer rettigheder."""
    rid = S.save_tool_result("bash", {"command": "ls"}, "ud")
    sti = S.TOOL_RESULTS_DIR / f"{rid}.json"
    os.chmod(sti, 0o644)
    ud = S.repair_permissions()
    assert ud["set"] >= 1 and ud["fejl"] == 0
    assert (sti.stat().st_mode & 0o777) == 0o600


def test_reparationen_foelger_ikke_symlinks(tmp_path):
    """En oprydning der foelger et link, aendrer noget andet end det den tror."""
    udenfor = tmp_path / "udenfor.json"
    udenfor.write_text("{}")
    os.chmod(udenfor, 0o644)
    S._sikr_privat_rod()
    link = S.TOOL_RESULTS_DIR / "link.json"
    link.symlink_to(udenfor)
    ud = S.repair_permissions()
    assert ud["sprunget"] >= 1
    assert (udenfor.stat().st_mode & 0o777) == 0o644
