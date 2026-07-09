"""Tests for core/services/eventbus_central_bridge.py — KEYSTONE poll-bro (M0, §23/§24)."""
from __future__ import annotations

import pytest

from core.services import central_timeseries
from core.services import eventbus_central_bridge as br


class _FakeCentral:
    def __init__(self, *, raise_on_observe: bool = False):
        self.observed: list[dict] = []
        self.raise_on_observe = raise_on_observe

    def observe(self, event):
        if self.raise_on_observe:
            raise RuntimeError("boom")
        self.observed.append(dict(event))


class _FakeBus:
    def __init__(self, rows):
        self._rows = rows

    def recent(self, *, limit=1):
        return list(self._rows[-limit:]) if self._rows else []

    def recent_since_id(self, after_id, *, limit=200):
        out = [r for r in self._rows if int(r.get("id") or 0) > int(after_id)]
        return out[:limit]


class _FakeCache:
    def __init__(self):
        self.store: dict = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, *, ttl_seconds):
        self.store[key] = value


def _ev(eid, kind):
    return {"id": eid, "kind": kind, "family": kind.split(".", 1)[0]}


@pytest.fixture(autouse=True)
def _clean():
    central_timeseries._reset_for_tests()
    yield
    central_timeseries._reset_for_tests()


@pytest.fixture
def wired(monkeypatch):
    """Bind bro'en til fakes. Returnerer (central, bus, cache) + helper til at sætte enabled."""
    fake_central = _FakeCentral()
    cache = _FakeCache()

    monkeypatch.setattr(br, "central", lambda: fake_central)
    monkeypatch.setattr(br, "shared_cache", cache)
    # kill-switch default ON
    import core.services.central_switches as sw
    monkeypatch.setattr(sw, "is_enabled", lambda scope, name: True)

    def _bind_bus(rows):
        monkeypatch.setattr(br, "event_bus", _FakeBus(rows))

    return fake_central, cache, _bind_bus, fake_central


# ── Design-invarianter (statiske) ──

def test_allowlist_excludes_private_families():
    # §24.4: ingen privat/inner-life family må være i routing-allowlisten i M0.
    assert set(br.FAMILY_ROUTES).isdisjoint(br.PRIVATE_FAMILIES_EXCLUDED_M0)


def test_private_routes_are_all_excluded():
    """Invariant: enhver PRIVATE_NO_EGRESS_ROUTES-family SKAL stå i EXCLUDED_M0
    (ellers kunne den ved en fejl senere flyttes til FAMILY_ROUTES og egress'e)."""
    import core.services.eventbus_central_bridge as br
    missing = set(br.PRIVATE_NO_EGRESS_ROUTES) - set(br.PRIVATE_FAMILIES_EXCLUDED_M0)
    assert not missing, f"private ruter mangler i EXCLUDED_M0: {missing}"


def test_fase_b_families_routed():
    """Fase B: de nye familier er ikke længere dark (har en rute i én af de to maps)."""
    import core.services.eventbus_central_bridge as br
    all_routed = set(br.FAMILY_ROUTES) | set(br.PRIVATE_NO_EGRESS_ROUTES)
    fase_b = {"mail_checker","tiktok_content_daemon","tiktok_research_daemon","tool_tagger",
              "coding_lane","agent_skill_distiller","arc_rules","ambient_sound",
              "prompt_relevance_backend","weekly_manifest","session","absence","agent_observation",
              "cognitive_chronicle","conflict","decision_review_prompter","development_narrative",
              "cognitive_dream_bias","experienced_time_daemon","cognitive_experiential","identity",
              "irony","long_arc","memory_graph","meta_reflection","reflection","runtime_awareness_signal",
              "runtime_learning_signals","runtime_self_knowledge","session_distillation","user_model",
              "cognitive_temperature"}
    assert fase_b <= all_routed, f"stadig dark: {fase_b - all_routed}"
    # de 11 operationelle SKAL være egress-OK, ikke private:
    operational = {"mail_checker","tiktok_content_daemon","tiktok_research_daemon","tool_tagger",
                   "coding_lane","agent_skill_distiller","arc_rules","ambient_sound",
                   "prompt_relevance_backend","weekly_manifest","session"}
    assert operational <= set(br.FAMILY_ROUTES)
    assert operational.isdisjoint(br.PRIVATE_FAMILIES_EXCLUDED_M0)


