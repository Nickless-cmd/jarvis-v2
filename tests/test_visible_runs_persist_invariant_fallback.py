"""Test for fix D2 (2026-06-11): when LLM emitter tool-result markers
som prose, _persist_session_assistant_message må IKKE bare raise og
lade run-en blive completed uden at appende noget til chat. Det
resulterede i Discord-runs der completed silent uden besked til Bjørn.

Vi forventer:
- En sanitized fallback-besked persisteres til chat (så user får signal)
- channel.chat_message_appended event publiceres (så Discord sub fyrer)
- Den oprindelige besked stadig logges som warning for dev-visibility
"""
from __future__ import annotations

import importlib

import pytest


def _make_run(visible_runs):
    return visible_runs.VisibleRun(
        run_id="visible-test-fallback",
        lane="primary",
        provider="deepseek",
        model="deepseek-v4-flash",
        user_message="hej",
        session_id="chat-test-session-fallback",
    )


def test_persist_with_invariant_leak_still_persists_fallback(monkeypatch) -> None:
    """Når invariant-check raiser, skal persist alligevel append en
    sanitized fallback + publish channel.chat_message_appended event."""
    visible_runs = importlib.import_module("core.services.visible_runs")

    appended_messages: list[dict] = []
    monkeypatch.setattr(
        visible_runs, "append_chat_message",
        lambda **kwargs: appended_messages.append(kwargs) or {"id": "m-fake", **kwargs},
    )

    published: list[tuple[str, dict]] = []
    from core.eventbus import bus as _bus_mod
    monkeypatch.setattr(
        _bus_mod.event_bus, "publish",
        lambda kind, payload: published.append((kind, payload)),
    )

    run = _make_run(visible_runs)
    # Leaky text: starts med tool-result marker.
    leaky = (
        "([search_memory]: [Tool error: workspace_dir() called without "
        "user_id]) jeg vil prøve igen"
    )

    # Må IKKE raise — persist skal være robust.
    visible_runs._persist_session_assistant_message(run, leaky)

    assert len(appended_messages) == 1, "skal appende en fallback-besked"
    persisted = appended_messages[0]
    assert persisted["role"] == "assistant"
    # Skal IKKE være den leaky tekst — skal være sanitized.
    assert "[search_memory]" not in persisted["content"]
    assert "tool-resultater" in persisted["content"].lower() or "fejl" in persisted["content"].lower()

    # Skal publish event så Discord/webchat sub kan deliver beskeden.
    kinds = [k for k, _ in published]
    assert "channel.chat_message_appended" in kinds


def test_persist_clean_text_still_works(monkeypatch) -> None:
    """Regression-check: clean tekst skal stadig persistes som-er."""
    visible_runs = importlib.import_module("core.services.visible_runs")

    appended_messages: list[dict] = []
    monkeypatch.setattr(
        visible_runs, "append_chat_message",
        lambda **kwargs: appended_messages.append(kwargs) or {"id": "m-clean", **kwargs},
    )

    from core.eventbus import bus as _bus_mod
    monkeypatch.setattr(_bus_mod.event_bus, "publish", lambda *a, **k: None)

    run = _make_run(visible_runs)
    clean_text = "Det er gjort. Commit pushed."
    visible_runs._persist_session_assistant_message(run, clean_text)

    assert len(appended_messages) == 1
    assert appended_messages[0]["content"] == clean_text


def test_persist_skips_when_no_session(monkeypatch) -> None:
    """Regression-check: ingen session = ingen append."""
    visible_runs = importlib.import_module("core.services.visible_runs")

    appended_messages: list[dict] = []
    monkeypatch.setattr(
        visible_runs, "append_chat_message",
        lambda **kwargs: appended_messages.append(kwargs),
    )

    run = visible_runs.VisibleRun(
        run_id="visible-no-session",
        lane="primary",
        provider="deepseek",
        model="deepseek-v4-flash",
        user_message="hej",
        session_id="",
    )
    visible_runs._persist_session_assistant_message(run, "noget tekst")

    assert appended_messages == []
