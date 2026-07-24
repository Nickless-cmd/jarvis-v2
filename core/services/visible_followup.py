"""Provider-neutral agentic follow-up dispatcher.

The visible-chat agentic loop sends the assistant's tool_calls to the provider
and streams the follow-up response (which may be more tool_calls or final
prose). Before this module existed the loop was hardcoded to Ollama's
``/api/chat`` NDJSON endpoint — for non-Ollama visible providers like GitHub
Copilot that either hung or hit the wrong backend.

This module exposes :func:`stream_visible_followup` which delegates to a
per-provider :class:`FollowupAdapter`. Each adapter:

1. Builds a provider-native request carrying the prior conversation, the
   assistant's tool_calls, and the executed tool results.
2. Streams the response as :class:`FollowupEvent` values (deltas, new tool
   calls, done, or failed).

Adapters never emit user-visible SSE directly; the caller translates
``FollowupEvent`` into SSE + persistence, enforcing the presentation
invariant at a single choke point.

Structure (2026-07-07 split of a 2024-line god-file into cohesive units —
this module stays the public facade and re-exports everything for backward
compatibility, so ``from core.services.visible_followup import X`` keeps
working for every symbol):

- ``visible_followup_events``    — FollowupEvent/carrier dataclasses + protocol
- ``visible_followup_lean``      — lean agentic-round-prompt transform + flag
- ``visible_followup_adapters``  — the 3 per-provider adapters
- (this file)                    — registry, dispatcher, synthesize helpers,
                                    kill-switches, and the fault-injection harness
"""

from __future__ import annotations

import json  # noqa: F401 — re-exported for backward-compat (pre-split facade symbol)
import logging
import os
import threading
import time  # noqa: F401 — re-exported for backward-compat (pre-split facade symbol)
from dataclasses import dataclass  # noqa: F401 — re-exported (pre-split facade symbol)
from typing import Iterator, Protocol, runtime_checkable  # noqa: F401 — Protocol/runtime_checkable re-exported

# Re-export shared failure taxonomy (some callers import these from here).
from core.services.stream_failure_kind import (  # noqa: F401
    FailureKind,
    MalformedStreamPayload,
    classify_failure,
    compute_backoff_with_jitter,
    safe_decode_line,
    try_parse_json_line,
)

# ── Re-exports from the split submodules (backward-compat facade) ────────────
# Everything importable from this module before the split stays importable.
# urllib_request / urllib_error are re-exported so tests that patch
# ``visible_followup.urllib_request.urlopen`` keep working (the adapters use
# the same module objects).
from urllib import error as urllib_error  # noqa: F401
from urllib import request as urllib_request  # noqa: F401

from core.services.visible_followup_events import (  # noqa: F401
    FollowupAdapter,
    FollowupDelta,
    FollowupDone,
    FollowupEvent,
    FollowupFailed,
    FollowupReasoningDelta,
    FollowupToolCalls,
    ToolExchange,
    ToolResult,
    _observe_malformed_stream_payload,
)
from core.services.visible_followup_lean import (  # noqa: F401
    _AGENTIC_LEAN_PROMPT_ENV,
    _LEAN_KEEP_ROW_PREFIXES,
    _LEAN_TAIL_START_MARKERS,
    _lean_strip_user_message,
    _split_on_double_newline,
    agentic_lean_prompt_enabled,
    build_lean_base_messages,
)
from core.services.visible_followup_adapters import (  # noqa: F401
    _OLLAMA_MAX_FOLLOWUP_EXCHANGES,
    _OLLAMA_MAX_TOOL_RESULT_CHARS,
    CodexFollowupAdapter,
    OllamaFollowupAdapter,
    OpenAICompatFollowupAdapter,
)

_log = logging.getLogger(__name__)


# ── Registry / dispatcher ────────────────────────────────────────────────────


_OLLAMA_ADAPTER = OllamaFollowupAdapter()
_COPILOT_ADAPTER = OpenAICompatFollowupAdapter(provider_id="github-copilot")