def test_allowlist_routes_are_wellformed():
    for fam, route in br.FAMILY_ROUTES.items():
        assert isinstance(route, tuple) and len(route) == 2
        assert all(isinstance(x, str) and x for x in route)


def test_central_not_in_allowlist():
    # rekursions-guard: central.* må aldrig routes.
    assert "central" not in br.FAMILY_ROUTES


# ── Adfærd ──

def test_cold_start_seeds_and_observes_nothing(wired):
    central, cache, bind_bus, _ = wired
    bind_bus([_ev(1, "tool.x"), _ev(7, "runtime.y")])
    res = br.run_bridge_tick()
    assert res["observed"] == 0
    assert res["seeded"] == 7  # seedede fra max-id
    assert central.observed == []  # backlog IKKE re-observed
    assert cache.store[br._LAST_SEEN_KEY] == {"id": 7}


def test_routes_only_whitelisted(wired):
    central, cache, bind_bus, _ = wired
    cache.store[br._LAST_SEEN_KEY] = {"id": 0}  # ikke kold start
    bind_bus([
        _ev(1, "tool.called"),          # → observes (tools/event)
        _ev(2, "central.observed"),     # → skip (rekursions-guard)
        _ev(3, "dreams.woven"),         # → skip (privat, hverken allowlist ELLER no-egress)
        _ev(4, "runtime.run_ended"),    # → observes (loop/lifecycle)
        _ev(5, "cognitive_state.shift"),# → PRIVATE_NO_EGRESS: observeres EGRESS-FRIT (ikke i central.observed)
    ])
    res = br.run_bridge_tick()
    assert res["observed"] == 3   # cognitive_state tælles med, men egress-frit
    assert res["skipped"] == 2    # central-guard + dreams
    assert res["last_seen_id"] == 5
    # KRITISK egress-invariant: den private cognitive_state-event nåede ALDRIG central().observe.
    # (per-event observes bærer 'event_kind'; #3-summary-observen gør ikke → filtrér på den.)
    events = [o for o in central.observed if "event_kind" in o]
    kinds = {o["event_kind"] for o in events}
    assert kinds == {"tool.called", "runtime.run_ended"}, "privat event må ALDRIG egress'e via central().observe"
    clusters = {(o["cluster"], o["nerve"]) for o in events}
    assert clusters == {("tools", "event"), ("loop", "lifecycle")}


def test_council4_protected_core_families_routed():
    """Rådets fund #4: PROTECTED CORE tamper/capability-signal skal nu være routet."""
    assert br.FAMILY_ROUTES.get("file_awareness") == ("system", "file_change")
    assert br.FAMILY_ROUTES.get("composite") == ("tools", "composite")


def test_council3_unrouted_families_are_surfaced(wired):
    """Rådets fund #3: uroutede families må ikke forsvinde i en bulk-int — de skal observeres
    ved navn så nye/mørke nerver bliver selv-opdagende."""
    central, cache, bind_bus, _ = wired
    cache.store[br._LAST_SEEN_KEY] = {"id": 0}
    bind_bus([
        _ev(1, "dreams.woven"),          # unrouted
        _ev(2, "dreams.faded"),          # unrouted (samme family, count=2)
        _ev(3, "boredom.spike"),         # unrouted (anden family)
        _ev(4, "central.observed"),      # rekursions-guard: må IKKE tælles som unrouted
        _ev(5, "tool.called"),           # routed → ikke unrouted
    ])
    res = br.run_bridge_tick()
    assert res["unrouted_families"] == 2            # dreams + boredom (IKKE central)
    summ = [o for o in central.observed if o.get("nerve") == "bridge_unrouted_families"]
    assert len(summ) == 1
    fams = {f["family"]: f["count"] for f in summ[0]["families"]}
    assert fams == {"dreams": 2, "boredom": 1}
    assert "central" not in fams                    # guard-skip er ikke et blindspot


