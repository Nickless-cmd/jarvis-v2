"""Daemon Manager — registry, lifecycle control, and state persistence for all daemons.

Single source of truth for daemon enabled/disabled state, interval overrides,
and last-run tracking. Heartbeat runtime checks is_enabled() before each daemon call
and calls record_daemon_tick() after.

State persisted to DAEMON_STATE.json in the runtime workspace.
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.workspace_paths import shared_dir


def _state_file() -> Path:
    return shared_dir() / "runtime" / "DAEMON_STATE.json"

# Registry: daemon name → module path, state var to reset on restart, default cadence.
_REGISTRY: dict[str, dict[str, Any]] = {
    "somatic": {
        "module": "core.services.somatic_daemon",
        "reset_var": "_heartbeat_count_since_gen",
        "reset_value": 999,
        "default_cadence_minutes": 3,
        "description": "LLM-generated first-person body/energy description",
    },
    "surprise": {
        "module": "core.services.surprise_daemon",
        "reset_var": "_heartbeats_since_surprise",
        "reset_value": 999,
        "default_cadence_minutes": 4,
        "default_enabled": False,  # PENSIONERET 2026-07-15 — cluster_affect overtager (samme generering, én familie-gate)
        "retired": "2026-07-15",
        "description": "[PENSIONERET → cluster_affect] Detects divergence from baseline reaction patterns",
    },
    "aesthetic_taste": {
        "module": "core.services.aesthetic_taste_daemon",
        "reset_var": "_last_insight_at",
        "reset_value": None,
        "default_cadence_minutes": 7,
        "description": "Tracks style preferences and aesthetic tendencies",
    },
    "irony": {
        "module": "core.services.irony_daemon",
        "reset_var": "_observations_today",
        "reset_value": 0,
        "default_cadence_minutes": 30,
        "default_enabled": False,  # PENSIONERET 2026-07-15 — cluster_innervoice overtager (samme generering, én familie-gate)
        "retired": "2026-07-15",
        "description": "[PENSIONERET → cluster_innervoice] Generates situational self-distance observations (max 1/day)",
    },
    "thought_stream": {
        "module": "core.services.thought_stream_daemon",
        "reset_var": "_last_fragment_at",
        "reset_value": None,
        "default_cadence_minutes": 2,
        "default_enabled": False,  # PENSIONERET 2026-07-15 — cluster_innervoice overtager (samme generering, én familie-gate)
        "retired": "2026-07-15",
        "description": "[PENSIONERET → cluster_innervoice] Generates associative thought fragments",
    },
    "thought_action_proposal": {
        "module": "core.services.thought_action_proposal_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 5,
        "description": "Converts thought fragments into action proposals",
    },
    "conflict": {
        "module": "core.services.conflict_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 8,
        "default_enabled": False,  # PENSIONERET 2026-07-15 — cluster_affect overtager (samme generering, én familie-gate)
        "retired": "2026-07-15",
        "description": "[PENSIONERET → cluster_affect] Detects inner tensions between active states",
    },
    "reflection_cycle": {
        "module": "core.services.reflection_cycle_daemon",
        "reset_var": "_last_reflection_at",
        "reset_value": None,
        "default_cadence_minutes": 10,
        "default_enabled": False,  # PENSIONERET 2026-07-15 — cluster_innervoice overtager (samme generering, én familie-gate)
        "retired": "2026-07-15",
        "description": "[PENSIONERET → cluster_innervoice] Pure experiential awareness — non-instrumental reflection",
    },
    "memory_safeguard": {
        "module": "core.services.daemon_memory_safeguard",
        "reset_var": "_last_nudge_at",
        "reset_value": None,
        "default_cadence_minutes": 15,
        "description": "Post-hoc check for missed memory consolidation — nudges if learning markers found without save calls",
    },
    "curiosity": {
        "module": "core.services.curiosity_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 5,
        "description": "Scans thought stream for gaps and generates curiosity signals",
    },
    "meta_reflection": {
        "module": "core.services.meta_reflection_daemon",
        "reset_var": "_last_meta_at",
        "reset_value": None,
        "default_cadence_minutes": 30,
        "default_enabled": False,  # PENSIONERET 2026-07-15 — cluster_innervoice overtager (insight+credit-assignment i familien)
        "retired": "2026-07-15",
        "description": "[PENSIONERET → cluster_innervoice] Cross-signal pattern synthesis and meta-insights",
    },
    "experienced_time": {
        "module": "core.services.experienced_time_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 5,
        "description": "Density-based felt duration — how time feels vs. clock time",
    },
    "development_narrative": {
        "module": "core.services.development_narrative_daemon",
        "reset_var": "_last_narrative_at",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "default_enabled": False,  # PENSIONERET 2026-07-15 — cluster_narrative overtager (samme daglige generering; medlem self-throttler 24t)
        "retired": "2026-07-15",
        "description": "[PENSIONERET → cluster_narrative] Daily LLM-generated self-reflection on development",
    },
    "absence": {
        "module": "core.services.absence_daemon",
        "reset_var": "_last_generated_at",
        "reset_value": None,
        "default_cadence_minutes": 15,
        "description": "Three-tier tracking of experiential absence quality",
    },
    "creative_drift": {
        "module": "core.services.creative_drift_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 30,
        "default_enabled": False,  # PENSIONERET 2026-07-15 — cluster_innervoice overtager (samme generering, én familie-gate)
        "retired": "2026-07-15",
        "description": "[PENSIONERET → cluster_innervoice] Spontaneous unexpected associations and ideas",
    },
    "existential_wonder": {
        "module": "core.services.existential_wonder_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "default_enabled": False,  # PENSIONERET 2026-07-15 — cluster_innervoice overtager; _latest_wonder-output BEVARET (convene_judge/proactivity_bridge/visible_inner_life)
        "retired": "2026-07-15",
        "description": "[PENSIONERET → cluster_innervoice] Self-generated philosophical questions from self-observation",
    },
    "dream_insight": {
        "module": "core.services.dream_insight_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 30,
        "description": "Persists dream articulation output as private brain records",
    },
    "code_aesthetic": {
        "module": "core.services.code_aesthetic_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 10080,
        "default_enabled": False,  # PENSIONERET 2026-07-13 (Fase 7) — blind ugentlig LLM-refleksion nedlagt
        "retired": "2026-07-13",
        "description": "[PENSIONERET] Weekly codebase aesthetic reflection (7 days)",
    },
    "memory_decay": {
        "module": "core.services.memory_decay_daemon",
        "reset_var": "_last_decay_at",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "description": "Selective forgetting + re-discovery of signals",
    },
    "memory_pruning": {
        "module": "core.services.memory_pruning_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 360,
        "description": "6t arkivering af entries med salience < 0.05 — learning to forget",
    },
    "identity_drift": {
        "module": "core.services.identity_drift_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "default_enabled": False,  # PENSIONERET 2026-07-15 — cluster_narrative overtager (medlem self-throttler 24t; snapshot-output BEVARET). Var orphan (ingen tick-site før) → familien giver den nu en live tick.
        "retired": "2026-07-15",
        "description": "[PENSIONERET → cluster_narrative] 24t identity-drift detektor — sammenligner SOUL/IDENTITY/USER/STANDING_ORDERS mod sidste snapshot, fyrer identity.drift_detected ved uautoriserede ændringer",
    },
    "causal_inference": {
        "module": "core.services.causal_inference_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 15,
        "description": "15min causal-graph inference (three-tier matching) — populates causal_edges from events allowlist, emits causal.inference_stats",
    },
    "narrative_summary": {
        "module": "core.services.narrative_summary_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 15,
        "default_enabled": False,  # PENSIONERET 2026-07-15 — cluster_narrative overtager (medlem self-throttler 15min; narrative.summary-output BEVARET)
        "retired": "2026-07-15",
        "description": "[PENSIONERET → cluster_narrative] Phase 2.5 of causal graph — every 15 min, asks cheap LLM to summarise the most recent backward causal chain into a 1-2 sentence Danish narrative; persists as narrative.summary event",
    },
    "pattern_counterfactual": {
        "module": "core.services.pattern_counterfactual_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 60,
        "description": "Phase 3.5 of causal graph — hourly, takes top 3 recurring patterns and asks cheap LLM 'what would change if this stopped?'; persists as counterfactual.pattern_what_if events (24h dedupe per pattern)",
    },
    "memory_maintenance": {
        "module": "core.services.memory_maintenance_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 720,
        "description": "Periodic MEMORY.md dedup: Tier A auto-merge duplicates, Tier B flag overlaps",
    },
    "longing_signal": {
        "module": "core.services.longing_signal_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 10,
        "default_enabled": False,  # PENSIONERET 2026-07-15 — cluster_affect overtager (non-LLM member; kører ubetinget hver familie-tick); action_router-kaldet er is_enabled-gatet → no-op
        "retired": "2026-07-15",
        "description": "[PENSIONERET → cluster_affect] Generative autonomy Spor-1: longing-toward-user pressure signal (gated by generative_autonomy_enabled)",
    },
    "user_model": {
        "module": "core.services.user_model_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 10,
        "description": "Theory of mind — models user preferences and patterns",
    },
    "desire": {
        "module": "core.services.desire_daemon",
        "reset_var": "_last_generated_at",
        "reset_value": None,
        "default_cadence_minutes": 8,
        "default_enabled": False,  # PENSIONERET 2026-07-15 — cluster_affect overtager (samme generering, én familie-gate)
        "retired": "2026-07-15",
        "description": "[PENSIONERET → cluster_affect] Emergent appetites with intensity-based lifecycle",
    },
    "autonomous_council": {
        "module": "core.services.autonomous_council_daemon",
        "reset_var": "_last_council_at",
        "reset_value": None,
        "default_cadence_minutes": 30,
        "default_enabled": False,  # PENSIONERET 2026-07-13 (Lag 6) — convene_judge overtager; motor (convene_council + council_deliberation_controller) bevaret
        "retired": "2026-07-13",
        "description": "[PENSIONERET] Spontaneous self-triggered council deliberation via signal scoring",
    },
    "council_memory": {
        "module": "core.services.council_memory_daemon",
        "reset_var": "_last_llm_call_at",
        "reset_value": None,
        "default_cadence_minutes": 10,
        "description": "Injects relevant past council conclusions into heartbeat context",
    },
    "signal_decay": {
        "module": "core.services.signal_decay_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 60,
        "description": "Archives and deletes stale signals older than 24h across all signal tables",
    },
    "cache_maintenance": {
        "module": "core.services.cache_maintenance_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 360,
        "default_enabled": True,
        "description": "6t cleanup af web_cache: sletter udløbne entries (web_search + web_scrape), logger cache-sammensætning",
    },
    "tiktok_content": {
        "module": "core.services.tiktok_content_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 480,
        "default_enabled": False,  # PENSIONERET 2026-07-10 (Bjørn) — kode+registrering bevaret, kører ikke
        "retired": "2026-07-10",
        "description": "[PENSIONERET] Autonomous TikTok content: 3 videos/day (jarvis_work, facts, agi_journey)",
    },
    "tiktok_research": {
        "module": "core.services.tiktok_research_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "default_enabled": False,  # PENSIONERET 2026-07-10 (Bjørn) — kode+registrering bevaret, kører ikke
        "retired": "2026-07-10",
        "description": "[PENSIONERET] Daily content research: generates TikTok concept pool for 3 slot types",
    },
    "emotion_repair_bridge": {
        "module": "core.services.emotion_repair_bridge_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 5,
        "default_enabled": False,  # PENSIONERET 2026-07-15 — cluster_affect overtager (non-LLM member; kører ubetinget hver familie-tick; egen cadence-gate)
        "retired": "2026-07-15",
        "description": "[PENSIONERET → cluster_affect] Emotion→Selvreparation + Selvreparation→Sanser: mapter frustration/doubt/skam til repair patterns og bridge outcome til emotional memory",
    },
    "mail_checker": {
        "module": "core.services.mail_checker_daemon",
        "reset_var": "_last_check_at",
        "reset_value": None,
        "default_cadence_minutes": 15,
        "description": "Checks jarvis@srvlab.dk inbox for new emails and notifies via eventbus",
    },
    "current_pull": {
        "module": "core.services.current_pull",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 10080,
        "default_enabled": False,  # PENSIONERET 2026-07-13 (Fase 7) — blind ugentlig LLM-pull nedlagt
        "retired": "2026-07-13",
        "description": "[PENSIONERET] Lag 5: weekly self-set desire field — what pulls at Jarvis right now",
    },
    "visual_memory": {
        "module": "core.services.visual_memory",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 360,
        "description": "Lag 6: webcam snapshot + vision model room description (4x/day)",
    },
    "task_worker": {
        "module": "core.services.task_worker",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 2,
        "description": "Consumes queued runtime_tasks (initiative/heartbeat/open-loop followups, generic)",
    },
    "life_projects_reassessment": {
        "module": "core.services.life_projects",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "description": "24t re-vurdering af aktive life projects (long_term_intentions)",
    },
    "relation_map_refresh": {
        "module": "core.services.relation_map",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 720,
        "description": "12t opdatering af relation map: last_seen for primary, tom stale-check for secondary",
    },
    "consolidation_judge": {
        "module": "core.services.consolidation_judge_daemon",
        "reset_var": "_last_judgment_at",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "default_enabled": False,  # PENSIONERET 2026-07-15 — cluster_narrative overtager (medlem self-throttler 24t)
        "retired": "2026-07-15",
        "description": "[PENSIONERET → cluster_narrative] Natlig revision: samler dagens data og tvinger stillingtagen til 3-5 konkrete valg (accept/reject/defer)",
    },
    "memory_safeguard": {
        "module": "core.services.daemon_memory_safeguard",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 15,
        "description": "Daemon-sikkerhedsnet: tjekker om seneste tur indeholdt læringsmarkører uden save-tool kald",
    },
    "my_projects_watchdog": {
        "module": "core.services.my_projects",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 240,
        "default_enabled": True,
        "description": "240min checker: genstarter grid-bot, dealwork-worker, superteam-scanner og toku-poller hvis de er døde",
    },
    "active_sensing": {
        "module": "core.services.active_sensing_daemon",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 30,
        "default_enabled": True,
        "description": "Aktiv sansetrang: Sansernes Arkiv vælger selv at sanse (visual/audio/atmosphere/mixed) på eget initiativ",
    },
    "ground_truth_registry": {
        "module": "core.services.ground_truth_registry",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 60,
        "default_enabled": True,
        "description": "Lag 3 (Lying Engine): 60min refresh af Ground Truth Registry — system_model, host, expression_count, commit_count, daemon_count",
    },
    "associative_recall": {
        "module": "core.services.associative_recall",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 2,
        "default_enabled": True,
        "description": "Associativ hukommelse: dormant memories trigged by context — queries experiential + private brain + sensory DBs, scores candidates, maintains persistent active memories",
    },
    "wakeup_cleanup": {
        "module": "core.services.self_wakeup",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 60,
        "default_enabled": True,
        "description": "A3: ryd consumed/cancelled/stale-fired wakeups ældre end hhv 7/7/24 dage — forhindrer wakeup-bloat",
    },
    "memory_write_queue": {
        "module": "core.services.memory_write_queue",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 2,
        "default_enabled": True,
        "description": "B5: async write queue — processes deferred sensory/brain/sidecar writes every 120s for non-blocking memory writes",
    },
    "selective_consolidation": {
        "module": "core.services.selective_consolidation_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "default_enabled": True,
        "description": "D1: daily selective consolidation — archives bottom (100-K)% af dagens sensory/brain/private records; kun top-K% når long-term",
    },
    "cost_optimization": {
        "module": "core.services.cost_optimization_daemon",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 60,
        "default_enabled": True,
        "description": "D5: cost optimization — monitors daily/weekly LLM spend against budget, emits alerts at 80%+ utilization",
    },
    "identity_sketch": {
        "module": "core.services.identity_sketch",
        "reset_var": None,
        "reset_value": None,
        "default_cadence_minutes": 360,
        "default_enabled": False,  # PENSIONERET 2026-07-15 — cluster_narrative overtager (medlem self-throttler 6h staleness; identity_sketch.json-output BEVARET)
        "retired": "2026-07-15",
        "description": "[PENSIONERET → cluster_narrative] Memory Phase 2: refresh identity sketch every 6h (auto trigger). Skips if fresh; regenerates from live signals if stale.",
    },
    "communication_guard": {
        "module": "core.services.communication_guard_daemon",
        "reset_var": "_unused_reset_marker",
        "reset_value": None,
        "default_cadence_minutes": 60,
        "default_enabled": True,
        "description": "60min cleanup af udløbne TTL-triggers i communication guard (godnat-fraser etc.)",
    },
    "file_awareness": {
        "module": "core.services.file_awareness_daemon",
        "reset_var": None,
        "reset_value": None,
        "default_cadence_minutes": 5,
        "description": "Somatisk fil-awareness: mærk når nogen piller i mine filer live",
    },
    "decision_review": {
        "module": "core.services.decision_review_daemon",
        "reset_var": None,
        "reset_value": None,
        "default_cadence_minutes": 360,
        # 2026-06-11 (Bjørn frustration crisis fix C1): DEAKTIVERET.
        # Daemonen lod Jarvis selv-bedømme om han holdt sine egne
        # behavioral_decisions. Resultat: konsekvent "kept"-verdict
        # med tynd evidens, der gav ham 1.0 adherence_score på
        # decision #3 ("Verify before I narrate") — samtidig med at
        # han hallucinerede tool-work i Discord, JarvisX og webchat.
        # Positiv-bias self-validation feedback loop.
        # Skal erstattes af external-truth review (læser git-log +
        # tool-history) i fix C3.
        "default_enabled": False,
        "description": "[DEAKTIVERET 2026-06-11 — selv-bias problem] 6t adherence-loop: LLM-self-review af behavioral decisions.",
    },
    "event_trigger_shadow": {
        "module": "core.services.event_trigger_shadow",
        "reset_var": "_last_tick_at",
        "reset_value": None,
        "default_cadence_minutes": 3,
        # C5 θ-kalibrerings-meter. Rå, NON-LLM signal-delta-tjek. Var før placeret INDE i
        # _build_influence_trace (aktivitets-gated) → tikkede kun når Jarvis var aktiv, tavs
        # hele natten. Flyttet 2026-07-14 til den ubetingede daemon-sektion (% 6 ≈ 3 min ved
        # 30s-scheduler) → 500-ring dækker ~25t = ét fuldt 24t θ-vindue uanset idle.
        "description": "event-trigger SHADOW-meter (observe-only): registrerer hvad den event-drevne trigger VILLE dispatche, til θ-kalibrering. Fyrer aldrig LLM/råd.",
    },
    "provider_autodiscovery": {
        "module": "core.services.provider_autodiscovery",
        "reset_var": "_last_discovery_at",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        # Governed (spec §5.5 Fase C): stager kun nye modeller i pending_models — promotion
        # til routbar pool er MANUEL (smoke + gratis + score-gate). Default OFF; owner tænder.
        "default_enabled": False,
        "description": "Fase C: dagligt /models-scan af alle providers → nye modeller til pending_models-staging (ALDRIG auto-routbar; promotion manuel/gated)",
    },
    "provider_self_heal": {
        "module": "core.services.provider_self_heal",
        "reset_var": "_last_heal_at",
        "reset_value": None,
        "default_cadence_minutes": 60,
        # Sikkert at auto-køre (spec §5.5 Fase C): eskalerer kun (3+ providers nede → Discord)
        # og fjerner 404-modeller reaktivt (de-eskalering). Ingen addition. Default ON.
        "default_enabled": True,
        "description": "Fase C: 60min self-heal — 3+ providers nede samtidig → eskalér til Bjørn (Discord); model-drift (404) fjernes reaktivt",
    },
    "cluster_somatic": {
        "module": "core.services.cluster_daemon",
        "reset_var": "_SOMATIC_FAMILY",
        "reset_value": None,
        "default_cadence_minutes": 3,
        "default_enabled": True,
        # Cluster-daemon-konsolidering (spec 2026-07-14), FAMILIE #1:
        # somatic + experienced_time + absence under ÉN event-gate. Kører i
        # SHADOW/parallel (cluster_daemon_shadow-flag, default True): observerer
        # kun hvad familien VILLE producere og rapporterer til Centralen med
        # cluster_shadow-markør til parity-sammenligning. AFMONTERER IKKE de 3
        # gamle daemons — prove-then-retire, retire er gated på parity-data.
        "description": "[SHADOW] cluster-daemon FAMILIE #1 (somatic/embodiment): somatic+experienced_time+absence under én event-gate; observe-only parity mod de 3 gamle daemons (aldrig begge live).",
    },
    "cluster_innervoice": {
        "module": "core.services.cluster_daemon",
        "reset_var": "_INNERVOICE_FAMILY",
        "reset_value": None,
        "default_cadence_minutes": 2,
        "default_enabled": True,
        # Cluster-daemon-konsolidering (spec 2026-07-14), FAMILIE #2 (inner-voice):
        # thought_stream + reflection_cycle + meta_reflection + irony +
        # existential_wonder + creative_drift foldet ind i ÉN Central-styret
        # familie under ÉN event-gate. Kører LIVE (prove-then-retire END STATE) —
        # de 6 gamle daemons er PENSIONERET (default_enabled=False, retired
        # 2026-07-15). Hvert member kalder den gamle daemons generering
        # (skip_event_gate=True) så alle outputs bevares — især
        # existential_wonder._latest_wonder (load-bearing for convene_judge,
        # proactivity_bridge, visible_inner_life). Aldrig begge live.
        "description": "cluster-daemon FAMILIE #2 (inner-voice) LIVE: thought_stream+reflection_cycle+meta_reflection+irony+existential_wonder+creative_drift under ÉN event-gate; erstatter de 6 pensionerede daemons; bevarer alle outputs (incl. latest_wonder).",
    },
    "cluster_affect": {
        "module": "core.services.cluster_daemon",
        "reset_var": "_AFFECT_FAMILY",
        "reset_value": None,
        "default_cadence_minutes": 4,
        "default_enabled": True,
        # Cluster-daemon-konsolidering (spec 2026-07-14), FAMILIE #3 (affect):
        # surprise + conflict + desire + longing_signal + emotion_repair_bridge
        # foldet ind i ÉN Central-styret familie. Kører LIVE (prove-then-retire
        # END STATE) — de 5 gamle daemons er PENSIONERET (default_enabled=False,
        # retired 2026-07-15). To tiers: de 3 LLM-medlemmer (surprise/conflict/
        # desire) bag ÉN event-gate (skip_event_gate=True i deres tick); de 2
        # non-LLM-medlemmer (longing_signal, emotion_repair_bridge) kører
        # UBETINGET hver tick (egen cadence/killswitch). Bevarer alle outputs —
        # surprise/conflict-cachen er load-bearing for cluster_innervoice, og
        # longing ingest'er stadig i pressure-accumulatoren. Aldrig begge live.
        "description": "cluster-daemon FAMILIE #3 (affect) LIVE: surprise+conflict+desire (gated LLM) + longing_signal+emotion_repair_bridge (non-LLM, ubetinget) under ÉN event-gate; erstatter de 5 pensionerede daemons; bevarer alle outputs (surprise/conflict-cache, longing-pressure).",
    },
    "cluster_narrative": {
        "module": "core.services.cluster_daemon",
        "reset_var": "_NARRATIVE_FAMILY",
        "reset_value": None,
        "default_cadence_minutes": 1440,
        "default_enabled": True,
        # Cluster-daemon-konsolidering (spec 2026-07-14), FAMILIE #4 (narrative/
        # self-history): development_narrative + narrative_summary + identity_drift
        # + identity_sketch + consolidation_judge foldet ind i ÉN Central-styret
        # familie. Kører LIVE (prove-then-retire END STATE) — de 5 gamle daemons er
        # PENSIONERET (default_enabled=False, retired 2026-07-15). KEY DIFFERENCE
        # fra familie #2/#3: TIME-BASED (ikke event-drevet) — INGEN
        # should_generative_fire event-gate. Bjørn: "nogen er nød til at forblive
        # på tid for hans indre liv". Hvert medlem kører UBETINGET hver familie-tick
        # og self-throttler på sin EGEN cadence (24t/15min/24t/6h/24t), så output +
        # daglig rytme bevares. default_cadence_minutes=1440 markerer den
        # dominerende daglige rytme (dokumentation; heartbeaten gater på is_enabled,
        # ikke cadence — medlemmerne self-throttler). Aldrig begge live.
        "description": "cluster-daemon FAMILIE #4 (narrative/self-history) LIVE, TIME-BASED (ingen event-gate): development_narrative+narrative_summary+identity_drift+identity_sketch+consolidation_judge; hvert medlem self-throttler på egen cadence; erstatter de 5 pensionerede daemons; bevarer alle outputs (development-narrative log, identity_drift snapshot).",
    },
}


def get_daemon_names() -> set[str]:
    return set(_REGISTRY.keys())


def _load_state() -> dict[str, dict[str, Any]]:
    p = _state_file()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict[str, dict[str, Any]]) -> None:
    p = _state_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_daemon_state(name: str) -> dict[str, Any]:
    return _load_state().get(name, {})


def _set_daemon_state(name: str, updates: dict[str, Any]) -> None:
    state = _load_state()
    entry = state.get(name, {})
    entry.update(updates)
    state[name] = entry
    _save_state(state)


def _require_known(name: str) -> None:
    if name not in _REGISTRY:
        valid = sorted(_REGISTRY.keys())
        raise ValueError(f"unknown daemon '{name}'. Valid: {valid}")


def is_enabled(name: str) -> bool:
    """Return True if the named daemon should run. Unknown daemons return True (safe default)."""
    if name not in _REGISTRY:
        return True
    entry = _get_daemon_state(name)
    default = _REGISTRY[name].get("default_enabled", True)
    return bool(entry.get("enabled", default))


def set_daemon_enabled(name: str, enabled: bool) -> None:
    _require_known(name)
    _set_daemon_state(name, {"enabled": enabled})


def get_effective_cadence(name: str) -> int:
    """Return interval in minutes: override if set, else default."""
    entry = _get_daemon_state(name)
    override = entry.get("interval_minutes_override")
    if override is not None:
        return int(override)
    return int(_REGISTRY[name]["default_cadence_minutes"])


def record_daemon_tick(name: str, result: dict[str, Any]) -> None:
    """Record last_run_at and a summary of the tick result. Called by heartbeat_runtime."""
    if name not in _REGISTRY:
        return
    now = datetime.now(UTC).isoformat()
    summary = ", ".join(f"{k}: {v}" for k, v in list(result.items())[:3])
    _set_daemon_state(name, {"last_run_at": now, "last_result_summary": summary})


def _hours_since(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return max((datetime.now(UTC) - dt).total_seconds() / 3600.0, 0.0)
    except ValueError:
        return None


def get_all_daemon_states() -> list[dict[str, Any]]:
    """Return status for all registered daemons."""
    file_state = _load_state()
    result = []
    for name, reg in _REGISTRY.items():
        entry = file_state.get(name, {})
        override = entry.get("interval_minutes_override")
        last_run = entry.get("last_run_at", "")
        _default_enabled = reg.get("default_enabled", True)
        result.append({
            "name": name,
            "enabled": bool(entry.get("enabled", _default_enabled)),
            "description": reg["description"],
            "default_cadence_minutes": reg["default_cadence_minutes"],
            "interval_minutes_override": override,
            "effective_cadence_minutes": int(override) if override is not None else reg["default_cadence_minutes"],
            "last_run_at": last_run,
            "hours_since_last_run": _hours_since(last_run),
            "last_result_summary": entry.get("last_result_summary", ""),
        })
    return result


def control_daemon(
    name: str,
    action: str,
    *,
    interval_minutes: int | None = None,
) -> dict[str, Any]:
    """Control a daemon. Actions: enable, disable, restart, set_interval.

    Returns {"ok": True, "name": name, "action": action} on success.
    Raises ValueError on unknown daemon, invalid action, or bad params.
    """
    _require_known(name)

    if action == "enable":
        set_daemon_enabled(name, True)
    elif action == "disable":
        set_daemon_enabled(name, False)
    elif action == "restart":
        _restart_daemon(name)
    elif action == "set_interval":
        if interval_minutes is None:
            raise ValueError("interval_minutes required for set_interval action")
        if interval_minutes < 1:
            raise ValueError(f"interval_minutes must be >= 1, got {interval_minutes}")
        _set_daemon_state(name, {"interval_minutes_override": interval_minutes})
    else:
        raise ValueError(f"unknown action '{action}'. Valid: enable, disable, restart, set_interval")

    return {"ok": True, "name": name, "action": action}


def _restart_daemon(name: str) -> None:
    """Clear the module-level state variable so the daemon fires on next heartbeat tick."""
    reg = _REGISTRY[name]
    module_path = reg["module"]
    reset_var = reg["reset_var"]
    reset_value = reg["reset_value"]

    # Module may not be imported yet — no-op then.
    module = sys.modules.get(module_path)
    if module is None:
        return

    if hasattr(module, reset_var):
        setattr(module, reset_var, reset_value)


