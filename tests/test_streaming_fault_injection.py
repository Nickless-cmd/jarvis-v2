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
from core.services.stream_failure_kind import (
    FailureKind,
    classify_failure,
    is_retryable_kind,
)
from core.services.visible_model import (
    VisibleModelResult,
    VisibleModelStreamDone,
    VisibleModelToolCalls,
)


@pytest.fixture(autouse=True)
def _reset_provider_circuit_breaker():
    """Start every test with a clean provider circuit breaker.

    ``core.services.provider_circuit_breaker`` keeps its breaker state in
    module-level globals (``_FAILURES``, ``_OPENED_AT`` and the ``_PP``
    per-provider breaker). Other tests in the suite open/trip the breaker for
    a provider and don't reset it, so a leaked OPEN state leaks in and diverts
    the ``_drive`` streaming path — the followup nerves never fire and
    ``persisted_text`` comes back empty (the widespread nerve_names/persisted
    assertion failures in the full suite). Only the Fase-3 tests requested
    ``_breaker_clean`` explicitly; the baseline drive tests had no guard.
    Reset before AND after each test so this file neither inherits nor exports
    breaker pollution.
    """
    import core.services.provider_circuit_breaker as _cb

    _cb.reset_all()
    yield
    _cb.reset_all()


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

    def events_of(self, event_name: str) -> list[str]:
        """Alle SSE-chunks der bærer ``event: <event_name>``."""
        return [c for c in self.chunks if f"event: {event_name}" in c]

    def round_retry_nerves(self) -> list[dict]:
        return [d for n, d in self.nerves if n == "round_retry"]


