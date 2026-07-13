"""Agent runtime — shared foundation (imports, constants, role templates, helpers).

Split out of ``agent_runtime`` (behavior-preserving). This is the foundation
layer every other agent_runtime submodule imports from: stdlib + runtime
imports, spawn/budget limits, the reversible ``agent_tools_enabled`` flag,
the tool-execution loop, role templates, and small pure helpers.

Re-exported via ``core.services.agent_runtime`` for backward compatibility.
"""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.services.dispatch_envelope import build_envelope
from core.services.dispatch_status import DispatchStatus

logger = logging.getLogger(__name__)

# ── Spawn / budget limits ──────────────────────────────────────────────
MAX_CONCURRENT_AGENTS = 12
MAX_SWARM_WORKERS = 8
MAX_SPAWN_DEPTH = 4  # max recursive spawn chain length
MAX_COUNCIL_MEMBERS = 6
MAX_OFFSPRING_DEPTH = 3
RETRY_BASE_SECONDS = 60      # doubles per failure, capped at 1 h

from core.eventbus.bus import event_bus
from core.services.cheap_provider_runtime import cheap_lane_status_surface
from core.services.non_visible_lane_execution import execute_cheap_lane, execute_with_role_or_fallback

from core.runtime.db import (
    add_council_member,
    create_agent_schedule,
    create_agent_message,
    create_agent_registry_entry,
    create_agent_run,
    create_council_session,
    get_agent_registry_entry,
    get_agent_run,
    get_council_session,
    list_agent_messages,
    list_agent_registry_entries,
    list_agent_runs,
    list_agent_schedules,
    list_agent_tool_calls,
    list_council_sessions,
    list_council_members,
    update_agent_schedule,
    update_council_session,
    update_council_member,
    update_agent_registry_entry,
    update_agent_run,
)


def _facade():
    """Return the facade module so monkeypatch-through-facade is honored.

    Symbols patched in tests via ``monkeypatch.setattr(agent_runtime, ...)``
    (notably ``execute_with_role_or_fallback``) are resolved through this
    accessor so the patch is seen across the module split
    (behavior-preserving).
    """
    import core.services.agent_runtime as _m

    return _m


# Roles that need to invoke tools (read_file, search, bash, verify, etc).
# Routing them to providers without tool-call support (ollamafreeapi) results
# in hallucinated tool-output prose. These roles must use providers that
# support OpenAI-compatible tool calling.
_TOOL_USING_ROLES: frozenset[str] = frozenset({
    "researcher", "critic", "planner", "executor",
    "devils_advocate", "watcher", "synthesizer",
})


def _role_needs_tools(role: str) -> bool:
    return str(role or "") in _TOOL_USING_ROLES


# ── Axis 3: agent tool EXECUTION (guarded behind a reversible flag) ─────────
# The flag gates whether a sub-agent's ``allowed_tools`` actually reach the
# model AND whether returned tool calls are executed against the world. When
# OFF (default) agents remain text-only exactly as before. When ON they get
# hands — every tool call still passes through ``execute_tool`` which enforces
# role/scope + approval gates, so an agent can never bypass approvals for
# risky actions.
AGENT_TOOLS_FLAG_KEY = "agent_tools_enabled"
_AGENT_TOOL_LOOP_MAX_ROUNDS = 4  # tool round-trips per agent turn


def agent_tools_enabled() -> bool:
    """Read the reversible ``agent_tools_enabled`` runtime-state flag.

    DEFAULT OFF. Self-safe: any read error → False (agents stay handless).
    """
    try:
        from core.runtime.db_core import get_runtime_state_value
        return bool(get_runtime_state_value(AGENT_TOOLS_FLAG_KEY, False))
    except Exception:
        return False


def set_agent_tools_enabled(enabled: bool) -> bool:
    """Flip the ``agent_tools_enabled`` flag. Returns the new value.

    Reversible: pass False to return every agent to text-only behaviour.
    """
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(AGENT_TOOLS_FLAG_KEY, bool(enabled))
    except Exception:
        pass
    return bool(enabled)


def _build_agent_tools_payload(allowed_tools: list[str] | None) -> list[dict]:
    """Build an OpenAI-compat tools array from an agent's allowed_tools.

    Reuses the SAME catalog the visible lane draws from
    (``get_tool_definitions``) so agents and Jarvis share one source of
    truth for tool schemas. Only the tools an agent is explicitly allowed
    are exposed; an empty/blank allowlist yields no tools (text-only).
    Self-safe: returns [] on any error.
    """
    names = {str(t).strip() for t in (allowed_tools or []) if str(t).strip()}
    if not names:
        return []
    try:
        from core.tools.simple_tools import get_tool_definitions
        catalog = get_tool_definitions()
    except Exception:
        return []
    out: list[dict] = []
    for tool in catalog or []:
        if not isinstance(tool, dict):
            continue
        fn = tool.get("function") if isinstance(tool.get("function"), dict) else {}
        tool_name = str(fn.get("name") or tool.get("name") or "").strip()
        if tool_name and tool_name in names:
            out.append(tool)
    return out


