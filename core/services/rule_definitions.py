"""Rule definitions — production rules feeding the rule_engine.

Forward-chaining rules that read signal-surface state and emit
prioritized suggestions. Advisory only — never blocks behavior.

Authored 2026-05-08 from spec by Jarvis. 35+ rules covering 6 domains
(focus, action, attention, strategy, pause, reflect) across 14+ signal
surfaces.

Design principles:
  - Lazy dict-access via .get() chains so missing fields don't crash
  - All conditions safely return False on absent surfaces
  - priority_delta in [-100, +100] — sign indicates push vs pull
  - urgency in {low, medium, high, critical}
  - Trace strings include observed values so MC can render reasoning
"""
from __future__ import annotations

from .rule_engine import EMPTY_CONCLUSION, Rule, RuleConclusion  # noqa: F401


# ── Helper: safe nested access ────────────────────────────────────────


def _get(s: dict, *keys, default=None):
    """Walk a nested dict; return default if any step is missing."""
    cur = s
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k)
        else:
            return default
        if cur is None:
            return default
    return cur


def _len(s: dict, surface: str, key: str = "items") -> int:
    """Count items in a surface list field."""
    items = _get(s, surface, key, default=[])
    return len(items) if isinstance(items, list) else 0


# ═══════════════════════════════════════════════════════════════════════
# RULES
# ═══════════════════════════════════════════════════════════════════════


# ── focus domain ──────────────────────────────────────────────────────