def _drive(monkeypatch, shape: str, *, run_id: str,
           provider: str = "deepseek", model: str = "deepseek-v4-flash",
           central_nerves: list | None = None, **inject_kwargs) -> _DriveResult:
    """Driv ÉT minimalt agentisk followup-run gennem det ægte spor med en aktiv
    fejl-injektion. Returnerer opsamlet udfald.

    ``provider``/``model``: override run's visible-provider (til failover-tests).
    ``central_nerves``: hvis givet (en liste), opsamles ALLE ``central().observe``-
    payloads heri (breaker open/close + provider_failover lever her, ikke i fo._observe)."""

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

    # Fang breaker/failover-nerver der ruter gennem central().observe (cluster=
    # "stream") i stedet for fo._observe — kun hvis kalderen bad om det.
    if central_nerves is not None:
        class _CapCentral:
            def observe(self, payload):
                central_nerves.append(dict(payload or {}))
        # central() er importeret lazily inde i hot-stien → patch begge moduler.
        monkeypatch.setattr("core.services.central_core.central",
                            lambda: _CapCentral())

    run = vr.VisibleRun(
        run_id=run_id, lane="primary", provider=provider,
        model=model, user_message="hej",
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


def test_partial_then_drop_raised_no_longer_centrally_silent(monkeypatch) -> None:
    """§2-HUL LUKKET (B11 step 3 — denne assertion var tidligere baseline-SILENT):

    Et transport-drop som RÅ exception (mest realistisk for en socket-drop)
    fanges af _pump_agentic's except (visible_runs.py:2090). Det satte før
    _a_failure men fyrede ALDRIG note_round_failed → den PRIMÆRE cut-klasse var
    CENTRALT USYNLIG på round-failure-niveau.

    Nu fyrer pump-except-stien note_round_failed med den klassificerede
    failure_kind (B11). Break/retry-adfærd er UÆNDRET (turen dør stadig — retry-
    loopet 4.1 bygges senere); det er KUN nerven der er tilføjet."""
    res = _drive(monkeypatch, vf.FAULT_PARTIAL_DELTAS_THEN_DROP,
                 run_id="partial-drop-silent",
                 drop_as_exception=True)

    names = res.nerve_names()
    # FIX: round-failure er ikke længere tavs på den raise-baserede drop-sti.
    assert "followup_failed" in names, \
        ("B11-fix: raised transport-drop fyrer nu followup_failed "
         "(pump-except wirer note_round_failed)")
    # Loop-complete fyrer stadig (turen afsluttes observerbart på tur-niveau).
    assert "followup_loop_complete" in names, \
        "turen afsluttes observerbart på loop-niveau (note_loop_complete)"
    # … og en terminal-frame når stadig klienten (I2).
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


# ── B11: struktureret failure-taksonomi (single source of truth for I5) ──────


@pytest.mark.parametrize(
    "http_status, error_text, kind_hint, expect_kind, expect_retryable",
    [
        # ── retryable på samme provider ──
        (502, "HTTP 502 Bad Gateway", "", FailureKind.HTTP_5XX, True),
        (503, "service unavailable", "", FailureKind.HTTP_5XX, True),
        (504, "gateway timeout", "", FailureKind.HTTP_5XX, True),
        (500, "internal server error", "", FailureKind.HTTP_5XX, True),
        (429, "rate limited", "", FailureKind.HTTP_429, True),
        (None, "ConnectionError: connection reset by peer", "",
         FailureKind.TRANSIENT_DROP, True),
        (None, "stream closed before completed", "",
         FailureKind.TRANSIENT_DROP, True),
        (None, "<urlopen error [Errno 104] connection aborted>", "",
         FailureKind.TRANSIENT_DROP, True),
        (None, "JSONDecodeError: Expecting value: line 1", "",
         FailureKind.MALFORMED_STREAM_PAYLOAD, True),
        (None, "UnicodeDecodeError: 'utf-8' codec can't decode byte", "",
         FailureKind.MALFORMED_STREAM_PAYLOAD, True),
        # ── provider_stall: retryable-LOOKING men IKKE auto-retry (D11) ──
        (None, "round-silence-timeout: timed out waiting for provider stream item", "",
         FailureKind.PROVIDER_STALL, False),
        (None, "first-byte budget exceeded — no bytes", "",
         FailureKind.PROVIDER_STALL, False),
        # ── fatal ──
        (400, "context_length_exceeded: prompt too long for model context window", "",
         FailureKind.HTTP_400_OVERFLOW, False),
        (400, "prompt is too long: 208863, model maximum context length: 202752", "",
         FailureKind.HTTP_400_OVERFLOW, False),
        (400, "invalid_request_body", "", FailureKind.HTTP_4XX, False),
        (401, "unauthorized", "", FailureKind.HTTP_4XX, False),
        (403, "forbidden", "", FailureKind.HTTP_4XX, False),
        (404, "not found", "", FailureKind.HTTP_4XX, False),
        (422, "unprocessable entity", "", FailureKind.HTTP_4XX, False),
        (None, "generation cancelled by user", "", FailureKind.USER_CANCEL, False),
        # ── kind_hint vinder over alt ──
        (None, "whatever", FailureKind.USER_CANCEL, FailureKind.USER_CANCEL, False),
        (502, "HTTP 502", FailureKind.PROVIDER_STALL, FailureKind.PROVIDER_STALL, False),
        # ── ukendt → konservativt fatal ──
        (None, "something we have never seen", "", FailureKind.UNKNOWN, False),
        # ── status udledt fra fri-tekst når struktureret mangler ──
        (None, "followup-round-2-provider-error: HTTP 503", "",
         FailureKind.HTTP_5XX, True),
    ],
)
def test_classify_failure_taxonomy(
    http_status, error_text, kind_hint, expect_kind, expect_retryable
) -> None:
    """classify_failure er DEN ENE retryable/kind-sandhedskilde (I5).

    Spejler codex' split: transient_drop/5xx/429/malformed = retryable;
    provider_stall = retryable-LOOKING men IKKE auto-retry på samme provider
    (D11); 4xx/overflow/invalid/cancel = fatal."""
    kind, retryable = classify_failure(
        http_status=http_status, error_text=error_text, kind_hint=kind_hint)
    assert kind == expect_kind, f"{error_text!r} → {kind} (forventet {expect_kind})"
    assert retryable is expect_retryable
    # is_retryable_kind skal være konsistent med klassifikatorens retryable-flag.
    assert is_retryable_kind(kind) is expect_retryable


def test_classify_failure_provider_stall_is_not_retryable() -> None:
    """D11-invariant: provider_stall er ALDRIG retryable på samme provider
    (re-trigger blot samme timeout → circuit-breaker/failover, ikke retry)."""
    assert is_retryable_kind(FailureKind.PROVIDER_STALL) is False
    _, retryable = classify_failure(
        http_status=None, kind_hint=FailureKind.PROVIDER_STALL)
    assert retryable is False


def test_classify_failure_overflow_distinct_from_generic_400() -> None:
    """S5: context-window-overløb er en EGEN navngivet kind, ikke et tavst 400."""
    k_overflow, _ = classify_failure(
        http_status=400, error_text="prompt too long for context window")
    k_generic, _ = classify_failure(
        http_status=400, error_text="invalid_request_body")
    assert k_overflow == FailureKind.HTTP_400_OVERFLOW
    assert k_generic == FailureKind.HTTP_4XX
    assert k_overflow != k_generic


# ── B11: FollowupFailed bærer failure_kind + http_status ─────────────────────


def test_followup_failed_has_structured_fields_defaults() -> None:
    """Bagudkompat: de nye felter er OPTIONAL (default ""/None) så legacy-
    konstruktion (kun round_index/error/summary) ikke brækker."""
    f = vf.FollowupFailed(round_index=0, error="e", summary="s")
    assert f.failure_kind == ""
    assert f.http_status is None


def test_unsupported_provider_carries_invalid_request_kind() -> None:
    """Dispatcherens unsupported-provider-sti bærer nu failure_kind."""
    events = list(vf.stream_visible_followup(
        provider="__nope__", model="m",
        base_messages=[], exchanges=[], round_index=0))
    assert isinstance(events[0], vf.FollowupFailed)
    assert events[0].failure_kind == FailureKind.INVALID_REQUEST
    assert events[0].http_status is None


def test_injected_clean_fail_carries_http_5xx_kind() -> None:
    """Den injicerede HTTP-502-fejl bærer http_status=502 + http_5xx-kind
    (beviser populeringen på en yielded FollowupFailed-sti)."""
    with vf.fault_injection(vf.FAULT_CLEAN_FAIL_BEFORE_DELTA):
        events = list(vf.stream_visible_followup(
            provider="deepseek", model="m",
            base_messages=[], exchanges=[], round_index=0))
    failed = [e for e in events if isinstance(e, vf.FollowupFailed)]
    assert failed
    assert failed[0].http_status == 502
    assert failed[0].failure_kind == FailureKind.HTTP_5XX


def test_injected_overflow_carries_overflow_kind() -> None:
    """Det injicerede context-overløb (HTTP 400 'prompt too long') bærer
    http_400_overflow-kind (S5) — distinkt fra et transport-drop."""
    with vf.fault_injection(vf.FAULT_HTTP_400_OVERFLOW):
        events = list(vf.stream_visible_followup(
            provider="deepseek", model="m",
            base_messages=[], exchanges=[], round_index=0))
    failed = [e for e in events if isinstance(e, vf.FollowupFailed)]
    assert failed
    assert failed[0].http_status == 400
    assert failed[0].failure_kind == FailureKind.HTTP_400_OVERFLOW


# ── B11 step 3: raised-drop pump-except-sti FYRER nu note_round_failed ────────


def test_raised_drop_now_fires_followup_failed_nerve(monkeypatch) -> None:
    """§11.4-FIX (B11 step 3): et RAISED transport-drop (pump-except-stien,
    visible_runs.py:2090) fyrer nu note_round_failed med den klassificerede
    failure_kind. Tidligere var den PRIMÆRE cut-klasse CENTRALT TAVS på round-
    failure-niveau (kun den yielded-FollowupFailed-sti fyrede nerven).

    Dette INVERTERER baseline-assertionen i
    test_partial_then_drop_raised_is_centrally_SILENT (samme scenarie)."""
    res = _drive(monkeypatch, vf.FAULT_PARTIAL_DELTAS_THEN_DROP,
                 run_id="raised-drop-nerve", drop_as_exception=True)

    names = res.nerve_names()
    assert "followup_failed" in names, \
        "B11-fix: raised transport-drop fyrer nu note_round_failed (ikke længere tavs)"
    # Nerven bærer den klassificerede failure_kind (transient_drop = retryable)
    # + raised=True-markøren, så Centralen kan skelne pump-except fra yielded.
    failed_payloads = [d for n, d in res.nerves if n == "followup_failed"]
    assert any(
        d.get("failure_kind") == FailureKind.TRANSIENT_DROP and d.get("raised") is True
        for d in failed_payloads
    ), f"nerve skal bære transient_drop + raised=True; fik {failed_payloads}"
    # Break/retry-adfærd er UÆNDRET: turen dør stadig (ingen retry-loop endnu).
    assert res.done_status == "interrupted"
    assert res.has_terminal_frame()


def test_yielded_failed_nerve_carries_structured_kind(monkeypatch) -> None:
    """Den yielded-FollowupFailed-sti bærer nu også failure_kind i nerven
    (clean HTTP 502 → http_5xx, raised=False)."""
    res = _drive(monkeypatch, vf.FAULT_CLEAN_FAIL_BEFORE_DELTA,
                 run_id="yielded-kind-nerve")
    failed_payloads = [d for n, d in res.nerves if n == "followup_failed"]
    assert failed_payloads
    assert any(
        d.get("failure_kind") == FailureKind.HTTP_5XX and d.get("raised") is False
        for d in failed_payloads
    ), f"yielded-sti skal bære http_5xx + raised=False; fik {failed_payloads}"


# ── Fase 1: rund-niveau retry der bevarer turen (spec §4.1/C11/D11/E11) ──────
#
# Disse tests kører med kill-switchen ON (JARVIS_AGENTIC_ROUND_RETRY=1) og
# INVERTERER baseline-assertionerne ovenfor: turen OVERLEVER et forbigående
# mid-turn-blip, partiel tekst KASSERES (ingen dublet), pumpen FENCES (ingen
# orphan), og note_round_retry(recovered/exhausted) fyrer.


@pytest.fixture
def _retry_on(monkeypatch):
    """Slå kill-switchen ON via env (vinder over config)."""
    monkeypatch.setenv(vf._AGENTIC_ROUND_RETRY_ENV, "1")
    assert vf.agentic_round_retry_enabled() is True
    yield


def test_PRIMARY_partial_then_drop_retry_survives_no_dup(monkeypatch, _retry_on) -> None:
    """PRIMÆR Fase 1-accept (spec §11.3): partial-deltas-så-drop med retry ON.

    (i)  turen SURVIVER (completed, ikke interrupted),
    (ii) INGEN dubleret persisteret tekst — den partielle tekst fra det FEJLEDE
         forsøg er KASSERET (C11 snapshot+trunkér); kun recover-teksten persisteres,
    (iii) en round_restart_discard_partial-SSE blev emitteret (klient-discard-kontrakt),
    (iv) note_round_retry(outcome=recovered) fyrede."""
    partials = ("partial-", "svar-", "før-drop")
    res = _drive(monkeypatch, vf.FAULT_PARTIAL_DELTAS_THEN_DROP,
                 run_id="f1-primary",
                 partial_deltas=partials, drop_as_exception=True,
                 fire_once=False, fail_times=1, recover_text="DET-ÆGTE-SVAR")

    # (i) turen overlever.
    assert res.done_status == "completed", \
        "Fase 1: retry skal lade turen OVERLEVE et forbigående drop"

    # (ii) ingen dubleret tekst: den partielle (fejlede) tekst er kasseret;
    #      kun recover-teksten står i persisteringen.
    joined_partial = "".join(partials)
    assert "DET-ÆGTE-SVAR" in res.persisted_text, "recover-svaret skal persisteres"
    assert joined_partial not in res.persisted_text, \
        "C11: den partielle tekst fra det fejlede forsøg skal være KASSERET"
    # Recover-teksten må ikke dukke op to gange (ingen dobbelt-persist).
    assert res.persisted_text.count("DET-ÆGTE-SVAR") == 1

    # (iii) discard-kontrakten blev signaleret til klienten.
    assert res.events_of("round_restart_discard_partial"), \
        "C11: round_restart_discard_partial-SSE skal emitteres ved retry"

    # (iv) recovered-nerven fyrede.
    recovered = [d for d in res.round_retry_nerves() if d.get("outcome") == "recovered"]
    assert recovered, f"note_round_retry(recovered) skal fyre; fik {res.round_retry_nerves()}"

    # En "Reconnecting n/m"-retry-SSE blev også sendt (S4 synligt signal).
    assert res.events_of("retry"), "retry/Reconnecting-SSE skal emitteres"


def test_retry_no_second_concurrent_pump_fence(monkeypatch, _retry_on) -> None:
    """D11-fence: ingen anden SAMTIDIG pump / ingen orphan.

    Vi tæller hvor mange gange stream_visible_followup faktisk DISPATCHES og at
    den dødde generators ``close()`` blev kaldt (force-close af det fejlede
    forsøgs provider-stream) FØR det nye forsøg spawnes. Med fail_times=1 →
    præcis 2 dispatches (forsøg 1 fejler + close, forsøg 2 recoverer)."""
    closed: list[bool] = []
    real_dispatch = vf.stream_visible_followup
    dispatch_count = {"n": 0}

    def _counting_dispatch(**kw):
        dispatch_count["n"] += 1
        gen = real_dispatch(**kw)

        # Wrap generatoren så vi kan registrere close() (D11 force-close).
        class _TrackingGen:
            def __iter__(self):
                return self

            def __next__(self):
                return next(gen)

            def close(self):
                closed.append(True)
                return gen.close()

        return _TrackingGen()

    monkeypatch.setattr(vf, "stream_visible_followup", _counting_dispatch)

    res = _drive(monkeypatch, vf.FAULT_PARTIAL_DELTAS_THEN_DROP,
                 run_id="f1-fence",
                 drop_as_exception=True, fire_once=False,
                 fail_times=1, recover_text="OK")

    assert res.done_status == "completed"
    # Præcis 2 dispatches: ingen tredje samtidig pump.
    assert dispatch_count["n"] == 2, \
        f"forventede 2 dispatches (1 fejl + 1 recover); fik {dispatch_count['n']}"
    # Det fejlede forsøgs generator blev force-lukket (fence) før recover-spawn.
    assert closed, "D11: det fejlede forsøgs provider-stream skal force-closes (close())"


def test_exhaustion_emits_partial_and_interrupts_never_blank(monkeypatch, _retry_on) -> None:
    """E11/P6/S7-udmattelse: gentagne fejl udtømmer budgettet →
    note_round_retry(outcome=exhausted) + checkpointed partial + interruption —
    ALDRIG blank. Vi sætter fail_times højere end round_stream_max_retries (3),
    så ingen recover nogensinde lander."""
    # Tving et lavt budget så testen er hurtig+deterministisk.
    monkeypatch.setattr("core.services.affect_modulation.compute_agentic_loop_budget",
                        lambda **_k: {"max_rounds": 5,
                                      "round_stream_max_retries": 2,
                                      "turn_total_stream_retries": 12,
                                      "turn_total_wall_clock_s": 600.0,
                                      "round_total_timeout_s": 300.0,
                                      "round_silence_timeout_s": 180.0})

    res = _drive(monkeypatch, vf.FAULT_PARTIAL_DELTAS_THEN_DROP,
                 run_id="f1-exhaust",
                 partial_deltas=("nåede-", "lidt"), drop_as_exception=True,
                 fire_once=False, fail_times=99, recover_text="(uopnåelig)")

    # Udmattelse → interruption (ikke completed).
    assert res.done_status == "interrupted", \
        "udmattet retry-budget → interruption (de eksisterende semantikker)"
    # exhausted-nerven fyrede.
    exhausted = [d for d in res.round_retry_nerves() if d.get("outcome") == "exhausted"]
    assert exhausted, f"note_round_retry(exhausted) skal fyre; fik {res.round_retry_nerves()}"
    # ALDRIG blank: den ærlige udmattelses-note nåede klienten + persisteringen.
    assert "måtte give op" in res.persisted_text, \
        "P6: checkpointed partial + ærlig note må aldrig blive et tomt tab"
    assert res.has_terminal_frame()
    # Vi retry'ede præcis round_stream_max_retries (2) gange før vi gav op.
    assert any(int(d.get("attempt") or 0) == 2
               for d in res.round_retry_nerves()), \
        "skal have retry'et op til per-runde-loftet (2) før udmattelse"


def test_provider_stall_is_not_retried(monkeypatch, _retry_on) -> None:
    """D11: provider_stall (silence/idle-timeout) er IKKE retryable på samme
    provider → den skal gå direkte til interruption, ALDRIG retry.

    Vi simulerer en stall ved at lade pumpen hænge (ingen events, intet drop)
    indtil round-silence-watchdog'en fyrer. Vi sætter et meget lavt
    silence-timeout så testen er hurtig."""
    monkeypatch.setattr("core.services.affect_modulation.compute_agentic_loop_budget",
                        lambda **_k: {"max_rounds": 5,
                                      "round_stream_max_retries": 3,
                                      "turn_total_stream_retries": 12,
                                      "turn_total_wall_clock_s": 600.0,
                                      "round_total_timeout_s": 6.0,
                                      "round_silence_timeout_s": 2.0})

    # Stub stream_visible_followup til at hænge (yield intet, sov forbi
    # silence-timeout). Watchdog'en fyrer → provider_stall.
    def _stalling_dispatch(**_kw):
        import time as _t
        _t.sleep(4.0)  # > silence_timeout (2s) → watchdog fyrer
        return
        yield  # pragma: no cover (gør funktionen til en generator)

    monkeypatch.setattr(vf, "stream_visible_followup", _stalling_dispatch)

    res = _drive(monkeypatch, vf.FAULT_CLEAN_FAIL_BEFORE_DELTA,  # injektion ryddes ikke pga. stub
                 run_id="f1-stall")

    # Stall → interruption, og INGEN retry-nerve (provider_stall retries aldrig).
    assert res.done_status == "interrupted"
    assert not res.round_retry_nerves(), \
        "D11: provider_stall må ALDRIG udløse en round_retry"
    assert not res.events_of("retry"), \
        "D11: ingen Reconnecting-retry-SSE for en stall"


def test_flag_off_partial_then_drop_identical_to_baseline(monkeypatch) -> None:
    """Kill-switch OFF (eksplicit): partial-then-drop opfører sig BYTE-IDENTISK
    med baseline — turen dør, partiel tekst persisteres, INGEN retry-nerve/SSE.
    Spejler test_partial_then_drop_C11_partial_text_persists men asserter
    EKSPLICIT fraværet af enhver Fase-1-bivirkning."""
    monkeypatch.setenv(vf._AGENTIC_ROUND_RETRY_ENV, "0")
    assert vf.agentic_round_retry_enabled() is False

    partials = ("partial-", "svar-", "før-drop")
    res = _drive(monkeypatch, vf.FAULT_PARTIAL_DELTAS_THEN_DROP,
                 run_id="f1-flag-off",
                 partial_deltas=partials, drop_as_exception=True)

    assert res.done_status == "interrupted", "flag OFF → turen dør (baseline)"
    assert "".join(partials) in res.persisted_text, \
        "flag OFF → partiel tekst persisteres (baseline C11)"
    assert not res.round_retry_nerves(), "flag OFF → INGEN round_retry-nerve"
    assert not res.events_of("retry"), "flag OFF → INGEN retry-SSE"
    assert not res.events_of("round_restart_discard_partial"), \
        "flag OFF → INGEN discard-SSE"


# ═════════════════════════════════════════════════════════════════════════════
# Fase 3 (spec §4 S6, §11.2): per-provider circuit-breaker + provider-failover
# wired ind i den synlige rund-retry-beslutning. Komponerer med fail_times-
# harnessen: en DØD/vedvarende-fejlende provider skal kort-sluttes (breaker
# åbner) og faile over — IKKE retry-storme gennem tur-budgettet.
# ═════════════════════════════════════════════════════════════════════════════
import core.services.provider_circuit_breaker as _cbmod  # noqa: E402


@pytest.fixture
def _breaker_clean():
    """Frisk breaker-state før og efter hver Fase-3-test."""
    _cbmod.pp_reset_all()
    yield
    _cbmod.pp_reset_all()


@pytest.fixture
def _failover_on(monkeypatch):
    """Slå BÅDE round-retry OG provider-failover ON (failover bygger på begge)."""
    monkeypatch.setenv(vf._AGENTIC_ROUND_RETRY_ENV, "1")
    monkeypatch.setenv(vf._PROVIDER_FAILOVER_ENV, "1")
    assert vf.agentic_round_retry_enabled() is True
    assert vf.provider_failover_enabled() is True
    yield


def test_failover_flag_default_off(monkeypatch) -> None:
    """provider_failover_enabled er DEFAULT OFF (uafhængig kill-switch)."""
    monkeypatch.delenv(vf._PROVIDER_FAILOVER_ENV, raising=False)

    class _S:
        extra: dict = {}
    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: _S())
    assert vf.provider_failover_enabled() is False


