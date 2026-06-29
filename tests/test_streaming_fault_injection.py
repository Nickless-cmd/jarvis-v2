"""Fase 0 — fejl-injektions-harness + BASELINE-tests for streaming-robusthed.

Se ``docs/streaming-production-grade-spec.md`` (§0, §4.1, §11). Dette er
VERIFIKATIONS-FUNDAMENTET der skal eksistere FØR den hotte agentic-loop røres
(Fase 1). Filen er ADDITIV: den ændrer IKKE retry/break-logikken — den driver
det ÆGTE ``_stream_visible_run``/followup-spor gennem fejl-injektoren og
ASSERTERER NUVÆRENDE (pre-Fase-1) adfærd som den dokumenterede baseline.

Tre fejl-former (spec §11.2 "Fase 0-harness 3 former"):
  (a) clean_fail_before_delta   — HTTP 502 før nogen delta (ingen partiel tekst).
  (b) partial_deltas_then_drop  — PRIMÆR: N deltas, så et forbigående drop.
                                  Trigger for de blokerende huller C11 + D11.
  (c) http_400_overflow         — context-window-overløb (HTTP 400), distinkt
                                  fra et transport-drop (fatal, ikke retryable).

BASELINE-assertions markeret "BASELINE: dette er buggen; Fase 1 inverterer det"
er præcis dem Fase 1 skal FLIPPE (efter fixet: partiel tekst KASSERES + turen
OVERLEVER + retry synlig i Centralen).

Hermetisk: injektoren erstatter provider-kaldet; ingen netværk/ollama. First-pass-
model, tool-eksekvering, prompt-bygning og persistering er mocket til minimum.
"""
from __future__ import annotations

import asyncio

import pytest

import core.services.ollama_visible_prompt as ovp
import core.services.visible_runs as vr
from core.services import followup_observer as fo
from core.services import visible_followup as vf
from core.services.visible_model import (
    VisibleModelResult,
    VisibleModelStreamDone,
    VisibleModelToolCalls,
)


# ── Test-harness: driv det ÆGTE _stream_visible_run-spor hermetisk ───────────


class _DriveResult:
    """Opsamlet udfald af ét drevet run (til assertions)."""

    def __init__(self, chunks: list[str], persisted: list[str],
                 nerves: list[tuple[str, dict]]) -> None:
        self.chunks = chunks
        self.persisted = persisted
        self.nerves = nerves

    @property
    def persisted_text(self) -> str:
        return self.persisted[0] if self.persisted else ""

    @property
    def done_event(self) -> str:
        for c in self.chunks:
            if "event: done" in c:
                return c
        return ""

    @property
    def done_status(self) -> str:
        # Det terminale 'done'-event bærer status (completed/interrupted/...).
        import json
        for c in self.chunks:
            if "event: done" not in c:
                continue
            for line in c.splitlines():
                if line.startswith("data: "):
                    try:
                        return str(json.loads(line[6:]).get("status") or "")
                    except Exception:
                        return ""
        return ""

    def has_terminal_frame(self) -> bool:
        # I2-invariant: ENTEN et 'done'-event ELLER en typed fejl-frame skal nå
        # klienten. Vi accepterer begge som terminal-bevis i baseline.
        return any(
            ("event: done" in c) or ("event: error" in c) or ("event: failed" in c)
            for c in self.chunks
        )

    def nerve_names(self) -> list[str]:
        return [n for n, _ in self.nerves]