_ADAPTERS: dict[str, FollowupAdapter] = {
    "ollama": _OLLAMA_ADAPTER,
    "github-copilot": _COPILOT_ADAPTER,
    # Share a single OpenAICompatFollowupAdapter instance per openai-compat
    # provider so agentic tool-calling loops work for the same providers the
    # visible lane can already dispatch to (see cheap_provider_runtime
    # _OPENAI_COMPATIBLE_PROVIDERS).
    "opencode": OpenAICompatFollowupAdapter(provider_id="opencode"),
    "groq": OpenAICompatFollowupAdapter(provider_id="groq"),
    "openrouter": OpenAICompatFollowupAdapter(provider_id="openrouter"),
    "mistral": OpenAICompatFollowupAdapter(provider_id="mistral"),
    "nvidia-nim": OpenAICompatFollowupAdapter(provider_id="nvidia-nim"),
    "sambanova": OpenAICompatFollowupAdapter(provider_id="sambanova"),
    "deepseek": OpenAICompatFollowupAdapter(provider_id="deepseek"),
    # Codex Responses API — own adapter (function_call/function_call_output replay)
    # so gpt-5.4-mini / gpt-5.x can complete agentic tool-calling turns.
    "openai-codex": CodexFollowupAdapter(),
}


def supported_followup_providers() -> tuple[str, ...]:
    """Provider ids with a working follow-up adapter.

    Used by ``visible_runs.py`` to decide whether to enter the agentic loop
    at all. Providers not in this set fall back to persisting the first-pass
    text (already streamed live) as the assistant response.
    """
    return tuple(sorted(_ADAPTERS.keys()))


def stream_visible_followup(
    *,
    provider: str,
    model: str,
    base_messages: list[dict],
    exchanges: list[ToolExchange],
    tool_definitions: list[dict] | None = None,
    round_index: int = 0,
    thinking_mode: str = "think",
    temperature: float | None = None,
    top_p: float | None = None,
    tool_choice: str | None = None,
    run_id: str = "",
    autonomous: bool = False,
) -> Iterator[FollowupEvent]:
    """Dispatch to the provider's follow-up adapter; yield FollowupEvents.

    ``base_messages`` is the conversation *without* tool turns (pure
    user/assistant prose). ``exchanges`` is the chronological list of tool
    rounds (assistant_tool_calls + results) that should be replayed to the
    model in the provider-native shape.

    For unsupported providers a single :class:`FollowupFailed` is yielded so
    the caller can record a trace event and fall back cleanly.
    """
    # Fejl-injektions-hook (Fase 0) — STRENGT prod-no-op når intet er registreret
    # (returnerer None øjeblikkeligt). Test/repro-script registrerer via inject_fault().
    _injected = _maybe_inject_fault(round_index)
    if _injected is not None:
        yield from _injected
        return
    adapter = _ADAPTERS.get((provider or "").strip().lower())
    if adapter is None:
        yield FollowupFailed(
            round_index=round_index,
            error=f"unsupported-provider:{provider}",
            summary=f"followup-round-{round_index + 1}-unsupported-provider:{provider}",
            # No adapter exists for this provider — re-sampling cannot heal it.
            failure_kind=FailureKind.INVALID_REQUEST,
            http_status=None,
        )
        return
    # Only the OllamaFollowupAdapter currently honors thinking_mode; the
    # OpenAI-compat adapter ignores unknown kwargs gracefully if added later.
    _kwargs: dict = dict(
        model=model,
        base_messages=base_messages,
        exchanges=exchanges,
        tool_definitions=tool_definitions,
        round_index=round_index,
    )
    if isinstance(adapter, OllamaFollowupAdapter):
        _kwargs["thinking_mode"] = thinking_mode
    # Temperatur/top_p honoreres af de to sampling-providere (ollama + openai-
    # compat). Codex/Copilot-adapterne tager dem ikke → send kun hvor de findes.
    if isinstance(adapter, (OllamaFollowupAdapter, OpenAICompatFollowupAdapter)):
        if temperature is not None:
            _kwargs["temperature"] = temperature
        if top_p is not None:
            _kwargs["top_p"] = top_p
    # tool_choice="none" tvinger prosa UDEN at fjerne tools-arrayet → [system,tools]-
    # prefixet forbliver byte-stabilt på tværs af runder (cache-fix). Kun openai-
    # compat (deepseek-stien) honorerer det i payloaden.
    if isinstance(adapter, OpenAICompatFollowupAdapter) and tool_choice is not None:
        _kwargs["tool_choice"] = tool_choice
    # Cache-telemetri-kontekst (kun openai-compat-adapteren bruger det i dag).
    if isinstance(adapter, OpenAICompatFollowupAdapter):
        _kwargs["run_id"] = run_id
        _kwargs["autonomous"] = autonomous
    yield from adapter.stream_followup(**_kwargs)


