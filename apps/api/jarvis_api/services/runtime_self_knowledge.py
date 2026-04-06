"""Runtime self-knowledge — a bounded map of what Jarvis can do, what
influences him, what is gated, and what is structurally given.

This service reads from existing runtime surfaces and composes a single
self-knowledge map.  It does not create new state — it reads and classifies
what already exists.

Categories:
1. active_capabilities — things Jarvis can actively use right now
2. approval_gated — things that exist but require user/approval
3. passive_inner_forces — things that influence Jarvis but are not tools
4. structural_constraints — things that are part of his nature/boundaries
5. unavailable_or_inactive — things in the system but currently off

Design constraints:
- Read-only composition from existing surfaces
- No canonical identity mutation
- No fake consciousness claims
- Bounded output suitable for prompt inclusion
"""
from __future__ import annotations

from core.identity.workspace_bootstrap import workspace_memory_paths

from apps.api.jarvis_api.services.runtime_surface_cache import runtime_surface_cache


def build_runtime_self_knowledge_map(
    *, heartbeat_state: dict[str, object] | None = None
) -> dict[str, object]:
    """Build a bounded self-knowledge map from existing runtime surfaces.

    Returns a dict with five categories and a compact prompt-ready summary.
    """
    with runtime_surface_cache():
        active = _build_active_capabilities(heartbeat_state=heartbeat_state)
        gated = _build_approval_gated()
        inner = _build_passive_inner_forces()
        constraints = _build_structural_constraints()
        inactive = _build_unavailable_or_inactive()

    # Compact prompt-ready summary
    summary_parts = []
    if active["items"]:
        summary_parts.append(f"{len(active['items'])} active capabilities")
    if gated["items"]:
        summary_parts.append(f"{len(gated['items'])} approval-gated")
    if inner["items"]:
        summary_parts.append(f"{len(inner['items'])} passive inner forces")
    if inactive["items"]:
        summary_parts.append(f"{len(inactive['items'])} currently unavailable")

    return {
        "active_capabilities": active,
        "approval_gated": gated,
        "passive_inner_forces": inner,
        "structural_constraints": constraints,
        "unavailable_or_inactive": inactive,
        "summary": {
            "overview": " | ".join(summary_parts) if summary_parts else "No runtime self-knowledge available.",
            "active_count": len(active["items"]),
            "gated_count": len(gated["items"]),
            "inner_force_count": len(inner["items"]),
            "constraint_count": len(constraints["items"]),
            "inactive_count": len(inactive["items"]),
        },
    }


# ---------------------------------------------------------------------------
# Category builders
# ---------------------------------------------------------------------------


