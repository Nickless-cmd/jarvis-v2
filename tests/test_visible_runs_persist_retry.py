"""H5 persist-retry (spec §2.5 / §11.2 P5): persistering af assistant-svaret må
ALDRIG tabes tavst pga. et FORBIGÅENDE DB-blip. "Vist live, væk ved reload" er
data-integritet, ikke bare en nerve.

Vi tester to lag:
- ``_append_chat_message_with_retry``: forbigående sqlite-lock fejler N gange →
  retry'er → beskeden BLIVER persisteret (ingen nerve fyres). Permanent fejl
  propageres uændret (caller fyrer ``persist_failed``-backstop-nerven).
- ``_persist_session_assistant_message`` + caller-mønster: når retries er udtømte,
  propageres fejlen → ``_observe_persist_failed`` fyrer NØJAGTIG én gang.

Hermetisk: ingen rigtig DB, ingen sleep af betydning (backoffs patches til 0).
"""
from __future__ import annotations

import importlib
import sqlite3

import pytest


def _make_run(visible_runs):
    return visible_runs.VisibleRun(
        run_id="visible-test-persist-retry",
        lane="primary",
        provider="deepseek",
        model="deepseek-v4-flash",
        user_message="hej",
        session_id="chat-test-session-persist-retry",
    )


@pytest.fixture
def vr():
    return importlib.import_module("core.services.visible_runs")


def test_retry_succeeds_after_transient_lock(vr, monkeypatch) -> None:
    """append_chat_message kaster 'database is locked' 2 gange, så lykkes →
    helperen retry'er og returnerer den persisterede besked. Ingen exception
    boblet ud → ingen persist_failed-nerve."""
    calls = {"n": 0}

    def flaky(**kwargs):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise sqlite3.OperationalError("database is locked")
        return {"id": "m-ok", **kwargs}

    monkeypatch.setattr(vr, "append_chat_message", flaky)
    # Ingen rigtig søvn i testen.
    monkeypatch.setattr(vr.time, "sleep", lambda *_a, **_k: None)

    result = vr._append_chat_message_with_retry(
        session_id="s1", role="assistant", content="svaret", reasoning_content="",
    )
    assert calls["n"] == 3, "skal have prøvet 3 gange (2 fejl + 1 succes)"
    assert result["id"] == "m-ok"
    assert result["content"] == "svaret"


def test_retry_exhausted_raises_for_backstop(vr, monkeypatch) -> None:
    """append_chat_message kaster ALTID 'database is locked' → efter udtømte
    backoffs (2) propageres fejlen, så caller kan fyre persist_failed."""
    calls = {"n": 0}

    def always_locked(**kwargs):
        calls["n"] += 1
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(vr, "append_chat_message", always_locked)
    monkeypatch.setattr(vr.time, "sleep", lambda *_a, **_k: None)

    with pytest.raises(sqlite3.OperationalError):
        vr._append_chat_message_with_retry(
            session_id="s1", role="assistant", content="svaret",
        )
    # 1 initial + 2 retries (default backoffs (0.2, 0.5)).
    assert calls["n"] == 3, "skal prøve 1 + 2 retries før den giver op"


def test_non_transient_error_not_retried(vr, monkeypatch) -> None:
    """En PERMANENT fejl (fx 'no such table' / IntegrityError) må IKKE retry'es —
    det ville bare spilde tid. Propageres ved FØRSTE forsøg."""
    calls = {"n": 0}

    def integrity_fail(**kwargs):
        calls["n"] += 1
        raise sqlite3.IntegrityError("UNIQUE constraint failed")

    monkeypatch.setattr(vr, "append_chat_message", integrity_fail)
    slept = {"n": 0}
    monkeypatch.setattr(vr.time, "sleep", lambda *_a, **_k: slept.__setitem__("n", slept["n"] + 1))

    with pytest.raises(sqlite3.IntegrityError):
        vr._append_chat_message_with_retry(
            session_id="s1", role="assistant", content="svaret",
        )
    assert calls["n"] == 1, "permanent fejl må ikke retry'es"
    assert slept["n"] == 0, "ingen backoff på permanent fejl"


def test_operationalerror_non_lock_not_retried(vr, monkeypatch) -> None:
    """En OperationalError der IKKE er en lock/busy (fx 'no such table') er
    permanent → ikke transient → ingen retry."""
    calls = {"n": 0}

    def no_table(**kwargs):
        calls["n"] += 1
        raise sqlite3.OperationalError("no such table: chat_messages")

    monkeypatch.setattr(vr, "append_chat_message", no_table)
    monkeypatch.setattr(vr.time, "sleep", lambda *_a, **_k: None)

    with pytest.raises(sqlite3.OperationalError):
        vr._append_chat_message_with_retry(
            session_id="s1", role="assistant", content="svaret",
        )
    assert calls["n"] == 1, "ikke-lock OperationalError må ikke retry'es"


def test_persist_message_retry_then_success_no_nerve(vr, monkeypatch) -> None:
    """End-to-end gennem _persist_session_assistant_message: transient lock
    helbredes af retryen → beskeden persisteres → INGEN persist_failed-nerve."""
    calls = {"n": 0}
    appended: list[dict] = []

    def flaky(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise sqlite3.OperationalError("database is locked")
        appended.append(kwargs)
        return {"id": "m-ok", **kwargs}

    monkeypatch.setattr(vr, "append_chat_message", flaky)
    monkeypatch.setattr(vr.time, "sleep", lambda *_a, **_k: None)

    nerves: list[str] = []
    monkeypatch.setattr(
        vr, "_observe_persist_failed",
        lambda run, exc: nerves.append(str(exc)),
    )
    # Hold event-bus + privacy-guard ude af vejen.
    from core.eventbus import bus as _bus_mod
    monkeypatch.setattr(_bus_mod.event_bus, "publish", lambda *a, **k: None)

    run = _make_run(vr)

    # Simulér caller-mønsteret (visible_runs.py:3655 / :4221).
    try:
        vr._persist_session_assistant_message(run, "det rigtige svar")
    except Exception as exc:  # pragma: no cover - skal ikke ske
        vr._observe_persist_failed(run, exc)

    assert len(appended) == 1, "beskeden skal være persisteret efter retry"
    assert appended[0]["content"]  # ikke tom
    assert nerves == [], "ingen persist_failed-nerve når retryen lykkes"


def test_persist_message_exhausted_fires_nerve_once(vr, monkeypatch) -> None:
    """End-to-end: persistent lock → retries udtømt → fejlen propageres ud af
    _persist_session_assistant_message → caller fyrer persist_failed NØJAGTIG én
    gang."""
    def always_locked(**kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(vr, "append_chat_message", always_locked)
    monkeypatch.setattr(vr.time, "sleep", lambda *_a, **_k: None)

    nerves: list[str] = []
    monkeypatch.setattr(
        vr, "_observe_persist_failed",
        lambda run, exc: nerves.append(str(exc)),
    )
    from core.eventbus import bus as _bus_mod
    monkeypatch.setattr(_bus_mod.event_bus, "publish", lambda *a, **k: None)

    run = _make_run(vr)

    # Caller-mønsteret: try/except + _observe_persist_failed (backstop).
    try:
        vr._persist_session_assistant_message(run, "det rigtige svar")
    except Exception as exc:
        vr._observe_persist_failed(run, exc)

    assert len(nerves) == 1, "persist_failed skal fyre NØJAGTIG én gang efter udtømte retries"
    assert "locked" in nerves[0].lower()
