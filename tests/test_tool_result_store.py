"""Fuldstændighed er et FELT, ikke en note i teksten.

DeepSeek-harness-spec'ens Gap J: «relies on ambient file permissions, clips the
value advertised as full output, and does not make authority, completeness,
retention, provenance, and retrieval separate contracts».

Verificeret 8/9-2026: klipningen ER synlig for et menneske — `clip_head_tail`
splejser «… [N tegn udeladt …] …» ind i teksten. Men en programmatisk læser
skulle parse dansk prosa for at vide om den havde hele outputtet. Nu er det en
maskinlæsbar kendsgerning.
"""
from __future__ import annotations

import core.services.tool_result_store as store


def test_et_lille_resultat_er_komplet(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "TOOL_RESULTS_DIR", tmp_path)
    rid = store.save_tool_result("bash", {"command": "ls"}, "kort output")
    data = store.get_tool_result(rid)
    assert data is not None
    assert data["complete"] is True
    assert data["original_chars"] == len("kort output")
    assert data["stored_chars"] == data["original_chars"]


def test_et_klippet_resultat_siger_det_i_et_FELT(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "TOOL_RESULTS_DIR", tmp_path)
    monkeypatch.setattr(store, "_MAX_STORED_CHARS", 500)
    raa = "linje\n" * 400
    rid = store.save_tool_result("bash", {}, raa)
    data = store.get_tool_result(rid)
    assert data is not None
    assert data["complete"] is False
    assert data["original_chars"] == len(raa)
    assert data["stored_chars"] < data["original_chars"]


def test_klipningen_er_stadig_synlig_i_teksten(tmp_path, monkeypatch):
    """Feltet ERSTATTER ikke noten. Et menneske der læser resultatet skal stadig
    kunne se at der mangler noget, uden at slå metadata op."""
    monkeypatch.setattr(store, "TOOL_RESULTS_DIR", tmp_path)
    monkeypatch.setattr(store, "_MAX_STORED_CHARS", 500)
    rid = store.save_tool_result("bash", {}, "linje\n" * 400)
    data = store.get_tool_result(rid)
    assert data is not None
    assert "udeladt" in str(data["result"])


def test_gamle_poster_uden_felterne_siger_UKENDT_ikke_ufuldstaendig(tmp_path, monkeypatch):
    """Et manglende felt må ikke læses som «ufuldstændig» — vi ved det ikke, og
    at gætte ville gøre gammelt, komplet output mistænkeligt."""
    import json
    monkeypatch.setattr(store, "TOOL_RESULTS_DIR", tmp_path)
    gammel = tmp_path / "gammel.json"
    gammel.write_text(json.dumps({"result_id": "gammel", "result": "noget"}), encoding="utf-8")
    data = store.get_tool_result("gammel")
    assert data is not None
    assert data["complete"] is None
    assert data["original_chars"] is None


def test_et_ukendt_id_giver_None(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "TOOL_RESULTS_DIR", tmp_path)
    assert store.get_tool_result("findes-ikke") is None


# ── Hoved OG hale, ikke kun hoved (30/9-2026) ────────────────────────────────
#
# Afkortningen var `normalized[: max_chars - 1] + "…"` — halen blev droppet. For
# et `bash`-resultat er halen oftest SVARET: exit-status, den sidste linje,
# tallet man bad om. Målt på en faktisk request var `bash` to tredjedele af alt
# værktøjs-output i prompten, så det er netop dér formen betyder noget.
#
# Samme princip som desk fik samme dag: hoved, hale, og en notits der siger hvor
# meget der mangler — så modellen VED der er mere i stedet for at tro at
# outputtet stopper.

from core.services.tool_result_store import render_tool_result_for_prompt as _render

_LANGT = "START-KOMMANDO" + ("x" * 3000) + "-SIDSTE-LINJE-EXITKODE-0"


def test_halen_bevares():
    """Kernen. Svaret staar til sidst i et kommando-output."""
    ud = _render(_LANGT, expand=False, max_chars=400)
    assert ud.endswith("EXITKODE-0"), ud[-60:]
    assert ud.startswith("START-KOMMANDO"), ud[:40]


def test_notitsen_siger_hvor_meget_der_mangler():
    """Uden den tror modellen at outputtet stopper dér."""
    ud = _render(_LANGT, expand=False, max_chars=400)
    assert "udeladt" in ud, ud


def test_budgettet_overholdes():
    """Notitsen skal regnes MED, ellers spraenger afkortningen sit eget loft."""
    for budget in (200, 400, 1200, 1500):
        ud = _render(_LANGT, expand=False, max_chars=budget)
        assert len(ud) <= budget, f"budget {budget}, fik {len(ud)}"


def test_kort_indhold_roeres_ikke():
    """Kontrollen. Uden den kunne testene ovenfor bestaa paa en funktion der
    ALTID klipper — og saa forsvandt korte resultater ogsaa."""
    kort = "kun lidt tekst"
    assert _render(kort, expand=False, max_chars=400) == kort


def test_det_er_DETERMINISTISK():
    """Gengivelsen skal vaere byte-identisk tur efter tur, ellers braekker den
    praefiks-cachen — hele grunden til at budgettet er fast (se kommentaren i
    `transcript_sections`)."""
    a = _render(_LANGT, expand=False, max_chars=400)
    b = _render(_LANGT, expand=False, max_chars=400)
    assert a == b


def test_et_bittesmaa_budget_falder_tilbage_til_hoved_kun():
    """En hale paa tre tegn oplyser ingen. Under graensen er hoved-kun aerligere
    end en notits der fylder mere end det den beskriver."""
    ud = _render(_LANGT, expand=False, max_chars=60)
    assert len(ud) <= 60
    assert ud.startswith("START")
