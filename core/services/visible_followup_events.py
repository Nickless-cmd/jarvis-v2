"""Follow-up event/carrier types + the adapter protocol (split from
``visible_followup.py``).

These are the pure data shapes exchanged between the follow-up adapters and
the caller (``visible_runs.py``). Adapters emit :data:`FollowupEvent` values;
the caller translates them into SSE + persistence at a single choke point.

``_observe_malformed_stream_payload`` lives here too because both the Ollama
and OpenAI-compat adapters (in ``visible_followup_adapters.py``) share it.

Everything here is re-exported from ``core.services.visible_followup`` for
backward compatibility — import from either module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol, runtime_checkable


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
