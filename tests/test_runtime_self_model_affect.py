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
    ls["carried_integrity"] = 0.1
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
    ls["carried_integrity"] = 1.0
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