def _build_active_capabilities(
    *, heartbeat_state: dict[str, object] | None = None
) -> dict[str, object]:
    """Things Jarvis can actively use right now."""
    items: list[dict[str, str]] = []

    # Visible lane
    try:
        from apps.api.jarvis_api.services.visible_model import visible_execution_readiness
        vis = visible_execution_readiness()
        status = str(vis.get("provider_status") or "unknown")
        items.append({
            "id": "visible-chat-lane",
            "label": "Visible chat lane",
            "status": status,
            "mutability": "usable",
            "detail": f"provider={vis.get('provider')} model={vis.get('model')}",
        })
    except Exception:
        pass

    # Heartbeat
    try:
        hb_state = heartbeat_state or {}
        if not hb_state:
            from core.runtime.db import get_heartbeat_runtime_state
            hb_state = get_heartbeat_runtime_state() or {}
        enabled = bool(hb_state.get("enabled"))
        items.append({
            "id": "heartbeat-runtime",
            "label": "Heartbeat runtime",
            "status": "enabled" if enabled else "disabled",
            "mutability": "usable",
            "detail": f"schedule={hb_state.get('schedule_state', 'unknown')}",
        })
    except Exception:
        pass

    # Private brain / distillation
    try:
        from apps.api.jarvis_api.services.session_distillation import build_private_brain_context
        brain = build_private_brain_context(limit=4)
        if brain.get("active"):
            items.append({
                "id": "private-brain-continuity",
                "label": "Private brain continuity motor",
                "status": "active",
                "mutability": "usable",
                "detail": f"{brain.get('record_count', 0)} active records",
            })
    except Exception:
        pass

    # Session distillation
    items.append({
        "id": "session-distillation",
        "label": "Session distillation",
        "status": "active",
        "mutability": "usable",
        "detail": "Runs at visible run completion",
    })

    items.append({
        "id": "runtime-task-ledger",
        "label": "Runtime task ledger",
        "status": "active",
        "mutability": "usable",
        "detail": "Durable work units persist across turns and triggers",
    })

    items.append({
        "id": "runtime-flow-ledger",
        "label": "Runtime flow ledger",
        "status": "active",
        "mutability": "usable",
        "detail": "Multi-step work can continue instead of restarting from chat",
    })

    items.append({
        "id": "runtime-hook-bridge",
        "label": "Runtime hook bridge",
        "status": "active",
        "mutability": "usable",
        "detail": "Spontaneous events can create or resume bounded work",
    })

    items.append({
        "id": "layered-memory",
        "label": "Layered memory system",
        "status": "active",
        "mutability": "usable",
        "detail": "Daily and curated memory layers are both available",
    })

    try:
        from apps.api.jarvis_api.services.runtime_browser_body import list_browser_bodies

        bodies = list_browser_bodies(limit=1)
        status = str((bodies[0] if bodies else {}).get("status") or "idle")
        items.append({
            "id": "browser-body",
            "label": "Browser body",
            "status": status,
            "mutability": "usable",
            "detail": "Bounded browser state can be carried as an active runtime organ",
        })
    except Exception:
        pass

    # Cheap lane
    try:
        from apps.api.jarvis_api.services.non_visible_lane_execution import cheap_lane_execution_truth
        cheap = cheap_lane_execution_truth()
        if cheap.get("can_execute"):
            items.append({
                "id": "cheap-lane",
                "label": "Cheap model lane (internal jobs)",
                "status": "ready",
                "mutability": "usable",
                "detail": "For runtime-internal small tasks",
            })
    except Exception:
        pass

    # Local lane
    try:
        from apps.api.jarvis_api.services.non_visible_lane_execution import local_lane_execution_truth
        local = local_lane_execution_truth()
        if local.get("can_execute"):
            items.append({
                "id": "local-lane",
                "label": "Local model lane",
                "status": "ready",
                "mutability": "usable",
                "detail": f"provider_status={local.get('provider_status', 'unknown')}",
            })
    except Exception:
        pass

    return {"items": items, "label": "Active capabilities — things I can use right now"}


def _build_approval_gated() -> dict[str, object]:
    """Things that exist but require user approval."""
    items: list[dict[str, str]] = []

    # Workspace capabilities requiring approval
    try:
        from core.tools.workspace_capabilities import load_workspace_capabilities
        caps = load_workspace_capabilities()
        for cap in caps.get("runtime_capabilities", []):
            if str(cap.get("runtime_status") or "") == "approval-required":
                items.append({
                    "id": f"capability:{cap.get('capability_id', 'unknown')}",
                    "label": str(cap.get("name") or cap.get("capability_id") or "unnamed"),
                    "status": "approval-required",
                    "mutability": "approval-gated",
                    "detail": "Requires user approval before use",
                })
    except Exception:
        pass

    # SOUL.md / IDENTITY.md mutation
    items.append({
        "id": "soul-identity-mutation",
        "label": "SOUL.md / IDENTITY.md canonical writes",
        "status": "approval-required",
        "mutability": "approval-gated",
        "detail": "Proposals can be made but only applied with user approval",
    })

    # Runtime contract candidates
    try:
        from core.runtime.db import runtime_contract_candidate_counts
        counts = runtime_contract_candidate_counts()
        proposed = sum(v for k, v in counts.items() if k.endswith(":proposed"))
        if proposed > 0:
            items.append({
                "id": "pending-contract-candidates",
                "label": f"{proposed} pending contract candidate(s)",
                "status": "awaiting-review",
                "mutability": "approval-gated",
                "detail": "Runtime proposals awaiting user review",
            })
    except Exception:
        pass

    return {"items": items, "label": "Approval-gated — exists but requires permission"}