def _drive(monkeypatch, shape: str, *, run_id: str, **inject_kwargs) -> _DriveResult:
    """Driv ÉT minimalt agentisk followup-run gennem det ægte spor med en aktiv
    fejl-injektion. Returnerer opsamlet udfald."""

    # First-pass: ét tool-kald, så stream-done med tom prosa (→ agentic loop).
    def _fake_stream_model(**_kw):
        yield VisibleModelToolCalls(tool_calls=[{
            "id": "c1", "type": "function",
            "function": {"name": "read_file", "arguments": '{"path": "x"}'},
        }])
        yield VisibleModelStreamDone(
            result=VisibleModelResult(text="", input_tokens=10,
                                      output_tokens=5, cost_usd=0.0))

    def _fake_exec_tools(_tool_calls, **_kw):
        return [{
            "tool_name": "read_file", "tool_call_id": "c1",
            "status": "completed", "arguments": {"path": "x"},
            "result_text": "file-contents", "result": {"ok": True},
        }]

    monkeypatch.setattr(vr, "stream_visible_model", _fake_stream_model)
    monkeypatch.setattr(vr, "_execute_simple_tool_calls", _fake_exec_tools)
    monkeypatch.setattr(vr, "_build_visible_input",
                        lambda *a, **k: [{"role": "user", "content": "hej"}])
    monkeypatch.setattr(vr, "_visible_run_cancelled", lambda _rid: False)
    monkeypatch.setattr(ovp, "serialize_ollama_chat_messages", lambda x: list(x))

    # Persistering + bus + baggrunds-kost mocket → hermetisk, ingen DB/netværk.
    persisted: list[str] = []
    monkeypatch.setattr(
        vr, "_persist_session_assistant_message",
        lambda run, text, **_k: persisted.append(text))
    monkeypatch.setattr(vr, "append_chat_message", lambda **_k: {"id": "m1"})
    monkeypatch.setattr(vr, "record_cost", lambda **_k: None)
    monkeypatch.setattr(vr.event_bus, "publish", lambda *a, **k: None)
    # Tunge baggrunds-daemons (_post_process: memory-konsolidering/session-summary
    # → LLM-fallback-kæder) mockes → hermetisk + hurtigt. De er fire-and-forget
    # daemon-tråde der kører EFTER assertions; her gøres de til no-ops.
    monkeypatch.setattr(vr, "_run_memory_postprocess", lambda *a, **k: None)
    monkeypatch.setattr(vr, "_track_runtime_candidates", lambda *a, **k: None)
    # set_last_visible_run_outcome → _persist_visible_run_outcome →
    # write_private_terminal_layers udløser et SYNKRONT inner-voice-LLM-kald
    # (private_layer_pipeline) der ellers rammer netværket. No-op for hermetik.
    monkeypatch.setattr(vr, "write_private_terminal_layers", lambda *a, **k: None)

    # Fang ALLE followup-cluster-nerver (note_round/_failed/_loop_complete/...).
    # _observe er det fælles choke point alle note_*-kald ruter igennem.
    nerves: list[tuple[str, dict]] = []
    monkeypatch.setattr(fo, "_observe",
                        lambda nerve, run_id, **d: nerves.append((nerve, d)))

    run = vr.VisibleRun(
        run_id=run_id, lane="primary", provider="deepseek",
        model="deepseek-v4-flash", user_message="hej",
        session_id=f"s-{run_id}")

    async def _run() -> list[str]:
        out: list[str] = []
        with vf.fault_injection(shape, **inject_kwargs):
            async for chunk in vr._stream_visible_run(run):
                out.append(chunk)
        return out

    chunks = asyncio.run(_run())
    return _DriveResult(chunks, persisted, nerves)


# ── Harness/flag-enheds-tests (uden at drive et helt run) ────────────────────


def test_injector_is_strict_noop_when_disabled() -> None:
    """Prod-sikkerhed: uden registrering er hooket et NO-OP (ingen latency)."""
    vf.clear_faults()
    assert vf._maybe_inject_fault(0) is None
    # Dispatcher uden injektion + ukendt provider → den normale unsupported-sti
    # (beviser at hooket ikke kortslutter prod-stien).
    events = list(vf.stream_visible_followup(
        provider="__nonexistent__", model="m",
        base_messages=[], exchanges=[], round_index=0))
    assert len(events) == 1
    assert isinstance(events[0], vf.FollowupFailed)
    assert "unsupported-provider" in events[0].error


def test_injector_fire_once_clears_itself() -> None:
    """fire_once (default): injektionen forsvinder efter første dispatch."""
    with vf.fault_injection(vf.FAULT_CLEAN_FAIL_BEFORE_DELTA):
        first = list(vf.stream_visible_followup(
            provider="deepseek", model="m",
            base_messages=[], exchanges=[], round_index=0))
        assert isinstance(first[0], vf.FollowupFailed)
        # Andet kald INDE i samme kontekst → injektion allerede forbrugt → no-op.
        assert vf._maybe_inject_fault(0) is None
    assert vf._maybe_inject_fault(0) is None


def test_kill_switch_flag_default_off(monkeypatch) -> None:
    """AGENTIC_ROUND_RETRY_ENABLED er DEFAULT OFF (retry ikke bygget endnu)."""
    monkeypatch.delenv(vf._AGENTIC_ROUND_RETRY_ENV, raising=False)

    class _S:
        extra: dict = {}
    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: _S())
    assert vf.agentic_round_retry_enabled() is False