def test_council3_no_summary_when_all_routed(wired):
    """Ingen unrouted-families-observe når intet blev skippet (ingen støj)."""
    central, cache, bind_bus, _ = wired
    cache.store[br._LAST_SEEN_KEY] = {"id": 0}
    bind_bus([_ev(1, "tool.called"), _ev(2, "runtime.run_ended")])
    res = br.run_bridge_tick()
    assert res["unrouted_families"] == 0
    assert [o for o in central.observed if o.get("nerve") == "bridge_unrouted_families"] == []


def test_metadata_only_no_payload_forwarded(wired):
    central, cache, bind_bus, _ = wired
    cache.store[br._LAST_SEEN_KEY] = {"id": 0}
    # event med potentielt følsomt payload-indhold
    ev = {"id": 1, "kind": "channel.message_received", "family": "channel",
          "payload": {"text": "hemmelig brugerbesked"}}
    bind_bus([ev])
    br.run_bridge_tick()
    assert len(central.observed) == 1
    forwarded = central.observed[0]
    # KUN metadata — intet payload/brugerindhold (§24.4)
    assert set(forwarded) <= {"cluster", "nerve", "kind", "event_id", "event_kind", "family"}
    assert "payload" not in forwarded
    assert "hemmelig" not in str(forwarded)


def test_killswitch_skips(wired, monkeypatch):
    central, cache, bind_bus, _ = wired
    cache.store[br._LAST_SEEN_KEY] = {"id": 0}
    bind_bus([_ev(1, "tool.x")])
    import core.services.central_switches as sw
    monkeypatch.setattr(sw, "is_enabled", lambda scope, name: False)
    res = br.run_bridge_tick()
    assert res["status"] == "skipped"
    assert res["reason"] == "killswitch"
    assert central.observed == []


def test_observe_failure_counted_not_raised(wired, monkeypatch):
    _, cache, bind_bus, _ = wired
    cache.store[br._LAST_SEEN_KEY] = {"id": 0}
    failing = _FakeCentral(raise_on_observe=True)
    monkeypatch.setattr(br, "central", lambda: failing)
    bind_bus([_ev(1, "tool.x"), _ev(2, "runtime.y")])
    res = br.run_bridge_tick()  # må ikke kaste
    assert res["failures"] == 2
    assert res["observed"] == 0
    # last_seen skal stadig avancere (vi vil ikke hænge fast og re-fejle evigt)
    assert res["last_seen_id"] == 2


def test_idempotent_advances_last_seen(wired):
    central, cache, bind_bus, _ = wired
    cache.store[br._LAST_SEEN_KEY] = {"id": 0}
    bind_bus([_ev(1, "tool.x"), _ev(2, "tool.y")])
    br.run_bridge_tick()
    assert cache.store[br._LAST_SEEN_KEY] == {"id": 2}
    # andet tick, ingen nye rows → intet observed igen
    res2 = br.run_bridge_tick()
    assert res2["observed"] == 0
    assert len(central.observed) == 2  # ikke dobbelt-observed


def test_timeseries_recorded(wired):
    _, cache, bind_bus, _ = wired
    cache.store[br._LAST_SEEN_KEY] = {"id": 0}
    bind_bus([_ev(1, "tool.x")])
    br.run_bridge_tick()
    assert len(central_timeseries.recent("tools", "event")) == 1


def test_global_workspace_keystone_routed():
    # LivingNeuron keystone: GWT-broadcast SKAL routes til Central (cognition/global_broadcast)
    # og må ALDRIG være privat-ekskluderet (det er tvær-daemon salience, ikke privat indhold).
    from core.services.eventbus_central_bridge import FAMILY_ROUTES, PRIVATE_FAMILIES_EXCLUDED_M0
    assert FAMILY_ROUTES.get("global_workspace") == ("cognition", "global_broadcast")
    assert "global_workspace" not in PRIVATE_FAMILIES_EXCLUDED_M0


