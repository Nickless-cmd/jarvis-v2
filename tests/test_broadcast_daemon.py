"""Global Workspace-eksperimentet skal kunne FORKLARE sin tavshed.

## Hvad der var galt (18/9-2026)

Eksperimentet stod `enabled` i fem måneder med NUL udsendelser og så sundt ud
imens — `experiment_broadcast_events` havde 0 rækker.

Det var ikke ledningerne. Lytteren kører i samme proces som udgiverne
(begge services kører samme app; kun `JARVIS_ENABLE_RUNTIME_SERVICES` skiller
dem), event-navnene passer, og 172 kortlagte events fyrede alene på to dage.

Det er aritmetik: en udsendelse kræver TRE forskellige kilder i SAMME
emne-klynge, og kun fire kilde-typer udgiver overhovedet — med hvert sit
ordforråd. At tre af dem skulle lande i én klynge er nærmest udelukket.

Tærsklen er en HYPOTESE om hvad en bevidst udsendelse kræver, ikke en
indstilling. Den røres ikke her. Men «tændt, 0 events» læser som sundhed, og
«tændt, men ingen klynge nåede 3 kilder» er et svar.
"""
from __future__ import annotations

from core.services import broadcast_daemon as bd


def test_en_tom_tick_siger_HVORFOR_den_er_tom(monkeypatch):
    monkeypatch.setattr("core.runtime.db.get_experiment_enabled", lambda _id: True)
    monkeypatch.setattr("core.services.global_workspace.get_workspace_snapshot", lambda: [])
    monkeypatch.setattr("core.services.emotion_concepts.get_active_emotion_concepts", lambda: [])
    ud = bd.tick_broadcast_daemon()
    assert ud["broadcast_count"] == 0
    assert ud["silent_reason"], "tavsheden forklarede ikke sig selv"
    assert ud["threshold"] == bd._COHERENCE_THRESHOLD


def test_for_faa_kilder_forklares_med_TAL(monkeypatch):
    """Det er forskellen mellem «der skete ikke noget» og «der kan ikke ske
    noget med de kilder der findes»."""
    poster = [
        {"source": "surprise_daemon", "topic": "fejl i login", "signal_type": "x",
         "payload_summary": "", "timestamp": "2026-09-18T11:00:00+00:00"},
        {"source": "tool_pipeline", "topic": "fejl i login", "signal_type": "y",
         "payload_summary": "", "timestamp": "2026-09-18T11:00:01+00:00"},
    ]
    monkeypatch.setattr("core.runtime.db.get_experiment_enabled", lambda _id: True)
    monkeypatch.setattr("core.services.global_workspace.get_workspace_snapshot", lambda: poster)
    monkeypatch.setattr("core.services.emotion_concepts.get_active_emotion_concepts", lambda: [])
    ud = bd.tick_broadcast_daemon()
    assert ud["broadcast_count"] == 0
    assert ud["distinct_sources"] == 2
    assert ud["best_cluster_sources"] == 2
    assert "2" in ud["silent_reason"] and str(bd._COHERENCE_THRESHOLD) in ud["silent_reason"]


def test_fladen_baerer_grunden_uden_at_koere_en_ny_analyse(monkeypatch):
    monkeypatch.setattr("core.services.global_workspace.get_workspace_snapshot", lambda: [])
    flade = bd.build_workspace_surface()
    assert flade["silent_reason"]


def test_taersklen_roeres_IKKE():
    """Den er en hypotese om hvad en bevidst udsendelse kraever. At saenke den
    for at faa tal paa skaermen ville vaere at aendre forsoeget for at faa et
    resultat."""
    assert bd._COHERENCE_THRESHOLD == 3
