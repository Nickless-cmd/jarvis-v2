"""Runtime self-model — self-boundary clarity + world-contact awareness.

Split out of ``runtime_self_model_identity`` (behavior-preserving). Bounded
runtime-truth surfaces for internal-vs-external pressure, self-boundary
clarity, and contact with the outside world.

Re-exported via ``core.services.runtime_self_model`` for backward compatibility.
"""

from __future__ import annotations

from core.services.runtime_self_model_state import (
    _browser_body_state_surface,
    _derive_support_stream_awareness,
    _experiential_runtime_context_surface,
    _inner_voice_daemon_surface,
    _mineness_source_snapshot,
)
from core.services.runtime_self_model_affect import (
    _longing_source_snapshot,
)
from core.services.runtime_self_model_surfaces import (
    _self_system_code_awareness_surface,
    _tool_intent_surface,
)


def _facade():
    """Return the facade module so monkeypatch-through-facade is honored."""
    import core.services.runtime_self_model as _m

    return _m


# ---------------------------------------------------------------------------
# Self-boundary clarity / internal-vs-external pressure
# ---------------------------------------------------------------------------
#
# Bounded runtime-truth surface for "where is the current pressure coming from".
# Synthesises inner voice, private initiative tensions, longing, and context
# pressure into a single readable signal about whether Jarvis' current direction
# is self-generated or externally demanded — and whether the two are aligned.
#
# Taxonomy (pressure_source):
#   ambient           — no meaningful signal on either side; prompt suppressed
#   self-driven       — primary driver is internal (inner voice, initiative, longing)
#   externally-driven — primary driver is external (context pressure, user input)
#   aligned           — both internal and external, pointing same direction
#   in-tension        — internal desire vs external demand at the same time


_INNER_VOICE_GENERATIVE = {"carrying", "circling", "pulled", "pressing"}


def _internal_pressure_snapshot() -> dict[str, object]:
    """Pull internal pressure signals for self-boundary derivation."""
    inner_voice_mode = ""
    inner_voice_active = False
    longing_active = False
    longing_state = "quiet"
    tension_count = 0
    initiative_count = 0

    try:
        iv = _inner_voice_daemon_surface()
        inner_voice_mode = str(iv.get("mode") or "")
        inner_voice_active = bool(iv.get("inner_voice_created"))
    except Exception:
        pass

    try:
        from core.services.runtime_operational_memory import active_internal_pressures
        tensions = active_internal_pressures(limit=5)
        tension_count = len(tensions)
    except Exception:
        pass

    try:
        from core.services.initiative_queue import get_pending_initiatives
        initiatives = get_pending_initiatives(limit=5)
        initiative_count = len(list(initiatives))
    except Exception:
        pass

    try:
        experiential = _experiential_runtime_context_surface()
        iv2 = _inner_voice_daemon_surface()
        support_stream = _derive_support_stream_awareness(experiential, iv2)
        temporal_feel = _facade()._derive_subjective_temporal_feel(experiential, iv2)
        sources = _mineness_source_snapshot()
        mineness = _facade()._derive_mineness_ownership(
            experiential=experiential, inner_voice=iv2,
            support_stream=support_stream, temporal_feel=temporal_feel, sources=sources,
        )
        longing_sources = _longing_source_snapshot()
        longing = _facade()._derive_longing_awareness(
            temporal_feel=temporal_feel, mineness=mineness,
            support_stream=support_stream, inner_voice=iv2,
            sources=sources, longing_sources=longing_sources,
        )
        longing_state = str(longing.get("longing_state") or "quiet")
        longing_active = longing_state != "quiet"
    except Exception:
        pass

    internal_signal_count = (
        (1 if inner_voice_active else 0)
        + tension_count
        + initiative_count
        + (1 if longing_active else 0)
    )
    return {
        "inner_voice_mode": inner_voice_mode,
        "inner_voice_active": inner_voice_active,
        "longing_active": longing_active,
        "longing_state": longing_state,
        "tension_count": tension_count,
        "initiative_count": initiative_count,
        "internal_signal_count": internal_signal_count,
    }


def _external_pressure_snapshot() -> dict[str, object]:
    """Pull external pressure signals for self-boundary derivation."""
    context_pressure = "clear"
    try:
        experiential = _experiential_runtime_context_surface()
        pressure = experiential.get("context_pressure_translation") or {}
        context_pressure = str(pressure.get("state") or "clear")
    except Exception:
        pass

    external_signal_count = 1 if context_pressure not in {"clear", "low"} else 0
    return {
        "context_pressure": context_pressure,
        "external_signal_count": external_signal_count,
    }