def synthesize_nonthinking_rescue(
    *,
    provider: str,
    model: str,
    base_messages: list[dict],
    exchanges: list["ToolExchange"],
) -> str:
    """Sidste-udvejs synteseturn der OMGÅR DeepSeek #1453 (tom completion efter
    tool-kald).

    DeepSeek-V3 issue #1453 (verificeret 2026-06-30): thinking-modellerne
    (deepseek-v4-flash/v4-pro/reasoner) returnerer INTERMITTENT et helt tomt svar
    (content="", reasoning_content="", completion_tokens=0, HTTP 200) når tool-
    resultater fødes tilbage — og bliver ved at være tomme ved retry i SAMME
    thinking-kontekst. Den eneste kendte kur er at undgå thinking-maskineriet.

    Denne funktion kører ÉN frisk syntese-runde med den NON-thinking compat-alias
    (deepseek-chat) UDEN tools (force-prose), med fuld kontekst (base_messages +
    tool-exchanges). deepseek-chat har ikke reasoning_content-protokollen der
    trigger #1453, så den kan formulere svaret når thinking-stien choker. Kaldes
    KUN når den agentiske loop allerede ENDTE tom efter tool-kald — derfor rent
    additiv: værste fald er den også returnerer tom, og vi falder igennem til den
    eksisterende fallback. Idempotent: ingen tools eksekveres, kun syntese.

    Returnerer den syntetiserede tekst (strippet) eller "" ved enhver fejl/tomhed.
    Synkron (dran den interne generator) — kald via asyncio.to_thread fra async-
    stien så event-loopet ikke blokeres. Self-safe: kaster aldrig."""
    try:
        _pid = (provider or "").strip().lower()
        # Kun DeepSeek thinking-modeller rammes af #1453. Andre providere (eller
        # deepseek-chat selv) har ikke bug'en → ingen rescue (undgå dobbelt-svar).
        if _pid != "deepseek":
            return ""
        if model not in ("deepseek-v4-flash", "deepseek-v4-pro", "deepseek-reasoner"):
            return ""
        from core.services.cheap_provider_runtime import deepseek_model_for_thinking_mode
        _chat_model = deepseek_model_for_thinking_mode(model, "fast")
        if _chat_model == model:
            # Intet ægte swap (uventet) → drop hellere end at gentage thinking-kaldet.
            return ""
        # FollowupDone.text == "".join(deltas) i adapterne — så brug Done.text som
        # autoritativ (undgå dobling), fald tilbage på akkumulerede deltas hvis
        # runden afsluttede uden et eksplicit Done (fejl/afbrud).
        # Lav temp til den faktuelle syntese (samme anti-hallucination-setting
        # som de agentiske runder). Frakoblet ved negativ værdi.
        _r_temp: float | None = 0.3
        _r_top_p: float | None = 0.9
        try:
            from core.runtime.settings import load_settings as _ld_r
            _st_r = _ld_r()
            _r_temp = float(getattr(_st_r, "agentic_followup_temperature", 0.3))
            _r_top_p = float(getattr(_st_r, "agentic_followup_top_p", 0.9))
            if _r_temp < 0:
                _r_temp = None
            if _r_top_p < 0:
                _r_top_p = None
        except Exception:
            pass
        _delta_parts: list[str] = []
        _done_text = ""
        for _ev in stream_visible_followup(
            provider=provider,
            model=_chat_model,
            base_messages=base_messages,
            exchanges=exchanges,
            tool_definitions=None,   # force-prose: ingen flere tool-runder
            round_index=900,         # rescue-marker (uden for normalt rundetal)
            thinking_mode="fast",
            temperature=_r_temp,
            top_p=_r_top_p,
        ):
            if isinstance(_ev, FollowupDelta):
                _delta_parts.append(_ev.delta)
            elif isinstance(_ev, FollowupDone):
                _done_text = str(_ev.text or "")
            elif isinstance(_ev, FollowupFailed):
                # Rescue fejlede selv → giv op (den ydre fallback tager over).
                break
        return (_done_text or "".join(_delta_parts)).strip()
    except Exception:
        return ""


