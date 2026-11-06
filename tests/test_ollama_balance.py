"""Ventende rutine-kørsler skal have en synlig grund — også ved ollama-blokering."""
from __future__ import annotations

import pytest

from core.services import ollama_balance
from core.services.ollama_balance import OllamaReading
from tests.test_routine_dispatch import _run, deterministic_user_keys  # noqa: F401


def _events(run_id):
    from core.runtime import db_routines

    owner = db_routines.get_run(run_id)["owner_user_id"]
    with db_routines.connect() as conn:
        rows = conn.execute(
            "SELECT kind,payload_enc FROM routine_run_events WHERE run_id=? ORDER BY seq",
            (run_id,),
        ).fetchall()
    import json
    from core.services.routine_crypto import open_sealed as unseal

    return [(r["kind"], json.loads(unseal(owner, r["payload_enc"]))) for r in rows]


@pytest.fixture(autouse=True)
def _fresh_cache():
    ollama_balance.reset_cache()
    import core.services.routine_runner as rr

    rr._alerted_runs.clear()
    yield
    ollama_balance.reset_cache()


def _pending(monkeypatch):
    from core.services import routine_dispatch

    monkeypatch.setattr(
        routine_dispatch, "resolve_owner_session", lambda _o: ("chat-bjorn", "valid"),
    )
    monkeypatch.setattr(
        routine_dispatch, "runtime_presence", lambda _s: ("busy", "active-run"),
    )


def test_pending_run_gets_waiting_event_once(isolated_runtime, monkeypatch):
    from core.services.routine_runner import RoutineRunner

    _s, _r, run = _run(isolated_runtime, mode="session")
    _pending(monkeypatch)
    import core.services.routine_runner as rr

    monkeypatch.setattr(rr, "_standard_provider", lambda: "deepseek")
    runner = RoutineRunner()
    for _ in range(3):
        outcome = runner.run_next()
    assert (outcome.path, outcome.reason) == ("pending", "active-run")
    assert _events(run.run_id) == [("waiting", {"reason": "active-run"})]


def test_blocked_ollama_is_named_and_owner_alerted(isolated_runtime, monkeypatch):
    from core.services.routine_runner import RoutineRunner
    import core.services.routine_runner as rr

    _s, _r, run = _run(isolated_runtime, mode="session")
    _pending(monkeypatch)
    monkeypatch.setattr(rr, "_standard_provider", lambda: "ollama")
    monkeypatch.setattr(rr, "_standard_model", lambda: "m:cloud")
    monkeypatch.setattr(
        ollama_balance, "_post",
        lambda *_a: OllamaReading(ollama_balance.BLOCKED, 402, "payment required"),
    )
    alerts = []
    monkeypatch.setattr(rr, "_alert_owner", lambda text, rid: alerts.append((text, rid)))
    runner = RoutineRunner()
    runner.run_next()
    runner.run_next()
    kinds = _events(run.run_id)
    assert kinds == [
        ("waiting", {"reason": "active-run"}),
        ("waiting", {
            "reason": "ollama_blocked",
            "detail": "ollama-lanen afviste et prøvekald: HTTP 402 payment required",
        }),
    ]
    assert len(alerts) == 1 and alerts[0][1] == run.run_id
    assert "HTTP 402 payment required" in alerts[0][0]


@pytest.mark.parametrize("reading", [
    OllamaReading(ollama_balance.HEALTHY, 200),
    OllamaReading(ollama_balance.UNKNOWN, 0, "URLError"),
])
def test_healthy_or_unknown_ollama_never_claims_blocked(isolated_runtime, monkeypatch, reading):
    from core.services.routine_runner import RoutineRunner
    import core.services.routine_runner as rr

    _s, _r, run = _run(isolated_runtime, mode="session")
    _pending(monkeypatch)
    monkeypatch.setattr(rr, "_standard_provider", lambda: "ollama")
    monkeypatch.setattr(rr, "_standard_model", lambda: "m:cloud")
    monkeypatch.setattr(ollama_balance, "_post", lambda *_a: reading)
    alerts = []
    monkeypatch.setattr(rr, "_alert_owner", lambda *a: alerts.append(a))
    RoutineRunner().run_next()
    assert _events(run.run_id) == [("waiting", {"reason": "active-run"})]
    assert alerts == []


def test_probe_classifies_real_http_error(monkeypatch):
    import io, urllib.error

    def boom(req, timeout):
        raise urllib.error.HTTPError("u", 402, "Payment Required", {}, io.BytesIO(b'{"error":"x"}'))

    monkeypatch.setattr(ollama_balance.urllib.request, "urlopen", boom)
    assert ollama_balance._post("http://h", "m", 1) == OllamaReading(
        ollama_balance.BLOCKED, 402, '{"error":"x"}',
    )