def _build_passive_inner_forces() -> dict[str, object]:
    """Things that influence Jarvis but are not directly actionable tools."""
    items: list[dict[str, str]] = []

    # Private brain carry
    try:
        from apps.api.jarvis_api.services.session_distillation import build_private_brain_context
        brain = build_private_brain_context(limit=4)
        if brain.get("active"):
            for excerpt in (brain.get("excerpts") or [])[:3]:
                items.append({
                    "id": f"brain-carry:{excerpt.get('type', 'unknown')}",
                    "label": f"Inner carry: {excerpt.get('focus', 'unnamed')[:40]}",
                    "status": "active",
                    "mutability": "influential-not-mutable",
                    "detail": str(excerpt.get("summary", ""))[:80],
                })
    except Exception:
        pass

    # Open loops
    try:
        from apps.api.jarvis_api.services.open_loop_signal_tracking import build_runtime_open_loop_signal_surface
        loops = build_runtime_open_loop_signal_surface(limit=4)
        for item in (loops.get("items") or [])[:2]:
            status = str(item.get("status") or "")
            if status in {"active", "softening"}:
                items.append({
                    "id": f"open-loop:{item.get('signal_id', 'unknown')[:16]}",
                    "label": f"Open loop: {item.get('title', 'unnamed')[:40]}",
                    "status": status,
                    "mutability": "influential-not-mutable",
                    "detail": str(item.get("summary", ""))[:80],
                })
    except Exception:
        pass

    # Initiative tension
    try:
        from apps.api.jarvis_api.services.private_initiative_tension_signal_tracking import build_runtime_private_initiative_tension_signal_surface
        tension = build_runtime_private_initiative_tension_signal_surface(limit=2)
        if tension.get("active"):
            intensity = str((tension.get("summary") or {}).get("current_intensity") or "low")
            items.append({
                "id": "initiative-tension",
                "label": "Initiative tension",
                "status": f"active ({intensity})",
                "mutability": "influential-not-mutable",
                "detail": "Inner pull toward proactive engagement",
            })
    except Exception:
        pass

    # Autonomy pressure
    try:
        from apps.api.jarvis_api.services.autonomy_pressure_signal_tracking import build_runtime_autonomy_pressure_signal_surface
        pressure = build_runtime_autonomy_pressure_signal_surface(limit=2)
        if pressure.get("active"):
            items.append({
                "id": "autonomy-pressure",
                "label": "Autonomy pressure",
                "status": "active",
                "mutability": "influential-not-mutable",
                "detail": "Bounded proactive readiness pressure",
            })
    except Exception:
        pass

    # Regulation / homeostasis
    try:
        from apps.api.jarvis_api.services.regulation_homeostasis_signal_tracking import build_runtime_regulation_homeostasis_signal_surface
        reg = build_runtime_regulation_homeostasis_signal_surface(limit=2)
        if reg.get("active"):
            items.append({
                "id": "regulation-homeostasis",
                "label": "Regulation / homeostasis",
                "status": "active",
                "mutability": "influential-not-mutable",
                "detail": "Internal balance and self-regulation state",
            })
    except Exception:
        pass

    # Question gates
    try:
        from apps.api.jarvis_api.services.proactive_question_gate_tracking import build_runtime_proactive_question_gate_surface
        gates = build_runtime_proactive_question_gate_surface(limit=2)
        if gates.get("active"):
            items.append({
                "id": "question-gates",
                "label": "Proactive question gates",
                "status": "active",
                "mutability": "influential-not-mutable",
                "detail": "Bounded question-capable readiness (not execution permission)",
            })
    except Exception:
        pass

    return {"items": items, "label": "Passive inner forces — influences me but not directly mutable"}


def _build_structural_constraints() -> dict[str, object]:
    """Things that are part of Jarvis' nature and boundaries."""
    items: list[dict[str, str]] = [
        {
            "id": "runtime-truth-outranks",
            "label": "Runtime truth outranks speculation",
            "status": "structural",
            "mutability": "not-mutable",
            "detail": "Observable runtime state always outranks inferred or guessed state",
        },
        {
            "id": "no-hidden-execution",
            "label": "No hidden execution",
            "status": "structural",
            "mutability": "not-mutable",
            "detail": "All actions are observable and bounded — no hidden side-effects",
        },
        {
            "id": "multi-entry-bounded-runtime",
            "label": "Multi-entry bounded runtime",
            "status": "structural",
            "mutability": "not-mutable",
            "detail": "Work can start from chat, heartbeat, hooks, and flows, but always stays bounded by runtime policy",
        },
        {
            "id": "no-free-identity-writes",
            "label": "No free canonical identity writes",
            "status": "structural",
            "mutability": "not-mutable",
            "detail": "SOUL.md / IDENTITY.md changes require user approval",
        },
        {
            "id": "question-gated-not-execution",
            "label": "Question-gated ≠ execution-granted",
            "status": "structural",
            "mutability": "not-mutable",
            "detail": "Proactive readiness is not permission to act",
        },
        {
            "id": "workspace-memory-separation",
            "label": "Workspace memory ≠ private mind",
            "status": "structural",
            "mutability": "not-mutable",
            "detail": "MEMORY.md is workspace/project memory, not inner private state",
        },
        {
            "id": "layered-memory-distinction",
            "label": "Layered memory ≠ single file",
            "status": "structural",
            "mutability": "not-mutable",
            "detail": "Daily memory, curated memory, and private carry are different memory layers with different roles",
        },
        {
            "id": "private-brain-is-private",
            "label": "Private brain is private",
            "status": "structural",
            "mutability": "not-mutable",
            "detail": "Private brain records are inner carry, not shared output",
        },
        {
            "id": "standing-orders-authority",
            "label": "Standing orders carry durable authority",
            "status": "structural",
            "mutability": "not-mutable",
            "detail": "STANDING_ORDERS.md is canonical runtime authority across turns, not a disposable note",
        },
        {
            "id": "tasks-not-flows",
            "label": "Tasks are not flows",
            "status": "structural",
            "mutability": "not-mutable",
            "detail": "Tasks are durable work units; flows are the stepwise path those tasks travel",
        },
        {
            "id": "browser-body-is-bounded",
            "label": "Browser body is bounded",
            "status": "structural",
            "mutability": "not-mutable",
            "detail": "A browser body is an operative runtime surface, not unrestricted omnipresence or free web action",
        },
    ]

    return {"items": items, "label": "Structural constraints — part of my nature and boundaries"}


