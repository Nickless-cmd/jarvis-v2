"""Tests for runtime_self_model_state — henfaldet paa det baarne.

Koblingen blev flyttet TO gange 23/11-2026, og den anden flytning er den
vigtige. Foerst laeste laengslen `forgetting_curve.carried_integrity()`, hvis
"baerende" population var 294 af 369 daemon-telemetri. Saa blev den flyttet til
`private_brain_salience_stats()` — men det tal er et GENNEMSNIT over 72.297
poster hvoraf 60.090 staar paa praecis 1.0, saa det bliver 0.985 uanset hvor
meget der er faldet og kan aldrig give `fading`.

Den endelige kilde er forgetting-kurven med daemon-telemetrien filtreret vaek:
0.531 over 111 reelt relationelle poster. Testene her maaler at tallet BAERES
igennem kaeden, at en manglende maaling ikke laeses som glemsel, og at filteret
faktisk holder telemetrien ude.
"""

from __future__ import annotations

from core.services import runtime_self_model_state as rsm
from core.services import forgetting_curve


def test_snapshot_baerer_henfaldet(monkeypatch) -> None:
    """Aggregatet skal ende i snapshot med sine egne tal — ikke kun et flag."""
    monkeypatch.setattr(
        forgetting_curve,
        "carried_integrity",
        lambda: {"integrity": 0.42, "tracked": 111, "faded": 31},
    )

    snapshot = rsm._mineness_source_snapshot()

    assert snapshot["carried_decay_integrity"] == 0.42
    assert snapshot["carried_decay_tracked"] == 111
    assert snapshot["carried_decay_faded"] == 31


def test_manglende_maaling_maa_ikke_lases_som_glemsel(monkeypatch) -> None:
    """Fejler maalingen, er integriteten 1.0 — ikke 0.

    En manglende maaling der faldt tilbage paa 0 ville melde "alt er glemt" og
    drive laengslen mod quiet paa et datagrundlag der ikke findes.
    """

    def _boom() -> dict[str, object]:
        raise RuntimeError("kurven utilgaengelig")

    monkeypatch.setattr(forgetting_curve, "carried_integrity", _boom)

    snapshot = rsm._mineness_source_snapshot()

    assert snapshot["carried_decay_integrity"] == 1.0
    assert snapshot["carried_decay_tracked"] == 0
    assert snapshot["carried_decay_faded"] == 0


def test_mineness_baerer_henfaldet_videre_til_laengslen() -> None:
    """Mineness skal videresende tallet under det navn laengslen laeser."""
    mineness = rsm._derive_mineness_ownership(
        experiential={},
        inner_voice={},
        support_stream={},
        temporal_feel={},
        sources={
            "brain_active": True,
            "brain_record_count": 6,
            "carried_decay_integrity": 0.31,
            "carried_decay_tracked": 111,
            "carried_decay_faded": 60,
        },
    )

    assert mineness["carried_decay_integrity"] == 0.31
    assert mineness["carried_decay_tracked"] == 111
    assert mineness["carried_decay_faded"] == 60


def test_manglende_integritet_i_sources_giver_ikke_null() -> None:
    """Uden maaling i sources skal mineness melde intakt, ikke glemt."""
    mineness = rsm._derive_mineness_ownership(
        experiential={},
        inner_voice={},
        support_stream={},
        temporal_feel={},
        sources={},
    )

    assert mineness["carried_decay_integrity"] == 1.0
    assert mineness["carried_decay_tracked"] == 0


def test_daemon_telemetri_taelles_ikke_som_baerende() -> None:
    """Filteret skal holde de kilder ude hvis henfald ikke er glemsel.

    Uden dette filter var 294 af 369 "baerende" poster telemetri, og
    integriteten maalte henfald af en tankestroem — ikke af noget man kan
    laenges efter.
    """
    for kilde in (
        "thought-stream-daemon:heartbeat",
        "curiosity-daemon:thought-stream",
        "reflection-cycle-daemon:heartbeat",
        "meta-reflection-daemon:heartbeat",
        "somatic-daemon:heartbeat",
    ):
        assert not forgetting_curve._is_carried({"source": kilde}), kilde

    # Indhold om mig/relationen skal stadig taelle med.
    for kilde in ("diary:diary-synthesis-abc", "self-model:sm-123", "absence-daemon"):
        assert forgetting_curve._is_carried({"source": kilde}), kilde
