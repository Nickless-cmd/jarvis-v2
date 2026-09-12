"""E2E: et helt research-run gennem den ÆGTE orkestrator og den ÆGTE v2-oversætter.

Hullet (målt 13/9-2026): ingen test drev et research-run gennem ruten. Den eneste
flade var en schema-test af `research_mode` (`test_chat_stream_v2_override.py:15`).
Ruten `/v1/chat/stream` var altså aldrig kørt ende-til-ende for research.

Denne fil lukker hullet: den kører det rigtige `stream_research_run` — plan →
workers → top-up → critic → quality-gate → `research_completed` — og fører hele
den legacy-strøm gennem det rigtige `translate_to_v2`, som er præcis den
oversætter `/v1/chat/stream` bruger (`chat_stream_v2.py:564`).

Det der IKKE er ægte her: worker- og visible-factory'erne er fakes (ellers ville
testen kalde rigtige modeller og netværk), og store'en er en fake. Det er
bevidst: testen måler INTEGRATIONEN mellem orkestratoren og oversætteren — ikke
modellernes svar.
"""

from __future__ import annotations

import asyncio
import json

from core.services import research_orchestrator as orchestrator
from core.services.visible_runs_sse_v2 import translate_to_v2


def _legacy(name: str, payload: dict | None = None) -> str:
    return f"event: {name}\ndata: {json.dumps(payload or {})}\n\n"


def _fake_store(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator.store, "create_run", lambda **kw: {"id": "research-e2e", **kw})
    monkeypatch.setattr(
        orchestrator.store, "transition_run",
        lambda rid, status, **kw: {"id": rid, "status": status},
    )
    monkeypatch.setattr(orchestrator.store, "create_tasks", lambda rid, tasks: [
        {"id": f"t{i}", "ordinal": i, "title": t.title, "objective": t.objective}
        for i, t in enumerate(tasks, 1)
    ])
    monkeypatch.setattr(orchestrator.store, "start_task", lambda tid, **kw: {"id": tid})
    monkeypatch.setattr(orchestrator.store, "complete_task", lambda tid, finding, **kw: {"id": tid})
    monkeypatch.setattr(orchestrator.store, "source_count", lambda rid: 3)
    monkeypatch.setattr(orchestrator.store, "list_sources", lambda rid: [
        {"url": "https://a.example/1", "canonical_url": "https://a.example/1", "task_id": "t1"},
        {"url": "https://b.example/2", "canonical_url": "https://b.example/2", "task_id": "t1"},
        {"url": "https://c.example/3", "canonical_url": "https://c.example/3", "task_id": "t2"},
    ])
    monkeypatch.setattr(orchestrator.store, "list_findings", lambda rid: [{"task_ordinal": 1}])
    monkeypatch.setattr(orchestrator.store, "tool_call_count", lambda rid: 4)
    monkeypatch.setattr(orchestrator.store, "consume_pending_steers", lambda rid: [])
    monkeypatch.setattr(orchestrator.store, "bind_visible_run", lambda rid, visible: None)


def _fake_ledger(monkeypatch) -> None:
    monkeypatch.setattr(orchestrator.research_ledger, "record_run_started", lambda *a, **kw: None)
    monkeypatch.setattr(orchestrator.research_ledger, "record_run_completed", lambda *a, **kw: None)


async def _visible(**_kwargs):
    """Syntesen som klienten venter på — i den ÆGTE legacy-form.

    Formen er målt mod producenten (`visible_runs.py:1722`):
    `{"type": "delta", "run_id": ..., "delta": ...}`. Da testen først blev
    skrevet med `{"text": ...}`, fangede den en ægte bug i `_delta_text` (den
    læste en nøgle producenten aldrig sender). Formen holdes derfor tro mod
    producenten med vilje — en fake der ikke matcher producenten skjuler bugs.
    """
    yield _legacy("delta", {"type": "delta", "run_id": "visible-e2e", "delta": "Svaret er [1] og [2]. "})
    yield _legacy("delta", {"type": "delta", "run_id": "visible-e2e", "delta": "Usikkerhed: prisen kan ændre sig."})
    yield _legacy("done", {})


def _collect(iterator) -> list[str]:
    async def _run():
        return [frame async for frame in iterator]

    return asyncio.run(_run())


def test_et_helt_research_run_naar_frem_til_klienten(monkeypatch):
    """Plan → workers → quality → completed → v2-frames hos klienten."""
    _fake_store(monkeypatch)
    _fake_ledger(monkeypatch)
    # Planner (C1) og dommer (C3) slået FRA: e2e'en måler kernen, ikke de to
    # ekstra netværkskald. Flag-læsningen stubbes, så testen ikke arver maskinens
    # levende config — og så D1's tændte flag ikke laver testen om til et netværkskald.
    monkeypatch.setattr(orchestrator, "_setting", lambda name, default: False)

    workers: list[dict] = []

    def _worker_factory(**kwargs):
        workers.append(kwargs)
        return {
            "status": "completed",
            "text": json.dumps({
                "findings": [{"claim": "Pris er X", "source_urls": ["https://a.example/1"]}],
                "sources": [{"url": "https://a.example/1"}],
            }),
        }

    legacy = _collect(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris, sikkerhed og drift i en grundig rapport",
        session_id="s-e2e",
        visible_factory=_visible,
        worker_factory=_worker_factory,
        orchestrator_enabled=True,
    ))

    # 1. Orkestreringen kørte faktisk — ikke bare en inline-syntese.
    assert any("event: research_started" in f for f in legacy), legacy[:2]
    assert any("event: research_plan" in f for f in legacy), "planen blev aldrig sendt"
    assert workers, "ingen workers blev spawnet — runnet orkestrerede ikke"

    # 2. Fase C2's indsats nåede worker'en: budgettet er sat og sendt videre.
    assert all(kw.get("budget_tokens") for kw in workers), workers

    # 3. Slut-tilstanden bærer evidensen — ikke bare et svar.
    completed = json.loads(
        next(f for f in legacy if "event: research_completed" in f).split("data: ", 1)[1]
    )
    assert completed["sources"] == 3, completed
    assert completed["findings"] >= 1, completed
    assert completed["quality"] in {"passed", "failed", "not_evaluated"}, completed
    # Syntesens citationer skal være NÅET frem til kvalitetsgaten. Gaten ser kun
    # dem hvis `_delta_text` læser den ægte `delta`-nøgle — ellers evaluerer den
    # en tom rapport og `citation_validity` bliver False. Det gjorde den frem til
    # 13/9-2026 (se `test_A1_delta_text_laeser_den_aegte_frame`).
    assert completed["quality_gates"]["citation_validity"] is True, completed["quality_gates"]
    assert completed["judge"] == {}, "dommeren kørte selvom flaget var slået fra"
    assert completed["timed_out"] is False, completed

    # 4. Hele den ÆGTE oversætter på strømmen → de v2-frames klienten renderer.
    async def _replay():
        for frame in legacy:
            yield frame

    body = "".join(_collect(translate_to_v2(
        _replay(),
        model="m",
        provider="p",
        lane="primary",
        session_id="s-e2e",
        ping_interval_s=0.05,
    )))

    for ev in ("message_start", "content_block_start", "content_block_delta",
               "content_block_stop", "message_delta", "message_stop"):
        assert f"event: {ev}" in body, f"mangler {ev} i v2-strømmen:\n{body[:600]}"
    assert "Svaret er" in body, "syntese-teksten nåede ikke klienten"
    assert body.rstrip().endswith("}"), "sidste frame er ikke velformet"