def test_failover_flag_env_override(monkeypatch) -> None:
    monkeypatch.setenv(vf._PROVIDER_FAILOVER_ENV, "1")
    assert vf.provider_failover_enabled() is True
    monkeypatch.setenv(vf._PROVIDER_FAILOVER_ENV, "off")
    assert vf.provider_failover_enabled() is False


def test_pick_failover_target_basic(_breaker_clean) -> None:
    """pick_failover_target → ollama (gratis ollama-cloud) for en anden primær."""
    tgt = vf.pick_failover_target("groq", "some-model")
    assert tgt is not None
    assert tgt[0] == "ollama"
    assert "deepseek" in tgt[1]        # model = deepseek-v4-flash:cloud via ollama-cloud


def test_pick_failover_target_none_when_already_fallback(_breaker_clean) -> None:
    """Ingen failover fra ollama → ollama (kan ikke faile over til sig selv)."""
    assert vf.pick_failover_target("ollama", "deepseek-v4-flash:cloud") is None


def test_pick_failover_target_none_when_fallback_breaker_open(_breaker_clean) -> None:
    """Hvis fallback'ens (ollama) EGEN breaker er åben → ingen failover."""
    # Brug REAL monotonic (ingen now=) så pp_is_open()'s egen monotonic ser den åben.
    _cbmod.pp_configure("ollama", threshold=4, cooldown_s=60.0)
    for _ in range(4):
        _cbmod.pp_record_failure("ollama")
    assert _cbmod.pp_is_open("ollama") is True
    assert vf.pick_failover_target("groq", "m") is None


