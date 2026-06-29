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
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Iterator, Protocol, runtime_checkable
from urllib import error as urllib_error
from urllib import request as urllib_request

from core.services.stream_failure_kind import (
    FailureKind,
    MalformedStreamPayload,
    classify_failure,
    compute_backoff_with_jitter,
    safe_decode_line,
    try_parse_json_line,
)

_log = logging.getLogger(__name__)


def _observe_malformed_stream_payload(
    provider: str, model: str, round_index: int, *, ended_malformed: bool,
    detail: str = "",
) -> None:
    """A11 (spec §11.1): followup-adapterens NDJSON/SSE-decoder mødte en malformet
    chunk eller et split UTF-8-codepoint. Self-safe nerve i Centralen (stream-cluster).

    ``ended_malformed=False`` = vi sprang ÉN dårlig chunk over (lav severity, stream
    overlevede); ``True`` = streamen sluttede uden ``done`` efter et skip → den
    retryable :class:`MalformedStreamPayload` 4.1's rund-retry fanger (høj severity)."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "stream",
            "nerve": "malformed_stream_payload",
            "lane": "visible", "provider": str(provider or ""), "model": str(model or ""),
            "path": f"followup_round_{int(round_index) + 1}",
            "severity": "fail" if ended_malformed else "skip",
            "ended_malformed": bool(ended_malformed),
            "detail": str(detail or "")[:200],
        })
    except Exception:
        pass


_OLLAMA_MAX_FOLLOWUP_EXCHANGES = 10
_OLLAMA_MAX_TOOL_RESULT_CHARS = 8000


# ── Lean agentic-round-prompt (spec §4.7, I7) ────────────────────────────────
#
# PROBLEM (kode-bekræftet): hver agentisk followup-runde gen-sender HELE den tunge
# assembly-prompt. ``_build_visible_input`` (visible_model.py) flytter den per-turn-
# dynamiske HALE (inder-liv/somatik/mood/diagnostik/awareness/memory-recall/
# digests/finitude/presence) UD af system-beskeden og NED på den SIDSTE bruger-
# besked. Den hale framer KUN det FØRSTE svar — under opgave-eksekvering (runde ≥2)
# er den ren kontekst-bloat: den fortynder vinduet, øger thinking-modellers fejl og
# kan tippe lange/autonome loops over model-vinduet (Ollama 400 "prompt too long" →
# tavst svar).
#
# LEAN-TRANSFORMEN (runde ≥2): behold den LOAD-BEARING kerne, drop den tunge
# berigelse fra den sidste bruger-besked:
#   BEHOLD:  system-beskeden (identitet-kerne + tool-katalog-linje + tool-output-
#            hygiejne — Jarvis' STEMME), HELE samtale-historikken, den oprindelige
#            bruger-opgave, ALLE tool-exchanges (de ligger i ``exchanges``, røres
#            ALDRIG her), og de 2 load-bearing anti-løgn-rækker.
#   DROP:    den per-turn-dynamiske hale (alt fra det første heavy-marker og frem).
#
# De 2 load-bearing anti-løgn-rækker (spec §4.7) BEVARES eksplicit:
#   1. ``⚖️ FØR DU SVARER`` (behavioral anchor) — extraheres fra halen og re-appendes.
#   2. tool-output-hygiejnen (``🔧 TOOL-OUTPUT``) — ligger i SYSTEM-beskeden, som
#      lean-transformen aldrig rører → den overlever automatisk.
#
# Konservativ ved tvivl: kan vi ikke finde halen, sender vi den FULDE besked (lean
# = byte-identisk full i det tilfælde). At miste stemme/anti-løgn er værre end bloat.

# Det første heavy-enrichment-marker halen kan begynde med (rækkefølge fra
# prompt_contract: inder-liv → diagnostik-header → awareness-buffer → …). Det
# FØRSTE der optræder i den sidste bruger-besked markerer hale-grænsen.
_LEAN_TAIL_START_MARKERS: tuple[str, ...] = (
    "[INDRE LIV]",
    "📊 INTERN DIAGNOSTIK",
    "[SELF-MONITOR]",
    "[VERIFICATION]",
    "[REASONING]",
    "[ROUTING]",
    "[MEMORY-RECALL]",
    "[CALIBRATION]",
    "[OPERATIONAL]",
    "[AWARENESS]",
)

# De 2 load-bearing anti-løgn-rækker — bevares ALTID i lean-prompten.
# Behavioral anchor (anti-fabrikation) ligger i halen → extraheres + re-appendes.
# Match på prefiks (teksten efter kan variere let på tværs af versioner).
_LEAN_KEEP_ROW_PREFIXES: tuple[str, ...] = (
    "⚖️ FØR DU SVARER",
)


def _split_on_double_newline(text: str) -> list[str]:
    """Split en sammensat besked i blokke på ``\\n\\n`` (assembly-join-grænsen)."""
    return text.split("\n\n")


def _lean_strip_user_message(text: str) -> tuple[str, bool, int]:
    """Skær den tunge per-turn-hale af ÉN bruger-besked, men bevar de load-bearing
    anti-løgn-rækker. Returnerer ``(lean_text, changed, dropped_chars)``.

    Konservativ: finder vi intet heavy-marker → ``changed=False`` og teksten
    returneres uændret (lean = full). Aldrig en exception ud (caller er hot-loop)."""
    if not text:
        return text, False, 0
    # Find den TIDLIGSTE hale-grænse blandt alle kendte heavy-markers.
    _cut = -1
    for _m in _LEAN_TAIL_START_MARKERS:
        _i = text.find(_m)
        if _i != -1 and (_cut == -1 or _i < _cut):
            _cut = _i
    if _cut == -1:
        return text, False, 0
    _head = text[:_cut].rstrip()
    _tail = text[_cut:]
    # Bevar de load-bearing anti-løgn-rækker fra halen (behavioral anchor).
    _kept_rows: list[str] = []
    for _block in _split_on_double_newline(_tail):
        _b = _block.strip()
        if not _b:
            continue
        for _pref in _LEAN_KEEP_ROW_PREFIXES:
            if _b.startswith(_pref):
                _kept_rows.append(_b)
                break
    _lean = _head
    if _kept_rows:
        _lean = (_head + "\n\n" + "\n\n".join(_kept_rows)).strip() if _head else "\n\n".join(_kept_rows)
    # POST-BETINGELSE (load-bearing honesty-garanti): hver anti-løgn-række der fandtes
    # i originalen SKAL overleve i lean. Hvis en formaterings-finte (fx række glued til
    # en heavy-blok uden dobbelt-newline) ville droppe den → fail-open til FULD prompt.
    # Bloat er bedre end at tabe anti-fabrikations-ankeret midt i et loop.
    for _pref in _LEAN_KEEP_ROW_PREFIXES:
        if _pref in text and _pref not in _lean:
            return text, False, 0
    _dropped = max(0, len(text) - len(_lean))
    return _lean, True, _dropped


def build_lean_base_messages(
    base_messages: list[dict],
) -> tuple[list[dict], dict]:
    """Producér en LEAN udgave af ``base_messages`` til agentiske runder ≥2.

    Drop den tunge per-turn-hale fra den SIDSTE bruger-besked; behold system-
    beskeden (identitet/tools/stemme), historikken, opgaven og de 2 anti-løgn-rækker.
    ``exchanges`` (tool-resultater) ligger UDENFOR ``base_messages`` og røres ALDRIG.

    Returnerer ``(lean_messages, metrics)``. ``metrics`` bærer char-reduktionen
    (før/efter + estimeret token-besparelse) til observe-nerven. Ren funktion —
    muterer ikke input (kopierer den ene besked vi ændrer). Self-safe: enhver
    overraskelse → original messages + ``changed=False`` (fail-open mod bloat,
    ALDRIG mod tab af stemme/anti-løgn)."""
    _before = sum(len(str(m.get("content") or "")) for m in base_messages)
    try:
        if not base_messages:
            return base_messages, {"changed": False, "before_chars": _before,
                                   "after_chars": _before, "dropped_chars": 0}
        # Find INDEKSET på den sidste user-besked (det er den der bærer halen).
        _last_user_idx = -1
        for _i in range(len(base_messages) - 1, -1, -1):
            if str(base_messages[_i].get("role") or "") == "user":
                _last_user_idx = _i
                break
        if _last_user_idx == -1:
            return base_messages, {"changed": False, "before_chars": _before,
                                   "after_chars": _before, "dropped_chars": 0}
        _orig = str(base_messages[_last_user_idx].get("content") or "")
        _lean_text, _changed, _dropped = _lean_strip_user_message(_orig)
        if not _changed:
            return base_messages, {"changed": False, "before_chars": _before,
                                   "after_chars": _before, "dropped_chars": 0}
        # Kopiér KUN den besked vi ændrer; resten deles by-reference (uændret).
        _out = list(base_messages)
        _new_msg = dict(_out[_last_user_idx])
        _new_msg["content"] = _lean_text
        _out[_last_user_idx] = _new_msg
        _after = _before - _dropped
        return _out, {
            "changed": True,
            "before_chars": _before,
            "after_chars": _after,
            "dropped_chars": _dropped,
            # Grov token-heuristik (char/4) — samme som prompt_contract triage.
            "before_tokens": _before // 4,
            "after_tokens": _after // 4,
            "saved_tokens": _dropped // 4,
        }
    except Exception:
        # Fail-open mod bloat — ALDRIG mod tab af stemme/anti-løgn.
        return base_messages, {"changed": False, "before_chars": _before,
                               "after_chars": _before, "dropped_chars": 0}


# ── Event types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class FollowupDelta:
    """A chunk of prose produced by the model during this follow-up round."""

    delta: str


@dataclass(frozen=True, slots=True)
class FollowupReasoningDelta:
    """A chunk of REASONING (thinking-mode trace) streamed token-for-token.
    Surfaces deepseek's reasoning_content live så frontenden kan vise et
    foldbart 'tænker…'-felt mens det sker. Akkumuleres stadig til FollowupDone
    for persistens; dette er kun til live-visning."""

    delta: str


@dataclass(frozen=True, slots=True)
class FollowupToolCalls:
    """Model requested one or more additional tool calls in this round."""

    tool_calls: list[dict]


@dataclass(frozen=True, slots=True)
class FollowupDone:
    """The model finished this round cleanly (may have emitted text, tool calls, or both)."""

    text: str
    # Reasoning trace from thinking-mode models (Deepseek v4-pro/reasoner).
    # Must be threaded into the assistant message that joins the next
    # ToolExchange so multi-round agentic loops survive past round 1.
    reasoning_content: str = ""


@dataclass(frozen=True, slots=True)
class FollowupFailed:
    """The round failed before completing (network error, HTTP 5xx, timeout, etc.).

    ``failure_kind`` + ``http_status`` are the STRUCTURED taxonomy (spec B11/I5)
    that Fase 1's round-retry depends on — the single source of truth for
    retryability, replacing substring-matching on ``summary``. Both are OPTIONAL
    (default ""/None) so legacy construction sites and pickled/serialized callers
    keep working; populate via ``classify_failure`` at every raise/yield site.
    ``error``/``summary`` remain for backward-compat + human-readable context.
    """

    round_index: int
    error: str
    summary: str
    # Structured taxonomy (B11). "" = unclassified (legacy / not yet wired).
    failure_kind: str = ""
    # HTTP status when known (urllib/httpx); None for transport drops / local exc.
    http_status: int | None = None


FollowupEvent = (
    FollowupDelta | FollowupReasoningDelta | FollowupToolCalls | FollowupDone | FollowupFailed
)


# ── Tool-result carrier ──────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ToolResult:
    """One executed tool's output, keyed back to the model's original tool_call.

    ``tool_call_id`` is the id the model gave the call (OpenAI-style). Ollama
    does not include ids today, so for Ollama results it may be empty — the
    Ollama adapter packs results into a user-message block keyed by tool_name.
    """

    tool_call_id: str
    tool_name: str
    content: str


@dataclass(frozen=True, slots=True)
class ToolExchange:
    """One round of tool-calling: the assistant's tool_calls + the executed results.

    ``text`` is any prose the assistant emitted alongside the tool_calls in
    that round (often empty — many models only emit tool_calls without
    prose). ``tool_calls`` is the raw list of tool_call dicts the model
    produced (OpenAI-style ``{"id","type","function":{"name","arguments"}}``
    or Ollama's ``{"function":{"name","arguments"}}``). ``results`` are the
    executed outputs keyed back to those calls.
    """

    text: str
    tool_calls: list[dict]
    results: list[ToolResult]
    # Reasoning content from thinking-mode models — must be replayed in the
    # assistant message on followup turns (Deepseek requires this).
    reasoning_content: str = ""


# ── Adapter protocol ─────────────────────────────────────────────────────────


@runtime_checkable
class FollowupAdapter(Protocol):
    provider_id: str

    def stream_followup(
        self,
        *,
        model: str,
        base_messages: list[dict],
        exchanges: list[ToolExchange],
        tool_definitions: list[dict] | None = None,
        round_index: int = 0,
    ) -> Iterator[FollowupEvent]:
        ...


# ── Ollama adapter (preserves existing /api/chat NDJSON behavior) ────────────


class OllamaFollowupAdapter:
    """Follow-up via Ollama's ``/api/chat`` streaming NDJSON endpoint.

    Uses the modern OpenAI-spec tool message format: assistant turns carry
    structured ``tool_calls``, and results are sent back as ``role=tool``
    messages with ``tool_call_id`` linking them to the originating call.
    Modern Ollama (0.2+) and modern instruction-tuned models (Qwen3+,
    Llama 3+, deepseek-v4 etc.) are all trained on this format and continue
    agentic loops naturally — no soft "you may call more tools" prompt
    needed.

    Historical context: until 2026-04-25 this adapter packed tool results
    into a synthetic *user* message ("[tool_name]:\\nresult ... Please
    respond. You may call additional tools."). That worked OK for old
    models (Llama 2, tiny Qwens) but starved newer ones of the structural
    cue they were trained on. Symptom: the model would write a "Lad mig X"
    plan in prose and end its turn instead of emitting another tool_call.
    Switching to the structured format gives the same agentic-loop quality
    we always had on the GitHub Copilot path.
    """

    provider_id = "ollama"

    def _normalize_tool_calls(self, tool_calls: list[dict]) -> list[dict]:
        """Replay tool_calls — men REPARÉR afkortede/malformede argument-strenge først.

        Ollama's /api/chat accepterer ``arguments`` som dict. MEN hvis et tidligere tool-kald
        blev cuttet midt i stream'en (model-output afbrudt) er ``arguments`` en AFKORTET streng
        som ``{"path": "/foo`` — ollama afviser så HELE followup-request-body'en med HTTP 400
        'Value looks like object, but can't find closing "}" symbol'. Det dræber hele runden
        (cut-off: "spinner → stop → intet"). Tool'et er ALLEREDE kørt; argumenterne er kun
        replay-kontekst → ved uparselig streng falder vi tilbage til {} fremfor at vælte runden.
        """
        out: list[dict] = []
        for raw in tool_calls:
            if not isinstance(raw, dict):
                continue
            tc = dict(raw)
            # arguments kan ligge top-level (tc["arguments"]) eller under function-dict'en.
            self._repair_arguments(tc)
            fn = tc.get("function")
            if isinstance(fn, dict):
                fn = dict(fn)            # kopiér så vi ikke muterer kilde-exchanges
                self._repair_arguments(fn)
                tc["function"] = fn
            out.append(tc)
        return out

    @staticmethod
    def _repair_arguments(container: dict) -> None:
        """Hvis container['arguments'] er en STRENG der ikke er gyldig JSON → erstat med {}.
        Dict-argumenter (ollama-native) og gyldige JSON-strenge røres ikke."""
        if "arguments" not in container:
            return
        args = container.get("arguments")
        if not isinstance(args, str):
            return
        s = args.strip()
        if not s:
            container["arguments"] = {}
            return
        try:
            import json as _json
            _json.loads(s)               # gyldig JSON-streng → lad stå
        except Exception:
            container["arguments"] = {}  # afkortet/malformet → safe fallback

    def _compact_exchanges(self, exchanges: list[ToolExchange]) -> list[ToolExchange]:
        """Bound Ollama follow-up replay so long tool loops do not 400.

        Ollama cloud accepts large contexts, but repeated structured
        assistant/tool turns with full file contents can still make
        /api/chat reject the payload in later rounds. Keep recent tool
        history and trim each tool result; durable checkpoints retain the
        full local details outside the provider payload.
        """
        bounded = list(exchanges)[-_OLLAMA_MAX_FOLLOWUP_EXCHANGES:]
        compacted: list[ToolExchange] = []
        for exch in bounded:
            results: list[ToolResult] = []
            for tr in exch.results:
                content = str(tr.content or "")
                if len(content) > _OLLAMA_MAX_TOOL_RESULT_CHARS:
                    omitted = len(content) - _OLLAMA_MAX_TOOL_RESULT_CHARS
                    content = (
                        content[:_OLLAMA_MAX_TOOL_RESULT_CHARS]
                        + f"\n\n[tool result truncated for follow-up context; {omitted} chars omitted]"
                    )
                results.append(
                    ToolResult(
                        tool_call_id=tr.tool_call_id,
                        tool_name=tr.tool_name,
                        content=content,
                    )
                )
            compacted.append(
                ToolExchange(
                    text=exch.text,
                    tool_calls=list(exch.tool_calls),
                    results=results,
                    reasoning_content=exch.reasoning_content,
                )
            )
        return compacted

    def _serialize_exchanges(self, exchanges: list[ToolExchange]) -> list[dict]:
        """Replay exchanges as structured assistant + role=tool messages.

        For each exchange:
          {"role": "assistant", "content": <text>, "tool_calls": [...]}
          {"role": "tool", "tool_call_id": "...", "name": "...", "content": "..."}
          (one tool message per result)

        No "Continue." or "Please respond" seed prompt — modern models
        infer continuation from the structured turn pattern.
        """
        messages: list[dict] = []
        for exch in self._compact_exchanges(exchanges):
            _asst: dict[str, object] = {
                "role": "assistant",
                "content": exch.text,
                "tool_calls": self._normalize_tool_calls(list(exch.tool_calls)),
            }
            # Replay thinking-modellens ræsonnering tilbage så deepseek/GLM/...
            # beholder sin tankerække mellem tool-runder (ellers re-tænker den
            # forfra hver runde → tool-spam → tabt svar). Ollama accepterer
            # `thinking` i assistant-beskeder for thinking-modeller.
            if exch.reasoning_content:
                _asst["thinking"] = exch.reasoning_content
            messages.append(_asst)
            for tr in exch.results:
                tool_msg: dict[str, object] = {
                    "role": "tool",
                    "content": tr.content,
                }
                if tr.tool_call_id:
                    tool_msg["tool_call_id"] = tr.tool_call_id
                if tr.tool_name:
                    tool_msg["name"] = tr.tool_name
                messages.append(tool_msg)
        return messages

    def stream_followup(
        self,
        *,
        model: str,
        base_messages: list[dict],
        exchanges: list[ToolExchange],
        tool_definitions: list[dict] | None = None,
        round_index: int = 0,
        thinking_mode: str = "think",
    ) -> Iterator[FollowupEvent]:
        # 2026-06-13: ollama-followup skal bruge OLLAMA-providerens base_url, ikke
        # visible-lanen (deepseek-API). Ellers POST'er tool-runden ollama-format til
        # deepseek → 401, og members' værktøjsbrug brækker.
        from core.runtime.provider_router import (
            load_provider_router_registry as _lprr,
            _provider_base_url as _pburl,
        )
        base_url = (
            _pburl(provider="ollama", registry=_lprr()) or "http://127.0.0.1:11434"
        ).rstrip("/")

        messages = list(base_messages) + self._serialize_exchanges(exchanges)

        payload: dict[str, object] = {
            "model": model,
            "messages": messages,
            "stream": True,
            # Match the first-pass num_ctx so accumulated tool-result rounds
            # don't get truncated. See _VISIBLE_OLLAMA_NUM_CTX in
            # core/services/visible_model.py.
            "options": {"num_ctx": 262_144},
        }
        # Mirror first-pass thinking-mode controls so subsequent rounds
        # respect the user's choice (Fast/Think/Deep) for reasoning models
        # like deepseek-v4-flash.
        _mode = (thinking_mode or "think").strip().lower()
        if _mode == "fast":
            payload["think"] = False
        elif _mode == "deep":
            payload["reasoning_effort"] = "high"
        if tool_definitions:
            payload["tools"] = tool_definitions

        req = urllib_request.Request(
            f"{base_url}/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        parts: list[str] = []
        reasoning_parts: list[str] = []  # ollama `message.thinking` for thinking-models
        collected_tool_calls: list[dict] = []
        last_exc: BaseException | None = None

        attempts = 3
        for attempt in range(attempts):
            try:
                # Two-stage deadline (replaces single read-timeout):
                #
                #   FIRST_BYTE_BUDGET (90s): how long to wait for ANY
                #   data from Ollama. Big prompts → long warmup is OK.
                #
                #   INTER_BYTE_BUDGET (90s, applied via urllib timeout):
                #   once stream is alive, max gap between bytes. If
                #   Ollama freezes mid-stream, the outer visible-run
                #   watchdog still marks the run interrupted. Keep this
                #   at least as generous as the outer 75s silence budget
                #   so the adapter does not preempt productive slow
                #   follow-up rounds.
                #
                # Why this matters: a single 180s read-timeout meant
                # Bjørn waited 3 minutes for "stuck" runs to die. A
                # single 90s timeout killed legitimate slow-warmup
                # responses on big prompts. Two-stage gets both:
                # generous on warmup, fast-fail on freeze.
                #
                # Implementation: urllib's `timeout` IS the per-read
                # deadline (= inter-byte once stream is alive). For
                # the first-byte budget we use a watchdog thread that
                # force-closes the response socket if no bytes arrive
                # within the budget — surfacing as URLError to the
                # outer loop's existing retry/handling.
                FIRST_BYTE_BUDGET_S = 90
                INTER_BYTE_BUDGET_S = 90

                got_first_byte = threading.Event()
                watchdog_response = {"resp": None}

                def _first_byte_watchdog():
                    if got_first_byte.wait(timeout=FIRST_BYTE_BUDGET_S):
                        return  # stream is alive, watchdog done
                    # First-byte budget exceeded — kill the connection.
                    # Closing the response forces the read loop to
                    # raise, which the outer `except` catches normally.
                    r = watchdog_response["resp"]
                    if r is not None:
                        try:
                            r.close()
                        except Exception:
                            pass

                watchdog = threading.Thread(
                    target=_first_byte_watchdog,
                    name="ollama-first-byte-watchdog",
                    daemon=True,
                )
                watchdog.start()

                # A11 (spec §11.1): saw_done = nåede terminal; saw_malformed = sprang
                # ≥1 dårlig chunk over. Slutter streamen uden done EFTER et skip →
                # typed retryable MalformedStreamPayload (4.1's rund-retry fanger den).
                saw_done = False
                saw_malformed = False
                with urllib_request.urlopen(req, timeout=INTER_BYTE_BUDGET_S) as resp:
                    watchdog_response["resp"] = resp
                    for raw_line in resp:
                        # First byte received — disarm the watchdog.
                        # Subsequent reads are governed by urllib's
                        # per-read timeout; the outer visible-run
                        # watchdog is responsible for classifying a
                        # truly silent follow-up round.
                        if not got_first_byte.is_set():
                            got_first_byte.set()
                        # A11 pkt. 1: decode UDEN at rejse (split æøå/emoji → U+FFFD).
                        line = safe_decode_line(raw_line).strip()
                        if not line:
                            continue
                        # A11 pkt. 2: én malformet NDJSON-linje må IKKE dræbe streamen.
                        event, _ok = try_parse_json_line(line)
                        if not _ok:
                            saw_malformed = True
                            _observe_malformed_stream_payload(
                                "ollama", model, round_index,
                                ended_malformed=False, detail=line[:120])
                            continue
                        if event is None:
                            continue
                        msg = event.get("message") or {}
                        delta = str(msg.get("content") or "")
                        if delta:
                            parts.append(delta)
                            yield FollowupDelta(delta=delta)
                        # 2026-06-13: deepseek-v4/GLM/minimax thinking-modeller via
                        # ollama lægger ræsonneringen i `message.thinking` (separat
                        # felt), content er TOM under tool-runder. Uden at læse det
                        # var hver runde text_chars=0, tankerækken gik tabt, og
                        # modellen mistede kontinuitet mellem runder → tool-spam →
                        # tabt endeligt svar. Fang + surface + replay (Bjørn fandt det).
                        think = str(msg.get("thinking") or "")
                        if think:
                            reasoning_parts.append(think)
                            yield FollowupReasoningDelta(delta=think)
                        tc = msg.get("tool_calls") or []
                        if tc:
                            collected_tool_calls.extend(tc)
                        if event.get("done"):
                            saw_done = True
                            break
                # Make sure watchdog exits cleanly even on early-break
                got_first_byte.set()
                # A11: streamen sluttede UDEN done EFTER et malformet-skip →
                # trunkeret final-JSON. Rejs typed retryable så den klassificeres
                # som malformed_stream_payload (caught af except Exception nedenfor
                # → FollowupFailed → 4.1's rund-retry).
                if not saw_done and saw_malformed:
                    _observe_malformed_stream_payload(
                        "ollama", model, round_index, ended_malformed=True,
                        detail="stream ended without done after malformed chunk")
                    raise MalformedStreamPayload(
                        "Ollama followup stream ended malformed (truncated final JSON)")
                last_exc = None
                break
            except urllib_error.HTTPError as he:
                # Læs provider-body'en så DEN ÆGTE årsag (fx Geminis
                # "missing a thought_signature") når frem til brugeren — ikke kun
                # det nøgne "HTTP Error 400: Bad Request" (Bjørn 2026-06-16).
                _http_body = ""
                try:
                    _http_body = he.read().decode("utf-8", "replace").strip()
                except Exception:
                    _http_body = ""
                if _http_body:
                    setattr(he, "_jarvis_body", _http_body[:300])
                last_exc = he
                code = int(getattr(he, "code", 0) or 0)
                # 429 = rate-limit (Ollama cloud efter mange hurtige tool-runder).
                # Tidligere ikke-retryable → runnet aborterede midt i loopet og
                # tabte det endelige svar. Nu: backoff + retry, respektér
                # Retry-After-headeren hvis sat (2026-06-13, Bjørn så 429-cutoff).
                retryable = code in {429, 502, 503, 504}
                if retryable and attempt < (attempts - 1):
                    if code == 429:
                        try:
                            _ra = float(he.headers.get("Retry-After") or 0)
                        except (ValueError, TypeError, AttributeError):
                            _ra = 0.0
                        # Delt jitter-helper (spec §11.2): mere generøs base for
                        # rate-limit + respektér Retry-After som gulv, men med
                        # jitter så samtidige runs ikke retry'er i lås.
                        backoff = compute_backoff_with_jitter(
                            attempt, base=2.0, retry_after=_ra or None)
                    else:
                        backoff = compute_backoff_with_jitter(attempt)
                    _log.warning(
                        "ollama followup round %d retrying after HTTP %s in %.1fs (attempt %d/%d)",
                        round_index, code, backoff, attempt + 1, attempts,
                    )
                    time.sleep(backoff)
                    continue
                break
            except urllib_error.URLError as ue:
                last_exc = ue
                if attempt < (attempts - 1):
                    _log.warning(
                        "ollama followup round %d retrying after URLError: %s (attempt %d/%d)",
                        round_index,
                        ue,
                        attempt + 1,
                        attempts,
                    )
                    time.sleep(compute_backoff_with_jitter(attempt))
                    continue
                break
            except Exception as e:
                last_exc = e
                break

        if last_exc is not None:
            _body = getattr(last_exc, "_jarvis_body", "")
            _err_text = str(last_exc) or "unknown"
            if _body:
                _err_text = f"{_err_text}: {_body}"
            summary = f"followup-round-{round_index + 1}-timeout"
            if "timed out" not in str(last_exc).lower():
                summary = (
                    f"followup-round-{round_index + 1}-provider-error: {_err_text}"
                )
            _log.error(
                "ollama followup round %d failed: %s", round_index, _err_text, exc_info=True
            )
            _status = (
                int(getattr(last_exc, "code", 0) or 0)
                if isinstance(last_exc, urllib_error.HTTPError)
                else None
            )
            _kind, _ = classify_failure(http_status=_status, error_text=_err_text)
            yield FollowupFailed(
                round_index=round_index,
                error=_err_text,
                summary=summary,
                failure_kind=_kind,
                http_status=_status,
            )
            return

        if collected_tool_calls:
            yield FollowupToolCalls(tool_calls=collected_tool_calls)
        yield FollowupDone(
            text="".join(parts),
            reasoning_content="".join(reasoning_parts),
        )


# ── OpenAI-compatible adapter (GitHub Copilot, and room for openai proper) ──


class OpenAICompatFollowupAdapter:
    """Follow-up via OpenAI-compatible ``/chat/completions`` SSE streams.

    Emits proper structured tool messages:
    ``{"role": "tool", "tool_call_id": "...", "content": "..."}`` and a prior
    assistant turn with ``tool_calls`` so the model can link results back
    to calls. This is the contract documented in the OpenAI Chat Completions
    spec and honored by Copilot and OpenRouter.
    """

    def __init__(self, *, provider_id: str) -> None:
        self.provider_id = provider_id

    def _normalize_assistant_tool_calls(self, tool_calls: list[dict]) -> list[dict]:
        """Normalize assistant tool_calls to match the OpenAI chat-completions
        wire spec.

        Per spec, ``function.arguments`` must be a JSON-encoded string —
        not an object. Several providers (GitHub Copilot, OpenCode/MiniMax)
        reject requests where arguments is a dict with HTTP 400. We parse
        incoming tool_call args to dict in visible_runs; here we re-encode
        them on the way back out so every openai-compat provider is happy.
        """
        normalized: list[dict] = []
        for raw in tool_calls:
            tc = dict(raw or {})
            fn = dict(tc.get("function") or {})
            if fn:
                args = fn.get("arguments")
                if isinstance(args, dict):
                    fn["arguments"] = json.dumps(args, ensure_ascii=False)
                tc["function"] = fn
            normalized.append(tc)
        return normalized

    def _build_request(
        self, *, model: str, messages: list[dict], tool_definitions: list[dict] | None
    ) -> urllib_request.Request:
        if self.provider_id == "github-copilot":
            # Lazy imports: these modules pull in auth state we don't want to
            # touch at module load.
            from core.auth.copilot_session import get_copilot_session_token
            from core.runtime.settings import load_settings
            from core.services.non_visible_lane_execution import (
                _COPILOT_API_ROOT,
                _github_copilot_request_headers,
                _load_github_copilot_token,
            )
            from core.services.visible_model import _normalize_github_models_model_id

            profile = (load_settings().visible_auth_profile or "default").strip() or "default"
            _load_github_copilot_token(profile=profile)
            session_token = get_copilot_session_token(profile=profile)
            normalized_model = _normalize_github_models_model_id(model)
            payload: dict[str, object] = {
                "model": normalized_model,
                "messages": messages,
                "stream": True,
            }
            if tool_definitions:
                # Copilot chat/completions currently enforces max 128 tools.
                # Without this cap the followup stream fails with HTTP 400 and
                # visible runs are interrupted mid tool-calling loop.
                payload["tools"] = list(tool_definitions)[:128]
            return urllib_request.Request(
                f"{_COPILOT_API_ROOT}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers=_github_copilot_request_headers(
                    session_token, accept="text/event-stream"
                ),
                method="POST",
            )

        # Generic openai-compat provider (opencode, groq, openrouter, mistral,
        # nvidia-nim, sambanova). Look up base_url + credentials via the cheap
        # provider runtime so we don't duplicate config here.
        from core.services.cheap_provider_runtime import (
            _OPENAI_COMPATIBLE_PROVIDERS,
            _require_credentials,
            provider_runtime_defaults,
        )

        if self.provider_id not in _OPENAI_COMPATIBLE_PROVIDERS:
            raise RuntimeError(
                f"OpenAICompatFollowupAdapter: no request builder for provider '{self.provider_id}'"
            )

        defaults = provider_runtime_defaults(self.provider_id)
        base_url = str(defaults.get("base_url") or "").rstrip("/")
        # Auth profile lookup — provider name og auth profile er ikke altid
        # det samme (deepseek bruger fx "default" profil, ikke "deepseek").
        # Fald tilbage til provider name hvis registry-entry mangler.
        try:
            from core.runtime.provider_router import load_provider_router_registry
            _registry = load_provider_router_registry()
            _auth_profile = ""
            for _p in _registry.get("providers") or []:
                if str(_p.get("provider") or "") == self.provider_id:
                    _auth_profile = str(_p.get("auth_profile") or "").strip()
                    break
            _auth_profile = _auth_profile or self.provider_id
        except Exception:
            _auth_profile = self.provider_id
        credentials = _require_credentials(
            profile=_auth_profile, provider=self.provider_id
        )
        api_key = str(credentials.get("api_key") or "").strip()
        payload: dict[str, object] = {
            "model": model,
            "messages": messages,
            "stream": True,
            # Without explicit max_tokens, MiniMax/OpenCode caps at ~512 and
            # cuts the assistant off mid-sentence. 4096 is plenty for any
            # follow-up turn while staying within the free quota.
            "max_tokens": 4096,
        }
        if tool_definitions:
            from core.services.cheap_provider_runtime import _normalize_tools_for_openai_chat
            payload["tools"] = _normalize_tools_for_openai_chat(list(tool_definitions))
        return urllib_request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                # OpenCode is fronted by Cloudflare and blocks the default
                # Python urllib user-agent (HTTP 403 error code 1010). Set
                # the same UA we use on first-pass calls via _http_json.
                "User-Agent": "jarvis-v2/cheap-lane",
            },
            method="POST",
        )

    def _serialize_exchanges(self, exchanges: list[ToolExchange]) -> list[dict]:
        """Turn accumulated exchanges into OpenAI-compat tool messages.

        For each exchange:
          ``{"role": "assistant", "content": <text>, "tool_calls": [...]}``
          ``{"role": "tool", "tool_call_id": "...", "name": "...", "content": "..."}``
          (one tool message per result)

        ``tool_call_id`` is required by spec. If a result lacks an id we
        still include the message with ``name`` only — some providers
        tolerate this; others reject it, in which case the follow-up fails
        cleanly via :class:`FollowupFailed`.
        """
        messages: list[dict] = []
        for exch in exchanges:
            assistant_msg: dict[str, object] = {
                "role": "assistant",
                "content": exch.text,
                "tool_calls": self._normalize_assistant_tool_calls(
                    list(exch.tool_calls)
                ),
            }
            # Thinking-mode replay: Deepseek v4-pro/reasoner requires the
            # reasoning_content from the prior assistant turn to be sent
            # back verbatim, otherwise the API rejects with
            # "reasoning_content must be passed back to the API".
            if exch.reasoning_content:
                assistant_msg["reasoning_content"] = exch.reasoning_content
            messages.append(assistant_msg)
            for tr in exch.results:
                tool_msg: dict[str, object] = {
                    "role": "tool",
                    "content": tr.content,
                }
                if tr.tool_call_id:
                    tool_msg["tool_call_id"] = tr.tool_call_id
                if tr.tool_name:
                    tool_msg["name"] = tr.tool_name
                messages.append(tool_msg)
        return messages

    def stream_followup(
        self,
        *,
        model: str,
        base_messages: list[dict],
        exchanges: list[ToolExchange],
        tool_definitions: list[dict] | None = None,
        round_index: int = 0,
        thinking_mode: str = "think",
    ) -> Iterator[FollowupEvent]:
        from core.services.visible_model import (
            _chat_completion_stream_is_terminal,
            _extract_chat_completion_delta,
            _extract_chat_completion_reasoning,
            _finalize_openai_tool_calls,
            _iter_sse_events,
            _merge_openai_tool_call_deltas,
        )

        # Deepseek thinking-mode toggles via model-name swap, ikke via
        # request-param. "fast" → swap til deepseek-chat (non-thinking
        # compat-alias). Andre openai-compat providere har ikke thinking-
        # mode og returneres uændret.
        if self.provider_id == "deepseek":
            from core.services.cheap_provider_runtime import (
                deepseek_model_for_thinking_mode,
            )
            model = deepseek_model_for_thinking_mode(model, thinking_mode)

        # Legacy assistant-turns uden reasoning_content: Deepseek thinking-mode
        # afviser hele requesten hvis feltet mangler. Tidligere strippede vi
        # turn'en — det fjernede kontekst og fik Jarvis til at "glemme" prior
        # samtale. Tilføjer placeholder reasoning i stedet så indholdet
        # bevares. Strip kun fra base_messages — current-run exchanges har
        # reasoning_content via _serialize_exchanges.
        _is_thinking_model = (
            self.provider_id == "deepseek"
            and model in ("deepseek-v4-flash", "deepseek-v4-pro", "deepseek-reasoner")
        )
        if _is_thinking_model:
            _LEGACY_REASONING_PLACEHOLDER = (
                "[legacy turn — reasoning trace not preserved before "
                "reasoning_content persistence shipped]"
            )
            base_messages = [
                (
                    m if not (
                        m.get("role") == "assistant"
                        and not str(m.get("reasoning_content") or "").strip()
                    )
                    else {**m, "reasoning_content": _LEGACY_REASONING_PLACEHOLDER}
                )
                for m in base_messages
            ]

        messages = list(base_messages) + self._serialize_exchanges(exchanges)

        # Belt-and-suspenders: even after _is_thinking_model patch above
        # covered base_messages, current-run exchanges can still arrive
        # without reasoning_content (e.g., model returned empty reasoning,
        # or a tool-call round captured no thinking trace). Deepseek
        # thinking-mode rejects the entire request with HTTP 400 if ANY
        # assistant message lacks reasoning_content. Patch the merged
        # message list once, right before send.
        if (
            self.provider_id == "deepseek"
            and model in ("deepseek-v4-flash", "deepseek-v4-pro", "deepseek-reasoner")
        ):
            _PLACEHOLDER = (
                "[reasoning trace not captured for this turn — preserving "
                "field so deepseek thinking-mode accepts the request]"
            )
            messages = [
                (
                    m if not (
                        m.get("role") == "assistant"
                        and not str(m.get("reasoning_content") or "").strip()
                    )
                    else {**m, "reasoning_content": _PLACEHOLDER}
                )
                for m in messages
            ]

        if self.provider_id == "deepseek":
            _has_rc = sum(
                1 for m in messages
                if m.get("role") == "assistant" and str(m.get("reasoning_content") or "").strip()
            )
            _no_rc = sum(
                1 for m in messages
                if m.get("role") == "assistant" and not str(m.get("reasoning_content") or "").strip()
            )
            if _no_rc and model in ("deepseek-v4-flash", "deepseek-v4-pro", "deepseek-reasoner"):
                _log.warning(
                    "deepseek followup round=%d model=%s missing reasoning_content on %d assistants — patching",
                    round_index, model, _no_rc,
                )

        try:
            req = self._build_request(
                model=model, messages=messages, tool_definitions=tool_definitions
            )
        except Exception as e:
            _log.error(
                "%s followup round %d request-build failed: %s",
                self.provider_id,
                round_index,
                e,
                exc_info=True,
            )
            yield FollowupFailed(
                round_index=round_index,
                error=str(e) or "build-failed",
                summary=f"followup-round-{round_index + 1}-build-error: {e}",
                # A request-build failure is a local/config fault — never retry.
                failure_kind=FailureKind.INVALID_REQUEST,
                http_status=None,
            )
            return

        parts: list[str] = []
        reasoning_parts: list[str] = []
        tool_call_accumulator: dict[int, dict] = {}
        # DSML-leak filter for followup-rounds (Deepseek v4-pro/flash kan
        # spille sin interne tool-call DSL ud i delta.content sammen med
        # struktureret tool_calls — første-pass har allerede filteret,
        # men followup-runder gik gennem en separat SSE-parser uden det.)
        from core.services.cheap_provider_runtime import _strip_dsml_leak
        _dsml_in_block = False
        _dsml_buffer = ""
        import time as _time
        _t0 = _time.monotonic()
        _ttfb_ms: int | None = None
        _prompt_chars = sum(len(str(m.get("content", ""))) for m in messages)

        try:
            with urllib_request.urlopen(req, timeout=180) as response:
                for event in _iter_sse_events(response):
                    if _ttfb_ms is None:
                        _ttfb_ms = int((_time.monotonic() - _t0) * 1000)
                    delta = _extract_chat_completion_delta(event)
                    if delta:
                        _dsml_buffer += delta
                        safe, _dsml_buffer, _dsml_in_block = _strip_dsml_leak(
                            _dsml_buffer, _dsml_in_block
                        )
                        if safe:
                            parts.append(safe)
                            yield FollowupDelta(delta=safe)
                    reasoning_delta = _extract_chat_completion_reasoning(event)
                    if reasoning_delta:
                        reasoning_parts.append(reasoning_delta)
                        yield FollowupReasoningDelta(delta=reasoning_delta)
                    _merge_openai_tool_call_deltas(tool_call_accumulator, event)
                    if _chat_completion_stream_is_terminal(event):
                        break
        except urllib_error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            summary = f"followup-round-{round_index + 1}-provider-error: HTTP {exc.code}"
            if body:
                summary = f"{summary}: {body[:180]}"
            _log.error(
                "%s followup round %d HTTP %s: %s",
                self.provider_id,
                round_index,
                exc.code,
                body,
            )
            _status = int(getattr(exc, "code", 0) or 0) or None
            _kind, _ = classify_failure(http_status=_status, error_text=f"{summary} {body}")
            yield FollowupFailed(
                round_index=round_index, error=summary, summary=summary,
                failure_kind=_kind, http_status=_status,
            )
            return
        except Exception as exc:
            summary = f"followup-round-{round_index + 1}-provider-error: {exc or 'unknown'}"
            if "timed out" in str(exc).lower():
                summary = f"followup-round-{round_index + 1}-timeout"
            _log.error(
                "%s followup round %d failed: %s",
                self.provider_id,
                round_index,
                exc,
                exc_info=True,
            )
            _kind, _ = classify_failure(http_status=None, error_text=str(exc))
            yield FollowupFailed(
                round_index=round_index,
                error=str(exc) or "unknown",
                summary=summary,
                failure_kind=_kind,
                http_status=None,
            )
            return

        tool_calls = [
            tool_call_accumulator[idx] for idx in sorted(tool_call_accumulator.keys())
        ]
        tool_calls = _finalize_openai_tool_calls(tool_calls)
        _total_ms = int((_time.monotonic() - _t0) * 1000)
        text_chars = sum(len(p) for p in parts)
        tool_call_count = len(tool_calls)
        if text_chars == 0 and tool_call_count > 0:
            # DeepSeek thinking-mode sender content i reasoning_content
            # i stedet for content — så text_chars=0 er normalt når
            # modellen producerer tool_calls. Nedgrader WARNING til INFO
            # for at undgå log-støj.
            _log.info(
                "visible-latency provider=%s round=followup-%d prompt_chars=%d ttfb_ms=%s total_ms=%d text_chars=%d tool_calls=%d",
                self.provider_id,
                round_index,
                _prompt_chars,
                _ttfb_ms if _ttfb_ms is not None else -1,
                _total_ms,
                text_chars,
                tool_call_count,
            )
        else:
            _log.warning(
                "visible-latency provider=%s round=followup-%d prompt_chars=%d ttfb_ms=%s total_ms=%d text_chars=%d tool_calls=%d",
                self.provider_id,
                round_index,
                _prompt_chars,
                _ttfb_ms if _ttfb_ms is not None else -1,
                _total_ms,
                text_chars,
                tool_call_count,
            )
        if tool_calls:
            yield FollowupToolCalls(tool_calls=tool_calls)
        yield FollowupDone(
            text="".join(parts),
            reasoning_content="".join(reasoning_parts),
        )


# ── Codex (OpenAI Responses API) adapter ─────────────────────────────────────


class CodexFollowupAdapter:
    """Follow-up via the OpenAI Codex Responses API (chatgpt.com/backend-api).

    Codex does NOT use chat-completions messages — it uses the Responses API
    ``input`` array of typed items. Prior tool rounds replay as ``function_call``
    + ``function_call_output`` items keyed by ``call_id`` (the model's own id for
    the call). Mirrors :class:`OpenAICompatFollowupAdapter` but in Responses-
    native shape. Without this adapter the agentic loop skips openai-codex
    ("provider-not-supported") and ABORTS the run on any tool-calling turn
    (gpt-5.4-mini empty/aborted-tool bug, 2026-06-15).
    """

    provider_id = "openai-codex"

    def _build_input(self, base_messages: list[dict], exchanges: list[ToolExchange]) -> list[dict]:
        items: list[dict] = []
        for m in base_messages:
            role = str(m.get("role") or "user")
            text = str(m.get("content") or "")
            if not text:
                continue
            if role == "assistant":
                items.append({"role": "assistant", "content": [{"type": "output_text", "text": text}]})
            else:  # user / system → input_text
                items.append({"role": role, "content": [{"type": "input_text", "text": text}]})
        for exch in exchanges:
            if exch.text:
                items.append({"role": "assistant", "content": [{"type": "output_text", "text": exch.text}]})
            for tc in exch.tool_calls:
                fn = tc.get("function") or {}
                args = fn.get("arguments")
                if isinstance(args, (dict, list)):
                    args = json.dumps(args, ensure_ascii=False)
                items.append({
                    "type": "function_call",
                    "call_id": str(tc.get("id") or ""),
                    "name": str(fn.get("name") or ""),
                    "arguments": str(args if args is not None else "{}"),
                })
            for tr in exch.results:
                items.append({
                    "type": "function_call_output",
                    "call_id": str(tr.tool_call_id or ""),
                    "output": str(tr.content or ""),
                })
        return items

    def stream_followup(
        self,
        *,
        model: str,
        base_messages: list[dict],
        exchanges: list[ToolExchange],
        tool_definitions: list[dict] | None = None,
        round_index: int = 0,
        thinking_mode: str = "think",
    ) -> Iterator[FollowupEvent]:
        from core.services.cheap_provider_runtime import (
            _iter_openai_codex_chat_events,
            CheapProviderError,
        )
        from core.services.visible_model import _provider_router_config

        cfg = _provider_router_config(provider="openai-codex")
        profile = str(cfg.get("auth_profile") or "").strip() or "codex"
        base_url = str(cfg.get("base_url") or "").strip()

        input_items = self._build_input(base_messages, exchanges)
        collected_tool_calls: list[dict] = []
        try:
            for ev in _iter_openai_codex_chat_events(
                model=model, auth_profile=profile, base_url=base_url,
                message="", tools=tool_definitions or None, input_items=input_items,
            ):
                kind = ev.get("kind")
                if kind == "delta":
                    d = str(ev.get("text") or "")
                    if d:
                        yield FollowupDelta(delta=d)
                elif kind == "tool_call":
                    collected_tool_calls.append({
                        "id": str(ev.get("id") or ""),
                        "type": "function",
                        "function": {
                            "name": str(ev.get("name") or ""),
                            "arguments": str(ev.get("arguments") or ""),
                        },
                    })
                elif kind == "done":
                    if collected_tool_calls:
                        yield FollowupToolCalls(tool_calls=collected_tool_calls)
                    yield FollowupDone(text=str(ev.get("full_text") or ""), reasoning_content="")
        except CheapProviderError as exc:
            _kind, _ = classify_failure(http_status=None, error_text=str(exc))
            yield FollowupFailed(
                round_index=round_index, error=str(exc),
                summary=f"followup-round-{round_index + 1}-codex-error:{exc}",
                failure_kind=_kind, http_status=None,
            )
        except Exception as exc:  # noqa: BLE001 — surface as clean failure
            _kind, _ = classify_failure(http_status=None, error_text=str(exc))
            yield FollowupFailed(
                round_index=round_index, error=str(exc),
                summary=f"followup-round-{round_index + 1}-codex-error:{exc}",
                failure_kind=_kind, http_status=None,
            )


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
    yield from adapter.stream_followup(**_kwargs)


def build_visible_followup_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push (system_cartographer dark-edge
    closure). Reports module presence so the cartographer registers it as
    observed. Specific state-readers added as the module evolves.
    """
    return {
        "active": True,
        "mode": "visible_followup",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }


def _emit_visible_followup_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a scoped event — defensive, never blocks caller.
    Cartographer scans for event_bus.publish() text.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            f"visible_followup.{kind}",
            payload or {},
        )
    except Exception:
        pass


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


# ── Kill-switch: AGENTIC_LEAN_PROMPT (spec §4.7, I7) ─────────────────────────
#
# Den ENE sandhedskilde for om lean agentic-round-prompten (runde ≥2) er aktiv.
# DEFAULT OFF (fail-closed) → byte-identisk med i dag (full prompt hver runde).
# Samme dual-læsnings-mønster som ``agentic_round_retry_enabled()``:
#   1. env ``JARVIS_AGENTIC_LEAN_PROMPT`` vinder når sat til en sandheds-værdi.
#   2. ellers runtime-config ``settings.extra["agentic_lean_prompt_enabled"]``.
# At slå lean FRA må ALDRIG slå terminal-frame (I2) eller nerve (I4) fra — flaget
# styrer KUN om halen trimmes på runde ≥2.

_AGENTIC_LEAN_PROMPT_ENV = "JARVIS_AGENTIC_LEAN_PROMPT"


def agentic_lean_prompt_enabled() -> bool:
    """Er lean agentic-round-prompt (runde ≥2, spec §4.7) slået til? Default False.

    Env-override (``JARVIS_AGENTIC_LEAN_PROMPT``) vinder over runtime-config.
    Selv-sikker: enhver fejl → False (fail-closed → full prompt hver runde)."""
    env_value = os.environ.get(_AGENTIC_LEAN_PROMPT_ENV)
    if env_value is not None:
        val = env_value.strip().lower()
        if val in _TRUTHY:
            return True
        if val in _FALSY:
            return False
        # Ukendt env-værdi → fald tilbage til config (ignorér uparselbart env).
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().extra.get("agentic_lean_prompt_enabled", False))
    except Exception:
        return False


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

