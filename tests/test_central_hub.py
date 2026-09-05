"""Tests for central_hub — Jarvis Mind-projektions-hub (ét ground truth)."""
from __future__ import annotations

import pytest

from core.services import central_hub as h


@pytest.fixture(autouse=True)
def _clear_section_cache():
    """Hub'en cacher sektioner 12s — ryd mellem tests så monkeypatch'ede bygger ses."""
    h._section_cache.clear()
    yield
    h._section_cache.clear()


def test_index_lists_all_sections():
    idx = h.mind_index()
    keys = [s["section"] for s in idx]
    assert "overview" in keys and "mind" in keys and "observability" in keys
    # 2026-09-05: var et magisk 10-tal og faldt da «decisions» kom til. Tæller
    # nu mod den faktiske sektionsliste, så en ny fane ikke braekker testen —
    # den skal fange at en fane FORSVINDER, ikke at der kommer en til.
    from core.services.central_hub import _SECTION_ORDER
    assert len(idx) == len(_SECTION_ORDER)
    assert "decisions" in keys
    # ready-flag matcher byggerne (udvides efterhånden som faner fyldes)
    ready = {s["section"] for s in idx if s["ready"]}
    assert {"overview", "mind", "observability"} <= ready
    # 2026-09-05: var "council", men den fik en bygger uden at testen fulgte med
    # — den har fejlet i et stykke tid. Bruger nu en fane der faktisk er pending.
    assert "hardening" not in ready  # endnu pending


def test_pending_section_is_marked_not_error():
    r = h.mind_section("hardening")
    assert r["pending"] is True and r["active"] is False
    assert "error" not in r


def test_unknown_section_is_error():
    r = h.mind_section("frobnicate")
    assert r.get("error") and r["active"] is False


def test_section_is_self_safe_on_builder_crash(monkeypatch):
    # en byggers fejl må aldrig vælte hub'en — sektionen returnerer {error}
    monkeypatch.setitem(h._BUILDERS, "mind",
                        lambda: (_ for _ in ()).throw(RuntimeError("surface nede")))
    r = h.mind_section("mind")
    assert "surface nede" in r["error"] and r["active"] is False
    assert r["section"] == "mind"


def test_snapshot_default_is_index_only():
    snap = h.mind_snapshot()
    assert "index" in snap and snap["sections"] == {}
    snap2 = h.mind_snapshot(sections=["overview"])
    assert "overview" in snap2["sections"]


def test_overview_reads_central_pulse(monkeypatch):
    import core.services.central_realtime as cr
    monkeypatch.setattr(cr, "realtime_snapshot",
                        lambda **k: {"status": "green", "coverage": {"nerves": 5},
                                     "diagnose": {}, "processes": [], "clusters": []})
    r = h.mind_section("overview")
    assert r["status"] == "green" and r["coverage"]["nerves"] == 5 and r["active"] is True


# ---------------------------------------------------------------------------
# Beslutninger skal nå et menneske
#
# Målt 2026-09-05: 48 initiativer i køen — 6 ventende, 26 udløbet uden svar,
# NUL nogensinde godkendt eller afvist. Ruterne fandtes
# (/mc/initiatives/{id}/approve|reject, /mc/life-projects/{id}/abandon) — der
# var bare ingen knap nogen steder. Han spurgte 48 gange og fik intet svar,
# fordi spørgsmålet aldrig nåede et menneske.
# ---------------------------------------------------------------------------


def test_beslutninger_er_en_sektion_i_hubben():
    from core.services.central_hub import mind_index

    sektioner = [s["section"] for s in mind_index()]
    assert "decisions" in sektioner, (
        "beslutnings-sektionen mangler — så er køen usynlig igen"
    )
    # Den skal ligge tidligt: den kræver handling, modsat de øvrige som informerer.
    assert sektioner.index("decisions") <= 2


def test_sektionen_projicerer_baade_initiativer_og_livsprojekter():
    from core.services.central_hub import mind_section

    d = mind_section("decisions")
    assert d.get("active") is True
    assert "items" in d and isinstance(d["items"], list)
    for i in d["items"]:
        assert i.get("kind") in ("initiative", "life_project")
        assert i.get("id"), "en post uden id kan man ikke svare på"
        assert i.get("actions"), "en post uden handlinger er ikke en beslutning"


def test_ubesvarede_taelles_og_naevnes():
    """Tallet der gør ondt skal stå i svaret, ikke skulle graves frem."""
    from core.services.central_hub import mind_section

    d = mind_section("decisions")
    koe = d.get("queue") or {}
    assert "expired_unanswered" in koe
    if int(koe.get("expired_unanswered") or 0) > 0:
        assert "udloebet uden svar" in str(d.get("unanswered_note") or "")


def test_sektionen_er_selvsikker_mod_en_doed_kilde(monkeypatch):
    """En fejl i én kilde må ikke koste hele sektionen."""
    from core.services import central_hub as H

    monkeypatch.setattr(
        "core.services.initiative_queue.get_initiative_queue_state",
        lambda: (_ for _ in ()).throw(RuntimeError("nede")),
    )
    d = H._build_decisions()
    assert d.get("active") is True
    assert isinstance(d.get("items"), list)


def test_gammelt_skrald_vises_ikke_som_beslutning(monkeypatch):
    """Porten stopper nye poster ved kilden — men køen rummer stadig det der
    blev gemt før den fandtes. Det må ikke stå foran et menneske."""
    from core.services import central_hub as H

    monkeypatch.setattr(
        "core.services.initiative_queue.get_initiative_queue_state",
        lambda: {"pending": [
            {"initiative_id": "a", "focus": "Use JSON format with thought, initiative"},
            {"initiative_id": "b", "focus": "What might the next move be?"},
            {"initiative_id": "c", "focus": "Ryd op i de temporale kanter i brain-grafen"},
        ], "pending_count": 3, "expired_count": 0},
    )
    monkeypatch.setattr(
        "core.services.life_projects.build_life_projects_surface", lambda: {"items": []},
    )
    d = H._build_decisions()
    tekster = [i["text"] for i in d["items"]]
    assert tekster == ["Ryd op i de temporale kanter i brain-grafen"]