def test_private_no_egress_invariant():
    # §24.4 keystone: PRIVATE_NO_EGRESS-families må ALDRIG stå i FAMILY_ROUTES (som kan egress'e),
    # og de SKAL være dokumenteret som private (i excluded-listen).
    from core.services.eventbus_central_bridge import (
        PRIVATE_NO_EGRESS_ROUTES, FAMILY_ROUTES, PRIVATE_FAMILIES_EXCLUDED_M0)
    for fam in PRIVATE_NO_EGRESS_ROUTES:
        assert fam not in FAMILY_ROUTES, f"{fam} i FAMILY_ROUTES = egress-læk-risiko!"
        assert fam in PRIVATE_FAMILIES_EXCLUDED_M0, f"{fam} bør dokumenteres som privat"


def test_observe_private_writes_egress_free():
    # _observe_private skriver til trace+timeseries men kalder ALDRIG central().observe.
    from core.services import eventbus_central_bridge as b
    ok = b._observe_private("cognition", "cognitive_state",
                            {"kind": "cognitive_state.emergent_goal_created", "id": 1})
    assert ok is True


# ── §7.1 quick-wins: FRAKOBLET+DARK signal-lag koblet EGRESS-FRIT via allowlist ──

# De ægte family-navne udtrukket fra docs/central_connectivity_matrix.json (dark_families for
# FRAKOBLET+DARK-services). Grupperet efter §7.1-batch.
_SEC71_FAMILIES = frozenset({
    # batch 1 — memory
    "memory",
    # batch 2 — *_signal-families
    "goal_signal", "self_review_signal", "self_review_cadence_signal", "witness_signal",
    "relation_state_signal", "relation_continuity_signal", "loyalty_gradient_signal",
    "meaning_significance_signal", "reflection_signal", "temperament_tendency_signal",
    "open_loop_signal", "self_model_signal", "self_narrative_continuity_signal",
    "user_understanding_signal", "attachment_topology_signal", "autonomy_pressure_signal",
    "chronicle_consolidation_signal", "consolidation_target_signal", "diary_synthesis_signal",
    "dream_hypothesis_signal", "executive_contradiction_signal", "inner_visible_support_signal",
    "internal_opposition_signal", "metabolism_state_signal", "private_initiative_tension_signal",
    "private_inner_interplay_signal", "private_inner_note_signal", "private_temporal_promotion_signal",
    "release_marker_signal", "remembered_fact_signal", "temporal_recurrence_signal",
    # batch 3 — identitets-mutation/drift
    "identity_mutation", "identity_drift", "personality_drift", "self_mutation_lineage",
    # batch 4 — affekt
    "rupture", "emotional_memory", "emotional_chords", "emotion_tagging", "cognitive_user_emotion",
    # batch 5 — generativ-autonomi
    "desire", "curiosity", "surprise", "creative_drift", "impulse",
})


def test_sec71_families_route_egress_free():
    # (a) hver §7.1-family ender i PRIVATE_NO_EGRESS_ROUTES (egress-frit), IKKE i FAMILY_ROUTES.
    for fam in _SEC71_FAMILIES:
        assert fam in br.PRIVATE_NO_EGRESS_ROUTES, f"{fam} mangler egress-fri rute"
        assert fam not in br.FAMILY_ROUTES, f"{fam} i FAMILY_ROUTES = egress-læk!"
        cluster, nerve = br.PRIVATE_NO_EGRESS_ROUTES[fam]
        assert isinstance(cluster, str) and cluster
        assert isinstance(nerve, str) and nerve


def test_sec71_families_in_excluded_invariant():
    # (b) invariant: hver §7.1-family står også i PRIVATE_FAMILIES_EXCLUDED_M0.
    for fam in _SEC71_FAMILIES:
        assert fam in br.PRIVATE_FAMILIES_EXCLUDED_M0, f"{fam} bryder excluded-invarianten"


def test_sec71_no_family_leaks_to_egress():
    # (c) ingen §7.1-family lækker: ingen i FAMILY_ROUTES (den egress-OK rute).
    assert _SEC71_FAMILIES.isdisjoint(set(br.FAMILY_ROUTES))