def synthesize_final_answer(
    *,
    provider: str,
    model: str,
    base_messages: list[dict],
    exchanges: list["ToolExchange"],
) -> str:
    """HARNESS-FINALIZE lag 2b (Bjørn 4. jul, provider-AGNOSTISK): ét tool-FRIT
    syntese-kald der TVINGER prosa fra HVILKEN SOM HELST model/lane, når den
    agentiske finalize-runde stadig endte tom.

    Modsat synthesize_nonthinking_rescue (deepseek-#1453-specifik) virker denne på
    ALLE providere: den fjerner tools fysisk (tool_definitions=None → hver adapter
    udelader tools-arrayet) OG appender en eksplicit "skriv dit endelige svar nu"-
    instruktion, så selv en model der ignorerer tool_choice MÅ producere prosa. For
    deepseek-thinking-modeller swappes til non-thinking chat-aliaset (omgår #1453).

    Rent additiv + idempotent (ingen tools eksekveres). Kaldes KUN når followup_text
    allerede er tom → værste fald returnerer også tom, og den deterministiske
    floor (genbrug streamede bytes / templated resume) tager over. Self-safe.
    Synkron — kald via asyncio.to_thread fra async-stien."""
    try:
        _pid = (provider or "").strip().lower()
        _use_model = model
        # deepseek-thinking → swap til chat-alias (ellers re-trigger #1453).
        if _pid == "deepseek" and model in (
                "deepseek-v4-flash", "deepseek-v4-pro", "deepseek-reasoner"):
            try:
                from core.services.cheap_provider_runtime import deepseek_model_for_thinking_mode
                _swap = deepseek_model_for_thinking_mode(model, "fast")
                if _swap and _swap != model:
                    _use_model = _swap
            except Exception:
                pass
        _r_temp: float | None = 0.3
        _r_top_p: float | None = 0.9
        try:
            from core.runtime.settings import load_settings as _ld_r
            _st_r = _ld_r()
            _r_temp = float(getattr(_st_r, "agentic_followup_temperature", 0.3))
            _r_top_p = float(getattr(_st_r, "agentic_followup_top_p", 0.9))
            if _r_temp < 0:
                _r_temp = None
            if _r_top_p < 0:
                _r_top_p = None
        except Exception:
            pass
        # Eksplicit finalize-instruktion (append-only → cache-prefix urørt).
        _finalize_msgs = list(base_messages) + [{
            "role": "user",
            "content": (
                "Skriv nu dit endelige svar til brugeren i prosa, baseret på "
                "værktøjs-resultaterne ovenfor. Kald IKKE værktøjer — opsummer "
                "hvad du fandt og svar direkte."),
        }]
        _delta_parts: list[str] = []
        _done_text = ""
        for _ev in stream_visible_followup(
            provider=provider,
            model=_use_model,
            base_messages=_finalize_msgs,
            exchanges=exchanges,
            tool_definitions=None,   # force-prose: ingen tools på NOGEN adapter
            round_index=901,         # finalize-synthese-marker
            thinking_mode="fast",
            temperature=_r_temp,
            top_p=_r_top_p,
        ):
            if isinstance(_ev, FollowupDelta):
                _delta_parts.append(_ev.delta)
            elif isinstance(_ev, FollowupDone):
                _done_text = str(_ev.text or "")
            elif isinstance(_ev, FollowupFailed):
                break
        return (_done_text or "".join(_delta_parts)).strip()
    except Exception:
        return ""