def test_breaker_opens_and_no_retry_storm(monkeypatch, _failover_on, _breaker_clean) -> None:
    """KOMPOSITION: en provider der bliver ved med at fejle (fail_times=99) åbner
    breakeren og bliver IKKE retry-stormet. Med en LAV breaker-threshold (2) på
    den aktive provider åbner breakeren FØR round-retry-budgettet (3) er brugt →
    vi falder til graceful exhaustion uden at hamre videre. provider_circuit_open-
    nerven fyrer (cluster=stream). Run-provider = deepseek → ingen failover-target
    (kan ikke faile over til sig selv) → ren breaker-stop-sti."""
    # Lav threshold så breakeren åbner hurtigt og deterministisk. Run-provider =
    # ollama = fallback'en selv → pick_failover_target returnerer None (ingen self-failover).
    _cbmod.pp_configure("ollama", threshold=2, cooldown_s=60.0)

    real_dispatch = vf.stream_visible_followup
    dispatch_count = {"n": 0}

    def _counting(**kw):
        dispatch_count["n"] += 1
        return real_dispatch(**kw)
    monkeypatch.setattr(vf, "stream_visible_followup", _counting)

    central_nerves: list[dict] = []
    res = _drive(monkeypatch, vf.FAULT_PARTIAL_DELTAS_THEN_DROP,
                 run_id="f3-breaker", provider="ollama",
                 model="deepseek-v4-flash:cloud",
                 central_nerves=central_nerves,
                 partial_deltas=("p-",), drop_as_exception=True,
                 fire_once=False, fail_times=99, recover_text="(uopnåelig)")

    # Breakeren åbnede → provider_circuit_open-nerve fyrede (cluster=stream).
    opens = [n for n in central_nerves if n.get("nerve") == "provider_circuit_open"]
    assert opens, f"provider_circuit_open skal fyre; fik {central_nerves}"
    assert opens[0]["cluster"] == "stream"
    assert opens[0]["provider_id"] == "ollama"

    # INGEN retry-storm: vi stoppede ved/omkring breaker-tærsklen, IKKE det fulde
    # round-retry-budget (som ellers ville give 1 + 3 = 4 dispatches). Med
    # threshold=2 åbner breakeren efter 2 fejl → klart < 4.
    assert dispatch_count["n"] <= 3, \
        f"breakeren skal stoppe retry-storm; fik {dispatch_count['n']} dispatches"

    # Aldrig blankt: turen ender med en terminal-frame.
    assert res.has_terminal_frame()
    assert res.done_status == "interrupted"


