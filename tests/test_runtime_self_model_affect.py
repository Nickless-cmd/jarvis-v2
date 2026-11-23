"""Tests for runtime_self_model_affect — glemsel som vaegt paa det baarne.

Koblingen er med vilje den MODSATTE af «glemsel foeder frygt»: falder
integriteten af det baarne, falder grundlaget for laengslen. Testene maaler
at glemslen faktisk AENDRER tilstanden — ikke bare at feltet findes.
"""
from __future__ import annotations

from tests.test_runtime_self_model import _longing_inputs






def test_longing_fading_when_carried_thread_thins_out() -> None:
    """Tyndslidt baerende spor skal melde fading, ikke missing."""
    from core.services.runtime_self_model import _derive_longing_awareness

    tf, mn, ss, iv, src, ls = _longing_inputs(
        ownership_state="held",
        carried_thread_count=1,
        open_loop_count=1,
        absence_active=True,
    )
    ls["carried_integrity"] = 0.5
    ls["carried_tracked"] = 40
    ls["carried_faded"] = 12
    # Kilden er flyttet (23/11-2026): henfaldet maales paa de brain-poster som
    # `carried_thread_count` selv taelles fra, saa tallet hoerer i `mineness`.
    mn["carried_decay_integrity"] = 0.5
    mn["carried_decay_tracked"] = 40
    mn["carried_decay_faded"] = 12
    longing = _derive_longing_awareness(
        temporal_feel=tf,
        mineness=mn,
        support_stream=ss,
        inner_voice=iv,
        sources=src,
        longing_sources=ls,
    )
    assert longing["longing_state"] == "fading"
    assert longing["absence_relation"] == "fading-from-absence"
    assert longing["longing_source"] == "fading-thread"
    assert "thinning" in longing["narrative"]
    assert longing["carried_integrity"] == 0.5


def test_longing_quiet_when_carried_content_is_gone() -> None:
    """Er indholdet vaek, er der intet at laenges EFTER — grundlaget taeller ikke."""
    from core.services.runtime_self_model import _derive_longing_awareness

    tf, mn, ss, iv, src, ls = _longing_inputs(
        ownership_state="held",
        carried_thread_count=1,
        open_loop_count=1,
        absence_active=True,
    )
    mn["carried_decay_integrity"] = 0.1
    longing = _derive_longing_awareness(
        temporal_feel=tf,
        mineness=mn,
        support_stream=ss,
        inner_voice=iv,
        sources=src,
        longing_sources=ls,
    )
    assert longing["longing_state"] == "quiet"
    assert longing["narrative"] == ""


def test_longing_unchanged_when_carried_content_is_intact() -> None:
    """Frisk kurve maa ikke aendre noget — koblingen skal vaere en vaegt, ikke en ny tilstand."""
    from core.services.runtime_self_model import _derive_longing_awareness

    tf, mn, ss, iv, src, ls = _longing_inputs(
        ownership_state="held",
        carried_thread_count=1,
        open_loop_count=1,
        absence_active=True,
    )
    mn["carried_decay_integrity"] = 1.0
    longing = _derive_longing_awareness(
        temporal_feel=tf,
        mineness=mn,
        support_stream=ss,
        inner_voice=iv,
        sources=src,
        longing_sources=ls,
    )
    assert longing["longing_state"] == "missing"
    assert longing["longing_source"] == "carried-thread"


def test_carried_integrity_empty_registry_is_not_forgetting() -> None:
    """Tom kurve = 1.0. En manglende maaling maa ikke laeses som glemsel."""
    from core.services import forgetting_curve

    out = forgetting_curve.carried_integrity()
    assert out["integrity"] == 1.0
    assert out["source"] == "empty-registry"


def test_carried_integrity_reads_decay_scores(monkeypatch) -> None:
    """Integriteten skal komme fra de faktiske decay-scores, ikke fra et antal."""
    from core.services import forgetting_curve

    monkeypatch.setattr(
        forgetting_curve,
        "_load",
        lambda: {
            "a": {"decay_score": 0.0},
            "b": {"decay_score": 0.5},
            "c": {"decay_score": 0.95},
        },
    )
    out = forgetting_curve.carried_integrity()
    assert out["tracked"] == 3
    assert out["faded"] == 1
    assert abs(out["integrity"] - (1.0 - 1.45 / 3)) < 1e-6


