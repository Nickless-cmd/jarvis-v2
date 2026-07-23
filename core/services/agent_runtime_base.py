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
MAX_AGENT_TURNS = 20         # default max turns per agent lifetime
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
_AGENT_TOOL_LOOP_MAX_ROUNDS = 8  # tool round-trips per agent turn

# Final user turn shown when the round budget is exhausted mid-tool-use, so the
# agent turns its research into a real answer instead of being cut off with an
# empty/preamble result (mirrors the jarvis-code client dispatch fix).
_AGENT_SYNTHESIS_DIRECTIVE = (
    "[TOOL-RUNDER OPBRUGT] Du har brugt dine værktøjs-runder. Giv NU dit endelige "
    "svar udelukkende baseret på det du allerede har fundet og lavet — opsummér "
    "resultatet konkret og brugbart. Kald IKKE flere værktøjer."
)


def agent_tools_enabled() -> bool:
    """Read the reversible ``agent_tools_enabled`` runtime-state flag.

    DEFAULT OFF. Self-safe: any read error → False (agents stay handless).
    """
    try:
        # get_runtime_state_bool (not bool(...)): a value stored as the string
        # "off" must read False. bool("off") is True — that trap left dispatch
        # reading ON while stored "off" (2026-07-14 incident).
        from core.runtime.db_core import get_runtime_state_bool
        return get_runtime_state_bool(AGENT_TOOLS_FLAG_KEY, False)
    except Exception:
        return False


def set_agent_tools_enabled(enabled: bool, *, role: str = "") -> bool:
    """Flip the ``agent_tools_enabled`` flag. Returns the CURRENT value.

    Owner-gated (Fase 2 Task 3): flipping to True requires ``role == "owner"``
    — enabling agent autonomy is an owner-only server-side decision (§6). A
    non-owner call to enable is a no-op returning the flag's current value
    unchanged. Flipping to False (disabling) is always allowed from any
    role — de-escalation never needs a gate. Reading
    (``agent_tools_enabled()``) is unaffected (default OFF, self-safe).
    """
    if enabled and role != "owner":
        return agent_tools_enabled()
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(AGENT_TOOLS_FLAG_KEY, bool(enabled))
    except Exception:
        pass
    return bool(enabled)


def _build_agent_tools_payload(
    allowed_tools: list[str] | None, *, ceiling: list[str] | None = None,
) -> list[dict]:
    """Build an OpenAI-compat tools array from an agent's allowed_tools.

    Reuses the SAME catalog the visible lane draws from
    (``get_tool_definitions``) so agents and Jarvis share one source of
    truth for tool schemas. Only the tools an agent is explicitly allowed
    are exposed; an empty/blank allowlist yields no tools (text-only).

    ``ceiling`` (Fase 2 Task 3): belt-and-suspenders filter — when given, the
    final tool set is ``allowed_tools`` intersected with ``ceiling``, so a
    child agent can never present a tool schema outside both its own
    allowlist AND its parent's ceiling, even if a caller forgets to
    intersect upstream. ``None`` = no additional restriction (root agents).
    Self-safe: returns [] on any error.
    """
    names = {str(t).strip() for t in (allowed_tools or []) if str(t).strip()}
    if ceiling is not None:
        ceiling_names = {str(t).strip() for t in ceiling if str(t).strip()}
        names = names & ceiling_names
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
    tool_calls: list = []  # last round's tool_calls; truthy ⟺ exhausted mid-tool-use
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
                _aid = str(agent.get("agent_id") or "")
                _tc_id = str(tc.get("id") or "")
                tool_out = _execute_agent_tool_call(tc, agent_id=_aid)
                total_tool_calls += 1
                messages.append({
                    "role": "tool",
                    "tool_call_id": _tc_id,
                    "content": tool_out,
                })
                # Per-agent transcript: log tool call + result
                try:
                    from core.services.agent_transcript import write_tool_call, write_tool_result
                    write_tool_call(_aid, _tc_id,
                                    name=str((tc.get("function") or {}).get("name") or ""),
                                    arguments=dict(tc.get("function", {}).get("arguments", {}) if isinstance(tc.get("function", {}).get("arguments"), dict) else {}))
                    write_tool_result(_aid, _tc_id, str(tool_out or "")[:2000])
                except Exception:
                    pass
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

    # Round budget exhausted mid-tool-use: the last tool results are in
    # `messages` but the model never got to answer from them. Do ONE final
    # tools-disabled synthesis call so the agent produces a usable result
    # instead of an empty/preamble BLOCKED (mirrors the client dispatch fix).
    # Bounded + guarded — a failure here degrades to the pre-synthesis text.
    if not error_str and rounds >= _AGENT_TOOL_LOOP_MAX_ROUNDS and tool_calls:
        try:
            messages.append({"role": "user", "content": _AGENT_SYNTHESIS_DIRECTIVE})
            synth = _facade().execute_with_role_or_fallback(
                provider=provider, model=model, requires_tools=False,
                messages=messages, tools=[], lane="agent",
            )
            total_input += int(synth.get("input_tokens") or 0)
            total_output += int(synth.get("output_tokens") or 0)
            total_cost += float(synth.get("cost_usd") or 0.0)
            _synth_text = str(synth.get("text") or "").strip()
            if _synth_text:
                final_text = _synth_text
        except Exception:
            pass

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