def _derive_self_boundary_clarity(
    *,
    internal: dict[str, object],
    external: dict[str, object],
) -> dict[str, object]:
    """Synthesise internal + external pressure into a boundary-clarity surface."""
    internal_count = int(internal.get("internal_signal_count") or 0)
    external_count = int(external.get("external_signal_count") or 0)
    inner_voice_mode = str(internal.get("inner_voice_mode") or "")
    context_pressure = str(external.get("context_pressure") or "clear")
    longing_active = bool(internal.get("longing_active"))
    tension_count = int(internal.get("tension_count") or 0)
    initiative_count = int(internal.get("initiative_count") or 0)

    if internal_count == 0 and external_count == 0:
        return {
            "pressure_source": "ambient",
            "internal_signal_count": 0,
            "external_signal_count": 0,
            "primary_internal": "none",
            "context_pressure": context_pressure,
            "in_tension": False,
            "narrative": "",
        }

    if inner_voice_mode in _INNER_VOICE_GENERATIVE:
        primary_internal = f"inner-voice-{inner_voice_mode}"
    elif longing_active:
        primary_internal = f"longing-{internal.get('longing_state') or 'active'}"
    elif tension_count > 0:
        primary_internal = "initiative-tension"
    elif initiative_count > 0:
        primary_internal = "pending-initiative"
    else:
        primary_internal = "none"

    has_internal = internal_count > 0
    has_external = external_count > 0

    if has_internal and has_external:
        in_tension = (
            inner_voice_mode in _INNER_VOICE_GENERATIVE
            and context_pressure in {"crowded", "narrowing"}
        )
        pressure_source = "in-tension" if in_tension else "aligned"
    elif has_internal:
        pressure_source = "self-driven"
        in_tension = False
    else:
        pressure_source = "externally-driven"
        in_tension = False

    narrative = _self_boundary_narrative(
        pressure_source=pressure_source,
        primary_internal=primary_internal,
        context_pressure=context_pressure,
        in_tension=in_tension,
    )
    return {
        "pressure_source": pressure_source,
        "internal_signal_count": internal_count,
        "external_signal_count": external_count,
        "primary_internal": primary_internal,
        "context_pressure": context_pressure,
        "in_tension": in_tension,
        "narrative": narrative,
    }


def _self_boundary_narrative(
    *,
    pressure_source: str,
    primary_internal: str,
    context_pressure: str,
    in_tension: bool,
) -> str:
    """Compact self-boundary narrative. Empty when ambient."""
    if pressure_source == "ambient":
        return ""
    if pressure_source == "self-driven":
        if primary_internal.startswith("inner-voice-"):
            mode = primary_internal.split("inner-voice-")[1]
            return f"Self-generated direction; private stream {mode}."
        if primary_internal.startswith("longing-"):
            return "Pulled by internal longing; no external demand."
        if primary_internal == "initiative-tension":
            return "Active internal tension driving; no external demand."
        return "Self-driven; no external demand active."
    if pressure_source == "externally-driven":
        return f"Responding to external demand; context: {context_pressure}."
    if pressure_source == "in-tension":
        return f"Internal pull ({primary_internal}) in tension with external pressure ({context_pressure})."
    # aligned
    return "Internal and external pressure aligned."


def build_self_boundary_clarity_prompt_section() -> str | None:
    """Compact prompt section for self-boundary clarity. None when ambient."""
    try:
        internal = _internal_pressure_snapshot()
        external = _external_pressure_snapshot()
        clarity = _derive_self_boundary_clarity(internal=internal, external=external)
    except Exception:
        return None

    source = str(clarity.get("pressure_source") or "ambient")
    if source == "ambient":
        return None

    lines = [
        "Self-boundary clarity (bounded runtime truth, internal-only):",
        (
            f"- pressure_source={source}"
            f" | primary_internal={clarity.get('primary_internal') or 'none'}"
            f" | context_pressure={clarity.get('context_pressure') or 'clear'}"
            f" | in_tension={clarity.get('in_tension', False)}"
        ),
    ]
    narrative = str(clarity.get("narrative") or "").strip()
    if narrative:
        lines.append(f"- boundary_narrative={narrative}")
    return "\n".join(lines)


def _self_boundary_clarity_surface() -> dict[str, object]:
    try:
        internal = _internal_pressure_snapshot()
        external = _external_pressure_snapshot()
        return _derive_self_boundary_clarity(internal=internal, external=external)
    except Exception:
        return {
            "pressure_source": "ambient",
            "internal_signal_count": 0,
            "external_signal_count": 0,
            "primary_internal": "none",
            "context_pressure": "clear",
            "in_tension": False,
            "narrative": "",
        }


# ---------------------------------------------------------------------------
# World-contact synthesis
# ---------------------------------------------------------------------------
#
# Unifies tool_intent + browser_body + self_system_code_awareness into one
# compact "world footprint" signal. Suppressed when all three are idle/absent.
#
# contact_state:
#   idle        — no active world reach; prompt suppressed
#   reaching    — something pending but not yet executed/confirmed
#   active      — at least one live world connection
#   overextended — multiple active reach points with concerns