def test_kill_switch_flag_env_override_on(monkeypatch) -> None:
    """Env-override (JARVIS_AGENTIC_ROUND_RETRY=1) slår flaget TIL."""
    monkeypatch.setenv(vf._AGENTIC_ROUND_RETRY_ENV, "1")
    assert vf.agentic_round_retry_enabled() is True
    monkeypatch.setenv(vf._AGENTIC_ROUND_RETRY_ENV, "true")
    assert vf.agentic_round_retry_enabled() is True


def test_kill_switch_flag_env_override_off_wins_over_config(monkeypatch) -> None:
    """Env-override vinder over config (kill-switch-formål: slå FRA uden redeploy)."""
    monkeypatch.setenv(vf._AGENTIC_ROUND_RETRY_ENV, "off")

    class _S:
        extra = {"agentic_round_retry_enabled": True}  # config siger TIL …
    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: _S())
    assert vf.agentic_round_retry_enabled() is False  # … men env=off vinder.


def test_kill_switch_flag_reads_from_config_when_no_env(monkeypatch) -> None:
    """Uden env læses flaget fra runtime-config (settings.extra)."""
    monkeypatch.delenv(vf._AGENTIC_ROUND_RETRY_ENV, raising=False)

    class _S:
        extra = {"agentic_round_retry_enabled": True}
    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: _S())
    assert vf.agentic_round_retry_enabled() is True


# ── (a) clean_fail_before_delta — BASELINE ───────────────────────────────────


def test_clean_fail_before_delta_ends_interrupted_no_retry(monkeypatch) -> None:
    """En clean HTTP-502-fejl FØR nogen delta → turen ender afbrudt (intet retry).

    BASELINE: ingen rund-retry findes endnu, så et forbigående blip dræber turen.
    Fase 1 skal i stedet retry'e runden og lade turen overleve."""
    res = _drive(monkeypatch, vf.FAULT_CLEAN_FAIL_BEFORE_DELTA,
                 run_id="clean-fail")

    assert res.done_status == "interrupted", \
        "BASELINE: clean fail dræber turen (interrupted, intet retry)"
    assert res.has_terminal_frame(), "I2: en terminal-frame skal altid nå klienten"
    # Ingen partiel tekst → persisteret svar er KUN resume-noten (intet model-svar).
    assert "[search_memory]" not in res.persisted_text
    assert "afbrudt i agentic loopet" in res.persisted_text


def test_clean_fail_fires_followup_failed_nerve(monkeypatch) -> None:
    """Central-dækning: clean fail (yielded FollowupFailed) FYRER followup_failed.

    Dette er den OBSERVEREDE sti — modsat den raise-baserede drop nedenfor, der
    er SILENT (§2-hul). Dokumenteret kontrast."""
    res = _drive(monkeypatch, vf.FAULT_CLEAN_FAIL_BEFORE_DELTA,
                 run_id="clean-fail-nerve")
    assert "followup_failed" in res.nerve_names(), \
        "clean fail fyrer note_round_failed (yielded-FollowupFailed-stien)"


# ── (b) partial_deltas_then_drop — PRIMÆR — C11 + D11 BASELINE ────────────────


def test_partial_then_drop_C11_partial_text_persists(monkeypatch) -> None:
    """C11 BASELINE (dette er buggen; Fase 1 inverterer det):

    En runde der STREAMER partiel tekst og SÅ dropper → den partielle tekst står
    BÅDE live OG i det persisterede svar, selvom runden fejlede. Deltas appendes
    til _all_followup_parts (visible_runs.py:2211) og trunkeres ALDRIG ved fejl;
    de føder det persisterede svar (visible_runs.py:3043).

    EFTER Fase 1 (C11-fix): den partielle tekst skal KASSERES (snapshot+trunkér)
    og turen skal OVERLEVE via retry. Denne assertion FLIPPES da."""
    partials = ("partial-", "svar-", "før-drop")
    res = _drive(monkeypatch, vf.FAULT_PARTIAL_DELTAS_THEN_DROP,
                 run_id="partial-drop-c11",
                 partial_deltas=partials, drop_as_exception=True)

    joined = "".join(partials)
    # BASELINE: den partielle tekst er IKKE kasseret — den står i persisteringen.
    assert joined in res.persisted_text, \
        "BASELINE C11: partiel tekst IKKE kasseret — den persisteres trods fejl"
    # Den blev også streamet live (delta-events).
    delta_chunks = [c for c in res.chunks
                    if "event: delta" in c and '"delta"' in c]
    assert len(delta_chunks) >= len(partials), \
        "BASELINE C11: partielle deltas blev streamet live til klienten"
    # Turen DØR stadig (intet retry i baseline).
    assert res.done_status == "interrupted"


