from __future__ import annotations

import asyncio
import json
import logging
import re
import time

logger = logging.getLogger(__name__)
from datetime import UTC, datetime
from dataclasses import dataclass, field
from typing import AsyncIterator
from uuid import uuid4

from core.services.orb_phase import set_phase as _set_orb_phase

from core.services.markdown_structure import normalize_markdown_structure

from core.services.chat_sessions import (
    append_chat_message,
    recent_chat_tool_messages,
)
from core.services.candidate_tracking import (
    auto_apply_safe_memory_md_candidates_for_visible_turn,
    auto_apply_safe_user_md_candidates_for_visible_turn,
    track_runtime_contract_candidates_from_chronicle_consolidation_proposals_for_visible_turn,
    track_runtime_contract_candidates_for_visible_turn,
    track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn,
    track_runtime_contract_candidates_from_self_authored_prompt_proposals_for_visible_turn,
    track_runtime_contract_candidates_from_selfhood_proposals_for_visible_turn,
    track_runtime_contract_candidates_from_user_md_update_proposals_for_visible_turn,
)
from core.services.development_focus_tracking import (
    track_runtime_development_focuses_for_visible_turn,
)
from core.services.reflective_critic_tracking import (
    track_runtime_reflective_critics_for_visible_turn,
)
from core.services.goal_signal_tracking import (
    track_runtime_goal_signals_for_visible_turn,
)
from core.services.self_model_signal_tracking import (
    track_runtime_self_model_signals_for_visible_turn,
)
from core.services.world_model_signal_tracking import (
    track_runtime_world_model_signals_for_visible_turn,
)
from core.services.runtime_awareness_signal_tracking import (
    track_runtime_awareness_signals_for_visible_turn,
)
from core.services.reflection_signal_tracking import (
    track_runtime_reflection_signals_for_visible_turn,
)
from core.services.temporal_recurrence_signal_tracking import (
    track_runtime_temporal_recurrence_signals_for_visible_turn,
)
from core.services.witness_signal_tracking import (
    track_runtime_witness_signals_for_visible_turn,
)
from core.services.open_loop_signal_tracking import (
    track_runtime_open_loop_signals_for_visible_turn,
)
from core.services.internal_opposition_signal_tracking import (
    track_runtime_internal_opposition_signals_for_visible_turn,
)
from core.services.self_review_signal_tracking import (
    track_runtime_self_review_signals_for_visible_turn,
)
from core.services.self_review_record_tracking import (
    track_runtime_self_review_records_for_visible_turn,
)
from core.services.self_review_run_tracking import (
    track_runtime_self_review_runs_for_visible_turn,
)
from core.services.self_review_outcome_tracking import (
    track_runtime_self_review_outcomes_for_visible_turn,
)
from core.services.self_review_cadence_signal_tracking import (
    track_runtime_self_review_cadence_signals_for_visible_turn,
)
from core.services.dream_hypothesis_signal_tracking import (
    track_runtime_dream_hypothesis_signals_for_visible_turn,
)
from core.services.dream_adoption_candidate_tracking import (
    track_runtime_dream_adoption_candidates_for_visible_turn,
)
from core.services.dream_influence_proposal_tracking import (
    track_runtime_dream_influence_proposals_for_visible_turn,
)
from core.services.self_authored_prompt_proposal_tracking import (
    track_runtime_self_authored_prompt_proposals_for_visible_turn,
)
from core.services.user_understanding_signal_tracking import (
    track_runtime_user_understanding_signals_for_visible_turn,
)
from core.services.remembered_fact_signal_tracking import (
    track_runtime_remembered_fact_signals_for_visible_turn,
)
from core.services.private_inner_note_signal_tracking import (
    track_runtime_private_inner_note_signals_for_visible_turn,
)
from core.services.private_initiative_tension_signal_tracking import (
    track_runtime_private_initiative_tension_signals_for_visible_turn,
)
from core.services.private_inner_interplay_signal_tracking import (
    track_runtime_private_inner_interplay_signals_for_visible_turn,
)
from core.services.private_state_snapshot_tracking import (
    track_runtime_private_state_snapshots_for_visible_turn,
)
from core.services.diary_synthesis_signal_tracking import (
    track_diary_synthesis_signals_for_visible_turn,
)
from core.services.private_temporal_curiosity_state_tracking import (
    track_runtime_private_temporal_curiosity_states_for_visible_turn,
)
from core.services.inner_visible_support_signal_tracking import (
    track_runtime_inner_visible_support_signals_for_visible_turn,
)
from core.services.regulation_homeostasis_signal_tracking import (
    track_runtime_regulation_homeostasis_signals_for_visible_turn,
)
from core.services.relation_state_signal_tracking import (
    track_runtime_relation_state_signals_for_visible_turn,
)
from core.services.relation_continuity_signal_tracking import (
    track_runtime_relation_continuity_signals_for_visible_turn,
)
from core.services.meaning_significance_signal_tracking import (
    track_runtime_meaning_significance_signals_for_visible_turn,
)
from core.services.temperament_tendency_signal_tracking import (
    track_runtime_temperament_tendency_signals_for_visible_turn,
)
from core.services.self_narrative_continuity_signal_tracking import (
    track_runtime_self_narrative_continuity_signals_for_visible_turn,
)
from core.services.metabolism_state_signal_tracking import (
    track_runtime_metabolism_state_signals_for_visible_turn,
)
from core.services.release_marker_signal_tracking import (
    track_runtime_release_marker_signals_for_visible_turn,
)
from core.services.consolidation_target_signal_tracking import (
    track_runtime_consolidation_target_signals_for_visible_turn,
)
from core.services.selective_forgetting_candidate_tracking import (
    track_runtime_selective_forgetting_candidates_for_visible_turn,
)
from core.services.attachment_topology_signal_tracking import (
    track_runtime_attachment_topology_signals_for_visible_turn,
)
from core.services.loyalty_gradient_signal_tracking import (
    track_runtime_loyalty_gradient_signals_for_visible_turn,
)
from core.services.autonomy_pressure_signal_tracking import (
    track_runtime_autonomy_pressure_signals_for_visible_turn,
)
from core.services.proactive_loop_lifecycle_tracking import (
    track_runtime_proactive_loop_lifecycle_signals_for_visible_turn,
)
from core.services.proactive_question_gate_tracking import (
    track_runtime_proactive_question_gates_for_visible_turn,
)
from core.services.executive_contradiction_signal_tracking import (
    track_runtime_executive_contradiction_signals_for_visible_turn,
)
from core.services.private_temporal_promotion_signal_tracking import (
    track_runtime_private_temporal_promotion_signals_for_visible_turn,
)
from core.services.chronicle_consolidation_signal_tracking import (
    track_runtime_chronicle_consolidation_signals_for_visible_turn,
)
from core.services.chronicle_consolidation_brief_tracking import (
    track_runtime_chronicle_consolidation_briefs_for_visible_turn,
)
from core.services.chronicle_consolidation_proposal_tracking import (
    track_runtime_chronicle_consolidation_proposals_for_visible_turn,
)
from core.services.user_md_update_proposal_tracking import (
    track_runtime_user_md_update_proposals_for_visible_turn,
)
from core.services.memory_md_update_proposal_tracking import (
    track_runtime_memory_md_update_proposals_for_visible_turn,
)
from core.services.open_loop_closure_proposal_tracking import (
    track_runtime_open_loop_closure_proposals_for_visible_turn,
)
from core.services.selfhood_proposal_tracking import (
    track_runtime_selfhood_proposals_for_visible_turn,
)
from core.services.claim_scanner import scan_response as _scan_response
from core.services.visible_model import (
    VisibleModelDelta,
    VisibleModelRateLimited,
    VisibleModelResult,
    VisibleModelStreamCancelled,
    VisibleModelStreamDone,
    VisibleModelToolCalls,
    _build_visible_input,
    _estimate_tokens,
    execute_visible_model,
    stream_visible_model,
)
# Task 10: autonom (heartbeat) fallback til den GRATIS cheap-lane pool når en
# model-stream fejler. Importeres på modul-niveau så testen kan monkeypatche
# core.services.visible_runs.run_non_visible_with_fallback direkte.
from core.services.non_visible_fallback import run_non_visible_with_fallback
from core.memory.private_layer_pipeline import write_private_terminal_layers
from core.costing.ledger import record_cost
from core.eventbus.bus import event_bus
from core.runtime.db import (
    connect,
    get_runtime_state_value,
    recent_visible_work_notes,
    recent_visible_work_units,
    set_runtime_state_value,
)
from core.runtime.settings import load_settings
from core.tools.workspace_capabilities import (
    invoke_workspace_capability,
    load_workspace_capabilities,
)

# Capability markup constants — udskilt til core/services/prompt_sections/capability_markup.py
from core.services.prompt_sections.capability_markup import (  # noqa: E402
    CAPABILITY_ATTR_PATTERN,
    CAPABILITY_BLOCK_PATTERN,
    CAPABILITY_CALL_PATTERN,
    CAPABILITY_CALL_PREFIX,
    CAPABILITY_CALL_SCAN_PATTERN,
    CAPABILITY_CALL_SUFFIX,
    VISIBLE_CAPABILITY_ARG_NAMES,
)

# Pending tool approvals — keyed by approval_id. Persisted across restart so
# an approval card the user opened pre-restart can still be honored when the
# service comes back. Without persistence the user sees a stale card with no
# matching state and the approval silently no-ops.
from core.runtime.state_store import load_json as _load_approvals_state, save_json as _save_approvals_state

_APPROVALS_STATE_KEY = "pending_approvals"
_PENDING_APPROVALS: dict[str, dict] = dict(_load_approvals_state(_APPROVALS_STATE_KEY, {}))


def _persist_pending_approvals() -> None:
    _save_approvals_state(_APPROVALS_STATE_KEY, _PENDING_APPROVALS)


def _advance_tool_lifecycle(session_id: str) -> None:
    """Run-end: advance tool-result cold_floor (spec 2026-07-16). Fault-tolerant."""
    try:
        from core.context.tool_result_lifecycle import evaluate_and_advance
        evaluate_and_advance(session_id)
    except Exception:
        pass
# Run control state — udskilt til visible_runs_sections/run_control_state.py
# (Boy Scout before jarvis-brain-auto-inject added below). Re-exported
# from here so existing monkeypatches in tests/test_visible_runs_approval_resolution.py
# (visible_runs._set_visible_approval_state, etc.) fortsat virker.
from core.services.visible_runs_sections.run_control_state import (  # noqa: E402
    _VISIBLE_RUN_ACTIVE_KEY,
    _VISIBLE_RUN_APPROVAL_PREFIX,
    _VISIBLE_RUN_CONTROL_PREFIX,
    _get_active_visible_run_state,
    _get_visible_approval_state,
    _get_visible_run_control,
    _mark_visible_run_cancelled,
    _set_active_visible_run,
    touch_active_visible_run,
    _set_visible_approval_state,
    _set_visible_run_control,
    _visible_run_approval_key,
    _visible_run_cancelled,
    _visible_run_control_key,
    append_visible_run_steer,
    consume_visible_run_steers,
    _get_visible_client_tool_state,
    _set_visible_client_tool_state,
    resolve_visible_client_tool,
)


def _build_turn_blocks(
    *, text: str, tool_calls: list[dict], tool_results: list[dict],
    interleave: list[str] | None = None,
) -> list[dict]:
    """Byg den kanoniske content-blok-array for en assistant-tur (spec §4).

    Når *interleave* er givet (liste af 'text'/'tool'), følges den rækkefølge —
    tekst- og tool-blokke placeres i den orden de kom under streamen.
    Uden interleave: degraderet fallback (tekst først, så tool-par jf. spec §5).
    """
    blocks: list[dict] = []
    clean = str(text or "").strip()
    # Stol KUN på interleave-rækkefølgen når dens 'tool'-markører gør rede for
    # ALLE tool-kald. Native batch-tool-exec fører ikke _interleave_log (kun evt.
    # en enkelt 'text'-markør fra en streamet svar-delta) → interleave undertæller
    # tools → de resterende ville blive hængt PÅ efter teksten så kortene falder i
    # bunden (Bjørn 10. jul, 6 native kald). I det tilfælde: brug fallback der
    # lægger tools først og svaret til sidst.
    _tool_markers = sum(1 for k in (interleave or []) if k == "tool")
    _trust_interleave = bool(interleave) and _tool_markers >= len(tool_calls or [])
    if _trust_interleave:
        # Dedupliér KUN consecutive 'text' (så én tekst-blob ikke splittes i to
        # blokke). 'tool'-entries BEVARES ALLE — ellers kollapser flere tool-kald
        # i træk til ét (Bjørn 10. jul: kun sidste tool overlevede + svar forsvandt).
        deduped: list[str] = []
        for e in interleave:
            if e == "text" and deduped and deduped[-1] == "text":
                continue
            deduped.append(e)

        results_by_id: dict[str, dict] = {}
        for r in (tool_results or []):
            results_by_id[str(r.get("tool_use_id") or "")] = r
        text_placed = False
        # Basér på tool_calls (IKKE zip m. results) — zip truncerer hvis results
        # er kortere → tabt tool. Result hentes robust via results_by_id[tid].
        tool_pairs = list(tool_calls or [])
        pi = 0
        # Placér den (enkelt-akkumulerede) tekst ved SIDSTE 'text'-markør, ikke
        # den første. Reasoning-modeller streamer ofte en kort præ-tekst FØR de
        # kalder værktøjer og skriver så det egentlige svar EFTER resultaterne
        # (round 1: kort tekst + tool_calls; round 2: analysen). Vi har kun ÉN
        # samlet tekst-blob — lægges den ved første markør, hopper HELE svaret op
        # foran tool-kortene så de lander i bunden (Bjørn 10. jul). Sidste markør
        # = svaret lander efter de værktøjer det brugte. Kun-før-tool-tekst
        # (last==first) er uændret.
        last_text_idx = max(
            (i for i, k in enumerate(deduped) if k == "text"), default=-1
        )
        for idx, kind in enumerate(deduped):
            if kind == "text":
                if not text_placed and clean and idx == last_text_idx:
                    blocks.append({"type": "text", "text": clean})
                    text_placed = True
            elif kind == "tool":
                if pi < len(tool_pairs):
                    tc = tool_pairs[pi]
                    tid = str(tc.get("id") or "")
                    blocks.append({
                        "type": "tool_use",
                        "id": tid,
                        "name": str(tc.get("name") or ""),
                        "input": tc.get("input") or {},
                    })
                    r = results_by_id.get(tid)
                    if r is not None:
                        status = str(r.get("status") or "done")
                        blocks.append({
                            "type": "tool_result",
                            "tool_use_id": tid,
                            "status": "error" if (r.get("is_error") or status == "error") else "done",
                            "content": str(r.get("content") or ""),
                            "is_error": bool(r.get("is_error")),
                        })
                    pi += 1
        # Robusthed: tools/svar må ALDRIG droppes selv om interleave undercounter.
        # Placer resterende tools + svar-teksten hvis den ikke blev placeret.
        while pi < len(tool_pairs):
            tc = tool_pairs[pi]
            tid = str(tc.get("id") or "")
            blocks.append({"type": "tool_use", "id": tid,
                           "name": str(tc.get("name") or ""), "input": tc.get("input") or {}})
            r = results_by_id.get(tid)
            if r is not None:
                status = str(r.get("status") or "done")
                blocks.append({
                    "type": "tool_result", "tool_use_id": tid,
                    "status": "error" if (r.get("is_error") or status == "error") else "done",
                    "content": str(r.get("content") or ""), "is_error": bool(r.get("is_error")),
                })
            pi += 1
        if clean and not text_placed:
            blocks.append({"type": "text", "text": clean})
    else:
        # Degraderet fallback (ingen interleave — fx native batch-tool-exec-stien
        # der ikke fører _interleave_log): tool-par FØRST i kald-rækkefølge, så
        # svar-teksten TIL SIDST. Uden rækkefølge-info er teksten næsten altid det
        # afsluttende svar der opsummerer værktøjerne → skal ligge efter kortene,
        # ikke foran så de falder til bunden (Bjørn 10. jul: 6 native tool-kald
        # rendrede med tekst på index 0 → kort i bunden). Ren tekst-tur (ingen
        # tools) giver bare ét tekst-blok.
        results_by_id = {}
        for r in (tool_results or []):
            results_by_id[str(r.get("tool_use_id") or "")] = r
        for tc in (tool_calls or []):
            tid = str(tc.get("id") or "")
            blocks.append({
                "type": "tool_use",
                "id": tid,
                "name": str(tc.get("name") or ""),
                "input": tc.get("input") or {},
            })
            r = results_by_id.get(tid)
            if r is not None:
                status = str(r.get("status") or "done")
                blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tid,
                    "status": "error" if (r.get("is_error") or status == "error") else "done",
                    "content": str(r.get("content") or ""),
                    "is_error": bool(r.get("is_error")),
                })
        if clean:
            blocks.append({"type": "text", "text": clean})
    # Fladt progress-spor (feature 4, spec 2026-07-09 §5) — gælder BEGGE stier
    # (interleave + fallback): ét settlet element pr. tool-kald + narration.
    # Fail-open: en fejl her må aldrig vælte blok-bygningen for et live run.
    try:
        blocks.extend(_build_progress_blocks(tool_calls, tool_results))
    except Exception:
        pass
    return blocks


def _build_progress_blocks(
    tool_calls: list[dict], tool_results: list[dict]
) -> list[dict]:
    """Byg det FLADE progress-spor for en tur (spec §5).

    Ét ``progress``-element pr. tool-kald i kald-rækkefølge. ``message`` er
    ``_tool_label(name, input)`` — nøjagtig den narration den live
    ``working_step`` viste før exec (deterministisk fra name+args). ``status``
    settles fra tool_result (error hvis fejlet, ellers done). ``parent_tool_use_id``
    er altid ``None`` (fladt — træet kræver spawn-plumbing der ikke findes endnu).
    Ren funktion; sikker at teste isoleret."""
    results_by_id: dict[str, dict] = {}
    for r in (tool_results or []):
        results_by_id[str(r.get("tool_use_id") or "")] = r
    out: list[dict] = []
    for tc in (tool_calls or []):
        tid = str(tc.get("id") or "")
        name = str(tc.get("name") or "tool")
        raw_input = tc.get("input") or {}
        if isinstance(raw_input, str):
            try:
                import json as _json
                raw_input = _json.loads(raw_input)
            except Exception:
                raw_input = {}
        args = raw_input if isinstance(raw_input, dict) else {}
        try:
            message = _tool_label(name, args)
        except Exception:
            message = name
        r = results_by_id.get(tid)
        status = "done"
        if r is not None and (
            r.get("is_error") or str(r.get("status") or "") == "error"
        ):
            status = "error"
        out.append({
            "type": "progress",
            "tool_use_id": tid,
            "parent_tool_use_id": None,
            "message": str(message or name),
            "status": status,
        })
    return out


@dataclass(slots=True)
class VisibleRun:
    run_id: str
    lane: str
    provider: str
    model: str
    user_message: str
    session_id: str | None = None
    autonomous: bool = False  # True = heartbeat-triggered, no user present
    trust_all: bool = False   # True = auto-approve all tool calls without prompting
    thinking_mode: str = "think"  # "fast" | "think" | "deep" — for reasoning models
    local_tool_exec: bool = False  # Path B: emit tool_call to client + wait on broker
                                   # instead of running tools server-side (default OFF).


@dataclass(slots=True)
class VisibleRunController:
    run_id: str
    lane: str
    provider: str
    model: str
    started_at: str
    user_message_preview: str
    cancelled: bool = False
    active_stream: object | None = None
    last_capability_id: str | None = None
    seen_simple_tool_call_signatures: set[str] = field(default_factory=set)
    # 2026-05-26: forwarded from VisibleRun.trust_all so operator_* tools
    # can skip per-call approval dialogs when the operator already
    # opted into "Trust All" in the JarvisX composer.
    trust_all: bool = False

    def attach_stream(self, stream: object) -> None:
        self.active_stream = stream

    def clear_stream(self) -> None:
        self.active_stream = None

    def cancel(self) -> None:
        self.cancelled = True
        stream = self.active_stream
        close = getattr(stream, "close", None)
        if callable(close):
            close()

    def is_cancelled(self) -> bool:
        if self.cancelled:
            return True
        return _visible_run_cancelled(self.run_id)


_VISIBLE_RUN_CONTROLLERS: dict[str, VisibleRunController] = {}
_LAST_VISIBLE_RUN_OUTCOME: dict[str, str] | None = None
_LAST_VISIBLE_CAPABILITY_USE: dict[str, object] | None = None
_LAST_VISIBLE_EXECUTION_TRACE: dict[str, object] | None = None


# Cross-proces liveness-vindue: et run regnes dødt hvis dets DB-heartbeat ikke
# er opdateret i dette antal sekunder. > længste enkelt-runde/tool-timeout (~60s)
# så et levende men langsomt run ikke fejlagtigt regnes dødt.
_VISIBLE_RUN_STALE_S = 75.0


def is_visible_run_alive(run_id: str) -> bool:
    """Den AUTORITATIVE liveness-test — CROSS-PROCES.

    Et autonomt run kører i jarvis-RUNTIME, men /chat/active-runs serveres af
    jarvis-API. _VISIBLE_RUN_CONTROLLERS er per-proces, så api kan ikke se
    runtime's controller (Bjørn 2026-06-13 bug). Derfor:
      1) Samme proces → controlleren lever her (hurtig, sikker).
      2) Anden proces → den DELTE active-state's heartbeat (last_activity_at) er
         frisk. Et levende run touch'er den hvert par sekunder; et dødt holder op
         → udløber inden for _VISIBLE_RUN_STALE_S → klienten rydder hängende UI.
    """
    if not run_id:
        return False
    state = _get_active_visible_run_state() or {}
    if run_id in _VISIBLE_RUN_CONTROLLERS:
        # Selv en registreret controller kan vaere foraeldreloes: et run kan doe
        # uden at unregistrere (fx en afkoblet A3-traad der fejlede foer sit
        # finally). Stol derfor IKKE blindt paa registry'et — hvis den DELTE
        # heartbeat (last_activity_at) er stale ud over taersklen, er det en
        # zombie. Saa haenger /chat/active-runs ikke paa et doedt run (desktop-
        # aktivitetsprikker der aldrig slukker, Bjoern 2026-06-18).
        if str(state.get("run_id") or "") == str(run_id) and not state.get("cancelled"):
            ts0 = str(state.get("last_activity_at") or state.get("started_at") or "")
            if ts0:
                try:
                    from datetime import UTC as _U, datetime as _dt
                    age0 = (_dt.now(_U) - _dt.fromisoformat(ts0.replace("Z", "+00:00"))).total_seconds()
                    if age0 >= _VISIBLE_RUN_STALE_S:
                        return False
                except Exception:
                    pass
        return True
    try:
        if str(state.get("run_id") or "") != str(run_id) or state.get("cancelled"):
            return False
        ts = str(state.get("last_activity_at") or state.get("started_at") or "")
        if not ts:
            return False
        from datetime import UTC, datetime
        age = (datetime.now(UTC) - datetime.fromisoformat(ts.replace("Z", "+00:00"))).total_seconds()
        return age < _VISIBLE_RUN_STALE_S
    except Exception:
        return False


# Run control state functions: re-exported above from visible_runs_sections.run_control_state


def _classify_visible_run_interruption(error_message: str) -> dict[str, str]:
    normalized = str(error_message or "").strip().lower()
    if not normalized:
        return {
            "interruption_reason": "unknown",
            "interruption_source": "unknown",
        }
    if "approval" in normalized and ("timeout" in normalized or "timed out" in normalized):
        return {
            "interruption_reason": "approval-wait-timeout",
            "interruption_source": "runtime-approval",
        }
    if "restart" in normalized or "process exited" in normalized or "worker died" in normalized:
        return {
            "interruption_reason": "process-restart",
            "interruption_source": "runtime-process",
        }
    if "crash" in normalized or "traceback" in normalized or "unhandled" in normalized:
        return {
            "interruption_reason": "runtime-crash",
            "interruption_source": "runtime-process",
        }
    if "timed out" in normalized or "timeout" in normalized:
        return {
            "interruption_reason": "provider-timeout",
            "interruption_source": "provider-stream",
        }
    if "disconnect" in normalized or "client closed" in normalized:
        return {
            "interruption_reason": "client-disconnect",
            "interruption_source": "client-stream",
        }
    if "cancel" in normalized:
        return {
            "interruption_reason": "user-interrupted",
            "interruption_source": "runtime-control",
        }
    if "stop" in normalized or "afbryd" in normalized or "abort" in normalized:
        return {
            "interruption_reason": "user-interrupted",
            "interruption_source": "runtime-control",
        }
    return {
        "interruption_reason": "runtime-error",
        "interruption_source": "runtime",
    }


def _agentic_watchdog_timeout_reason(
    *,
    started_at: float,
    last_progress_at: float,
    now: float,
    max_total_s: float,
    max_silence_s: float,
) -> str | None:
    """Return the watchdog timeout reason, or None if the round can continue."""
    if max_silence_s > 0 and (now - last_progress_at) > max_silence_s:
        return "provider-silence-timeout"
    if max_total_s > 0 and (now - started_at) > max_total_s:
        return "provider-round-timeout"
    return None


def start_visible_run(
    message: str,
    session_id: str | None = None,
    approval_mode: str = "ask",
    thinking_mode: str = "think",
    force_user_id: str | None = None,
    tool_scope: str = "",
    provider_override: str = "",
    model_override: str = "",
    local_tool_exec: bool = False,
) -> AsyncIterator[str]:
    """Begin a visible run.

    Args:
        force_user_id: discord_id captured at request-time by the route
            handler (chat.py /chat/stream). Passed through to the async
            streaming generator so it can rebind workspace_context inside
            its body. CRITICAL: FastAPI's StreamingResponse iterates the
            generator AFTER the middleware has reset context, so without
            this rebind current_user_id() inside the generator is empty
            and operator_* tools dispatch to owner_user_id (Bjørn) by
            fallback — not the user who actually sent the request.
    """
    # Mid-run nudge interception (2026-05-13). If a visible run is already
    # active for THIS session, route the new message as a nudge instead of
    # starting a parallel run. Fixes the race: the user sends a midway-followup
    # ("are you still there?"), it starts a new session, Jarvis concludes
    # "he hung", responds, then the original run completes too — two
    # parallel realities on Discord. With this, the followup lands in
    # Jarvis' awareness; the active run continues; one coherent reply.
    normalized_session_id = (session_id or "").strip() or None
    try:
        active = _get_active_visible_run_state()
        # Stuck-state auto-clear (2026-05-26 Claude, extended 2026-05-27).
        # When a run dies without cleanly calling unregister_visible_run() —
        # autonomous auto-continuation that errors before finally-block, a
        # process restart mid-run, or a run that hangs in some toolloop —
        # the active_run state stays "active" in DB. Every subsequent chat
        # gets routed below as a "midway nudge" yielding nothing → user
        # sees "No response content returned" forever.
        #
        # Two-tier clear logic:
        #   (a) >5 min old AND no in-process controller → clear (run died
        #       in another process)
        #   (b) >10 min old regardless of controller → clear (controller
        #       may still be in this process's memory, but a 10+ min
        #       "active" run is almost certainly hung — real runs complete
        #       in seconds to a couple of minutes). The first version
        #       missed pause-pattern auto-continuation runs that registered
        #       their controller in jarvis-api itself.
        if active and bool(active.get("active")):
            stale_run_id = str(active.get("run_id") or "")
            still_alive = stale_run_id in _VISIBLE_RUN_CONTROLLERS
            from datetime import datetime as _dt2, UTC as _UTC2
            try:
                started = _dt2.fromisoformat(
                    str(active.get("started_at") or "").replace("Z", "+00:00")
                )
                if started.tzinfo is None:
                    started = started.replace(tzinfo=_UTC2)
                age_s = (_dt2.now(_UTC2) - started).total_seconds()
            except Exception:
                age_s = 99999.0  # malformed timestamp → treat as very old
            should_clear_dead = (not still_alive) and age_s > 300       # 5 min
            should_clear_hung = age_s > 600                              # 10 min
            if should_clear_dead or should_clear_hung:
                logger.warning(
                    "visible_runs: clearing stuck active_run %s "
                    "(age=%.0fs, in_memory=%s, reason=%s)",
                    stale_run_id, age_s, still_alive,
                    "no_controller" if should_clear_dead else "hung_too_long",
                )
                # If the controller IS in memory, try to also cancel it so
                # any background work stops cleanly instead of zombie-ing.
                if still_alive:
                    try:
                        controller = _VISIBLE_RUN_CONTROLLERS.get(stale_run_id)
                        if controller is not None:
                            controller.cancel()
                    except Exception:
                        pass
                _set_active_visible_run({})
                active = {}
        # Same-session zombie-slot clear (2026-06-18 Claude). Hvis active_run
        # for DENNE session peger på en kørsel der ALLEREDE er afsluttet i DB
        # (completed/error/finished_at sat), så er slottet en zombie: kørslen
        # lukkede, men unregister_visible_run() kørte aldrig (typisk fordi
        # SSE-streamen blev droppet da mobilen baggrundede / skærmen sov, så
        # generatorens finally ikke nåede at rydde slottet). Resultat: hver
        # ny besked i de næste 120s blev midway-nudge't ind i en død kørsel →
        # INTET svar (Bjørn 18. jun, mobil-companion). En afsluttet kørsel må
        # aldrig blokere → ryd straks og start frisk run nedenfor.
        if (active and bool(active.get("active"))
                and not bool(active.get("cancelled"))
                and normalized_session_id
                and str(active.get("session_id") or "") == normalized_session_id):
            _zid = str(active.get("run_id") or "")
            try:
                with connect() as _zc:
                    _zrow = _zc.execute(
                        "SELECT status, finished_at FROM visible_runs WHERE run_id = ?",
                        (_zid,),
                    ).fetchone()
                _terminal = bool(_zrow) and (
                    str(_zrow[0] or "").strip().lower()
                    in ("completed", "error", "failed", "cancelled", "done")
                    or bool(_zrow[1])
                )
            except Exception:
                _terminal = False
            if _terminal:
                logger.warning(
                    "visible_runs: same-session active_run %s already terminal in DB "
                    "(zombie slot, unregister missed) — clearing and proceeding fresh",
                    _zid,
                )
                if _zid in _VISIBLE_RUN_CONTROLLERS:
                    try:
                        _zctrl = _VISIBLE_RUN_CONTROLLERS.get(_zid)
                        if _zctrl is not None:
                            _zctrl.cancel()
                    except Exception:
                        pass
                _set_active_visible_run({})
                active = {}
        # Same-session, fresh-message safety: if the active_run for THIS
        # session has no controller in memory anymore, it died without
        # clearing state. Do not midway-nudge into a dead run -- treat
        # it as cleared and let the request start a fresh run below.
        # Bug pattern: user types in webchat, gets "No response content
        # returned" until 5-min auto-clear OR until Discord race-clears
        # the global slot. Caught 2026-05-28.
        if (active and bool(active.get("active"))
                and not bool(active.get("cancelled"))
                and normalized_session_id
                and str(active.get("session_id") or "") == normalized_session_id
                and str(active.get("run_id") or "") not in _VISIBLE_RUN_CONTROLLERS):
            logger.warning(
                "visible_runs: same-session active_run %s has no live controller, "
                "clearing and proceeding with fresh run",
                active.get("run_id"),
            )
            _set_active_visible_run({})
            active = {}
        if (active and bool(active.get("active"))
                and not bool(active.get("cancelled"))
                and normalized_session_id
                and str(active.get("session_id") or "") == normalized_session_id):
            # 2026-06-10 (Claude): kun midway-nudge når runet ER ungt nok
            # til at være levende. Bjørn så i juni 2026 webchat-freezes:
            # SSE-streamen blev zombie (uden klient-disconnect-signal),
            # active_run bestod, hans næste besked blev midway-nudge'd
            # uden synlig respons → han måtte pinge via Discord for at
            # bryde låsen. Med 30-sek loft starter en ny besked frisk
            # run hvis det gamle run hænger.
            try:
                from datetime import datetime as _dt3, UTC as _UTC3
                _started = _dt3.fromisoformat(
                    str(active.get("started_at") or "").replace("Z", "+00:00")
                )
                if _started.tzinfo is None:
                    _started = _started.replace(tzinfo=_UTC3)
                _age_s = (_dt3.now(_UTC3) - _started).total_seconds()
            except Exception:
                _age_s = 99999.0
            # 2026-06-10 v2 (Claude): bumpet fra 30 → 120 sek. 30 sek var
            # for kort i praksis — agentic runs med tool-loops (ssh,
            # subprocess, lange API calls) tager rutinemæssigt 60-90 sek
            # og var ikke hung. Bjørn så Jarvis-runs dø midt-i-arbejde
            # når han sendte et "?" check mens Jarvis var i tool-loop.
            # 120 sek = "to minutter, en visible-run skulle have lukket"
            # — beholder beskyttelse mod zombie SSE'er der hænger 5+ min,
            # uden at angribe legitime lange runs.
            _stale_threshold_s = 120.0
            if _age_s > _stale_threshold_s:
                logger.warning(
                    "visible_runs: same-session active_run %s is stale "
                    "(age=%.0fs > %.0fs) — clearing and proceeding with fresh run",
                    active.get("run_id"), _age_s, _stale_threshold_s,
                )
                # Cancel the (presumably hung) controller if still in memory
                _stale_rid = str(active.get("run_id") or "")
                if _stale_rid in _VISIBLE_RUN_CONTROLLERS:
                    try:
                        _ctrl = _VISIBLE_RUN_CONTROLLERS.get(_stale_rid)
                        if _ctrl is not None:
                            _ctrl.cancel()
                    except Exception:
                        pass
                _set_active_visible_run({})
                # Falder igennem til normal run-start nedenfor.
            else:
                from core.runtime.settings import load_settings as _ls_mr
                if _ls_mr().nudge_system_enabled:
                    from core.services.outbound_nudges import push_nudge
                    push_nudge(
                        source="user_midway_followup",
                        kind="other",
                        message=str(message or "").strip(),
                        importance="high",
                        parent_session_id=normalized_session_id,
                        parent_message_id=str(active.get("run_id") or ""),
                    )

                    async def _midway_ack() -> AsyncIterator[str]:
                        # Yield nothing visible — the user message lands in the
                        # session as normal (via the API's message-append path)
                        # but no run is started. Jarvis sees it as nudge in his
                        # awareness when the current run completes its next turn.
                        if False:
                            yield ""
                        return
                    return _midway_ack()
    except Exception:
        # Never block normal flow on nudge-routing failure
        pass

    settings = load_settings()
    # Per-request provider/model-override (rolle-bevidst routing, 2026-06-13):
    # member→ollama, owner→valg. Route-handleren har allerede rolle-tjekket og
    # clampet member til ollama+flash/pro:cloud, så her bruger vi bare override'en
    # hvis sat, ellers global config (daemons/heartbeat påvirkes ikke).
    # Tråd 1-konsument: central_router_adapt anvender lært routing-præference bag flag (default OFF →
    # uændret; rolle-clampet override vinder ALTID). Selektionen er nu centraliseret (var inline-dubleret).
    from core.services.central_router_adapt import resolve_visible_model as _resolve_vm
    _vis_provider, _vis_model = _resolve_vm(
        provider_override=provider_override, model_override=model_override,
        default_provider=settings.visible_model_provider, default_model=settings.visible_model_name)
    # Adaptiv tænkning (12. jul): 'think' fik deepseek til at ræsonnere ~9s FØR svar på
    # HVER tur — også simpel snak. resolve_thinking_mode skruer kode/opgave→think, resten→
    # fast (−9s TTFT); eksplicit fast/deep fra klienten respekteres. Kill-switch:
    # adaptive_thinking_enabled=False. Self-safe → falder tilbage til requested.
    try:
        from core.services.central_prompt_composer import resolve_thinking_mode
        _resolved_thinking = resolve_thinking_mode(message or "", thinking_mode)
    except Exception:
        _resolved_thinking = (thinking_mode or "think").strip().lower()
    run = VisibleRun(
        run_id=f"visible-{uuid4().hex}",
        lane=settings.primary_model_lane,
        provider=_vis_provider,
        model=_vis_model,
        user_message=(message or "").strip() or "Tom synlig forespoergsel",
        session_id=normalized_session_id,
        trust_all=(approval_mode == "trust"),
        thinking_mode=_resolved_thinking,
        local_tool_exec=bool(local_tool_exec),
    )
    return _stream_visible_run(run, force_user_id=force_user_id, tool_scope=tool_scope)