def test_failover_picks_ollama_when_primary_breaker_open(
        monkeypatch, _failover_on, _breaker_clean) -> None:
    """En primær (groq) hvis breaker åbner → failer over til ollama (gratis
    ollama-cloud) for resten af turen, og ollama's første kald RECOVERER.
    provider_failover-nerven fyrer (from=groq → to=ollama). Vi modellerer det via
    per-provider fail-styring: groq fejler altid, ollama lykkes."""
    # Groq's breaker åbner hurtigt (threshold 2); ollama er sund.
    _cbmod.pp_configure("groq", threshold=2, cooldown_s=60.0)

    # Provider-bevidst dispatch-stub: groq → transport-drop (raise), ollama →
    # clean FollowupDone. Vi behøver ikke fault-injektoren her.
    real_dispatch = vf.stream_visible_followup
    seen_providers: list[str] = []

    def _provider_aware(**kw):
        prov = (kw.get("provider") or "").lower()
        seen_providers.append(prov)

        def _gen():
            if prov == "ollama":
                yield vf.FollowupDelta(delta="FAILOVER-SVAR")
                yield vf.FollowupDone(text="")
            else:
                raise ConnectionError("groq socket closed before done")
        return _gen()
    monkeypatch.setattr(vf, "stream_visible_followup", _provider_aware)

    central_nerves: list[dict] = []
    res = _drive(monkeypatch, vf.FAULT_CLEAN_FAIL_BEFORE_DELTA,  # injektion uvirksom (stub overstyrer)
                 run_id="f3-failover", provider="groq", model="groq-model",
                 central_nerves=central_nerves)

    # provider_failover-nerven fyrede (from groq → to ollama).
    fos = [n for n in central_nerves if n.get("nerve") == "provider_failover"]
    assert fos, f"provider_failover skal fyre; fik {central_nerves}"
    assert fos[0]["from_provider"] == "groq"
    assert fos[0]["to_provider"] == "ollama"
    assert fos[0]["cluster"] == "stream"

    # Vi failede faktisk over: ollama blev dispatchet EFTER groq.
    assert "groq" in seen_providers and "ollama" in seen_providers
    assert seen_providers.index("ollama") > seen_providers.index("groq")

    # En provider_failover-SSE nåede klienten.
    assert res.events_of("provider_failover"), "provider_failover-SSE skal emitteres"

    # Turen OVERLEVEDE via fallback'en.
    assert res.done_status == "completed"
    assert "FAILOVER-SVAR" in res.persisted_text