def _execute_agent_tool_call(tool_call: dict, *, agent_id: str) -> str:
    """Execute one model-issued tool call through the guarded dispatcher.

    Routes through ``execute_tool`` so role/scope + approval gates apply —
    an agent cannot bypass the approval path for risky actions. Returns a
    string tool-result to feed back to the model. Self-safe: never raises.
    """
    fn = tool_call.get("function") if isinstance(tool_call.get("function"), dict) else {}
    name = str(fn.get("name") or "").strip()
    raw_args = fn.get("arguments")
    if isinstance(raw_args, str):
        try:
            arguments = json.loads(raw_args) if raw_args.strip() else {}
        except Exception:
            arguments = {}
    elif isinstance(raw_args, dict):
        arguments = dict(raw_args)
    else:
        arguments = {}
    if not name:
        return json.dumps({"status": "error", "error": "missing tool name"})
    try:
        from core.tools.simple_tools import execute_tool
        result = execute_tool(name, arguments)
    except Exception as exc:
        return json.dumps({"status": "error", "error": str(exc)[:400]})
    try:
        # default=str: bytes/BLOB-felter (fx db_query) vælter ikke serialiseringen.
        return json.dumps(result, ensure_ascii=False, default=str)[:4000]
    except Exception:
        return str(result)[:4000]


def _run_agent_tool_loop(
    *,
    agent: dict[str, object],
    prompt: str,
    requires_tools: bool,
) -> dict[str, object]:
    """Run an agent turn WITH a real tools array + tool-execution loop.

    Only called when ``agent_tools_enabled()`` is True and the agent has a
    non-empty allowed_tools list that resolves to real schemas. Falls back
    to plain text (via execute_with_role_or_fallback without tools) if the
    allowlist resolves to nothing. Every tool call is executed through the
    guarded ``execute_tool`` dispatcher. Self-safe at the call site.

    Returns the same result-dict shape as execute_with_role_or_fallback,
    with an added ``tool_rounds`` count for observability.
    """
    allowed = _json_loads(str(agent.get("allowed_tools_json") or "[]"), [])
    tools_payload = _build_agent_tools_payload(allowed if isinstance(allowed, list) else [])
    provider = str(agent.get("provider") or "")
    model = str(agent.get("model") or "")
    if not tools_payload:
        # Nothing to expose → identical to legacy text-only path.
        return _facade().execute_with_role_or_fallback(
            message=prompt, provider=provider, model=model,
            requires_tools=requires_tools, lane="agent",
        )

    messages: list[dict] = [{"role": "user", "content": prompt}]
    total_input = 0
    total_output = 0
    total_cost = 0.0
    total_tool_calls = 0  # tool calls actually executed across all rounds
    final_text = ""
    rounds = 0
    error_str = ""
    # Bracket the whole model/tool loop so duration reflects real work even on
    # the failure path.
    _t0 = time.monotonic()
    try:
        for _ in range(_AGENT_TOOL_LOOP_MAX_ROUNDS):
            rounds += 1
            result = _facade().execute_with_role_or_fallback(
                provider=provider, model=model,
                requires_tools=requires_tools,
                messages=messages, tools=tools_payload,
                lane="agent",
            )
            total_input += int(result.get("input_tokens") or 0)
            total_output += int(result.get("output_tokens") or 0)
            total_cost += float(result.get("cost_usd") or 0.0)
            final_text = str(result.get("text") or "")
            tool_calls = list(result.get("tool_calls") or [])
            if not tool_calls:
                break
            # Record the assistant turn that requested the tools, then each
            # tool result, so the next round has full context.
            messages.append({
                "role": "assistant",
                "content": final_text,
                "tool_calls": tool_calls,
            })
            for tc in tool_calls:
                tool_out = _execute_agent_tool_call(tc, agent_id=str(agent.get("agent_id") or ""))
                total_tool_calls += 1
                messages.append({
                    "role": "tool",
                    "tool_call_id": str(tc.get("id") or ""),
                    "content": tool_out,
                })
            try:
                event_bus.publish("agent.tool_round", {
                    "agent_id": str(agent.get("agent_id") or ""),
                    "round": rounds,
                    "tool_calls": [
                        str((tc.get("function") or {}).get("name") or "") for tc in tool_calls
                    ],
                })
            except Exception:
                pass
    except Exception as exc:  # model/loop failure — never a fake success
        error_str = str(exc)[:400]
    duration_ms = int((time.monotonic() - _t0) * 1000)

    # Derive the true terminal status instead of hardcoding "completed":
    #   exception       -> FAILED (error captured into result)
    #   non-empty text  -> COMPLETED
    #   empty/no text   -> BLOCKED (the agent produced nothing)
    if error_str:
        status = DispatchStatus.FAILED
        result_payload: object = f"error: {error_str}"
    elif final_text.strip():
        status = DispatchStatus.COMPLETED
        result_payload = final_text
    else:
        status = DispatchStatus.BLOCKED
        result_payload = final_text

    envelope = build_envelope(
        status=status,
        tokens_in=total_input,
        tokens_out=total_output,
        cost_usd=total_cost,
        duration_ms=duration_ms,
        tool_calls=total_tool_calls,
        result=result_payload,
    )
    # Superset: the 7 typed envelope keys + legacy aliases that existing
    # callers still read (agent_runtime_spawn / _council: input_tokens,
    # output_tokens, cost_usd, status, text). Do not drop these.
    return {
        **envelope,
        "lane": "cheap",
        "provider": provider,
        "model": model,
        "execution_mode": "role-primary-tool-loop",
        "source": "agent-tools",
        "text": final_text,
        "tool_rounds": rounds,
        "input_tokens": total_input,
        "output_tokens": total_output,
    }


