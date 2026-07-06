"""API-forbindelses-nerve — metadata-only presence + GDPR-anonymisering.

Invarianter: record() akkumulerer in-memory (ingen DB i hot-path), observerer SELEKTIVT til
Centralen (kun ny forbindelse + fejl), og IP anonymiseres til /24 (GDPR). Aldrig body/indhold.
"""
from __future__ import annotations

from unittest import mock

import core.services.api_connection_nerve as nerve
from core.runtime import db_api_connections as db


def _reset():
    with nerve._LOCK:
        nerve._PRESENCE.clear()
        nerve._LOG_BUFFER.clear()


def test_anonymize_ip_truncates_to_24():
    assert db.anonymize_ip("185.107.14.241") == "185.107.14.0/24"
    assert db.anonymize_ip("10.0.0.39") == "10.0.0.0/24"
    assert db.anonymize_ip("") == ""
    # allerede anonymiseret → uændret
    assert db.anonymize_ip("185.107.14.0/24") == "185.107.14.0/24"


def test_record_accumulates_without_db_and_observes_new_connection():
    """record() rører ikke DB (billig); NY forbindelse → én Central-observe."""
    _reset()
    observed = []
    fake_central = mock.MagicMock()
    fake_central.observe.side_effect = lambda ev: observed.append(ev)
    with mock.patch("core.runtime.db_api_connections.flush_records") as flush_db, \
            mock.patch("core.services.central_core.central", return_value=fake_central), \
            mock.patch.object(nerve, "_maybe_flush_async"):
        nerve.record(ip="185.107.14.5", method="GET", path="/api/chat", status=200,
                     latency_ms=12, user_id="bjorn")
        nerve.record(ip="185.107.14.5", method="GET", path="/api/chat", status=200,
                     latency_ms=9, user_id="bjorn")  # samme → ikke ny
        flush_db.assert_not_called()  # record rører ALDRIG DB
    # kun ÉN observe (den nye forbindelse), ikke pr. request
    assert len(observed) == 1
    assert observed[0]["kind"] == "new_connection"
    assert observed[0]["ip"] == "185.107.14.5" and observed[0]["user_id"] == "bjorn"
    # presence akkumulerede begge
    with nerve._LOCK:
        st = nerve._PRESENCE[("185.107.14.5", "bjorn")]
        assert st["request_count"] == 2


def test_error_always_observed():
    """En FEJL (status ≥ 400) observeres ALTID til Centralen (fejl-synlighed)."""
    _reset()
    observed = []
    fake_central = mock.MagicMock()
    fake_central.observe.side_effect = lambda ev: observed.append(ev)
    with mock.patch("core.services.central_core.central", return_value=fake_central), \
            mock.patch.object(nerve, "_maybe_flush_async"):
        # /health er "quiet" → ingen new_connection-observe, MEN fejl skal stadig observeres
        nerve.record(ip="1.2.3.4", method="GET", path="/health", status=500,
                     latency_ms=3, user_id="")
    assert len(observed) == 1 and observed[0]["kind"] == "error" and observed[0]["status"] == 500


def test_no_body_or_content_in_payload():
    """Metadata-only: payloaden må ALDRIG indeholde body/indhold — kun ip/metode/sti/status/tal."""
    _reset()
    observed = []
    fake_central = mock.MagicMock()
    fake_central.observe.side_effect = lambda ev: observed.append(ev)
    with mock.patch("core.services.central_core.central", return_value=fake_central), \
            mock.patch.object(nerve, "_maybe_flush_async"):
        nerve.record(ip="9.9.9.9", method="POST", path="/api/chat", status=200,
                     latency_ms=5, user_id="mikkel", session_id="chat-xyz")
    keys = set(observed[0].keys())
    # kun tilladte metadata-nøgler
    assert keys <= {"cluster", "nerve", "kind", "ip", "user_id", "method", "path",
                    "status", "latency_ms"}
    assert "body" not in keys and "content" not in keys


def test_flush_drains_presence_and_log(tmp_path, monkeypatch):
    """flush() sender dirty presence + log til DB og tømmer log-bufferen."""
    _reset()
    captured = {}
    monkeypatch.setattr("core.runtime.db_api_connections.flush_records",
                        lambda pd, logs: captured.update({"pd": pd, "logs": logs}) or (len(pd) + len(logs)))
    with mock.patch("core.services.central_core.central"), \
            mock.patch.object(nerve, "_maybe_flush_async"):
        nerve.record(ip="5.5.5.5", method="GET", path="/api/x", status=200, latency_ms=1, user_id="u")
    n = nerve.flush()
    assert n == 2  # 1 presence + 1 log
    assert captured["pd"][0]["ip"] == "5.5.5.5"
    assert captured["logs"][0]["path"] == "/api/x"
    with nerve._LOCK:
        assert not nerve._LOG_BUFFER  # tømt