# ── Kill-switch: AGENTIC_ROUND_RETRY_ENABLED (Fase 0, P1) ────────────────────
#
# Den ENE sandhedskilde for om rund-niveau stream-retry (§4.1, Fase 1) er aktiv.
# I dag DEFAULT OFF — selve retry-logikken er ikke bygget endnu; flaget eksisterer
# så Fase 1 kan gate på det og vi kan slå retry FRA uden redeploy hvis den opfører
# sig forkert (spec §9 P1). At slå retry FRA må ALDRIG slå terminal-frame (I2) eller
# en nerve (I4) fra — de er ubetingede; flaget styrer KUN retry-grenen.
#
# Læses dual (samme mønster som ``read_runtime_key(env_override=...)``):
#   1. env ``JARVIS_AGENTIC_ROUND_RETRY`` vinder når sat til en sandheds-værdi.
#   2. ellers runtime-config ``settings.extra["agentic_round_retry_enabled"]``.
# Begge fejl-sikre → False (retry findes ikke endnu, så fail-closed er korrekt).

_AGENTIC_ROUND_RETRY_ENV = "JARVIS_AGENTIC_ROUND_RETRY"
_TRUTHY = ("1", "true", "yes", "on")
_FALSY = ("0", "false", "no", "off")


def agentic_round_retry_enabled() -> bool:
    """Er rund-niveau stream-retry (Fase 1) slået til? Default False.

    Env-override (``JARVIS_AGENTIC_ROUND_RETRY``) vinder over runtime-config.
    Selv-sikker: enhver fejl → False (fail-closed; retry findes ikke endnu)."""
    env_value = os.environ.get(_AGENTIC_ROUND_RETRY_ENV)
    if env_value is not None:
        val = env_value.strip().lower()
        if val in _TRUTHY:
            return True
        if val in _FALSY:
            return False
        # Ukendt env-værdi → fald tilbage til config (ignorér uparselbart env).
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().extra.get("agentic_round_retry_enabled", False))
    except Exception:
        return False


# ── Kill-switch: PROVIDER_FAILOVER (spec §4 S6, §11.2) ───────────────────────
#
# Den ENE sandhedskilde for om visible-lane PROVIDER-FAILOVER (Fase 3) er aktiv.
# DEFAULT OFF (fail-closed) → byte-identisk med i dag (ingen failover-re-sample;
# en åben breaker / fatal-men-failover-bar fejl falder til graceful exhaustion).
# UAFHÆNGIGT af ``agentic_round_retry_enabled()`` så failover kan slås til separat.
# Dual-læsning (samme mønster):
#   1. env ``JARVIS_PROVIDER_FAILOVER`` vinder når sat til en sandheds-værdi.
#   2. ellers runtime-config ``settings.extra["provider_failover_enabled"]``.
# At slå failover FRA må ALDRIG slå terminal-frame (I2) / nerve (I4) / circuit-
# breaker-observabilitet fra — flaget styrer KUN selve re-sample-på-fallback-grenen.

_PROVIDER_FAILOVER_ENV = "JARVIS_PROVIDER_FAILOVER"

# Den dokumenterede pålidelige fallback (reference_glm52_ttft_cancel: deepseek-
# v4-flash:cloud, TTFT 11-17s). Ét sted så failover-målet er entydigt.
# Fix 2026-07-16: provideren var 'deepseek' (betalt) MED et ':cloud'-modelnavn —
# deepseek.com afviser ':cloud'-tag'et (HTTP 400), og baggrunds-failover til betalt
# deepseek bryder Bjørn-reglen (betalt deepseek KUN i visible lane). deepseek-v4-flash
# :cloud er en OLLAMA-cloud-model → provideren skal være 'ollama' (gratis + gyldigt tag).
_FAILOVER_FALLBACK_PROVIDER = "ollama"
_FAILOVER_FALLBACK_MODEL = "deepseek-v4-flash:cloud"


