"""Preflight oplyser BEGGE kvote-vinduer — og det ugentlige kan blokere.

Målt 24/11-2026: `secondary_pct` / `seven_day_pct` blev læst og kasseret, så
en dispatch med 100 % ugentligt forbrug og 20 % 5-timers blev godkendt som
«ok» og døde sekunder efter worktreet var oprettet.
"""
from __future__ import annotations

import json

import pytest

from core.services import dispatch_quota


class _Resp:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_Resp":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def close(self) -> None:
        pass


def _patch(monkeypatch, payload: dict) -> None:
    def _urlopen(req, timeout=None):
        return _Resp(payload)

    monkeypatch.setattr(dispatch_quota.urllib.request, "urlopen", _urlopen)


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    dispatch_quota.reset_cache()
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-token")
    monkeypatch.setattr(dispatch_quota, "_CLAUDE_ENV_FILE", str(tmp_path / "x.env"))
    yield
    dispatch_quota.reset_cache()


def test_begge_vinduer_staar_i_begrundelsen(monkeypatch):
    _patch(monkeypatch, {
        "five_hour": {"utilization": 20.0, "resets_at": "2026-11-25T00:30:00+00:00"},
        "seven_day": {"utilization": 3.0, "resets_at": "2026-11-30T01:00:00+00:00"},
    })
    r = dispatch_quota.quota_preflight("claude")

    assert "5-timers-kvoten" in r["reason"]
    assert "ugentlige" in r["reason"]
    assert [w["pct"] for w in r["windows"]] == [20.0, 3.0]


def test_ugentligt_loft_blokerer_selv_naar_5_timer_er_lavt(monkeypatch):
    """Den ægte adfærdsændring: før slap 100 % ugentligt igennem som «ok»."""
    _patch(monkeypatch, {
        "five_hour": {"utilization": 20.0, "resets_at": "2026-11-25T00:30:00+00:00"},
        "seven_day": {"utilization": 100.0, "resets_at": "2026-11-30T01:00:00+00:00"},
    })
    r = dispatch_quota.quota_preflight("claude")

    assert r["allow"] is False
    assert r["severity"] == "block"
    assert r["pct"] == 100.0


def test_advisory_oplyser_uden_at_blokere(monkeypatch):
    _patch(monkeypatch, {
        "five_hour": {"utilization": 20.0, "resets_at": "2026-11-25T00:30:00+00:00"},
        "seven_day": {"utilization": 3.0, "resets_at": "2026-11-30T01:00:00+00:00"},
    })
    a = dispatch_quota.quota_advisory("claude")

    assert a["measured"] is True
    assert {w["label"] for w in a["windows"]} == {
        "5-timers-kvoten", "den ugentlige kvote"
    }


def test_stale_maaling_siges_hoejt(monkeypatch):
    """Codex' kvote læses fra en rollout-fil; otte dage gammel så den frisk ud."""
    reading = dispatch_quota.QuotaReading(
        ok=True, backend="claude", observed_at="2026-11-16T00:00:00+00:00",
        values={"five_hour_pct": 0.0, "five_hour_resets_at": "",
                "seven_day_pct": 0.0, "seven_day_resets_at": ""},
        stale_hours=191.2,
    )
    monkeypatch.setattr(dispatch_quota, "claude_quota", lambda: reading)

    r = dispatch_quota.quota_preflight("claude")

    assert "191.2 t gammel" in r["reason"]
