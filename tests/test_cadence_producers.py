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