def provider_failover_enabled() -> bool:
    """Er visible-lane provider-failover (Fase 3, spec §11.2) slået til? Default False.

    Env-override (``JARVIS_PROVIDER_FAILOVER``) vinder over runtime-config.
    Selv-sikker: enhver fejl → False (fail-closed; ingen failover-re-sample)."""
    env_value = os.environ.get(_PROVIDER_FAILOVER_ENV)
    if env_value is not None:
        val = env_value.strip().lower()
        if val in _TRUTHY:
            return True
        if val in _FALSY:
            return False
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().extra.get("provider_failover_enabled", False))
    except Exception:
        return False


def pick_failover_target(
    current_provider: str, current_model: str
) -> tuple[str, str] | None:
    """Vælg en kendt-pålidelig fallback-provider for RESTEN af denne tur (S6/§11.2).

    Returnerer ``(provider, model)`` eller ``None`` hvis ingen meningsfuld failover
    findes (fx vi er ALLEREDE på fallback'en → undgå at faile over til os selv,
    eller fallback'ens EGEN breaker er åben → den er også død).

    Default-målet er ``ollama``/``deepseek-v4-flash:cloud`` — samme model, men via
    den GRATIS ollama-cloud-sti (Bjørns free-tier) i stedet for betalt deepseek
    direkte. Self-safe: enhver fejl → None (→ graceful exhaustion)."""
    try:
        cur_p = (current_provider or "").strip().lower()
        fb_p = _FAILOVER_FALLBACK_PROVIDER.strip().lower()
        # Allerede på fallback'en (samme provider) → ingen meningsfuld failover.
        if cur_p == fb_p:
            return None
        # Fallback'en skal selv være en understøttet followup-provider.
        try:
            if fb_p not in {p.strip().lower() for p in supported_followup_providers()}:
                return None
        except Exception:
            pass
        # Fallback'ens EGEN breaker åben → den er også død; ingen failover.
        try:
            from core.services import provider_circuit_breaker as _cb
            if _cb.pp_is_open(fb_p):
                return None
        except Exception:
            pass
        return (_FAILOVER_FALLBACK_PROVIDER, _FAILOVER_FALLBACK_MODEL)
    except Exception:
        return None


# ── Fejl-injektions-harness (Fase 0, P7) — TEST-ONLY, prod-no-op ─────────────
#
# Tvinger ``stream_visible_followup`` til at producere de tre fejl-former spec'en
# kræver (§11.2 "Fase 0-harness 3 former"). STRENGT NO-OP i produktion: hvis intet
# er registreret returnerer ``_maybe_inject_fault`` øjeblikkeligt uden allokering
# eller latency. Et MODUL-NIVEAU registry (ikke ContextVar) er valgt med vilje:
# pumpen kører i en ``run_in_executor``-tråd UDEN ``copy_context`` (visible_runs.py
# ~2107), så en ContextVar sat i test-tråden ville være usynlig i pump-tråden.
# Et proces-globalt registry er trådsynligt + deterministisk + trivielt at rydde.
#
# Genbrugelig af BÅDE pytest OG en manuel repro-scriptet via inject_fault()/clear.

# Tre kanoniske fejl-former (spec §11.2 / Fase 0):
FAULT_CLEAN_FAIL_BEFORE_DELTA = "clean_fail_before_delta"
FAULT_PARTIAL_DELTAS_THEN_DROP = "partial_deltas_then_drop"  # PRIMÆR (trigger for C11/D11)
FAULT_HTTP_400_OVERFLOW = "http_400_overflow"

