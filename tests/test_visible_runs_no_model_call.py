"""En kørsel der aldrig nåede modellen må ikke skrive narrativ (14/11-2026).

MÅLT på `visible-976e37a519bc4a908ed5463d2de2c3d7`: aflyst FØR første modelkald
(`provider_call_count=0`, `invoke_status='not-invoked'`, tom tekst), og alligevel
fik 21 tabeller rækker bundet til run-id'et — heriblandt
`runtime_self_review_records/signals`, `private_inner_notes`,
`private_growth_notes` og `session_summaries`. Den indre stemme læste dem som
«den afbrudte kørsel efterlod noget» og fødte falske initiativer.

De FAKTUELLE rækker (`visible_runs`) skal stadig skrives. Den positive kontrol
(en kørsel MED modelkald) er med for at bevise at testen måler noget: skriver
den ikke narrativ her, er det fixturen der er i stykker, ikke rettelsen.
"""
from __future__ import annotations

import types

import pytest


def _run(run_id: str = "visible-976e37a519bc4a908ed5463d2de2c3d7"):
    return types.SimpleNamespace(
        run_id=run_id,
        lane="visible",
        provider="test-provider",
        model="test-model",
        session_id="chat-s-1",
        user_id="",
        autonomous=False,
        user_message="kig på det tabte værktøjskald",
    )


def _trace(run, **updates) -> None:
    """Sæt sporet som den rigtige kørsel gør: start, så opdateringer."""
    from core.services.visible_run_trace import (
        _start_visible_execution_trace,
        _update_visible_execution_trace,
    )

    _start_visible_execution_trace(run)
    if updates:
        _update_visible_execution_trace(run, updates)


def _count(table: str, run_id: str) -> int:
    from core.runtime.db import connect

    with connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if exists is None:
            return 0
        return conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE run_id = ?", (run_id,)
        ).fetchone()[0]


# ── Prædikatet ──────────────────────────────────────────────────────────────


def test_predicate_true_for_cancelled_before_first_model_call(isolated_runtime):
    from core.services.visible_run_trace import run_never_reached_model

    run = _run()
    _trace(run, provider_first_pass_status="cancelled",
           provider_error_summary="user-cancelled")
    assert run_never_reached_model(run.run_id, "") is True
    assert run_never_reached_model(run.run_id, None) is True


@pytest.mark.parametrize("case", ["has_call", "has_text", "other_runs_trace",
                                  "no_trace", "unknown_count"])
def test_predicate_fails_open(isolated_runtime, case):
    """Alt der ikke er entydigt «ingen modelkald, intet output» = gammel adfærd."""
    import core.services.visible_run_trace as T

    run = _run()
    text = ""
    if case == "has_call":
        _trace(run, provider_call_count=1)
    elif case == "has_text":
        _trace(run)
        text = "et ægte svar"
    elif case == "other_runs_trace":
        _trace(_run("visible-en-anden-koersel"))
    elif case == "no_trace":
        T._LAST_VISIBLE_EXECUTION_TRACE = None
    elif case == "unknown_count":
        _trace(run)
        T._LAST_VISIBLE_EXECUTION_TRACE = {
            k: v for k, v in T._LAST_VISIBLE_EXECUTION_TRACE.items()
            if k != "provider_call_count"
        }
    assert T.run_never_reached_model(run.run_id, text) is False


# ── Kaldstedet: set_last_visible_run_outcome ruter flaget til persist ──────


def _sync_threads(monkeypatch):
    import threading

    class _Sync:
        def __init__(self, *, target=None, args=(), kwargs=None, **_kw):
            self._t, self._a, self._k = target, args, kwargs or {}

        def start(self):
            self._t(*self._a, **self._k)

    monkeypatch.setattr(threading, "Thread", _Sync)


@pytest.mark.parametrize("calls,expected", [(0, True), (1, False)])
def test_outcome_persist_is_told_whether_the_model_was_reached(
    isolated_runtime, monkeypatch, calls, expected
):
    import core.services.visible_runs_outcomes as O

    seen: list[dict] = []
    monkeypatch.setattr(O, "_persist_visible_run_outcome",
                        lambda run, **kw: seen.append(kw))
    _sync_threads(monkeypatch)
    run = _run()
    _trace(run, provider_call_count=calls)

    O.set_last_visible_run_outcome(run, status="cancelled", text_preview=None)

    assert [kw["no_model_call"] for kw in seen] == [expected]