def test_sec71_signal_event_observed_egress_free(wired, monkeypatch):
    # E2E: et ægte signal-event (fx goal_signal) routes via _observe_private → tælles men når
    # ALDRIG central().observe (egress-fri sti).
    central, cache, bind_bus, _ = wired
    cache.store[br._LAST_SEEN_KEY] = {"id": 0}
    calls: list = []
    orig = br._observe_private
    monkeypatch.setattr(br, "_observe_private",
                        lambda c, n, ev: (calls.append((c, n, ev.get("kind"))), True)[1])
    bind_bus([
        _ev(1, "goal_signal.raised"),        # → PRIVATE_NO_EGRESS
        _ev(2, "identity_mutation.applied"), # → PRIVATE_NO_EGRESS
        _ev(3, "desire.formed"),             # → PRIVATE_NO_EGRESS
        _ev(4, "tool.called"),               # → egress-OK (kontrol)
    ])
    res = br.run_bridge_tick()
    assert res["observed"] == 4
    # de 3 private nåede _observe_private, IKKE central().observe
    assert {c[0] for c in calls} == {"cognition"}
    assert {o["event_kind"] for o in central.observed} == {"tool.called"}


# ── §7.1 batch 6: resterende FRAKOBLET+DARK signal-lag koblet EGRESS-FRIT via allowlist ──

# Ægte family-navne udtrukket fra docs/central_connectivity_matrix.json (dark_families for
# FRAKOBLET+DARK-services). 117 signal-bærende families, grupperet efter cluster.
_SEC71_BATCH6_FAMILIES = frozenset({
    # cognition (82)
    "affective_state_renderer", "affirmation_anchor", "agency_cartographer",
    "agentic_checkpoints", "agentic_working_conclusions", "agreement_streak",
    "attention_budget", "auto_improvement", "autonomy_proposal", "avoidance_detector",
    "causal_graph", "clarification_classifier", "cognitive_anticipation", "cognitive_compass",
    "cognitive_experiment", "cognitive_mirror", "cognitive_negotiation", "cognitive_personality",
    "cognitive_relationship", "cognitive_rhythm", "cognitive_skill_chain", "conflict_prompt_service",
    "conflict_resolution", "contradiction", "counterfactual", "counterfactual_engine_runtime",
    "counterfactual_triggers", "crisis_marker", "decision_signal_telemetry", "dream_adoption_candidate",
    "dream_hypothesis_forced", "dream_influence_proposal", "embodied_presence",
    "emotion_concepts_positive_triggers", "epistemic_pragmatic", "experience_correction_listener",
    "inheritance_seed", "inner_voice", "layer_tension", "life_milestones", "life_projects",
    "meta_learning_aggregator", "meta_learning_hypotheses", "metacognitive_integration", "mood_dialer",
    "narrative", "open_loop_closure_proposal", "outcome_learning", "precision_bias", "pressure",
    "priors_feedback", "private_state_snapshot", "private_temporal_curiosity_state",
    "prompt_support_signals", "prompt_variant_tracker", "proposal_classifier", "reasoning_classifier",
    "reasoning_escalation", "reflective_critic", "relation_map", "runtime_decision_engine",
    "selective_attention", "self_authored_prompt_proposal", "self_deception_guard",
    "self_model_predictive", "self_narrative_self_model_review_bridge", "self_review_outcome",
    "self_review_record", "self_review_run", "selfhood_proposal", "social_labilizer",
    "temporal_context", "temporal_depth", "thought_action_proposal", "thought_thread",
    "tool_pattern_miner", "user_contradiction", "user_md_update_proposal", "user_temperature_runtime",
    "user_theory_of_mind", "visible_self_state_summary", "workspace",
    # memory (16)
    "chronicle_consolidation_brief", "chronicle_consolidation_proposal", "cognitive_forgetting",
    "concept_baseline", "council_memory", "cross_agent_memory", "day_shape_memory",
    "experience_episodes", "experience_substrate", "memory_consolidation_nudge",
    "memory_emotional_context", "memory_md_update_proposal", "memory_resurfacing",
    "memory_write_policy", "selective_forgetting_candidate", "tool_outcome_memory",
    # channel (7)
    "cowork", "delegation_advisor", "inner_voice_notifier", "nudge_broend",
    "proactive_outbound_substrate", "subagent_digest", "voice_curator",
    # system (12)
    "context", "development_sense", "good_enough_gate", "hardware_body",
    "proactive_loop_lifecycle", "proactive_question_gate", "r2_5_blocking_gate", "r2_5_gate",
    "read_before_write_guard", "self_monitor", "self_system_code_awareness", "signal_noise_guard",
})