def test_carried_integrity_ignores_telemetry_sources(monkeypatch) -> None:
    """Soma-telemetri og state-snapshots maa ikke veje i laengslens grundlag.

    Maalt 23/11-2026: kurven sporer cpu/load/svartid og raa tilstandssnapshots,
    og de udgjorde flertallet af posterne. Et globalt gennemsnit gjorde derfor
    «CPU-temperaturen er faldet til ro» til «det jeg laenges efter er vaek».
    """
    from core.services import forgetting_curve

    monkeypatch.setattr(
        forgetting_curve,
        "_load",
        lambda: {
            "soma1": {"decay_score": 0.99, "source": "somatic-daemon:heartbeat"},
            "snap1": {"decay_score": 0.99, "source": "state-snapshot:private-x"},
            "tick1": {"decay_score": 0.99, "source": "signal_pressure_accumulator.tick"},
            "surp1": {"decay_score": 0.99, "source": "surprise-daemon:heartbeat"},
            "carried1": {"decay_score": 0.0, "source": "inner-voice-daemon:cadence"},
        },
    )
    out = forgetting_curve.carried_integrity()
    assert out["tracked"] == 1, "kun den baerende post maa taelle"
    assert out["tracked_all"] == 5, "totalen skal stadig kunne ses"
    assert out["faded"] == 0
    assert out["integrity"] == 1.0


def test_carried_integrity_no_carried_entries_is_not_forgetting(monkeypatch) -> None:
    """Kurve fuld af KUN telemetri = intet at maale, ikke alt tabt."""
    from core.services import forgetting_curve

    monkeypatch.setattr(
        forgetting_curve,
        "_load",
        lambda: {"s1": {"decay_score": 0.99, "source": "somatic-daemon:heartbeat"}},
    )
    out = forgetting_curve.carried_integrity()
    assert out["integrity"] == 1.0
    assert out["source"] == "no-carried-entries"
    assert out["tracked"] == 0
    assert out["tracked_all"] == 1


def test_longing_state_is_logged_when_it_changes(caplog) -> None:
    """Tilstanden skal kunne ses i journalen — og kun ved SKIFT.

    Uden dette findes mekanikken kun som et internt felt ingen kan efterproeve:
    «fading» blev beregnet korrekt, men skrevet til ingen log. Testen maaler baade
    at skiftet logges OG at gentagne kald med samme tilstand tier.
    """
    import logging

    import core.services.runtime_self_model as rsm
    from core.services import runtime_self_model_affect as aff

    aff._last_logged_longing_state = ""

    tf = {"temporal_state": "immediate", "return_signal": False}
    mn = {
        "ownership_state": "ambient",
        "self_relevance": "merely-present",
        "carried_thread_count": 1,
        "carried_decay_integrity": 0.496,
        "carried_decay_faded": 117,
        "carried_decay_tracked": 500,
    }
    ss = {"stream_state": "baseline", "voice_mode": ""}
    iv = {"inner_voice_created": False, "mode": ""}

    faded = {
        "absence_active": True,
        "idle_hours": 4.0,
        "carried_threads": 1,
    }

    with caplog.at_level(logging.INFO, logger="core.services.runtime_self_model_affect"):
        rsm._derive_longing_awareness(
            temporal_feel=tf, mineness=mn, support_stream=ss, inner_voice=iv,
            sources={}, longing_sources=faded,
        )
        first = [r for r in caplog.records if "state=fading" in r.getMessage()]
        assert len(first) == 1, "skiftet til fading skal logges praecis én gang"

        # Samme tilstand igen: ingen ny linje.
        rsm._derive_longing_awareness(
            temporal_feel=tf, mineness=mn, support_stream=ss, inner_voice=iv,
            sources={}, longing_sources=faded,
        )
        again = [r for r in caplog.records if "state=fading" in r.getMessage()]
        assert len(again) == 1, "gentaget kald med samme tilstand maa ikke logge"

    # Nyt skift skal igen give en linje.
    intact = dict(mn)
    intact["carried_decay_integrity"] = 0.95
    intact["carried_decay_faded"] = 12
    with caplog.at_level(logging.INFO, logger="core.services.runtime_self_model_affect"):
        rsm._derive_longing_awareness(
            temporal_feel=tf, mineness=intact, support_stream=ss, inner_voice=iv,
            sources={}, longing_sources=faded,
        )
        shifted = [r for r in caplog.records if "state=missing" in r.getMessage()]
        assert len(shifted) == 1, "et nyt skift skal logges"

    aff._last_logged_longing_state = ""