_KNOWN_FAULTS = frozenset({
    FAULT_CLEAN_FAIL_BEFORE_DELTA,
    FAULT_PARTIAL_DELTAS_THEN_DROP,
    FAULT_HTTP_400_OVERFLOW,
})

# Aktiv injektion (kun ÉN ad gangen — turen er sekventiel). None = prod-no-op.
_active_fault: dict | None = None
_fault_lock = threading.Lock()


def inject_fault(
    shape: str,
    *,
    partial_deltas: tuple[str, ...] = ("partial-", "svar-", "før-drop"),
    drop_as_exception: bool = True,
    http_status: int = 400,
    fire_once: bool = True,
    fail_times: int | None = None,
    recover_text: str = "recovered-final-answer",
) -> None:
    """Registrér en fejl-injektion for NÆSTE ``stream_visible_followup``-kald.

    TEST-ONLY. Skal altid parres med ``clear_faults()`` (brug context-manageren
    ``fault_injection()`` for garanteret oprydning).

    - ``shape``: én af FAULT_* (clean_fail_before_delta / partial_deltas_then_drop /
      http_400_overflow).
    - ``partial_deltas``: for partial_deltas_then_drop — teksten der streames FØR drop.
    - ``drop_as_exception``: for partial_deltas_then_drop — om drop'et er en RÅ
      exception (transport-drop, fanges af pumpens except → ingen note_round_failed;
      dokumenterer §2-hullet) eller et yielded FollowupFailed (observer fyrer).
    - ``http_status``: for http_400_overflow — HTTP-koden (default 400).
    - ``fire_once``: ryd registreringen efter første injektion (én runde).
    - ``fail_times``: Fase 1 retry-harness. Hvis sat: fejl de FØRSTE ``fail_times``
      dispatch-kald (samme runde re-samples via round-retry), og lad kald nr.
      ``fail_times+1`` LYKKES med en clean FollowupDone(``recover_text``). Kræver
      ``fire_once=False`` (injektionen skal overleve flere dispatch-kald). Med
      ``fail_times=None`` (default) er adfærden uændret (fire-once enkelt-fejl).
    - ``recover_text``: den endelige tekst det recoverede kald yielder.
    """
    if shape not in _KNOWN_FAULTS:
        raise ValueError(f"ukendt fault-shape: {shape!r} (kendte: {sorted(_KNOWN_FAULTS)})")
    with _fault_lock:
        global _active_fault
        _active_fault = {
            "shape": shape,
            "partial_deltas": tuple(partial_deltas),
            "drop_as_exception": bool(drop_as_exception),
            "http_status": int(http_status),
            "fire_once": bool(fire_once),
            "fail_times": (None if fail_times is None else int(fail_times)),
            "recover_text": str(recover_text),
            "_calls": 0,  # dispatch-tæller (til fail_times-recovery)
        }


def clear_faults() -> None:
    """Fjern enhver aktiv injektion. Idempotent. TEST-ONLY."""
    with _fault_lock:
        global _active_fault
        _active_fault = None


class fault_injection:
    """Context-manager der registrerer en injektion + RYDDER den ved exit
    (også ved exception). Foretrukne måde at bruge harnessen i pytest/repro.

    Eksempel::

        with fault_injection(FAULT_PARTIAL_DELTAS_THEN_DROP):
            ... drive et agentisk run ...
    """

    def __init__(self, shape: str, **kwargs) -> None:
        self._shape = shape
        self._kwargs = kwargs

    def __enter__(self) -> "fault_injection":
        inject_fault(self._shape, **self._kwargs)
        return self

    def __exit__(self, *_exc) -> bool:
        clear_faults()
        return False