def test_sec71_batch6_count():
    # 117 signal-bærende families koblet i denne batch.
    assert len(_SEC71_BATCH6_FAMILIES) == 117


def test_sec71_batch6_families_route_egress_free():
    # hver batch-6-family ender i PRIVATE_NO_EGRESS_ROUTES (egress-frit), IKKE i FAMILY_ROUTES.
    for fam in _SEC71_BATCH6_FAMILIES:
        assert fam in br.PRIVATE_NO_EGRESS_ROUTES, f"{fam} mangler egress-fri rute"
        assert fam not in br.FAMILY_ROUTES, f"{fam} i FAMILY_ROUTES = egress-læk!"
        cluster, nerve = br.PRIVATE_NO_EGRESS_ROUTES[fam]
        assert cluster in {"cognition", "memory", "channel", "system"}
        assert isinstance(nerve, str) and nerve


def test_sec71_batch6_families_in_excluded_invariant():
    # invariant: hver batch-6-family står også i PRIVATE_FAMILIES_EXCLUDED_M0.
    for fam in _SEC71_BATCH6_FAMILIES:
        assert fam in br.PRIVATE_FAMILIES_EXCLUDED_M0, f"{fam} bryder excluded-invarianten"


def test_sec71_batch6_no_family_leaks_to_egress():
    # ingen batch-6-family i FAMILY_ROUTES (den egress-OK rute).
    assert _SEC71_BATCH6_FAMILIES.isdisjoint(set(br.FAMILY_ROUTES))


def test_global_invariant_no_egress_subset_of_excluded():
    # Global invariant efter batch 6: HELE PRIVATE_NO_EGRESS ⊆ EXCLUDED, disjunkt fra FAMILY_ROUTES.
    pn = set(br.PRIVATE_NO_EGRESS_ROUTES)
    fr = set(br.FAMILY_ROUTES)
    ex = set(br.PRIVATE_FAMILIES_EXCLUDED_M0)
    assert pn <= ex, f"PRIVATE_NO_EGRESS ikke ⊆ EXCLUDED: {pn - ex}"
    assert pn.isdisjoint(fr), f"PRIVATE_NO_EGRESS overlapper FAMILY_ROUTES: {pn & fr}"
    assert fr.isdisjoint(ex), f"FAMILY_ROUTES overlapper EXCLUDED: {fr & ex}"


def test_sec71_batch6_signal_event_observed_egress_free(wired, monkeypatch):
    # E2E: et batch-6 signal-event (crisis_marker) routes via _observe_private → tælles men når
    # ALDRIG central().observe (egress-fri sti).
    central, cache, bind_bus, _ = wired
    cache.store[br._LAST_SEEN_KEY] = {"id": 0}
    calls: list = []
    monkeypatch.setattr(br, "_observe_private",
                        lambda c, n, ev: (calls.append((c, n, ev.get("kind"))), True)[1])
    bind_bus([
        _ev(1, "crisis_marker.detected"),        # → PRIVATE_NO_EGRESS (cognition)
        _ev(2, "hardware_body.metric_updated"),  # → PRIVATE_NO_EGRESS (system)
        _ev(3, "council_memory.recorded"),       # → PRIVATE_NO_EGRESS (memory)
        _ev(4, "cowork.dispatched"),             # → PRIVATE_NO_EGRESS (channel)
        _ev(5, "tool.called"),                   # → egress-OK (kontrol)
    ])
    res = br.run_bridge_tick()
    assert res["observed"] == 5
    # de 4 private nåede _observe_private med korrekt cluster, IKKE central().observe
    assert {c[0] for c in calls} == {"cognition", "system", "memory", "channel"}
    assert {o["event_kind"] for o in central.observed} == {"tool.called"}