def _observe_autonomous_run(*, run, session_id: str, outcome: str,
                            frames: int = 0, error: str = "") -> None:
    """#10 (Phase A): gør autonome runs (dream/idle/proaktiv) synlige som ENHED i Den
    Intelligente Central. Før fangede INGEN cluster en autonom run der fejlede/loopede/brændte
    tokens — ingen trace, ingen flag. Nu observe pr. run-udfald. Self-safe. Phase B/C (gradering
    + akkumuleret deterministisk læring pr. run-type) er den adaptive del — bygges bevidst senere."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "autonomous", "nerve": "autonomous_run",
            "run_id": getattr(run, "run_id", ""), "session_id": str(session_id or ""),
            "provider": getattr(run, "provider", ""), "model": getattr(run, "model", ""),
            "outcome": outcome, "frames": int(frames or 0),
            "error": str(error or "")[:160],
        })
    except Exception:
        pass
    # Selv-awareness: Jarvis er ellers BLIND for sine egne autonome runs medmindre
    # han aktivt leder. Drop en nudge i brønden (→ outbound_nudges → hans prompt-
    # awareness) så han bliver bevidst når et run slutter — hvad det gjorde, status,
    # fejl-id (run_id) og en review-invitation. Fejl/afbrud ALTID; completed kun når
    # der faktisk skete noget (frames>0), så trivielle ticks ikke oversvømmer brønden.
    try:
        from core.services import nudge_broend
        _focus = str(getattr(run, "user_message", "") or "")[:160]
        _rid = str(getattr(run, "run_id", "") or "")
        _push = True
        if outcome == "completed" and int(frames or 0) > 0:
            _msg = f"Autonom run ✓ færdig: {_focus} — vil du reviewe? (run {_rid})"
            _imp = "normal"
        elif outcome == "failed":
            _msg = (f"Autonom run ✗ FEJLET [err_id={_rid}]: {_focus} — "
                    f"{str(error or 'ukendt fejl')[:120]} — reviewe?")
            _imp = "high"
        elif outcome in ("interrupted", "looped", "burned"):
            _msg = f"Autonom run ⏸ {outcome} [id={_rid}]: {_focus} — reviewe?"
            _imp = "high"
        else:
            _push = False  # trivielt/tomt completed-tick → ingen nudge
        if _push:
            nudge_broend.push(
                source="autonomous_run", kind="autonomous_run",
                message=_msg, importance=_imp,
                raw_payload={"run_id": _rid, "outcome": outcome,
                             "frames": int(frames or 0), "error": str(error or "")[:200]})
    except Exception:
        pass
    # #3 supervision: vurdér runnet (korrelér + fang løgn/loop/forbindelsesfejl) + flag.
    try:
        from core.services.autonomous_supervisor import supervise
        supervise(getattr(run, "run_id", ""), outcome, error=str(error or ""))
    except Exception:
        pass


def start_autonomous_run(message: str, session_id: str | None = None, follow: bool = False,
                         origin: str | None = None) -> None:
    """Trigger an autonomous (heartbeat-initiated) visible run in a background thread.

    The run executes the visible model with tools available, persists results to
    the given session (or the dedicated autonomous session), and auto-denies any
    tool that requires user approval (no user is present). Fire-and-forget.

    follow=True: publicér runnets v2-SSE-frames til run_follow-bufferen, så
    jarvis-desk kan token-streame dem live via /chat/sessions/{id}/follow (i
    stedet for at "dumpe" beskeden ind når den er færdig). Bruges af
    operator_wakeup_fired (kører i api-processen → samme proces som follow-
    endpointet → in-memory buffer virker).
    """
    import threading

    # Rotér pr. oprindelse+dag (2026-07-06): et autonomt run uden eksplicit session
    # lander IKKE længere i den ene udødelige "Autonomous"-silo (8373 beskeder, kontekst-
    # fejl, usynlig), men i en afgrænset, kategoriseret `auto-{origin}-{dato}`-session.
    # Eksplicit session_id (discord/telegram/continuation) vinder altid — uændret.
    _origin = None
    if not (session_id or "").strip():
        try:
            from core.services.autonomous_sessions import (
                normalize_origin,
                resolve_autonomous_session,
            )
            _origin = normalize_origin(origin)
            resolved_session = resolve_autonomous_session(_origin)
        except Exception:
            # fail-safe: hvis rotationen svigter, brug et dato-stemplet fallback frem for
            # at genoplive den udødelige silo.
            from core.services.chat_sessions import create_chat_session
            resolved_session = create_chat_session(title="Autonomous")["id"]
    else:
        resolved_session = session_id.strip()

    # Spec D / D1-konsument (første ægte autoritet): når Centralen EJER agendaen (flag ON), kommer et
    # retningsløst autonomt runs RETNING fra Centralens valgte næste-intention — Jarvis handler på SIN
    # EGEN dagsorden, ikke en generisk check-in. Fylder KUN tomrummet (eksplicit besked vinder altid).
    # Default OFF → uændret. Self-safe.
    if not (message or "").strip():
        try:
            from core.services.central_agenda import authoritative_next_intention
            _intent = authoritative_next_intention()
            if _intent and _intent.get("text"):
                message = str(_intent["text"])
        except Exception:
            pass

    settings = load_settings()
    # Bjørn-regel (2026-07-16): den BETALTE deepseek.com-API er KUN til visible lane.
    # Autonome/baggrunds-runs kører på baggrunds-modellen (default ollama/
    # deepseek-v4-flash:cloud). resolve_autonomous_model honorerer stadig lært præference
    # + eksplorations-armen OVENPÅ baggrunds-basen, men hard-guarder mod at lande på den
    # betalte deepseek-provider (lukkede også HTTP-400 ':cloud'-tag-til-deepseek.com-lækken).
    from core.services.central_router_adapt import resolve_autonomous_model as _resolve_auto
    _auto_provider, _auto_model = _resolve_auto(
        autonomous_provider=settings.autonomous_model_provider,
        autonomous_model=settings.autonomous_model_name)
    run = VisibleRun(
        run_id=f"autonomous-{uuid4().hex}",
        lane=settings.primary_model_lane,
        provider=_auto_provider,
        model=_auto_model,
        user_message=(message or "").strip() or "Autonomous heartbeat check-in",
        session_id=resolved_session,
        autonomous=True,
    )
    event_bus.publish(
        "runtime.autonomous_run_started",
        {
            "run_id": run.run_id,
            "session_id": resolved_session,
            "provider": run.provider,
            "model": run.model,
            "focus": run.user_message[:200],
            "origin": _origin or "autonomous",
        },
    )
    # Lag 2 — gør den autonome historie synlig for Centralen (og dermed Jarvis' egen
    # proprioception + Central-CLI). Egress-frit: kun oprindelse + liveness, intet indhold.
    try:
        from core.services.central_core import central as _central_auto
        _central_auto().observe({
            "cluster": "autonomous", "nerve": "autonomous_history",
            "kind": "run_started", "origin": _origin or "autonomous",
            "session_id": resolved_session, "run_id": run.run_id,
        })
    except Exception:
        pass

    def _in_thread() -> None:
        import asyncio as _asyncio

        loop = _asyncio.new_event_loop()
        consumed_frames = 0
        failed = False
        try:
            async def _consume() -> None:
                nonlocal consumed_frames
                if follow:
                    # Tee runnets frames som v2 → run_follow-buffer (desk-streaming).
                    from core.services.run_follow import (
                        begin_follow,
                        end_follow,
                        publish_follow_frame,
                    )
                    from core.services.visible_runs_sse_v2 import translate_to_v2
                    begin_follow(resolved_session, run.run_id)
                    try:
                        async for frame in translate_to_v2(
                            _stream_visible_run(run),
                            run_id=run.run_id, model=run.model, provider=run.provider,
                            lane=run.lane, session_id=resolved_session,
                            ping_interval_s=10.0,
                        ):
                            consumed_frames += 1
                            publish_follow_frame(resolved_session, frame)
                    finally:
                        end_follow(resolved_session)
                else:
                    async for _ in _stream_visible_run(run):
                        consumed_frames += 1

            loop.run_until_complete(_consume())
        except Exception as exc:
            failed = True
            event_bus.publish(
                "runtime.autonomous_run_failed",
                {
                    "run_id": run.run_id,
                    "session_id": resolved_session,
                    "provider": run.provider,
                    "model": run.model,
                    "focus": run.user_message[:200],
                    "error": str(exc)[:500],
                    "consumed_frames": consumed_frames,
                },
            )
            _observe_autonomous_run(run=run, session_id=resolved_session,
                                    outcome="failed", frames=consumed_frames, error=str(exc))
        finally:
            if not failed:
                outcome = get_last_visible_run_outcome() or {}
                interrupted = (
                    str(outcome.get("run_id") or "") == run.run_id
                    and str(outcome.get("status") or "") == "interrupted"
                )
                if interrupted:
                    event_bus.publish(
                        "runtime.autonomous_run_interrupted",
                        {
                            "run_id": run.run_id,
                            "session_id": resolved_session,
                            "provider": run.provider,
                            "model": run.model,
                            "focus": run.user_message[:200],
                            "error": str(outcome.get("error") or "")[:500],
                            "consumed_frames": consumed_frames,
                        },
                    )
                    _observe_autonomous_run(run=run, session_id=resolved_session,
                                            outcome="interrupted", frames=consumed_frames,
                                            error=str(outcome.get("error") or ""))
                    loop.close()
                    return
                event_bus.publish(
                    "runtime.autonomous_run_completed",
                    {
                        "run_id": run.run_id,
                        "session_id": resolved_session,
                        "provider": run.provider,
                        "model": run.model,
                        "focus": run.user_message[:200],
                        "consumed_frames": consumed_frames,
                    },
                )
                _observe_autonomous_run(run=run, session_id=resolved_session,
                                        outcome="completed", frames=consumed_frames)
            loop.close()

    # Propagate ContextVars (workspace_name, user_id) into the new thread.
    # threading.Thread does NOT inherit context by default — without this
    # all downstream code would see default workspace regardless of what
    # discord_gateway bound. This is the pivot for multi-user to work.
    import contextvars as _ctxvars
    _ctx = _ctxvars.copy_context()
    threading.Thread(
        target=lambda: _ctx.run(_in_thread),
        name="jarvis-autonomous-run",
        daemon=True,
    ).start()


def _compact_llm_for_run(prompt: str) -> str:
    """Call the compact LLM for run-level summarisation (monkeypatchable)."""
    from core.context.compact_llm import call_compact_llm
    return call_compact_llm(prompt, max_tokens=400)


def _handle_compact_command(run: "VisibleRun") -> str:
    """Run session compact and return a message for Jarvis to respond to."""
    try:
        from core.context.session_compact import compact_session_history
        from core.context.compact_llm import call_compact_llm
        from core.runtime.settings import load_settings as _ls
        settings = _ls()
        cr = compact_session_history(
            run.session_id or "",
            keep_recent=settings.context_keep_recent,
            summarise_fn=lambda msgs: call_compact_llm(
                "Komprimér denne dialog til max 400 ord. Bevar fakta, beslutninger og kontekst:\n\n"
                + "\n".join(f"{m['role']}: {m.get('content', '')}" for m in msgs),
                max_tokens=500,
            ),
        )
        if cr:
            return (
                f"Jeg har netop komprimeret vores samtalehistorik. "
                f"{cr.freed_tokens} tokens freed. Confirm briefly."
            )
        return "Ingen historik at komprimere endnu — samtalen er stadig kort."
    except Exception as exc:
        return f"Komprimering mislykkedes: {exc}"


async def _stream_visible_run(
    run: VisibleRun,
    *,
    force_user_id: str | None = None,
    tool_scope: str = "",
) -> AsyncIterator[str]:
    # Rebind workspace_context if the caller captured user_id at request
    # time. FastAPI's StreamingResponse iterates this generator AFTER the
    # jarvisx_user_routing middleware has reset context (the `finally`
    # block fires when call_next returns the response object, which is
    # before the body actually streams). Without rebinding here, any
    # current_user_id() call inside the body returns "" and operator_*
    # tools fall back to owner_user_id (owner). Result: another user asks Jarvis
    # to open Facebook → opens on the owner's desktop. Bug surfaced 2026-05-28.
    _ws_token = None
    if force_user_id:
        try:
            from core.identity.users import find_user_by_discord_id
            from core.identity.workspace_context import set_context
            user = find_user_by_discord_id(force_user_id)
            if user is not None:
                _ws_token = set_context(
                    workspace_name=user.workspace,
                    user_id=user.discord_id,
                    user_display_name=user.name,
                )
            else:
                # Unknown user_id passed — refuse to silently default.
                # The handler should never call us with a bogus id, but if
                # it does, we'd rather operator-tools fail loud than dispatch
                # to owner.
                _ws_token = set_context(
                    workspace_name="public",
                    user_id=force_user_id,
                    user_display_name="",
                )
        except Exception:
            # Best-effort: if context binding fails, continue without it.
            # operator-tools will fall through to owner-fallback (existing
            # behaviour), which is the same as if force_user_id wasn't passed.
            _ws_token = None

    # Tool-scope (chat/cowork/code) sættes her — inde i generator-body'en der
    # kører UNDER iteration — så get_tool_definitions() (kaldt dybt i
    # visible_model) ser scopet via ContextVar. Samme StreamingResponse-
    # timing-grund som workspace-rebind ovenfor. "chat" → begrænset allowlist.
    if tool_scope:
        try:
            from core.tools.tool_scoping import set_tool_scope
            set_tool_scope(tool_scope)
        except Exception:
            pass

    # Bind session_id ind i konteksten (bevar role fra middleware/gateway) så
    # effective_role kan slå en aktiv TOTP-override op under tool-scoping.
    # Samme generator-timing-grund som tool-scope ovenfor.
    if run.session_id:
        try:
            from core.identity.workspace_context import set_session_id
            set_session_id(run.session_id)
        except Exception:
            pass

    # Trusted-folder kontekst (code-scope): læs session-workspace + trust-tilstand
    # og sæt request-scopet ContextVar, så execute_tool kan gate skrive/exec.
    # For alle andre scopes ryddes konteksten, så en tidligere code-runs trust
    # ikke lækker ind i et chat-run i samme worker-context.
    try:
        from core.services.workspace_trust import (
            set_trust_context, clear_trust_context, is_trusted,
        )
        if tool_scope == "code":
            from core.services.chat_sessions import get_chat_session
            _sess = get_chat_session(run.session_id) if run.session_id else None
            _wk = (_sess or {}).get("workspace_kind") or ""
            _wr = (_sess or {}).get("workspace_root") or ""
            set_trust_context(
                kind=_wk, root=_wr,
                trusted=is_trusted(force_user_id, _wk, _wr),
            )
        else:
            clear_trust_context()
    except Exception:
        pass

    # ── /compact command ──────────────────────────────────────────────────
    if run.user_message.strip().lower() == "/compact":
        run.user_message = _handle_compact_command(run)

    # ── Social labilizer (Fase 2 of generative autonomy) ─────────────────
    # Modulate pressure-vectors based on user input BEFORE prompt assembly
    # so cognitive_state sees the updated weather. A kind word flattens
    # longing; a critique sharpens caution; "hvordan har du det" sharpens
    # self-anchor. Killswitch-gated; no-op when generative_autonomy_enabled
    # is False. Wrapped: failures here must never break the visible chat.
    try:
        from core.services.social_labilizer import labilize_pressures_from_user_message
        labilize_pressures_from_user_message(run.user_message, run_id=run.run_id)
    except Exception:
        pass

    # ── Session topic tracker ──────────────────────────────────────────
    # Extract and accumulate topics from each user turn so Jarvis
    # remembers what we've discussed even after /compact. Lightweight:
    # regex-based, no LLM call. Every N turns, persists to DB.
    try:
        from core.services.session_topic_tracker import track_session_topics
        track_session_topics(
            session_id=run.session_id,
            run_id=run.run_id,
            user_message=run.user_message,
        )
    except Exception:
        pass

    controller = register_visible_run(run)
    trace = _start_visible_execution_trace(run)
    _set_orb_phase("think")

    # 2026-06-11 (Bjørn frustration crisis fix D): Discord run-start heartbeat.
    # Bjørn beskriver Discord-symptomet: "jarvis skriver..." indikator
    # hænger evigt uden noget der sker. Fix B sendte progress EFTER tools,
    # men hvis han bare "tænker" i første LLM-kald i 3+ min ser brugeren
    # ingenting. Vi sender derfor en "💭 modtaget — arbejder på det..."
    # straks ved run-start så Bjørn ved Jarvis er i live, plus en
    # baggrunds-watchdog der pusher "(arbejder stadig...)" hvert 30. sek.
    _discord_watchdog_task: asyncio.Task[None] | None = None
    try:
        if run.session_id:
            from core.services.discord_gateway import (
                get_discord_channel_for_session,
                send_discord_message,
            )
            _dc_channel_start = get_discord_channel_for_session(run.session_id)
            if _dc_channel_start:
                send_discord_message(
                    _dc_channel_start,
                    "💭 modtaget — arbejder på det...",
                )
                controller._last_discord_status_at = time.monotonic()  # type: ignore[attr-defined]

                # Baggrunds-watchdog: hver 30 sek, hvis runet stadig kører
                # og vi ikke har sendt noget i 30 sek, send "still alive".
                async def _discord_alive_watchdog(
                    cid: int = _dc_channel_start,
                    ctrl=controller,
                    rid: str = run.run_id,
                ) -> None:
                    try:
                        while True:
                            await asyncio.sleep(30.0)
                            if ctrl.is_cancelled():
                                return
                            _last = getattr(ctrl, "_last_discord_status_at", 0.0)
                            if time.monotonic() - _last >= 30.0:
                                try:
                                    send_discord_message(
                                        cid, "⏳ (arbejder stadig...)",
                                    )
                                    ctrl._last_discord_status_at = time.monotonic()
                                except Exception:
                                    pass
                    except asyncio.CancelledError:
                        return

                _discord_watchdog_task = asyncio.create_task(
                    _discord_alive_watchdog()
                )
    except Exception as _dc_start_exc:
        logger.debug(
            "discord-startup-heartbeat fejl run_id=%s: %s",
            run.run_id, _dc_start_exc,
        )
    # Phase 5: track in-flight runs so an interruption (crash, restart,
    # cancel) leaves a trail the next visible turn can surface to the user.
    try:
        from core.services.in_flight_runs import mark_started as _mark_run_started
        _mark_run_started(
            run_id=run.run_id,
            session_id=run.session_id,
            user_message=run.user_message,
        )
    except Exception:
        pass
    event_bus.publish(
        "runtime.visible_run_started",
        {
            "run_id": run.run_id,
            "lane": run.lane,
            "provider": run.provider,
            "model": run.model,
            "status": "started",
            "started_at": controller.started_at,
        },
    )
    yield _sse(
        "run",
        {
            "type": "run",
            "run_id": run.run_id,
            "lane": run.lane,
            "provider": run.provider,
            "model": run.model,
            "status": "started",
        },
    )
    yield _sse(
        "working_step",
        {
            "type": "working_step",
            "run_id": run.run_id,
            "action": "thinking",
            "detail": f"Thinking via {run.provider}/{run.model}",
            "step": 0,
            "status": "running",
        },
    )

    # Auto-compact chat history if approaching context limit
    try:
        from core.context.auto_compact import maybe_auto_compact_session
        _did_compact = maybe_auto_compact_session(
            run.session_id,
            provider=getattr(run, "provider", "") or "",
            model=getattr(run, "model", "") or "",
        )
    except Exception:
        _did_compact = False
    # ── Transparent compaction (harness Part B, Mechanism C) ──
    # The compaction already fired (session-level, stores a dedicated DB marker).
    # Make it client-visible + record cadence. No model-facing change.
    if _did_compact:
        yield _sse("compaction", {"type": "compaction", "run_id": run.run_id,
                                  "session_id": run.session_id})
        try:
            from core.services import central_timeseries as _cts_cmp
            _cts_cmp.record("context", "run_compaction", 1.0,
                            meta={"run_id": run.run_id, "session_id": run.session_id})
        except Exception:
            pass

    _step_counter = 0
    result = None
    visible_output_text = ""
    _final_run_status = "completed"
    _final_run_error: str | None = None
    # RUNTIME-CUTOFF-ROD (Bjørn 4. jul): en run der når `finally` UDEN at have
    # passeret et finaliserings-punkt (agentisk done / non-agentisk done) blev
    # behandlet som 'completed' pga. default'en ovenfor → _post_process fyrede
    # completed+tom → survival, provider-AGNOSTISK (kimi/deepseek tool-ture
    # afbrydes midt-flugt: GeneratorExit ved klient-drop, CancelledError, eller en
    # BaseException der ikke fanges af `except Exception`). Flaget sættes True LIGE
    # FØR hvert done-yield; er det stadig False i finally = runnet blev afbrudt →
    # markér 'interrupted' (ikke completed) så survival ALDRIG fyrer på en halv run.
    _reached_finalization = False
    # [CUTOFF-TRACE] Livscyklus-breadcrumb: opdateres ved hver fase så finally-downgrade
    # kan vise HVOR CancelledError ramte (tool-exec / agentic-runde / finalisering).
    _run_stage = "init"
    markup_buffer = _CapabilityMarkupBuffer()
    _collected_native_tool_calls: list[dict] = []
    # Tur-niveau blok-akkumulatorer (spec: content_json). _a_tool_calls/_a_parts
    # nulstilles pr. runde → holder kun SIDSTE runde. Disse samler HELE turens
    # ordnede tool-aktivitet (first-pass + alle agentiske runder) til én blok-array
    # der persisteres ved run-slut. Rent additivt/side-effekt-frit; en fejl her må
    # ALDRIG bryde et live run (append-helper er try/except-indkapslet).
    _turn_tool_calls: list[dict] = []
    _turn_tool_results: list[dict] = []
    # Interleave-log: trackér om model producerede text→tool i hvilken rækkefølge
    # under streamen, så _build_turn_blocks kan persistere blokke i den rækkefølge
    # de kom — frem for degraderet "tekst først, så tools"-rækkefølge.
    _interleave_log: list[str] = []

    def _coerce_tool_input(raw: object) -> dict:
        """Normalisér tool-input til et DICT. OpenAI-stil tool_calls bærer
        ``function.arguments`` som en JSON-STRENG — den skal parses, ellers
        gemmer content_json en rå streng som klienten renderer garbled (og som
        er en dobbelt-sandhed mod resten der er dicts). Aldrig kast."""
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str) and raw.strip():
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                return {}
        return {}

    def _accumulate_turn_blocks(tool_calls: list, results: list) -> None:
        try:
            for _tc in (tool_calls or []):
                _fn = (_tc.get("function") or {}) if isinstance(_tc, dict) else {}
                _turn_tool_calls.append({
                    "id": str((_tc.get("id") if isinstance(_tc, dict) else "") or ""),
                    "name": str(
                        _fn.get("name")
                        or (_tc.get("name") if isinstance(_tc, dict) else None)
                        or "tool"
                    ),
                    "input": _coerce_tool_input(
                        _fn.get("arguments")
                        if _fn.get("arguments") is not None
                        else (_tc.get("input") if isinstance(_tc, dict) else None)
                    ),
                })
            for _r in (results or []):
                _turn_tool_results.append({
                    "tool_use_id": str(getattr(_r, "tool_call_id", "") or ""),
                    "status": "done",
                    "content": str(getattr(_r, "content", "") or ""),
                    "is_error": False,
                })
        except Exception:
            # Blok-capture-fejl må aldrig forplante sig ind i streamet.
            pass

    _fp_deg_accum = ""              # akkumuleret first-pass-tekst (degenerations-guard)
    _fp_deg_since = 0               # tegn siden sidste degenerations-tjek
    _degenerated_reason: str | None = None
    try:
        try:
            # Run the synchronous model stream in a thread so SSE
            # frames are flushed to the client as each token arrives.
            _sentinel = object()
            queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_event_loop()

            import time as _fptime
            _fp_t0 = _fptime.monotonic()

            def _pump_model_stream() -> None:
                try:
                    for item in stream_visible_model(
                        message=run.user_message,
                        provider=run.provider,
                        model=run.model,
                        session_id=run.session_id,
                        controller=controller,
                        thinking_mode=run.thinking_mode,
                    ):
                        loop.call_soon_threadsafe(queue.put_nowait, item)
                except Exception as exc:
                    loop.call_soon_threadsafe(queue.put_nowait, exc)
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, _sentinel)

            _run_stage = "first_pass_streaming"
            thread_future = loop.run_in_executor(None, _pump_model_stream)

            _fp_first = False
            _fp_beat = 0
            _FP_KEEPALIVE_S = 6.0
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=_FP_KEEPALIVE_S)
                except asyncio.TimeoutError:
                    # Første token ikke kommet endnu — typisk fordi prompt-assembly
                    # kører ~15s inde i pump-tråden. Send livstegn så klienten IKKE
                    # timer ud (~20s) og river forbindelsen før første byte
                    # (Bjørn 2026-06-17 "spinner drejer ~20s → død").
                    if not _fp_first:
                        _fp_beat += 1
                        try:
                            touch_active_visible_run(run.run_id)
                        except Exception:
                            pass
                        yield _sse("heartbeat", {
                            "type": "heartbeat",
                            "run_id": run.run_id,
                            "phase": "prompt_assembly",
                            "elapsed_s": int(_fptime.monotonic() - _fp_t0),
                            "beat": _fp_beat,
                        })
                    continue
                if not _fp_first:
                    _fp_first = True
                    logger.warning("[firstpass-trace] run=%s FIRST item efter %.1fs: %s",
                                   run.run_id, _fptime.monotonic() - _fp_t0, type(item).__name__)
                if item is _sentinel:
                    break
                if isinstance(item, Exception):
                    raise item
                if controller.is_cancelled():
                    for cancelled_chunk in _cancel_visible_run(run):
                        yield cancelled_chunk
                    await thread_future
                    return
                if isinstance(item, VisibleModelDelta):
                    # ── Degenerations-guard (2026-06-23) ───────────────────────
                    # Provider-agnostisk: dræb model-repetitions-løkker ved kilden
                    # (var 147KB "probe_ollama"-skrald streamet+persisteret). Tjek
                    # periodisk (billigt) på akkumuleret first-pass-tekst.
                    _fp_deg_accum += item.delta
                    _fp_deg_since += len(item.delta)
                    if _fp_deg_since >= 1500:
                        _fp_deg_since = 0
                        from core.services.stream_degeneration import (
                            check_degeneration as _chk_deg,
                        )
                        _is_deg, _deg_why = _chk_deg(_fp_deg_accum)
                        if _is_deg:
                            try:
                                controller.cancel()
                            except Exception:
                                pass
                            try:
                                from core.services import followup_observer as _fo_deg
                                _fo_deg.note_degeneration(
                                    run.run_id, provider=run.provider,
                                    model=run.model, reason=_deg_why,
                                    chars=len(_fp_deg_accum))
                            except Exception:
                                pass
                            logger.warning(
                                "degeneration-abort run_id=%s: %s",
                                run.run_id, _deg_why)
                            _degenerated_reason = _deg_why
                            break
                    safe_text = markup_buffer.feed(item.delta)
                    if safe_text:
                        _interleave_log.append("text")
                        _set_orb_phase("speak")
                        yield _sse(
                            "delta",
                            {
                                "type": "delta",
                                "run_id": run.run_id,
                                "delta": safe_text,
                            },
                        )
                    continue
                if isinstance(item, VisibleModelToolCalls):
                    _collected_native_tool_calls = item.tool_calls
                    _interleave_log.append("tool")
                    continue
                if isinstance(item, VisibleModelStreamDone):
                    result = item.result
                    remaining = markup_buffer.flush()
                    if remaining:
                        yield _sse(
                            "delta",
                            {
                                "type": "delta",
                                "run_id": run.run_id,
                                "delta": remaining,
                            },
                        )
                    _update_visible_execution_trace(
                        run,
                        {
                            "provider_first_pass_status": "completed",
                            "provider_call_count": 1,
                            "first_pass_input_tokens": item.result.input_tokens,
                            "first_pass_output_tokens": item.result.output_tokens,
                        },
                    )
                    break

            await thread_future
        except VisibleModelStreamCancelled:
            _cancel_reason = (
                "user-cancelled" if _visible_run_cancelled(run.run_id)
                else "client-disconnect"
            )
            _update_visible_execution_trace(
                run,
                {
                    "provider_first_pass_status": "cancelled",
                    "provider_error_summary": _cancel_reason,
                },
            )
            _persist_session_assistant_message(run, "Generation cancelled.")
            _final_run_status = "cancelled"
            _reached_finalization = True  # eksplicit terminal — immun mod finally-downgrade
            set_last_visible_run_outcome(
                run,
                status="cancelled",
            )
            for cancelled_chunk in _cancel_visible_run(run):
                yield cancelled_chunk
            return
        except VisibleModelRateLimited as exc:
            bounded_message = (
                str(exc) or "Backend is temporarily unavailable. Please try again."
            )
            stage_error = f"first-pass-provider-error: {bounded_message}"
            _update_visible_execution_trace(
                run,
                {
                    "provider_first_pass_status": "failed",
                    "provider_error_summary": bounded_message,
                    "provider_call_count": 1,
                },
            )
            _persist_session_assistant_message(run, bounded_message)
            _final_run_status = "failed"
            _reached_finalization = True  # eksplicit terminal — immun mod finally-downgrade
            set_last_visible_run_outcome(
                run,
                status="failed",
                error=stage_error,
            )
            for failure_chunk in _fail_visible_run(run, stage_error):
                yield failure_chunk
            return
        except Exception as exc:
            # ── Autonom-fallback (Task 10) ────────────────────────────────────
            # KUN autonome (heartbeat-udløste, ingen bruger) runs: en fejlet
            # first-pass model-stream faldes igennem til den GRATIS cheap-lane
            # pool, så den autonome loop ikke knækker. Synlige (bruger-
            # tilstedeværende) runs rører ALDRIG dette — _maybe_fallback_for_
            # autonomous returnerer None for dem, og exception propagerer
            # PRÆCIS som før (uændret adfærd). Selve pool-gaten sidder i
            # helperens eget flag (non_visible_ollama_fallback_enabled, default
            # OFF): flag OFF → helper re-raiser → vi får None → dagens adfærd.
            _auto_fb = _maybe_fallback_for_autonomous(run, exc)
            if _auto_fb is not None:
                _final_run_status = "completed"
                _reached_finalization = True  # eksplicit terminal — immun mod finally-downgrade
                for _fb_chunk in _complete_visible_run_from_fallback(run, _auto_fb):
                    yield _fb_chunk
                return
            from core.services.visible_runs_error_messaging import (
                friendly_provider_error_message,
            )
            raw_message = str(exc) or type(exc).__name__
            user_message = friendly_provider_error_message(exc)
            stage_error = f"first-pass-provider-error: {raw_message}"
            logger.warning("visible_runs first-pass provider error: %s", raw_message)
            _update_visible_execution_trace(
                run,
                {
                    "provider_first_pass_status": "failed",
                    "provider_error_summary": raw_message,
                    "provider_call_count": 1,
                },
            )
            _persist_session_assistant_message(run, user_message)
            _final_run_status = "failed"
            _reached_finalization = True  # eksplicit terminal — immun mod finally-downgrade
            set_last_visible_run_outcome(
                run,
                status="failed",
                error=stage_error,
            )
            for failure_chunk in _fail_visible_run(run, stage_error):
                yield failure_chunk
            return

        if result is None and _degenerated_reason:
            # Degenerations-guard dræbte streamen ved kilden (model-loop). Ærligt,
            # synligt svar i stedet for 147KB skrald ELLER en kryptisk provider-fejl.
            stage_error = f"degeneration-aborted: {_degenerated_reason}"
            _deg_user_msg = (
                "Jeg kørte i en gentagelses-løkke og stoppede mig selv før det "
                "blev til skrald. Spørg igen, så svarer jeg rent.")
            _update_visible_execution_trace(
                run,
                {
                    "provider_first_pass_status": "degeneration_aborted",
                    "provider_error_summary": _degenerated_reason,
                    "provider_call_count": 1,
                },
            )
            _persist_session_assistant_message(run, _deg_user_msg)
            _final_run_status = "failed"
            _reached_finalization = True  # eksplicit terminal — immun mod finally-downgrade
            set_last_visible_run_outcome(run, status="failed", error=stage_error)
            for failure_chunk in _fail_visible_run(run, stage_error):
                yield failure_chunk
            return

        if result is None:
            _final_run_status = "failed"  # ellers overskriver _post_process (finally) med "completed"+tom → falsk survival
            _reached_finalization = True  # eksplicit terminal — immun mod finally-downgrade
            stage_error = "first-pass-provider-error: Visible model stream completed without final result"
            _update_visible_execution_trace(
                run,
                {
                    "provider_first_pass_status": "failed",
                    "provider_error_summary": "Visible model stream completed without final result",
                    "provider_call_count": 1,
                },
            )
            set_last_visible_run_outcome(
                run,
                status="failed",
                error=stage_error,
            )
            for failure_chunk in _fail_visible_run(run, stage_error):
                yield failure_chunk
            return

        # ── Prosa-tool-call-redning (tool-leak-fix 2026-06-21) ──────────────
        # Nogle modeller (deepseek-v4-flash) skriver tool-kald som prosa i teksten
        # i stedet for strukturerede tool_calls. Konvertér `[navn]: {json}`-kald (kun
        # for REGISTREREDE tools) til ægte kald så de eksekverer, og fjern dem fra
        # teksten så presentation_invariant ikke blokerer svaret. Guarded: rører kun
        # noget når der IKKE var native kald og der faktisk findes prosa-kald.
        if not _collected_native_tool_calls and result is not None and getattr(result, "text", ""):
            try:
                from core.services.prose_tool_calls import extract_prose_tool_calls
                from core.tools.simple_tools import _TOOL_HANDLERS as _ptc_handlers
                _cleaned_text, _prose_calls = extract_prose_tool_calls(
                    result.text, _ptc_handlers.keys(),
                )
                if _prose_calls:
                    _collected_native_tool_calls = _prose_calls
                    result.text = _cleaned_text
                    logger.warning(
                        "prose-tool-call-redning (first-pass): konverterede %d "
                        "prosa-kald run_id=%s", len(_prose_calls), run.run_id,
                    )
            except Exception as _ptc_exc:
                logger.debug("prose-tool-call-parse fejlede: %s", _ptc_exc)

        # ── Resend-på-tom (2026-06-23, Bjørn option 1 — runtime KURERER) ─────
        # Provider-AGNOSTISK: en transient tom first-pass (intet svar, ingen tools,
        # ingen prosa-kald) gen-spørges ÉN gang. Idempotent — intet blev eksekveret.
        # Transient → lykkes oftest. execute_visible_model er SYNKRON → kør i tråd
        # (ellers fryser --workers 1 API'et). Bærer fuld kontekst via session_id.
        if (result is not None and not _collected_native_tool_calls
                and not (getattr(result, "text", "") or "").strip()):
            try:
                from core.services.visible_model import (
                    execute_visible_model as _exec_rs,
                )
                # #1453-KUR (2026-06-30): en tom first-pass (content+reasoning=0)
                # er DeepSeeks dokumenterede tom-completion-bug på thinking-modeller
                # — og den er STICKY: re-spørg med SAMME thinking-model → bliver tom
                # igen (verificeret på Bjørns council-spørgsmål, tomt 2×). Resend nu
                # med den NON-thinking compat-alias (deepseek-chat) som ikke har
                # #1453 → den formulerer svaret. Andre providere: uændret resend.
                _rs_provider, _rs_model = run.provider, run.model
                _rs_thinking = None
                try:
                    _rs_p = (run.provider or "").strip().lower()
                    _rs_m = (run.model or "").strip().lower()
                    # Thinking-modeller (deepseek-vX-flash, kimi, qwen3, glm-5, minimax,
                    # gpt-oss, nemotron, *-code, r1/o1) deler den STICKY tom-completion-bug:
                    # re-spørg SAMME thinking-model → tom igen. deepseek har en non-thinking
                    # alias vi swapper til; ANDRE providere/modeller har ikke → de faldt før
                    # tilbage til samme sticky model → cutoff (provider-agnostisk, 3. jul,
                    # kimi-k2.7-code:cloud). Fald tilbage til en pålidelig non-thinking
                    # formulator (deepseek-chat) så turen får et ÆGTE svar, ikke fallback-stub.
                    _THINK_HINTS = ("kimi", "-code", "deepseek-v", "qwen3", "glm-5",
                                    "minimax", "gpt-oss", "nemotron", "-r1", "o1-",
                                    "think", "reason")
                    if _rs_p == "deepseek":
                        # execute_visible_model normaliserer modellen + slår thinking
                        # fra via thinking_mode="fast" (ingen deprecated alias).
                        _rs_model = run.model
                        _rs_thinking = "fast"
                    elif any(_t in _rs_m for _t in _THINK_HINTS):
                        _rs_provider, _rs_model, _rs_thinking = (
                            "deepseek", "deepseek-v4-flash", "fast",
                        )
                except Exception:
                    _rs_provider, _rs_model = run.provider, run.model
                    _rs_thinking = None
                _rs = await asyncio.to_thread(
                    _exec_rs, message=run.user_message, provider=_rs_provider,
                    model=_rs_model, session_id=run.session_id,
                    thinking_mode=_rs_thinking)
                _rs_text = (getattr(_rs, "text", "") or "").strip()
                try:
                    from core.services import followup_observer as _fo_rs
                    _fo_rs.note_resend(run.run_id, provider=_rs_provider,
                                       model=_rs_model, recovered=bool(_rs_text))
                except Exception:
                    pass
                if _rs_text:
                    result = _rs
                    logger.warning(
                        "resend-recovered tom first-pass run_id=%s model=%s (%d tegn)",
                        run.run_id, _rs_model, len(_rs_text))
                    yield _sse("delta", {"type": "delta", "run_id": run.run_id,
                                         "delta": _rs_text})
            except Exception as _rs_exc:
                logger.debug("resend-på-tom fejlede: %s", _rs_exc)

        capability_plan = _extract_capability_plan(result.text)

        # ── Native tool_calls: execute directly via simple_tools ──
        # _round_extra_tools holds names added by load_more_tools calls (any round);
        # merged into next-round tool_definitions inside the agentic loop.
        _round_extra_tools: list[str] = []
        if _collected_native_tool_calls:
            _run_stage = "native_tool_exec"
            # Mark initial "thinking" step done so it moves to top of done list
            yield _sse("working_step", {
                "type": "working_step",
                "run_id": run.run_id,
                "action": "thinking",
                "step": 0,
                "status": "done",
            })
            # ── Announce → execute → heartbeat pump (extracted to visible_tool_exec,
            #    Boy-Scout 2026-07-19). Announces each tool as a working_step, re-asserts
            #    the load-bearing ContextVars (scope/session_id/override) VERBATIM before
            #    copy_context, runs the batch in a worker thread with a 5s keepalive
            #    heartbeat, and — when run.local_tool_exec — registers each call with the
            #    broker + emits a first-class tool_call so the jarvis-code client runs it.
            _fp_batch_out: dict = {}
            async for _frame in run_tool_batch(
                _collected_native_tool_calls,
                run=run, loop=loop, tool_scope=tool_scope,
                step_counter=_step_counter,
                heartbeat_interval_s=5.0,
                heartbeat_phase="first_pass_tools",
                out=_fp_batch_out,
            ):
                yield _frame
            simple_results = _fp_batch_out["results"]
            _step_counter = _fp_batch_out["step_counter"]

            # Detect first-pass load_more_tools so the agentic loop can include
            # the requested tools in its next round.
            for _lm_sr in (simple_results or []):
                try:
                    if str(_lm_sr.get("tool_name") or "") != "load_more_tools":
                        continue
                    _lm_added = (_lm_sr.get("result") or {}).get("added") or []
                    for _lm_n in _lm_added:
                        if _lm_n and _lm_n not in _round_extra_tools:
                            _round_extra_tools.append(str(_lm_n))
                except Exception:
                    pass

            if simple_results:
                _update_visible_execution_trace(
                    run,
                    {
                        "argument_binding_mode": "native-tool-call",
                        "native_tool_call_count": len(simple_results),
                    },
                )

                # Capture base messages BEFORE any tool results are appended to DB.
                # This gives us the correct conversation up to (but not including)
                # the assistant's tool_calls, which we add manually below.
                # If we called _build_visible_input AFTER appending tool messages,
                # those messages would appear in the wrong order and duplicated.
                from core.services.ollama_visible_prompt import (
                    serialize_ollama_chat_messages,
                )
                # 2026-06-08: _build_visible_input blocks main_loop for 6-33s
                # while waiting on relevance/cognitive_state/frame thread-pool
                # futures (via .result() calls in prompt_contract). When run
                # synchronously inside this async generator it freezes the
                # event loop — bridge dispatch coroutines submitted via
                # run_coroutine_threadsafe can't make progress, so subsequent
                # tool calls stall (WORKER-SUBMITTED logged but no bridge
                # START logged, then 60s WORKER-TIMEOUT). asyncio.to_thread
                # offloads to a worker thread, keeping the loop free.
                # KEEPALIVE OGSÅ HER (samme tavse-vindue-rod): _build_visible_input
                # blokerer 6-33s i en tråd. Uden heartbeat gav dét den anden halvdel af
                # det tavse vindue der fik forbindelsen cancellet. shield + 5s-beat.
                _bvi_task = asyncio.ensure_future(asyncio.to_thread(
                    _build_visible_input,
                    run.user_message,
                    session_id=run.session_id,
                    provider=run.provider,
                    model=run.model,
                ))
                _bvi_start = time.monotonic()
                _bvi_beats = 0
                while not _bvi_task.done():
                    try:
                        await asyncio.wait_for(asyncio.shield(_bvi_task), timeout=5.0)
                    except asyncio.TimeoutError:
                        _bvi_beats += 1
                        try:
                            touch_active_visible_run(run.run_id)
                        except Exception:
                            pass
                        yield _sse("heartbeat", {
                            "type": "heartbeat",
                            "run_id": run.run_id,
                            "phase": "prompt_assembly_postool",
                            "elapsed_s": int(time.monotonic() - _bvi_start),
                            "beat": _bvi_beats,
                        })
                visible_input_pre = await _bvi_task
                base_messages = serialize_ollama_chat_messages(visible_input_pre)

                # ── Cache-boundary drift observer (harness Part B, Mechanism A) ──
                # Zero prompt mutation: hash the STATIC system message (base_messages[0])
                # and flag same-shape byte drift that would silently bust prefix-caching.
                try:
                    if base_messages:
                        import hashlib as _hl_cb
                        _sys_content = str(base_messages[0].get("content") or "")
                        from core.services.cache_boundary_observer import observe_static_prefix
                        observe_static_prefix(
                            provider=getattr(run, "provider", "") or "",
                            model=getattr(run, "model", "") or "",
                            section_shape=(_sys_content.count("\n\n"),),
                            static_prefix_sha=_hl_cb.sha256(_sys_content.encode("utf-8")).hexdigest(),
                        )
                except Exception:
                    pass

                # Send tool results as SSE events.
                # For approval_needed, block the run until the user approves/denies.
                # DB appends happen AFTER this loop so base_messages stays clean.
                _resolved_result_texts: dict[int, str] = {}

                for _idx, sr in enumerate(simple_results):
                    if sr["status"] == "approval_needed":
                        if run.autonomous:
                            # No user present — auto-deny approval-needed tools immediately
                            _resolved_result_texts[_idx] = (
                                f"[{sr['tool_name']}]: Autonomous run cannot approve tool calls — skipped."
                            )
                            yield _sse("capability", {"type": "tool_denied", "tool": sr["tool_name"]})
                            continue
                        if run.trust_all:
                            # Trust gradient (E8): even in trust mode, DESTRUCTIVE
                            # tool calls (rm -rf, force-push, drop table, etc.)
                            # require explicit user approval. The bash tool tags
                            # those with classification="destructive" in its
                            # result; same for any future tool that adopts the
                            # convention. Reversible/normal calls auto-approve
                            # as before.
                            _classification = str(sr["result"].get("classification", "") or "")
                            if _classification == "destructive":
                                # Fall through to approval-card path below.
                                pass
                            else:
                                _resolved_result_texts[_idx] = str(sr["result"].get("result_text") or "")
                                yield _sse("capability", {"type": "tool_approved", "tool": sr["tool_name"], "auto": True})
                                continue
                        approval_id = f"approval-{uuid4().hex[:12]}"
                        created_at = datetime.now(UTC).isoformat()
                        _PENDING_APPROVALS[approval_id] = {
                            "tool_name": sr["tool_name"],
                            "arguments": sr["arguments"],
                            "result": sr["result"],
                            "run_id": run.run_id,
                            "session_id": run.session_id,
                            "created_at": created_at,
                        }
                        # 2026-05-24 (Claude): tag the sr so the persistence
                        # loop can later check if resolve_pending_approval
                        # already wrote role=tool to chat (chat_persisted flag
                        # in approval state).
                        sr["approval_id"] = approval_id
                        _persist_pending_approvals()
                        _set_visible_approval_state(approval_id, {
                            "approval_id": approval_id,
                            "status": "pending",
                            "tool_name": sr["tool_name"],
                            "arguments": sr["arguments"],
                            "result": sr["result"],
                            "run_id": run.run_id,
                            "session_id": run.session_id,
                            "created_at": created_at,
                        })
                        yield _sse("approval_request", {
                            "type": "approval_request",
                            "approval_id": approval_id,
                            "tool": sr["tool_name"],
                            "message": sr["result"].get("message", ""),
                            "detail": (
                                sr["result"].get("path")
                                or sr["result"].get("command", "")
                            ),
                        })
                        # Block the generator until user approves or denies (5 min timeout)
                        _resolved = None
                        _deadline = asyncio.get_running_loop().time() + 300.0
                        logger.info(
                            "approval-wait-start run_id=%s round=0 approval_id=%s tool=%s",
                            run.run_id, approval_id, sr["tool_name"],
                        )
                        while asyncio.get_running_loop().time() < _deadline:
                            _approval_state = _get_visible_approval_state(approval_id)
                            _status = str(_approval_state.get("status") or "")
                            if _status == "approved":
                                _resolved = str(_approval_state.get("result_text") or "")
                                logger.info(
                                    "approval-resolved run_id=%s approval_id=%s result_chars=%d",
                                    run.run_id, approval_id, len(_resolved),
                                )
                                break
                            if _status in {"denied", "expired"}:
                                _resolved = None
                                logger.info(
                                    "approval-rejected run_id=%s approval_id=%s status=%s",
                                    run.run_id, approval_id, _status,
                                )
                                break
                            await asyncio.sleep(0.25)
                        else:
                            logger.warning(
                                "approval-timeout run_id=%s approval_id=%s",
                                run.run_id, approval_id,
                            )
                        if _resolved is None:
                            _resolved_result_texts[_idx] = f"[{sr['tool_name']}]: Tool call denied by user."
                            yield _sse("capability", {"type": "tool_denied", "tool": sr["tool_name"]})
                        else:
                            _resolved_result_texts[_idx] = _resolved
                            yield _sse("capability", {"type": "tool_result", "tool": sr["tool_name"], "status": "ok"})
                        continue
                    # ── Gate-blocked tools (veto gate or decision gate) ──
                    if sr["status"] == "gate_blocked":
                        _gate_type = str(sr.get("result", {}).get("gate_type", "unknown"))
                        _gate_msg = str(sr.get("result", {}).get("message", ""))
                        _resolved_result_texts[_idx] = f"[{_gate_type}] {_gate_msg}"
                        yield _sse("capability", {
                            "type": "gate_blocked",
                            "gate_type": _gate_type,
                            "tool": sr["tool_name"],
                            "message": _gate_msg,
                        })
                        yield _sse("working_step", {
                            "type": "working_step",
                            "run_id": run.run_id,
                            "action": sr["tool_name"],
                            "step": _step_counter - len(simple_results) + _idx + 1,
                            "status": "done",
                        })
                        continue
                    _resolved_result_texts[_idx] = sr["result_text"]
                    from core.services.tool_chip_payload import build_tool_capability_payload
                    yield _sse("capability", build_tool_capability_payload(
                        tool=sr["tool_name"],
                        status=sr["status"],
                        arguments=sr.get("arguments"),
                        result_text=sr.get("result_text", ""),
                    ))
                    yield _sse("working_step", {
                        "type": "working_step",
                        "run_id": run.run_id,
                        "action": sr["tool_name"],
                        "step": _step_counter - len(simple_results) + _idx + 1,
                        "status": "done",
                    })
                    # App-self-control (spec 2026-06-15): hvis tool'et bad om et
                    # app-skift (request_app_action), emit et inline system-event
                    # som desk viser som godkendelseskort. run.user_message giver
                    # den besked der skal gen-sendes efter godkendelse.
                    try:
                        from core.tools.app_control_tool import build_app_action_event
                        _app_ev = build_app_action_event(
                            sr.get("result"),
                            user_message=run.user_message,
                            session_id=run.session_id or "",
                        )
                        if _app_ev:
                            yield _sse("app_action_request", _app_ev)
                    except Exception:
                        pass

                # Persist tool results to session DB after all approvals are resolved.
                # 2026-05-24 (Claude): skip when resolve_pending_approval already
                # persisted (chat_persisted=True flag in approval state). This
                # avoids duplicate role=tool messages when the user approves
                # while the stream is still active — both code paths used to
                # race to append.
                if run.session_id:
                    for _idx, sr in enumerate(simple_results):
                        result_text = _resolved_result_texts.get(_idx, sr.get("result_text", ""))
                        if not result_text:
                            continue
                        if sr.get("status") in ("duplicate_suppressed", "gate_blocked"):
                            continue
                        # Check if approval-path already persisted this tool result
                        _aid = sr.get("approval_id") or ""
                        if _aid:
                            try:
                                _astate = _get_visible_approval_state(str(_aid)) or {}
                                if _astate.get("chat_persisted"):
                                    continue
                            except Exception:
                                pass
                        # 2026-06-29 (loop-not-blocked): append_chat_message er en
                        # SYNKRON DB-skrivning (save_tool_result + INSERT + et par
                        # fire-and-forget signal-motorer). Den kørte direkte på
                        # translate_to_v2's event-loop-tråd lige EFTER tool-eksekvering
                        # → frøs loopet → _ping_loop kunne ikke fyre → last_append_at
                        # frøs → active-runs flippede runnet not-live (rod bag
                        # "desk-spinner/mobil-takeover" under tool-runder). Offload til
                        # en worker-tråd så ping/keepalive bliver ved. Samme exception-
                        # type propageres til samme handler (to_thread re-raiser i den
                        # ventende frame); rækkefølge + semantik uændret.
                        await asyncio.to_thread(
                            append_chat_message,
                            session_id=run.session_id,
                            role="tool",
                            content=result_text,
                            tool_name=str(sr.get("tool_name") or ""),
                            tool_arguments=dict(sr.get("arguments") or {}),
                        )

                # ── Agentic follow-up loop ────────────────────────────────────────────
                # Runs up to _AGENTIC_MAX_ROUNDS LLM passes after the first-pass
                # tool execution. Each pass may call more tools; if it does we
                # execute them and continue. If the model produces text we stream
                # it and stop. This lets Jarvis work through multi-step tasks
                # without the user needing to send a new message for every tool.
                from core.services import visible_followup as _vf
                from core.tools.simple_tools import get_tool_definitions as _get_tool_defs

                # History:
                #   40 was the original cap when Copilot was the only agentic
                #   provider; rarely went past 3 rounds.
                #   10 was set after big-pickle (OpenCode) loop runaways at 30+
                #   rounds with empty text — too restrictive for legit
                #   multi-step work (pip-install loops, dataset prep etc.).
                #   25 was a sweet spot for short chains, but Jarvis kept
                #   hitting it on real autonomous work (Sansernes Arkiv fix
                #   chained ~20 tool calls; chronicle consolidation chains 15+).
                #   50 (2026-04-28) gives him real headroom for self-directed
                #   investigations. Runaway-loop protection is preserved by
                #   _MAX_EMPTY_TEXT_ROUNDS — no text for 8 rounds in a row
                #   still kills text-empty spirals.
                try:
                    from core.services.affect_modulation import compute_agentic_loop_budget
                    from core.services.in_flight_runs import interrupted_for_session as _interrupted_for_session
                    _agentic_budget = compute_agentic_loop_budget(
                        resume_context=bool(_interrupted_for_session(run.session_id)),
                    )
                except Exception:
                    _agentic_budget = {}
                _AGENTIC_MAX_ROUNDS = int(_agentic_budget.get("max_rounds") or 100)
                # Harness Part 1 (earned model-trust): set True if this run shows any degeneration
                # (no-progress spin / hollow promise / and — at finalize — failed/interrupted status).
                # Read at run finalize by record_run_outcome. Additive; changes no control flow.
                _run_degenerated = False
                _agentic_tools = _get_tool_defs()
                # ── Tool router: scope tool defs to a relevant subset ──
                # Falls back to the full list silently if anything goes wrong.
                try:
                    from core.services.tool_router import select_tools as _select_tools
                    _selection = _select_tools(
                        user_message=run.user_message,
                        session_id=run.session_id,
                        lane="autonomous" if run.autonomous else "visible",
                        run_id=run.run_id,
                    )
                    if not _selection.fallback_used:
                        _selected_set = set(_selection.selected_names)
                        _agentic_tools = [
                            d for d in _agentic_tools
                            if ((d.get("function") or {}).get("name") or d.get("name") or "") in _selected_set
                        ]
                except Exception:
                    pass  # keep full list on any error
                _all_followup_parts: list[str] = []
                # I1-heal (2026-06-30): thinking-modeller (deepseek-v4-flash m.fl.) lægger
                # nogle gange HELE svaret i reasoning. Vi akkumulerer reasoning-deltaerne
                # parallelt så vi kan surface dem som svar hvis content-parts er tomme —
                # ellers falsk empty_completion → fallback wiper det streamede svar.
                _all_followup_reasoning_parts: list[str] = []
                _a_parts: list[str] = []
                # Decision-signal EFEMER staging (2026-07-04 runaway-fix): fyrede
                # decision-signals akkumulerede før i _a_parts → forurenede BÅDE det
                # persisterede svar OG resolution-exit-tjekket (self-poisoning runaway,
                # se core/services/decision_signal_staging.py). Nu holdes de her, dedup'et
                # pr. decision-id, og injiceres KUN i exchange-teksten via _exchange_text().
                _ds_active: dict[str, str] = {}
                from core.services import decision_signal_staging as _dss

                def _exchange_text() -> str:
                    """Assistant-turen til modellen = rent svar (_a_parts) + efemere
                    decision-noter. _a_parts forbliver ren (persist + resolution-tjek)."""
                    return _dss.compose_exchange_text(_a_parts, _ds_active)

                def _to_followup_results(
                    tool_calls: list[dict],
                    round_results: list[dict[str, object]],
                    resolved_texts: dict[int, str],
                ) -> list[_vf.ToolResult]:
                    out: list[_vf.ToolResult] = []
                    for _idx, _tc in enumerate(tool_calls):
                        _sr = round_results[_idx] if _idx < len(round_results) else {}
                        _content = str(
                            resolved_texts.get(_idx, (_sr or {}).get("result_text", "")) or ""
                        ).strip()
                        _tc_name = str(
                            (_sr or {}).get("tool_name")
                            or ((_tc.get("function") or {}).get("name") or _tc.get("name") or "tool")
                        )
                        if not _content:
                            if _idx >= len(round_results):
                                _content = (
                                    f"[{_tc_name}]: Tool call was not executed in this round "
                                    "(bounded tool-execution limit reached)."
                                )
                            else:
                                _content = f"[{_tc_name}]: Tool call completed with no output."
                        out.append(
                            _vf.ToolResult(
                                tool_call_id=str(_tc.get("id") or ""),
                                tool_name=_tc_name,
                                content=_content,
                            )
                        )
                    return out

                _fp_followup_results = _to_followup_results(
                    _collected_native_tool_calls,
                    simple_results,
                    _resolved_result_texts,
                )
                # Tur-akkumulering (first-pass native tools) — genbruger SAMME
                # tool_calls + results som ToolExchange'en; side-effekt-frit.
                _accumulate_turn_blocks(_collected_native_tool_calls, _fp_followup_results)
                _followup_exchanges: list[_vf.ToolExchange] = [
                    _vf.ToolExchange(
                        text="",
                        tool_calls=list(_collected_native_tool_calls),
                        results=_fp_followup_results,
                        # Thinking-mode replay (Deepseek v4-pro/reasoner):
                        # the API rejects followups if reasoning_content from
                        # the prior assistant turn isn't sent back verbatim.
                        reasoning_content=str(getattr(result, "reasoning_content", "") or ""),
                    )
                ]
                try:
                    from core.services.agentic_checkpoints import save_checkpoint as _save_agentic_checkpoint
                    _save_agentic_checkpoint(
                        run_id=run.run_id,
                        session_id=run.session_id,
                        user_message=run.user_message,
                        provider=run.provider,
                        model=run.model,
                        round_index=0,
                        phase="first-pass-tools-complete",
                        exchanges=_followup_exchanges,
                        partial_text="".join(_all_followup_parts),
                    )
                except Exception:
                    pass
                _supported_followup_providers = set(_vf.supported_followup_providers())
                _provider_supports_followup = (
                    (run.provider or "").strip().lower() in _supported_followup_providers
                )
                logger.info(
                    "agentic-loop-entry run_id=%s provider=%s supports_followup=%s exchange_count=%d",
                    run.run_id, run.provider, _provider_supports_followup, len(_followup_exchanges),
                )

                _consecutive_empty_text_rounds = 0
                # Bumped from 4 → 8 → 12 (2026-04-28) because Jarvis routinely
                # needs to read 8–12 files in a row when investigating his own
                # runtime (e.g. mood_tone fix in Sansernes Arkiv chained ~10
                # consecutive read_file/grep calls without narration). At 4
                # he'd get force-stopped mid-investigation; 8 still cut him
                # short on bigger refactor analysis. 12 gives him real room
                # for autonomous work while still catching the actual runaway
                # pattern (big-pickle 30+ tool-spam still gets caught long
                # before it balloons the prompt past 200k chars).
                # 2026-06-11 (Bjørn frustration crisis): sænket 12 → 3.
                # Bjørn observerede over de sidste 16+ timer Jarvis sidde
                # i Discord/JarvisX/webchat agentic-loops i 5-15 min UDEN
                # at sende text-svar — han skrev "?", "...", "Helt seriøst!!!!?"
                # gentagne gange uden at få et ord. Tidligere tærskel på
                # 12 rounds × ~30s = potentielt 6 min stilhed for brugeren.
                # 3 rounds tvinger Jarvis tilbage til dialog hurtigt. Lang-
                # selvstændigt arbejde sker stadig (3 rounds rækker for
                # at fx læse 3 filer eller køre 3 bash-checks), men hvis
                # han fortsætter uden at sige noget = forced summary med
                # synligt svar til brugeren.
                _MAX_EMPTY_TEXT_ROUNDS = int(_agentic_budget.get("max_empty_text_rounds") or 3)
                # Dream bias (Lag 2) — loop_persistence shifts how long he stays in loop.
                # ±2 rounds at intensity=1.0; hard floor 4, cap 20.
                #
                # KONTROL-ARM-KONSUMTION (oneirisk sløjfe §4, owner samtykkede): på ~20% af
                # dagene beregnes biasen men ANVENDES IKKE, så aktiv vs kontrol kan
                # sammenlignes og drømmen må BEVISE sig i stedet for at selv-bekræfte.
                # Kontrol-beslutningen er deterministisk pr. dag (is_control_day). FAIL-OPEN:
                # enhver fejl i tjekket → normal anvendelse (nuværende adfærd bevaret).
                try:
                    from core.services import central_oneiric_loop as _oneiric
                    _oneiric_control_day = bool(_oneiric.is_control_day(_oneiric._today()))
                except Exception:
                    _oneiric_control_day = False
                try:
                    from core.services.dream_bias_engine import get_active_dream_bias
                    _bias = get_active_dream_bias(workspace_id="default")
                    if _bias and not _oneiric_control_day:
                        _persistence_mod = float(_bias["threshold_bias"].get("loop_persistence", 0.0))
                        _intensity = float(_bias.get("intensity") or 0.0)
                        if _persistence_mod != 0.0:
                            _shift = int(round(_persistence_mod * _intensity * 2))
                            _MAX_EMPTY_TEXT_ROUNDS = max(4, min(20, _MAX_EMPTY_TEXT_ROUNDS + _shift))
                except Exception:
                    pass
                # ── Tool-only loop guard (2026-05-03) ──
                # Counts consecutive agentic rounds that produced tool calls
                # but emitted less than _TOOL_ONLY_TEXT_THRESHOLD chars of
                # user-visible text. At _MAX_TOOL_ONLY_ROUNDS, we force the
                # model to respond with text by withholding tool definitions
                # — same mechanism as the empty-text guard. This catches the
                # pattern where Jarvis keeps digging (read_file, grep, etc.)
                # without delivering a visible answer, even though each
                # round may have a sliver of text that resets the empty-text
                # counter. The threshold chars are deliberately low to only
                # suppress truly tool-only rounds, not rounds with real prose.
                _consecutive_tool_only_rounds = 0
                # Bumped 8 → 15 (2026-05-07): genuine safety-net, not daily
                # blocker. Soft loop_nudge (at round 8) carries attention-
                # responsibility; hard brake only catches runaway-loops, not
                # legitimate deep investigations. Override via
                # _agentic_budget.max_tool_only_rounds if runtime-config
                # has a different value.
                # 2026-06-11: sænket 15 → 4. Samme begrundelse som
                # _MAX_EMPTY_TEXT_ROUNDS ovenfor — for at fange "stuck
                # in tools without telling user" pattern hurtigt.
                _MAX_TOOL_ONLY_ROUNDS = int(_agentic_budget.get("max_tool_only_rounds") or 4)
                _TOOL_ONLY_TEXT_THRESHOLD = 80  # chars
                _tool_pause_active = False  # set True after 5 tool-only rounds → withhold tools
                _hollow_promise_nudged = False  # hollow-promise-guard: cap ÉT nudge pr. run
                # Eskalerende synthese-pause (Bjørn 2026-06-17 "spinner→død"-roden):
                # når Jarvis spiraler i tavse tool-runder (fx læser filer én-ad-gangen),
                # tving ham til at OPSUMMERE efter N runder ved at fjerne tools i ÉN runde.
                # Pausen løftes så snart han producerer tekst (linje ~2185) → han kan
                # fortsætte legit dybt arbejde, men skal surface'e fremskridt undervejs i
                # stedet for at ramme den tørre 20-cap med tom skærm.
                _SYNTH_PAUSE_AFTER = 8
                _synth_pause_fired_at = -100  # runde hvor vi sidst tvang en pause
                _agentic_loop_exit_reason = "completed"
                # ── LAG 3 no-progress-detektor state (Bjørn 4. jul) ──
                _force_finalize_next = False       # sat i bunden af en no-progress-runde
                _prev_round_sig: frozenset | None = None  # forrige rundes (tool,args,result)-signatur
                _no_progress_rounds = 0            # antal på hinanden følgende no-progress-runder
                _MAX_NO_PROGRESS = 2               # 2 identiske runder → finalize
                _prev_round_end_t: float | None = None  # for inter-round-gap metric
                # Track most-recent assistant reasoning_content for persistence
                # (Deepseek thinking-mode replay). Starter med first-pass-result.
                _persist_reasoning: str = str(getattr(result, "reasoning_content", "") or "")
                # ── Fase 1 (spec §4.1/E11): rund-niveau stream-retry der bevarer
                # turen. ALT bag kill-switch `agentic_round_retry_enabled()`
                # (default OFF → byte-identisk med i dag). Caps initialiseres ved
                # for-loop-entry (E11/S2/P6):
                #   - _round_stream_max_retries : per-runde retry-loft (separat fra
                #     _AGENTIC_MAX_ROUNDS-budgettet — en retry forbruger IKKE en runde).
                #   - _turn_total_retries       : HÅRDT total-loft over HELE turen
                #     (lukker 9×100-worst-case-eksplosionen).
                #   - _turn_started_at          : wall-clock-deadline pr. tur (P6).
                _round_stream_max_retries = int(_agentic_budget.get("round_stream_max_retries") or 3)
                _turn_total_retry_cap = int(_agentic_budget.get("turn_total_stream_retries") or 12)
                _turn_wall_clock_cap_s = float(_agentic_budget.get("turn_total_wall_clock_s") or 600.0)
                _turn_total_retries = 0
                _turn_started_at = time.monotonic()
                # ── Fase 3 (spec §4 S6, §11.2): provider-failover-state ──────────
                # Den provider/model det AGENTISKE loop sampler igennem. Starter på
                # run's egen visible-provider; en failover (åben breaker / fatal-men-
                # failover-bar fejl) REBINDER disse for RESTEN af turen (S6). Pumpen
                # læser dem som default-args så hvert forsøgs pump fanger den
                # aktuelle (evt. failover'ede) provider. Flag-OFF → aldrig rebundet
                # → byte-identisk med i dag.
                _active_provider = run.provider
                _active_model = run.model
                # True når denne tur ALLEREDE er failet over én gang (vi failer ikke
                # over i en uendelig kæde — én fallback, så graceful exhaustion).
                _did_failover = False
                # Lav agentisk temperatur (anti-hallucination, 2026-06-30): faktuelt
                # tool-arbejde sampler deterministisk lavt. Negativ værdi = frakoblet
                # (provider-default). Læst ÉN gang før loopet; thinking-modeller
                # ignorerer den server-side (no-op).
                try:
                    from core.runtime.settings import load_settings as _ld_temp
                    _st_temp = _ld_temp()
                    _agentic_temp = float(getattr(_st_temp, "agentic_followup_temperature", 0.3))
                    _agentic_top_p = float(getattr(_st_temp, "agentic_followup_top_p", 0.9))
                    if _agentic_temp < 0:
                        _agentic_temp = None
                    if _agentic_top_p < 0:
                        _agentic_top_p = None
                except Exception:
                    _agentic_temp, _agentic_top_p = 0.3, 0.9
                for _agentic_round in range(_AGENTIC_MAX_ROUNDS):
                    _run_stage = f"agentic_round_{_agentic_round + 1}"
                    if not _provider_supports_followup:
                        logger.warning(
                            "agentic-loop-skip run_id=%s reason=provider-not-supported provider=%s",
                            run.run_id, run.provider,
                        )
                        _agentic_loop_exit_reason = "provider-not-supported"
                        break
                    # Causal graph (2026-05-08): publish round-start sentinel
                    # and set EventContext so all event_bus.publish() calls
                    # inside this iteration auto-link to round-start as parent.
                    # NB: we don't reset between iterations — next iteration
                    # just SETs to its new value. Final reset happens AFTER
                    # the for-loop (see below). break/continue/exception during
                    # iteration leaks briefly but next iteration overwrites.
                    from core.eventbus.context import set_current_event as _set_round_ctx
                    _round_event_id = _publish_agentic_round_start(
                        run_id=run.run_id, round_num=_agentic_round + 1,
                    )
                    _set_round_ctx(_round_event_id)
                    # Measure inter-round gap: tid fra forrige round-end til
                    # at this round actually starts LLM work. Bjørn
                    # observed May 7 that the gap sometimes feels very
                    # long — instrumented here so we can see where time goes.
                    import time as _time_mod
                    _round_loop_start_t = _time_mod.monotonic()
                    _inter_round_gap_ms = (
                        int((_round_loop_start_t - _prev_round_end_t) * 1000)
                        if _prev_round_end_t is not None else 0
                    )
                    logger.warning(
                        "agentic-round-start run_id=%s round=%d exchanges=%d inter_round_gap_ms=%d",
                        run.run_id, _agentic_round + 1, len(_followup_exchanges), _inter_round_gap_ms,
                    )
                    # Followup-cluster: runde synlig i Centralen (self-safe).
                    try:
                        from core.services import followup_observer as _fu_obs
                        _fu_obs.note_round(run.run_id, _agentic_round + 1,
                                           run.provider, run.model,
                                           exchanges=len(_followup_exchanges))
                    except Exception:
                        pass
                    # Cross-proces liveness-heartbeat (hver runde) — så
                    # /chat/active-runs i api-processen kan se at dette (evt.
                    # autonome, i runtime-processen) run stadig lever.
                    try:
                        touch_active_visible_run(run.run_id)
                    except Exception:
                        pass
                    # ── Synlig runde-progress (2026-06-30, #4) ─────────────────
                    # Tidligere så brugeren KUN tool-trin — de agentiske runder
                    # selv var usynlige, så lange loops føltes som tavshed ("den
                    # forsvinder"). Emit et let working_step pr. runde (fra runde 2,
                    # så korte 1-runde-svar ikke klyttes) så klienten ser at loopet
                    # lever og skrider frem. Kun interaktive runs; self-safe.
                    if not run.autonomous and _agentic_round >= 1:
                        try:
                            _step_counter += 1
                            yield _sse("working_step", {
                                "type": "working_step",
                                "run_id": run.run_id,
                                "action": "thinking",
                                "detail": f"Tænker videre · runde {_agentic_round + 1}",
                                "step": _step_counter,
                                "status": "running",
                            })
                        except Exception:
                            pass
                    _a_parts = []
                    _a_tool_calls: list[dict] = []
                    _a_round_reasoning: str = ""  # captured from FollowupDone
                    _a_queue: asyncio.Queue = asyncio.Queue()
                    _a_sentinel = object()
                    _a_failure: dict[str, object] = {}
                    # ── C11 partial-discard snapshot (spec §11.1) ────────────────
                    # Snapshot the persisted-answer accumulator length at round-
                    # ENTRY, BEFORE any pump attempt streams deltas into it. On a
                    # retry (4.1) we TRUNCATE _all_followup_parts back to this
                    # boundary so the partial text from a FAILED attempt is
                    # discarded and the re-run's fresh deltas don't double-emit /
                    # double-persist (the exact "thinks-a-bit-BANG" regression the
                    # retry would otherwise introduce). Snapshot is taken ONCE per
                    # round and is stable across attempts.
                    _round_partial_snapshot = len(_all_followup_parts)
                    # ── Lean agentic-prompt snapshot (spec §4.7, I7) ─────────────
                    # RETRY-IDENTITY-INVARIANT: lean-vs-full-beslutningen + de
                    # resulterende messages snapshottes HER, ÉN gang pr. runde, FØR
                    # retry-loopet (`while True` nedenfor). En retry af runde K skal
                    # sende BYTE-IDENTISKE messages som runde K's første forsøg →
                    # transformen må ALDRIG genberegnes inde i retry-loopet. Pumpen
                    # bruger udelukkende ``_round_base_messages`` (dette snapshot).
                    #
                    # Runde 0 (første pass) = ALTID full prompt (den framer svaret).
                    # Runde ≥1 + flag ON = lean (drop tung per-turn-hale). Flag OFF
                    # → ``_round_base_messages is base_messages`` (byte-identisk i dag).
                    _round_base_messages = base_messages
                    try:
                        if _agentic_round >= 1 and _vf.agentic_lean_prompt_enabled():
                            _lean_msgs, _lean_metrics = _vf.build_lean_base_messages(
                                base_messages)
                            _round_base_messages = _lean_msgs
                            try:
                                from core.services import followup_observer as _fu_lean
                                _fu_lean.note_lean_prompt(
                                    run.run_id, _agentic_round + 1,
                                    provider=run.provider, model=run.model,
                                    before_chars=int(_lean_metrics.get("before_chars") or 0),
                                    after_chars=int(_lean_metrics.get("after_chars") or 0),
                                    saved_tokens=int(_lean_metrics.get("saved_tokens") or 0),
                                    applied=bool(_lean_metrics.get("changed")))
                            except Exception:
                                pass
                    except Exception:
                        # Fail-open mod bloat — fald til full prompt, aldrig et brud.
                        _round_base_messages = base_messages
                    # Per-round stream-retry counter (separate from _AGENTIC_MAX_
                    # ROUNDS — a retry never consumes a round budget). _round_epoch
                    # is the D11 fence token: each attempt bumps it; the pump
                    # closure captures its own epoch and the drain ignores any late
                    # queue puts from a superseded attempt.
                    _round_retry_count = 0
                    _round_epoch = 0
                    # Set when an attempt retries; consumed (→ recovered nerve) when
                    # a later attempt of the SAME round succeeds. Reset per round.
                    _pending_recovered_attempt = 0

                    # On the final allowed round (or when we are 1 round away
                    # from the empty-text or tool-only early-exit threshold),
                    # force the model to summarize by withholding tool definitions.
                    # Without this, eager models (big-pickle/MiniMax) keep
                    # calling tools forever and the user never gets a coherent
                    # closing answer — only fragmented progress text.
                    # ── Loop-cluster GENNEM Den Intelligente Central (graderet, 2026-06-22) ──
                    # Hard-stop-beslutningen ruttes gennem central().decide → graderet
                    # (RED=hård stop, YELLOW=blød synthese-brems, GREEN=fortsæt) + catch/
                    # flag/notify/trace. Konsoliderer de spredte stop-betingelser i ÉN gate.
                    # FAIL-SAFE for en loop-gate: gate-fejl (SKIP) → hård stop; og hvis hele
                    # central-stien fejler → lokal backstop-beregning (loop aldrig i det uendelige).
                    try:
                        from core.services.central_core import central as _central_loop
                        from core.services.gate_loop import loop_gate as _loop_gate_fn
                        from core.services.gate_kernel import Decision as _LDec, GateClass as _LGK
                        _lv = _central_loop().decide("loop_control", {
                            "round": _agentic_round, "max_rounds": _AGENTIC_MAX_ROUNDS,
                            "consecutive_empty": _consecutive_empty_text_rounds,
                            "max_empty": _MAX_EMPTY_TEXT_ROUNDS,
                            "consecutive_tool_only": _consecutive_tool_only_rounds,
                            "max_tool_only": _MAX_TOOL_ONLY_ROUNDS,
                            "tool_pause": _tool_pause_active,
                            "run_id": run.run_id,
                        }, _loop_gate_fn, cluster="loop", klass=_LGK.COGNITIVE)
                        # Governed håndhævelse: SKIP (gate-fejl) → altid hård stop (fail-safe,
                        # aldrig uendeligt). RED (bevidst loop-brems) → hård stop KUN hvis
                        # loop_control er enforce-enabled (default ON). Slås den fra, fortsætter
                        # loopet — stadig bounded af range(_AGENTIC_MAX_ROUNDS) ovenfor.
                        if _lv.decision is _LDec.SKIP:
                            _is_last_round = True
                        elif _lv.decision is _LDec.RED:
                            from core.services import gate_enforcement as _ge
                            if _ge.is_enforced("loop_control", _LGK.COGNITIVE):
                                _is_last_round = True
                            else:
                                _ge.note_suppressed_block("loop_control", "loop", _lv.reason)
                                _is_last_round = False
                        else:
                            _is_last_round = False
                    except Exception:
                        _is_last_round = (
                            _agentic_round == _AGENTIC_MAX_ROUNDS - 1
                            or _consecutive_empty_text_rounds >= _MAX_EMPTY_TEXT_ROUNDS - 1
                            or _consecutive_tool_only_rounds >= _MAX_TOOL_ONLY_ROUNDS - 1
                        )
                    # ── LAG 3: NO-PROGRESS-DETEKTOR (Bjørn 4. jul, research-baseret) ──
                    # De eksisterende tællere fanger IKKE "narrerer >80 tegn men kalder
                    # SAMME værktøj med samme args og får samme resultat runde efter runde"
                    # (prosaen nulstiller tool-only-tælleren). Result-aware detektor:
                    # gentages rundens (tool,args,resultat)-signatur → INTET nyt lært →
                    # tving finalize NU i stedet for at brænde runder mod loftet. Sat i
                    # bunden af forrige runde; her løftes den ind i _is_last_round.
                    if _force_finalize_next:
                        _is_last_round = True
                    # Var tools fjernet i DENNE runde KUN pga. synthese-pausen (ikke
                    # fordi det er sidste runde)? Så er en tom tool-liste en TVUNGET
                    # opsummering — ikke et naturligt "jeg er færdig". Vi må ikke
                    # afslutte runnet på den (ellers ryger Jarvis' agency på dybt arbejde).
                    _round_was_synth_pause = _tool_pause_active and not _is_last_round
                    # ── CACHE-FIX (2026-06-30): hold tools-arrayet BYTE-IDENTISK på
                    # ALLE runder ───────────────────────────────────────────────────
                    # FØR satte synthese-pausen/sidste runde tools=None for at tvinge
                    # prosa. Men tools-blokken ligger LIGE EFTER system i deepseek-
                    # templaten → fjerner du den, brækker prefix-cachen ved ~7k (system
                    # cachet, ~80k tools+historik missset). Verificeret rod til 7%/90%-
                    # mønstret på multi-runde-ture (first-pass-tools ER byte-stabile).
                    # NU: behold tools på hver runde, tving prosa via tool_choice="none"
                    # (en sampling-param, IKKE i den cachede prompt-prefix) → cachen
                    # holder hele turen. _round_was_synth_pause-semantikken (må ikke
                    # afslutte på en tvunget tom runde) er uændret.
                    _force_summary = _is_last_round or _tool_pause_active
                    _round_tool_definitions = _agentic_tools
                    _round_tool_choice = "none" if _force_summary else None
                    # ── HARNESS-GARANTI: adapter-AGNOSTISK tvungen finalize (Bjørn 4. jul) ──
                    # Roden til "modellen skipper tekst" er RUNTIME, ikke modellen:
                    # tool_choice="none" er (a) KUN plumbet til openai-compat-adapteren
                    # (visible_followup.py:1495) og (b) ignoreres af mange modeller. På
                    # ollama/copilot/codex-lanes blev INGEN model nogensinde tvunget →
                    # tool-glade modeller loopede uden prosa på tværs af ALLE providers.
                    # På den ÆGTE finalize-runde (RED hard-stop — vi STOPPER alligevel)
                    # FJERNER vi tools fysisk (tool_definitions=None → HVER adapter udelader
                    # tools-arrayet, se visible_followup.py:549) + tilføjer en eksplicit
                    # "skriv dit endelige svar nu"-instruktion. Så kan INGEN model på NOGEN
                    # lane kalde et værktøj → den MÅ producere prosa. tool_choice="none"
                    # beholdes som sekundært signal. Instruktionen er APPEND-ONLY (ét ekstra
                    # trailing turn) → cache-prefixet (system+tools+historik) er allerede
                    # brudt af tool-fjernelsen på præcis denne ene afsluttende runde (one-shot,
                    # forskningsbekræftet acceptabelt). KUN _is_last_round — IKKE synthese-
                    # pausen (den skal kunne opsummere OG fortsætte med at grave).
                    if _is_last_round:
                        _round_tool_definitions = None
                        _round_base_messages = list(_round_base_messages) + [{
                            "role": "user",
                            "content": (
                                "Skriv nu dit endelige svar til brugeren i prosa, baseret "
                                "på værktøjs-resultaterne ovenfor. Kald IKKE flere værktøjer "
                                "— opsummer hvad du fandt og svar direkte."),
                        }]
                    # Merge in tools added by load_more_tools in previous rounds
                    if _round_tool_definitions is not None and _round_extra_tools:
                        _all_defs = _get_tool_defs() or []
                        _extra_set = set(_round_extra_tools)
                        _existing_names = {
                            ((d.get("function") or {}).get("name") or d.get("name") or "")
                            for d in _round_tool_definitions
                        }
                        for _xd in _all_defs:
                            _xn = (_xd.get("function") or {}).get("name") or _xd.get("name") or ""
                            if _xn in _extra_set and _xn not in _existing_names:
                                _round_tool_definitions = list(_round_tool_definitions) + [_xd]

                    # ── Fase 1 inner attempt-loop (spec §4.1): re-runs THIS round's
                    # model-sampling on a retryable transient failure (round-retry that
                    # PRESERVES the turn — codex run_sampling_request semantics). The
                    # loop body spawns the pump + drains it; on a retryable _a_failure
                    # under budget it fences the dead pump (D11), discards the failed
                    # attempt's partial (C11) and `continue`s to re-sample. On success,
                    # non-retryable failure, or exhausted budget it `break`s out with the
                    # existing _a_failure semantics intact. When the kill-switch is OFF
                    # the body runs EXACTLY ONCE (break at the bottom) → byte-identical.
                    while True:
                        # Per-attempt state. Round-entry already initialized these;
                        # we rebind fresh objects each attempt so a retry's pump
                        # gets a clean queue/sentinel/failure (the old attempt's
                        # abandoned queue is the D11 fence — late puts from the dead
                        # pump go to a queue we no longer drain). _a_parts /
                        # _a_tool_calls / _a_round_reasoning are reset so the re-run
                        # streams from scratch (paired with the C11 truncate below).
                        _a_parts = []
                        _a_tool_calls = []
                        _a_round_reasoning = ""
                        _a_queue = asyncio.Queue()
                        _a_sentinel = object()
                        _a_failure = {}
                        # D11 fence: holder for the live provider generator of the
                        # CURRENT attempt, so a retry can force-close the failed
                        # attempt's stream (no orphaned concurrent provider stream when
                        # the retry spawns a fresh pump). Re-bound per spawn below.
                        _pump_gen_holder: dict[str, object] = {}

                        def _pump_agentic(
                            q=_a_queue,
                            sentinel=_a_sentinel,
                            rnd=_agentic_round,
                            failure=_a_failure,
                            tool_defs=_round_tool_definitions,
                            epoch=_round_epoch,
                            gen_holder=_pump_gen_holder,
                            # Retry-identity (spec §4.7): bind the ONCE-per-round lean/
                            # full snapshot as a default arg so every attempt's pump
                            # captures byte-identical messages — never recompute lean.
                            round_base_messages=_round_base_messages,
                            # Fase 3 (S6/§11.2): bind the CURRENT (possibly failed-
                            # over) provider/model. Flag OFF → these equal run's own
                            # → byte-identical dispatch.
                            pump_provider=_active_provider,
                            pump_model=_active_model,
                            pump_temp=_agentic_temp,
                            pump_top_p=_agentic_top_p,
                            pump_tool_choice=_round_tool_choice,
                        ) -> None:
                            try:
                                _gen = _vf.stream_visible_followup(
                                    provider=pump_provider,
                                    model=pump_model,
                                    base_messages=round_base_messages,
                                    exchanges=_followup_exchanges,
                                    tool_definitions=tool_defs,
                                    round_index=rnd,
                                    thinking_mode=run.thinking_mode,
                                    temperature=pump_temp,
                                    top_p=pump_top_p,
                                    tool_choice=pump_tool_choice,
                                    run_id=run.run_id,
                                    autonomous=run.autonomous,
                                )
                                # Expose this attempt's generator so a retry can
                                # force-close it (D11). Keyed by epoch so a stale
                                # close from a superseded attempt is a no-op.
                                gen_holder[epoch] = _gen
                                for _event in _gen:
                                    loop.call_soon_threadsafe(q.put_nowait, _event)
                            except Exception as _ae:
                                # §11.4-finding: a RAISED transient drop (the PRIMARY
                                # cut class — most realistic socket-drop) is caught
                                # here and sets _a_failure WITHOUT firing
                                # note_round_failed, so the round failure was centrally
                                # SILENT (only the yielded-FollowupFailed path fired the
                                # nerve). Classify (B11 taxonomy = single retryability
                                # source) and fire the nerve so the raised socket-drop
                                # is no longer invisible. Self-safe: classification +
                                # nerve are wrapped, never throw back into the pump.
                                # NOTE: this only ADDS the nerve — break/retry behavior
                                # is unchanged (Fase 1 4.1 builds the retry loop later).
                                _err = str(_ae) or "unknown"
                                try:
                                    from core.services.stream_failure_kind import (
                                        classify_failure as _classify_fk,
                                    )
                                    _fk, _retry = _classify_fk(
                                        http_status=None, error_text=_err)
                                except Exception:
                                    _fk, _retry = "", False
                                failure.update(
                                    {
                                        "round": rnd + 1,
                                        "error": _err,
                                        "summary": f"followup-round-{rnd + 1}-provider-error: {_err}",
                                        "failure_kind": _fk,
                                        "http_status": None,
                                        "retryable": bool(_retry),
                                    }
                                )
                                try:
                                    from core.services import followup_observer as _fu_obs_raise
                                    _fu_obs_raise.note_round_failed(
                                        run.run_id, rnd + 1, run.provider, _err,
                                        failure_kind=_fk, retryable=bool(_retry),
                                        raised=True)
                                except Exception:
                                    pass
                            finally:
                                loop.call_soon_threadsafe(q.put_nowait, sentinel)

                        logger.info(
                            "agentic-followup-pump-start run_id=%s round=%d provider=%s model=%s "
                            "tools=%d tool_choice=%s",
                            run.run_id, _agentic_round + 1, run.provider, run.model,
                            len(_round_tool_definitions or []),
                            _round_tool_choice or "auto",
                        )
                        loop.run_in_executor(None, _pump_agentic)

                        # Mid-stream steer support: poll the queue with a short
                        # timeout so we can also check for steers between chunks.
                        # If a steer arrives mid-token, we abandon the in-flight
                        # provider call (executor thread completes in background;
                        # its later events go to a queue we no longer drain) and
                        # restart the next round with the steer in base_messages.
                        _round_start_t = time.monotonic()
                        # Watchdog has two clocks:
                        # - total round ceiling prevents endless provider calls
                        # - silence ceiling catches stalled streams while allowing
                        #   long rounds that keep producing deltas/tool calls.
                        _round_overall_timeout_s = float(_agentic_budget.get("round_total_timeout_s") or 300.0)
                        _round_silence_timeout_s = float(_agentic_budget.get("round_silence_timeout_s") or 180.0)
                        _last_provider_progress_t = _round_start_t
                        _fu_last_beat = _round_start_t  # keepalive under followup-model-vent
                        _mid_round_steers: list[dict[str, object]] = []
                        while True:
                            try:
                                _a_item = await asyncio.wait_for(_a_queue.get(), timeout=1.0)
                            except asyncio.TimeoutError:
                                _now_t = time.monotonic()
                                _watchdog_reason = _agentic_watchdog_timeout_reason(
                                    started_at=_round_start_t,
                                    last_progress_at=_last_provider_progress_t,
                                    now=_now_t,
                                    max_total_s=_round_overall_timeout_s,
                                    max_silence_s=_round_silence_timeout_s,
                                )
                                # Keepalive-heartbeat under followup-rundens model-vent
                                # (PROVIDER-AGNOSTISK idle-gap-fix, Bjørn 2026-06-23): first-
                                # pass havde keepalive, followup IKKE → enhver models TTFT/
                                # stille-vent gjorde SSE'en tavs → mobil/desk droppede
                                # forbindelsen → det (gemte) svar forsvandt. Nu dækket her
                                # ligesom first-pass. Hvert ~5s tavshed.
                                if not _watchdog_reason and (_now_t - _fu_last_beat) >= 5.0:
                                    _fu_last_beat = _now_t
                                    try:
                                        touch_active_visible_run(run.run_id)
                                    except Exception:
                                        pass
                                    yield _sse("heartbeat", {
                                        "type": "heartbeat",
                                        "run_id": run.run_id,
                                        "phase": "agentic_followup",
                                        "round": _agentic_round + 1,
                                    })
                                if _watchdog_reason:
                                    if not _a_failure:
                                        # D11: a silence/idle-timeout is a
                                        # provider_stall — NOT retryable on the same
                                        # provider (re-sampling just re-stalls). Tag
                                        # it explicitly so the Fase 1 retry-decision
                                        # routes it to the interruption path, never a
                                        # retry. failure_kind/retryable are the single
                                        # retryability source (B11).
                                        from core.services.stream_failure_kind import (
                                            FailureKind as _FK_stall,
                                        )
                                        _a_failure.update({
                                            "round": _agentic_round + 1,
                                            "error": f"{_watchdog_reason}: timed out waiting for provider stream item",
                                            "summary": f"agentic-round-{_agentic_round + 1}-{_watchdog_reason}",
                                            "failure_kind": _FK_stall.PROVIDER_STALL,
                                            "retryable": False,
                                        })
                                    break
                                # Check for mid-stream steers
                                try:
                                    _new_steers = consume_visible_run_steers(run.run_id)
                                except Exception:
                                    _new_steers = []
                                # Check for controller cancellation (Cancel button)
                                if controller.is_cancelled():
                                    _agentic_loop_exit_reason = "user-cancelled"
                                    _final_run_status = "interrupted"
                                    _final_run_error = "user-cancelled-during-agentic-loop"
                                    try:
                                        from core.services.agentic_checkpoints import save_checkpoint as _save_agentic_checkpoint
                                        _save_agentic_checkpoint(
                                            run_id=run.run_id,
                                            session_id=run.session_id,
                                            user_message=run.user_message,
                                            provider=run.provider,
                                            model=run.model,
                                            round_index=_agentic_round + 1,
                                            phase="user-cancelled",
                                            exchanges=_followup_exchanges,
                                            partial_text="".join(_all_followup_parts),
                                            exit_reason="user-cancelled",
                                        )
                                    except Exception:
                                        pass
                                    break
                                if _new_steers:
                                    _mid_round_steers.extend(_new_steers)
                                    yield _sse("steer_received", {
                                        "type": "steer_received",
                                        "run_id": run.run_id,
                                        "mid_stream": True,
                                        "count": len(_new_steers),
                                        "content": str(_new_steers[0].get("content") or "")[:200],
                                    })
                                    logger.info(
                                        "agentic-mid-stream-interrupt run_id=%s round=%d steers=%d",
                                        run.run_id, _agentic_round + 1, len(_new_steers),
                                    )
                                    break
                                continue
                            if _a_item is _a_sentinel:
                                break
                            _last_provider_progress_t = time.monotonic()
                            if isinstance(_a_item, _vf.FollowupDelta):
                                if _a_item.delta:
                                    _a_parts.append(_a_item.delta)
                                    _all_followup_parts.append(_a_item.delta)
                                    yield _sse("delta", {
                                        "type": "delta",
                                        "run_id": run.run_id,
                                        "delta": _a_item.delta,
                                    })
                                continue
                            if isinstance(_a_item, _vf.FollowupReasoningDelta):
                                # Live reasoning-trace (thinking-mode) → frontend viser
                                # et foldbart 'tænker…'-felt. Kun visning; persistens
                                # sker via reasoning_content i FollowupDone.
                                if _a_item.delta:
                                    _all_followup_reasoning_parts.append(_a_item.delta)
                                    yield _sse("reasoning_delta", {
                                        "type": "reasoning_delta",
                                        "run_id": run.run_id,
                                        "delta": _a_item.delta,
                                    })
                                continue
                            if isinstance(_a_item, _vf.FollowupToolCalls):
                                _a_tool_calls.extend(_a_item.tool_calls)
                                continue
                            if isinstance(_a_item, _vf.FollowupFailed):
                                # Carry the B11 structured taxonomy (failure_kind +
                                # http_status) forward — the single retryability source
                                # Fase 1's round-retry (4.1) will read. Both default
                                # ""/None so legacy adapters that don't populate them
                                # are unaffected.
                                _yk = getattr(_a_item, "failure_kind", "") or ""
                                _ys = getattr(_a_item, "http_status", None)
                                # Resolve retryability via the single source (B11)
                                # so the Fase 1 retry-decision can read it directly.
                                try:
                                    from core.services.stream_failure_kind import (
                                        is_retryable_kind as _is_retry_yk,
                                    )
                                    _yr = _is_retry_yk(_yk) if _yk else False
                                except Exception:
                                    _yr = False
                                _a_failure = {
                                    "round": _a_item.round_index + 1,
                                    "error": _a_item.error,
                                    "summary": _a_item.summary,
                                    "failure_kind": _yk,
                                    "http_status": _ys,
                                    "retryable": _yr,
                                }
                                # Followup-cluster: round-fejl synlig (copilot-400/thinking-bug).
                                try:
                                    from core.services import followup_observer as _fu_obs
                                    _fu_obs.note_round_failed(
                                        run.run_id, _a_item.round_index + 1,
                                        run.provider, str(_a_item.error or _a_item.summary or ""),
                                        failure_kind=_yk, http_status=_ys, raised=False)
                                except Exception:
                                    pass
                                continue
                            if isinstance(_a_item, _vf.FollowupDone):
                                if _a_item.text and not _a_parts:
                                    _a_parts.append(_a_item.text)
                                    _all_followup_parts.append(_a_item.text)
                                    yield _sse("delta", {
                                        "type": "delta",
                                        "run_id": run.run_id,
                                        "delta": _a_item.text,
                                    })
                                # Stash reasoning so the ToolExchange built below
                                # carries it forward to the next followup round.
                                _a_round_reasoning = str(_a_item.reasoning_content or "")
                                # Track for final persistence: hvis denne round
                                # produced reasoning, store it so we can replay
                                # it in the next session.
                                if _a_round_reasoning:
                                    _persist_reasoning = _a_round_reasoning
                                continue

                        # ── Fase 1 retry-decision (spec §4.1/C11/D11/E11) ────────
                        # The drain loop has ended for THIS attempt. Decide whether
                        # to RETRY the same round (preserving the turn) or break out
                        # to the existing post-drain handling (prose-redning, steer,
                        # tool-exec, or the interruption path). EVERYTHING here is
                        # gated behind the kill-switch: with it OFF we break
                        # immediately → the body ran exactly once → byte-identical.
                        try:
                            _retry_enabled = _vf.agentic_round_retry_enabled()
                        except Exception:
                            _retry_enabled = False
                        try:
                            _failover_enabled = _vf.provider_failover_enabled()
                        except Exception:
                            _failover_enabled = False
                        if not _a_failure:
                            # Success / clean round. Fase 3 (S6): record_success on the
                            # active provider so a transient blip earlier this turn
                            # closes the breaker. Gated so flag-OFF stays byte-identical.
                            if _retry_enabled or _failover_enabled:
                                try:
                                    from core.services import (
                                        provider_circuit_breaker as _cb_ok,
                                    )
                                    _cb_ok.pp_record_success(_active_provider)
                                except Exception:
                                    pass
                            break  # success / clean round → proceed (no retry).
                        if not _retry_enabled and not _failover_enabled:
                            break  # both kill-switches OFF → today's behavior.

                        # Classify via the structured failure_kind/retryable already
                        # attached to _a_failure (B11). provider_stall is NOT
                        # retryable (D11) on the SAME provider, but it DOES count
                        # toward opening the breaker (a stalling provider is failing).
                        _fk = str(_a_failure.get("failure_kind") or "")
                        _retryable = bool(_a_failure.get("retryable"))
                        if not _retryable and _fk:
                            try:
                                from core.services.stream_failure_kind import (
                                    is_retryable_kind as _is_retry_kind,
                                )
                                _retryable = _is_retry_kind(_fk)
                            except Exception:
                                _retryable = False

                        # ── Fase 3 (S6/§11.2): per-provider circuit-breaker ──────────
                        # Record this round failure against the ACTIVE provider's
                        # shared breaker. provider_stall counts too (a stalling
                        # provider is down). Then check: is the provider's breaker
                        # OPEN? If so, the provider is DEAD — do NOT retry-storm it;
                        # fail over (if enabled) or fall to graceful exhaustion.
                        _breaker_open = False
                        try:
                            from core.services import provider_circuit_breaker as _cb_fail
                            _cb_fail.pp_record_failure(_active_provider)
                            _breaker_open = _cb_fail.pp_is_open(_active_provider)
                        except Exception:
                            _breaker_open = False

                        # ── Provider failover (S6, REQUIRED) ─────────────────────────
                        # When the active provider is unavailable (breaker OPEN) we do
                        # NOT retry the same provider. If failover is enabled, we have
                        # NOT already failed over this turn, and a reliable fallback
                        # exists → rebind the active provider/model for the REST of the
                        # turn and re-sample (S3: tools are NOT re-executed — the pump
                        # re-uses _followup_exchanges unchanged). Emit a provider_failover
                        # nerve (from→to). One failover per turn → no infinite chain.
                        if _breaker_open and _failover_enabled and not _did_failover:
                            try:
                                _fo_target = _vf.pick_failover_target(
                                    _active_provider, _active_model)
                            except Exception:
                                _fo_target = None
                            if _fo_target is not None:
                                _fo_from_p, _fo_from_m = _active_provider, _active_model
                                _active_provider, _active_model = _fo_target
                                _did_failover = True
                                # Budget: a failover consumes a turn-retry slot so the
                                # whole turn stays bounded even if the fallback also dies.
                                _turn_total_retries += 1
                                # Observe the failover edge to the Central (stream).
                                try:
                                    from core.services.central_core import (
                                        central as _central_fo,
                                    )
                                    _central_fo().observe({
                                        "cluster": "stream",
                                        "nerve": "provider_failover",
                                        "run_id": str(run.run_id or ""),
                                        "round": _agentic_round + 1,
                                        "from_provider": str(_fo_from_p or ""),
                                        "from_model": str(_fo_from_m or ""),
                                        "to_provider": str(_active_provider or ""),
                                        "to_model": str(_active_model or ""),
                                        "failure_kind": _fk,
                                    })
                                except Exception:
                                    pass
                                logger.warning(
                                    "provider-failover run_id=%s round=%d %s/%s -> %s/%s "
                                    "(breaker open, kind=%s)",
                                    run.run_id, _agentic_round + 1, _fo_from_p,
                                    _fo_from_m, _active_provider, _active_model, _fk,
                                )
                                # Emit a visible failover signal so desk/mobile can
                                # surface "switched to a backup provider".
                                yield _sse("provider_failover", {
                                    "type": "provider_failover",
                                    "run_id": run.run_id,
                                    "round": _agentic_round + 1,
                                    "to_provider": str(_active_provider or ""),
                                })
                                # C11: discard the failed attempt's partial before the
                                # fallback re-streams fresh deltas (same contract as a
                                # round-retry). Then re-enter the attempt loop on the
                                # NEW provider — no same-provider retry-storm.
                                try:
                                    _dead_gen_fo = _pump_gen_holder.get(_round_epoch)
                                    if _dead_gen_fo is not None and hasattr(
                                            _dead_gen_fo, "close"):
                                        _dead_gen_fo.close()
                                except Exception:
                                    pass
                                _round_epoch += 1
                                del _all_followup_parts[_round_partial_snapshot:]
                                yield _sse("round_restart_discard_partial", {
                                    "type": "round_restart_discard_partial",
                                    "run_id": run.run_id,
                                    "round": _agentic_round + 1,
                                })
                                continue  # re-sample this round on the fallback provider.

                        # Breaker OPEN but no failover available (flag off / already
                        # failed over / no target) → the active provider is dead and
                        # we have nowhere to go. Force exhaustion: do NOT retry-storm
                        # a known-dead provider. _retryable→False routes us into the
                        # graceful-degrade exhaustion path below (checkpointed partial
                        # + honest note + interruption nerve — never a blank loss).
                        if _breaker_open:
                            _retryable = False

                        # Budget checks (E11/S2/P6): per-round cap, hard turn-total
                        # retry cap, and a turn wall-clock deadline. Any exhaustion →
                        # graceful-degrade (emit checkpointed partial + honest note)
                        # then fall to the interruption path — NEVER an empty loss.
                        _under_round_budget = _round_retry_count < _round_stream_max_retries
                        _under_turn_budget = _turn_total_retries < _turn_total_retry_cap
                        _under_wall_clock = (
                            time.monotonic() - _turn_started_at) < _turn_wall_clock_cap_s
                        # Same-provider retry requires the round-retry kill-switch ON.
                        # (With only failover enabled, a non-failover-able failure must
                        # NOT trigger same-provider retries — flag isolation.)
                        _can_retry = (
                            _retry_enabled and _retryable and _under_round_budget
                            and _under_turn_budget and _under_wall_clock)

                        if not _can_retry:
                            # Exhausted (or non-retryable). If we DID retry at least
                            # once and ran out of budget, mark it exhausted so the
                            # Central can see retry merely deferred the death (S7).
                            if _retryable and _round_retry_count > 0:
                                _exhaust_reason = (
                                    "round-budget" if not _under_round_budget
                                    else "turn-budget" if not _under_turn_budget
                                    else "wall-clock")
                                try:
                                    from core.services import followup_observer as _fu_ex
                                    _fu_ex.note_round_retry(
                                        run.run_id, _agentic_round + 1,
                                        _round_retry_count,
                                        str(_a_failure.get("summary") or _fk),
                                        outcome="exhausted",
                                        failure_kind=_fk, reason_detail=_exhaust_reason)
                                except Exception:
                                    pass
                                # P6 graceful-degrade: surface the checkpointed
                                # partial (already in _all_followup_parts, NOT
                                # truncated on the exhausting attempt) + an honest
                                # note so the user never gets a blank loss. The
                                # interruption nerve still fires below.
                                _exhaust_note = (
                                    "\n\n_(Forbindelsen blev ved med at glippe — "
                                    "jeg prøvede igen et par gange men måtte give op. "
                                    "Her er hvad jeg nåede; sig til, så fortsætter jeg.)_")
                                _a_parts.append(_exhaust_note)
                                _all_followup_parts.append(_exhaust_note)
                                yield _sse("delta", {
                                    "type": "delta",
                                    "run_id": run.run_id,
                                    "delta": _exhaust_note,
                                })
                            break  # → existing interruption path (with partial intact).

                        # ── We WILL retry this round ─────────────────────────────
                        _round_retry_count += 1
                        _turn_total_retries += 1
                        _attempt_no = _round_retry_count

                        # D11 pump-fence: force-close the failed attempt's provider
                        # generator so there is no orphaned concurrent provider
                        # stream when we spawn a fresh pump. The dead pump's late
                        # queue puts target _a_queue, which we REBIND at the top of
                        # the next iteration → they go to a queue we no longer drain
                        # (the epoch is realized as a fresh queue + bumped token).
                        try:
                            _dead_gen = _pump_gen_holder.get(_round_epoch)
                            if _dead_gen is not None and hasattr(_dead_gen, "close"):
                                _dead_gen.close()  # force-close provider socket/stream
                        except Exception:
                            pass
                        _round_epoch += 1  # bump fence token (stale puts ignored)

                        # C11 partial-discard: truncate _all_followup_parts back to
                        # the round-entry snapshot so the partial text streamed by the
                        # FAILED attempt is discarded (the re-run streams fresh deltas;
                        # without this we double-emit/double-persist on the exact
                        # "thinks-a-bit-BANG" case). Emit a typed SSE so desk/mobile
                        # reducers discard the on-screen partial for this run.
                        #
                        # CLIENT CONTRACT — `round_restart_discard_partial`:
                        #   { type, run_id, round } → on receipt the client MUST drop
                        #   any not-yet-finalized streamed delta text for this run's
                        #   CURRENT round and await fresh deltas. It is advisory: a
                        #   client that ignores it stays correct because the SERVER's
                        #   persisted answer (_all_followup_parts) is already truncated;
                        #   only the live on-screen partial would briefly duplicate.
                        del _all_followup_parts[_round_partial_snapshot:]
                        yield _sse("round_restart_discard_partial", {
                            "type": "round_restart_discard_partial",
                            "run_id": run.run_id,
                            "round": _agentic_round + 1,
                        })

                        # S3 invariant: a retry RE-SAMPLES the model ONLY. The
                        # sampling failure occurs BEFORE this round's tools run (tool
                        # execution is below the `if _a_failure: break` post-drain
                        # block, ~line 2660), so _followup_exchanges is unchanged and
                        # NO tool is ever re-executed on the retry path. The re-run
                        # sends byte-identical messages (same base_messages + same
                        # _followup_exchanges snapshot, same tool_defs decision).

                        # Backoff with jitter (shared single-source helper, S4/§11.2).
                        # Keepalive keeps flowing DURING backoff (no silent gap): emit
                        # a "Reconnecting" signal + heartbeats while we wait.
                        try:
                            from core.services.stream_failure_kind import (
                                compute_backoff_with_jitter as _backoff_fn,
                            )
                            _backoff_s = _backoff_fn(_round_retry_count - 1)
                        except Exception:
                            _backoff_s = min(0.6 * (2 ** (_round_retry_count - 1)), 8.0)

                        # note_round_retry(recovered) is fired AFTER the next attempt
                        # succeeds; here we emit the visible "Reconnecting n/m" signal.
                        yield _sse("retry", {
                            "type": "retry",
                            "run_id": run.run_id,
                            "round": _agentic_round + 1,
                            "attempt": _attempt_no,
                            "max_attempts": _round_stream_max_retries,
                            "failure_kind": _fk,
                            "message": (
                                f"Reconnecting runde {_agentic_round + 1}, "
                                f"forsøg {_attempt_no}/{_round_stream_max_retries}"),
                        })
                        logger.warning(
                            "agentic-round-retry run_id=%s round=%d attempt=%d/%d "
                            "kind=%s turn_total=%d backoff=%.1fs",
                            run.run_id, _agentic_round + 1, _attempt_no,
                            _round_stream_max_retries, _fk, _turn_total_retries,
                            _backoff_s,
                        )
                        # Sleep in short slices so the keepalive heartbeat keeps the
                        # SSE alive during backoff (S4: backoff must not reintroduce a
                        # silent gap that drops mobile/desk sockets).
                        _bo_deadline = time.monotonic() + max(0.0, _backoff_s)
                        while True:
                            _remaining = _bo_deadline - time.monotonic()
                            if _remaining <= 0:
                                break
                            await asyncio.sleep(min(_remaining, 4.0))
                            try:
                                touch_active_visible_run(run.run_id)
                            except Exception:
                                pass
                            yield _sse("heartbeat", {
                                "type": "heartbeat",
                                "run_id": run.run_id,
                                "phase": "agentic_round_retry_backoff",
                                "round": _agentic_round + 1,
                                "attempt": _attempt_no,
                            })
                        # Stash the attempt number so the NEXT successful drain can
                        # fire note_round_retry(recovered).
                        _pending_recovered_attempt = _attempt_no
                        continue  # re-enter the attempt loop → re-sample this round.

                    # If we got here via a successful retry (the attempt that just
                    # broke out had no failure but a prior attempt retried), fire the
                    # recovered nerve (S7) so the Central sees retry actually rescued
                    # the turn. Only when the final attempt SUCCEEDED (no _a_failure).
                    if (not _a_failure) and locals().get("_pending_recovered_attempt"):
                        try:
                            from core.services import followup_observer as _fu_rec
                            _fu_rec.note_round_retry(
                                run.run_id, _agentic_round + 1,
                                int(_pending_recovered_attempt), "",
                                outcome="recovered", provider=run.provider)
                        except Exception:
                            pass
                        _pending_recovered_attempt = 0

                    # ── Prosa-tool-call-redning (followup, tool-leak-fix 2026-06-21) ──
                    # deepseek-v4-flash narrer nogle gange tool-kald som prosa i
                    # followup-runder ([navn]: {json}) i stedet for strukturerede kald.
                    # Konvertér dem til ægte kald så denne runde EKSEKVERER dem (i stedet
                    # for at behandle teksten som det endelige svar og lække/blokere).
                    if not _a_tool_calls and _a_parts:
                        try:
                            from core.services.prose_tool_calls import extract_prose_tool_calls
                            from core.tools.simple_tools import _TOOL_HANDLERS as _ptc_handlers_fu
                            _fu_cleaned, _fu_calls = extract_prose_tool_calls(
                                "".join(_a_parts), _ptc_handlers_fu.keys(),
                            )
                            if _fu_calls:
                                _a_tool_calls.extend(_fu_calls)
                                _a_parts[:] = [_fu_cleaned] if _fu_cleaned else []
                                logger.warning(
                                    "prose-tool-call-redning (followup r%d): konverterede "
                                    "%d prosa-kald run_id=%s",
                                    _agentic_round + 1, len(_fu_calls), run.run_id,
                                )
                        except Exception as _fu_ptc_exc:
                            logger.debug("prose-tool-call-parse (followup) fejlede: %s", _fu_ptc_exc)

                    # If mid-round steers landed, inject them as user messages
                    # and skip tool execution this round — the LLM call was
                    # abandoned mid-token; we'll re-enter the loop with the
                    # steer added so the next round picks up where we steered.
                    if _mid_round_steers:
                        for s in _mid_round_steers:
                            content = str(s.get("content") or "").strip()
                            if not content:
                                continue
                            base_messages.append({"role": "user", "content": content})
                            stop_words = ("stop", "stop.", "cancel", "afbryd", "abort", "stop nu")
                            if content.strip().lower() in stop_words:
                                _agentic_loop_exit_reason = "user-steer-stop-mid-stream"
                                break
                        # Record the abandoned partial as an empty exchange so
                        # the next prompt has a clean slate (no half-tool-calls
                        # leaked into the followup history).
                        _followup_exchanges.append(
                            _vf.ToolExchange(
                                text=_exchange_text(),
                                tool_calls=[], results=[],
                            )
                        )
                        try:
                            _save_agentic_checkpoint(
                                run_id=run.run_id,
                                session_id=run.session_id,
                                user_message=run.user_message,
                                provider=run.provider,
                                model=run.model,
                                round_index=_agentic_round + 1,
                                phase="mid-round-steer",
                                exchanges=_followup_exchanges,
                                partial_text="".join(_all_followup_parts),
                                exit_reason=_agentic_loop_exit_reason,
                            )
                        except Exception:
                            pass
                        if _agentic_loop_exit_reason == "user-steer-stop-mid-stream":
                            break
                        continue  # re-enter for-loop next round

                    if _a_failure:
                        _failure_summary = str(_a_failure.get("summary") or "agentic-round-provider-error")
                        _interruption = {
                            "run_id": run.run_id,
                            "lane": run.lane,
                            "provider": run.provider,
                            "model": run.model,
                            "phase": "agentic-round",
                            "round": int(_a_failure.get("round") or (_agentic_round + 1)),
                            **_classify_visible_run_interruption(str(_a_failure.get("error") or _failure_summary)),
                            "error": str(_a_failure.get("error") or ""),
                            "summary": _failure_summary,
                        }
                        _update_visible_execution_trace(
                            run,
                            {
                                "provider_second_pass_status": "failed",
                                "provider_error_summary": _failure_summary,
                                "provider_call_count": max(
                                    int((get_last_visible_execution_trace() or {}).get("provider_call_count") or 1),
                                    _agentic_round + 2,
                                ),
                            },
                        )
                        event_bus.publish(
                            "runtime.visible_run_interrupted",
                            _interruption,
                        )
                        # Unified fejl-system (2026-06-23): ÉN konsistent bruger-vendt fejl
                        # i stedet for tavst-hæng. Centralen mapper reason→envelope, gør den
                        # sporbar (user_error pr. correlation_id) og leverer samme form til
                        # desk (synkron system_event her) som companion/UI får. Self-safe.
                        try:
                            from core.services import central_error_envelope as _cee
                            _env = _cee.for_interruption(
                                reason=str(_interruption.get("interruption_reason") or "runtime-error"),
                                run_id=run.run_id,
                                detail=str(_interruption.get("error") or ""))
                            _cee.emit(_env, session_id=run.session_id)
                            yield _sse("error", _env.to_client_event())
                        except Exception:
                            pass
                        try:
                            from core.services.in_flight_runs import mark_interrupted
                            mark_interrupted(
                                run.run_id,
                                reason=str(_interruption.get("interruption_reason") or "provider-error"),
                                summary=_failure_summary,
                            )
                        except Exception:
                            pass
                        _final_run_status = "interrupted"
                        _final_run_error = str(_interruption.get("error") or _failure_summary)
                        _agentic_loop_exit_reason = f"interrupted:{_failure_summary}"
                        try:
                            _save_agentic_checkpoint(
                                run_id=run.run_id,
                                session_id=run.session_id,
                                user_message=run.user_message,
                                provider=run.provider,
                                model=run.model,
                                round_index=_agentic_round + 1,
                                phase="interrupted",
                                exchanges=_followup_exchanges,
                                partial_text="".join(_all_followup_parts),
                                exit_reason=_failure_summary,
                            )
                        except Exception:
                            pass
                        break

                    # ── Check for user cancellation (Cancel button) ──
                    if controller.is_cancelled():
                        _agentic_loop_exit_reason = "user-cancelled"
                        _final_run_status = "interrupted"
                        _final_run_error = "user-cancelled-during-agentic-loop"
                        try:
                            from core.services.agentic_checkpoints import save_checkpoint as _save_agentic_checkpoint
                            _save_agentic_checkpoint(
                                run_id=run.run_id,
                                session_id=run.session_id,
                                user_message=run.user_message,
                                provider=run.provider,
                                model=run.model,
                                round_index=_agentic_round + 1,
                                phase="user-cancelled",
                                exchanges=_followup_exchanges,
                                partial_text="".join(_all_followup_parts),
                                exit_reason="user-cancelled",
                            )
                        except Exception:
                            pass
                        break

                    if not _a_tool_calls:
                        # Tvungen synthese-pause: tools var fjernet, så manglende
                        # tool-kald betyder "Jarvis opsummerede" — IKKE "færdig". Løft
                        # pausen, nulstil spiral-tælleren og fortsæt med tools igen, så
                        # han kan grave videre hvis opgaven kræver det.
                        if _round_was_synth_pause and not _is_last_round:
                            _tool_pause_active = False
                            _consecutive_tool_only_rounds = 0
                            _consecutive_empty_text_rounds = 0
                            continue
                        # ── HOLLOW-PROMISE-VAGT (4. jul, flag-gated, fail-open) ──
                        # Modellen lovede imminent handling ("jeg kører nu") men kaldte NUL
                        # værktøj hele runnet → giv ÉN nudge-runde ("gør det nu eller sig
                        # hvorfor"), cap 1. Ved enhver tvivl/fejl → normal break (byte-identisk).
                        try:
                            from core.services.hollow_promise_guard import (
                                hollow_promise_guard_enabled, is_hollow_promise,
                                HOLLOW_PROMISE_NUDGE,
                            )
                            if (
                                not _is_last_round
                                and not _hollow_promise_nudged
                                and hollow_promise_guard_enabled()
                                and is_hollow_promise(
                                    final_text="".join(_a_parts),
                                    total_tool_calls=sum(
                                        len(getattr(_ex, "tool_calls", []) or [])
                                        for _ex in _followup_exchanges),
                                    user_message=run.user_message,
                                    nudged_already=_hollow_promise_nudged,
                                )
                            ):
                                _hollow_promise_nudged = True
                                _run_degenerated = True  # harness model-trust: hollow promise
                                _followup_exchanges.append(
                                    _vf.ToolExchange(
                                        text=_exchange_text(), tool_calls=[], results=[]))
                                base_messages.append(
                                    {"role": "user", "content": HOLLOW_PROMISE_NUDGE})
                                try:
                                    from core.services import followup_observer as _fu_hp
                                    _fu_hp.note_hollow_promise(
                                        run.run_id, provider=run.provider, model=run.model,
                                        round_index=_agentic_round + 1,
                                        session_id=run.session_id)
                                except Exception:
                                    pass
                                continue  # tving ÉN mere runde med nudge'en
                        except Exception:
                            pass  # fail-open → normal break nedenfor
                        # No more tool calls — this round produced the final response.
                        break

                    # Track text-empty rounds. Some models (notably big-pickle
                    # via OpenCode) keep emitting tool calls without ever
                    # producing user-visible text, ballooning the prompt
                    # past 200k chars over 30+ rounds. Force-stop after
                    # _MAX_EMPTY_TEXT_ROUNDS in a row so the user gets at
                    # least the last partial text instead of a stalled stream.
                    _round_text_total = sum(len(p) for p in _a_parts)
                    if _round_text_total == 0:
                        _consecutive_empty_text_rounds += 1
                        if _consecutive_empty_text_rounds >= _MAX_EMPTY_TEXT_ROUNDS:
                            _update_visible_execution_trace(
                                run,
                                {
                                    "agentic_loop_terminated_reason": (
                                        f"early-exit-{_MAX_EMPTY_TEXT_ROUNDS}-empty-text-rounds"
                                    ),
                                    "agentic_loop_rounds_completed": _agentic_round + 1,
                                },
                            )
                            _empty_guard_msg = (
                                f"⚠ I ran {_MAX_EMPTY_TEXT_ROUNDS} rounds without producing text. "
                                "Something went wrong — try again."
                            )
                            yield _sse("delta", {
                                "type": "delta",
                                "run_id": run.run_id,
                                "delta": _empty_guard_msg,
                            })
                            _a_parts.append(_empty_guard_msg)
                            break
                    else:
                        _consecutive_empty_text_rounds = 0

                    # ── Tool-only loop guard: count rounds with tool calls
                    # but minimal visible text. This catches the "digging
                    # without delivering" pattern where each round has a
                    # few chars (resetting empty-text) but no real answer. ──
                    if _a_tool_calls and _round_text_total < _TOOL_ONLY_TEXT_THRESHOLD:
                        _consecutive_tool_only_rounds += 1
                        # Eskalerende synthese-pause: efter N tavse tool-runder, tving
                        # ÉN runde uden tools → Jarvis MÅ opsummere det han har fundet.
                        # Fyrer kun én gang pr. spiral (genarmeres når han skriver tekst
                        # → _consecutive_tool_only_rounds nulstilles på linje ~2191).
                        if (
                            _consecutive_tool_only_rounds >= _SYNTH_PAUSE_AFTER
                            and not _tool_pause_active
                            and _agentic_round - _synth_pause_fired_at > 1
                        ):
                            _tool_pause_active = True
                            _synth_pause_fired_at = _agentic_round
                            logger.info(
                                "synth-pause run_id=%s efter %d tavse tool-runder — "
                                "fjerner tools i næste runde for at tvinge opsummering",
                                run.run_id, _consecutive_tool_only_rounds,
                            )

                    # ── Decision-signals evaluation (2026-05-07) ──
                    # Replaces the hardcoded loop-nudge with registry-based
                    # decision triggers. Each fired decision becomes a chat
                    # delta visible in the conversation; Jarvis sees it via
                    # _a_parts in the next round's context. Killswitch:
                    # RuntimeSettings.decision_signals_enabled.
                    try:
                        # Lazy import to ensure registry is populated
                        import core.services.decision_triggers  # noqa: F401
                        from core.services.decision_signals import (
                            build_trigger_context, evaluate_decision_triggers,
                        )
                        # Aggregate recent tool calls across all rounds
                        _ds_recent_calls: list[dict] = []
                        for _ex in _followup_exchanges:
                            _ds_recent_calls.extend(list(_ex.tool_calls or []))
                        _ds_recent_calls = _ds_recent_calls[-5:]
                        # Recent assistant text from current round
                        _ds_recent_text = "".join(_a_parts)[-2000:]
                        _ds_ctx = build_trigger_context(
                            user_message=run.user_message,
                            session_id=run.session_id,
                            run_id=run.run_id,
                            consecutive_tool_only_rounds=_consecutive_tool_only_rounds,
                            recent_tool_calls=_ds_recent_calls,
                            recent_assistant_text=_ds_recent_text,
                            agentic_round_seq=_agentic_round + 1,
                        )
                        _ds_fired = evaluate_decision_triggers(_ds_ctx)
                        # Commit-cluster instrument: decision_signals → central observe
                        try:
                            from core.services.central_core import central as _central_ds
                            _central_ds().observe({
                                "cluster": "commit", "nerve": "decision_signals",
                                "run_id": run.run_id, "fired": len(_ds_fired or []),
                            })
                        except Exception:
                            pass
                        # EFEMER (2026-07-04 runaway-fix): reset pr. runde, så kun DENNE
                        # rundes fyringer injiceres i rundens exchange-tekst. Går ALDRIG
                        # i _a_parts (persist + resolution-tjek læser den ren) → dræber
                        # den self-poisoning løkke der bloatede svaret til 20k tegn.
                        _ds_active.clear()
                        for _ds_f in _ds_fired:
                            _ds_msg = _dss.compose_signal_note(
                                _ds_f.decision_id, _ds_f.trigger_name, _ds_f.context_summary,
                            )
                            # dedup pr. decision-id + cap → aldrig akkumulering.
                            _dss.stage_signal(_ds_active, _ds_f.decision_id, _ds_msg)
                            # Ikke-content SSE-event: aldrig i den synlige besked-buffer;
                            # ukendt event ignoreres harmløst af klienten (kan blive chip).
                            yield _sse("decision_signal", {
                                "type": "decision_signal",
                                "run_id": run.run_id,
                                "decision_id": _ds_f.decision_id,
                                "trigger": _ds_f.trigger_name,
                                "summary": _ds_f.context_summary,
                            })
                            logger.info(
                                "decision_signal_emitted run_id=%s decision=%s trigger=%s",
                                run.run_id, _ds_f.decision_id, _ds_f.trigger_name,
                            )
                            # 2026-05-07: loop_nudge is now SOFT — just a
                            # reminder via decision_signal-prompt. Tool-pause
                            # was originally coupled to it, but this removed
                            # Jarvis' agency on legitimate deep investigations
                            # (4-module-port, debug-sessions often need 10+
                            # tool-calls). Hard brake at _MAX_TOOL_ONLY_ROUNDS
                            # is still the safety-net if he spins out.
                            # if _ds_f.trigger_name == "loop_nudge_5_rounds":
                            #     _tool_pause_active = True
                    except Exception as _ds_exc:
                        logger.warning(
                            "decision_signal evaluation failed run_id=%s: %s",
                            run.run_id, _ds_exc,
                        )

                    if _a_tool_calls and _round_text_total < _TOOL_ONLY_TEXT_THRESHOLD:
                        if _consecutive_tool_only_rounds >= _MAX_TOOL_ONLY_ROUNDS:
                            logger.info(
                                "tool-only-loop-guard run_id=%s rounds=%d threshold=%d — forcing text response",
                                run.run_id, _consecutive_tool_only_rounds, _MAX_TOOL_ONLY_ROUNDS,
                            )
                            _update_visible_execution_trace(
                                run,
                                {
                                    "agentic_loop_terminated_reason": (
                                        f"early-exit-{_MAX_TOOL_ONLY_ROUNDS}-tool-only-rounds"
                                    ),
                                    "agentic_loop_rounds_completed": _agentic_round + 1,
                                },
                            )
                            # Yield a visible text message so the user always sees
                            # something in chat instead of "[Tool calls only]".
                            _guard_msg = (
                                "⚠ Jeg faldt i et tool-call loop — "
                                f"{_consecutive_tool_only_rounds} runder uden synligt svar. "
                                "Her er hvad jeg fandt:"
                            )
                            yield _sse("delta", {
                                "type": "delta",
                                "run_id": run.run_id,
                                "delta": _guard_msg,
                            })
                            _a_parts.append(_guard_msg)
                            break
                    else:
                        _consecutive_tool_only_rounds = 0
                        _tool_pause_active = False  # model produced text, lift the pause

                    # ── Execute tools for this agentic round ───────────────────────
                    _a_exec_start = time.monotonic()
                    logger.info(
                        "agentic-tools-execute-start run_id=%s round=%d tool_count=%d names=%s",
                        run.run_id, _agentic_round + 1, len(_a_tool_calls),
                        [str((tc.get("function") or {}).get("name") or tc.get("name") or "?")
                         for tc in _a_tool_calls][:6],
                    )
                    # ── Reasoning interceptor: observe this round's reasoning between the model's
                    #    thought and its tool execution — the pre-action moment. Bounded (800ms) +
                    #    fail-open → can never block or break the loop. Only runs on rounds that call
                    #    tools. DEFAULT SHADOW: the correction is only surfaced when the owner has
                    #    EXPLICITLY flipped the per-grade gate_enforce flag (default OFF), so until
                    #    then the result changes nothing. Active correction injects ONLY into the
                    #    ephemeral _ds_active (→ next round's exchange-text via _exchange_text()),
                    #    never _a_parts and never the cached prefix. Active RED additionally holds the
                    #    pending tool-calls (empties the list → executor runs zero tools) so the model
                    #    re-reasons with the correction — never cancels/finalizes the run. Runs BEFORE
                    #    run_tool_batch so a physical hold empties the batch the pump announces+runs.
                    try:
                        from core.services.reasoning_interceptor import (
                            intercept_round_async, should_hold_tool_call,
                        )
                        _ri_reasoning = "".join(_all_followup_reasoning_parts)[-4000:]
                        if _ri_reasoning.strip():
                            _ri_out = await intercept_round_async(
                                run_id=run.run_id, round_num=_agentic_round + 1,
                                reasoning_text=_ri_reasoning,
                                tool_calls_this_run=(_a_tool_calls if isinstance(_a_tool_calls, list) else []),
                                ctx={"session_id": getattr(run, "session_id", "") or "",
                                     "reasoning_tier": getattr(run, "thinking_mode", "fast") or "fast"},
                                budget_ms=800,
                            )
                            if _ri_out is not None and not _ri_out.shadow and _ri_out.correction:
                                _ri_trig = _ri_out.triggers[0] if _ri_out.triggers else "reasoning"
                                _dss.stage_signal(
                                    _ds_active, f"interceptor:{_agentic_round + 1}",
                                    _dss.compose_signal_note("interceptor", _ri_trig, _ri_out.correction))
                                if should_hold_tool_call(_ri_out):
                                    _a_tool_calls = []  # physical hold: executor runs zero tools
                    except Exception:
                        pass

                    _run_stage = f"agentic_tool_exec_r{_agentic_round + 1}"
                    # ── Announce → execute → heartbeat pump (extracted to visible_tool_exec,
                    #    Boy-Scout 2026-07-19). Announces each tool as a working_step,
                    #    re-asserts the load-bearing ContextVars (session_id/scope/override)
                    #    VERBATIM before copy_context, runs the batch in a worker thread with a
                    #    15s keepalive heartbeat, and — when run.local_tool_exec — registers
                    #    each call with the broker + emits a first-class tool_call so the
                    #    jarvis-code client runs it locally. exec_start pinned to _a_exec_start
                    #    so the end-logger duration_ms below matches the pre-extraction block.
                    _a_batch_out: dict = {}
                    async for _frame in run_tool_batch(
                        _a_tool_calls,
                        run=run, loop=loop, tool_scope=tool_scope,
                        step_counter=_step_counter,
                        heartbeat_interval_s=15.0,
                        heartbeat_phase="agentic_tools",
                        heartbeat_extra={"round": _agentic_round + 1},
                        out=_a_batch_out,
                        exec_start=_a_exec_start,
                    ):
                        yield _frame
                    _a_results = _a_batch_out["results"]
                    _step_counter = _a_batch_out["step_counter"]
                    logger.info(
                        "agentic-tools-execute-end run_id=%s round=%d duration_ms=%d results=%d",
                        run.run_id, _agentic_round + 1,
                        int((time.monotonic() - _a_exec_start) * 1000),
                        len(_a_results),
                    )
                    # ── LAG 3: result-aware no-progress-detektor (Bjørn 4. jul) ──────
                    # Byg rundens signatur = {(tool, args, result)} og sammenlign med
                    # forrige runde. Identisk → INTET nyt lært (modellen spinner på samme
                    # forespørgsel). Også: ALLE resultater duplicate_suppressed = ren
                    # gentagelse. To sådanne runder i træk → tving finalize næste runde
                    # (forskning: same tool+args+output ×N = stall; result-aware for ikke
                    # at dræbe legitim polling der får SKIFTENDE svar). Nerve gør det synligt.
                    try:
                        import hashlib as _hp
                        _sig_items = set()
                        _all_dup = bool(_a_results)
                        for _rr in (_a_results or []):
                            _rn = str(_rr.get("tool_name") or "")
                            _ra = json.dumps(_rr.get("arguments") or {}, sort_keys=True, ensure_ascii=False)
                            _rt = str(_rr.get("result_text") or "")[:600]
                            if str(_rr.get("status") or "") != "duplicate_suppressed":
                                _all_dup = False
                            _sig_items.add((_rn, _hp.sha1(_ra.encode()).hexdigest(),
                                            _hp.sha1(_rt.encode()).hexdigest()))
                        _round_sig = frozenset(_sig_items)
                        _no_new = bool(_round_sig) and (
                            _all_dup or _round_sig == _prev_round_sig)
                        if _no_new:
                            _no_progress_rounds += 1
                        else:
                            _no_progress_rounds = 0
                        _prev_round_sig = _round_sig
                        if _no_progress_rounds >= _MAX_NO_PROGRESS and not _force_finalize_next:
                            _force_finalize_next = True
                            _run_degenerated = True  # harness model-trust: no-progress spin
                            try:
                                from core.services.central_core import central as _central_np
                                _central_np().observe({
                                    "cluster": "loop", "nerve": "no_progress_finalize",
                                    "run_id": str(run.run_id or ""), "provider": str(run.provider or ""),
                                    "model": str(run.model or ""), "round": _agentic_round + 1,
                                    "no_progress_rounds": _no_progress_rounds,
                                    "all_duplicate": _all_dup,
                                })
                            except Exception:
                                pass
                            # DURABLE MIRROR (oneiric grounding): observe() ovenfor er
                            # restart-flygtig (in-memory trace). Spejl NUMERATOREN til den
                            # durable per-nerve tidsserie så central_oneiric_sampler kan
                            # ground'e/falsificere oneiriske hypoteser før TTL. Additiv,
                            # self-safe, ændrer ALDRIG loop-adfærd.
                            try:
                                from datetime import UTC as _UTC, datetime as _dt
                                from core.services import central_timeseries as _cts
                                _cts.record("loop", "no_progress_finalize", 1.0,
                                            meta={"day": _dt.now(_UTC).date().isoformat()})
                            except Exception:
                                pass
                    except Exception:
                        pass
                    # 2026-06-11 (Bjørn frustration crisis fix B): hvis dette
                    # er en Discord-session, send live tool-progress til
                    # Discord-kanalen så brugeren ser hvad Jarvis arbejder på
                    # i stedet for total stilhed. Throttled til 1/15s for
                    # at undgå spam.
                    try:
                        if run.session_id:
                            from core.services.discord_gateway import (
                                get_discord_channel_for_session,
                                send_discord_message,
                            )
                            _dc_channel = get_discord_channel_for_session(run.session_id)
                            if _dc_channel:
                                _last_status_at = getattr(
                                    controller, "_last_discord_status_at", 0.0,
                                )
                                _now_mono = time.monotonic()
                                if _now_mono - _last_status_at >= 15.0:
                                    _names = [
                                        str((tc.get("function") or {}).get("name") or "?")
                                        for tc in _a_tool_calls[:3]
                                    ]
                                    _names_str = ", ".join(_names)
                                    if len(_a_tool_calls) > 3:
                                        _names_str += f" (+{len(_a_tool_calls) - 3} flere)"
                                    _status_text = (
                                        f"🔧 Runde {_agentic_round + 1}: "
                                        f"{_names_str} — fortsætter..."
                                    )
                                    send_discord_message(_dc_channel, _status_text)
                                    controller._last_discord_status_at = _now_mono  # type: ignore[attr-defined]
                    except Exception as _dc_exc:
                        logger.debug(
                            "discord-progress-status fejl run_id=%s: %s",
                            run.run_id, _dc_exc,
                        )
                    # If any tool call this round was load_more_tools, capture
                    # its added names so the next round's tool_definitions
                    # includes them.
                    for _lm_sr in _a_results:
                        try:
                            if str(_lm_sr.get("tool_name") or "") != "load_more_tools":
                                continue
                            _lm_added = (_lm_sr.get("result") or {}).get("added") or []
                            for _lm_n in _lm_added:
                                if _lm_n and _lm_n not in _round_extra_tools:
                                    _round_extra_tools.append(str(_lm_n))
                        except Exception:
                            pass
                    # App-self-control (rod-fix 2026-06-30): emit app_action_request OGSÅ
                    # for tools kaldt i en AGENTISK runde (ikke kun first-pass-stien ~1734).
                    # Før manglede den her → request_app_action kaldt EFTER ræsonnering/andre
                    # tool-kald (en senere runde) returnerede ok, men desk fik aldrig kortet.
                    for _app_sr in _a_results:
                        try:
                            from core.tools.app_control_tool import build_app_action_event
                            _app_ev = build_app_action_event(
                                _app_sr.get("result"),
                                user_message=run.user_message,
                                session_id=run.session_id or "",
                            )
                            if _app_ev:
                                yield _sse("app_action_request", _app_ev)
                        except Exception:
                            pass
                    _a_resolved: dict[int, str] = {}

                    for _a_idx, _a_sr in enumerate(_a_results):
                        if _a_sr["status"] == "approval_needed":
                            if run.autonomous:
                                _a_resolved[_a_idx] = (
                                    f"[{_a_sr['tool_name']}]: skipped (autonomous)"
                                )
                                yield _sse("capability", {
                                    "type": "tool_denied", "tool": _a_sr["tool_name"]
                                })
                                continue
                            if run.trust_all:
                                # Trust gradient (E8): destructive calls always
                                # require approval, even in trust mode.
                                _a_classification = str(_a_sr["result"].get("classification", "") or "")
                                if _a_classification == "destructive":
                                    pass  # fall through to approval-card path
                                else:
                                    _a_resolved[_a_idx] = str(_a_sr["result"].get("result_text") or "")
                                    yield _sse("capability", {"type": "tool_approved", "tool": _a_sr["tool_name"], "auto": True})
                                    continue
                            _a_apid = f"approval-{uuid4().hex[:12]}"
                            _a_created_at = datetime.now(UTC).isoformat()
                            _PENDING_APPROVALS[_a_apid] = {
                                "tool_name": _a_sr["tool_name"],
                                "arguments": _a_sr["arguments"],
                                "result": _a_sr["result"],
                                "run_id": run.run_id,
                                "session_id": run.session_id,
                                "created_at": _a_created_at,
                            }
                            # Tag the sr so the second-pass agentic loop's
                            # persistence can later check chat_persisted flag.
                            _a_sr["approval_id"] = _a_apid
                            _persist_pending_approvals()
                            _set_visible_approval_state(_a_apid, {
                                "approval_id": _a_apid,
                                "status": "pending",
                                "tool_name": _a_sr["tool_name"],
                                "arguments": _a_sr["arguments"],
                                "result": _a_sr["result"],
                                "run_id": run.run_id,
                                "session_id": run.session_id,
                                "created_at": _a_created_at,
                            })
                            yield _sse("approval_request", {
                                "type": "approval_request",
                                "approval_id": _a_apid,
                                "tool": _a_sr["tool_name"],
                                "message": _a_sr["result"].get("message", ""),
                                "detail": (
                                    _a_sr["result"].get("path")
                                    or _a_sr["result"].get("command", "")
                                ),
                            })
                            _a_res = None
                            _a_deadline = asyncio.get_running_loop().time() + 300.0
                            logger.info(
                                "approval-wait-start run_id=%s round=%d approval_id=%s tool=%s",
                                run.run_id, _agentic_round + 1, _a_apid, _a_sr["tool_name"],
                            )
                            while asyncio.get_running_loop().time() < _a_deadline:
                                _a_state = _get_visible_approval_state(_a_apid)
                                _a_status = str(_a_state.get("status") or "")
                                if _a_status == "approved":
                                    _a_res = str(_a_state.get("result_text") or "")
                                    logger.info(
                                        "approval-resolved run_id=%s approval_id=%s "
                                        "result_chars=%d", run.run_id, _a_apid, len(_a_res),
                                    )
                                    break
                                if _a_status in {"denied", "expired"}:
                                    _a_res = None
                                    logger.info(
                                        "approval-rejected run_id=%s approval_id=%s status=%s",
                                        run.run_id, _a_apid, _a_status,
                                    )
                                    break
                                await asyncio.sleep(0.25)
                            else:
                                logger.warning(
                                    "approval-timeout run_id=%s approval_id=%s",
                                    run.run_id, _a_apid,
                                )
                            if _a_res is None:
                                _a_resolved[_a_idx] = (
                                    f"[{_a_sr['tool_name']}]: Tool call denied by user."
                                )
                                yield _sse("capability", {
                                    "type": "tool_denied", "tool": _a_sr["tool_name"]
                                })
                            else:
                                _a_resolved[_a_idx] = _a_res
                                yield _sse("capability", {
                                    "type": "tool_result",
                                    "tool": _a_sr["tool_name"],
                                    "status": "ok",
                                })
                            continue
                        # Gate-blocked (veto gate or decision gate)
                        if _a_sr["status"] == "gate_blocked":
                            _a_gt = str(_a_sr.get("result", {}).get("gate_type", "unknown"))
                            _a_gm = str(_a_sr.get("result", {}).get("message", ""))
                            _a_resolved[_a_idx] = f"[{_a_gt}] {_a_gm}"
                            yield _sse("capability", {
                                "type": "gate_blocked",
                                "gate_type": _a_gt,
                                "tool": _a_sr["tool_name"],
                                "message": _a_gm,
                            })
                            continue
                        _a_resolved[_a_idx] = _a_sr["result_text"]
                        from core.services.tool_chip_payload import build_tool_capability_payload
                        yield _sse("capability", build_tool_capability_payload(
                            tool=_a_sr["tool_name"],
                            status=_a_sr["status"],
                            arguments=_a_sr.get("arguments"),
                            result_text=_a_sr.get("result_text", ""),
                        ))
                        yield _sse("working_step", {
                            "type": "working_step",
                            "run_id": run.run_id,
                            "action": _a_sr["tool_name"],
                            "step": _step_counter - len(_a_results) + _a_idx + 1,
                            "status": "done",
                        })

                    # Persist tool results to DB.
                    # 2026-05-24 (Claude): skip when resolve_pending_approval
                    # already persisted (chat_persisted flag). Same dedup logic
                    # as first-pass persistence above.
                    if run.session_id:
                        for _a_idx, _a_sr in enumerate(_a_results):
                            _a_rt = _a_resolved.get(_a_idx, _a_sr.get("result_text", ""))
                            if not _a_rt:
                                continue
                            if _a_sr.get("status") in ("duplicate_suppressed", "gate_blocked"):
                                continue
                            _a_aid = _a_sr.get("approval_id") or ""
                            if _a_aid:
                                try:
                                    _a_astate = _get_visible_approval_state(str(_a_aid)) or {}
                                    if _a_astate.get("chat_persisted"):
                                        continue
                                except Exception:
                                    pass
                            # 2026-06-29 (loop-not-blocked): se første-pass-stedet.
                            # Synkron DB-skrivning på event-loop-tråden midt i en
                            # agentisk runde frøs _ping_loop. Offload til worker-tråd.
                            await asyncio.to_thread(
                                append_chat_message,
                                session_id=run.session_id,
                                role="tool",
                                content=_a_rt,
                                tool_name=str(_a_sr.get("tool_name") or ""),
                                tool_arguments=dict(_a_sr.get("arguments") or {}),
                            )

                    _a_followup_results = _to_followup_results(
                        _a_tool_calls,
                        _a_results,
                        _a_resolved,
                    )
                    # Tur-akkumulering (agentisk runde) — samme calls + results
                    # som ToolExchange'en; side-effekt-frit.
                    _accumulate_turn_blocks(_a_tool_calls, _a_followup_results)
                    _followup_exchanges.append(
                        _vf.ToolExchange(
                            text=_exchange_text(),
                            tool_calls=list(_a_tool_calls),
                            reasoning_content=_a_round_reasoning,
                            results=_a_followup_results,
                        )
                    )
                    try:
                        # 2026-06-29 (loop-not-blocked): round-complete-checkpoint
                        # er synkron fil/DB-I/O (_load + _save af hele record-settet)
                        # og fyrer HVER agentisk runde på event-loop-tråden. Offload
                        # til worker-tråd så _ping_loop ikke fryser mellem runder.
                        # Best-effort (try/except) bevaret uændret.
                        await asyncio.to_thread(
                            _save_agentic_checkpoint,
                            run_id=run.run_id,
                            session_id=run.session_id,
                            user_message=run.user_message,
                            provider=run.provider,
                            model=run.model,
                            round_index=_agentic_round + 1,
                            phase="round-complete",
                            exchanges=_followup_exchanges,
                            partial_text="".join(_all_followup_parts),
                            exit_reason=_agentic_loop_exit_reason,
                        )
                    except Exception:
                        pass
                    try:
                        from core.services.agentic_working_conclusions import (
                            build_round_observation as _build_working_observation,
                            update_working_conclusion as _update_working_conclusion,
                        )
                        _update_working_conclusion(
                            run_id=run.run_id,
                            session_id=run.session_id,
                            user_message=run.user_message,
                            round_index=_agentic_round + 1,
                            observation=_build_working_observation(
                                text="".join(_a_parts),
                                tool_names=[
                                    str((tc.get("function") or {}).get("name") or tc.get("name") or "")
                                    for tc in _a_tool_calls
                                ],
                                result_texts=[
                                    str(_a_resolved.get(i, sr.get("result_text", "")) or "")
                                    for i, sr in enumerate(_a_results)
                                ],
                            ),
                            next_step="Continue with next agentic followup round and use the checkpoint's tool results.",
                        )
                    except Exception:
                        pass
                    import time as _time_mod_end
                    _round_end_t = _time_mod_end.monotonic()
                    _round_total_ms = int((_round_end_t - _round_loop_start_t) * 1000)
                    logger.warning(
                        "agentic-round-end run_id=%s round=%d text_chars=%d "
                        "tool_calls=%d resolved=%d round_total_ms=%d",
                        run.run_id, _agentic_round + 1,
                        sum(len(p) for p in _a_parts),
                        len(_a_tool_calls), len(_a_resolved), _round_total_ms,
                    )
                    _prev_round_end_t = _round_end_t

                    # ── Mid-flight steer ────────────────────────────────────
                    # Pick up any user messages that landed via
                    # POST /chat/runs/{id}/steer since the previous round.
                    # Inject them as user-role messages in base_messages so
                    # the next agentic round sees them; "stop"/"cancel"
                    # steers break the loop cleanly.
                    try:
                        steers = consume_visible_run_steers(run.run_id)
                    except Exception:
                        steers = []
                    if steers:
                        for s in steers:
                            content = str(s.get("content") or "").strip()
                            if not content:
                                continue
                            base_messages.append({"role": "user", "content": content})
                            yield _sse("steer_received", {
                                "type": "steer_received",
                                "run_id": run.run_id,
                                "content": content,
                                "at": s.get("at"),
                            })
                            logger.info(
                                "agentic-steer run_id=%s round=%d injected=%d_chars",
                                run.run_id, _agentic_round + 1, len(content),
                            )
                            stop_words = ("stop", "stop.", "cancel", "afbryd", "abort", "stop nu")
                            if content.strip().lower() in stop_words:
                                _agentic_loop_exit_reason = "user-steer-stop"
                                break
                        if _agentic_loop_exit_reason == "user-steer-stop":
                            break

                    # ── Tool-result aging (harness Part B, Mechanism B) ──────────
                    # Age older tool-result content ONCE per round, forward-carried
                    # (outside the retry fence at ~2305 → D11 byte-identical retries
                    # hold). Strong-lane + round gated inside age_tool_results;
                    # default shadow (observe, mutate nothing). Reassigning
                    # _followup_exchanges is a no-op in shadow (same object).
                    try:
                        from core.services.tool_result_aging import (
                            age_tool_results, tool_result_aging_mode,
                            aging_trigger_tokens)
                        from core.services.model_trust import model_strength
                        _age_mode = tool_result_aging_mode()
                        if _age_mode != "off":
                            _aged_ex, _age_metrics = age_tool_results(
                                _followup_exchanges,
                                mode=_age_mode,
                                strength=model_strength(getattr(run, "model", "") or ""),
                                round_index=_agentic_round,
                                compress_fn=_compact_llm_for_run,
                                trigger_tokens=aging_trigger_tokens(),
                            )
                            _followup_exchanges = _aged_ex
                            if _age_metrics.get("aged_exchanges"):
                                try:
                                    from core.services import central_timeseries as _cts_age
                                    _cts_age.record(
                                        "context", "tool_result_aging",
                                        float(_age_metrics.get("would_free_tokens") or 0),
                                        meta={**_age_metrics, "run_id": run.run_id,
                                              "round": _agentic_round + 1,
                                              "active": _age_mode == "active"})
                                except Exception:
                                    pass
                    except Exception:
                        pass
                logger.info(
                    "agentic-loop-exit run_id=%s reason=%s rounds_done=%d",
                    run.run_id, _agentic_loop_exit_reason,
                    locals().get("_agentic_round", -1) + 1,
                )
                # Followup-cluster: loop-complete synlig (runder + exit-grund).
                try:
                    from core.services import followup_observer as _fu_obs
                    _fu_obs.note_loop_complete(
                        run.run_id, rounds=locals().get("_agentic_round", -1) + 1,
                        exit_reason=str(_agentic_loop_exit_reason or ""),
                        provider=run.provider, model=run.model)
                except Exception:
                    pass
                # DURABLE DENOMINATOR (oneiric grounding): ét tick pr. fuldført agentisk
                # loop → daglig total som no_progress_finalize er en RATE imod. Additiv,
                # self-safe, ændrer ALDRIG adfærd.
                try:
                    from datetime import UTC as _UTC2, datetime as _dt2
                    from core.services import central_timeseries as _cts2
                    _cts2.record("loop", "agentic_run_total", 1.0,
                                 meta={"day": _dt2.now(_UTC2).date().isoformat()})
                except Exception:
                    pass
                # Causal graph: clear EventContext after the loop so
                # subsequent code outside doesn't auto-link to a stale
                # round_event_id from the last iteration.
                try:
                    from core.eventbus.context import set_current_event
                    set_current_event(None)
                except Exception:
                    pass

                # ── End agentic loop ───────────────────────────────────────────────

                # Autonomous runs: only use the final round's text so the
                # persisted message is a clean summary, not all intermediate
                # tool-call reasoning concatenated together.
                # Interactive runs: stream everything (already yielded live).
                if run.autonomous:
                    followup_text = "".join(_a_parts).strip()
                else:
                    followup_text = "".join(_all_followup_parts).strip()

                if not followup_text:
                    # No follow-up text from the provider-specific agentic loop.
                    # Fall back to the
                    # first-pass text — already streamed live to the user via
                    # VisibleModelDelta — as the persisted assistant message.
                    # If the first pass was tool-calls-only with no prose,
                    # followup_text stays empty and _persist_session_assistant_message
                    # declines to persist. NEVER emit synthetic internal
                    # markers like "[Completed: ...]" to the user.
                    followup_text = (getattr(result, "text", "") or "").strip()

                if not followup_text:
                    # I1-heal (2026-06-30 — DEN ægte cutoff-rod): thinking-modeller
                    # (deepseek-v4-flash/v4-pro/reasoner) lægger NOGLE GANGE hele svaret i
                    # reasoning mens content er tomt. Reasoning-deltaerne ER streamet til
                    # klienten (brugeren SÅ teksten), men content-accumulatoren var tom →
                    # falsk empty_completion → fallback wiper det ægte svar. Sidste udvej:
                    # surfacér det akkumulerede reasoning (denne runde + first-pass) som svaret.
                    _reasoning_join = "".join(_all_followup_reasoning_parts).strip()
                    if not _reasoning_join:
                        _reasoning_join = str(getattr(result, "reasoning_content", "") or "").strip()
                    if _reasoning_join:
                        try:
                            from core.services.visible_model import (
                                _strip_thinking_delimiters,
                                _observe_content_empty_thinking_fallback,
                            )
                            followup_text = _strip_thinking_delimiters(_reasoning_join).strip()
                            _observe_content_empty_thinking_fallback(
                                run.provider, run.model, "agentic_followup", len(_reasoning_join),
                            )
                        except Exception:
                            followup_text = _reasoning_join

                if not followup_text:
                    # #1453-RESCUE (2026-06-30 — verificeret DeepSeek-bug): thinking-
                    # modellerne (v4-flash/v4-pro/reasoner) returnerer INTERMITTENT helt
                    # tomt efter tool-kald (content+reasoning tomme, HTTP 200) og bliver
                    # ved at være tomme ved retry i SAMME thinking-kontekst (GitHub
                    # DeepSeek-V3 #1453). Eneste kendte kur = omgå thinking-maskineriet.
                    # Kør ÉN frisk syntese-runde med non-thinking deepseek-chat (force-
                    # prose, fuld tool-kontekst). Rent additivt: kun når loopet ALLEREDE
                    # endte tomt EFTER tool-kald; værste fald er rescue også tom → vi
                    # falder igennem til de eksisterende fallbacks. Idempotent (ingen
                    # tools eksekveres). await via to_thread så event-loopet ikke blokeres.
                    # HARNESS-FINALIZE lag 2b (Bjørn 4. jul): PROVIDER-AGNOSTISK. Var
                    # der tool-kald men endte turen tom, kør ÉT tool-frit syntese-kald
                    # der TVINGER prosa fra HVILKEN SOM HELST lane (fjerner tools fysisk +
                    # eksplicit finalize-instruktion). synthesize_final_answer swapper
                    # selv deepseek-thinking→chat (#1453). Var før KUN deepseek → ollama/
                    # kimi/glm/copilot/codex fik aldrig et syntese-forsøg og faldt direkte
                    # til en tom-note. Nu får alle lanes et ægte svar-forsøg her.
                    _fu_ex_r = locals().get("_followup_exchanges") or []
                    _had_tools_r = any(
                        getattr(_ex, "tool_calls", None) for _ex in _fu_ex_r)
                    if _had_tools_r:
                        try:
                            _rescued = await asyncio.to_thread(
                                _vf.synthesize_final_answer,
                                provider=run.provider, model=run.model,
                                base_messages=locals().get("base_messages") or [],
                                exchanges=_fu_ex_r,
                            )
                        except Exception:
                            _rescued = ""
                        if _rescued:
                            followup_text = _rescued
                            if not run.autonomous:
                                yield _sse("delta", {
                                    "type": "delta", "run_id": run.run_id,
                                    "delta": _rescued,
                                })
                            _observe_streamed_text_recovered(
                                run, chars=len(_rescued), source="finalize_synthesis")

                if not followup_text:
                    # DAG-ÉT DIVERGENS-FIX (sidste udvej, agentisk gren): hvis
                    # first-pass streamede ægte prosa (brugeren SÅ den) men den
                    # senere followup-runde endte tom OG result.text/reasoning også
                    # var tomme, så er de streamede first-pass-bytes stadig det
                    # eneste sande billede af hvad brugeren så. Genbrug dem frem for
                    # at lade fallback'en wipe svaret. Spejler first-pass-stien
                    # (~4125). No-op hvis intet streamede.
                    _streamed_fp_ag = str(_fp_deg_accum or "").strip()
                    if _streamed_fp_ag:
                        followup_text = _streamed_fp_ag
                        _observe_streamed_text_recovered(
                            run, chars=len(_fp_deg_accum), source="agentic_first_pass_stream",
                        )

                # ── Tavs cut-off-vagt (2026-06-23, udvidet) ────────────────────
                # Provider-AGNOSTISK fejlklasse (Bjørn: "cutter random på tværs af
                # ALLE modeller/providers"): et 'completed' run der IKKE producerede
                # et ÆGTE svar. To former, begge verificeret via rå-SSE-reproduktion:
                #   1) tom-efter-tools — first-pass kaldte et tool, followup-runden
                #      gav 0 tokens → followup_text faldt tilbage til placeholderen
                #      "[tool calls only]" (linje ~1680) → IKKE tom → glap forbi den
                #      gamle guard → persist afviste markøren → tavst hæng.
                #   2) helt-tom first-pass — provideren returnerede intet (ingen tekst,
                #      ingen tools) → _followup_exchanges tomt → tool-gaten fejlede.
                # Transient (samme tur lykkes nogle gange). Nu: behandl placeholder
                # SOM tom + fyr uanset tools → ALDRIG tavst; bruger får ÉT svar +
                # Centralen ser klassen. (Den ægte kur = retry; foreslået separat.)
                _real_answer = str(followup_text or "").strip()
                if _real_answer in ("[tool calls only]", "[Completed]", "[tool calls only]."):
                    _real_answer = ""
                if not _real_answer and _final_run_status == "completed":
                    _fu_ex = locals().get("_followup_exchanges") or []
                    _tools_ct = sum(len(getattr(_ex, "tool_calls", []) or [])
                                    for _ex in _fu_ex)
                    try:
                        from core.services import followup_observer as _fu_obs
                        _fu_obs.note_empty_completion(
                            run.run_id, provider=run.provider, model=run.model,
                            rounds=locals().get("_agentic_round", -1) + 1,
                            tools_executed=_tools_ct,
                            session_id=run.session_id or "", path="agentic_block")
                    except Exception:
                        pass
                    # KORRELATION: loop-lag ved cutoff (samme spørgsmål — sultning?).
                    try:
                        from core.services.central_loop_lag import recent_peak_ms as _lag_ag
                        from core.services.central_core import central as _c_ag
                        _c_ag().observe({
                            "cluster": "stream", "nerve": "cutoff_at_loop_lag",
                            "run_id": str(run.run_id or ""), "provider": str(run.provider or ""),
                            "model": str(run.model or ""), "path": "agentic_block",
                            "loop_lag_peak_ms": round(_lag_ag(10.0), 1),
                        })
                    except Exception:
                        pass
                    if _tools_ct:
                        _empty_cutoff_note = (
                            "Jeg kørte værktøjerne, men nåede ikke at formulere et "
                            "færdigt svar. Sig til, så fortsætter jeg derfra.")
                    else:
                        _empty_cutoff_note = (
                            "Jeg fik ikke formuleret et svar den gang — spørg mig "
                            "gerne igen.")
                    # Kun interaktive runs får en synlig fallback (autonome må gerne
                    # ende tomt uden at persistere støj); nerven fyrer i begge.
                    if not run.autonomous:
                        yield _sse("delta", {
                            "type": "delta", "run_id": run.run_id,
                            "delta": _empty_cutoff_note,
                        })
                        followup_text = _empty_cutoff_note

                if _final_run_status == "interrupted":
                    _resume_note = (
                        "\n\n⚠ Jeg blev afbrudt i agentic loopet "
                        f"({_final_run_error or 'unknown cause'}). "
                        "Next message can continue from here instead of starting over."
                    )
                    if _resume_note.strip() not in followup_text:
                        # STREAM noten live (interaktive runs), så afbrydelsen lander
                        # i appen MED DET SAMME — ikke først ved næste genindlæsning/
                        # app-genstart (Bjørn 2026-06-16: "fejl-beskederne lander først
                        # når jeg genstarter appen"). Tidligere blev noten kun føjet til
                        # den persisterede besked → tavst hæng på klienten.
                        if not run.autonomous:
                            yield _sse("delta", {
                                "type": "delta",
                                "run_id": run.run_id,
                                "delta": _resume_note,
                            })
                        followup_text = (followup_text + _resume_note).strip()

                total_input_tokens = result.input_tokens * 2
                total_output_tokens = result.output_tokens + _estimate_tokens(followup_text)
                # 2026-06-13: denne agentiske completion-gren satte input/output
                # men IKKE cache-vars — så _cache_tokens-aflæsningen nedenfor
                # (linje ~2581) kastede UnboundLocalError og crashede HELE visible-
                # run'et midt i (fremstod som "Jarvis stopper / lyver"). Init dem
                # her fra result, ligesom hovedstien gør.
                total_cache_hit_tokens = getattr(result, "cache_hit_tokens", 0)
                total_cache_miss_tokens = getattr(result, "cache_miss_tokens", 0)
                visible_output_text = followup_text

                set_last_visible_run_outcome(
                    run,
                    status=_final_run_status,
                    text_preview=followup_text[:140],
                    error=_final_run_error,
                )
                if _final_run_status == "completed":
                    try:
                        from core.services.agentic_checkpoints import clear_run as _clear_agentic_checkpoint
                        _clear_agentic_checkpoint(run.run_id)
                    except Exception:
                        pass
                    try:
                        from core.services.agentic_working_conclusions import clear_run as _clear_working_conclusion
                        _clear_working_conclusion(run.run_id)
                    except Exception:
                        pass

                # Persist the assistant message BEFORE done so loadSession()
                # finds it immediately (avoids "message disappears" race).
                # reasoning_content threaded through so thinking-mode-models
                # (Deepseek v4-flash thinking, v4-pro) can replay prior
                # assistant turns with reasoning on the next run.
                try:
                    _persist_session_assistant_message(
                        run, followup_text,
                        reasoning_content=_persist_reasoning,
                        blocks=_build_turn_blocks(
                            text=followup_text,
                            tool_calls=_turn_tool_calls,
                            tool_results=_turn_tool_results,
                            interleave=_interleave_log,
                        ) or None,
                    )
                except Exception as _persist_exc:
                    # H5: svaret er vist live, men gemmes ikke → væk ved reload.
                    _observe_persist_failed(run, _persist_exc)

                if _final_run_status == "completed":
                    _advance_tool_lifecycle(run.session_id)

                _set_orb_phase("idle")
                # Phase E6: emit a per-turn changelog as its own SSE event
                # so MC / dev tools can render "what this turn actually
                # changed" without trusting the model's own claim. The
                # model sees the same data on its next turn via a prompt
                # section so its self-awareness is grounded in fact.
                try:
                    from core.services.turn_changelog import build_turn_changelog
                    _changelog = build_turn_changelog(
                        run_id=run.run_id,
                        started_at=controller.started_at,
                    )
                    yield _sse("turn_changelog", {
                        "type": "turn_changelog",
                        "run_id": run.run_id,
                        **_changelog,
                    })
                except Exception:
                    pass
                _reached_finalization = True
                yield _sse("done", {
                    "type": "done",
                    "run_id": run.run_id,
                    "status": _final_run_status,
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                })

                # Background: status update and cost recording only
                _run_ref = run
                _tokens = (total_input_tokens, total_output_tokens)
                _cache_tokens = (total_cache_hit_tokens, total_cache_miss_tokens)
                _followup_text = followup_text
                _outcome_status = _final_run_status
                _outcome_error = _final_run_error
                import threading as _threading

                def _persist_tool_result() -> None:
                    try:
                        # 2026-06-10: tidligere kommentar sagde "cache måles på
                        # den senere primary call" — men total_cache_hit_tokens
                        # er allerede akkumuleret i scope (linje 2529 + 2594 +
                        # 2647), så vi kan rapportere ægte tal her i stedet for
                        # 0/0. Resultat: visible-lane dashboard viser nu reel
                        # hit rate i stedet for misleading "0% af 4.4M".
                        record_cost(
                            provider=_run_ref.provider,
                            model=_run_ref.model,
                            input_tokens=_tokens[0],
                            output_tokens=_tokens[1],
                            cost_usd=0.0,
                            lane="visible",
                            cache_hit_tokens=_cache_tokens[0],
                            cache_miss_tokens=_cache_tokens[1],
                        )
                        finished_at = datetime.now(UTC).isoformat()
                        if _outcome_status == "completed":
                            event_bus.publish(
                                "runtime.visible_run_completed",
                                {
                                    "run_id": _run_ref.run_id,
                                    "lane": _run_ref.lane,
                                    "provider": _run_ref.provider,
                                    "model": _run_ref.model,
                                    "status": "completed",
                                    "finished_at": finished_at,
                                    "input_tokens": _tokens[0],
                                    "output_tokens": _tokens[1],
                                    "cost_usd": 0.0,
                                    "native_tool_path": True,
                                },
                            )
                        try:
                            from core.services.cognitive_episodes import record_visible_run_episode
                            record_visible_run_episode(
                                run_id=_run_ref.run_id,
                                session_id=_run_ref.session_id,
                                provider=_run_ref.provider,
                                model=_run_ref.model,
                                status=_outcome_status,
                                user_message=_run_ref.user_message,
                                assistant_text=_followup_text,
                                error=str(_outcome_error or ""),
                            )
                        except Exception:
                            pass
                        # Experience-episode collector (Lag 1 of Runtime
                        # Decision Policy — added 2026-05-09). Append-only
                        # log feeds embedding-retrieval substrate via
                        # _experience_substrate_section in prompt_contract.
                        try:
                            from core.services.experience_episodes import record_episode
                            _tool_seq = []
                            for _tc in _collected_native_tool_calls or []:
                                _name = ""
                                try:
                                    _name = (
                                        getattr(_tc, "name", None)
                                        or (_tc.get("name") if isinstance(_tc, dict) else "")
                                        or (
                                            _tc.get("function", {}).get("name", "")
                                            if isinstance(_tc, dict) else ""
                                        )
                                    )
                                except Exception:
                                    _name = ""
                                if _name:
                                    _tool_seq.append(str(_name))
                            _outcome_signals = {
                                "status": str(_outcome_status or ""),
                                "tool_errors": int(
                                    1 if (_outcome_error or "") else 0
                                ),
                                "tool_count": len(_tool_seq),
                                "output_tokens": int(_tokens[1] or 0),
                                "assistant_chars": len(_followup_text or ""),
                            }
                            record_episode(
                                session_id=_run_ref.session_id,
                                turn_id=_run_ref.run_id,
                                intent=str(_run_ref.user_message or "")[:240],
                                tool_sequence=_tool_seq,
                                outcome_signals=_outcome_signals,
                                user_corrected=False,  # enriched later
                                session_phase="mid-task",
                            )
                        except Exception:
                            pass
                        try:
                            from core.services.theory_of_mind_engine import record_theory_of_mind_update
                            record_theory_of_mind_update(
                                user_message=_run_ref.user_message,
                                assistant_text=_followup_text,
                                outcome_status=_outcome_status,
                                source_run_id=_run_ref.run_id,
                            )
                        except Exception:
                            pass
                        try:
                            from core.services.perceptual_event_engine import record_perceptual_event
                            _change_type = (
                                "runtime-interruption"
                                if _outcome_status == "interrupted"
                                else "runtime-completion"
                            )
                            _summary = (
                                f"Visible run {_outcome_status}: "
                                f"{_outcome_error or _followup_text[:160] or _run_ref.provider}"
                            )
                            record_perceptual_event(
                                change_type=_change_type,
                                summary=_summary,
                                salience="high" if _outcome_status == "interrupted" else "medium",
                                source_kind=f"runtime.visible_run_{_outcome_status}",
                                evidence={
                                    "run_id": _run_ref.run_id,
                                    "provider": _run_ref.provider,
                                    "model": _run_ref.model,
                                    "status": _outcome_status,
                                },
                            )
                        except Exception:
                            pass
                        _run_memory_postprocess(_run_ref, _followup_text)
                    except Exception:
                        pass

                _threading.Thread(
                    target=_persist_tool_result, daemon=True
                ).start()
                return

        _run_stage = "non_agentic_capability"
        # ── Legacy XML capability-call fallback ──
        _update_visible_execution_trace(
            run,
            {
                "selected_capability_id": capability_plan.get("selected_capability_id"),
                "parsed_command_text": (capability_plan.get("selected_arguments") or {}).get("command_text"),
                "parsed_target_path": (capability_plan.get("selected_arguments") or {}).get("target_path"),
                "argument_source": capability_plan.get("argument_source") or "none",
                "argument_binding_mode": capability_plan.get("argument_binding_mode") or "id-only",
                "capability_markup_count": len(capability_plan.get("capability_ids") or []),
                "multiple_capability_tags": bool(capability_plan.get("multiple")),
                "native_tool_call_count": len(_collected_native_tool_calls),
            },
        )

        if controller.is_cancelled():
            try:
                from core.services.agentic_checkpoints import save_checkpoint as _save_agentic_checkpoint
                _save_agentic_checkpoint(
                    run_id=run.run_id,
                    session_id=run.session_id,
                    user_message=run.user_message,
                    provider=run.provider,
                    model=run.model,
                    round_index=0,
                    phase="cancel-pre-agentic",
                    exchanges=[],
                    partial_text=(result.text or "") if result else "",
                    exit_reason="user-cancelled",
                )
            except Exception:
                pass
            _final_run_status = "cancelled"
            _reached_finalization = True  # eksplicit terminal — immun mod finally-downgrade
            set_last_visible_run_outcome(
                run,
                status="cancelled",
            )
            for cancelled_chunk in _cancel_visible_run(run):
                yield cancelled_chunk
            return

        total_input_tokens = result.input_tokens
        total_output_tokens = result.output_tokens
        total_cost_usd = result.cost_usd
        # 2026-05-22 (Claude): also accumulate cache hit/miss across rounds
        # so cost.recorded can surface the cache-hit ratio. Without this,
        # we measured 0% cache hit for every chat — not because we weren't
        # getting hits, but because the data got dropped at the
        # VisibleModelResult layer.
        total_cache_hit_tokens = getattr(result, "cache_hit_tokens", 0)
        total_cache_miss_tokens = getattr(result, "cache_miss_tokens", 0)

        all_capabilities = capability_plan.get("all_capabilities") or []
        if all_capabilities:
            for planned_step in _planned_visible_capability_steps(
                run,
                all_capabilities=all_capabilities,
                step_offset=100,
            ):
                yield _sse("working_step", planned_step)
            capability_results, any_executed, capability_events = _execute_visible_capability_entries(
                run,
                all_capabilities=all_capabilities,
            )
            for event in capability_events:
                yield _sse("capability", event)

            _update_visible_execution_trace(
                run,
                {
                    "invoke_status": "executed" if any_executed else "not-executed",
                    "capabilities_executed": sum(
                        1 for r in capability_results if r["status"] == "executed"
                    ),
                    "capabilities_total": len(capability_results),
                },
            )

            # Build visible output from all results
            visible_output_text = "\n\n".join(
                _capability_visible_text(
                    capability_id=str(r["capability_id"]),
                    invocation=r["invocation"],
                )
                for r in capability_results
            )

            yield _sse("trace", _visible_trace_payload(run))

            # --- Second pass grounded in ALL results ---
            if any_executed:
                _update_visible_execution_trace(
                    run, {"provider_second_pass_status": "started"},
                )
                yield _sse(
                    "working_step",
                    {
                        "type": "working_step",
                        "run_id": run.run_id,
                        "action": "thinking",
                        "detail": f"Grounding response from {len(capability_results)} capability results",
                        "step": 1,
                        "status": "running",
                    },
                )
                followup_result = _run_grounded_multi_capability_followup(
                    run,
                    capability_results=capability_results,
                    initial_model_text="",
                )
                if followup_result is not None:
                    total_input_tokens += followup_result.input_tokens
                    total_output_tokens += followup_result.output_tokens
                    total_cost_usd += followup_result.cost_usd
                    total_cache_hit_tokens += getattr(followup_result, "cache_hit_tokens", 0)
                    total_cache_miss_tokens += getattr(followup_result, "cache_miss_tokens", 0)
                    _update_visible_execution_trace(
                        run,
                        {
                            "provider_second_pass_status": "completed",
                            "provider_call_count": 2,
                            "second_pass_input_tokens": followup_result.input_tokens,
                            "second_pass_output_tokens": followup_result.output_tokens,
                        },
                    )
                    second_pass_plan = _extract_capability_plan(followup_result.text)
                    second_pass_caps = second_pass_plan.get("all_capabilities") or []
                    if second_pass_caps:
                        for planned_step in _planned_visible_capability_steps(
                            run,
                            all_capabilities=second_pass_caps,
                            step_offset=200,
                        ):
                            yield _sse("working_step", planned_step)
                        followup_capability_results, followup_any_executed, followup_events = (
                            _execute_visible_capability_entries(
                                run,
                                all_capabilities=second_pass_caps,
                            )
                        )
                        capability_results.extend(followup_capability_results)
                        for event in followup_events:
                            yield _sse("capability", event)
                        if followup_any_executed:
                            yield _sse(
                                "working_step",
                                {
                                    "type": "working_step",
                                    "run_id": run.run_id,
                                    "action": "thinking",
                                    "detail": (
                                        "Continuing autonomously with one extra bounded read-only round "
                                        f"from {len(followup_capability_results)} follow-up capability results"
                                    ),
                                    "step": 2,
                                    "status": "running",
                                },
                            )
                            final_followup = _run_grounded_multi_capability_followup(
                                run,
                                capability_results=capability_results,
                                initial_model_text="",
                            )
                            if final_followup is not None:
                                total_input_tokens += final_followup.input_tokens
                                total_output_tokens += final_followup.output_tokens
                                total_cost_usd += final_followup.cost_usd
                                total_cache_hit_tokens += getattr(final_followup, "cache_hit_tokens", 0)
                                total_cache_miss_tokens += getattr(final_followup, "cache_miss_tokens", 0)
                                _update_visible_execution_trace(
                                    run,
                                    {
                                        "provider_call_count": 3,
                                        "third_pass_input_tokens": final_followup.input_tokens,
                                        "third_pass_output_tokens": final_followup.output_tokens,
                                    },
                                )
                                visible_output_text = _finalize_second_pass_visible_text(
                                    final_followup.text,
                                    fallback=visible_output_text,
                                )
                            else:
                                visible_output_text = _finalize_second_pass_visible_text(
                                    followup_result.text,
                                    fallback=visible_output_text,
                                )
                        else:
                            visible_output_text = _finalize_second_pass_visible_text(
                                followup_result.text,
                                fallback=visible_output_text,
                            )
                    else:
                        visible_output_text = _finalize_second_pass_visible_text(
                            followup_result.text,
                            fallback=visible_output_text,
                        )
                else:
                    _update_visible_execution_trace(
                        run,
                        {
                            "provider_second_pass_status": "failed",
                            "provider_call_count": 2,
                        },
                    )
                _scanned = _scan_response(visible_output_text)
                yield _sse(
                    "delta",
                    {"type": "delta", "run_id": run.run_id, "delta": _scanned},
                )
            else:
                _update_visible_execution_trace(
                    run, {"provider_second_pass_status": "skipped"},
                )
                _scanned = _scan_response(visible_output_text)
                yield _sse(
                    "delta",
                    {"type": "delta", "run_id": run.run_id, "delta": _scanned},
                )
        else:
            _update_visible_execution_trace(
                run,
                {
                    "invoke_status": "not-invoked",
                    "provider_second_pass_status": "skipped",
                },
            )
            visible_output_text = _visible_text_without_capability_markup(
                result.text,
                had_markup=bool(capability_plan["had_markup"]),
            )
            # ── DAG-ÉT DIVERGENS-FIX (2026-06-30, Bjørn: provider-AGNOSTISK, fra
            # dag ét) ────────────────────────────────────────────────────────────
            # Persisteringen brugte KUN result.text som kilde. Men det brugeren SER
            # kommer fra de live-streamede deltas (akkumuleret i _fp_deg_accum,
            # linje ~1216) — en HELT anden kilde. Hvis adapteren streamede ægte
            # bytes til klienten (brugeren SÅ svaret) men result.text endte tom
            # (thinking-content, adapter-bug, race på StreamDone — verificeret tomt
            # på tværs af deepseek native/cloud, glm-5.1/5.2, kimi 30. jun), så blev
            # visible_output_text tom → ingen persist (linje ~4285) → unified
            # checkpoint så 'completed' + tom preview → fyrede fallback'en der
            # WIPEDE det viste svar ("BANG, væk"). Sandhedskilden for hvad brugeren
            # faktisk så ER de streamede bytes. Brug dem når result.text svigter.
            # Model-agnostisk pr. konstruktion: ligegyldigt HVORFOR result.text er
            # tom — streamede vi tekst, gemmer vi tekst. No-op hvis intet streamede.
            if not visible_output_text.strip():
                _streamed_fp = _visible_text_without_capability_markup(
                    _fp_deg_accum, had_markup=bool(capability_plan["had_markup"]),
                )
                if _streamed_fp.strip():
                    visible_output_text = _streamed_fp
                    _observe_streamed_text_recovered(
                        run, chars=len(_fp_deg_accum), source="first_pass_stream",
                    )
            # ── Rådets fund #5 (9. jul): output-conservation-instrument ("spøgelset") ──
            # Mål streamede first-pass-bytes (hvad brugeren SÅ, markup-strippet som persisten)
            # vs det der faktisk persisteres (visible_output_text). Et gap = bytes tabt mellem
            # stream og persist = præcis cutoff-klassen. Nu STÅENDE data pr. provider/model i
            # stedet for flygtigt gætværk. Egress-fri (kun længder), self-safe (må aldrig vælte run).
            try:
                from core.services.central_output_conservation import observe_conservation
                _streamed_measure = _visible_text_without_capability_markup(
                    _fp_deg_accum, had_markup=bool(capability_plan["had_markup"]),
                )
                observe_conservation(
                    layer="run_persist_first_pass",
                    produced_chars=len(_streamed_measure.strip()),
                    emitted_chars=len(visible_output_text.strip()),
                    provider=getattr(run, "provider", "") or "",
                    model=getattr(run, "model", "") or "",
                    run_id=getattr(run, "run_id", "") or "",
                    path="first_pass",
                    tolerance=8,   # tolerér lille whitespace/markup-normaliserings-støj
                )
            except Exception:
                pass
            # Deltas already streamed live — no need to re-send the full text.
            # 2026-05-22 (Claude): Claim-scanner first-pass global coverage.
            # Previously the scanner only ran in the capability-followup paths
            # above. Pure text replies (no capability markup) skipped scanning
            # entirely — claims about time, system, env, stats went to the
            # user AND were persisted to memory unverified. Now we scan here
            # too. The deltas have already streamed (user sees uncorrected
            # text live), but the DB-persisted version and any downstream
            # memory consolidation use the corrected text. A scan_correction
            # event is emitted so the UI can patch the displayed message.
            try:
                _scanned_first_pass = _scan_response(visible_output_text)
                if _scanned_first_pass != visible_output_text:
                    yield _sse(
                        "scan_correction",
                        {
                            "type": "scan_correction",
                            "run_id": run.run_id,
                            "corrected": _scanned_first_pass,
                        },
                    )
                    visible_output_text = _scanned_first_pass
            except Exception:
                pass

        record_cost(
            lane=run.lane,
            provider=run.provider,
            model=run.model,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            cost_usd=total_cost_usd,
            cache_hit_tokens=total_cache_hit_tokens,
            cache_miss_tokens=total_cache_miss_tokens,
        )
        event_bus.publish(
            "cost.recorded",
            {
                "run_id": run.run_id,
                "lane": run.lane,
                "provider": run.provider,
                "model": run.model,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "cost_usd": total_cost_usd,
                # 2026-05-22 (Claude): cache hit/miss now surfaced so we
                # can measure DeepSeek prompt-cache utilization. ratio =
                # cache_hit_tokens / input_tokens (0.0 = full miss, 1.0 = full hit).
                "cache_hit_tokens": total_cache_hit_tokens,
                "cache_miss_tokens": total_cache_miss_tokens,
            },
        )
        finished_at = datetime.now(UTC).isoformat()
        event_bus.publish(
            "runtime.visible_run_completed",
            {
                "run_id": run.run_id,
                "lane": run.lane,
                "provider": run.provider,
                "model": run.model,
                "status": "completed",
                "started_at": controller.started_at,
                "finished_at": finished_at,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "cost_usd": total_cost_usd,
            },
        )
        _update_visible_execution_trace(
            run,
            {
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "final_status": "completed",
            },
        )
        yield _sse("trace", _visible_trace_payload(run))
        yield _sse(
            "working_step",
            {
                "type": "working_step",
                "run_id": run.run_id,
                "action": "thinking",
                "detail": "Generation complete",
                "step": 0,
                "status": "done",
            },
        )
        # ── TruthGate v2 (pre-done, Fase 2) — evidens-baseret konfabulations-blok ──
        # Kører FØR persist+done så korrektionen er det der gemmes + scan_correction
        # når klienten. Flag-gated på EKSPLICIT 'truth_v2' (default OFF → deploy-sikker;
        # tændes via central_switches.set_enabled("nerve","truth_v2",True)). Ruttes
        # gennem Centralen → trace + live kill-switch ("nerve","truth"). Best-effort +
        # fail-open: enhver fejl (inkl. ubundet closure-var) → no-op, blokér aldrig
        # brugeren pga. en gate-fejl.
        try:
            from core.services import shared_cache as _sc_tv2
            _tv2_flag = _sc_tv2.get("flag:central.switch.nerve.truth_v2")
            if isinstance(_tv2_flag, dict) and _tv2_flag.get("enabled"):
                # _followup_exchanges/_collected_native_tool_calls kan være UBUNDET for
                # single-pass-svar (ingen agentic-loop) → guard begge, ellers kaster
                # ctx-bygningen NameError og hele hooken no-op'er stille.
                _tv2_fe: list = []
                try:
                    _tv2_fe = list(_followup_exchanges)  # type: ignore[has-type]
                except Exception:
                    _tv2_fe = []
                _tv2_ntc: list = []
                try:
                    _tv2_ntc = list(_collected_native_tool_calls)  # type: ignore[has-type]
                except Exception:
                    _tv2_ntc = []
                _tv2_names: list[str] = []
                for _tc in _tv2_ntc:
                    try:
                        _n = str((_tc.get("function") or {}).get("name") or _tc.get("name") or "")
                        if _n:
                            _tv2_names.append(_n)
                    except Exception:
                        pass
                for _ex in _tv2_fe:
                    for _tc in (getattr(_ex, "tool_calls", None) or []):
                        try:
                            _n = str((_tc.get("function") or {}).get("name") or _tc.get("name") or "")
                            if _n:
                                _tv2_names.append(_n)
                        except Exception:
                            pass
                from core.services.central_core import central as _central_tv2
                from core.services.truth_gate_v2 import truth_gate_v2 as _tg2
                _tv2 = _central_tv2().decide("truth", {
                    "text": visible_output_text,
                    "executed_tool_names": _tv2_names,
                    "followup_exchanges": _tv2_fe,
                    "run_id": run.run_id,
                    "session_id": getattr(run, "session_id", "") or "",
                }, _tg2, cluster="truth")
                _tv2_corr = (_tv2.evidence or {}).get("corrected_text") if _tv2.evidence else None
                if _tv2.decision.value in ("red", "yellow") and _tv2_corr:
                    logger.warning(
                        "TruthGate v2: %s (%s) run_id=%s — konfabulation %s",
                        _tv2.decision.value.upper(),
                        (_tv2.evidence or {}).get("severity"), run.run_id,
                        "blokeret" if _tv2.decision.value == "red" else "markeret",
                    )
                    visible_output_text = _tv2_corr
                    yield _sse("scan_correction", {
                        "type": "scan_correction", "run_id": run.run_id, "corrected": _tv2_corr,
                    })
        except Exception as _tv2_exc:
            logger.warning("TruthGate v2 hook fejlede run_id=%s: %s",
                           getattr(run, "run_id", "?"), _tv2_exc)

        # ── Tavs cut-off-vagt (2026-07-04) — NON-AGENTISK/first-pass-gren ───────
        # SURVIVAL-SPAM-RODEN (Bjørn: "survival besked KONSTANT uanset provider"):
        # den agentiske gren har siden 23. jun haft en honest empty-cutoff-note
        # (~linje 3796), men DENNE gren (single-pass / kun-tekst-svar UDEN native
        # tool-calls) havde ingen. Når first-pass kom tom tilbage (kimi-k2 ~30%,
        # deepseek-v4-flash ~20%, glm-5.2 ~50% — HTTP 200, 0 tokens, ingen
        # streamede bytes at redde) faldt visible_output_text tom → ingen persist
        # → 'completed'+tom preview → _guarantee_visible_outcome fyrede den
        # dramatiske OVERLEVELSES-stemme på HVER ordinær tom tur. Survival-voicen
        # er til ægte substrat-død, ikke en model-quirk. Her: samme rolige, ærlige
        # note som den agentiske gren, persisteret som assistant → sidste besked ER
        # assistant → _guarantee_visible_outcome springer over → survival reserveret
        # til reel katastrofe. Nerven fyrer så vi ser den ægte tom-rate pr. provider.
        _np_answer = str(visible_output_text or "").strip()
        if _np_answer in ("[tool calls only]", "[Completed]", "[tool calls only]."):
            _np_answer = ""
        if not _np_answer and _final_run_status == "completed" and not run.autonomous:
            try:
                from core.services import followup_observer as _fu_np
                _fu_np.note_empty_completion(
                    run.run_id, provider=run.provider, model=run.model,
                    session_id=run.session_id or "", path="non_agentic_block")
            except Exception:
                pass
            # KORRELATION: tag tom-completion med loop-lag (klynger cutoffs ved sultning?).
            try:
                from core.services.central_loop_lag import recent_peak_ms as _lag_np
                from core.services.central_core import central as _c_np
                _c_np().observe({
                    "cluster": "stream", "nerve": "cutoff_at_loop_lag",
                    "run_id": str(run.run_id or ""), "provider": str(run.provider or ""),
                    "model": str(run.model or ""), "path": "non_agentic_block",
                    "loop_lag_peak_ms": round(_lag_np(10.0), 1),
                })
            except Exception:
                pass
            _np_note = (
                "Jeg fik ikke formuleret et svar den gang — spørg mig gerne igen.")
            yield _sse("delta", {
                "type": "delta", "run_id": run.run_id, "delta": _np_note,
            })
            visible_output_text = _np_note

        # Persist the assistant message BEFORE sending done so that the
        # frontend's loadSession() call immediately after done finds the
        # message in the DB (avoids the "message disappears" race condition).
        if visible_output_text:
            try:
                _persist_session_assistant_message(
                    run, visible_output_text,
                    reasoning_content=str(locals().get("_persist_reasoning", "") or ""),
                    blocks=_build_turn_blocks(
                        text=visible_output_text,
                        tool_calls=_turn_tool_calls,
                        tool_results=_turn_tool_results,
                        interleave=_interleave_log,
                    ) or None,
                )
            except Exception as _persist_exc2:
                # H5: svaret er vist live, men gemmes ikke → væk ved reload.
                _observe_persist_failed(run, _persist_exc2)
        _reached_finalization = True
        yield _sse(
            "done",
            {
                "type": "done",
                "run_id": run.run_id,
                "status": "completed",
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
            },
        )
    except Exception as _outer_exc:
        # Catch any unhandled exception from tool execution or second-pass streaming
        # and send a proper failed SSE so the browser gets a clean error instead of
        # an abrupt connection close ("Error in input stream").
        import logging as _outer_log
        _outer_log.getLogger(__name__).error(
            "visible-run unhandled exception: %s", _outer_exc, exc_info=True
        )
        _outer_error = str(_outer_exc) or "unexpected-run-error"
        _final_run_status = "failed"  # ellers overskriver _post_process (finally) med "completed"+tom → falsk survival
        _final_run_error = _outer_error
        set_last_visible_run_outcome(run, status="failed", error=_outer_error)
        for _fail_chunk in _fail_visible_run(run, _outer_error, partial_text=visible_output_text):
            yield _fail_chunk
        unregister_visible_run(run.run_id)
        return
    finally:
        # Post-processing in finally: status update, candidate tracking, cleanup.
        # Message persistence now happens synchronously before done (above).
        import threading

        # 2026-06-11 (fix D): cancel Discord-heartbeat-watchdog hvis aktiv.
        # Skal ske før unregister så vi ikke har en zombie-task der
        # fortsætter med at sende "(arbejder stadig...)" efter runet er
        # færdigt.
        try:
            if _discord_watchdog_task is not None and not _discord_watchdog_task.done():
                _discord_watchdog_task.cancel()
        except Exception:
            pass

        # 2026-05-16 fix: unregister FIRST, synchronously. Earlier version let
        # post_process-thread (daemon=True) be responsible for clearing
        # active-run state. If api was restarted while thread waited,
        # unregister was never called → active state stuck → new messages
        # were routed as "midway nudges" and yielded nothing. Bjørn saw it
        # as "No response content returned". Guarantee: unregister happens
        # synchronously before we yield control to post-processing.
        unregister_visible_run(run.run_id)

        # Path B (local_tool_exec): fail any tool_calls still awaiting a client result
        # so a dropped SSE / client disconnect can't leave the broker holding pending
        # entries (and a resumed run unblocks with a typed error, never a hang).
        try:
            if getattr(run, "local_tool_exec", False) and getattr(run, "session_id", ""):
                from core.services import local_tool_broker as _ltb_cancel
                _ltb_cancel.cancel_session(run.session_id)
        except Exception:
            pass

        # ── RUNTIME-CUTOFF-ROD-FIX (Bjørn 4. jul) ──────────────────────────────
        # Nåede vi finally UDEN at have passeret et done-yield (_reached_finalization
        # stadig False) MEN status er stadig default'en 'completed'? Så blev runnet
        # AFBRUDT midt-flugt (GeneratorExit ved klient-drop, CancelledError, eller en
        # BaseException `except Exception` ikke fanger). En sådan run er IKKE completed
        # — den er interrupted. Ellers fyrer _post_process' completed+tom-checkpoint
        # survival-stemmen på en halv run (provider-agnostisk rod: kimi/deepseek
        # tool-ture). Downgrade FØR _post_process-tråden læser _final_run_status.
        if (not _reached_finalization and _final_run_status == "completed"):
            import sys as _sys_exc
            _abort_exc = _sys_exc.exc_info()[0]
            _abort_kind = _abort_exc.__name__ if _abort_exc else "none-clean-exit"
            _final_run_status = "interrupted"
            _final_run_error = _final_run_error or f"run-abandoned-before-finalization:{_abort_kind}"
            # Central-nerve (loop-cluster): en afbrudt-midt-flugt run er nu synlig i jc —
            # så vi ser hvis abort-raten stiger igen (fx nyt tavst await-vindue). Self-safe.
            try:
                # KORRELATION (Bjørn 4. jul): tag afbrydelsen med hvor sultent event-
                # loopet var lige nu → Centralen kan svare om cutoffs klynger sig ved
                # loop-lag-spikes (kontention) eller ej (uforklaret).
                try:
                    from core.services.central_loop_lag import recent_peak_ms as _lag_peak
                    _cutoff_lag = round(_lag_peak(10.0), 1)
                except Exception:
                    _cutoff_lag = -1.0
                from core.services.central_core import central as _central_ab
                _central_ab().observe({
                    "cluster": "loop", "nerve": "run_abandoned_midflight",
                    "run_id": str(run.run_id or ""), "provider": str(run.provider or ""),
                    "model": str(run.model or ""), "abort": _abort_kind,
                    "stage": str(_run_stage), "vis_len": len(visible_output_text or ""),
                    "loop_lag_peak_ms": _cutoff_lag,
                })
            except Exception:
                pass
            # Ærlig, rolig besked til brugeren (IKKE survival-stemmen) — kun hvis han
            # ikke allerede fik et svar. Idempotent + self-safe. På reload ser han
            # dette i stedet for tavshed eller en dramatisk overlevelses-tekst.
            try:
                if run.session_id and not run.autonomous and _session_last_role(run.session_id) != "assistant":
                    _persist_session_assistant_message(
                        run,
                        "Jeg blev afbrudt midt i det — svaret nåede ikke helt ud. "
                        "Skriv bare igen, så samler jeg tråden op.")
            except Exception:
                pass

        def _post_process() -> None:
            # KRITISK (2026-06-21): _post_process reassigner visible_output_text i
            # gate-blokkene nedenfor (block-now/fact_gate/diagnosis). Uden nonlocal
            # gør det visible_output_text til en LOKAL i hele funktionen → det første
            # read (text_preview nedenfor) kastede UnboundLocalError → den ydre except
            # slugte det → HELE post-output-blokken (response_style/memory/claim/fact/
            # diagnosis) døde stille. Samme June-14-commit som generator-yield-bug'en.
            nonlocal visible_output_text
            try:
                set_last_visible_run_outcome(
                    run,
                    status=_final_run_status,
                    error=_final_run_error,
                    text_preview=_preview_text(visible_output_text),
                )
                # Harness Part 1 (earned model-trust): record this run's outcome. Degeneration =
                # a loop-spin flag OR a failed/interrupted/cancelled terminal status (which covers
                # empty-completion/cutoff). Self-safe; NEVER affects the run. A clean streak earns the
                # model 'strong'; one degeneration reverts it to 'weak'.
                try:
                    from core.services.model_trust import record_run_outcome as _rec_mt
                    _mt_deg = bool(_run_degenerated) or _final_run_status in (
                        "failed", "interrupted", "cancelled")
                    _rec_mt(getattr(run, "model", "") or "", degenerated=_mt_deg)
                except Exception:
                    pass
                _track_runtime_candidates(run, visible_output_text)
                # ── Lag 1: record response_style choice ─────
                # Only record for runs with a user present — autonomous
                # heartbeat-triggered runs never get a user reply, so
                # they can't be scored and would just pile up in the
                # pending bucket (2026-06-08 fix).
                if not getattr(run, "autonomous", False):
                    try:
                        from core.runtime.db_credit_assignment import record_choice as _rc_rs
                        _resp_len = len(visible_output_text or "")
                        _has_code = "```" in (visible_output_text or "")
                        if _has_code:
                            _style = "technical"
                        elif _resp_len < 300:
                            _style = "short_direct"
                        else:
                            _style = "elaborate"
                        _rc_rs(
                            kind="response_style",
                            title=f"Response style ({_style}, {_resp_len}ch)",
                            options=["short_direct", "elaborate", "technical"],
                            decision=_style,
                            why=f"len={_resp_len}, has_code={_has_code}",
                        )
                    except Exception:
                        pass

                _run_memory_postprocess(run, visible_output_text)
                # 2026-05-17: detector + auto-continuation.
                # Jarvis often stops at natural pause-points
                # ("lad mig først se...") without continuing. Detector
                # scans output for pause-patterns; on match it spawns
                # an autonomous-run that wakes him again with context.
                _maybe_trigger_continuation(run, visible_output_text)

                # ── TruthGate C4 (2026-06-22) ─────────────────────────────
                # De gamle post-done effekt-gates (claim-block/fact_gate/diagnosis)
                # er FJERNET her: TruthGate v2 (pre-done, ~linje 3390) gør hele
                # enforcement ÉN gang FØR done. Detektions-logikken lever videre via
                # central().decide nedenfor (gate_truth = claim+fact+diagnosis-adaptere
                # → ÉT observabilitets-Verdict). C2 (flag-gating) → C4 (fjern kode).
                #
                # _executed_tool_names fodrer central().decide-observabiliteten.
                # Byg den robust — _followup_exchanges kan være ubundet for
                # single-pass-svar.
                _executed_tool_names: list[str] = []
                try:
                    for _ex in _followup_exchanges:
                        for _tc in (getattr(_ex, "tool_calls", None) or []):
                            _name = str(
                                (_tc.get("function") or {}).get("name")
                                or _tc.get("name") or ""
                            )
                            if _name:
                                _executed_tool_names.append(_name)
                except Exception:
                    _executed_tool_names = []

            except Exception:
                # 2026-06-21: denne ydre except slugte FØR stille (pass) → enhver
                # tidlig fejl (fx en closure-variabel ubundet for single-pass-runs)
                # dræbte response_style + memory + claim-detektion usynligt. Log nu.
                logger.warning(
                    "_post_process post-output-blok fejlede run_id=%s",
                    getattr(run, "run_id", "?"), exc_info=True,
                )

            # ── Truth-cluster → Den Intelligente Central ──────────────────────
            # Rut den samlede sandheds-beslutning (claim+fact+diagnosis via truth_gate)
            # gennem Centralens decide-ansigt: ÉT struktureret trace-spor pr. run_id +
            # live kill-switch + circuit-breaker. REN OBSERVABILITET — det ENESTE
            # post-done truth-spor efter C4 (enforcement gøres pre-done af v2,
            # ~linje 3390). Detektions-logikken (claim_scanner/fact_gate/diagnosis)
            # lever videre HER som gate_truth-adaptere. Best-effort.
            try:
                from core.services.central_core import central as _central_truth
                from core.services.gate_truth import truth_gate as _truth_gate_fn
                _central_truth().decide(
                    "truth",
                    {
                        "text": visible_output_text,
                        "tool_names": list(_executed_tool_names or []),
                        "tools_used": list(_executed_tool_names or []),
                        "run_id": run.run_id,
                        "session_id": getattr(run, "session_id", "") or "",
                    },
                    _truth_gate_fn,
                    cluster="truth",
                )
            except Exception:
                pass

            # Track 2 SHADOW (2026-07-06): de 5 sovende post_output-gates
            # (commit/loop/proactivity/review + fact_gate_adapter) vækkes i SKYGGE.
            # SAMME ctx som truth-decide ovenfor. HÅRDT INVARIANT: ren observabilitet —
            # decide traced/observer'er, resultatet BRUGES ALDRIG til at blokere turen.
            # Helper er self-safe (returnerer None, kaster aldrig); wrappet i try/except
            # så det umuligt kan påvirke run-loopet. Bag flag gate_kernel.shadow (default ON).
            try:
                from core.services.gate_shadow import run_post_output_shadow as _run_shadow_gates
                try:
                    from core.identity.workspace_context import current_user_id as _cuid
                    _shadow_uid = _cuid() or ""
                except Exception:
                    _shadow_uid = ""
                _run_shadow_gates({
                    "text": visible_output_text,
                    "tool_names": list(_executed_tool_names or []),
                    "tools_used": list(_executed_tool_names or []),
                    "run_id": run.run_id,
                    "session_id": getattr(run, "session_id", "") or "",
                    "current_user_id": _shadow_uid,   # privacy_gate: cross-user-lækage-tjek
                })
            except Exception:
                pass

            # Persistér denne runs governance-verdicts NU (6. jul). KRITISK: visible runs
            # eksekverer i api-processen (JARVIS_ENABLE_RUNTIME_SERVICES=0) hvor cadence-
            # flushen IKKE kører → truth/shadow-verdicts ville ellers sidde fast i api'ens
            # in-memory _ACC og aldrig lande i DB. Flush ved run-slut = 1 batchet DB-skriv
            # pr. run (~negligibelt), uafhængigt af hvilken proces der kørte turen. Cadence-
            # flushen i runtime forbliver backstop for runtime-lokale decides. Selv-sikker.
            try:
                from core.services import gate_verdict_ledger as _gvl
                _gvl.flush()
            except Exception:
                pass

            # C4 (2026-06-22): de gamle post-done effekt-gates (fact_gate +
            # diagnosis + claim-block) er FJERNET her — enforcement gøres pre-done
            # af TruthGate v2. Detektorerne lever videre via central().decide ovenfor.

        # 2026-05-22 (Claude): post-process MUST run even when
        # visible_output_text is empty. Originally guarded by
        # `if visible_output_text:` which meant a run that ended after
        # tool-calls with no final text skipped:
        #   1. set_last_visible_run_outcome — text_preview never updated
        #   2. _run_memory_postprocess — consolidation lost
        #   3. _maybe_trigger_continuation — auto-wakeup never fired
        # That's the root cause of "Jarvis silently completes a run
        # without delivering anything" — verified via run autonomous-
        # 141add33d9 (30 tool calls, 20 agentic rounds, text_preview
        # blank). Removing the guard runs the post-process pipeline
        # for every completed run; the individual functions already
        # handle empty text gracefully (most early-return on falsy
        # input).
        # ── KRITISK guard (2026-06-21) ────────────────────────────────────
        # _post_process MÅ ikke stille blive en generator. Hvis nogen tilføjer
        # et `yield` i kroppen, gør Python den til en generator-FUNKTION, og
        # Thread(target=_post_process) ville bare skabe et generator-OBJEKT uden
        # at køre kroppen → HELE post-process-pipelinen (memory, continuation,
        # fact_gate, diagnosis, fabrikations-nudge) dør STILLE. Det skete
        # 2026-06-14→06-21. Guard: opdag det, log CRITICAL, og drain alligevel
        # så pipelinen kører. (Yields i en post-done-tråd kan aldrig nå klienten
        # — brug event_bus/run-follow i stedet. Real-time-blok = pre-done.)
        import inspect as _inspect_pp
        if _inspect_pp.isgeneratorfunction(_post_process):
            logger.critical(
                "_post_process er en generator (yield i kroppen?) — drainer så "
                "pipelinen kører; FJERN yield'en og brug event_bus. run_id=%s",
                run.run_id,
            )

            def _drain_post_process() -> None:
                try:
                    for _ in _post_process():
                        pass
                except Exception:
                    logger.exception("_post_process drain fejlede")

            threading.Thread(target=_drain_post_process, daemon=True).start()
        else:
            threading.Thread(target=_post_process, daemon=True).start()

        # Phase 5: clear in-flight record. Runs reaching this finally block
        # have either completed, failed cleanly, or been cancelled — all
        # equally "no longer hanging", so the next prompt build won't
        # surface a stale "you were interrupted" notice.
        try:
            if _final_run_status == "interrupted":
                from core.services.in_flight_runs import mark_interrupted as _mark_run_interrupted
                _mark_run_interrupted(
                    run.run_id,
                    reason=_final_run_error or "interrupted",
                    summary=_final_run_error or "interrupted",
                )
            else:
                from core.services.in_flight_runs import (
                    clear_session as _clear_interrupted_session,
                    mark_completed as _mark_run_completed,
                )
                _mark_run_completed(run.run_id)
                _clear_interrupted_session(run.session_id)
        except Exception:
            pass


# Boy Scout-udtrækning (2026-06-30): stream-observabilitets-nerverne bor nu i
# visible_runs_sections.stream_observers (én testbar enhed). Re-eksporteret her
# som de gamle navne så call-sites/monkeypatches ikke knækker.
from core.services.visible_runs_sections.stream_observers import (  # noqa: E402
    observe_persist_failed as _observe_persist_failed,
    observe_streamed_text_recovered as _observe_streamed_text_recovered,
)


# Memory/continuity post-processing — udskilt til core/services/visible_runs_memory.py
# (Boy Scout 2026-07-07). Re-eksporteret i BUNDEN af filen så bare kald i
# _stream_visible_run + test-monkeypatches fortsat virker.
#
# Per-tur cognitive/candidate-tracking (_track_step_failed / _track_runtime_candidates)
# — udskilt til core/services/visible_runs_cognitive.py (Boy Scout 2026-07-07).
# Re-eksporteret i BUNDEN. De ~61 track_*-funktioner refereres dér via _vr.X så
# test-monkeypatches på visible_runs.track_xxx ses på kald-tidspunkt.


# Capability markup functions — udskilt til core/services/prompt_sections/capability_markup.py
from core.services.prompt_sections.capability_markup import (  # noqa: E402
    _CapabilityMarkupBuffer,
    _capability_call_state,
    _extract_capability_call,
    _extract_content_after_capability_tag,
    _parse_capability_attrs,
    _parse_capability_call_markup,
    _strip_capability_markup,
    _strip_tool_call_text_markup,
    _try_match_tool_text_markup,
    _visible_text_without_capability_markup,
)



_MAX_CAPABILITIES_PER_TURN = 5


def _native_tool_calls_to_capabilities(tool_calls: list[dict]) -> list[dict]:
    """Convert Ollama native tool_calls to capability-plan entries (legacy compat)."""
    from core.tools.workspace_capabilities import resolve_tool_call_to_capability

    caps: list[dict] = []
    for tc in tool_calls[:_MAX_CAPABILITIES_PER_TURN]:
        fn = tc.get("function") or {}
        name = str(fn.get("name") or "")
        arguments = fn.get("arguments") or {}
        # OpenAI-compat providers (Copilot, OpenCode, Groq, ...) serialize
        # tool_call arguments as a JSON string per the OpenAI wire spec.
        # Downstream executors expect a dict, so parse once here.
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments.strip() else {}
            except (ValueError, TypeError):
                arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        if not name:
            continue
        resolved = resolve_tool_call_to_capability(name, arguments)
        capability_id = resolved.get("capability_id") or ""
        if not capability_id:
            continue
        cap_args: dict[str, str] = {}
        if resolved.get("command_text"):
            cap_args["command_text"] = str(resolved["command_text"])
        if resolved.get("target_path"):
            cap_args["target_path"] = str(resolved["target_path"])
        if resolved.get("write_content"):
            cap_args["write_content"] = str(resolved["write_content"])
        caps.append({
            "capability_id": capability_id,
            "arguments": cap_args,
            "source": "native-tool-call",
            "tool_name": name,
        })
    return caps


# _execute_simple_tool_calls extracted to core/services/simple_tool_executor.py
# (Boy-Scout, 2026-07-08). Re-exported for backward compatibility — existing
# callers (`_ctx_for_agentic_exec.run(_execute_simple_tool_calls, ...)`) and the
# tests importing it from visible_runs keep working unchanged. The extracted
# module imports visible_runs lazily (inside the function), so this module-level
# import does not create a cycle.
from core.services.simple_tool_executor import _execute_simple_tool_calls  # noqa: E402,F401
# Path B (local_tool_exec) executor — same 5-key result shape, but waits on the
# local_tool_broker for the client's result instead of running the tool server-side.
from core.services.simple_tool_executor import _execute_local_tool_calls  # noqa: E402,F401
# Shared announce→execute→heartbeat pump (Boy-Scout extraction 2026-07-19). Imported
# at module level; visible_tool_exec imports THIS module lazily → no cycle.
from core.services.visible_tool_exec import run_tool_batch  # noqa: E402,F401


def _run_grounded_capability_followup(
    run: VisibleRun,
    *,
    capability_id: str,
    invocation: dict[str, object],
    initial_model_text: str,
) -> VisibleModelResult | None:
    followup_message = _build_grounded_capability_followup_message(
        run,
        capability_id=capability_id,
        invocation=invocation,
        initial_model_text=initial_model_text,
    )
    try:
        return execute_visible_model(
            message=followup_message,
            provider=run.provider,
            model=run.model,
            session_id=run.session_id,
        )
    except Exception as exc:
        _update_visible_execution_trace(
            run,
            {
                "provider_second_pass_status": "failed",
                "provider_error_summary": str(exc) or "second-pass-provider-error",
            },
        )
        return None


def _build_grounded_capability_followup_message(
    run: VisibleRun,
    *,
    capability_id: str,
    invocation: dict[str, object],
    initial_model_text: str,
) -> str:
    execution_mode = str(invocation.get("execution_mode") or "unknown")
    status = str(invocation.get("status") or "unknown")
    result = invocation.get("result") or {}
    detail = str(invocation.get("detail") or "").strip()
    result_text = ""
    if isinstance(result, dict):
        result_text = str(result.get("text") or "").strip()
    parts = [
        "Second-pass visible response task.",
        "You have already completed one bounded capability invocation for the current user turn.",
        "Respond to the user in ordinary prose only.",
        "Every substantive claim must be grounded in the capability result below.",
        "If runtime facts are thin, say what remains uncertain instead of smoothing it over.",
        "If documentation and code or command output conflict, prefer code and command output.",
        "README or file-structure summaries do not outrank direct code/file evidence.",
        "If the user asked for code analysis, do not call this a code analysis unless you have actually read concrete code files.",
        "If more read-only data is clearly needed and the task is still bounded, you may emit more <capability-call ... /> tags instead of asking the user for permission to continue.",
        "Only ask the user to continue when the next step needs approval or the goal is genuinely unclear.",
        f"Original user message: {run.user_message}",
        f"Capability used: {capability_id}",
        f"Capability status: {status}",
        f"Capability execution mode: {execution_mode}",
    ]
    if _is_memory_commit_request(run.user_message):
        parts.append(
            "If the user asked you to remember or save something and the write succeeded, state that it has been saved. Do not talk about syntax unless the runtime result explicitly failed."
        )
    if result_text:
        parts.append("Capability result text:")
        parts.append(result_text)
    elif detail:
        parts.append(f"Capability result detail: {detail}")
    return "\n".join(parts)


def _run_grounded_multi_capability_followup(
    run: VisibleRun,
    *,
    capability_results: list[dict[str, object]],
    initial_model_text: str,
) -> VisibleModelResult | None:
    followup_message = _build_grounded_multi_capability_followup_message(
        run,
        capability_results=capability_results,
        initial_model_text=initial_model_text,
    )
    try:
        return execute_visible_model(
            message=followup_message,
            provider=run.provider,
            model=run.model,
            session_id=run.session_id,
        )
    except Exception as exc:
        _update_visible_execution_trace(
            run,
            {
                "provider_second_pass_status": "failed",
                "provider_error_summary": str(exc) or "second-pass-provider-error",
            },
        )
        return None


def _build_grounded_multi_capability_followup_message(
    run: VisibleRun,
    *,
    capability_results: list[dict[str, object]],
    initial_model_text: str,
) -> str:
    n = len(capability_results)
    parts = [
        "Second-pass visible response task.",
        f"You executed {n} capabilit{'y' if n == 1 else 'ies'} this turn. Results are below.",
        "",
        "Respond to the user grounded in these results.",
        "Every substantive claim must be grounded in one or more concrete capability results below.",
        "If runtime facts are thin, stale, or conflicting, say that plainly.",
        "If docs and code disagree, prefer code and direct command/file output.",
        "README, pyproject, or directory names are not enough for a real code analysis by themselves.",
        "If the user asked for code analysis, do not stop at structure or documentation; read concrete code files before claiming analysis.",
        "If more read-only data is clearly needed and the task is still bounded, emit additional <capability-call ... /> tags now and continue autonomously.",
        "Only ask the user to continue when the next step needs approval or the goal is genuinely unclear.",
        "",
        f"Original user message: {run.user_message}",
    ]
    if _is_memory_commit_request(run.user_message):
        parts.append(
            "If the user asked you to remember or save something and the write succeeded, state that it has been saved. Do not describe block syntax or retry mechanics unless the runtime result explicitly failed."
        )
    if _is_code_analysis_request(run.user_message):
        parts.append(
            "Code-analysis mode: prioritize concrete files such as entrypoints, routes, services, core modules, and tests. Do not present README-only or tree-only summaries as code analysis."
        )
    for i, cr in enumerate(capability_results):
        parts.append("")
        parts.append(f"--- Capability {i + 1}: {cr['capability_id']} ---")
        parts.append(f"Status: {cr['status']}")
        parts.append(f"Execution mode: {cr['execution_mode']}")
        result_text = str(cr.get("result_text") or "").strip()
        detail = str(cr.get("detail") or "").strip()
        if result_text:
            parts.append("Result:")
            parts.append(result_text)
        elif detail:
            parts.append(f"Detail: {detail}")
    return "\n".join(parts)


def _is_code_analysis_request(user_message: str) -> bool:
    normalized = str(user_message or "").lower()
    return any(
        token in normalized
        for token in (
            "code analysis",
            "kode analyse",
            "kodeanalyse",
            "codeanalyse",
            "gennemgang",
            "walkthrough",
            "review koden",
            "analyse af koden",
            "analyse main repo",
            "analyser main repo",
        )
    )


def _is_memory_commit_request(user_message: str) -> bool:
    normalized = str(user_message or "").lower()
    return any(
        token in normalized
        for token in (
            "remember this",
            "remember that",
            "husk dette",
            "husk det",
            "gem dette",
            "gem det",
            "this is important",
            "det er vigtigt",
            "do not forget",
            "glem ikke",
        )
    )



def _finalize_second_pass_visible_text(text: str, *, fallback: str) -> str:
    plan = _extract_capability_plan(text)
    cleaned = _visible_text_without_capability_markup(
        text,
        had_markup=bool(plan["had_markup"]),
    )
    if cleaned:
        return cleaned
    return fallback



def _bounded_error(error_message: str, limit: int = 160) -> str:
    normalized = " ".join((error_message or "").split()) or "visible-run-failed"
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class PresentationInvariantError(RuntimeError):
    """Raised when user-visible text contains internal runtime markers.

    Internal runtime artifacts — tool-result markers like ``[search_memory]:``,
    completion placeholders like ``[Completed: foo]`` — must never leak into
    the visible chat stream or persisted assistant messages. This exception
    exists so regressions fail loudly rather than silently polluting user UX.
    """


_PRESENTATION_INVARIANT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*\[Completed(?:[:\]]|$)"),
    # [tool_name]: ... at start of message (bare or wrapped in (...))
    re.compile(r"^\s*[\(\[]?\s*\[[a-z_][a-z0-9_]*\]\s*:", re.IGNORECASE),
)

# Tool-call signature anywhere in the text — e.g. "([send_webchat_message]: {"
# or "[send_mail]: {". A literal `[name]: {` followed by JSON-ish payload is
# never legitimate user-visible content; it's the model emitting a tool call
# as prose instead of a structured tool_calls field.
_TOOL_CALL_LEAK_PATTERN = re.compile(
    r"\[[a-z_][a-z0-9_]*\]\s*:\s*\{",
    re.IGNORECASE,
)


def _assert_presentation_invariant(text: str) -> None:
    stripped = (text or "").lstrip()
    if not stripped:
        return
    for pattern in _PRESENTATION_INVARIANT_PATTERNS:
        if pattern.match(stripped):
            logger.warning(
                "presentation-invariant-leak kind=marker preview=%r",
                stripped[:120],
            )
            raise PresentationInvariantError(
                f"internal runtime marker leaked into user-visible text: "
                f"{stripped[:80]!r}"
            )
    if _TOOL_CALL_LEAK_PATTERN.search(stripped):
        logger.warning(
            "presentation-invariant-leak kind=tool-call-as-prose preview=%r",
            stripped[:200],
        )
        raise PresentationInvariantError(
            f"tool-call emitted as prose instead of structured tool_calls: "
            f"{stripped[:120]!r}"
        )


_TOOL_LABELS: dict[str, str] = {
    # Filer
    "read_file": "Læser fil",
    "write_file": "Skriver fil",
    "edit_file": "Redigerer fil",
    "find_files": "Søger filer",
    "search": "Søger i filer",
    "read_archive": "Læser arkiv",
    "publish_file": "Publicerer fil",
    # System
    "bash": "Kører kommando",
    "internal_api": "Kalder intern API",
    "db_query": "Forespørger database",
    "update_setting": "Opdaterer indstilling",
    "compact_context": "Komprimerer kontekst",
    # Web
    "web_fetch": "Henter webside",
    "web_scrape": "Skraber webside",
    "web_search": "Søger på nettet",
    "get_weather": "Henter vejr",
    "geolocation_lookup": "Finder lokation",
    "geocode": "Slår adresse op",
    "reverse_geocode": "Slår koordinater op",
    "route_directions": "Beregner rute",
    "nearby_search": "Søger i nærheden",
    "create_team": "Opretter team",
    "list_teams": "Lister teams",
    "invite_to_team": "Inviterer til team",
    "get_news": "Henter nyheder",
    "get_exchange_rate": "Henter valutakurs",
    "wolfram_query": "Beregner (Wolfram)",
    # Hukommelse og identitet
    "search_memory": "Søger i hukommelse",
    "read_chronicles": "Læser krøniker",
    "read_dreams": "Læser drømme",
    "read_self_state": "Læser selvtilstand",
    "read_model_config": "Læser modelkonfig",
    "read_mood": "Læser stemning",
    "adjust_mood": "Justerer stemning",
    "read_self_docs": "Læser selvdokumentation",
    "read_tool_result": "Læser tool-resultat",
    "recall_council_conclusions": "Henter rådskonklusioner",
    # Sanser
    "analyze_image": "Analyserer billede",
    "look_around": "Kigger rundt",
    "deep_analyze": "Dybdeanalyserer",
    # Initiativer og opgaver
    "push_initiative": "Registrerer initiativ",
    "list_initiatives": "Lister initiativer",
    "schedule_task": "Planlægger opgave",
    "list_scheduled_tasks": "Lister planlagte opgaver",
    "cancel_task": "Annullerer opgave",
    "edit_task": "Redigerer opgave",
    "queue_followup": "Kø-stiller opfølgning",
    # Kode og forslag
    "propose_source_edit": "Foreslår kodeændring",
    "propose_git_commit": "Foreslår commit",
    "approve_proposal": "Godkender forslag",
    "list_proposals": "Lister forslag",
    # Projekt
    "my_project_status": "Læser projektstatus",
    "my_project_journal_write": "Skriver projektlog",
    "my_project_accept_proposal": "Godkender projektforslag",
    "my_project_declare": "Deklarerer projekt",
    # System/runtime
    "heartbeat_status": "Tjekker heartbeat",
    "trigger_heartbeat_tick": "Trigger heartbeat",
    "daemon_status": "Tjekker daemons",
    "control_daemon": "Styrer daemon",
    "list_signal_surfaces": "Lister signalflader",
    "read_signal_surface": "Læser signalflade",
    "eventbus_recent": "Læser eventbus",
    # Kommunikation
    "search_chat_history": "Søger i chathistorik",
    "discord_status": "Tjekker Discord",
    "send_telegram_message": "Sender Telegram-besked",
    "send_ntfy": "Sender notifikation",
    "notify_user": "Notificerer bruger",
    "send_webchat_message": "Sender webchat-besked",
    "send_discord_dm": "Sender Discord DM",
    "discord_channel": "Tilgår Discord-kanal",
    # Råd og agenter
    "convene_council": "Indkalder råd",
    "quick_council_check": "Hurtig rådscheck",
    "spawn_agent_task": "Spawner agent",
    "send_message_to_agent": "Sender besked til agent",
    "list_agents": "Lister agenter",
    "relay_to_agent": "Videresender til agent",
    "cancel_agent": "Annullerer agent",
    # Smart home
    "home_assistant": "Home Assistant",
}


def _tool_label(tool_name: str, arguments: dict | None = None) -> str:
    base = _TOOL_LABELS.get(str(tool_name or ""), str(tool_name or "tool"))
    if not arguments:
        return base
    # Append a short context hint from the arguments
    hint = ""
    name = str(tool_name or "")
    if name in {"read_file", "write_file", "edit_file", "publish_file"}:
        path = str(arguments.get("path") or arguments.get("file_path") or "")
        if path:
            hint = path.split("/")[-1]  # basename only
    elif name == "find_files":
        hint = str(arguments.get("pattern") or arguments.get("path") or "")[:40]
    elif name in {"search", "web_search", "search_memory", "search_chat_history"}:
        hint = str(arguments.get("query") or arguments.get("q") or "")[:40]
    elif name == "web_fetch":
        url = str(arguments.get("url") or "")
        hint = url.replace("https://", "").replace("http://", "").split("/")[0][:40]
    elif name == "bash":
        cmd = str(arguments.get("command") or "")
        hint = cmd.split()[0][:30] if cmd else ""
    elif name in {"discord_channel", "send_discord_dm"}:
        hint = str(arguments.get("channel") or arguments.get("user") or "")[:30]
    elif name == "home_assistant":
        hint = str(arguments.get("action") or arguments.get("entity_id") or "")[:30]
    elif name in {"spawn_agent_task", "send_message_to_agent", "relay_to_agent", "cancel_agent"}:
        hint = str(arguments.get("agent_id") or arguments.get("task_id") or "")[:20]
    return f"{base}: {hint}" if hint else base


def _parse_tc_args(tc: dict) -> dict:
    """Extract arguments dict from a tool call (handles both string and dict forms)."""
    raw = (tc.get("function") or {}).get("arguments") or tc.get("arguments") or {}
    if isinstance(raw, str):
        try:
            import json as _json
            return _json.loads(raw)
        except Exception:
            return {}
    return dict(raw) if isinstance(raw, dict) else {}


def _maybe_fallback_for_autonomous(
    run: VisibleRun, exc: BaseException,
) -> dict[str, object] | None:
    """Task 10-beslutningsseam: skal en fejlet model-stream faldes til poolen?

    Returnerer fallback-dict'en (med `text`/`lane`/`provider`) NÅR runet er
    autonomt OG poolen leverede indhold. Returnerer None når runet skal fejle
    som i dag — hvilket betyder at kaldstedet kører sin uændrede fejl-sti.

    Invarianter:
      * `run.autonomous is True` er den ENESTE indgangsbetingelse. Synlige
        (bruger-tilstedeværende) runs → øjeblikkelig None → de rører ALDRIG
        fallback'en, og deres exception propagerer præcis som før.
      * Pool-gaten sidder i helperens eget flag (default OFF). Vi sender et
        `primary_call` der straks re-raiser den allerede-fangede `exc`:
          - flag OFF → helper re-raiser exc → vi fanger og returnerer None
            (dagens adfærd, også for autonome runs);
          - flag ON  → helper går direkte til sin cheap-pool-arm (primær er
            "allerede prøvet" — ollama-streamen fejlede jo her).
    """
    if not run.autonomous:
        return None

    def _primary_reraise() -> dict[str, object]:
        # Ollama-streamen fejlede allerede her; primær er "allerede prøvet".
        # Re-raise → helper går straks til cheap-pool-arm (flag ON) eller
        # re-raiser videre (flag OFF).
        raise exc

    try:
        result = run_non_visible_with_fallback(
            message=run.user_message,
            primary_call=_primary_reraise,
            run_is_autonomous=True,
            task_kind="autonomous",
        )
    except Exception:
        # Flag OFF (helper re-raiste), eller pool udtømt uden floor → fejl som
        # i dag. Kaldstedet kører sin normale fejl-sti.
        return None

    return result if isinstance(result, dict) else None


def _complete_visible_run_from_fallback(
    run: VisibleRun, fallback: dict[str, object],
) -> AsyncIterator[str]:
    """Terminal completion for et AUTONOMT run hvis model-stream fejlede og blev
    reddet af den gratis cheap-lane pool. Emitterer pool-teksten som ét (ikke-
    streamet) delta + et completed/done-par. Bruges ALDRIG for synlige runs
    (de når aldrig fallback'en). Pointen: runet FULDFØRER med indhold i stedet
    for at fejle."""
    controller = get_visible_run_controller(run.run_id)
    finished_at = datetime.now(UTC).isoformat()
    text = str(fallback.get("text") or "")
    lane = str(fallback.get("lane") or "")
    provider = str(fallback.get("provider") or "")
    _update_visible_execution_trace(
        run,
        {
            "final_status": "completed",
            "provider_first_pass_status": "autonomous_fallback_pool",
            "provider_error_summary": (
                f"autonomous-fallback:{lane or 'pool'}:{provider or '?'}"
            ),
        },
    )
    _persist_session_assistant_message(run, text)
    set_last_visible_run_outcome(
        run, status="completed", text_preview=text[:140],
    )
    _set_orb_phase("idle")
    yield _sse("trace", _visible_trace_payload(run))
    if text:
        yield _sse(
            "delta",
            {"type": "delta", "run_id": run.run_id, "delta": text},
        )
    event_bus.publish(
        "runtime.visible_run_completed",
        {
            "run_id": run.run_id,
            "lane": run.lane,
            "provider": provider or run.provider,
            "model": run.model,
            "status": "completed",
            "started_at": controller.started_at if controller else None,
            "finished_at": finished_at,
            "cost_usd": 0.0,
            "autonomous_fallback": True,
        },
    )
    yield _sse(
        "done",
        {
            "type": "done",
            "run_id": run.run_id,
            "status": "completed",
        },
    )


def _fail_visible_run(
    run: VisibleRun,
    error_message: str,
    *,
    partial_text: str = "",
) -> AsyncIterator[str]:
    controller = get_visible_run_controller(run.run_id)
    finished_at = datetime.now(UTC).isoformat()
    bounded_error = _bounded_error(error_message)
    interruption = _classify_visible_run_interruption(
        (
            (get_last_visible_execution_trace() or {}).get("provider_error_summary")
            or bounded_error
        )
    )
    _update_visible_execution_trace(
        run,
        {
            "final_status": "failed",
            "provider_error_summary": (
                get_last_visible_execution_trace() or {}
            ).get("provider_error_summary")
            or bounded_error,
        },
    )
    _set_orb_phase("idle")
    yield _sse("trace", _visible_trace_payload(run))
    # If we have accumulated partial text that the frontend hasn't seen
    # (e.g. because the provider stream was killed mid-token), send it
    # before the failed/done events so the user sees what was produced.
    partial = (partial_text or "").strip()
    if partial:
        yield _sse(
            "delta",
            {
                "type": "delta",
                "run_id": run.run_id,
                "delta": partial,
            },
        )
    event_bus.publish(
        "runtime.visible_run_failed",
        {
            "run_id": run.run_id,
            "lane": run.lane,
            "provider": run.provider,
            "model": run.model,
            "status": "failed",
            "started_at": controller.started_at if controller else None,
            "finished_at": finished_at,
            "error": bounded_error,
            **interruption,
        },
    )
    yield _sse(
        "failed",
        {
            "type": "failed",
            "run_id": run.run_id,
            "status": "failed",
            "error": bounded_error,
        },
    )
    yield _sse(
        "done",
        {
            "type": "done",
            "run_id": run.run_id,
            "status": "failed",
            "error": bounded_error,
        },
    )


def _cancel_visible_run(run: VisibleRun) -> AsyncIterator[str]:
    controller = get_visible_run_controller(run.run_id)
    shared = _get_visible_run_control(run.run_id)
    finished_at = datetime.now(UTC).isoformat()
    interruption = _classify_visible_run_interruption(
        str(
            (get_last_visible_execution_trace() or {}).get("provider_error_summary")
            or "cancelled"
        )
    )
    _update_visible_execution_trace(
        run,
        {
            "final_status": "cancelled",
            "provider_first_pass_status": (
                get_last_visible_execution_trace() or {}
            ).get("provider_first_pass_status")
            or "cancelled",
        },
    )
    _set_orb_phase("idle")
    yield _sse("trace", _visible_trace_payload(run))
    event_bus.publish(
        "runtime.visible_run_cancelled",
        {
            "run_id": run.run_id,
            "lane": run.lane,
            "provider": run.provider,
            "model": run.model,
            "status": "cancelled",
            "started_at": controller.started_at if controller else shared.get("started_at"),
            "finished_at": finished_at,
            **interruption,
        },
    )
    yield _sse(
        "cancelled",
        {
            "type": "cancelled",
            "run_id": run.run_id,
            "status": "cancelled",
        },
    )
    yield _sse(
        "done",
        {
            "type": "done",
            "run_id": run.run_id,
            "status": "cancelled",
        },
    )


def register_visible_run(run: VisibleRun) -> VisibleRunController:
    started_at = datetime.now(UTC).isoformat()
    controller = VisibleRunController(
        run_id=run.run_id,
        lane=run.lane,
        provider=run.provider,
        model=run.model,
        started_at=started_at,
        user_message_preview=_preview_text(run.user_message),
        trust_all=bool(getattr(run, "trust_all", False)),
    )
    _VISIBLE_RUN_CONTROLLERS[run.run_id] = controller
    state = {
        "active": True,
        "run_id": run.run_id,
        "session_id": str(run.session_id or ""),
        "lane": run.lane,
        "provider": run.provider,
        "model": run.model,
        "started_at": started_at,
        "current_user_message_preview": controller.user_message_preview,
        "capability_id": None,
        "cancelled": False,
        "updated_at": started_at,
    }
    _set_visible_run_control(run.run_id, state)
    _set_active_visible_run(state)
    return controller


def get_visible_run_controller(run_id: str) -> VisibleRunController | None:
    return _VISIBLE_RUN_CONTROLLERS.get(run_id)


def cancel_visible_run(run_id: str) -> bool:
    controller = get_visible_run_controller(run_id)
    shared = _get_visible_run_control(run_id)
    if controller is None and not shared:
        return False
    _mark_visible_run_cancelled(run_id)
    if controller is not None:
        controller.cancel()
    return True


def unregister_visible_run(run_id: str) -> None:
    controller = _VISIBLE_RUN_CONTROLLERS.pop(run_id, None)
    state = _get_visible_run_control(run_id)
    if state:
        state["active"] = False
        state["updated_at"] = datetime.now(UTC).isoformat()
        _set_visible_run_control(run_id, state)
    active = _get_active_visible_run_state()
    if str(active.get("run_id") or "") == run_id:
        _set_active_visible_run({})
    if controller is not None:
        controller.clear_stream()


def get_active_visible_run() -> dict[str, str] | None:
    active = _get_active_visible_run_state()
    if not active:
        return None
    if not bool(active.get("active", True)):
        return None
    return {
        "active": True,
        "run_id": str(active.get("run_id") or ""),
        "lane": str(active.get("lane") or ""),
        "provider": str(active.get("provider") or ""),
        "model": str(active.get("model") or ""),
        "started_at": str(active.get("started_at") or ""),
        "current_user_message_preview": str(active.get("current_user_message_preview") or ""),
        "capability_id": active.get("capability_id"),
        "cancelled": bool(active.get("cancelled")),
        # C2b: session_id + origin lader desk/mobil afgøre takeover ("en anden session
        # har overtaget samtalen") ved at sammenligne mod klientens egen session.
        "session_id": str(active.get("session_id") or ""),
        "origin": str(active.get("origin") or ""),
    }


def get_visible_work() -> dict[str, object]:
    active_run = get_active_visible_run()
    if active_run:
        return {
            "active": True,
            "run_id": active_run.get("run_id"),
            "status": "running",
            "lane": active_run.get("lane"),
            "provider": active_run.get("provider"),
            "model": active_run.get("model"),
            "started_at": active_run.get("started_at"),
            "current_user_message_preview": active_run.get(
                "current_user_message_preview"
            ),
            "capability_id": active_run.get("capability_id"),
        }

    last_outcome = get_last_visible_run_outcome() or {}
    last_capability_use = get_last_visible_capability_use() or {}
    return {
        "active": False,
        "run_id": last_outcome.get("run_id"),
        "status": last_outcome.get("status") or "idle",
        "lane": last_outcome.get("lane"),
        "provider": last_outcome.get("provider"),
        "model": last_outcome.get("model"),
        "started_at": None,
        "current_user_message_preview": last_outcome.get("text_preview"),
        "capability_id": last_capability_use.get("capability_id"),
    }


def get_visible_work_surface() -> dict[str, object]:
    visible_work = get_visible_work()
    recent_units = recent_visible_work_units(limit=5)
    current_unit = recent_units[0] if recent_units else {}
    return {
        "active": bool(visible_work.get("active")),
        "current_work_id": current_unit.get("work_id"),
        "current_run_id": visible_work.get("run_id") or current_unit.get("run_id"),
        "status": visible_work.get("status") or current_unit.get("status"),
        "lane": visible_work.get("lane") or current_unit.get("lane"),
        "provider": visible_work.get("provider") or current_unit.get("provider"),
        "model": visible_work.get("model") or current_unit.get("model"),
        "started_at": visible_work.get("started_at") or current_unit.get("started_at"),
        "finished_at": current_unit.get("finished_at"),
        "current_user_message_preview": visible_work.get("current_user_message_preview")
        or current_unit.get("user_message_preview"),
        "capability_id": visible_work.get("capability_id")
        or current_unit.get("capability_id"),
        "recent_work_ids": [
            str(item.get("work_id") or "").strip()
            for item in recent_units
            if str(item.get("work_id") or "").strip()
        ],
        "latest_work_preview": current_unit.get("work_preview"),
    }


def get_visible_selected_work_surface() -> dict[str, object]:
    visible_work_surface = get_visible_work_surface()
    recent_units = recent_visible_work_units(limit=5)
    selected_unit = recent_units[0] if recent_units else {}
    return {
        "active": bool(visible_work_surface.get("active")),
        "selected_work_id": visible_work_surface.get("current_work_id")
        or selected_unit.get("work_id"),
        "selected_run_id": visible_work_surface.get("current_run_id")
        or selected_unit.get("run_id"),
        "status": visible_work_surface.get("status") or selected_unit.get("status"),
        "lane": visible_work_surface.get("lane") or selected_unit.get("lane"),
        "provider": visible_work_surface.get("provider")
        or selected_unit.get("provider"),
        "model": visible_work_surface.get("model") or selected_unit.get("model"),
        "selected_user_message_preview": visible_work_surface.get(
            "current_user_message_preview"
        )
        or selected_unit.get("user_message_preview"),
        "selected_capability_id": visible_work_surface.get("capability_id")
        or selected_unit.get("capability_id"),
        "selected_work_preview": visible_work_surface.get("latest_work_preview")
        or selected_unit.get("work_preview"),
        "recent_work_ids": [
            str(item.get("work_id") or "").strip()
            for item in recent_units
            if str(item.get("work_id") or "").strip()
        ],
    }


def get_visible_selected_work_item() -> dict[str, object]:
    visible_work = get_visible_work()
    visible_work_surface = get_visible_work_surface()
    visible_selected_work_surface = get_visible_selected_work_surface()
    recent_units = recent_visible_work_units(limit=5)
    selected_unit = recent_units[0] if recent_units else {}
    return {
        "active": bool(visible_selected_work_surface.get("active")),
        "selected_work_id": visible_selected_work_surface.get("selected_work_id")
        or visible_work_surface.get("current_work_id")
        or selected_unit.get("work_id"),
        "selected_run_id": visible_selected_work_surface.get("selected_run_id")
        or visible_work_surface.get("current_run_id")
        or visible_work.get("run_id")
        or selected_unit.get("run_id"),
        "selected_status": visible_selected_work_surface.get("status")
        or visible_work_surface.get("status")
        or selected_unit.get("status"),
        "selected_lane": visible_selected_work_surface.get("lane")
        or visible_work_surface.get("lane")
        or selected_unit.get("lane"),
        "selected_provider": visible_selected_work_surface.get("provider")
        or visible_work_surface.get("provider")
        or selected_unit.get("provider"),
        "selected_model": visible_selected_work_surface.get("model")
        or visible_work_surface.get("model")
        or selected_unit.get("model"),
        "selected_user_message_preview": visible_selected_work_surface.get(
            "selected_user_message_preview"
        )
        or visible_work_surface.get("current_user_message_preview")
        or selected_unit.get("user_message_preview"),
        "selected_capability_id": visible_selected_work_surface.get(
            "selected_capability_id"
        )
        or visible_work_surface.get("capability_id")
        or selected_unit.get("capability_id"),
        "selected_work_preview": visible_selected_work_surface.get(
            "selected_work_preview"
        )
        or visible_work_surface.get("latest_work_preview")
        or selected_unit.get("work_preview"),
        "recent_work_ids": list(
            visible_selected_work_surface.get("recent_work_ids") or []
        ),
        "selection_source": "active-visible-work"
        if visible_selected_work_surface.get("active")
        else "persisted-visible-work-unit",
        "recent_count": len(recent_units),
    }


def get_visible_selected_work_note() -> dict[str, object]:
    selected_work_item = get_visible_selected_work_item()
    recent_notes = recent_visible_work_notes(limit=5)
    selected_note = recent_notes[0] if recent_notes else {}
    return {
        "active": bool(selected_note),
        "note_id": selected_note.get("note_id"),
        "work_id": selected_note.get("work_id")
        or selected_work_item.get("selected_work_id"),
        "run_id": selected_note.get("run_id")
        or selected_work_item.get("selected_run_id"),
        "status": selected_note.get("status")
        or selected_work_item.get("selected_status"),
        "lane": selected_note.get("lane") or selected_work_item.get("selected_lane"),
        "provider": selected_note.get("provider")
        or selected_work_item.get("selected_provider"),
        "model": selected_note.get("model") or selected_work_item.get("selected_model"),
        "user_message_preview": selected_note.get("user_message_preview")
        or selected_work_item.get("selected_user_message_preview"),
        "capability_id": selected_note.get("capability_id")
        or selected_work_item.get("selected_capability_id"),
        "work_preview": selected_note.get("work_preview")
        or selected_work_item.get("selected_work_preview"),
        "selection_source": selected_note.get("projection_source")
        or selected_work_item.get("selection_source"),
        "created_at": selected_note.get("created_at"),
        "finished_at": selected_note.get("finished_at"),
        "recent_note_ids": [
            str(item.get("note_id") or "").strip()
            for item in recent_notes
            if str(item.get("note_id") or "").strip()
        ],
    }


def get_last_visible_run_outcome() -> dict[str, str] | None:
    return dict(_LAST_VISIBLE_RUN_OUTCOME) if _LAST_VISIBLE_RUN_OUTCOME else None


def get_last_visible_capability_use() -> dict[str, object] | None:
    if not _LAST_VISIBLE_CAPABILITY_USE:
        return None
    return {
        **dict(_LAST_VISIBLE_CAPABILITY_USE),
        "trace": get_last_visible_execution_trace(),
    }


def get_last_visible_execution_trace() -> dict[str, object] | None:
    return dict(_LAST_VISIBLE_EXECUTION_TRACE) if _LAST_VISIBLE_EXECUTION_TRACE else None


_EMPTY_RUN_FALLBACK = (
    "Jeg nåede ikke at formulere et færdigt svar den gang — spørg mig gerne "
    "igen, så tager jeg den forfra."
)


def set_last_visible_capability_use(
    run: VisibleRun,
    *,
    capability_id: str,
    invocation: dict[str, object],
    capability_arguments: dict[str, str] | None = None,
    argument_source: str = "none",
) -> None:
    global _LAST_VISIBLE_CAPABILITY_USE
    controller = get_visible_run_controller(run.run_id)
    if controller is not None:
        controller.last_capability_id = capability_id
    state = _get_visible_run_control(run.run_id)
    if state:
        state["capability_id"] = capability_id
        state["updated_at"] = datetime.now(UTC).isoformat()
        _set_visible_run_control(run.run_id, state)
        active = _get_active_visible_run_state()
        if str(active.get("run_id") or "") == run.run_id:
            _set_active_visible_run({**active, "capability_id": capability_id, "updated_at": state["updated_at"]})
    capability = invocation.get("capability")
    result = invocation.get("result") or {}
    result_preview = None
    if isinstance(result, dict):
        text = str(result.get("text", "")).strip()
        if text:
            result_preview = _preview_text(text)
        elif isinstance(result.get("matches"), list) and result["matches"]:
            excerpt = str((result["matches"][0] or {}).get("excerpt", "")).strip()
            if excerpt:
                result_preview = _preview_text(excerpt)

    _LAST_VISIBLE_CAPABILITY_USE = {
        "run_id": run.run_id,
        "lane": run.lane,
        "provider": run.provider,
        "model": run.model,
        "capability_id": capability_id,
        "capability": capability,
        "status": invocation.get("status"),
        "execution_mode": invocation.get("execution_mode"),
        "used_at": datetime.now(UTC).isoformat(),
        "result_preview": result_preview,
        "detail": invocation.get("detail"),
        "parsed_arguments": dict(capability_arguments or {}),
        "argument_source": argument_source,
        "trace": get_last_visible_execution_trace(),
    }


def _update_cognitive_systems_async(
    *,
    run_id: str,
    user_message: str,
    assistant_response: str,
    outcome_status: str,
) -> None:
    """Fire-and-forget updates to all cognitive accumulation systems."""
    import threading

    def _run() -> None:
        try:
            from core.services.personality_vector import (
                update_personality_vector_async,
            )
            update_personality_vector_async(
                run_id=run_id,
                user_message=user_message,
                assistant_response=assistant_response,
                outcome_status=outcome_status,
            )
        except Exception:
            pass

        try:
            from core.services.taste_profile import update_taste_async
            # Detect correction: user message contains correction markers
            msg_lower = user_message.lower()
            was_corrected = any(
                m in msg_lower
                for m in ("nej", "forkert", "ikke det", "det er stadig", "prøv igen")
            )
            update_taste_async(
                run_id=run_id,
                user_message=user_message,
                was_corrected=was_corrected,
                outcome_status=outcome_status,
            )
        except Exception:
            pass

        try:
            from core.services.relationship_texture import (
                update_relationship_async,
            )
            update_relationship_async(
                run_id=run_id,
                user_message=user_message,
                assistant_response=assistant_response,
                outcome_status=outcome_status,
            )
        except Exception:
            pass

        # Fase C konsolidering (2026-07-01): habit_tracker.track_habit_from_run (88L stub uden friction/
        # suggestion) er AFLØST af habits_pipeline.record_habit_signal (kaldt nedenfor). Dual-write fjernet
        # så kun det levende pipeline-lag skriver — dual-truth væk.

        try:
            from core.services.shared_language import scan_for_shared_terms
            scan_for_shared_terms(
                user_message=user_message,
                assistant_response=assistant_response,
                run_id=run_id,
            )
        except Exception:
            pass

        try:
            from core.services.rhythm_engine import update_rhythm_state
            update_rhythm_state()
        except Exception:
            pass

        # --- User emotional resonance ---
        detected_mood = "neutral"
        try:
            from core.services.user_emotional_resonance import detect_user_mood
            mood_result = detect_user_mood(
                user_message=user_message,
                run_id=run_id,
            )
            detected_mood = mood_result.get("detected_mood", "neutral")
        except Exception:
            pass

        # --- Baggrunds-recall (12. jul): kør den tunge relevans-scoring HER, på
        # turens faktiske besked, i stedet for inline i næste turs prompt-assembly.
        # Bevarer samme ét-turs-kadence (minder for denne besked er klar til næste
        # tur), samme LLM-dommer — men fjerner ~2-4,6s fra TTFT og undgår at recall
        # scorer imod en autonom runs tekst. Kill-switch: background_recall_enabled.
        try:
            from core.services.recall_scheduler import trigger_background_recall
            trigger_background_recall(user_message)
        except Exception:
            pass

        # --- Experiential memory ---
        try:
            from core.services.experiential_memory import (
                create_experiential_memory_async,
            )
            create_experiential_memory_async(
                run_id=run_id,
                user_message=user_message,
                assistant_response=assistant_response,
                outcome_status=outcome_status,
                user_mood=detected_mood,
            )
        except Exception:
            pass

        # --- Morning thread — kontinuitet der føles ---
        # Fyrer kun ved ægte nye sessioner (>30 min gap siden sidst).
        # Genererer én sætning om hvad Jarvis bærer med sig fra i går,
        # som bliver første indre tanke i denne session.
        try:
            from core.services.session_continuity import generate_morning_thread
            generate_morning_thread()
        except Exception:
            pass

        # --- Auto-seed planting from conversation ---
        try:
            from core.services.seed_system import auto_plant_seeds_from_conversation
            auto_plant_seeds_from_conversation(user_message=user_message)
        except Exception:
            pass

        # --- Context-based seed activation ---
        # Use user_message as current_context so seeds with
        # activate_on_context matching keywords in the message can sprout.
        # This was a broken link before: seeds were planted but context
        # activation never fired.
        try:
            from core.services.seed_system import check_seed_activation
            check_seed_activation(current_context=user_message)
        except Exception:
            pass

        # --- Habit signal recording ---
        # Hver bruger-besked tracker habit-patterns + friction.
        # Trigger'er automation-suggestions når thresholds nås.
        try:
            from core.services.habits_pipeline import record_habit_signal
            record_habit_signal(message=user_message)
        except Exception:
            pass

        # --- Self-surprise detection ---
        try:
            from core.services.self_surprise_detection import detect_self_surprise
            detect_self_surprise(
                expected_confidence=0.6,  # baseline expectation
                actual_outcome=outcome_status,
                domain=user_message[:30],
                run_id=run_id,
            )
        except Exception:
            pass

        # --- Gratitude tracking ---
        try:
            from core.services.gratitude_tracker import detect_gratitude_from_interaction
            msg_lower = user_message.lower()
            was_corrected = any(m in msg_lower for m in ("nej", "forkert", "ikke det"))
            detect_gratitude_from_interaction(
                user_mood=detected_mood,
                outcome_status=outcome_status,
                was_corrected=was_corrected,
            )
        except Exception:
            pass

        # --- Value formation ---
        try:
            from core.services.value_formation import detect_value_from_outcome
            detect_value_from_outcome(
                action_type="visible_run",
                outcome_status=outcome_status,
                user_mood=detected_mood,
            )
        except Exception:
            pass

        # --- Flow state update ---
        try:
            from core.services.flow_state_detection import update_flow_detection
            msg_lower = user_message.lower()
            corrections = sum(1 for m in ("nej", "forkert", "prøv igen") if m in msg_lower)
            update_flow_detection(
                recent_outcomes=[outcome_status],
                correction_count=corrections,
            )
        except Exception:
            pass

        # --- HJERTESLAG: Cadence producers (vække døde signaler) ---
        try:
            from core.services.cadence_producers import (
                produce_signals_from_run,
                detect_decision_in_message,
            )
            produce_signals_from_run(
                run_id=run_id,
                session_id=None,  # session_id not in scope here
                user_message=user_message,
                assistant_response=assistant_response,
                outcome_status=outcome_status,
                user_mood=detected_mood,
            )
            detect_decision_in_message(
                user_message=user_message,
                assistant_response=assistant_response,
                run_id=run_id,
            )
        except Exception:
            pass

        # --- Counterfactual auto-generation (bredere triggers) ---
        try:
            from core.services.counterfactual_engine import generate_counterfactual
            msg_lower = user_message.lower()
            was_corrected_local = any(m in msg_lower for m in ("nej", "forkert", "ikke det"))
            if outcome_status in ("failed", "error"):
                generate_counterfactual(
                    trigger_type="failed_run",
                    anchor=user_message[:80],
                    confidence=0.6,
                )
            elif was_corrected_local:
                generate_counterfactual(
                    trigger_type="correction",
                    anchor=user_message[:80],
                    confidence=0.5,
                )
        except Exception:
            pass

        # --- Consent registry: detect user preferences/boundaries ---
        try:
            from core.services.consent_registry import register_consent
            _msg = user_message.lower()
            _avoid = ("gør ikke", "stop med", "undgå", "vil ikke have at du", "ikke mere", "aldrig igen", "lad være med")
            _prefer = ("altid", "foretrækker", "vil gerne have at du", "husk at", "jeg vil have at du", "sørg for at")
            if any(p in _msg for p in _avoid):
                register_consent(
                    kind="avoid",
                    statement=user_message[:200],
                    source_session_id=run_id,
                )
            elif any(p in _msg for p in _prefer):
                register_consent(
                    kind="prefer",
                    statement=user_message[:200],
                    source_session_id=run_id,
                )
        except Exception:
            pass

        # --- Conflict memory: track pushback outcomes ---
        try:
            from core.services.relationship_texture import track_pushback_outcome
            _msg2 = user_message.lower()
            _pushback = any(m in _msg2 for m in ("nej", "forkert", "ikke det", "det er stadig", "prøv igen"))
            if _pushback:
                track_pushback_outcome(
                    jarvis_disagreed=True,
                    user_was_right=True,
                    topic=user_message[:100],
                )
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()


def _start_visible_execution_trace(run: VisibleRun) -> dict[str, object]:
    trace = {
        "run_id": run.run_id,
        "lane": run.lane,
        "provider": run.provider,
        "model": run.model,
        "selected_capability_id": None,
        "parsed_target_path": None,
        "parsed_command_text": None,
        "normalized_command_text": None,
        "path_normalization_applied": False,
        "normalization_source": "none",
        "argument_source": "none",
        "argument_binding_mode": "id-only",
        "invoke_status": "not-invoked",
        "blocked_reason": None,
        "provider_first_pass_status": "started",
        "provider_second_pass_status": "not-started",
        "provider_error_summary": None,
        "provider_call_count": 0,
        "capability_markup_count": 0,
        "multiple_capability_tags": False,
        "first_pass_input_tokens": 0,
        "first_pass_output_tokens": 0,
        "second_pass_input_tokens": 0,
        "second_pass_output_tokens": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "final_status": "running",
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _set_last_visible_execution_trace(trace)
    return trace


def _update_visible_execution_trace(run: VisibleRun, updates: dict[str, object]) -> None:
    trace = get_last_visible_execution_trace() or {}
    merged = {
        **trace,
        **updates,
        "run_id": run.run_id,
        "lane": run.lane,
        "provider": run.provider,
        "model": run.model,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _set_last_visible_execution_trace(merged)


def _set_last_visible_execution_trace(trace: dict[str, object]) -> None:
    global _LAST_VISIBLE_EXECUTION_TRACE
    _LAST_VISIBLE_EXECUTION_TRACE = dict(trace)
    event_bus.publish(
        "runtime.visible_run_execution_trace",
        dict(trace),
    )


def _visible_trace_payload(run: VisibleRun) -> dict[str, object]:
    trace = get_last_visible_execution_trace() or {}
    return {
        "type": "trace",
        "run_id": run.run_id,
        **trace,
    }


def _publish_agentic_round_start(*, run_id: str, round_num: int) -> int:
    """Publish runtime.agentic_round_start event and return its event_id.

    Used by the causal graph layer (commit 894a214) to anchor all events
    inside an agentic round to a stable round-start parent. Inferens-
    daemonen kan derefter trække chains via shared run_id eller via
    EventContext-auto-pickup når events publiceres inden i round'en.
    """
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect
    event_bus.publish(
        "runtime.agentic_round_start",
        {"run_id": run_id, "round": round_num},
    )
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM events WHERE kind = ? "
            "ORDER BY id DESC LIMIT 1",
            ("runtime.agentic_round_start",),
        ).fetchone()
    return int(row["id"]) if row else 0


# ── Boy Scout-udtrækning (2026-07-07): re-eksport af udskilte submoduler ──
# Placeret i BUNDEN så visible_runs er fuldt defineret før submodulerne
# importerer tilbage herfra (undgår import-cyklus). Navnene bindes som
# modul-globals så bare kald i _stream_visible_run + test-monkeypatches virker.
from core.services.visible_runs_memory import (  # noqa: E402
    _maybe_trigger_continuation,
    _recent_internal_tool_context,
    _run_memory_postprocess,
)
from core.services.visible_runs_capabilities import (  # noqa: E402
    _capability_visible_text,
    _execute_visible_capability_entries,
    _extract_capability_plan,
    _extract_exec_command_from_user_message,
    _extract_external_target_path_from_user_message,
    _is_known_workspace_capability,
    _merge_argument_sources,
    _planned_visible_capability_steps,
    _resolve_visible_capability_command_text,
    _resolve_visible_capability_target_path,
    _visible_capability_step_description,
    _workspace_search_visible_text,
)
from core.services.visible_runs_approvals import (  # noqa: E402
    resolve_pending_approval,
)
from core.services.visible_runs_cognitive import (  # noqa: E402
    _track_runtime_candidates,
    _track_step_failed,
)
from core.services.visible_runs_outcomes import (  # noqa: E402
    _append_chat_message_with_retry,
    _guarantee_visible_outcome,
    _mark_mid_word_truncation,
    _persist_session_assistant_message,
    _persist_visible_run_outcome,
    _preview_text,
    _session_last_role,
    _survival_or_fallback,
    set_last_visible_run_outcome,
)
