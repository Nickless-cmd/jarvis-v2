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
import threading
import time
from dataclasses import dataclass
from typing import Iterator, Protocol, runtime_checkable
from urllib import error as urllib_error
from urllib import request as urllib_request

_log = logging.getLogger(__name__)

_OLLAMA_MAX_FOLLOWUP_EXCHANGES = 10
_OLLAMA_MAX_TOOL_RESULT_CHARS = 2500


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
    """The round failed before completing (network error, HTTP 5xx, timeout, etc.)."""

    round_index: int
    error: str
    summary: str


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
        """Pass through tool_calls untouched.

        Unlike the OpenAI-compat adapter (which JSON-encodes args for
        Copilot/MiniMax), Ollama's /api/chat accepts ``arguments`` as a
        dict. We don't re-serialize.
        """
        out: list[dict] = []
        for raw in tool_calls:
            if isinstance(raw, dict):
                out.append(dict(raw))
        return out

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
                        line = raw_line.decode("utf-8").strip()
                        if not line:
                            continue
                        event = json.loads(line)
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
                            break
                # Make sure watchdog exits cleanly even on early-break
                got_first_byte.set()
                last_exc = None
                break
            except urllib_error.HTTPError as he:
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
                        backoff = max(_ra, 2.0 * (2**attempt))  # mere generøs for rate-limit
                    else:
                        backoff = 0.6 * (2**attempt)
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
                    time.sleep(0.6 * (2**attempt))
                    continue
                break
            except Exception as e:
                last_exc = e
                break

        if last_exc is not None:
            summary = f"followup-round-{round_index + 1}-timeout"
            if "timed out" not in str(last_exc).lower():
                summary = (
                    f"followup-round-{round_index + 1}-provider-error: "
                    f"{str(last_exc) or 'unknown'}"
                )
            _log.error(
                "ollama followup round %d failed: %s", round_index, last_exc, exc_info=True
            )
            yield FollowupFailed(
                round_index=round_index,
                error=str(last_exc) or "unknown",
                summary=summary,
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
            yield FollowupFailed(
                round_index=round_index, error=summary, summary=summary
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
            yield FollowupFailed(
                round_index=round_index,
                error=str(exc) or "unknown",
                summary=summary,
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
            yield FollowupFailed(
                round_index=round_index, error=str(exc),
                summary=f"followup-round-{round_index + 1}-codex-error:{exc}",
            )
        except Exception as exc:  # noqa: BLE001 — surface as clean failure
            yield FollowupFailed(
                round_index=round_index, error=str(exc),
                summary=f"followup-round-{round_index + 1}-codex-error:{exc}",
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
    adapter = _ADAPTERS.get((provider or "").strip().lower())
    if adapter is None:
        yield FollowupFailed(
            round_index=round_index,
            error=f"unsupported-provider:{provider}",
            summary=f"followup-round-{round_index + 1}-unsupported-provider:{provider}",
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

