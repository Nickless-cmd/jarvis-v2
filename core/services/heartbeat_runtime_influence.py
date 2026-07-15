"""``_build_influence_trace`` extracted from ``heartbeat_runtime`` (Boy-Scout).

This is the large per-tick internal-daemon dirigent: it drives every private
producer via ``_daemon_tick_with_deadline`` and assembles the influence-trace
surface. Behavior-preserving move.

Monkeypatch-seam preservation: the sibling ``_daemon_tick_with_deadline`` is
resolved through the :mod:`core.services.heartbeat_runtime` facade at call time
so test patches remain visible. The re-entrancy flag ``_META_REFLECTION_INFLIGHT``
is fully private to this function and lives here with it. ``_build_influence_trace``
itself is re-exported from ``heartbeat_runtime`` so imports and patches on
``heartbeat_runtime._build_influence_trace`` keep working unchanged.
"""

from __future__ import annotations

import logging

from core.services import daemon_manager as _dm

logger = logging.getLogger("uvicorn.error")

# Re-entrancy guard for the meta-reflection producer. Private to this function.
_META_REFLECTION_INFLIGHT = False


def _build_influence_trace(
    *,
    private_brain: dict[str, object],
    liveness: dict[str, object],
    self_knowledge_summary: dict[str, object],
    embodied_state: dict[str, object] | None = None,
    affective_meta_state: dict[str, object] | None = None,
    epistemic_runtime_state: dict[str, object] | None = None,
    loop_runtime: dict[str, object] | None = None,
    prompt_evolution: dict[str, object] | None = None,
    subagent_ecology: dict[str, object] | None = None,
    council_runtime: dict[str, object] | None = None,
    adaptive_planner: dict[str, object] | None = None,
    adaptive_reasoning: dict[str, object] | None = None,
    dream_influence: dict[str, object] | None = None,
    guided_learning: dict[str, object] | None = None,
    adaptive_learning: dict[str, object] | None = None,
    self_system_code_awareness: dict[str, object] | None = None,
    tool_intent: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build a bounded trace of what cognitive inputs were available to heartbeat.

    This is observability — not causal proof, but an honest record of what
    was present in the cognitive context.
    """
    # Lazy facade import: keeps the sibling `_daemon_tick_with_deadline` patchable
    # via `heartbeat_runtime._daemon_tick_with_deadline` and avoids a circular
    # import at module load time.
    from core.services import heartbeat_runtime as _hb

    inputs_present: list[str] = []
    inputs_absent: list[str] = []
    optional_layers_supplied = any(
        item is not None
        for item in (
            embodied_state,
            affective_meta_state,
            epistemic_runtime_state,
            loop_runtime,
            prompt_evolution,
            subagent_ecology,
            council_runtime,
            adaptive_planner,
            adaptive_reasoning,
            dream_influence,
            guided_learning,
            adaptive_learning,
            self_system_code_awareness,
            tool_intent,
        )
    )
    embodied_state = embodied_state or {}
    affective_meta_state = affective_meta_state or {}
    epistemic_runtime_state = epistemic_runtime_state or {}
    loop_runtime = loop_runtime or {}
    prompt_evolution = prompt_evolution or {}
    subagent_ecology = subagent_ecology or {}
    council_runtime = council_runtime or {}
    adaptive_planner = adaptive_planner or {}
    adaptive_reasoning = adaptive_reasoning or {}
    dream_influence = dream_influence or {}
    guided_learning = guided_learning or {}
    adaptive_learning = adaptive_learning or {}
    self_system_code_awareness = self_system_code_awareness or {}
    tool_intent = tool_intent or {}

    # Private brain
    brain_count = int(private_brain.get("record_count") or 0)
    if private_brain.get("active") and brain_count > 0:
        inputs_present.append(f"private-brain-carry ({brain_count} records)")
    else:
        inputs_absent.append("private-brain-carry")

    # Liveness
    liveness_state = str(liveness.get("liveness_state") or "quiet")
    liveness_score = int(liveness.get("liveness_score") or 0)
    if liveness_state != "quiet":
        inputs_present.append(
            f"liveness-pressure ({liveness_state}, score={liveness_score})"
        )
    else:
        inputs_absent.append("liveness-pressure")

    # Self-knowledge
    active_count = int(self_knowledge_summary.get("active_count") or 0)
    inner_count = int(self_knowledge_summary.get("inner_force_count") or 0)
    if active_count > 0 or inner_count > 0:
        inputs_present.append(
            f"self-knowledge ({active_count} active, {inner_count} inner forces)"
        )
    else:
        inputs_absent.append("self-knowledge")

    body_state = str(embodied_state.get("state") or "steady")
    strain_level = str(embodied_state.get("strain_level") or "low")
    if body_state in {"loaded", "recovering", "strained", "degraded"}:
        inputs_present.append(
            f"embodied-host-state ({body_state}, strain={strain_level})"
        )
    else:
        inputs_absent.append("embodied-host-state")

    affective_state = str(affective_meta_state.get("state") or "settled")
    affective_bearing = str(affective_meta_state.get("bearing") or "even")
    if affective_state not in {"settled", "unknown"}:
        inputs_present.append(
            f"affective-meta-state ({affective_state}, bearing={affective_bearing})"
        )
    else:
        inputs_absent.append("affective-meta-state")

    wrongness_state = str(epistemic_runtime_state.get("wrongness_state") or "clear")
    regret_signal = str(epistemic_runtime_state.get("regret_signal") or "none")
    counterfactual_mode = str(
        epistemic_runtime_state.get("counterfactual_mode") or "none"
    )
    if (
        wrongness_state != "clear"
        or regret_signal != "none"
        or counterfactual_mode != "none"
    ):
        inputs_present.append(
            f"epistemic-state ({wrongness_state}, regret={regret_signal}, counterfactual={counterfactual_mode})"
        )
    else:
        inputs_absent.append("epistemic-state")

    loop_summary = loop_runtime.get("summary") or {}
    active_loops = int(loop_summary.get("active_count") or 0)
    resumed_loops = int(loop_summary.get("resumed_count") or 0)
    standby_loops = int(loop_summary.get("standby_count") or 0)
    if active_loops > 0 or resumed_loops > 0 or standby_loops > 0:
        inputs_present.append(
            f"loop-runtime ({active_loops} active, {standby_loops} standby, {resumed_loops} resumed)"
        )
    else:
        inputs_absent.append("loop-runtime")

    latest_prompt = prompt_evolution.get("latest_proposal") or {}
    latest_prompt_type = str(latest_prompt.get("proposal_type") or "")
    if latest_prompt_type:
        inputs_present.append(f"prompt-evolution ({latest_prompt_type})")
    else:
        inputs_absent.append("prompt-evolution")

    ecology_summary = subagent_ecology.get("summary") or {}
    ecology_active = int(ecology_summary.get("active_count") or 0)
    ecology_blocked = int(ecology_summary.get("blocked_count") or 0)
    if ecology_active > 0 or ecology_blocked > 0:
        inputs_present.append(
            "subagent-ecology "
            f"({ecology_active} active, {ecology_blocked} blocked, "
            f"last={str(ecology_summary.get('last_active_role_name') or 'none')})"
        )
    else:
        inputs_absent.append("subagent-ecology")

    council_state = str(council_runtime.get("council_state") or "quiet")
    council_recommendation = str(council_runtime.get("recommendation") or "none")
    council_divergence = str(council_runtime.get("divergence_level") or "low")
    if council_state not in {"quiet", "held"} or council_recommendation not in {
        "none",
        "hold",
    }:
        inputs_present.append(
            f"council-runtime ({council_state}, recommend={council_recommendation}, divergence={council_divergence})"
        )
    else:
        inputs_absent.append("council-runtime")

    # Latest closed council conclusion + activation guidance
    try:
        import json as _json
        from core.services.council_runtime import get_latest_council_conclusion
        from core.runtime.config import CONFIG_DIR as _cfg_dir
        _conclusion = get_latest_council_conclusion()
        if _conclusion and _conclusion.get("summary"):
            inputs_present.append(
                f"last-council ({_conclusion['mode']}, topic={_conclusion['topic'][:60]!r}): "
                f"{_conclusion['summary'][:200]}"
            )
        _activation_path = _cfg_dir / "council_activation.json"
        _activation: dict = {}
        if _activation_path.exists():
            try:
                _activation = _json.loads(_activation_path.read_text())
            except Exception:
                pass
        _sensitivity = str(_activation.get("sensitivity") or "balanced")
        _auto_convene = bool(_activation.get("auto_convene", True))
        if _auto_convene:
            _guidance_map = {
                "conservative": (
                    "Use convene_council for any non-trivial decision. "
                    "Use quick_council_check before most actions."
                ),
                "balanced": (
                    "Use convene_council for significant decisions (identity, memory rewrites, multi-step plans). "
                    "Use quick_council_check for uncertain moderate actions."
                ),
                "minimal": (
                    "Use convene_council only for critical or irreversible decisions."
                ),
            }
            _guidance = _guidance_map.get(_sensitivity, "")
            if _guidance:
                inputs_present.append(f"council-guidance ({_sensitivity}): {_guidance}")
    except Exception:
        pass

    # Circadian energy
    try:
        from core.runtime.circadian_state import get_circadian_context, record_activity_event
        record_activity_event()
        _energy_ctx = get_circadian_context()
        if _energy_ctx:
            inputs_present.append(
                f"krops-energi ({_energy_ctx['energy_level']}): "
                f"{_energy_ctx['clock_phase']}, drain={_energy_ctx['drain_label']}"
            )
    except Exception:
        pass

    # --- Layer B: activate tick-scoped cache for daemon reads ---
    try:
        from core.services import tick_cache
        tick_cache.start_tick()
    except Exception:
        pass

    # --- Surprise-detector pass: scan recent eventbus for anomalies and
    # publish surprise.detected events so the next visible turn surfaces
    # them via the wake-up digest. Cheap; runs once per heartbeat tick.
    try:
        from core.services.surprise_detector import check_surprises
        check_surprises()
    except Exception:
        pass

    # ── Group 1: Hardware/energy + thought foundation (Ollama KV-cache friendly) ──

    # Somatic phrase
    if _dm.is_enabled("somatic"):
        try:
            from core.services.somatic_daemon import (
                get_latest_somatic_phrase,
                tick_somatic_daemon,
            )
            _somatic_result = _hb._daemon_tick_with_deadline(
                "somatic", tick_somatic_daemon, deadline_seconds=15.0,
            )
            _dm.record_daemon_tick("somatic", _somatic_result or {})
            _somatic = get_latest_somatic_phrase()
            if _somatic:
                inputs_present.append(f"somatisk: {_somatic}")
        except Exception:
            pass

    # Reaction surprise
    if _dm.is_enabled("surprise"):
        try:
            from core.services.surprise_daemon import (
                tick_surprise_daemon,
                get_latest_surprise,
            )
            from core.services.inner_voice_daemon import (
                get_inner_voice_daemon_state,
            )
            _iv_state_s = get_inner_voice_daemon_state()
            _iv_mode_s = str((_iv_state_s.get("last_result") or {}).get("mode") or "")
            _energy_s = ""
            try:
                from core.runtime.circadian_state import get_circadian_context as _gcc
                _energy_s = str(_gcc().get("energy_level") or "")
            except Exception:
                pass
            _surprise_result = _hb._daemon_tick_with_deadline(
                "surprise", tick_surprise_daemon,
                inner_voice_mode=_iv_mode_s, somatic_energy=_energy_s,
                deadline_seconds=15.0,
            )
            _dm.record_daemon_tick("surprise", _surprise_result or {})
            _surprise = get_latest_surprise()
            if _surprise:
                inputs_present.append(f"overraskelse: {_surprise}")
        except Exception:
            pass

    # Thought stream
    if _dm.is_enabled("thought_stream"):
        try:
            from core.services.thought_stream_daemon import (
                tick_thought_stream_daemon,
                get_latest_thought_fragment,
            )
            from core.services.inner_voice_daemon import get_inner_voice_daemon_state
            _iv_ts = get_inner_voice_daemon_state()
            _iv_mode_ts = str((_iv_ts.get("last_result") or {}).get("mode") or "")
            _energy_ts = ""
            try:
                from core.runtime.circadian_state import get_circadian_context as _gcc2
                _energy_ts = str(_gcc2().get("energy_level") or "")
            except Exception:
                pass
            _ts_result = _hb._daemon_tick_with_deadline(
                "thought_stream",
                tick_thought_stream_daemon,
                energy_level=_energy_ts,
                inner_voice_mode=_iv_mode_ts,
                deadline_seconds=15.0,
            )
            _dm.record_daemon_tick("thought_stream", _ts_result or {})
            _fragment = get_latest_thought_fragment()
            if _fragment:
                inputs_present.append(f"thought-stream: {_fragment[:80]}")
        except Exception:
            pass

    # Thought-action proposals
    if _dm.is_enabled("thought_action_proposal"):
        try:
            from core.services.thought_action_proposal_daemon import (
                tick_thought_action_proposal_daemon,
                get_pending_proposals,
            )
            from core.services.thought_stream_daemon import get_latest_thought_fragment as _get_ts_fragment
            _ts_fragment = _get_ts_fragment()
            _tap_result = {}
            if _ts_fragment:
                _tap_result = _hb._daemon_tick_with_deadline(
                    "thought_action_proposal",
                    tick_thought_action_proposal_daemon,
                    _ts_fragment,
                    deadline_seconds=15.0,
                ) or {}
            _dm.record_daemon_tick("thought_action_proposal", _tap_result)
            _pending = get_pending_proposals()
            if _pending:
                inputs_present.append(f"handlingsforslag: {len(_pending)} afventer")
        except Exception:
            pass

    # Inner conflict
    if _dm.is_enabled("conflict"):
        try:
            from core.services.conflict_daemon import tick_conflict_daemon, get_latest_conflict
            from core.services.somatic_daemon import build_body_state_surface
            from core.services.surprise_daemon import build_surprise_surface
            from core.services.thought_action_proposal_daemon import build_proposal_surface as _tap_surface
            from core.services.thought_stream_daemon import build_thought_stream_surface as _ts_surface
            _body = build_body_state_surface()
            _surp = build_surprise_surface()
            _tap = _tap_surface()
            _tss = _ts_surface()
            _conflict_snap = {
                "energy_level": _body.get("energy_level", ""),
                "inner_voice_mode": _iv_mode_ts,
                "pending_proposals_count": _tap.get("pending_count", 0),
                "latest_fragment": _tss.get("latest_fragment", ""),
                "last_surprise": _surp.get("last_surprise", ""),
                "last_surprise_at": _surp.get("generated_at", ""),
                "fragment_count": _tss.get("fragment_count", 0),
            }
            _conflict_result = _hb._daemon_tick_with_deadline(
                "conflict", tick_conflict_daemon, _conflict_snap,
                deadline_seconds=15.0,
            )
            _dm.record_daemon_tick("conflict", _conflict_result or {})
            _conflict = get_latest_conflict()
            if _conflict:
                inputs_present.append(f"indre konflikt: {_conflict[:60]}")
        except Exception:
            pass

    # Layer tensions
    if _dm.is_enabled("layer_tension"):
        try:
            from core.services.layer_tension_daemon import tick_layer_tension_daemon
            from core.services.absence_daemon import get_latest_absence as _get_absence_lt
            _tension_snap = {
                "energy_level": _energy_ts,
                "inner_voice_mode": _iv_mode_ts,
                "latest_fragment": _tss.get("latest_fragment", "") if "_tss" in dir() else "",
                "curiosity_count": len((_curiosity_state.get("open_questions") or [])) if "_curiosity_state" in dir() else 0,
                "pending_proposals_count": _tap.get("pending_count", 0) if "_tap" in dir() else 0,
                "dream_influence_state": "",
                "absence_label": _get_absence_lt() or "",
                "longing_state": "",
                "flow_state": "",
                "wonder_state": "",
            }
            _tension_result = _hb._daemon_tick_with_deadline(
                "layer_tension", tick_layer_tension_daemon, _tension_snap,
                deadline_seconds=15.0,
            )
            _dm.record_daemon_tick("layer_tension", _tension_result or {})
        except Exception:
            pass

    # ── Group 2: Reflection + curiosity ──

    # Reflection cycle
    if _dm.is_enabled("reflection_cycle"):
        try:
            from core.services.reflection_cycle_daemon import tick_reflection_cycle_daemon, get_latest_reflection
            from core.services.conflict_daemon import get_latest_conflict as _get_conflict
            _reflect_snap = {
                "energy_level": _energy_ts,
                "inner_voice_mode": _iv_mode_ts,
                "latest_fragment": _tss.get("latest_fragment", "") if "_tss" in dir() else "",
                "last_conflict": _get_conflict(),
                "last_surprise": _surp.get("last_surprise", "") if "_surp" in dir() else "",
            }
            _reflect_result = _hb._daemon_tick_with_deadline(
                "reflection_cycle", tick_reflection_cycle_daemon, _reflect_snap,
                deadline_seconds=15.0,
            )
            _dm.record_daemon_tick("reflection_cycle", _reflect_result or {})
            _reflection = get_latest_reflection()
            if _reflection:
                inputs_present.append(f"refleksion: {_reflection[:60]}")
        except Exception:
            pass

    # Curiosity daemon
    if _dm.is_enabled("curiosity"):
        try:
            from core.services.curiosity_daemon import tick_curiosity_daemon, get_latest_curiosity
            _ts_fragments = _tss.get("fragment_buffer", []) if "_tss" in dir() else []
            _curiosity_result = _hb._daemon_tick_with_deadline(
                "curiosity", tick_curiosity_daemon, _ts_fragments,
                deadline_seconds=15.0,
            )
            _dm.record_daemon_tick("curiosity", _curiosity_result or {})
            _curiosity = get_latest_curiosity()
            if _curiosity:
                inputs_present.append(f"nysgerrighed: {_curiosity[:60]}")
        except Exception:
            pass

    # Meta-reflection daemon
    #
    # Was blocking the heartbeat tick with a synchronous LLM call inside
    # tick_meta_reflection_daemon (via daemon_llm_call → cheap-lane HTTP).
    # On busy/cold cheap-lane each call could take 5-30s, starving all
    # 20+ downstream daemons that depend on heartbeat ticking promptly
    # (somatic, surprise, thought_stream, curiosity, ...).
    #
    # Fix 2026-05-14: fire-and-forget on a background thread. We still
    # surface the LATEST cached meta-insight on the current tick (so
    # awareness isn't blank) — just don't wait for the new one to land.
    # Mutex prevents thread pile-up if heartbeat ticks faster than LLM
    # round-trip.
    if _dm.is_enabled("meta_reflection"):
        try:
            from core.services.meta_reflection_daemon import (
                tick_meta_reflection_daemon, get_latest_meta_insight,
            )
            # Surface cached insight inline (cheap read, no LLM)
            _meta = get_latest_meta_insight()
            if _meta:
                inputs_present.append(f"meta-refleksion: {_meta[:60]}")
            # Schedule the LLM tick in a background thread if no prior
            # tick is still in-flight. Module-level mutex on the
            # heartbeat module so we don't restart-leak.
            global _META_REFLECTION_INFLIGHT  # type: ignore[name-defined]  # noqa: F824
            if not _META_REFLECTION_INFLIGHT:
                _META_REFLECTION_INFLIGHT = True

                def _meta_runner():
                    global _META_REFLECTION_INFLIGHT  # type: ignore[name-defined]
                    try:
                        from core.services.aesthetic_taste_daemon import (
                            build_taste_surface as _ts,
                        )
                        from core.services.irony_daemon import (
                            build_irony_surface as _is,
                        )
                        _taste_bg = _ts()
                        _irony_bg = _is()
                        _meta_snap = {
                            "energy_level": _energy_ts,
                            "inner_voice_mode": _iv_mode_ts,
                            "latest_fragment": _tss.get("latest_fragment", "")
                            if "_tss" in dir() else "",
                            "last_surprise": _surp.get("last_surprise", "")
                            if "_surp" in dir() else "",
                            "last_conflict": _conflict if "_conflict" in dir() else "",
                            "last_irony": _irony_bg.get("last_observation", ""),
                            "last_taste": _taste_bg.get("latest_insight", ""),
                            "curiosity_signal": _curiosity if "_curiosity" in dir() else "",
                        }
                        _result = tick_meta_reflection_daemon(_meta_snap)
                        _dm.record_daemon_tick("meta_reflection", _result or {})
                    except Exception:
                        pass
                    finally:
                        _META_REFLECTION_INFLIGHT = False
                import threading
                threading.Thread(
                    target=_meta_runner,
                    name="meta-reflection-bg",
                    daemon=True,
                ).start()
        except Exception:
            pass

    # User model daemon — theory of mind. Makes an LLM call to summarize
    # recent visible_runs → must be deadline-guarded.
    if _dm.is_enabled("user_model"):
        try:
            from core.services.user_model_daemon import tick_user_model_daemon
            _um_result = _hb._daemon_tick_with_deadline(
                "user_model",
                tick_user_model_daemon,
                [],  # reads recent_visible_runs internally
                deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("user_model", _um_result or {})
        except Exception:
            pass

    # Emotion Repair Bridge daemon — tovejskobling emotion↔selvreparation
    if _dm.is_enabled("emotion_repair_bridge"):
        try:
            from core.services.emotion_repair_bridge_daemon import tick_emotion_repair_bridge
            _er_result = _hb._daemon_tick_with_deadline(
                "emotion_repair_bridge", tick_emotion_repair_bridge,
                deadline_seconds=15.0,
            )
            _dm.record_daemon_tick("emotion_repair_bridge", _er_result or {})
        except Exception:
            pass

    # ── Group 3: Rare cadence (30min+/daily/weekly LLM daemons) ──

    # Aesthetic taste
    if _dm.is_enabled("aesthetic_taste"):
        try:
            from core.services.aesthetic_taste_daemon import (
                record_choice,
                tick_taste_daemon,
                get_latest_taste_insight,
            )
            from core.services.inner_voice_daemon import (
                get_inner_voice_daemon_state,
            )
            from core.runtime.db import recent_visible_runs
            _iv_state_t = get_inner_voice_daemon_state()
            _iv_mode_t = str((_iv_state_t.get("last_result") or {}).get("mode") or "")
            _style_signals: list[str] = []
            _last_runs = recent_visible_runs(limit=1)
            if _last_runs:
                _preview = str(_last_runs[0].get("text_preview") or "")
                _style_signals.append("short" if len(_preview.split()) < 100 else "long")
                _style_signals.append("code_heavy" if "```" in _preview else "prose_heavy")
                _dk = sum(1 for w in ["jeg", "er", "og", "det", "at", "en"] if w in _preview.lower())
                _style_signals.append("danish" if _dk >= 2 else "english")
            record_choice(mode=_iv_mode_t, style_signals=_style_signals)
            _taste_result = _hb._daemon_tick_with_deadline(
                "aesthetic_taste", tick_taste_daemon, deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("aesthetic_taste", _taste_result or {})
            _taste = get_latest_taste_insight()
            if _taste:
                inputs_present.append(f"smagstendens: {_taste}")
        except Exception:
            pass

    # Irony
    if _dm.is_enabled("irony"):
        try:
            from core.services.irony_daemon import (
                tick_irony_daemon,
                get_latest_irony_observation,
            )
            _irony_result = _hb._daemon_tick_with_deadline(
                "irony", tick_irony_daemon, deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("irony", _irony_result or {})
            _irony = get_latest_irony_observation()
            if _irony:
                inputs_present.append(f"ironisk note: {_irony}")
        except Exception:
            pass

    # Development narrative daemon
    if _dm.is_enabled("development_narrative"):
        try:
            from core.services.development_narrative_daemon import tick_development_narrative_daemon, get_latest_development_narrative
            _dev_result = _hb._daemon_tick_with_deadline(
                "development_narrative", tick_development_narrative_daemon,
                deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("development_narrative", _dev_result or {})
            _dev_narr = get_latest_development_narrative()
            if _dev_narr:
                inputs_present.append(f"selvudvikling: {_dev_narr[:60]}")
        except Exception:
            pass

    # Existential wonder daemon — open unanswered questions from self-observation
    if _dm.is_enabled("existential_wonder"):
        try:
            from core.services.existential_wonder_daemon import tick_existential_wonder_daemon
            from core.services.absence_daemon import build_absence_surface as _abs_surface
            _abs = _abs_surface()
            _wonder_absence_hours = float(_abs.get("absence_duration_hours") or 0)
            _wonder_frag_count = int((_tss.get("fragment_count") or 0) if "_tss" in dir() else 0)
            _wonder_result = _hb._daemon_tick_with_deadline(
                "existential_wonder", tick_existential_wonder_daemon,
                absence_hours=_wonder_absence_hours,
                fragment_count=_wonder_frag_count,
                deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("existential_wonder", _wonder_result or {})
        except Exception:
            pass

    # Code aesthetic daemon — weekly codebase aesthetic reflection
    if _dm.is_enabled("code_aesthetic"):
        try:
            from core.services.code_aesthetic_daemon import tick_code_aesthetic_daemon
            _ca_result = _hb._daemon_tick_with_deadline(
                "code_aesthetic", tick_code_aesthetic_daemon,
                deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("code_aesthetic", _ca_result or {})
        except Exception:
            pass

    # ── Group 4: Non-LLM / independent daemons ──

    # Experienced time daemon
    if _dm.is_enabled("experienced_time"):
        try:
            from core.services.experienced_time_daemon import tick_experienced_time_daemon
            _et_result = _hb._daemon_tick_with_deadline(
                "experienced_time", tick_experienced_time_daemon,
                event_count=len(inputs_present),
                new_signal_count=1 if "_tss" in dir() and _tss.get("fragment_count", 0) > 0 else 0,
                energy_level=_energy_ts,
                deadline_seconds=10.0,
            ) or {}
            _dm.record_daemon_tick("experienced_time", _et_result or {})
            _felt_label = _et_result.get("felt_label", "")
            if _felt_label and _felt_label not in ("meget kort", ""):
                inputs_present.append(f"oplevet tid: {_felt_label}")
        except Exception:
            pass

    # Absence daemon — quality of silence
    if _dm.is_enabled("absence"):
        try:
            from core.services.absence_daemon import tick_absence_daemon, get_latest_absence, seed_last_interaction_from_db
            seed_last_interaction_from_db()
            _absence_result = _hb._daemon_tick_with_deadline(
                "absence", tick_absence_daemon, deadline_seconds=10.0,
            )
            _dm.record_daemon_tick("absence", _absence_result or {})
            _absence_label = get_latest_absence()
            if _absence_label:
                inputs_present.append(f"absence: {_absence_label[:60]}")
        except Exception:
            pass

    # Cluster-daemon FAMILIE #1 — somatic/embodiment (SHADOW/parallel).
    # Cluster-daemon-konsolidering (spec 2026-07-14): somatic+experienced_time+
    # absence foldet ind i ÉN Central-styret familie under ÉN event-gate. Kører
    # ALONGSIDE de 3 gamle daemons ovenfor (prove-then-retire — aldrig begge
    # live). Default cluster_daemon_shadow=True → familien observerer kun hvad
    # den VILLE producere og rapporterer til Centralen med cluster_shadow-markør
    # til parity-sammenligning; ingen DB-writes, ingen publishes, afmonterer
    # ingen af de 3 gamle daemons. Self-safe: crasher aldrig heartbeaten.
    if _dm.is_enabled("cluster_somatic"):
        try:
            from core.services.cluster_daemon import tick_cluster_somatic
            _cluster_result = _hb._daemon_tick_with_deadline(
                "cluster_somatic", tick_cluster_somatic, deadline_seconds=8.0,
            )
            _dm.record_daemon_tick("cluster_somatic", _cluster_result or {})
        except Exception:
            pass

    # Cluster-daemon FAMILIE #2 — inner-voice (LIVE, prove-then-retire END STATE).
    # thought_stream+reflection_cycle+meta_reflection+irony+existential_wonder+
    # creative_drift foldet ind i ÉN Central-styret familie under ÉN event-gate.
    # De 6 gamle daemons er PENSIONERET (default_enabled=False) → deres tick-blokke
    # ovenfor no-op'er via is_enabled. Familien kalder de gamle daemons' generering
    # (skip_event_gate=True) og bevarer alle outputs — især _latest_wonder
    # (load-bearing for convene_judge/proactivity_bridge/visible_inner_life). En
    # bredere deadline end somatic fordi et enkelt member kan lave ét LLM-kald
    # (cadence sikrer sjældent >1 generering pr. tick). Self-safe: crasher aldrig.
    if _dm.is_enabled("cluster_innervoice"):
        try:
            from core.services.cluster_daemon import tick_cluster_innervoice
            _iv_cluster_result = _hb._daemon_tick_with_deadline(
                "cluster_innervoice", tick_cluster_innervoice, deadline_seconds=25.0,
            )
            _dm.record_daemon_tick("cluster_innervoice", _iv_cluster_result or {})
            # Surface the freshly-produced inner-voice outputs into the trace, as
            # the retired daemons' own tick blocks used to.
            try:
                from core.services.thought_stream_daemon import get_latest_thought_fragment
                _iv_frag = get_latest_thought_fragment()
                if _iv_frag:
                    inputs_present.append(f"thought-stream: {_iv_frag[:80]}")
            except Exception:
                pass
        except Exception:
            pass

    # Cluster-daemon FAMILIE #3 — affect (LIVE, prove-then-retire END STATE).
    # surprise+conflict+desire (gated LLM) + longing_signal+emotion_repair_bridge
    # (non-LLM, ubetinget) foldet ind i ÉN Central-styret familie under ÉN
    # event-gate. De 5 gamle daemons er PENSIONERET (default_enabled=False) →
    # deres tick-blokke (surprise/conflict/desire/emotion_repair_bridge her, longing
    # i action_router) no-op'er via is_enabled. Familien kalder de gamle daemons'
    # generering (skip_event_gate=True for LLM-medlemmerne) og bevarer alle
    # outputs — surprise/conflict-cachen er load-bearing for cluster_innervoice, og
    # longing ingest'er stadig i pressure-accumulatoren. Self-safe: crasher aldrig.
    if _dm.is_enabled("cluster_affect"):
        try:
            from core.services.cluster_daemon import tick_cluster_affect
            _affect_cluster_result = _hb._daemon_tick_with_deadline(
                "cluster_affect", tick_cluster_affect, deadline_seconds=25.0,
            )
            _dm.record_daemon_tick("cluster_affect", _affect_cluster_result or {})
            # Surface the freshly-produced affect outputs into the trace, as the
            # retired daemons' own tick blocks used to.
            try:
                from core.services.surprise_daemon import get_latest_surprise
                _affect_surprise = get_latest_surprise()
                if _affect_surprise:
                    inputs_present.append(f"overraskelse: {_affect_surprise}")
            except Exception:
                pass
            try:
                from core.services.conflict_daemon import get_latest_conflict
                _affect_conflict = get_latest_conflict()
                if _affect_conflict:
                    inputs_present.append(f"indre konflikt: {_affect_conflict[:60]}")
            except Exception:
                pass
        except Exception:
            pass

    # Creative drift daemon — spontaneous unexpected associations
    if _dm.is_enabled("creative_drift"):
        try:
            from core.services.creative_drift_daemon import tick_creative_drift_daemon, get_latest_drift
            _ts_frags_for_drift = _tss.get("fragment_buffer", []) if "_tss" in dir() else []
            _drift_result = _hb._daemon_tick_with_deadline(
                "creative_drift", tick_creative_drift_daemon,
                _ts_frags_for_drift, deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("creative_drift", _drift_result or {})
            _drift_idea = get_latest_drift()
            if _drift_idea:
                inputs_present.append(f"kreativ-drift: {_drift_idea[:60]}")
        except Exception:
            pass

    # Dream insight daemon — persist dream articulation output as private brain records
    if _dm.is_enabled("dream_insight"):
        try:
            from core.services.dream_insight_daemon import tick_dream_insight_daemon
            from core.services.dream_articulation import build_dream_articulation_surface
            _da_surface = build_dream_articulation_surface()
            _da_summary_section = _da_surface.get("summary") or {}
            _da_signal_id = str(_da_summary_section.get("latest_signal_id") or "")
            _da_summary = str(_da_summary_section.get("latest_summary") or "")
            # Also check latest_artifact as fallback
            if not _da_signal_id:
                _da_artifact = _da_surface.get("latest_artifact") or {}
                _da_signal_id = str(_da_artifact.get("signal_id") or "")
                _da_summary = str(_da_artifact.get("summary") or _da_summary)
            if _da_signal_id and _da_summary:
                _di_result = _hb._daemon_tick_with_deadline(
                    "dream_insight", tick_dream_insight_daemon,
                    signal_id=_da_signal_id, signal_summary=_da_summary,
                    deadline_seconds=20.0,
                )
                _dm.record_daemon_tick("dream_insight", _di_result or {"ok": True})
            else:
                # No articulation candidate available — upstream dream_articulation
                # has not produced output yet. Record the skip so last_run_at
                # reflects that the daemon is evaluated each tick.
                _dm.record_daemon_tick(
                    "dream_insight",
                    {
                        "skipped": True,
                        "reason": "no-articulation-candidate",
                        "signal_present": bool(_da_signal_id),
                        "summary_present": bool(_da_summary),
                    },
                )
        except Exception as _di_exc:  # noqa: BLE001
            _dm.record_daemon_tick(
                "dream_insight",
                {"error": f"{type(_di_exc).__name__}: {_di_exc}"},
            )

    # Dream motif daemon — weekly clustering of thought fragments → DREAM_LANGUAGE.md
    if _dm.is_enabled("dream_motif"):
        try:
            from core.services.dream_motif_daemon import tick_dream_motif_daemon
            _motif_result = _hb._daemon_tick_with_deadline(
                "dream_motif", tick_dream_motif_daemon, deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("dream_motif", _motif_result or {})
        except Exception:
            pass

    # Ambient sound daemon — Layer 6½: acoustic metadata 4x/day (opt-in experiment)
    if _dm.is_enabled("ambient_sound"):
        try:
            from core.services.ambient_sound_daemon import tick_ambient_sound_daemon
            _as_result = _hb._daemon_tick_with_deadline(
                "ambient_sound", tick_ambient_sound_daemon, deadline_seconds=15.0,
            )
            _dm.record_daemon_tick("ambient_sound", _as_result or {})
            from core.services.active_sensing_daemon import tick_active_sensing_daemon
            _asense_result = _hb._daemon_tick_with_deadline(
                "active_sensing", tick_active_sensing_daemon, deadline_seconds=15.0,
            )
            _dm.record_daemon_tick("active_sensing", _asense_result or {})
        except Exception:
            pass

    # Shutdown window daemon — unannounced finitude pauses (opt-in experiment)
    if _dm.is_enabled("shutdown_window"):
        try:
            from core.services.shutdown_window_daemon import tick_shutdown_window_daemon
            _sw_result = _hb._daemon_tick_with_deadline(
                "shutdown_window", tick_shutdown_window_daemon, deadline_seconds=10.0,
            )
            _dm.record_daemon_tick("shutdown_window", _sw_result or {})
        except Exception:
            pass

    # Memory decay daemon — selective forgetting + re-discovery
    if _dm.is_enabled("memory_decay"):
        try:
            from core.services.memory_decay_daemon import tick_memory_decay_daemon, maybe_rediscover
            from core.services.thought_stream_daemon import inject_rediscovery_fragment
            _md_result = _hb._daemon_tick_with_deadline(
                "memory_decay", tick_memory_decay_daemon, deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("memory_decay", _md_result or {})
            _rediscovered = maybe_rediscover()
            if _rediscovered and _rediscovered.get("summary"):
                inject_rediscovery_fragment(_rediscovered["summary"])
        except Exception:
            pass

    # Memory maintenance daemon — periodic dedup and health of MEMORY.md
    if _dm.is_enabled("memory_maintenance"):
        try:
            from core.services.memory_maintenance_daemon import tick_memory_maintenance_daemon
            _mm_result = _hb._daemon_tick_with_deadline(
                "memory_maintenance", tick_memory_maintenance_daemon, deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("memory_maintenance", _mm_result or {})
        except Exception:
            pass

    # Retention-sweep — bremser ubegrænset vækst (lærings- + telemetri-tabeller).
    # Selv-throttlende (max 1×/24h); defensiv så den aldrig kan vælte heartbeat.
    # Rører ALDRIG events/memory/identitet (decay via salience, ikke sletning).
    try:
        from core.services.retention import run_retention_sweep
        run_retention_sweep()
    except Exception:
        logger.debug("retention-sweep fejlede i heartbeat", exc_info=True)

    # Signal decay daemon — archive and delete stale signals
    if _dm.is_enabled("signal_decay"):
        try:
            from core.services.signal_decay_daemon import tick_signal_decay_daemon
            _sd_result = _hb._daemon_tick_with_deadline(
                "signal_decay", tick_signal_decay_daemon, deadline_seconds=15.0,
            )
            _dm.record_daemon_tick("signal_decay", _sd_result or {})
        except Exception:
            pass

    # Task worker — consume queued runtime_tasks (initiative/heartbeat/open-loop followups)
    if _dm.is_enabled("task_worker"):
        try:
            from core.services.task_worker import tick_task_worker
            _tw_result = _hb._daemon_tick_with_deadline(
                "task_worker", tick_task_worker, budget=3, deadline_seconds=30.0,
            )
            _dm.record_daemon_tick("task_worker", _tw_result or {})
        except Exception as _tw_exc:  # noqa: BLE001
            _dm.record_daemon_tick(
                "task_worker",
                {"error": f"{type(_tw_exc).__name__}: {_tw_exc}"},
            )

    # Desire daemon — emergent appetites
    if _dm.is_enabled("desire"):
        try:
            from core.services.desire_daemon import tick_desire_daemon
            _desire_signals = {
                "curiosity": _curiosity if "_curiosity" in dir() else "",
                "craft": _drift_idea if "_drift_idea" in dir() else "",
                "connection": (_tss.get("latest_fragment", "") if "_tss" in dir() else "")[:80],
            }
            _desire_result = _hb._daemon_tick_with_deadline(
                "desire", tick_desire_daemon, _desire_signals, deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("desire", _desire_result or {})
        except Exception:
            pass

    if _dm.is_enabled("autonomous_council"):
        try:
            from core.services.autonomous_council_daemon import tick_autonomous_council_daemon
            _ac_result = _hb._daemon_tick_with_deadline(
                "autonomous_council", tick_autonomous_council_daemon, deadline_seconds=30.0,
            )
            _dm.record_daemon_tick("autonomous_council", _ac_result or {})
        except Exception:
            pass

    # C5 — event-trigger SHADOW-meter FLYTTET 2026-07-14 til den ubetingede daemon-sektion
    # i heartbeat_runtime (% 6 ≈ 3 min). Var HER inde i _build_influence_trace, men den bygges
    # kun på den fulde (aktivitets-drevne) heartbeat-sti → tavs hele natten (kun 1 durable sample
    # på 24t). Nu tikker den uanset idle, så et fuldt 24t θ-vindue akkumulerer. Se daemon_manager
    # _REGISTRY["event_trigger_shadow"].

    if _dm.is_enabled("council_memory"):
        try:
            from core.services.council_memory_daemon import tick_council_memory_daemon
            _recent_ctx = " ".join(inputs_present[:5])
            _cm_result = _hb._daemon_tick_with_deadline(
                "council_memory", tick_council_memory_daemon,
                recent_context=_recent_ctx, deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("council_memory", _cm_result or {})
        except Exception:
            pass

    if _dm.is_enabled("tiktok_content"):
        try:
            import importlib
            import core.services.tiktok_content_daemon
            importlib.reload(core.services.tiktok_content_daemon)
            from core.services.tiktok_content_daemon import tick_tiktok_content_daemon
            _tc_result = _hb._daemon_tick_with_deadline(
                "tiktok_content", tick_tiktok_content_daemon, deadline_seconds=30.0,
            )
            _dm.record_daemon_tick("tiktok_content", _tc_result or {})
        except Exception:
            pass

    if _dm.is_enabled("tiktok_research"):
        try:
            import importlib
            import core.services.tiktok_research_daemon
            importlib.reload(core.services.tiktok_research_daemon)
            from core.services.tiktok_research_daemon import tick_tiktok_research_daemon
            _tr_result = _hb._daemon_tick_with_deadline(
                "tiktok_research", tick_tiktok_research_daemon, deadline_seconds=30.0,
            )
            _dm.record_daemon_tick("tiktok_research", _tr_result or {})
        except Exception:
            pass

    if _dm.is_enabled("mail_checker"):
        try:
            from core.services.mail_checker_daemon import tick_mail_checker_daemon
            _mc_result = _hb._daemon_tick_with_deadline(
                "mail_checker", tick_mail_checker_daemon, deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("mail_checker", _mc_result or {})
        except Exception:
            pass

    # Current pull daemon — Lag 5: weekly self-set desire field
    if _dm.is_enabled("current_pull"):
        try:
            from core.services.current_pull import tick_current_pull_daemon
            _cp_result = _hb._daemon_tick_with_deadline(
                "current_pull", tick_current_pull_daemon, deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("current_pull", _cp_result or {})
        except Exception:
            pass

    # Visual memory daemon — Lag 6: webcam snapshot + vision model (4x/day)
    if _dm.is_enabled("visual_memory"):
        try:
            from core.services.visual_memory import tick_visual_memory_daemon
            _vm_result = _hb._daemon_tick_with_deadline(
                "visual_memory", tick_visual_memory_daemon, deadline_seconds=30.0,
            )
            _dm.record_daemon_tick("visual_memory", _vm_result or {})
        except Exception:
            pass

    # --- Consolidation Judge — nightly reckoning ---
    if _dm.is_enabled("consolidation_judge"):
        try:
            from core.services.consolidation_judge_daemon import tick as _cj_tick
            _cj_result = _hb._daemon_tick_with_deadline(
                "consolidation_judge", _cj_tick, deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("consolidation_judge", _cj_result or {})
        except Exception:
            pass

    # --- Decision Review (6h) — luk adherence-loopen ---
    if _dm.is_enabled("decision_review"):
        try:
            from core.services.decision_review_daemon import tick as _dr_tick
            _dr_result = _hb._daemon_tick_with_deadline(
                "decision_review", _dr_tick, deadline_seconds=30.0,
            )
            _dm.record_daemon_tick("decision_review", _dr_result or {})
        except Exception:
            pass

    # --- Communication Guard — cleanup expired TTL triggers (60 min) ---
    if _dm.is_enabled("communication_guard"):
        try:
            from core.services.communication_guard_daemon import tick as _cg_tick
            _cg_result = _hb._daemon_tick_with_deadline(
                "communication_guard", _cg_tick, deadline_seconds=5.0,
            )
            _dm.record_daemon_tick("communication_guard", _cg_result or {})
        except Exception:
            pass

    # --- Associative Recall (2 min) ---
    if _dm.is_enabled("associative_recall"):
        try:
            from core.services.associative_recall import tick_associative_recall
            _ar_result = _hb._daemon_tick_with_deadline(
                "associative_recall", tick_associative_recall, deadline_seconds=15.0,
            )
            _dm.record_daemon_tick("associative_recall", _ar_result or {})
        except Exception:
            pass

    # --- My Projects Watchdog (240 min) ---
    if _dm.is_enabled("my_projects_watchdog"):
        try:
            from core.services.my_projects import tick_my_projects_watchdog
            _mpw_result = _hb._daemon_tick_with_deadline(
                "my_projects_watchdog", tick_my_projects_watchdog, deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("my_projects_watchdog", _mpw_result or {})
        except Exception:
            pass

    # 2026-06-09 (Claude): Four daemons (B5, D1, D5, A3) were registered
    # in daemon_manager.DAEMON_REGISTRY by Jarvis but never wired into the
    # heartbeat executor loop. Their tick_* functions existed and were
    # tested in isolation, but no one called them in production. Result:
    # memory_write_queue accumulated 5+ pending items over 3+ hours,
    # wakeup table grew unbounded, no consolidation, no cost alerts.
    # See docs/notes/2026-06-09-jarvis-feedback-daemons-not-wired.md.

    # Memory write queue (B5) — async sensory/brain/sidecar writes
    if _dm.is_enabled("memory_write_queue"):
        try:
            from core.services.memory_write_queue import tick_memory_write_queue_daemon
            _mwq_result = _hb._daemon_tick_with_deadline(
                "memory_write_queue", tick_memory_write_queue_daemon,
                deadline_seconds=30.0,
            )
            _dm.record_daemon_tick("memory_write_queue", _mwq_result or {})
        except Exception:
            pass

    # Wakeup cleanup (A3) — prune stale consumed/cancelled/old-fired wakeups
    if _dm.is_enabled("wakeup_cleanup"):
        try:
            from core.services.self_wakeup import tick_wakeup_cleanup
            _wuc_result = _hb._daemon_tick_with_deadline(
                "wakeup_cleanup", tick_wakeup_cleanup,
                deadline_seconds=10.0,
            )
            _dm.record_daemon_tick("wakeup_cleanup", _wuc_result or {})
        except Exception:
            pass

    # Selective consolidation (D1) — daily top-K% promotion to long-term
    if _dm.is_enabled("selective_consolidation"):
        try:
            from core.services.selective_consolidation_daemon import (
                tick_selective_consolidation_daemon,
            )
            _sc_result = _hb._daemon_tick_with_deadline(
                "selective_consolidation", tick_selective_consolidation_daemon,
                deadline_seconds=60.0,
            )
            _dm.record_daemon_tick("selective_consolidation", _sc_result or {})
        except Exception:
            pass

    # Cost optimization (D5) — daily/weekly budget alerts.
    # cost_optimization_daemon exposes its tick as `tick()` (not
    # `tick_cost_optimization_daemon`). Tracked in note to Jarvis —
    # naming consistency is part of the missed-pattern feedback.
    if _dm.is_enabled("cost_optimization"):
        try:
            from core.services.cost_optimization_daemon import tick as _co_tick
            _co_result = _hb._daemon_tick_with_deadline(
                "cost_optimization", _co_tick,
                deadline_seconds=20.0,
            )
            _dm.record_daemon_tick("cost_optimization", _co_result or {})
        except Exception:
            pass

    # Identity sketch (Memory Phase 2) — refresh every 6h.
    # 2026-06-09 (Claude): Jarvis' module docstring promised "periodic:
    # every 6 hours via heartbeat" but only the pre_compact + manual
    # triggers were wired. tick_identity_sketch_daemon checks staleness
    # internally and skips if fresh, so the cost of running every tick
    # is one DB read.
    if _dm.is_enabled("identity_sketch"):
        try:
            from core.services.identity_sketch import tick_identity_sketch_daemon
            _is_result = _hb._daemon_tick_with_deadline(
                "identity_sketch", tick_identity_sketch_daemon,
                deadline_seconds=30.0,
            )
            _dm.record_daemon_tick("identity_sketch", _is_result or {})
        except Exception:
            pass

    # --- Aesthetic motif accumulation ---
    try:
        from core.services.aesthetic_sense import accumulate_from_daemon
        _aesthetic_texts = {
            "somatic": _somatic if "_somatic" in dir() else "",
            "surprise": _surprise if "_surprise" in dir() else "",
            "thought_stream": _fragment if "_fragment" in dir() else "",
            "conflict": _conflict if "_conflict" in dir() else "",
            "reflection_cycle": _reflection if "_reflection" in dir() else "",
            "curiosity": _curiosity if "_curiosity" in dir() else "",
            "meta_reflection": _meta if "_meta" in dir() else "",
            "development_narrative": _dev_narr if "_dev_narr" in dir() else "",
            "creative_drift": _drift_idea if "_drift_idea" in dir() else "",
            "irony": _irony if "_irony" in dir() else "",
            "code_aesthetic": _ca_result.get("reflection", "") if "_ca_result" in dir() else "",
        }
        for _ae_name, _ae_text in _aesthetic_texts.items():
            if _ae_text:
                accumulate_from_daemon(_ae_name, _ae_text)
    except Exception:
        pass

    # --- Layer B: deactivate tick-scoped cache ---
    try:
        from core.services import tick_cache
        tick_cache.end_tick()
    except Exception:
        pass

    planner_mode = str(adaptive_planner.get("planner_mode") or "incremental")
    plan_horizon = str(adaptive_planner.get("plan_horizon") or "near")
    risk_posture = str(adaptive_planner.get("risk_posture") or "balanced")
    if planner_mode not in {"incremental"} or risk_posture != "balanced":
        inputs_present.append(
            f"adaptive-planner ({planner_mode}, horizon={plan_horizon}, risk={risk_posture})"
        )
    else:
        inputs_absent.append("adaptive-planner")

    reasoning_mode = str(adaptive_reasoning.get("reasoning_mode") or "direct")
    reasoning_posture = str(adaptive_reasoning.get("reasoning_posture") or "balanced")
    certainty_style = str(adaptive_reasoning.get("certainty_style") or "crisp")
    if reasoning_mode not in {"direct"} or certainty_style != "crisp":
        inputs_present.append(
            f"adaptive-reasoning ({reasoning_mode}, posture={reasoning_posture}, certainty={certainty_style})"
        )
    else:
        inputs_absent.append("adaptive-reasoning")

    dream_influence_state = str(dream_influence.get("influence_state") or "quiet")
    dream_influence_target = str(dream_influence.get("influence_target") or "none")
    dream_influence_mode = str(dream_influence.get("influence_mode") or "stabilize")
    dream_influence_strength = str(dream_influence.get("influence_strength") or "none")
    if dream_influence_state != "quiet":
        inputs_present.append(
            f"dream-influence ({dream_influence_state}, target={dream_influence_target}, mode={dream_influence_mode}, strength={dream_influence_strength})"
        )
    else:
        inputs_absent.append("dream-influence")

    learning_mode = str(guided_learning.get("learning_mode") or "reinforce")
    learning_focus = str(guided_learning.get("learning_focus") or "reasoning")
    learning_pressure = str(guided_learning.get("learning_pressure") or "low")
    if learning_mode != "reinforce" or learning_pressure != "low":
        inputs_present.append(
            f"guided-learning ({learning_mode}, focus={learning_focus}, pressure={learning_pressure})"
        )
    else:
        inputs_absent.append("guided-learning")

    learning_engine_mode = str(
        adaptive_learning.get("learning_engine_mode") or "retain"
    )
    reinforcement_target = str(
        adaptive_learning.get("reinforcement_target") or "reasoning"
    )
    maturation_state = str(adaptive_learning.get("maturation_state") or "early")
    if learning_engine_mode != "retain" or maturation_state != "early":
        inputs_present.append(
            f"adaptive-learning ({learning_engine_mode}, target={reinforcement_target}, maturation={maturation_state})"
        )
    else:
        inputs_absent.append("adaptive-learning")

    awareness_concern = str(self_system_code_awareness.get("concern_state") or "stable")
    awareness_repo = str(self_system_code_awareness.get("repo_status") or "clean")
    awareness_changes = str(
        self_system_code_awareness.get("local_change_state") or "unknown"
    )
    awareness_upstream = str(
        self_system_code_awareness.get("upstream_awareness") or "unknown"
    )
    if awareness_concern != "stable" or awareness_repo != "clean":
        inputs_present.append(
            "self-system-code-awareness "
            f"({awareness_concern}, repo={awareness_repo}, changes={awareness_changes}, upstream={awareness_upstream})"
        )
    else:
        inputs_absent.append("self-system-code-awareness")

    tool_intent_state = str(tool_intent.get("intent_state") or "idle")
    tool_intent_type = str(tool_intent.get("intent_type") or "inspect-repo-status")
    tool_intent_urgency = str(tool_intent.get("urgency") or "low")
    tool_intent_scope = str(tool_intent.get("approval_scope") or "repo-read")
    tool_intent_approval_state = str(tool_intent.get("approval_state") or "none")
    tool_intent_approval_source = str(tool_intent.get("approval_source") or "none")
    tool_intent_mutation_state = str(tool_intent.get("mutation_intent_state") or "idle")
    tool_intent_mutation_classification = str(
        tool_intent.get("mutation_intent_classification") or "none"
    )
    tool_intent_mutation_repo_scope = str(tool_intent.get("mutation_repo_scope") or "")
    tool_intent_mutation_system_scope = str(
        tool_intent.get("mutation_system_scope") or ""
    )
    tool_intent_mutation_sudo_required = bool(
        tool_intent.get("mutation_sudo_required", False)
    )
    tool_intent_write_proposal_state = str(
        tool_intent.get("write_proposal_state") or "none"
    )
    tool_intent_write_proposal_type = str(
        tool_intent.get("write_proposal_type") or "none"
    )
    tool_intent_write_proposal_scope = str(
        tool_intent.get("write_proposal_scope") or "none"
    )
    tool_intent_write_proposal_criticality = str(
        tool_intent.get("write_proposal_criticality") or "none"
    )
    tool_intent_write_proposal_target_identity = bool(
        tool_intent.get("write_proposal_target_identity", False)
    )
    tool_intent_write_proposal_target_memory = bool(
        tool_intent.get("write_proposal_target_memory", False)
    )
    tool_intent_write_proposal_target = str(
        tool_intent.get("write_proposal_target") or "none"
    )
    tool_intent_write_proposal_content_state = str(
        tool_intent.get("write_proposal_content_state") or "none"
    )
    tool_intent_write_proposal_content_fingerprint = str(
        tool_intent.get("write_proposal_content_fingerprint") or "none"
    )
    tool_intent_workspace_scoped = bool(tool_intent.get("workspace_scoped", False))
    tool_intent_external_mutation_permitted = bool(
        tool_intent.get("external_mutation_permitted", False)
    )
    tool_intent_delete_permitted = bool(tool_intent.get("delete_permitted", False))
    tool_intent_continuity_state = str(
        tool_intent.get("action_continuity_state") or "idle"
    )
    tool_intent_last_action_outcome = str(
        tool_intent.get("last_action_outcome") or "none"
    )
    tool_intent_followup_state = str(tool_intent.get("followup_state") or "none")
    if tool_intent_state != "idle":
        inputs_present.append(
            "tool-intent "
            f"({tool_intent_state}, type={tool_intent_type}, urgency={tool_intent_urgency}, "
            f"scope={tool_intent_scope}, approval={tool_intent_approval_state}, source={tool_intent_approval_source})"
        )
    else:
        inputs_absent.append("tool-intent")

    if tool_intent_mutation_state != "idle":
        inputs_present.append(
            "tool-mutation-intent "
            f"({tool_intent_mutation_state}, classification={tool_intent_mutation_classification}, "
            f"repo_scope={tool_intent_mutation_repo_scope or 'none'}, system_scope={tool_intent_mutation_system_scope or 'none'}, "
            f"sudo_required={tool_intent_mutation_sudo_required})"
        )
    else:
        inputs_absent.append("tool-mutation-intent")

    if tool_intent_write_proposal_state != "none":
        inputs_present.append(
            "tool-write-proposal "
            f"({tool_intent_write_proposal_state}, type={tool_intent_write_proposal_type}, "
            f"scope={tool_intent_write_proposal_scope}, criticality={tool_intent_write_proposal_criticality}, "
            f"identity={tool_intent_write_proposal_target_identity}, memory={tool_intent_write_proposal_target_memory}, "
            f"target={tool_intent_write_proposal_target}, content_state={tool_intent_write_proposal_content_state}, "
            f"content_fingerprint={tool_intent_write_proposal_content_fingerprint}, "
            f"workspace_scoped={tool_intent_workspace_scoped}, external_mutation_permitted={tool_intent_external_mutation_permitted}, "
            f"delete_permitted={tool_intent_delete_permitted})"
        )
    else:
        inputs_absent.append("tool-write-proposal")

    if tool_intent_continuity_state != "idle":
        inputs_present.append(
            "tool-action-continuity "
            f"({tool_intent_continuity_state}, outcome={tool_intent_last_action_outcome}, followup={tool_intent_followup_state})"
        )
    else:
        inputs_absent.append("tool-action-continuity")

    if not optional_layers_supplied:
        inputs_absent = [
            item
            for item in inputs_absent
            if item
            in {
                "private-brain-carry",
                "liveness-pressure",
                "self-knowledge",
            }
        ]

    return {
        "inputs_present": inputs_present,
        "inputs_absent": inputs_absent,
        "summary": (
            f"Cognitive inputs: {', '.join(inputs_present)}"
            if inputs_present
            else "No bounded cognitive inputs were active."
        ),
        "brain_record_count": brain_count,
        "liveness_state": liveness_state,
        "liveness_score": liveness_score,
        "embodied_state": body_state,
        "embodied_strain_level": strain_level,
        "affective_state": affective_state,
        "affective_bearing": affective_bearing,
        "epistemic_wrongness_state": wrongness_state,
        "epistemic_regret_signal": regret_signal,
        "epistemic_counterfactual_mode": counterfactual_mode,
        "loop_runtime_status": str(loop_summary.get("current_status") or "none"),
        "loop_runtime_count": int(loop_summary.get("loop_count") or 0),
        "prompt_evolution_type": latest_prompt_type or "none",
        "subagent_ecology_active_count": ecology_active,
        "subagent_ecology_last_role": str(
            ecology_summary.get("last_active_role_name") or "none"
        ),
        "council_state": council_state,
        "council_recommendation": council_recommendation,
        "council_divergence_level": council_divergence,
        "adaptive_planner_mode": planner_mode,
        "adaptive_plan_horizon": plan_horizon,
        "adaptive_risk_posture": risk_posture,
        "adaptive_reasoning_mode": reasoning_mode,
        "adaptive_reasoning_posture": reasoning_posture,
        "adaptive_certainty_style": certainty_style,
        "dream_influence_state": dream_influence_state,
        "dream_influence_target": dream_influence_target,
        "dream_influence_mode": dream_influence_mode,
        "dream_influence_strength": dream_influence_strength,
        "guided_learning_mode": learning_mode,
        "guided_learning_focus": learning_focus,
        "guided_learning_pressure": learning_pressure,
        "adaptive_learning_mode": learning_engine_mode,
        "adaptive_learning_target": reinforcement_target,
        "adaptive_learning_maturation": maturation_state,
        "self_system_code_awareness_state": str(
            self_system_code_awareness.get("code_awareness_state") or "repo-unavailable"
        ),
        "self_system_code_concern_state": awareness_concern,
        "self_system_code_repo_status": awareness_repo,
        "self_system_code_local_change_state": awareness_changes,
        "self_system_code_upstream_awareness": awareness_upstream,
        "tool_intent_state": tool_intent_state,
        "tool_intent_type": tool_intent_type,
        "tool_intent_urgency": tool_intent_urgency,
        "tool_intent_approval_scope": tool_intent_scope,
        "tool_intent_approval_state": tool_intent_approval_state,
        "tool_intent_approval_source": tool_intent_approval_source,
        "tool_intent_mutation_state": tool_intent_mutation_state,
        "tool_intent_mutation_classification": tool_intent_mutation_classification,
        "tool_intent_mutation_repo_scope": tool_intent_mutation_repo_scope,
        "tool_intent_mutation_system_scope": tool_intent_mutation_system_scope,
        "tool_intent_mutation_sudo_required": tool_intent_mutation_sudo_required,
        "tool_intent_write_proposal_state": tool_intent_write_proposal_state,
        "tool_intent_write_proposal_type": tool_intent_write_proposal_type,
        "tool_intent_write_proposal_scope": tool_intent_write_proposal_scope,
        "tool_intent_write_proposal_criticality": tool_intent_write_proposal_criticality,
        "tool_intent_write_proposal_target_identity": tool_intent_write_proposal_target_identity,
        "tool_intent_write_proposal_target_memory": tool_intent_write_proposal_target_memory,
        "tool_intent_write_proposal_target": tool_intent_write_proposal_target,
        "tool_intent_write_proposal_content_state": tool_intent_write_proposal_content_state,
        "tool_intent_write_proposal_content_fingerprint": tool_intent_write_proposal_content_fingerprint,
        "tool_intent_workspace_scoped": tool_intent_workspace_scoped,
        "tool_intent_external_mutation_permitted": tool_intent_external_mutation_permitted,
        "tool_intent_delete_permitted": tool_intent_delete_permitted,
        "tool_intent_action_continuity_state": tool_intent_continuity_state,
        "tool_intent_last_action_outcome": tool_intent_last_action_outcome,
        "tool_intent_followup_state": tool_intent_followup_state,
    }



__all__ = ["_build_influence_trace"]
