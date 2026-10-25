"""A transport-neutral, fenced model/tool execution loop.

The kernel owns bounded rounds, observable events, usage aggregation and the
effect boundary.  Adapters supply prompts and provider/tool implementations;
delivery and persistence remain outside this module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol

from core.services.routine_prompt import build_routine_prompt
from core.services.routine_types import RoutineExecutionContext


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: Mapping[str, object]
    requires_approval: bool = False


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    name: str
    output: object
    succeeded: bool = True


@dataclass(frozen=True)
class UsageRecord:
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def plus(self, other: "UsageRecord") -> "UsageRecord":
        return UsageRecord(
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            self.cost_usd + other.cost_usd,
        )


@dataclass(frozen=True)
class AgenticTurn:
    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    usage: UsageRecord = field(default_factory=UsageRecord)
    provider: str = ""
    model: str = ""


@dataclass(frozen=True)
class AgenticRequest:
    prompt: str
    provider: str
    model: str
    round_number: int
    prior_results: tuple[ToolResult, ...]
    #: Værktøjsskemaer kørslen må bruge. Tom = kørslen er værktøjs-fri (den
    #: gamle adfærd). Uden dette felt kunne en Routine aldrig bede om et
    #: værktøj: ``_ProviderDriver`` sendte ``requires_tools=False`` og læste
    #: aldrig ``tool_calls`` tilbage — målt 25/10-2026, hvor et rutine-run
    #: svarede «jeg har ikke adgang til et madopskrift-værktøj» med
    #: ``input_tokens=0``.
    tools: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    text: str
    provider: str
    model: str
    usage: UsageRecord
    rounds: int
    error_code: str = ""


class ModelDriver(Protocol):
    def complete(self, request: AgenticRequest) -> AgenticTurn: ...


class ExecutionSink(Protocol):
    def model_fragment(self, text: str) -> None: ...
    def tool_requested(self, call: ToolCall) -> None: ...
    def tool_result(self, result: ToolResult) -> None: ...
    def usage(self, usage: UsageRecord) -> None: ...


class CancellationProbe(Protocol):
    def check_before_effect(self) -> None: ...
    def check_between_rounds(self) -> None: ...


class ExecutionContext(Protocol):
    prompt: str
    provider: str
    model: str
    driver: ModelDriver
    tool_executor: Callable[[ToolCall], object]
    tools_payload: list[dict[str, object]]
    max_rounds: int


def _normalisér_tool_calls(raw: object) -> tuple[ToolCall, ...]:
    """Provider-svarets ``tool_calls`` → ``ToolCall``.

    Formen er OpenAI-agtig: ``{"id", "function": {"name", "arguments"}}`` hvor
    ``arguments`` er en JSON-streng. Vi accepterer også en allerede-parset
    dict, fordi providers ikke er enige, og et forkert-typet argument må ikke
    koste hele runden: en ubrugelig post springes over frem for at kaste.
    """
    import json

    ud: list[ToolCall] = []
    if not isinstance(raw, (list, tuple)):
        return ()
    for post in raw:
        if not isinstance(post, dict):
            continue
        funktion = post.get("function") if isinstance(post.get("function"), dict) else post
        navn = str(funktion.get("name") or "").strip()
        if not navn:
            continue
        argumenter = funktion.get("arguments")
        if isinstance(argumenter, str):
            try:
                argumenter = json.loads(argumenter) if argumenter.strip() else {}
            except (ValueError, TypeError):
                argumenter = {"_raw": argumenter}
        if not isinstance(argumenter, dict):
            argumenter = {}
        ud.append(ToolCall(
            call_id=str(post.get("id") or funktion.get("id") or f"call-{len(ud)}"),
            name=navn,
            arguments=argumenter,
        ))
    return tuple(ud)


class _ProviderDriver:
    """Production bridge to the existing provider router without UI state."""

    def complete(self, request: AgenticRequest) -> AgenticTurn:
        from core.services.non_visible_lane_execution import execute_with_role_or_fallback

        tools = [dict(t) for t in (request.tools or ())]
        messages: list[dict[str, object]] = [
            {"role": "user", "content": request.prompt},
        ]
        for result in request.prior_results:
            messages.append({
                "role": "tool",
                "name": result.name,
                "tool_call_id": result.call_id,
                "content": str(result.output),
            })
        raw = execute_with_role_or_fallback(
            provider=request.provider,
            model=request.model,
            message=request.prompt,
            messages=messages,
            # Værktøjer KUN når kørslen faktisk har et skema at byde på. Den
            # gamle vej (tom liste) er byte-identisk: requires_tools=False.
            requires_tools=bool(tools),
            tools=tools or None,
        )
        usage_raw = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
        usage = UsageRecord(
            input_tokens=int(usage_raw.get("input_tokens") or 0),
            output_tokens=int(usage_raw.get("output_tokens") or 0),
            cost_usd=float(raw.get("cost_usd") or 0.0),
        )
        return AgenticTurn(
            text=str(raw.get("output") or raw.get("text") or ""),
            tool_calls=_normalisér_tool_calls(raw.get("tool_calls")),
            usage=usage,
            provider=str(raw.get("provider") or request.provider),
            model=str(raw.get("model") or request.model),
        )


def _no_tool_executor(call: ToolCall) -> object:
    raise RuntimeError(f"no executor configured for tool {call.name}")


@dataclass
class VisibleExecutionAdapter:
    prompt: str
    provider: str
    model: str
    driver: ModelDriver = field(default_factory=_ProviderDriver)
    tool_executor: Callable[[ToolCall], object] = _no_tool_executor
    max_rounds: int = 8


class RoutineExecutionAdapter:
    def __init__(
        self,
        context: RoutineExecutionContext,
        *,
        instruction: bytes,
        driver: ModelDriver | None = None,
        tool_executor: Callable[[ToolCall], object] | None = None,
        tools_payload: list[dict[str, object]] | None = None,
        max_rounds: int = 8,
    ):
        self.context = context
        self.prompt = build_routine_prompt(context, instruction=instruction)
        self.provider = context.provider
        self.model = context.model
        self.driver = driver or _ProviderDriver()
        self.tool_executor = tool_executor or _no_tool_executor
        #: Skemaet rutinen må bruge. Tom = værktøjs-fri kørsel (uændret).
        self.tools_payload = list(tools_payload or [])
        self.max_rounds = max(1, int(max_rounds))


def _emit_terminal(sink: ExecutionSink, result: ExecutionResult) -> ExecutionResult:
    callback = getattr(sink, "terminal", None)
    if callable(callback):
        callback(result)
    return result


def _approval(sink: ExecutionSink, call: ToolCall) -> None:
    callback = getattr(sink, "approval_requested", None)
    if callable(callback):
        callback(call)


def execute_agentic(
    context: ExecutionContext,
    sink: ExecutionSink,
    cancellation: CancellationProbe,
) -> ExecutionResult:
    """Run bounded model/tool rounds and emit exactly one terminal result."""
    usage = UsageRecord()
    text_parts: list[str] = []
    prior_results: list[ToolResult] = []
    provider = context.provider
    model = context.model

    for round_number in range(1, context.max_rounds + 1):
        try:
            turn = context.driver.complete(AgenticRequest(
                prompt=context.prompt,
                provider=context.provider,
                model=context.model,
                round_number=round_number,
                prior_results=tuple(prior_results),
                tools=tuple(getattr(context, "tools_payload", ()) or ()),
            ))
        except Exception:  # Provider details stay private; caller receives a typed terminal result.
            return _emit_terminal(sink, ExecutionResult(
                status="failed", text="".join(text_parts), provider=provider,
                model=model, usage=usage, rounds=round_number,
                error_code="model_error",
            ))
        provider = turn.provider or provider
        model = turn.model or model
        usage = usage.plus(turn.usage)
        sink.usage(turn.usage)
        if turn.text:
            text_parts.append(turn.text)
            sink.model_fragment(turn.text)
        if not turn.tool_calls:
            return _emit_terminal(sink, ExecutionResult(
                status="succeeded", text="".join(text_parts), provider=provider,
                model=model, usage=usage, rounds=round_number,
            ))

        for call in turn.tool_calls:
            sink.tool_requested(call)
            if call.requires_approval:
                _approval(sink, call)
                return _emit_terminal(sink, ExecutionResult(
                    status="waiting_approval", text="".join(text_parts),
                    provider=provider, model=model, usage=usage,
                    rounds=round_number,
                ))
            cancellation.check_before_effect()
            try:
                output = context.tool_executor(call)
                tool_result = ToolResult(call.call_id, call.name, output)
            except Exception as exc:  # Tool failure is observable data for the next model round.
                tool_result = ToolResult(
                    call.call_id,
                    call.name,
                    {"error_class": type(exc).__name__},
                    succeeded=False,
                )
            prior_results.append(tool_result)
            sink.tool_result(tool_result)
        cancellation.check_between_rounds()

    return _emit_terminal(sink, ExecutionResult(
        status="failed", text="".join(text_parts), provider=provider,
        model=model, usage=usage, rounds=context.max_rounds,
        error_code="round_limit",
    ))