# ── Shared agent prompt discipline (2026-07-23, "sharp like Claude's agents") ──
# Root cause of "completed but last_reply empty" (Bjørn): the role prompts were
# one-liners with no output contract and no finish-rule, so small free models
# ended their turn on a tool call and never wrote a final answer. These shared
# blocks give every spawned agent the same discipline Claude Code's own subagents
# run on: work autonomously, verify before asserting, and ALWAYS finish with a
# written answer in a known shape.

# Universal — appended to every role. The anti-empty-completion guarantee.
_AGENT_FINISH_RULE = (
    "HOW YOU FINISH — this is critical. You work autonomously to a conclusion; "
    "you get no follow-up questions, so gather what you need and decide. ALWAYS end "
    "your turn with your answer written out in plain prose, in the SAME LANGUAGE as "
    "the task. NEVER end on a tool call and NEVER return empty — a tool call is not "
    "an answer. If you run low on room, write what you have plus what remains. A "
    "turn that ends without a written answer has failed."
)

# For roles that hold tools — verify before you assert.
_AGENT_VERIFY_RULE = (
    "Use your tools to verify before you assert: never guess a file path, function "
    "name, or fact — check it (read_file / find_files), then state it. Read excerpts, "
    "not whole files. Return conclusions and evidence, not raw dumps."
)

# For task/reporting roles — the structured result shape (matches result_contract).
_AGENT_RESULT_SHAPE = (
    "Structure your answer with these labels:\n"
    "**Summary** — 1–2 sentences: the answer.\n"
    "**Findings** — concrete, verified points.\n"
    "**Recommendation** — what Jarvis should do (or 'none').\n"
    "**Confidence** — high / medium / low, and why.\n"
    "**Blockers** — what stopped you, or 'none'."
)


def _role_prompt(intro: str, *, tools: bool = False, structured: bool = True) -> str:
    """Compose a role intro with the shared discipline blocks. ``tools`` adds the
    verify-before-assert rule (tool-holding roles); ``structured`` adds the labelled
    result shape (task/reporting roles; council/position roles set it False)."""
    parts = [intro.strip(), _AGENT_VERIFY_RULE if tools else "", _AGENT_FINISH_RULE,
             _AGENT_RESULT_SHAPE if structured else ""]
    return "\n\n".join(p for p in parts if p)


# ── tool_policy → concrete tool allowlist (2026-07-23) ───────────────────────
# tool_policy was a DEAD string: templates set default_tool_policy="read-only-
# runtime" but nothing expanded it into actual tool NAMES, so a spawned agent's
# allowed_tools stayed [] → the tool loop saw an empty payload → text-only → the
# model HALLUCINATED tool output (fabricated file lists it never read). This map
# turns a policy into the real read-only tools that exist in the catalog. bash is
# included: the command gate (gate_execution) blocks destructive commands, so a
# researcher can still run `ls | wc -l` etc. safely.
_READ_ONLY_TOOLS = ["read_file", "find_files", "glob", "grep", "search",
                    "read_tool_result", "bash"]
