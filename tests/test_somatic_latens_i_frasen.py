"""Kropslagets latens skal nå en flade — også i raw-signal-mode.

Målt 7/11-2026: ``track_request`` fodrede ``_latency_samples``, og
``_collect_snapshot`` lagde gennemsnittet i ``snapshot["latency_ms"]`` — men
``_build_raw_phrase`` (den gren der faktisk kører når ``raw_signal_mode`` er
tændt) læste det aldrig. Målingen fandtes, men nåede ingen flade.

Disse tests kører produktionens indgang (``tick_somatic_daemon``) og måler at
latensen står i den frase der gemmes. Fjernes latens-feltet fra
``_build_raw_phrase``, fejler de.
"""

from __future__ import annotations

import pytest

from core.services import somatic_daemon


@pytest.fixture()
def raw_mode(monkeypatch):
    """Tving raw-signal-mode til — det er den gren der kører i drift."""
    monkeypatch.setattr(somatic_daemon, "raw_signal_mode_enabled", lambda: True)
    monkeypatch.setattr(somatic_daemon, "_heartbeat_count_since_gen", 0)
    monkeypatch.setattr(somatic_daemon, "_last_energy_level", "")
    monkeypatch.setattr(somatic_daemon, "_last_cpu_pct", 0.0)
    monkeypatch.setattr(somatic_daemon, "_last_latency_ms", 0.0)
    monkeypatch.setattr(somatic_daemon, "_latency_samples", [])
    monkeypatch.setattr(somatic_daemon, "_cached_phrase", "")
    # Frasen skal ikke skrives til DB i testen — kun bygges og returneres.
    monkeypatch.setattr(somatic_daemon, "_store_phrase", lambda phrase, snap: None)
    return monkeypatch


def test_raw_phrase_baerer_latens_naar_der_har_vaeret_et_kald(raw_mode):
    """Et målt modelkald skal kunne ses i kropsfrasen."""
    somatic_daemon.record_latency_sample(340.0)

    result = somatic_daemon.tick_somatic_daemon(energy_level="høj")

    assert result["generated"] is True
    assert "svar 340ms" in result["phrase"], (
        f"latensen nåede ikke frasen: {result['phrase']!r}"
    )


def test_raw_phrase_udelader_latens_uden_kald(raw_mode):
    """Uden samples må frasen ikke påstå 0ms — feltet skal udelades."""
    result = somatic_daemon.tick_somatic_daemon(energy_level="høj")

    assert result["generated"] is True
    assert "svar" not in result["phrase"], (
        f"frasen påstår en latens der ikke er målt: {result['phrase']!r}"
    )


def test_track_request_fodrer_snapshot_og_frase(raw_mode):
    """Produktionens omslutning skal ende i frasen — ikke kun i en intern liste."""
    with somatic_daemon.track_request():
        pass

    assert somatic_daemon._latency_samples, "track_request målte intet"

    result = somatic_daemon.tick_somatic_daemon(energy_level="høj")

    assert result["generated"] is True
    assert "svar " in result["phrase"], (
        f"track_request's måling nåede ikke frasen: {result['phrase']!r}"
    )