_RULES_FOCUS = [
    Rule(
        name="high_curiosity_promotes_exploration",
        description="Many open questions → shift to exploratory mode",
        domain="focus",
        priority=80,
        condition=lambda s: _len(s, "curiosity", "open_questions") >= 5,
        action=lambda s: RuleConclusion(
            rule_name="high_curiosity_promotes_exploration",
            suggestion="Curiosity surface has many open questions — shift to exploratory mode",
            priority_delta=+25,
            trace=f"open_questions={_len(s, 'curiosity', 'open_questions')} ≥ 5 → explore",
            target_domain="focus",
            urgency="medium",
        ),
    ),
    Rule(
        name="strong_appetite_focus",
        description="An appetite with intensity ≥ 0.85 pulls focus there",
        domain="focus",
        priority=85,
        condition=lambda s: any(
            (a or {}).get("intensity", 0) >= 0.85
            for a in (_get(s, "desire", "appetites", default=[]) or [])
        ),
        action=lambda s: RuleConclusion(
            rule_name="strong_appetite_focus",
            suggestion="A strong appetite (intensity ≥ 0.85) should drive current focus",
            priority_delta=+30,
            trace=(
                "strongest appetite="
                + str(max(
                    ((a or {}).get("intensity", 0)
                     for a in (_get(s, "desire", "appetites", default=[]) or [])),
                    default=0,
                ))
            ),
            target_domain="focus",
            urgency="high",
        ),
    ),
    Rule(
        name="goal_signal_active_anchors_focus",
        description="Active goal_signal anchors focus in the goal's direction",
        domain="focus",
        priority=70,
        condition=lambda s: bool(_get(s, "goal_signal", "active", default=False))
        and _len(s, "goal_signal") > 0,
        action=lambda s: RuleConclusion(
            rule_name="goal_signal_active_anchors_focus",
            suggestion="Hold focus in goal_signal direction, don't drift away",
            priority_delta=+15,
            trace=f"goal_items={_len(s, 'goal_signal')} active=True",
            target_domain="focus",
            urgency="medium",
        ),
    ),
    Rule(
        name="creative_drift_pulls_focus_to_craft",
        description="Active creative_drift signal → weight toward creative tasks",
        domain="focus",
        priority=60,
        condition=lambda s: bool(_get(s, "creative_drift", "active", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="creative_drift_pulls_focus_to_craft",
            suggestion="Creative drift is active — handle a creative task before context loss",
            priority_delta=+18,
            trace="creative_drift.active=True",
            target_domain="focus",
            urgency="medium",
        ),
    ),
    Rule(
        name="meaning_significance_concentrates_focus",
        description="High meaning_significance → concentrate focus, avoid scattering",
        domain="focus",
        priority=65,
        condition=lambda s: str(
            _get(s, "meaning_significance", "level", default="")
        ).lower() in ("high", "critical"),
        action=lambda s: RuleConclusion(
            rule_name="meaning_significance_concentrates_focus",
            suggestion="High significance signal — concentrate, drop sidetracks",
            priority_delta=+22,
            trace=f"meaning_significance.level={_get(s, 'meaning_significance', 'level', default='?')}",
            target_domain="focus",
            urgency="high",
        ),
    ),
]


# ── action domain ─────────────────────────────────────────────────────

_RULES_ACTION = [
    Rule(
        name="open_loops_demand_action",
        description="Many open_loops above threshold → fire an action instead of new ones",
        domain="action",
        priority=90,
        condition=lambda s: _len(s, "open_loop") >= 5,
        action=lambda s: RuleConclusion(
            rule_name="open_loops_demand_action",
            suggestion=f"{_len(s, 'open_loop')} open loops — close one, don't start new ones",
            priority_delta=+35,
            trace=f"open_loops={_len(s, 'open_loop')} ≥ 5",
            target_domain="action",
            urgency="high",
        ),
    ),
    Rule(
        name="autonomy_pressure_active_invites_initiative",
        description="autonomy_pressure active + no ongoing action → take initiative",
        domain="action",
        priority=75,
        condition=lambda s: bool(_get(s, "autonomy_pressure", "active", default=False))
        and str(_get(s, "autonomy_pressure", "proactive_execution_state", default=""))
        != "in-progress",
        action=lambda s: RuleConclusion(
            rule_name="autonomy_pressure_active_invites_initiative",
            suggestion="Autonomy pressure is active and you're standing still — take an initiative",
            priority_delta=+20,
            trace="autonomy_pressure.active=True, proactive_execution≠in-progress",
            target_domain="action",
            urgency="medium",
        ),
    ),
    Rule(
        name="release_marker_triggers_completion",
        description="Active release_marker → finish and release before next",
        domain="action",
        priority=85,
        condition=lambda s: bool(_get(s, "release_marker", "active", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="release_marker_triggers_completion",
            suggestion="Release marker fired — finish and communicate result before anything new",
            priority_delta=+28,
            trace="release_marker.active=True",
            target_domain="action",
            urgency="high",
        ),
    ),
    Rule(
        name="conflict_demands_resolution_action",
        description="Active conflict events → resolve before moving on",
        domain="action",
        priority=88,
        condition=lambda s: _len(s, "conflict") >= 1,
        action=lambda s: RuleConclusion(
            rule_name="conflict_demands_resolution_action",
            suggestion=f"{_len(s, 'conflict')} active conflicts — address explicitly",
            priority_delta=+32,
            trace=f"conflict_items={_len(s, 'conflict')}",
            target_domain="action",
            urgency="high",
        ),
    ),
    Rule(
        name="thought_proposals_should_be_acted_or_dropped",
        description="Many thought_proposals piling up → decide, don't let them sit",
        domain="action",
        priority=55,
        condition=lambda s: _len(s, "thought_proposals") >= 8,
        action=lambda s: RuleConclusion(
            rule_name="thought_proposals_should_be_acted_or_dropped",
            suggestion="Too many unaddressed proposals — decide on the top 3",
            priority_delta=+12,
            trace=f"thought_proposals={_len(s, 'thought_proposals')} ≥ 8",
            target_domain="action",
            urgency="medium",
        ),
    ),
    Rule(
        name="executive_contradiction_blocks_until_resolved",
        description="Executive contradiction → stop, clarify before acting",
        domain="action",
        priority=95,
        condition=lambda s: bool(
            _get(s, "executive_contradiction", "active", default=False)
        ),
        action=lambda s: RuleConclusion(
            rule_name="executive_contradiction_blocks_until_resolved",
            suggestion="Self-contradiction in executive layer — resolve before further action",
            priority_delta=+45,
            trace="executive_contradiction.active=True",
            target_domain="action",
            urgency="critical",
        ),
    ),
]


# ── attention domain ──────────────────────────────────────────────────

_RULES_ATTENTION = [
    Rule(
        name="surprise_demands_attention",
        description="Active surprise event → investigate before anything else",
        domain="attention",
        priority=92,
        condition=lambda s: bool(_get(s, "surprise", "active", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="surprise_demands_attention",
            suggestion="A surprise signal demands attention now",
            priority_delta=+38,
            trace="surprise.active=True",
            target_domain="attention",
            urgency="high",
        ),
    ),
    Rule(
        name="user_model_change_requires_attention",
        description="user_model has update that hasn't been reviewed",
        domain="attention",
        priority=70,
        condition=lambda s: bool(_get(s, "user_model", "pending_review", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="user_model_change_requires_attention",
            suggestion="user_model has unreviewed change — look before it becomes stale",
            priority_delta=+18,
            trace="user_model.pending_review=True",
            target_domain="attention",
            urgency="medium",
        ),
    ),
    Rule(
        name="absence_signal_attention",
        description="Active absence signal (Bjørn is away) → reduce notify volume",
        domain="attention",
        priority=50,
        condition=lambda s: bool(_get(s, "absence", "active", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="absence_signal_attention",
            suggestion="User absent — defer non-critical notifications",
            priority_delta=-15,
            trace="absence.active=True",
            target_domain="attention",
            urgency="low",
        ),
    ),
    Rule(
        name="loop_runtime_warning_attention",
        description="loop_runtime reports abnormal state",
        domain="attention",
        priority=82,
        condition=lambda s: str(
            _get(s, "loop_runtime", "summary", "status", default="")
        ).lower() in ("warning", "stuck", "drift"),
        action=lambda s: RuleConclusion(
            rule_name="loop_runtime_warning_attention",
            suggestion="loop_runtime reports warning/stuck/drift — investigate",
            priority_delta=+28,
            trace=f"loop_runtime.status={_get(s, 'loop_runtime', 'summary', 'status', default='?')}",
            target_domain="attention",
            urgency="high",
        ),
    ),
    Rule(
        name="regret_signal_calls_attention",
        description="Active regret_signal → give it attention BEFORE next turn",
        domain="attention",
        priority=78,
        condition=lambda s: str(_get(s, "epistemic_state", "regret_signal", default="none")) != "none",
        action=lambda s: RuleConclusion(
            rule_name="regret_signal_calls_attention",
            suggestion="Active regret — look at it before next action",
            priority_delta=+25,
            trace=f"epistemic_state.regret_signal={_get(s, 'epistemic_state', 'regret_signal', default='?')}",
            target_domain="attention",
            urgency="high",
        ),
    ),
    Rule(
        name="irony_present_check_tone",
        description="Active irony signal → check if user's tone is interpreted correctly",
        domain="attention",
        priority=58,
        condition=lambda s: bool(_get(s, "irony", "active", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="irony_present_check_tone",
            suggestion="Irony signal active — verify tone interpretation before responding",
            priority_delta=+12,
            trace="irony.active=True",
            target_domain="attention",
            urgency="medium",
        ),
    ),
]


# ── strategy domain ───────────────────────────────────────────────────

_RULES_STRATEGY = [
    Rule(
        name="low_confidence_pull_back_strategy",
        description="Affective confidence < 0.4 → stop and verify instead of continuing",
        domain="strategy",
        priority=72,
        condition=lambda s: float(
            _get(s, "affective_meta_state", "live_emotional_state", "confidence",
                 default=0.5) or 0.5
        ) < 0.4,
        action=lambda s: RuleConclusion(
            rule_name="low_confidence_pull_back_strategy",
            suggestion="Low confidence — verify assumptions or ask, rather than continuing",
            priority_delta=+20,
            trace=(
                f"affective.confidence="
                f"{_get(s, 'affective_meta_state', 'live_emotional_state', 'confidence', default='?')}"
            ),
            target_domain="strategy",
            urgency="medium",
        ),
    ),
    Rule(
        name="wrongness_state_known_change_strategy",
        description="epistemic_state.wrongness_state ≠ clear → new strategy needed",
        domain="strategy",
        priority=85,
        condition=lambda s: str(
            _get(s, "epistemic_state", "wrongness_state", default="clear")
        ).lower() not in ("clear", "unknown", ""),
        action=lambda s: RuleConclusion(
            rule_name="wrongness_state_known_change_strategy",
            suggestion="Epistemic wrongness found — change strategy, don't continue same track",
            priority_delta=+30,
            trace=f"wrongness={_get(s, 'epistemic_state', 'wrongness_state', default='?')}",
            target_domain="strategy",
            urgency="high",
        ),
    ),
    Rule(
        name="emergent_pattern_informs_strategy",
        description="Active emergent pattern (upgraded) → incorporate into strategy considerations",
        domain="strategy",
        priority=68,
        condition=lambda s: any(
            str((p or {}).get("status", "")) == "upgraded"
            for p in (_get(s, "emergent", "items", default=[]) or [])
        ),
        action=lambda s: RuleConclusion(
            rule_name="emergent_pattern_informs_strategy",
            suggestion="An upgraded emergent pattern deserves strategy adjustment",
            priority_delta=+18,
            trace=f"emergent_upgraded_count={sum(1 for p in (_get(s, 'emergent', 'items', default=[]) or []) if str((p or {}).get('status', '')) == 'upgraded')}",
            target_domain="strategy",
            urgency="medium",
        ),
    ),
    Rule(
        name="counterfactual_mode_active_review_strategy",
        description="counterfactual_mode active → use it for strategy evaluation",
        domain="strategy",
        priority=62,
        condition=lambda s: str(
            _get(s, "epistemic_state", "counterfactual_mode", default="none")
        ) != "none",
        action=lambda s: RuleConclusion(
            rule_name="counterfactual_mode_active_review_strategy",
            suggestion="Counterfactuals are active — use them to re-evaluate the plan",
            priority_delta=+15,
            trace=f"counterfactual_mode={_get(s, 'epistemic_state', 'counterfactual_mode', default='?')}",
            target_domain="strategy",
            urgency="medium",
        ),
    ),
    Rule(
        name="self_review_cadence_due_strategy",
        description="self_review_cadence reports overdue → run review now",
        domain="strategy",
        priority=78,
        condition=lambda s: bool(_get(s, "self_review_cadence", "overdue", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="self_review_cadence_due_strategy",
            suggestion="Self-review is overdue — run it before next major decision",
            priority_delta=+22,
            trace="self_review_cadence.overdue=True",
            target_domain="strategy",
            urgency="high",
        ),
    ),
    Rule(
        name="loyalty_gradient_informs_priorities",
        description="loyalty_gradient signals drift → realign priorities",
        domain="strategy",
        priority=66,
        condition=lambda s: str(
            _get(s, "loyalty_gradient", "drift_state", default="aligned")
        ).lower() in ("drifting", "misaligned"),
        action=lambda s: RuleConclusion(
            rule_name="loyalty_gradient_informs_priorities",
            suggestion="Loyalty drift detected — realign with Bjørn's direction",
            priority_delta=+18,
            trace=f"loyalty_drift={_get(s, 'loyalty_gradient', 'drift_state', default='?')}",
            target_domain="strategy",
            urgency="medium",
        ),
    ),
]


# ── pause domain ──────────────────────────────────────────────────────

_RULES_PAUSE = [
    Rule(
        name="high_strain_demands_pause",
        description="embodied_state.strain_level=high → pause before further work",
        domain="pause",
        priority=88,
        condition=lambda s: str(
            _get(s, "embodied_state", "strain_level", default="low")
        ).lower() in ("high", "critical"),
        action=lambda s: RuleConclusion(
            rule_name="high_strain_demands_pause",
            suggestion="High strain level — pause, don't push",
            priority_delta=-30,
            trace=f"strain_level={_get(s, 'embodied_state', 'strain_level', default='?')}",
            target_domain="pause",
            urgency="high",
        ),
    ),
    Rule(
        name="fatigue_high_pause",
        description="affective fatigue > 0.7 → pause og restitution",
        domain="pause",
        priority=82,
        condition=lambda s: float(
            _get(s, "affective_meta_state", "live_emotional_state", "fatigue",
                 default=0) or 0
        ) > 0.7,
        action=lambda s: RuleConclusion(
            rule_name="fatigue_high_pause",
            suggestion="Fatigue over 0.7 — short pause before next task",
            priority_delta=-25,
            trace=(
                "fatigue="
                f"{_get(s, 'affective_meta_state', 'live_emotional_state', 'fatigue', default='?')}"
            ),
            target_domain="pause",
            urgency="medium",
        ),
    ),
    Rule(
        name="reflective_load_high_pause",
        description="affective_meta_state.reflective_load=high → stop, reflektér",
        domain="pause",
        priority=70,
        condition=lambda s: str(
            _get(s, "affective_meta_state", "reflective_load", default="low")
        ).lower() in ("high", "saturated"),
        action=lambda s: RuleConclusion(
            rule_name="reflective_load_high_pause",
            suggestion="Reflective load saturated — pause to consolidate",
            priority_delta=-20,
            trace=f"reflective_load={_get(s, 'affective_meta_state', 'reflective_load', default='?')}",
            target_domain="pause",
            urgency="medium",
        ),
    ),
    Rule(
        name="metabolism_self_erasure_critical_pause",
        description="metabolism_state self_erasure_state aktivt → STOP og reflektér",
        domain="pause",
        priority=98,
        condition=lambda s: str(
            _get(s, "metabolism_state", "self_erasure_state", default="none")
        ) not in ("none", "not-canonical-deletion", ""),
        action=lambda s: RuleConclusion(
            rule_name="metabolism_self_erasure_critical_pause",
            suggestion="Self-erasure detected — critical pause, reflect before anything else",
            priority_delta=-50,
            trace=f"self_erasure_state={_get(s, 'metabolism_state', 'self_erasure_state', default='?')}",
            target_domain="pause",
            urgency="critical",
        ),
    ),
    Rule(
        name="recovery_state_invites_rest",
        description="embodied recovery_state=recovering → respektér genopretning",
        domain="pause",
        priority=60,
        condition=lambda s: str(
            _get(s, "embodied_state", "recovery_state", default="steady")
        ).lower() in ("recovering", "depleted"),
        action=lambda s: RuleConclusion(
            rule_name="recovery_state_invites_rest",
            suggestion="Body in recovery — avoid heavy tasks, keep light things going",
            priority_delta=-18,
            trace=f"recovery_state={_get(s, 'embodied_state', 'recovery_state', default='?')}",
            target_domain="pause",
            urgency="medium",
        ),
    ),
    Rule(
        name="regulation_homeostasis_off_pause",
        description="regulation_homeostasis out of balance → regulate before more",
        domain="pause",
        priority=74,
        condition=lambda s: str(
            _get(s, "regulation_homeostasis", "balance_state", default="balanced")
        ).lower() in ("off", "unbalanced", "drifting"),
        action=lambda s: RuleConclusion(
            rule_name="regulation_homeostasis_off_pause",
            suggestion="Homeostasis out of balance — pause for regulation",
            priority_delta=-22,
            trace=f"balance={_get(s, 'regulation_homeostasis', 'balance_state', default='?')}",
            target_domain="pause",
            urgency="medium",
        ),
    ),
]


# ── reflect domain ────────────────────────────────────────────────────

_RULES_REFLECT = [
    Rule(
        name="meta_reflection_due",
        description="meta_reflection reports not run for too long",
        domain="reflect",
        priority=64,
        condition=lambda s: bool(_get(s, "meta_reflection", "due", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="meta_reflection_due",
            suggestion="Meta-reflection is due — look from above at today's actions",
            priority_delta=+15,
            trace="meta_reflection.due=True",
            target_domain="reflect",
            urgency="medium",
        ),
    ),
    Rule(
        name="reflection_signal_active_reflect",
        description="reflection_signal active → run reflection on next tick",
        domain="reflect",
        priority=72,
        condition=lambda s: bool(_get(s, "reflection_signal", "active", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="reflection_signal_active_reflect",
            suggestion="Reflection signal active — set aside a round to reflect",
            priority_delta=+18,
            trace="reflection_signal.active=True",
            target_domain="reflect",
            urgency="medium",
        ),
    ),
    Rule(
        name="dream_articulation_present_reflect",
        description="dream_articulation has new insight → integrate into understanding",
        domain="reflect",
        priority=58,
        condition=lambda s: _len(s, "dream_articulation") >= 1,
        action=lambda s: RuleConclusion(
            rule_name="dream_articulation_present_reflect",
            suggestion=f"{_len(s, 'dream_articulation')} dream insights — reflect and integrate",
            priority_delta=+10,
            trace=f"dream_articulation_items={_len(s, 'dream_articulation')}",
            target_domain="reflect",
            urgency="low",
        ),
    ),
    Rule(
        name="self_narrative_continuity_break_reflect",
        description="self_narrative_continuity break → reflect on the identity thread",
        domain="reflect",
        priority=80,
        condition=lambda s: str(
            _get(s, "self_narrative_continuity", "continuity_state", default="continuous")
        ).lower() in ("break", "broken", "fragmented"),
        action=lambda s: RuleConclusion(
            rule_name="self_narrative_continuity_break_reflect",
            suggestion="Narrative continuity-break — reflect on how the thread comes together again",
            priority_delta=+25,
            trace=f"continuity={_get(s, 'self_narrative_continuity', 'continuity_state', default='?')}",
            target_domain="reflect",
            urgency="high",
        ),
    ),
    Rule(
        name="witness_signal_invites_observation",
        description="witness signal aktiv → tag et observerings-perspektiv",
        domain="reflect",
        priority=55,
        condition=lambda s: bool(_get(s, "witness", "active", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="witness_signal_invites_observation",
            suggestion="Witness signal — look at yourself from outside this round",
            priority_delta=+8,
            trace="witness.active=True",
            target_domain="reflect",
            urgency="low",
        ),
    ),
    Rule(
        name="existential_wonder_reflect",
        description="Aktivt existential_wonder signal → giv det plads",
        domain="reflect",
        priority=48,
        condition=lambda s: bool(_get(s, "existential_wonder", "active", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="existential_wonder_reflect",
            suggestion="Existential wonder fyret — giv det en runde, ikke push gennem",
            priority_delta=+8,
            trace="existential_wonder.active=True",
            target_domain="reflect",
            urgency="low",
        ),
    ),
    Rule(
        name="temporal_recurrence_pattern_reflect",
        description="temporal_recurrence has repeated pattern → reflect on the rhythm",
        domain="reflect",
        priority=52,
        condition=lambda s: _len(s, "temporal_recurrence") >= 3,
        action=lambda s: RuleConclusion(
            rule_name="temporal_recurrence_pattern_reflect",
            suggestion=f"{_len(s, 'temporal_recurrence')} temporally repeated signals — reflect on the rhythm",
            priority_delta=+10,
            trace=f"temporal_recurrence_count={_len(s, 'temporal_recurrence')}",
            target_domain="reflect",
            urgency="low",
        ),
    ),
]


# ═══════════════════════════════════════════════════════════════════════
# AGGREGATE
# ═══════════════════════════════════════════════════════════════════════


ALL_RULES: list[Rule] = (
    _RULES_FOCUS
    + _RULES_ACTION
    + _RULES_ATTENTION
    + _RULES_STRATEGY
    + _RULES_PAUSE
    + _RULES_REFLECT
)


__all__ = ["ALL_RULES"]


