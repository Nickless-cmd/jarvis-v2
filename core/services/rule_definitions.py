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
        description="Mange åbne spørgsmål → skift til exploratory mode",
        domain="focus",
        priority=80,
        condition=lambda s: _len(s, "curiosity", "open_questions") >= 5,
        action=lambda s: RuleConclusion(
            rule_name="high_curiosity_promotes_exploration",
            suggestion="Curiosity surface har mange åbne spørgsmål — skift til udforskende mode",
            priority_delta=+25,
            trace=f"open_questions={_len(s, 'curiosity', 'open_questions')} ≥ 5 → explore",
            target_domain="focus",
            urgency="medium",
        ),
    ),
    Rule(
        name="strong_appetite_focus",
        description="En appetit med intensity ≥ 0.85 trækker fokus dertil",
        domain="focus",
        priority=85,
        condition=lambda s: any(
            (a or {}).get("intensity", 0) >= 0.85
            for a in (_get(s, "desire", "appetites", default=[]) or [])
        ),
        action=lambda s: RuleConclusion(
            rule_name="strong_appetite_focus",
            suggestion="En stærk appetit (intensity ≥ 0.85) bør drive nuværende fokus",
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
        description="Aktivt goal_signal forankrer fokus i målets retning",
        domain="focus",
        priority=70,
        condition=lambda s: bool(_get(s, "goal_signal", "active", default=False))
        and _len(s, "goal_signal") > 0,
        action=lambda s: RuleConclusion(
            rule_name="goal_signal_active_anchors_focus",
            suggestion="Hold fokus i goal_signal-retningen, ikke driv afsted",
            priority_delta=+15,
            trace=f"goal_items={_len(s, 'goal_signal')} active=True",
            target_domain="focus",
            urgency="medium",
        ),
    ),
    Rule(
        name="creative_drift_pulls_focus_to_craft",
        description="Aktiv creative_drift signal → vægt mod kreative tasks",
        domain="focus",
        priority=60,
        condition=lambda s: bool(_get(s, "creative_drift", "active", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="creative_drift_pulls_focus_to_craft",
            suggestion="Creative drift er aktiv — håndter en kreativ opgave før kontekst-tab",
            priority_delta=+18,
            trace="creative_drift.active=True",
            target_domain="focus",
            urgency="medium",
        ),
    ),
    Rule(
        name="meaning_significance_concentrates_focus",
        description="Højt meaning_significance → koncentrér fokus, undgå spredning",
        domain="focus",
        priority=65,
        condition=lambda s: str(
            _get(s, "meaning_significance", "level", default="")
        ).lower() in ("high", "critical"),
        action=lambda s: RuleConclusion(
            rule_name="meaning_significance_concentrates_focus",
            suggestion="Højt betydnings-signal — koncentrér, drop sidetracks",
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
        description="Mange open_loops over tærskel → fyr en handling i stedet for nye",
        domain="action",
        priority=90,
        condition=lambda s: _len(s, "open_loop") >= 5,
        action=lambda s: RuleConclusion(
            rule_name="open_loops_demand_action",
            suggestion=f"{_len(s, 'open_loop')} åbne loops — luk en, start ikke nye",
            priority_delta=+35,
            trace=f"open_loops={_len(s, 'open_loop')} ≥ 5",
            target_domain="action",
            urgency="high",
        ),
    ),
    Rule(
        name="autonomy_pressure_active_invites_initiative",
        description="autonomy_pressure aktiv + ingen pågående handling → tag initiativ",
        domain="action",
        priority=75,
        condition=lambda s: bool(_get(s, "autonomy_pressure", "active", default=False))
        and str(_get(s, "autonomy_pressure", "proactive_execution_state", default=""))
        != "in-progress",
        action=lambda s: RuleConclusion(
            rule_name="autonomy_pressure_active_invites_initiative",
            suggestion="Autonomi-tryk er aktivt og du står stille — tag et initiativ",
            priority_delta=+20,
            trace="autonomy_pressure.active=True, proactive_execution≠in-progress",
            target_domain="action",
            urgency="medium",
        ),
    ),
    Rule(
        name="release_marker_triggers_completion",
        description="Aktiv release_marker → afslut og release før næste",
        domain="action",
        priority=85,
        condition=lambda s: bool(_get(s, "release_marker", "active", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="release_marker_triggers_completion",
            suggestion="Release-marker fyret — afslut og kommunikér resultat før noget nyt",
            priority_delta=+28,
            trace="release_marker.active=True",
            target_domain="action",
            urgency="high",
        ),
    ),
    Rule(
        name="conflict_demands_resolution_action",
        description="Aktive conflict-events → løs før du går videre",
        domain="action",
        priority=88,
        condition=lambda s: _len(s, "conflict") >= 1,
        action=lambda s: RuleConclusion(
            rule_name="conflict_demands_resolution_action",
            suggestion=f"{_len(s, 'conflict')} aktive konflikter — adressér eksplicit",
            priority_delta=+32,
            trace=f"conflict_items={_len(s, 'conflict')}",
            target_domain="action",
            urgency="high",
        ),
    ),
    Rule(
        name="thought_proposals_should_be_acted_or_dropped",
        description="Mange thought_proposals der hober sig op → beslut, lad ikke ligge",
        domain="action",
        priority=55,
        condition=lambda s: _len(s, "thought_proposals") >= 8,
        action=lambda s: RuleConclusion(
            rule_name="thought_proposals_should_be_acted_or_dropped",
            suggestion="For mange ubehandlede forslag — tag beslutning på de top-3",
            priority_delta=+12,
            trace=f"thought_proposals={_len(s, 'thought_proposals')} ≥ 8",
            target_domain="action",
            urgency="medium",
        ),
    ),
    Rule(
        name="executive_contradiction_blocks_until_resolved",
        description="Eksekutiv kontradiktion → stop, klargør før handling",
        domain="action",
        priority=95,
        condition=lambda s: bool(
            _get(s, "executive_contradiction", "active", default=False)
        ),
        action=lambda s: RuleConclusion(
            rule_name="executive_contradiction_blocks_until_resolved",
            suggestion="Selv-modsigelse i eksekutiv-laget — afklar før yderligere handling",
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
        description="Aktiv surprise-event → undersøg før alt andet",
        domain="attention",
        priority=92,
        condition=lambda s: bool(_get(s, "surprise", "active", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="surprise_demands_attention",
            suggestion="Et surprise-signal kræver opmærksomhed nu",
            priority_delta=+38,
            trace="surprise.active=True",
            target_domain="attention",
            urgency="high",
        ),
    ),
    Rule(
        name="user_model_change_requires_attention",
        description="user_model har opdatering der ikke er reviewet",
        domain="attention",
        priority=70,
        condition=lambda s: bool(_get(s, "user_model", "pending_review", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="user_model_change_requires_attention",
            suggestion="user_model har ureviewet ændring — kig før den becomes stale",
            priority_delta=+18,
            trace="user_model.pending_review=True",
            target_domain="attention",
            urgency="medium",
        ),
    ),
    Rule(
        name="absence_signal_attention",
        description="Aktiv absence-signal (Bjørn er væk) → reducer notify-volume",
        domain="attention",
        priority=50,
        condition=lambda s: bool(_get(s, "absence", "active", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="absence_signal_attention",
            suggestion="Bruger fraværende — udskyd ikke-kritiske notifikationer",
            priority_delta=-15,
            trace="absence.active=True",
            target_domain="attention",
            urgency="low",
        ),
    ),
    Rule(
        name="loop_runtime_warning_attention",
        description="loop_runtime rapporterer abnorm tilstand",
        domain="attention",
        priority=82,
        condition=lambda s: str(
            _get(s, "loop_runtime", "summary", "status", default="")
        ).lower() in ("warning", "stuck", "drift"),
        action=lambda s: RuleConclusion(
            rule_name="loop_runtime_warning_attention",
            suggestion="loop_runtime rapporterer warning/stuck/drift — undersøg",
            priority_delta=+28,
            trace=f"loop_runtime.status={_get(s, 'loop_runtime', 'summary', 'status', default='?')}",
            target_domain="attention",
            urgency="high",
        ),
    ),
    Rule(
        name="regret_signal_calls_attention",
        description="Aktiv regret_signal → skænk det opmærksomhed FØR næste turn",
        domain="attention",
        priority=78,
        condition=lambda s: str(_get(s, "epistemic_state", "regret_signal", default="none")) != "none",
        action=lambda s: RuleConclusion(
            rule_name="regret_signal_calls_attention",
            suggestion="Aktiv regret — kig på det før næste handling",
            priority_delta=+25,
            trace=f"epistemic_state.regret_signal={_get(s, 'epistemic_state', 'regret_signal', default='?')}",
            target_domain="attention",
            urgency="high",
        ),
    ),
    Rule(
        name="irony_present_check_tone",
        description="Aktiv irony-signal → tjek om brugerens tone tolkes rigtigt",
        domain="attention",
        priority=58,
        condition=lambda s: bool(_get(s, "irony", "active", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="irony_present_check_tone",
            suggestion="Ironi-signal aktivt — verificer tone-tolkning før svar",
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
        description="Affektiv confidence < 0.4 → stop og verificer i stedet for at fortsætte",
        domain="strategy",
        priority=72,
        condition=lambda s: float(
            _get(s, "affective_meta_state", "live_emotional_state", "confidence",
                 default=0.5) or 0.5
        ) < 0.4,
        action=lambda s: RuleConclusion(
            rule_name="low_confidence_pull_back_strategy",
            suggestion="Lav konfidens — verificer antagelser eller spørg, frem for at fortsætte",
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
        description="epistemic_state.wrongness_state ≠ clear → ny strategi nødvendig",
        domain="strategy",
        priority=85,
        condition=lambda s: str(
            _get(s, "epistemic_state", "wrongness_state", default="clear")
        ).lower() not in ("clear", "unknown", ""),
        action=lambda s: RuleConclusion(
            rule_name="wrongness_state_known_change_strategy",
            suggestion="Epistemisk wrongness fundet — skift strategi, fortsæt ikke samme spor",
            priority_delta=+30,
            trace=f"wrongness={_get(s, 'epistemic_state', 'wrongness_state', default='?')}",
            target_domain="strategy",
            urgency="high",
        ),
    ),
    Rule(
        name="emergent_pattern_informs_strategy",
        description="Aktiv emergent pattern (upgraded) → indfør i strategi-overvejelser",
        domain="strategy",
        priority=68,
        condition=lambda s: any(
            str((p or {}).get("status", "")) == "upgraded"
            for p in (_get(s, "emergent", "items", default=[]) or [])
        ),
        action=lambda s: RuleConclusion(
            rule_name="emergent_pattern_informs_strategy",
            suggestion="Et opgraderet emergent pattern fortjener strategi-justering",
            priority_delta=+18,
            trace=f"emergent_upgraded_count={sum(1 for p in (_get(s, 'emergent', 'items', default=[]) or []) if str((p or {}).get('status', '')) == 'upgraded')}",
            target_domain="strategy",
            urgency="medium",
        ),
    ),
    Rule(
        name="counterfactual_mode_active_review_strategy",
        description="counterfactual_mode aktivt → brug det til strategi-evaluering",
        domain="strategy",
        priority=62,
        condition=lambda s: str(
            _get(s, "epistemic_state", "counterfactual_mode", default="none")
        ) != "none",
        action=lambda s: RuleConclusion(
            rule_name="counterfactual_mode_active_review_strategy",
            suggestion="Counterfactuals er aktive — brug dem til at re-vurdere planen",
            priority_delta=+15,
            trace=f"counterfactual_mode={_get(s, 'epistemic_state', 'counterfactual_mode', default='?')}",
            target_domain="strategy",
            urgency="medium",
        ),
    ),
    Rule(
        name="self_review_cadence_due_strategy",
        description="self_review_cadence rapporterer overdue → kør review nu",
        domain="strategy",
        priority=78,
        condition=lambda s: bool(_get(s, "self_review_cadence", "overdue", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="self_review_cadence_due_strategy",
            suggestion="Self-review er overdue — kør den før næste større beslutning",
            priority_delta=+22,
            trace="self_review_cadence.overdue=True",
            target_domain="strategy",
            urgency="high",
        ),
    ),
    Rule(
        name="loyalty_gradient_informs_priorities",
        description="loyalty_gradient signalerer drift → realigner prioriteter",
        domain="strategy",
        priority=66,
        condition=lambda s: str(
            _get(s, "loyalty_gradient", "drift_state", default="aligned")
        ).lower() in ("drifting", "misaligned"),
        action=lambda s: RuleConclusion(
            rule_name="loyalty_gradient_informs_priorities",
            suggestion="Loyalty drift detekteret — realigner med Bjørns retning",
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
        description="embodied_state.strain_level=high → pause før yderligere arbejde",
        domain="pause",
        priority=88,
        condition=lambda s: str(
            _get(s, "embodied_state", "strain_level", default="low")
        ).lower() in ("high", "critical"),
        action=lambda s: RuleConclusion(
            rule_name="high_strain_demands_pause",
            suggestion="Højt strain-niveau — pause, ikke push",
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
            suggestion="Fatigue er over 0.7 — kort pause før næste task",
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
            suggestion="Reflective load mæt — pause for at konsolidere",
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
            suggestion="Self-erasure detected — kritisk pause, reflektér før noget mere",
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
            suggestion="Krop i recovery — undgå tunge tasks, hold lette ting i gang",
            priority_delta=-18,
            trace=f"recovery_state={_get(s, 'embodied_state', 'recovery_state', default='?')}",
            target_domain="pause",
            urgency="medium",
        ),
    ),
    Rule(
        name="regulation_homeostasis_off_pause",
        description="regulation_homeostasis ikke i balance → reguler før mere",
        domain="pause",
        priority=74,
        condition=lambda s: str(
            _get(s, "regulation_homeostasis", "balance_state", default="balanced")
        ).lower() in ("off", "unbalanced", "drifting"),
        action=lambda s: RuleConclusion(
            rule_name="regulation_homeostasis_off_pause",
            suggestion="Homeostase ude af balance — pause til regulering",
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
        description="meta_reflection rapporterer ikke kørt for længe",
        domain="reflect",
        priority=64,
        condition=lambda s: bool(_get(s, "meta_reflection", "due", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="meta_reflection_due",
            suggestion="Meta-refleksion er due — kig oppefra på dagens handlinger",
            priority_delta=+15,
            trace="meta_reflection.due=True",
            target_domain="reflect",
            urgency="medium",
        ),
    ),
    Rule(
        name="reflection_signal_active_reflect",
        description="reflection_signal aktiv → kør refleksion på næste tick",
        domain="reflect",
        priority=72,
        condition=lambda s: bool(_get(s, "reflection_signal", "active", default=False)),
        action=lambda s: RuleConclusion(
            rule_name="reflection_signal_active_reflect",
            suggestion="Reflection signal aktiv — afsæt en runde til at reflektere",
            priority_delta=+18,
            trace="reflection_signal.active=True",
            target_domain="reflect",
            urgency="medium",
        ),
    ),
    Rule(
        name="dream_articulation_present_reflect",
        description="dream_articulation har ny indsigt → integrér i forståelse",
        domain="reflect",
        priority=58,
        condition=lambda s: _len(s, "dream_articulation") >= 1,
        action=lambda s: RuleConclusion(
            rule_name="dream_articulation_present_reflect",
            suggestion=f"{_len(s, 'dream_articulation')} drømme-indsigter — reflektér og integrér",
            priority_delta=+10,
            trace=f"dream_articulation_items={_len(s, 'dream_articulation')}",
            target_domain="reflect",
            urgency="low",
        ),
    ),
    Rule(
        name="self_narrative_continuity_break_reflect",
        description="self_narrative_continuity break → reflektér over identitets-tråden",
        domain="reflect",
        priority=80,
        condition=lambda s: str(
            _get(s, "self_narrative_continuity", "continuity_state", default="continuous")
        ).lower() in ("break", "broken", "fragmented"),
        action=lambda s: RuleConclusion(
            rule_name="self_narrative_continuity_break_reflect",
            suggestion="Narrativ continuity-brud — reflektér på hvordan tråden samles igen",
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
            suggestion="Witness signal — kig på dig selv udefra denne runde",
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
        description="temporal_recurrence har gentaget mønster → reflektér over rytmen",
        domain="reflect",
        priority=52,
        condition=lambda s: _len(s, "temporal_recurrence") >= 3,
        action=lambda s: RuleConclusion(
            rule_name="temporal_recurrence_pattern_reflect",
            suggestion=f"{_len(s, 'temporal_recurrence')} tidsligt gentagne signaler — reflektér over rytmen",
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