def test_failover_off_breaker_open_no_failover(
        monkeypatch, _breaker_clean) -> None:
    """Round-retry ON men failover OFF: en åben breaker stopper retry-storm men
    failer IKKE over (flag-isolation) → graceful exhaustion, ingen provider_
    failover-nerve."""
    monkeypatch.setenv(vf._AGENTIC_ROUND_RETRY_ENV, "1")
    monkeypatch.setenv(vf._PROVIDER_FAILOVER_ENV, "0")
    _cbmod.pp_configure("groq", threshold=2, cooldown_s=60.0)

    central_nerves: list[dict] = []
    res = _drive(monkeypatch, vf.FAULT_PARTIAL_DELTAS_THEN_DROP,
                 run_id="f3-no-failover", provider="groq", model="groq-model",
                 central_nerves=central_nerves,
                 partial_deltas=("p-",), drop_as_exception=True,
                 fire_once=False, fail_times=99, recover_text="(uopnåelig)")

    assert not [n for n in central_nerves if n.get("nerve") == "provider_failover"], \
        "failover OFF → INGEN provider_failover-nerve"
    assert not res.events_of("provider_failover")
    # Breakeren observeres stadig (open er ubetinget af failover-flaget).
    assert [n for n in central_nerves if n.get("nerve") == "provider_circuit_open"]
    assert res.has_terminal_frame()


