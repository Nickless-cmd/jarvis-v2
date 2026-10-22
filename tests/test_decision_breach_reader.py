"""Breach-læseren — den manglende anden halvdel af sløjfen.

Målt 22/10-2026: `decision_breach_recent` blev skrevet og aldrig læst. Disse
tests vogter at læseren (a) aggregerer inden for vinduet, (b) skiller
EKSEKVERBAR / MÅLBAR / EFTERLEVET ad, og (c) ikke gør «aldrig målt» til et
opdigtet tal.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import decision_breach_reader as br


def _rec(did: str, hours_ago: float) -> dict:
    return {
        "at": (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat(),
        "decision_id": did,
        "description": "x",
    }


def test_stats_aggregerer_pr_beslutning_og_ignorerer_gammelt(monkeypatch):
    recs = [_rec("d1", 1), _rec("d1", 2), _rec("d2", 30), _rec("d3", 24 * 40)]
    monkeypatch.setattr(br, "_records", lambda: recs)
    s = br.breach_stats(window_days=14)
    assert s["d1"]["count"] == 2
    assert s["d2"]["count"] == 1
    assert "d3" not in s, "brud uden for vinduet må ikke tælle som nutidig adfærd"
    assert s["d1"]["age_hours"] == pytest.approx(1, abs=0.2)


def test_breach_line_er_none_uden_brud(monkeypatch):
    monkeypatch.setattr(br, "_records", lambda: [])
    assert br.breach_line("d1") is None


def test_classify_skiller_de_tre_egenskaber(monkeypatch):
    monkeypatch.setattr(br, "_records", lambda: [_rec("d1", 1)] * 3)
    d = {
        "decision_id": "d1",
        "directive": "undgå at bruge bash til filredigering",
        "trigger_name": "",
        "adherence_score": None,
    }
    c = br.classify(d)
    assert c["executable"] is True, "direktivet har et mål gaten kan matche"
    assert c["measurable"] is True, "der findes brud at vurdere imod"
    assert c["adhered"] is None, "brud er mistanker — ikke en dom"
    assert c["weak"] is True, "3 brud uden måling er svag i praksis"


def test_aldrig_maalt_uden_signal_er_ikke_svag(monkeypatch):
    monkeypatch.setattr(br, "_records", lambda: [])
    d = {"decision_id": "d9", "directive": "vær nysgerrig", "adherence_score": None}
    c = br.classify(d)
    assert c["adhered"] is None
    assert c["measurable"] is False
    assert c["weak"] is False, "fravær af data må ikke straffes som brud"


def test_health_report_taeller_de_aldrig_maalte_i_to_grupper(monkeypatch):
    monkeypatch.setattr(br, "_records", lambda: [_rec("d1", 1)] * 3)
    decisions = [
        {"decision_id": "d1", "directive": "undgå bash", "adherence_score": None},
        {"decision_id": "d2", "directive": "vær nysgerrig", "adherence_score": None},
        {"decision_id": "d3", "directive": "altid test", "adherence_score": 0.9},
    ]
    r = br.health_report(decisions)
    assert r["never_measured"] == 2
    assert r["never_measured_with_breaches"] == 1
    assert r["never_measured_without_signal"] == 1
    assert r["mean_adhered"] == 0.9
