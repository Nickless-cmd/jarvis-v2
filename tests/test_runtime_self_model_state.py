"""Tests for runtime_self_model_state — salience-integritet gennem mineness.

Koblingen blev flyttet 23/11-2026: `carried_integrity` kom fra
forgetting-kurven, hvis "baerende" poster primaert var daemon-telemetri
(tankestroem, nysgerrighed, refleksion) — en helt anden population end de
traade `carried_thread_count` taelles fra. Integriteten maales nu over den
aktive private-brain-population, som er den samme population traadene
kommer fra.

Testene maaler at tallet faktisk BAERES igennem kæden, og at en manglende
maaling ikke læses som glemsel.
"""

from __future__ import annotations

from core.services import runtime_self_model_state as rsm
from core.runtime import db_private_brain


def test_snapshot_baerer_salience_integriteten(monkeypatch) -> None:
    """Aggregatet skal ende i snapshot med sine egne tal — ikke kun et flag."""
    monkeypatch.setattr(
        db_private_brain,
        "private_brain_salience_stats",
        lambda: {"integrity": 0.42, "tracked": 1000, "faded": 580},
    )

    snapshot = rsm._mineness_source_snapshot()

    assert snapshot["brain_salience_integrity"] == 0.42
    assert snapshot["brain_salience_tracked"] == 1000
    assert snapshot["brain_salience_faded"] == 580


def test_manglende_maaling_maa_ikke_lases_som_glemsel(monkeypatch) -> None:
    """Fejler aggregatet, er integriteten 1.0 — ikke 0.

    En manglende maaling der falder tilbage paa 0 ville melde "alt er glemt"
    og drive laengslen mod quiet paa et datagrundlag der ikke findes.
    """

    def _boom() -> dict[str, object]:
        raise RuntimeError("aggregat utilgaengeligt")

    monkeypatch.setattr(db_private_brain, "private_brain_salience_stats", _boom)

    snapshot = rsm._mineness_source_snapshot()

    assert snapshot["brain_salience_integrity"] == 1.0
    assert snapshot["brain_salience_tracked"] == 0
    assert snapshot["brain_salience_faded"] == 0


def test_mineness_baerer_integriteten_videre_til_laengslen() -> None:
    """Mineness skal videresende integriteten under det navn laengslen laeser."""
    mineness = rsm._derive_mineness_ownership(
        experiential={},
        inner_voice={},
        support_stream={},
        temporal_feel={},
        sources={
            "brain_active": True,
            "brain_record_count": 6,
            "brain_salience_integrity": 0.31,
            "brain_salience_tracked": 720,
            "brain_salience_faded": 500,
        },
    )

    assert mineness["carried_salience_integrity"] == 0.31
    assert mineness["carried_salience_tracked"] == 720
    assert mineness["carried_salience_faded"] == 500


def test_manglende_integritet_i_sources_giver_ikke_null() -> None:
    """Uden maaling i sources skal mineness stadig melde intakt, ikke glemt."""
    mineness = rsm._derive_mineness_ownership(
        experiential={},
        inner_voice={},
        support_stream={},
        temporal_feel={},
        sources={},
    )

    assert mineness["carried_salience_integrity"] == 1.0
    assert mineness["carried_salience_tracked"] == 0