def test_provider_stall_counts_toward_breaker(
        monkeypatch, _failover_on, _breaker_clean) -> None:
    """provider_stall tæller MOD at åbne breakeren (en stallende provider FEJLER)
    selvom den ikke retries på samme provider. Vi driver gentagne stalls og
    verificerer at breaker-failures akkumulerer for den aktive provider."""
    _cbmod.pp_configure("deepseek", threshold=2, cooldown_s=60.0)
    monkeypatch.setattr("core.services.affect_modulation.compute_agentic_loop_budget",
                        lambda **_k: {"max_rounds": 3,
                                      "round_stream_max_retries": 3,
                                      "turn_total_stream_retries": 12,
                                      "turn_total_wall_clock_s": 600.0,
                                      "round_total_timeout_s": 6.0,
                                      "round_silence_timeout_s": 2.0})

    def _stalling(**_kw):
        import time as _t
        _t.sleep(4.0)  # > silence-timeout → watchdog → provider_stall
        return
        yield  # pragma: no cover

    monkeypatch.setattr(vf, "stream_visible_followup", _stalling)

    central_nerves: list[dict] = []
    res = _drive(monkeypatch, vf.FAULT_CLEAN_FAIL_BEFORE_DELTA,
                 run_id="f3-stall-breaker", provider="deepseek",
                 model="deepseek-v4-flash", central_nerves=central_nerves)

    # En stall-fejl blev registreret mod breakeren (consecutive ≥ 1).
    snap = _cbmod.pp_snapshot("deepseek")
    assert snap.get("consecutive", 0) >= 1, \
        f"provider_stall skal tælle mod breakeren; snap={snap}"
    # provider_stall retries ALDRIG på samme provider (D11 bevaret).
    assert not res.round_retry_nerves()
    assert res.has_terminal_frame()
