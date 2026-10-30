"""Unit tests for retry policy + health check."""
from __future__ import annotations

import time
from unittest.mock import patch

from core.services.provider_retry_policy import retry_with_backoff, _is_transient
from core.services.provider_health_check import (
    _ping_host,
    health_check_all_providers,
    health_section,
    latest_health_snapshot,
)


# ── retry_policy ──


def test_is_transient_recognizes_timeout():
    assert _is_transient(TimeoutError("connection timed out"))


def test_is_transient_recognizes_429():
    assert _is_transient(RuntimeError("HTTP 429: rate limit exceeded"))


def test_is_transient_rejects_unknown_error():
    assert not _is_transient(ValueError("invalid input"))


def test_retry_succeeds_on_first_attempt():
    counter = {"n": 0}
    def fn():
        counter["n"] += 1
        return "ok"
    result = retry_with_backoff(fn, max_retries=3, base_delay=0.01)
    assert result == "ok"
    assert counter["n"] == 1


def test_retry_eventually_succeeds_after_failures():
    counter = {"n": 0}
    def fn():
        counter["n"] += 1
        if counter["n"] < 3:
            raise TimeoutError("transient")
        return "ok"
    result = retry_with_backoff(fn, max_retries=3, base_delay=0.01)
    assert result == "ok"
    assert counter["n"] == 3


def test_retry_gives_up_after_max_retries():
    counter = {"n": 0}
    def fn():
        counter["n"] += 1
        raise TimeoutError("always fails")
    try:
        retry_with_backoff(fn, max_retries=2, base_delay=0.01)
    except TimeoutError:
        pass
    else:
        assert False, "should have raised"
    assert counter["n"] == 3  # initial + 2 retries


def test_retry_does_not_retry_non_transient():
    counter = {"n": 0}
    def fn():
        counter["n"] += 1
        raise ValueError("permanent")
    try:
        retry_with_backoff(fn, max_retries=3, base_delay=0.01, only_transient=True)
    except ValueError:
        pass
    else:
        assert False, "should have raised"
    assert counter["n"] == 1  # no retries


def test_retry_backoff_actually_waits():
    counter = {"n": 0}
    started = time.time()
    def fn():
        counter["n"] += 1
        if counter["n"] < 3:
            raise TimeoutError("x")
        return "ok"
    retry_with_backoff(fn, max_retries=3, base_delay=0.05)
    elapsed = time.time() - started
    # 0.05 + 0.10 = 0.15s minimum
    assert elapsed >= 0.10


# ── health_check ──


def test_ping_host_reports_unreachable_on_error():
    with patch("urllib.request.urlopen", side_effect=ConnectionError("refused")):
        result = _ping_host("http://localhost:1/")
    assert result["reachable"] is False


def test_ping_host_kalder_401_for_auth_failed():
    """401 er et SVAR, men ikke et brugbart et.

    Testen hed oprindeligt `..._treats_401_as_reachable` og krævede `reachable is True`.
    Det var sandt indtil 28/10-2026, hvor `reachable` blev omdefineret til «kan bruges»
    — netop fordi 8/8 blev meldt sunde mens fem svarede med fejlkode. En 401 betyder
    «nøglen blev afvist», og det er den vigtigste oplysning sektionen kan give.
    """
    import urllib.error
    err = urllib.error.HTTPError("u", 401, "unauthorized", {}, None)
    with patch("urllib.request.urlopen", side_effect=err):
        result = _ping_host("http://example.com/")
    assert result["reachable"] is False
    assert result["status"] == "auth_failed"
    assert result["http_code"] == 401


def test_health_check_aggregates_results():
    # ollamafreeapi was removed from the ping rotation (2026-06-13, dead
    # provider). Assert aggregation against a currently-registered endpoint.
    #
    # 29/10-2026: proben bygges nu af `_probe_request` (base_url fra provider_router.json
    # + providerens egen nøgle), så URL'en kan ikke længere læses ud af `_PING_ENDPOINTS`
    # alene. Testen patcher derfor resolveren — det er den kontrakt der gælder.
    down_provider = "groq"

    def fake_probe(provider):
        return {"url": f"https://{provider}.example/models", "headers": {}, "has_credentials": True}

    def fake_ping(url, headers=None):
        if down_provider in url:
            return {"reachable": False, "status": "unreachable", "error": "down"}
        return {"reachable": True, "status": "healthy", "http_code": 200, "latency_ms": 50}

    with patch("core.services.provider_health_check._probe_request", side_effect=fake_probe), \
         patch("core.services.provider_health_check._ping_host", side_effect=fake_ping):
        snap = health_check_all_providers()
    assert down_provider in snap["unreachable"]
    assert snap["reachable_count"] == snap["total_count"] - 1


def test_health_section_returns_none_when_all_reachable():
    with patch("core.services.provider_health_check.latest_health_snapshot",
               return_value={"unreachable": [], "checked_at": "2026-04-27T08:00:00Z"}):
        assert health_section() is None


def test_health_section_warns_when_providers_down():
    with patch("core.services.provider_health_check.latest_health_snapshot", return_value={
        "unreachable": ["ollamafreeapi", "groq"],
        "checked_at": "2026-04-27T08:00:00Z",
    }):
        section = health_section()
    assert section is not None
    assert "ollamafreeapi" in section
    assert "groq" in section