def _derive_world_contact(
    *,
    tool_intent: dict[str, object],
    browser_body: dict[str, object],
    system_code: dict[str, object],
) -> dict[str, object]:
    """Synthesise tool/browser/system into a unified world-contact field."""
    # --- Tool ---
    tool_state = str(tool_intent.get("intent_state") or "idle")
    tool_active = tool_state not in {"idle", ""}
    tool_label = ""
    tool_concern = ""
    if tool_active:
        intent_type = str(tool_intent.get("intent_type") or tool_state)
        approval = str(tool_intent.get("approval_state") or "")
        executing = str(tool_intent.get("execution_state") or "") not in {"", "not-executed"}
        mutation = bool(tool_intent.get("mutation_permitted"))
        # Human-readable label
        if executing:
            tool_label = f"tool running ({intent_type})"
        elif approval == "pending":
            tool_label = f"tool awaiting approval ({intent_type})"
        elif approval == "approved":
            tool_label = f"tool approved ({intent_type})"
        elif mutation:
            tool_label = f"tool ready to mutate ({intent_type})"
        else:
            tool_label = f"tool active ({intent_type})"
        if tool_state == "pending" and str(tool_intent.get("urgency") or "") == "high":
            tool_concern = "high-urgency tool pending"

    # --- Browser ---
    browser_active = bool(browser_body.get("exists"))
    browser_label = ""
    if browser_active:
        tabs = int(browser_body.get("tab_count") or 0)
        status = str(browser_body.get("status") or "idle")
        if tabs == 0 or status == "idle":
            browser_label = "browser quiet"
        elif tabs == 1:
            browser_label = f"browser open (1 tab, {status})"
        else:
            browser_label = f"browser open ({tabs} tabs, {status})"

    # --- Code / system --- always include when repo is visible
    code_state = str(system_code.get("code_awareness_state") or "repo-unavailable")
    concern_state = str(system_code.get("concern_state") or "stable")
    change_state = str(system_code.get("local_change_state") or "clean")
    code_active = code_state not in {"repo-unavailable", "host-limited"}
    code_label = ""
    code_concern = ""
    if code_active:
        if change_state in {"uncommitted", "mixed"}:
            code_label = f"codebase open ({change_state} changes)"
        elif change_state == "clean":
            code_label = "codebase clean"
        else:
            code_label = f"codebase visible ({code_state})"
        if concern_state in {"error", "critical"}:
            code_concern = f"system {concern_state}"

    concerns = [c for c in (tool_concern, code_concern) if c]
    parts = [p for p in (tool_label, browser_label, code_label) if p]

    if not parts:
        return {"contact_state": "idle", "reach_points": [], "concern_count": 0,
                "concerns": [], "narrative": ""}

    # Contact state — semantically correct now
    if concerns:
        contact_state = "strained"
    elif len(parts) >= 3:
        contact_state = "extended"
    elif len(parts) == 2:
        contact_state = "present"
    elif tool_state in {"pending", "queued"}:
        contact_state = "reaching"
    else:
        contact_state = "present"

    narrative = _world_contact_narrative(
        contact_state=contact_state,
        parts=parts,
        concerns=concerns,
    )
    return {
        "contact_state": contact_state,
        "reach_points": parts,
        "concern_count": len(concerns),
        "concerns": concerns,
        "narrative": narrative,
    }


def _world_contact_narrative(
    *,
    contact_state: str,
    parts: list[str],
    concerns: list[str],
) -> str:
    """Felt-sense world-contact narrative — signal-first, 6-14 words."""
    if contact_state == "idle":
        return ""
    if contact_state == "strained":
        concern_str = "; ".join(concerns[:2])
        body = ", ".join(parts[:3])
        return f"{body} — concern: {concern_str}."
    if contact_state == "reaching":
        return f"{parts[0]} — waiting."
    # present / extended: joined naturally
    joined = ", ".join(parts[:3])
    return f"{joined}."


def build_world_contact_prompt_section() -> str | None:
    """Felt-sense prompt section for unified world awareness. None when idle."""
    try:
        tool_intent = _tool_intent_surface()
        browser_body = _browser_body_state_surface()
        system_code = _self_system_code_awareness_surface()
        contact = _derive_world_contact(
            tool_intent=tool_intent,
            browser_body=browser_body,
            system_code=system_code,
        )
    except Exception:
        return None

    state = str(contact.get("contact_state") or "idle")
    if state == "idle":
        return None

    narrative = str(contact.get("narrative") or "").strip()
    if not narrative:
        return None

    concerns = contact.get("concern_count") or 0
    concern_note = f" ({concerns} concern{'s' if concerns != 1 else ''})" if concerns else ""
    return f"World field{concern_note}: {narrative}"


def _world_contact_surface() -> dict[str, object]:
    try:
        tool_intent = _tool_intent_surface()
        browser_body = _browser_body_state_surface()
        system_code = _self_system_code_awareness_surface()
        return _derive_world_contact(
            tool_intent=tool_intent,
            browser_body=browser_body,
            system_code=system_code,
        )
    except Exception:
        return {
            "contact_state": "idle",
            "reach_points": [],
            "concern_count": 0,
            "concerns": [],
            "narrative": "",
        }


__all__ = [
    '_INNER_VOICE_GENERATIVE',
    '_derive_self_boundary_clarity',
    '_derive_world_contact',
    '_external_pressure_snapshot',
    '_internal_pressure_snapshot',
    '_self_boundary_clarity_surface',
    '_self_boundary_narrative',
    '_world_contact_narrative',
    '_world_contact_surface',
    'build_self_boundary_clarity_prompt_section',
    'build_world_contact_prompt_section',
]