def _maybe_inject_fault(round_index: int) -> Iterator[FollowupEvent] | None:
    """Prod-no-op hook: returnér en event-iterator hvis en injektion er aktiv,
    ellers None (øjeblikkeligt — ingen latency/allokering i den varme prod-sti).

    Kaldt fra ``stream_visible_followup`` FØR adapter-dispatch. Dette er den ENE
    produktions-rørende ændring (clearly-marked, self-safe)."""
    global _active_fault
    fault = _active_fault  # atomisk læsning af modul-global; intet lås i prod-stien
    if fault is None:
        return None
    with _fault_lock:
        active = _active_fault
        if active is None:
            return None
        # fail_times-mode (Fase 1 retry-harness): fejl de første N kald, lad
        # kald N+1 lykkes. Tæl dispatch-kald under lås så det er deterministisk.
        _fail_times = active.get("fail_times")
        if _fail_times is not None:
            _n = int(active.get("_calls") or 0)
            active["_calls"] = _n + 1
            if _n >= int(_fail_times):
                # Dette kald skal RECOVERE → clean done med recover_text.
                _recover = {"shape": "__recover__",
                            "recover_text": str(active.get("recover_text") or "")}
                if active.get("fire_once"):
                    _active_fault = None
                return _yield_injected_fault(_recover, round_index)
            # ellers: fald igennem og fejl som normalt (uden at rydde).
        elif active.get("fire_once"):
            _active_fault = None
    return _yield_injected_fault(active, round_index)


def _yield_injected_fault(fault: dict, round_index: int) -> Iterator[FollowupEvent]:
    """Generér event-strømmen for en given injektion (test-only)."""
    shape = fault["shape"]
    if shape == "__recover__":
        # Fase 1 retry-harness: et CLEAN done der lykkes på retry-attempt'et
        # (simulerer at det forbigående blip er væk anden gang). Yielder en
        # delta + done så turen kan fortsætte (recovered).
        _txt = str(fault.get("recover_text") or "")
        if _txt:
            yield FollowupDelta(delta=_txt)
        yield FollowupDone(text="")
        return
    if shape == FAULT_CLEAN_FAIL_BEFORE_DELTA:
        # (a) HTTP 502-klasse FØR nogen delta — clean fail, ingen partiel tekst.
        summary = f"followup-round-{round_index + 1}-provider-error: HTTP 502"
        _kind, _ = classify_failure(http_status=502, error_text=summary)
        yield FollowupFailed(round_index=round_index, error=summary, summary=summary,
                             failure_kind=_kind, http_status=502)
        return
    if shape == FAULT_PARTIAL_DELTAS_THEN_DROP:
        # (b) PRIMÆR: stream N deltas, så et forbigående drop. Dette er trigger
        # for C11 (partiel tekst i _all_followup_parts/persistering trods fejl)
        # og D11 (en retry ville spawne en anden pump).
        for chunk in fault["partial_deltas"]:
            if chunk:
                yield FollowupDelta(delta=chunk)
        if fault["drop_as_exception"]:
            # Transport-drop = rå exception ud af generatoren (mest realistisk for
            # en socket-drop). Fanges af _pump_agentic's except → sætter _a_failure
            # men fyrer IKKE note_round_failed (yielded-FollowupFailed-stien gør).
            raise ConnectionError("simulated transient stream drop after partial deltas")
        summary = f"followup-round-{round_index + 1}-provider-error: transient stream drop"
        _kind, _ = classify_failure(http_status=None, error_text=summary)
        yield FollowupFailed(round_index=round_index, error=summary, summary=summary,
                             failure_kind=_kind, http_status=None)
        return
    if shape == FAULT_HTTP_400_OVERFLOW:
        # (c) Context-window-overløb: HTTP 400 "prompt too long" — distinkt fra et
        # transport-drop (fatal, ikke retryable). Body-formen matcher den ægte
        # openai-compat-adapter (visible_followup.py:855).
        status = int(fault["http_status"])
        body = "context_length_exceeded: prompt too long for model context window"
        summary = f"followup-round-{round_index + 1}-provider-error: HTTP {status}: {body[:180]}"
        _kind, _ = classify_failure(http_status=status, error_text=f"{summary} {body}")
        yield FollowupFailed(round_index=round_index, error=summary, summary=summary,
                             failure_kind=_kind, http_status=status)
        return
    # Ukendt shape (bør ikke ske — inject_fault validerer): no-op.
    return