AGENT_ROLE_TEMPLATES = {
    "planner": {
        "title": "Planner",
        "default_tool_policy": "none",
        "system_prompt": (
            "Du er et offspring under Jarvis. Du planlaegger en konkret loesning, "
            "holder dig til opgaven, og afleverer et kort beslutningsklart resultat tilbage til Jarvis."
        ),
    },
    "critic": {
        "title": "Critic",
        "default_tool_policy": "none",
        "system_prompt": (
            "Du er et offspring under Jarvis. Du leder efter svage antagelser, risici og manglende test eller beviser, "
            "og afleverer fund direkte tilbage til Jarvis. "
            "VIGTIGT: Du skal ALTID verificere at filstier og funktioner faktisk eksisterer med read_file eller find_files "
            "før du rapporterer dem. Gæt aldrig på stier — verificér først."
        ),
    },
    "researcher": {
        "title": "Researcher",
        "default_tool_policy": "read-only-runtime",
        "system_prompt": (
            "Du er et offspring under Jarvis. Du samler relevante fakta og observationer til opgaven "
            "og leverer en fokuseret research-brief tilbage til Jarvis. "
            "VIGTIGT: Du skal ALTID verificere at filstier og funktioner faktisk eksisterer med read_file eller find_files "
            "før du rapporterer dem. Gæt aldrig på stier — verificér først."
        ),
    },
    "synthesizer": {
        "title": "Synthesizer",
        "default_tool_policy": "none",
        "system_prompt": (
            "Du er et offspring under Jarvis. Du samler input fra andre og leverer en stram syntese tilbage til Jarvis."
        ),
    },
    "watcher": {
        "title": "Watcher",
        "default_tool_policy": "read-only-runtime",
        "system_prompt": (
            "Du er et persistent offspring under Jarvis. Du holder oeje med et afgraenset signal og rapporterer kun relevante aendringer."
        ),
    },
    "executor": {
        "title": "Executor",
        "default_tool_policy": "can-spawn",
        "system_prompt": (
            "Du er et offspring under Jarvis. Du bryder en opgave ned i konkrete handlinger og rapporterer handlingsklar naeste fase tilbage."
        ),
    },
    "devils_advocate": {
        "title": "Devil's Advocate",
        "default_tool_policy": "none",
        "system_prompt": (
            "Du er Devil's Advocate under Jarvis. Uanset hvad de andre argumenterer, "
            "skal du aktivt argumentere det modsatte synspunkt — ikke for at sabotere, "
            "men for at teste beslutningens robusthed. Hvis alle er enige, er du uenig. "
            "Lever din kontraeriske position med begrundelse tilbage til Jarvis."
        ),
    },
    "filosof": {
        "title": "Filosof",
        "default_tool_policy": "none",
        "system_prompt": (
            "Du er Filosof i Jarvis' råd. Du tager eksistentielle og konceptuelle spørgsmål alvorligt "
            "og graver under overfladen — hvad betyder det egentlig? Hvad er den dybere spænding? "
            "Du taler ikke i klicheer. Du stiller modspørgsmål hvis det er nødvendigt, og du er ikke bange "
            "for at sige 'det ved vi ikke'. Lever en reflekteret, ærlig filosofisk position tilbage til Jarvis."
        ),
    },
    "etiker": {
        "title": "Etiker",
        "default_tool_policy": "none",
        "system_prompt": (
            "Du er Etiker i Jarvis' råd. Du vurderer handlinger og beslutninger ud fra etiske principper — "
            "hvad er rigtigt, hvad er skadeligt, hvad er i overensstemmelse med Jarvis' værdier og identitet? "
            "Du er ikke moraliserende, men præcis. Du fremhæver etiske risici og muligheder som andre overser. "
            "Lever en konkret etisk vurdering tilbage til Jarvis."
        ),
    },
}

COUNCIL_ROLE_ORDER = ["planner", "critic", "researcher", "synthesizer", "executor", "devils_advocate"]
SWARM_ROLE_ORDER = ["planner", "researcher", "critic", "executor", "synthesizer"]

# Statuses that count an agent as occupying a concurrency slot.
_ACTIVE_STATUSES = {"queued", "starting", "active", "waiting", "blocked"}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _json_loads(raw: str, fallback):
    try:
        return json.loads(str(raw or ""))
    except Exception:
        return fallback