def test_partial_then_drop_raised_is_centrally_SILENT(monkeypatch) -> None:
    """§2-HUL BASELINE (dokumenterer den nuværende tavshed):

    Et transport-drop som RÅ exception (mest realistisk for en socket-drop)
    fanges af _pump_agentic's except (visible_runs.py:2090) → sætter _a_failure
    men fyrer ALDRIG note_round_failed (kun den yielded-FollowupFailed-sti gør,
    visible_runs.py:2241). Så den PRIMÆRE cut-klasse er i dag CENTRALT USYNLIG
    på round-failure-niveau.

    Fase 1/2 skal lukke dette (note_round_failed/note_round_retry på pump-except-
    stien). Denne assertion markerer hullet — den FLIPPES da."""
    res = _drive(monkeypatch, vf.FAULT_PARTIAL_DELTAS_THEN_DROP,
                 run_id="partial-drop-silent",
                 drop_as_exception=True)

    names = res.nerve_names()
    # BASELINE: round-failure er SILENT på den raise-baserede drop-sti.
    assert "followup_failed" not in names, \
        ("BASELINE §2-hul: raised transport-drop fyrer IKKE followup_failed "
         "(pump-except bypasser note_round_failed) — Fase 1/2 lukker dette")
    # Loop-complete fyrer dog stadig (turen afsluttes observerbart på tur-niveau).
    assert "followup_loop_complete" in names, \
        "turen afsluttes observerbart på loop-niveau (note_loop_complete)"
    # … og en terminal-frame når stadig klienten (I2 holder selv på den tavse sti).
    assert res.has_terminal_frame()
    assert res.done_status == "interrupted"


def test_partial_then_drop_yielded_DOES_fire_nerve(monkeypatch) -> None:
    """Kontrast til ovenstående: hvis drop'et yields som FollowupFailed (i stedet
    for at raise), FYRER note_round_failed. Beviser at hullet er sti-specifikt
    (raise vs yield), ikke generelt — så Fase 1's fix-mål er præcist lokaliseret."""
    res = _drive(monkeypatch, vf.FAULT_PARTIAL_DELTAS_THEN_DROP,
                 run_id="partial-drop-yield",
                 drop_as_exception=False)
    assert "followup_failed" in res.nerve_names(), \
        "yielded FollowupFailed fyrer note_round_failed (den observerede sti)"
    # C11 gælder uanset drop-form: partiel tekst persisteres stadig.
    assert "partial-" in res.persisted_text


# ── (c) http_400_overflow — BASELINE ─────────────────────────────────────────


def test_http_400_overflow_surfaces_as_failure_not_completed(monkeypatch) -> None:
    """context-window-overløb (HTTP 400) surfacer som en FEJL — IKKE et tavst
    'completed'. Distinkt fra et transport-drop (fatal, ikke retryable).

    BASELINE: i dag landes overløb som en generisk interruption uden et navngivet
    failure_kind. Fase 1 (S5/§4.7) skal give det et eget kind + lean-prompt-
    mitigering. Her asserterer vi blot at det ikke bliver tavst completed."""
    res = _drive(monkeypatch, vf.FAULT_HTTP_400_OVERFLOW,
                 run_id="http-400-overflow")

    assert res.done_status != "completed", \
        "overløb må ALDRIG ende tavst 'completed'"
    assert res.done_status == "interrupted"
    assert res.has_terminal_frame()
    # HTTP 400-konteksten er bevaret i det persisterede svar (sporbarhed).
    assert "HTTP 400" in res.persisted_text or "context_length" in res.persisted_text


def test_http_400_overflow_fires_followup_failed_nerve(monkeypatch) -> None:
    """Central-dækning: overløb (yielded FollowupFailed) FYRER followup_failed.
    (Modsat det raise-baserede transport-drop, der er silent.)"""
    res = _drive(monkeypatch, vf.FAULT_HTTP_400_OVERFLOW,
                 run_id="http-400-nerve")
    assert "followup_failed" in res.nerve_names()


# ── Oprydning: ingen injektion må lække mellem tests ──────────────────────────


@pytest.fixture(autouse=True)
def _no_fault_leak():
    vf.clear_faults()
    yield
    vf.clear_faults()
