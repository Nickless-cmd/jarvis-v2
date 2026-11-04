"""Tests for counterfactual → verdensmodel-bindingen.

Fokus (4/11-2026): `_extract_event_kind` er den ene søm der afgør om en
forudsigelse kan efterprøves. Den læste kun en evidence-streng; nu læser den
feltet først, så en forudsigelse skrevet med `event_kind=` også kan afgøres.
Begge veje skal virke — den gamle, så historikken ikke mister sin betydning,
og den nye, så feltet faktisk bruges.
"""
from __future__ import annotations

from core.services.counterfactual_predictions import (
    _extract_event_kind,
    _frequency_verdict,
    _is_horizon_expired,
)
from datetime import UTC, datetime, timedelta


def test_extract_laeser_feltet_foerst():
    pred = {"event_kind": "tool.completed", "evidence": ["event_kind:anden.kind"]}
    assert _extract_event_kind(pred) == "tool.completed", (
        "feltet skal vinde over evidence-strengen — det er den ærlige datamodel"
    )


def test_extract_falder_tilbage_paa_evidence_strengen():
    """Gamle forudsigelser har kun strengen. De må ikke miste deres betydning."""
    pred = {"evidence": ["counterfactual:cf-1", "event_kind:goal.updated"]}
    assert _extract_event_kind(pred) == "goal.updated"


def test_extract_uden_begge_dele_giver_tom():
    assert _extract_event_kind({"evidence": ["counterfactual:cf-1"]}) == ""
    assert _extract_event_kind({}) == ""


def test_verdict_uden_event_kind_gaetter_ikke():
    """Den ærlige halvdel: uden kind kan frekvensen ikke sammenlignes."""
    v = _frequency_verdict(event_kind="", created_at=datetime.now(UTC))
    assert v["outcome"] == "uncertain"
    assert v["reason"] == "no-event-kind-tag-on-prediction"


def test_horisonten_skal_vaere_udloebet():
    now = datetime.now(UTC)
    gammel = {"created_at": (now - timedelta(days=9)).isoformat()}
    frisk = {"created_at": (now - timedelta(days=1)).isoformat()}
    assert _is_horizon_expired(gammel, now) is True
    assert _is_horizon_expired(frisk, now) is False
