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
import time
from dataclasses import dataclass
from typing import Iterator, Protocol, runtime_checkable
from urllib import error as urllib_error
from urllib import request as urllib_request

_log = logging.getLogger(__name__)


# ── Event types ──────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class FollowupDelta:
    """A chunk of prose produced by the model during this follow-up round."""

    delta: str


@dataclass(frozen=True, slots=True)
class FollowupToolCalls:
    """Model requested one or more additional tool calls in this round."""

    tool_calls: list[dict]


@dataclass(frozen=True, slots=True)
class FollowupDone:
    """The model finished this round cleanly (may have emitted text, tool calls, or both)."""

    text: str


@dataclass(frozen=True, slots=True)
class FollowupFailed:
    """The round failed before completing (network error, HTTP 5xx, timeout, etc.)."""

    round_index: int
    error: str
    summary: str


FollowupEvent = FollowupDelta | FollowupToolCalls | FollowupDone | FollowupFailed


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

    Preserves the legacy message shape used by ``visible_runs.py`` prior to
    this adapter: tool results are packed into a single user-role message
    using ``[tool_name]:\\nresult`` blocks. Many local models handle this
    shape more reliably than the OpenAI ``role=tool`` message.
    """

    provider_id = "ollama"

    def _serialize_exchanges(self, exchanges: list[ToolExchange]) -> list[dict]:
        """Turn accumulated exchanges into the legacy Ollama message block.

        For each exchange we append: an assistant text message (if non-empty)
        followed by a user message containing ``[tool]:\\nresult`` blocks.
        The final exchange uses the first-turn seed prose; intermediate
        exchanges use the ``Continue.`` seed.
        """
        messages: list[dict] = []
        last_index = len(exchanges) - 1
        for idx, exch in enumerate(exchanges):
            if exch.text:
                messages.append({"role": "assistant", "content": exch.text})
            results_block = "\n\n".join(
                f"[{tr.tool_name}]:\n{tr.content}" for tr in exch.results
            )
            if idx == 0:
                seed = (
                    "Here are the tool results for your previous request:\n\n"
                    f"{results_block}\n\n"
                    "Please respond based on these results. "
                    "You may call additional tools if you need more information."
                )
            elif idx == last_index:
                seed = f"Tool results:\n\n{results_block}\n\nContinue."
            else:
                seed = f"Tool results:\n\n{results_block}"
            messages.append({"role": "user", "content": seed})
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
        from core.runtime.provider_router import resolve_provider_router_target

        target = resolve_provider_router_target(lane="visible")
        base_url = (
            str(target.get("base_url") or "").strip() or "http://127.0.0.1:11434"
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
        collected_tool_calls: list[dict] = []
        last_exc: BaseException | None = None

        attempts = 3
        for attempt in range(attempts):
            try:
                with urllib_request.urlopen(req, timeout=90) as resp:
                    for raw_line in resp:
                        line = raw_line.decode("utf-8").strip()
                        if not line:
                            continue
                        event = json.loads(line)
                        msg = event.get("message") or {}
                        delta = str(msg.get("content") or "")
                        if delta:
                            parts.append(delta)
                            yield FollowupDelta(delta=delta)
                        tc = msg.get("tool_calls") or []
                        if tc:
                            collected_tool_calls.extend(tc)
                        if event.get("done"):
                            break
                last_exc = None
                break
            except urllib_error.HTTPError as he:
                last_exc = he
                retryable = int(getattr(he, "code", 0) or 0) in {502, 503, 504}
                if retryable and attempt < (attempts - 1):
                    _log.warning(
                        "ollama followup round %d retrying after HTTP %s (attempt %d/%d)",
                        round_index,
                        getattr(he, "code", "?"),
                        attempt + 1,
                        attempts,
                    )
                    time.sleep(0.6 * (2**attempt))
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
        yield FollowupDone(text="".join(parts))


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
        credentials = _require_credentials(
            profile=self.provider_id, provider=self.provider_id
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
            payload["tools"] = list(tool_definitions)
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
            messages.append(
                {
                    "role": "assistant",
                    "content": exch.text,
                    "tool_calls": self._normalize_assistant_tool_calls(
                        list(exch.tool_calls)
                    ),
                }
            )
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
    ) -> Iterator[FollowupEvent]:
        from core.services.visible_model import (
            _chat_completion_stream_is_terminal,
            _extract_chat_completion_delta,
            _finalize_openai_tool_calls,
            _iter_sse_events,
            _merge_openai_tool_call_deltas,
        )

        messages = list(base_messages) + self._serialize_exchanges(exchanges)

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
        tool_call_accumulator: dict[int, dict] = {}
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
                        parts.append(delta)
                        yield FollowupDelta(delta=delta)
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
        _log.warning(
            "visible-latency provider=%s round=followup-%d prompt_chars=%d ttfb_ms=%s total_ms=%d text_chars=%d tool_calls=%d",
            self.provider_id,
            round_index,
            _prompt_chars,
            _ttfb_ms if _ttfb_ms is not None else -1,
            _total_ms,
            sum(len(p) for p in parts),
            len(tool_calls),
        )
        if tool_calls:
            yield FollowupToolCalls(tool_calls=tool_calls)
        yield FollowupDone(text="".join(parts))


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