# ── Narrativ-skriverne: ægte DB for private_growth_notes ───────────────────


def _persist(run, *, no_model_call: bool, monkeypatch) -> list[str]:
    import core.services.visible_runs as vr
    import core.services.visible_runs_outcomes as O

    cognitive_calls: list[str] = []
    monkeypatch.setattr("core.memory.private_layer_pipeline.enrich_private_layers_async",
                        lambda **_kw: None)
    monkeypatch.setattr(vr, "_update_cognitive_systems_async",
                        lambda **kw: cognitive_calls.append(kw["run_id"]))
    O._persist_visible_run_outcome(
        run, status="cancelled", finished_at="2026-11-13T20:03:26+00:00",
        text_preview=None, error=None, no_model_call=no_model_call,
    )
    return cognitive_calls


def test_cancelled_run_without_model_call_writes_no_growth_note(
    isolated_runtime, monkeypatch
):
    run = _run()
    calls = _persist(run, no_model_call=True, monkeypatch=monkeypatch)

    assert _count("private_growth_notes", run.run_id) == 0
    assert _count("private_inner_notes", run.run_id) == 0
    assert calls == [], "cadence-producerne (self-review) må ikke startes"
    # Det FAKTUELLE bevares: kørslen findes, og den er aflyst.
    assert _count("visible_runs", run.run_id) == 1
    from core.runtime.db import connect
    with connect() as conn:
        status = conn.execute(
            "SELECT status FROM visible_runs WHERE run_id = ?", (run.run_id,)
        ).fetchone()[0]
    assert status == "cancelled"


def test_positive_control_run_with_model_call_still_writes_narrative(
    isolated_runtime, monkeypatch
):
    """Uden denne beviser den røde/grønne test ikke noget."""
    run = _run("visible-med-modelkald")
    calls = _persist(run, no_model_call=False, monkeypatch=monkeypatch)

    assert _count("private_growth_notes", run.run_id) == 1
    assert _count("private_inner_notes", run.run_id) == 1
    assert calls == [run.run_id]


# ── Trackerne + post-run-memory ────────────────────────────────────────────


_SELF_REVIEW_TRACKERS = (
    "track_runtime_self_review_signals_for_visible_turn",
    "track_runtime_self_review_records_for_visible_turn",
    "track_runtime_self_review_runs_for_visible_turn",
    "track_runtime_self_review_outcomes_for_visible_turn",
    "track_runtime_self_review_cadence_signals_for_visible_turn",
    "track_runtime_private_inner_note_signals_for_visible_turn",
)


@pytest.mark.parametrize("calls,text,expect_called", [
    (0, "", False),          # aflyst før modellen: ingen self-review
    (1, "et svar", True),    # positiv kontrol
])
def test_self_review_trackers_skip_runs_that_never_reached_the_model(
    isolated_runtime, monkeypatch, calls, text, expect_called
):
    import core.services.visible_runs_cognitive as VRC

    called: list[str] = []
    for name in _SELF_REVIEW_TRACKERS:
        monkeypatch.setattr(VRC._vr, name,
                            lambda _n=name, **_kw: called.append(_n), raising=False)
    monkeypatch.setattr(VRC, "_track_step_failed", lambda: None)
    run = _run()
    _trace(run, provider_call_count=calls)

    VRC._track_runtime_candidates(run, text)

    assert (set(called) == set(_SELF_REVIEW_TRACKERS)) is expect_called
    if not expect_called:
        assert called == []


@pytest.mark.parametrize("calls,text,expect_called", [
    (0, "", False),
    (1, "et svar", True),
])
def test_memory_postprocess_skips_narrative_producers_without_model_call(
    isolated_runtime, monkeypatch, calls, text, expect_called
):
    import core.services.session_distillation as SD
    import core.services.end_of_run_memory_consolidation as EC
    import core.services.visible_runs_memory as M

    called: list[str] = []
    monkeypatch.setattr(SD, "distill_session_carry",
                        lambda **_kw: called.append("distill") or {})
    monkeypatch.setattr(SD, "generate_session_summary",
                        lambda **_kw: called.append("summary") or "")
    monkeypatch.setattr(EC, "consolidate_run_memory",
                        lambda **_kw: called.append("consolidate") or {})
    run = _run()
    _trace(run, provider_call_count=calls)

    M._run_memory_postprocess(run, text)

    assert (sorted(called) == ["consolidate", "distill", "summary"]) is expect_called
    if not expect_called:
        assert called == []