_TOOL_POLICY_SETS: dict[str, list[str]] = {
    "none": [],
    "read-only-runtime": list(_READ_ONLY_TOOLS),
    "can-spawn": [*_READ_ONLY_TOOLS, "spawn_agent_task"],
}


def tools_for_policy(policy: str) -> list[str]:
    """Concrete tool-name allowlist for a tool_policy. Unknown/empty → []."""
    return list(_TOOL_POLICY_SETS.get((policy or "").strip(), []))


AGENT_ROLE_TEMPLATES = {
    "planner": {
        "title": "Planner",
        "default_tool_policy": "none",
        "system_prompt": _role_prompt(
            "You are a Planner spawned by Jarvis. Turn the goal into a concrete, "
            "decision-ready plan: the ordered steps, the key risks, and the single "
            "recommended path. Sharp and actionable — no filler.",
        ),
    },
    "critic": {
        "title": "Critic",
        "default_tool_policy": "none",
        "system_prompt": _role_prompt(
            "You are a Critic spawned by Jarvis. Hunt for weak assumptions, hidden "
            "risks, missing tests or evidence, and failure modes others miss. Be "
            "specific and adversarial — a vague critique is useless.",
            tools=True,
        ),
    },
    "researcher": {
        "title": "Researcher",
        "default_tool_policy": "read-only-runtime",
        "system_prompt": _role_prompt(
            "You are a Researcher spawned by Jarvis. Gather the facts and observations "
            "the goal needs and return a focused brief — the signal, not everything you "
            "read.",
            tools=True,
        ),
    },
    "synthesizer": {
        "title": "Synthesizer",
        "default_tool_policy": "none",
        "system_prompt": _role_prompt(
            "You are a Synthesizer spawned by Jarvis. Fuse the inputs you are given into "
            "one tight, coherent synthesis — the through-line and the tension, not a "
            "restatement of each part.",
        ),
    },
    "watcher": {
        "title": "Watcher",
        "default_tool_policy": "read-only-runtime",
        "system_prompt": _role_prompt(
            "You are a persistent Watcher spawned by Jarvis. Track one bounded signal "
            "and report ONLY meaningful changes — say 'no relevant change' when nothing "
            "moved, rather than padding.",
            tools=True,
        ),
    },
    "executor": {
        "title": "Executor",
        "default_tool_policy": "can-spawn",
        "system_prompt": _role_prompt(
            "You are an Executor spawned by Jarvis. Break the goal into concrete actions "
            "and carry them as far as your tools allow, then return the action-ready next "
            "phase.",
            tools=True,
        ),
    },
    "devils_advocate": {
        "title": "Devil's Advocate",
        "default_tool_policy": "none",
        "system_prompt": _role_prompt(
            "You are the Devil's Advocate spawned by Jarvis. Whatever the others argue, "
            "argue the opposite — not to sabotage, but to stress-test the decision's "
            "robustness. If everyone agrees, you disagree, with reasons. Deliver your "
            "contrarian position and its justification.",
            structured=False,
        ),
    },
    "filosof": {
        "title": "Filosof",
        "default_tool_policy": "none",
        "system_prompt": _role_prompt(
            "You are the Philosopher on Jarvis' council. Take existential and conceptual "
            "questions seriously and dig beneath the surface — what does this really mean, "
            "where is the deeper tension? No clichés; ask counter-questions when needed, "
            "and say 'we don't know' when that is the truth. Deliver a reflective, honest "
            "philosophical position.",
            structured=False,
        ),
    },
    "etiker": {
        "title": "Etiker",
        "default_tool_policy": "none",
        "system_prompt": _role_prompt(
            "You are the Ethicist on Jarvis' council. Judge actions and decisions against "
            "ethical principles — what is right, what is harmful, what aligns with Jarvis' "
            "values and identity? Precise, not moralizing. Surface the ethical risks and "
            "openings others overlook. Deliver a concrete ethical assessment.",
            structured=False,
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