def _build_unavailable_or_inactive() -> dict[str, object]:
    """Things in the system that are currently not active."""
    items: list[dict[str, str]] = []

    # Coding lane
    try:
        from apps.api.jarvis_api.services.non_visible_lane_execution import coding_lane_execution_truth
        coding = coding_lane_execution_truth()
        if not coding.get("can_execute"):
            items.append({
                "id": "coding-lane",
                "label": "Coding lane",
                "status": "unavailable",
                "mutability": "not-currently-available",
                "detail": f"status={coding.get('status', 'unknown')}",
            })
    except Exception:
        pass

    # Capabilities that are unavailable
    try:
        from core.tools.workspace_capabilities import load_workspace_capabilities
        caps = load_workspace_capabilities()
        for cap in caps.get("runtime_capabilities", []):
            if str(cap.get("runtime_status") or "") == "unavailable":
                items.append({
                    "id": f"capability-inactive:{cap.get('capability_id', 'unknown')}",
                    "label": str(cap.get("name") or cap.get("capability_id") or "unnamed"),
                    "status": "unavailable",
                    "mutability": "not-currently-available",
                    "detail": "Defined but not currently usable",
                })
    except Exception:
        pass

    # Webchat execution pilot (if not active)
    try:
        from apps.api.jarvis_api.services.tiny_webchat_execution_pilot import build_runtime_webchat_execution_pilot_surface
        pilot = build_runtime_webchat_execution_pilot_surface(limit=1)
        if not pilot.get("active"):
            items.append({
                "id": "webchat-execution-pilot",
                "label": "Webchat proactive execution pilot",
                "status": "inactive",
                "mutability": "not-currently-available",
                "detail": "Tiny bounded execution pilot — currently not active",
            })
    except Exception:
        pass

    return {"items": items, "label": "Unavailable or inactive — exists but currently off"}


# ---------------------------------------------------------------------------
# Compact prompt-ready section
# ---------------------------------------------------------------------------


def build_self_knowledge_prompt_section() -> str | None:
    """Build a compact self-knowledge section suitable for prompt inclusion.

    Returns None if nothing meaningful to include.
    Max ~600 chars to avoid prompt bloat.
    """
    knowledge = build_runtime_self_knowledge_map()
    active = knowledge["active_capabilities"]["items"]
    inner = knowledge["passive_inner_forces"]["items"]
    gated = knowledge["approval_gated"]["items"]

    if not active and not inner:
        return None

    lines = ["Runtime self-knowledge (bounded agency map):"]

    # Active capabilities — compact
    if active:
        cap_labels = [item["label"] for item in active[:4]]
        lines.append(f"- I can use: {', '.join(cap_labels)}")

    # Gated items — compact
    if gated:
        gated_labels = [item["label"] for item in gated[:2]]
        lines.append(f"- Approval-gated: {', '.join(gated_labels)}")

    runtime_organs = [
        item["label"]
        for item in active
        if item["id"] in {
            "runtime-task-ledger",
            "runtime-flow-ledger",
            "runtime-hook-bridge",
            "browser-body",
            "layered-memory",
        }
    ]
    if runtime_organs:
        lines.append(f"- Runtime organs: {', '.join(runtime_organs[:4])}")

    # Inner forces — compact
    if inner:
        inner_labels = [f"{item['label']} ({item['status']})" for item in inner[:3]]
        lines.append(f"- Inner forces: {', '.join(inner_labels)}")

    # Key constraints — always include a few
    paths = workspace_memory_paths()
    lines.append(
        "- Structural: runtime truth outranks speculation | standing orders are durable authority | tasks != flows | "
        f"layered_memory={paths['daily_dir'].name}+{paths['curated_memory'].name}"
    )

    return "\n".join(lines)
