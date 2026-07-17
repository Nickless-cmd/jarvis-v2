"""Agent runtime — sub-agents, councils, swarms (facade).

Jarvis' agent runtime: spawn/execute single sub-agents, run councils and
swarms to a landing conclusion, and manage the full agent lifecycle
(scheduling, budgets, retries, cleanup, promotion, crash recovery).

This module was split (behavior-preserving) into focused submodules:

- ``agent_runtime_base``     — imports, limits, role templates, tool loop,
                                the reversible ``agent_tools_enabled`` flag,
                                and small pure helpers
- ``agent_runtime_surfaces`` — read/build surfaces over agents + councils
- ``agent_runtime_spawn``    — spawn/execute/message/schedule/cleanup +
                                terminal lifecycle transitions
- ``agent_runtime_council``  — council & swarm collective rounds

Every public and private symbol that previously lived here is re-exported
from this module for full backward compatibility. Notably
``execute_with_role_or_fallback`` and ``execute_cheap_lane`` remain
patchable on this module — the submodules resolve the former through a
facade accessor so ``monkeypatch.setattr(agent_runtime,
"execute_with_role_or_fallback", ...)`` is honored across the split.
"""

from __future__ import annotations

# Re-export the full split surface. ``import *`` brings back every public
# symbol that used to be defined in this file (constants, db re-exports,
# execute_with_role_or_fallback/execute_cheap_lane, and all functions).
from core.services.agent_runtime_base import *  # noqa: F401,F403
from core.services.agent_runtime_surfaces import *  # noqa: F401,F403
from core.services.agent_runtime_spawn import *  # noqa: F401,F403
from core.services.agent_runtime_council import *  # noqa: F401,F403

# Underscore-prefixed / non-``*``-exported symbols that historical call-sites
# and tests import by name from this module. Explicit re-exports so they
# survive the ``import *`` (which skips leading-underscore names).
from core.services.agent_runtime_base import (  # noqa: F401
    _AGENT_TOOL_LOOP_MAX_ROUNDS,
    _ACTIVE_STATUSES,
    _TOOL_USING_ROLES,
    _build_agent_tools_payload,
    _execute_agent_tool_call,
    _facade,
    _json_loads,
    _now_iso,
    _role_needs_tools,
    _run_agent_tool_loop,
    event_bus,
    execute_cheap_lane,
    execute_with_role_or_fallback,
    logger,
)
from core.services.agent_runtime_surfaces import (  # noqa: F401
    _progress_label,
)
from core.services.agent_runtime_spawn import (  # noqa: F401
    _SPAWN_TOOL_INSTRUCTION,
    _WATCHER_RELAY_KEYWORDS,
    _agent_thread_id,
    _build_agent_prompt,
    _check_budget_and_expire,
    _check_max_turns_and_expire,
    _check_spawn_limits,
    _council_thread_id,
    _format_messages,
    _handle_agent_spawn_calls,
    _maybe_relay_watcher_signal,
    _result_contract_text,
    _schedule_retry_backoff,
    _spawn_depth_for,
)
from core.services.agent_runtime_council import (  # noqa: F401
    _augment_council_surface,
    _build_council_role_prefixed_summary,
    _close_council_agents,
    _derive_initiative,
    _detect_swarm_conflicts,
    _extract_confidence,
    _extract_vote,
    _format_peer_context,
    _load_council_model_config,
    _parse_percent_confidence,
    _run_collective_round,
    _trim,
)
