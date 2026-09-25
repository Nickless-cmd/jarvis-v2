"""Minimal tests for cadence_producers (coverage-gate + B-batch-2 observe smoke).

Den tunge produce_signals_from_run rører DB + mange daemons; her dækker vi import +
hjælpere + at heartbeat-producer-observe-nerven er registreret.
"""
from __future__ import annotations


def test_module_imports():
    from core.services import cadence_producers as cp
    assert hasattr(cp, "produce_signals_from_run")


def test_meaningful_run_topic_is_str():
    from core.services.cadence_producers import _meaningful_run_topic
    out = _meaningful_run_topic("Jarvis kører på localhost nu")
    assert isinstance(out, str)


def test_cadence_producers_nerve_in_catalog():
    from core.services import central_catalog as cc
    names = [n.name for n in cc.by_cluster("stream")]
    assert "cadence_producers" in names
    assert "notification_route" in names


def test_tick_frozen_detectors_cadence(isolated_runtime):
    # LivingNeuron Fase B: emergence hver 30., contradiction hver 20., ellers no-op. Self-safe.
    from core.services.cadence_producers import tick_frozen_detectors
    off = tick_frozen_detectors(7)   # hverken 15, 20 el. 30
    assert off == {"emergence": 0, "contradiction": 0}
    both = tick_frozen_detectors(60)  # 15, 20 OG 30 → emergence+contradiction+boredom
    assert {"emergence", "contradiction"} <= set(both)
    assert both.get("boredom") == 1
    # må aldrig kaste selv på skæve tal
    tick_frozen_detectors(0)
    tick_frozen_detectors(20)
    tick_frozen_detectors(30)


# ---------------------------------------------------------------------------
# Verdensmodellen skal kunne merge — ellers er den en logfil
#
# canonical_key var `world-model:run:{run_id}` — unik pr. tur. Merge-opslaget
# sker PÅ canonical_key, så det kunne aldrig finde en eksisterende række. Hver
# tur gav en ny `active` post, og tabellen voksede til 16.747 rækker hvor 16.746
# var samme boilerplate. 16.707 af dem kunne ikke nås af nogen kodesti.
# ---------------------------------------------------------------------------


def _kilde() -> str:
    import inspect

    from core.services import cadence_producers

    return inspect.getsource(cadence_producers)


def test_verdensmodellen_noegles_paa_emne_ikke_paa_run():
    kilde = _kilde()
    assert 'canonical_key=f"world-model:topic:{topic_slug}"' in kilde, (
        "verdensmodellens canonical_key er ikke emne-baseret — så kan merge "
        "aldrig finde en eksisterende antagelse"
    )
    assert 'canonical_key=f"world-model:run:{run_id}"' not in kilde, (
        "run_id er tilbage i canonical_key — det gør nøglen unik pr. tur og "
        "gør tabellen til en append-only kopi af chat-loggen"
    )


def test_verdensmodellen_gates_paa_at_der_ER_et_emne():
    """En triviel besked («ok», «tak») er ikke en antagelse om verden."""
    import re

    kilde = _kilde()
    i = kilde.find('canonical_key=f"world-model:topic:{topic_slug}"')
    assert i > 0
    foran = kilde[max(0, i - 600):i]
    assert re.search(r"if\s+topic_slug\s*:", foran), (
        "world-model-blokken er ikke gatet på topic_slug"
    )


def test_titlen_er_emnet_ikke_brugerens_raa_besked():
    """Titlen blev serveret tilbage som «dominerende verdenstråd» — altså hans
    samtalepartners sidste sætning præsenteret som en uafhængig observation."""
    kilde = _kilde()
    i = kilde.find('canonical_key=f"world-model:topic:{topic_slug}"')
    blok = kilde[i:i + 900]
    assert "title=meaningful_topic[:80]" in blok
    assert "title=user_message[:80]" not in blok


def test_fladen_viser_HELE_registret_ikke_en_frossen_liste():
    """15/9-2026: fladen viste 11 haardkodede navne mod 119 registrerede."""
    from core.services import internal_cadence as ic
    from core.services.cadence_producers import build_cadence_producers_surface

    ic._ensure_producers_registered()
    flade = build_cadence_producers_surface()

    assert flade["antal"] == len(ic._producers)
    assert set(flade["producers"]) == set(ic._producers)
    assert len(flade["producers"]) > 11
    # Formen er uaendret for eksisterende laesere, og grafen staar der stadig.
    assert all(isinstance(n, str) for n in flade["producers"])
    assert "afhaengighedsgraf" in flade
    detalje = flade["producer_detaljer"][0]
    assert {"name", "priority", "cooldown_minutes", "depends_on"} <= set(detalje)


# ── Droemme-hypotesens EMNE (25/9-2026) ──────────────────────────────────
#
# Indtil i dag skrev 13e `dream:topic:{slug af Bjoerns besked}`. Droemme-kaeden
# foejer paa emne — hypotese moeder maal eller fokus i SAMME emne — saa en
# samtale-slug kan aldrig moede noget. Maalt i produktionen: 42 hypoteser paa
# den form siden 9/6, nul adoptions-kandidater, og de fyldte alle tolv pladser
# i overfladen saa de fire med et rigtigt emne ikke kunne ses.

def _opsaet(monkeypatch, domaene):
    """Fang hypoteserne og bestem hvad domaene-opslaget svarer."""
    import core.services.cadence_producers as CP
    import core.services.dream_domains as DD
    fanget: list[dict] = []
    monkeypatch.setattr(CP, "upsert_runtime_dream_hypothesis_signal",
                        lambda **kw: fanget.append(kw) or kw)
    monkeypatch.setattr(DD, "domaene_for_tur", lambda t, **kw: domaene)
    monkeypatch.setattr("core.services.living_heartbeat_cycle.determine_life_phase",
                        lambda: {"phase": "dreaming"})
    return fanget


def test_emnet_er_domaenet_ikke_beskeden(monkeypatch):
    import core.services.cadence_producers as CP
    fanget = _opsaet(monkeypatch, "memory")
    CP.produce_signals_from_run(
        run_id="r0", session_id="s1",
        # Skal igennem stoejfilteret foerst: det kraever tekniske signalord.
        user_message="din hukommelse paa tvaers af sessioner i runtime holder ikke",
        assistant_response="ok", outcome_status="completed")
    noegler = [k["canonical_key"] for k in fanget]
    assert noegler == ["dream-hypothesis:post_run_hypothesis:memory"], noegler


def test_uden_domaene_skrives_der_INGEN_hypotese(monkeypatch):
    """DEN fejl. Ordret fra produktionen — den blev til
    `dream:topic:vis-mig-de-to-nye-commits-fra-claude.`"""
    import core.services.cadence_producers as CP
    fanget = _opsaet(monkeypatch, None)
    CP.produce_signals_from_run(
        run_id="r0", session_id="s1",
        user_message="vis mig de to nye commits fra claude og kør testene",
        assistant_response="ok", outcome_status="completed")
    assert fanget == [], (
        f"en samtale-slug blev skrevet som emne igen: "
        f"{[k['canonical_key'] for k in fanget]}")
