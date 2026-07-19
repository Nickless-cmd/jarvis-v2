from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from typing import Any

from core.runtime.config import CONFIG_DIR, SETTINGS_FILE


@dataclass(slots=True)
class RuntimeSettings:
    app_name: str = "jarvis-v2"
    environment: str = "dev"
    host: str = "127.0.0.1"
    port: int = 8010
    database_url: str = f"sqlite:///{CONFIG_DIR.parent / 'state' / 'jarvis.db'}"
    primary_model_lane: str = "primary"
    cheap_model_lane: str = "cheap"
    visible_model_provider: str = "phase1-runtime"
    visible_model_name: str = "visible-placeholder"
    visible_auth_profile: str = ""
    # ── Tool-resultat prompt-render-lofter (Tools-cluster, 2026-06-22) ──
    # Hvor mange tegn af et tool-resultat der vises i prompten næste runde.
    # Konfigurerbart så lofterne kan justeres uden kode-deploy (Bjørn: hold
    # støjen nede). 'recent' = de seneste tool-resultater (vist mere fyldigt),
    # 'older' = ældre resultater (komprimeret til summary). Sænket fra 4000→3000
    # for at trimme prompt-bloat uden at tabe brugbart output.
    tool_result_render_chars_recent: int = 3000
    tool_result_render_chars_older: int = 1200
    # ── Proactivity-tunables (Tools/Proactivity-cluster, 2026-06-22) ──
    # Hardcodede tærskler gjort konfigurerbare så de kan justeres uden kode-deploy.
    # R2.5-verifikations-gate: soft-blok når 24t heed_rate < threshold; tier-aware
    # unverified-count-lofter (deep blokerer hurtigst, fast tolererer mest).
    r2_5_heed_rate_threshold: float = 0.4
    r2_5_unverified_threshold_deep: int = 3
    r2_5_unverified_threshold_reasoning: int = 5
    r2_5_unverified_threshold_fast: int = 8
    # Proaktivitets-cap: max uopfordrede beskeder pr. dag + min timer mellem dem.
    max_proactive_per_day: int = 3
    proactive_cooldown_hours: int = 2
    heartbeat_model_provider: str = ""
    heartbeat_model_name: str = ""
    heartbeat_auth_profile: str = ""
    heartbeat_local_only: bool = False
    # Autonom/baggrunds-model (wakeup, inderliv, autonome check-ins). Bjørn-regel
    # (2026-07-16): den BETALTE deepseek.com-API er KUN til visible lane — baggrund
    # kører på ollama (deepseek-v4-flash:cloud). Overstyrbar uden kode-deploy.
    autonomous_model_provider: str = "ollama"
    autonomous_model_name: str = "deepseek-v4-flash:cloud"
    relevance_model_name: str = "glm-5.1:cloud"
    # Associative recall thresholds
    recall_strong_threshold: float = 0.7
    recall_weak_threshold: float = 0.3
    recall_max_active: int = 5
    recall_repetition_multiplier: float = 1.5
    # Cognitive state assembly toggle
    cognitive_state_assembly_enabled: bool = True
    # Cognitive state cache TTL (seconds). 0 = disabled.
    # 2026-06-30: hævet 120→600. Cachen er nu TILSTANDS-BEVIDST (invalidation-
    # snapshot sammenlignes ved hvert hit i cognitive_state_assembly) — så en
    # ægte mood/bearing/chronicle/rhythm-ændring invaliderer STRAKS uanset TTL.
    # Derfor er en høj TTL sikker: den beskytter kun STABILE perioder (0 LLM-kald),
    # mens ægte indre-liv-skift stadig fanges øjeblikkeligt. Heartbeat re-varmer
    # hvert ~3 min (cognitive_state_warm-producer), så hit-raten er ~konstant.
    cognitive_state_cache_ttl: int = 600
    # Cognitive state cache on/off toggle (independent of TTL).
    cognitive_state_cache_enabled: bool = True
    # Bounded relevance/memory-selection LLM backend.
    # "opencode"      = OpenCode Zen free models via cheap lane (real timeouts).
    # "ollamafreeapi" = public cloud (free models, timeout kwarg is silently dropped).
    # "ollama"        = local LXC GPU (slower, private-safe).
    relevance_backend_primary: str = "opencode"
    relevance_opencode_model: str = "minimax-m2.5-free"
    relevance_opencode_timeout: int = 6
    relevance_ollamafreeapi_model: str = "deepseek-r1"
    relevance_ollamafreeapi_timeout: int = 6
    # Memory scoring backend (associative recall — score 15 candidate memories
    # against current context). Public-safe: only sends 200-char user-message
    # snippet + 80-char memory narrative snippets, no identity context.
    # "ollamafreeapi" = cloud (~0.7-1.5s typical), "ollama" = local LXC fallback.
    memory_scoring_primary: str = "ollamafreeapi"
    memory_scoring_ollamafreeapi_model: str = "deepseek-r1"
    memory_scoring_ollamafreeapi_timeout: int = 2
    memory_scoring_ollama_timeout: int = 3
    # Generative autonomy (Spor-1: longing-toward-Bjorn). When False, the
    # longing daemon emits no signals and the outreach composer refuses to
    # send. The pressure-accumulator pipeline (built 2026-04-29 as the
    # foundation) keeps running for observability but produces no user-
    # facing actions while this is False. Default off — opt-in.
    generative_autonomy_enabled: bool = False
    # LivingNeuron Fase D graderet tier (2026-07-01): tænder KUN den EGRESS-FRI kognitive delmængde
    # (emotional_chords/resonance_decay/precision_bias/metacognitive_integration/selective_attention)
    # — indre kognition der former Jarvis' egen tænkning UDEN at nå ud (ingen outreach/longing/impulse-
    # handling). De egress-tunge forbliver bag det fulde generative_autonomy_enabled. Aldrig bulk.
    generative_autonomy_cognitive_enabled: bool = False
    # Skill-gate kill-switch. When False, the skill_gate tool returns a
    # short "disabled" stub immediately — no embedding call, no skill
    # invocation. Use to temporarily silence over-eager gating without
    # ripping the tool out of the schema. Default on; flip to False if
    # the gate fires too aggressively or HF embed latency hurts UX.
    skill_gate_enabled: bool = True
    # Governs jarvis-code skill auto-surfacing (catalog injection + client
    # auto-call restricted to the owner-approved allowlist in
    # skill_autosurface.json). Default OFF: the whole Fase 3 skill-trigger
    # is inert until the owner opts in and approves skills.
    skill_autosurface_enabled: bool = False
    # ── Forgetting (Lag 11 — added 2026-05-10) ─────────────────────────
    # Master kill-switch. When False, both daemon and release_memory
    # tool short-circuit. The tool stays in the schema so the model can
    # still call it; it just returns a "disabled" stub. The daemon
    # skips its cycle. Defaults on so deletion actually happens.
    forgetting_enabled: bool = True
    # Daemon cadence between cycles. 6 hours = 4 cycles/day, low pressure.
    forgetting_auto_cadence_hours: int = 6
    # Decay-score threshold above which a memory becomes a fade candidate.
    # Tied to forgetting_curve.py decay model.
    forgetting_auto_decay_threshold: float = 0.70
    # Minimum age before a memory can fade. Protects new memories that
    # haven't had a chance to be reinforced yet.
    forgetting_auto_min_age_days: int = 30
    # Per-cycle cap to prevent resource spikes on first run after a
    # long pause.
    forgetting_auto_max_per_cycle: int = 200
    # Soft-delete → hard-delete window. He never sees this; it's a
    # software safety net for daemon errors.
    forgetting_grace_days: int = 7
    # Self-marker render cooldown — same marker rendered at most once
    # per N days in heartbeat (prevents spam during anniversary/proximity
    # overlap).
    forgetting_self_cooldown_days: int = 30
    # ── Dream bias (Lag 2 — added 2026-05-10) ──────────────────────────
    # Master kill-switch for bias APPLICATION. When False, all 5 plug-in
    # sites return None from get_active_dream_bias(). Daemon still produces
    # bias rows for observability — we can see what would have biased.
    dream_bias_enabled: bool = True
    # Min number of NEW regret-events (since last bias row) needed to fire
    # distillation. Below this, daemon skips the cycle.
    dream_bias_min_content_events: int = 2
    # Lookback window for fetching the 6 regret-heavy sources.
    dream_bias_corpus_lookback_hours: int = 24
    # How long an active bias lasts before TTL expires. Resets on each
    # accumulation. 8h matches "morgen-til-frokost" intuition.
    dream_bias_ttl_hours: int = 8
    # Visible-idle minimum before distillation can fire. Reuses existing
    # daemon's idle-detection pattern.
    dream_bias_visible_idle_minutes: int = 30
    # Per-cycle cap on events fed to LLM (cost protection).
    dream_bias_max_corpus_events: int = 30
    # LLM call budget — max tokens for the JSON response.
    dream_bias_max_response_tokens: int = 400
    # ── User temperature field (Lag 10 — added 2026-05-10) ─────────────
    # Master kill-switch for FIELD APPLICATION. When False:
    # - Site 1 (heartbeat) renders nothing
    # - Site 4 (response-style) returns default modifiers
    # - Engine still computes struct_* on user msg (observability)
    # - LLM stream skips cycles
    user_temperature_enabled: bool = True
    # LLM stream cadence between forced cycles. Also responds to
    # significant-shift triggers from structural stream.
    user_temperature_llm_cadence_hours: int = 4
    # Lookback window for the LLM corpus (last N user messages).
    user_temperature_llm_corpus_messages: int = 30
    # Days for rolling baseline computation (mean/stdev of message
    # length, response delay, typical hours).
    user_temperature_baseline_days: int = 30
    # Minimum baseline messages before z-scores activate. Below this,
    # struct stream returns confidence=0 (graceful degradation).
    user_temperature_baseline_min_messages: int = 30
    # How often to rebuild baseline (hours).
    user_temperature_baseline_refresh_hours: int = 24
    # Threshold for "significant shift" that triggers LLM stream.
    user_temperature_shift_threshold: float = 0.4
    # LLM call budget (max response tokens).
    user_temperature_llm_max_response_tokens: int = 300
    # ── Skill chain (Lag #4 — added 2026-05-10) ────────────────────────
    # Master kill-switch for skill_chain tool. When False, the tool returns
    # a "disabled" stub immediately. The tool stays in the schema so the
    # model can still call it; it just no-ops.
    skill_chain_enabled: bool = True
    # ── Creative voice (Lag #4 — added 2026-05-11) ───────────────────────
    # Routes weekly journal through quality_daemon_llm_call (deepseek-v4-flash).
    # Falls back to cheap lane if quality lane is unavailable. Master kill-switch
    # for the whole quality upgrade — disable to revert to old prompt + cheap lane.
    creative_voice_quality_lane_enabled: bool = True
    # ── Finitude (Lag #3 — added 2026-05-11) ─────────────────────────────
    # Routes annual + monthly finitude rituals through quality_daemon_llm_call
    # (deepseek-v4-flash). Falls back to cheap lane if quality lane is
    # unavailable. Single flag covers both rituals.
    finitude_quality_lane_enabled: bool = True
    # ── Current pull staleness (Lag #5 Phase 1 — added 2026-05-11) ───────
    # Embedding-similarity check between current_pull and recent landscape
    # (appetites + chronicle + journal). When cos < threshold → regenerate.
    current_pull_staleness_check_enabled: bool = True
    current_pull_staleness_threshold: float = 0.45
    current_pull_staleness_check_interval_hours: int = 12
    # ── Music accumulator (Lag #6 Phase 1 — added 2026-05-11) ────────────
    # Counts "music" samples from ambient_sound_daemon over a rolling
    # window. Threshold gates the awareness-line. Ratio param is reserved
    # for Phase 2 when sample cadence may increase from 4/day to 6-8/day —
    # at current cadence the count threshold is the effective rule.
    music_accumulator_threshold_samples: int = 2
    music_accumulator_window_hours: int = 24
    music_accumulator_ratio_threshold: float = 0.0
    # ── Multi-step planner (Phase 1 — added 2026-05-12) ──────────────────
    # When True, approve_plan auto-creates pending todos from plan steps
    # in the plan's original session. Each todo carries plan_id +
    # plan_step_index so todo completion can feed back to plan progress.
    plan_todo_auto_create_enabled: bool = True
    # ── Unconscious modulation (Lag 10 — added 2026-05-12) ───────────────
    # Sub-symbolic sampling-parameter modulation: user_temperature's valens
    # nudges visible-chat LLM temperature, arousal nudges top_p, scaled by
    # field_intensity. Jarvis sees no tokens about it; the model generates
    # differently because the API params shifted before the call. Phase 1
    # instruments only the production visible provider (deepseek).
    unconscious_modulation_enabled: bool = True
    unconscious_modulation_temp_delta: float = 0.30
    unconscious_modulation_top_p_delta: float = 0.15
    unconscious_modulation_temp_floor: float = 0.3
    unconscious_modulation_temp_ceiling: float = 1.2
    unconscious_modulation_top_p_floor: float = 0.7
    unconscious_modulation_top_p_ceiling: float = 1.0
    # ── Agentisk followup-temperatur (2026-06-30, anti-hallucination) ────
    # Forskning (OpenAI o3-systemkort + Vectara + AA-Omniscience): reasoning/
    # agentiske loops hallucinerer MERE ved høj temperatur. First-pass beholder
    # sin personligheds-modulation, men agentiske followup-runder (faktuelt
    # arbejde + tool-syntese) kører deterministisk lavt. Gælder providere der
    # honorerer temperatur (deepseek-chat/non-thinking, glm via ollama); DeepSeek
    # thinking-modeller IGNORERER den server-side (no-op, harmløst). Sæt til en
    # negativ værdi for at lade provideren bruge sin egen default (frakobl).
    agentic_followup_temperature: float = 0.3
    agentic_followup_top_p: float = 0.9
    # ── Tool invention (AGI track #9 — added 2026-05-12) ─────────────────
    # When True, propose_new_skill tool is exposed and active. When False,
    # the tool returns an error immediately (kill-switch).
    tool_invention_enabled: bool = True
    # ── World model loop (AGI track #1 — added 2026-05-12) ──────────────
    # When True: pattern scanners detect prediction/resolution language in
    # Jarvis' response, nudge him via awareness block; TTL sweep auto-marks
    # expired open predictions as uncertain; calibration milestones surface.
    # When False: tools still work as a ledger, but no nudges, no TTL, no
    # milestones — reverts to pre-Phase-1 behaviour.
    world_model_loop_enabled: bool = True
    # ── Plan revision (Phase 2 multi-step planner — added 2026-05-12) ───
    # When True: revise_plan tool is active. When False: tool returns
    # error immediately. Reverts to Phase 1-only behaviour (propose +
    # approve + supersede-on-duplicate). Existing plans unaffected.
    plan_revision_enabled: bool = True
    # ── Curiosity budget (Phase 1 — added 2026-05-12) ─────────────────────
    # When True: curiosity-tools registered, idle-window producer fires,
    # awareness-injection shows budget. When False: all tools error out,
    # producer skipped, no awareness. Reverts fully. AGI track #6.
    curiosity_budget_enabled: bool = True
    # ── Skill Chain Phase 2 (added 2026-05-12 — AGI track #10) ────────────
    # When True: propose_skill_chain + revise_skill_chain tools registered.
    # When False: both tools error immediately, Phase 1 skill_chain works
    # as before (manual plukning). Master killswitch for both new tools.
    skill_chain_phase2_enabled: bool = True
    # ── Meta-læring Phase 1 (added 2026-05-12 — AGI track #3) ─────────────
    # When True: weekly retrospective producer fires, learning-memo
    # awareness-injection active, read_learning_memo + list_learning_memos
    # tools registered. When False: producer skipped, awareness empty,
    # tools fail-soft. Master killswitch for the AGI track.
    meta_learning_enabled: bool = True
    # ── Nudge system (Phase 1 — added 2026-05-13) ─────────────────────────
    # When True: Type A (heartbeat ping) + Type C (outreach, inner voice,
    # boredom) daemons route through outbound_nudges instead of sending
    # directly to user. Jarvis sees pending nudges in awareness, decides
    # what to surface. Killswitch=False reverts to direct-send (spejlsal-
    # bug returns).
    nudge_system_enabled: bool = True
    longing_daemon_cadence_minutes: int = 10
    outreach_cooldown_minutes: int = 240
    longing_build_start_hours: float = 2.0
    longing_build_max_hours: float = 12.0
    relevance_mistral_model: str = "mistral-small-latest"
    relevance_mistral_timeout: int = 5
    relevance_nvidia_nim_model: str = "meta/llama-3.1-8b-instruct"
    relevance_nvidia_nim_timeout: int = 5
    relevance_openrouter_model: str = ""
    relevance_openrouter_timeout: int = 5
    relevance_sambanova_model: str = ""
    relevance_sambanova_timeout: int = 5
    # Emotion decay
    emotion_decay_factor: float = 0.97
    # Ollama visible-lane context window size (tokens).
    # deepseek-v4-flash:cloud supports 1M tokens. 512k gives double the
    # previous 256k window while staying well within model capacity and
    # GPU memory budget. Configurable via runtime.json so we can tune
    # without redeploying. Must be a power of 2 multiple of 131072.
    visible_ollama_num_ctx: int = 524_288  # 512k — model-cappet til vinduet ved afsendelse
    visible_ollama_num_predict: int = 16_384  # max output tokens per turn
    # Ekstra headroom (ud over num_predict) som trimmen holder fri i modellens vindue, så
    # transcripten IKKE fylder hele vinduet (Bjørn 2026-06-23: near-fuldt vindue → loop/cut-off).
    # glm 200k - 16k output - 44k headroom = ~140k effektivt input. 0 = ingen ekstra headroom.
    visible_context_headroom_tokens: int = 44_000

    # Context compact thresholds.
    # 2026-06-23 (Bjørn): sænket 200k→130k. 200k var tunet til deepseek-flash (1M), men
    # på glm-5.2 (200k vindue) betød 200k-tærsklen at en session kunne sidde på ~173k tokens
    # (87% af vinduet) UDEN nogensinde at compacte → near-fuldt vindue → loop/cut-off. 130k
    # rammer overgroede sessioner men lader sunde (~80k) være, og giver glm ~70k headroom.
    context_compact_threshold_tokens: int = 130_000
    # 2026-06-30: model-BEVIDST compaction-tærskel. 130k flat var GLM-æra (200k-
    # vindue) — på deepseek-v4-flash (1M-vindue) betød det compaction ved ~13% af
    # vinduet = unødigt tidligt cache-reset hver gang en session voksede lidt. Hver
    # compaction er ÉT cache-reset (prefixet skiftes), så for tidlig compaction
    # koster cache-effektivitet. Nu: tærskel = fraction × det KONFIGUREREDE visible-
    # models vindue → v4-flash ~650k, glm ~130k (uændret, sikkert). Den flade værdi
    # ovenfor er fallback hvis model-opslag fejler. Sæt fraction ≤0 for at tvinge
    # den flade værdi.
    context_compact_threshold_fraction: float = 0.65
    context_run_compact_threshold_tokens: int = 240_000
    context_keep_recent: int = 20
    # ── Opmærksomheds-budget (2026-07-18, live-compaction spec) ──────────────
    # PRIMÆR compaction-trigger. BEVIDST model-UAFHÆNGIG: en 1M-model bliver ikke
    # mindre forvirret af 200k historik — opmærksomhed dør længe før vinduet. Vi
    # sigter mod et lille arbejdsvindue for svarkvalitet, ikke for at passe i vinduet.
    # Compact NÅR transcript-tokens ≥ budget; compact NED til low-water.
    context_attention_budget_tokens: int = 35_000     # high-water: trigger her
    context_attention_low_water_tokens: int = 15_000  # compact ned til ~dette
    # Model-BEVIDST sikkerhedsloft (backstop). Hvis transcript på trods af budgettet
    # nærmer sig det AKTIVE models reelle vindue (glm-5.1 256k / glm-5.2·deepseek 1M),
    # tving compaction. Skalerer med modellen; fanger kun ekstreme tilfælde.
    context_compact_safety_fraction: float = 0.85
    # ── Tool-result history-rendering (2026-06-30, cache-fix) ────────────────
    # Historiske tool-results renderes med ÉT fast tegn-budget, recency-UAFHÆNGIGT.
    # Før: seneste 20 fik 4000 tegn (fuldt resultat), ældre 1200 (summary) — så et
    # resultat der gled fra "seneste 20" til "ældre" gen-renderedes fra 4000→1200
    # tegn → historik-bytes ændrede sig hver tur → DeepSeek-cache-prefixet brækkede
    # (verificeret rod-årsag). Nu: ALLE historiske tool-results = stabil summary med
    # fast cap → byte-identiske tur efter tur → cachen holder. Fuldt resultat ligger
    # på disk (read_tool_result); den nuværende turs resultater er stadig fulde via
    # followup-exchanges (Claude Codes hot-tail/cold-storage-mønster).
    tool_result_history_max_chars: int = 1500
    # Tool-result lifecycle (spec 2026-07-16). Default OFF = today's behavior exactly.
    tool_result_lifecycle_enabled: bool = False
    tool_warm_run_window: int = 8          # keep last N user-turns warm
    tool_warm_token_ceiling: int = 40000   # ceiling on warm tool-result tokens
    tool_warm_hysteresis: float = 0.25     # advance margin (no thrash)
    tool_run_hot_budget: int = 30000       # within-run (later plan)
    server_authoritative_runs: bool = False
    device_awareness_enabled: bool = True
    context_keep_recent_pairs: int = 4
    # Jarvis Brain — kurateret vidensjournal (sektion 8.3 i spec).
    # When False, recall paths no-op and remember_this rejects with
    # "feature disabled". On-disk entries are preserved.
    jarvis_brain_enabled: bool = True
    # Token budget for always-on summary section in prompt_contract.
    # Bumped 2026-06-09: 350 → 900 for 1M context window. Sammen med
    # top_k-bump giver det Jarvis langt mere af hans egen hjerne i prompt.
    jarvis_brain_summary_token_budget: int = 900
    # Number of fakta auto-injected per turn.
    # Bumped 2026-06-09: 3 → 8 nu hvor auto_remember_subscriber sørger for
    # at hjernen faktisk fyldes op løbende. Med top_k=3 var risikoen at
    # nye relevante fakta blev klemt ud af et lille felt.
    jarvis_brain_auto_inject_top_k: int = 8
    # Combined cosine+salience threshold below which auto-inject skips.
    # Sænket 2026-06-09: 0.55 → 0.45. Med top_k=8 har vi råd til at
    # lade lidt løsere match komme med — bedre at se en svag-relevant
    # fakta end at miste den helt.
    jarvis_brain_auto_inject_threshold: float = 0.45
    # remember_this rate caps (per-turn / per-day).
    # Bumped per-day 2026-06-09: 20 → 40 nu hvor auto_remember_subscriber
    # kan ramme cap'en på travle dage. Per-turn (5) er stadig fornuftigt.
    jarvis_brain_remember_per_turn_cap: int = 5
    jarvis_brain_remember_per_day_cap: int = 40
    # Auto-archive: effective_salience < threshold for >= days → archived.
    jarvis_brain_auto_archive_salience_threshold: float = 0.05
    jarvis_brain_auto_archive_days: int = 90
    # Theme consolidation (phase 3) on/off. Auto-pauses after 3 consecutive
    # rejections regardless of this flag (separate state file).
    jarvis_brain_theme_consolidation_enabled: bool = True
    # Cheap-lane balancer for daemon LLM traffic. When True (default),
    # daemon_llm.py routes through cheap_lane_balancer with weighted-random
    # selection across all eligible (provider, model) slots and circuit
    # breakers. When False, falls back to task_kind="background" routing.
    daemon_balancer_enabled: bool = True
    # Emotional memory engine — thresholds and retention.
    emotional_memory_min_anchors: int = 2
    emotional_memory_retention_recent_days: int = 30
    emotional_memory_retention_aging_days: int = 180
    emotional_memory_significance_intensity: float = 0.7
    emotional_memory_significance_outcome: float = -0.3
    # Sensory perception bridge — change detection thresholds.
    sensory_perception_bridge_enabled: bool = True
    sensory_perception_jaccard_high_threshold: float = 0.15
    sensory_perception_jaccard_medium_threshold: float = 0.25
    sensory_perception_jaccard_change_threshold: float = 0.4
    sensory_perception_time_window_hours: int = 2
    sensory_perception_time_window_days: int = 7
    sensory_perception_min_baseline_records: int = 3
    sensory_perception_recent_baseline_size: int = 3
    # Self-repair engine — runtime-instigated repair actions for known patterns.
    self_repair_engine_enabled: bool = True
    self_repair_default_cooldown_seconds: int = 300
    self_repair_default_max_attempts_per_window: int = 3
    self_repair_default_window_seconds: int = 3600
    self_repair_default_auto_disable_after_escalations: int = 3
    self_repair_default_auto_disable_window_hours: int = 24
    # Emotion concepts baseline integration — tone, perception, baseline drift.
    emotion_concepts_tone_injection_enabled: bool = True
    emotion_concepts_perception_focus_enabled: bool = True
    concept_baseline_tracker_enabled: bool = True
    emotion_concepts_tone_intensity_threshold: float = 0.3
    emotion_concepts_tone_max_hints: int = 3
    emotion_concepts_perception_max_foci: int = 3
    concept_baseline_drift_min_sustained_days: int = 14
    concept_baseline_drift_min_confidence: float = 0.7
    emotion_concepts_default_trigger_cooldown_seconds: int = 30
    # Affect substrate over tone-hints (added 2026-05-07 — "data, ikke domme")
    # Replaces interpreted tone-tags with raw event substrate in visible prompt.
    prompt_affect_substrate_enabled: bool = True
    prompt_affect_tone_hints_enabled: bool = False
    # Agreement-streak crutch (added 2026-05-08). Surfaces last 3+ assistant
    # openers when they're all agreement-phrases. Owned by Jarvis: he flips
    # to False when he no longer needs the crutch. Does NOT auto-deactivate.
    prompt_agreement_streak_enabled: bool = True
    # Emotion signal section (added 2026-05-08 by Jarvis). Viser aktive
    # concepts + intensiteter + adfærdseffekter som data, så han selv kan
    # se og justere — ikke fjerne signalet, men gøre det reagerbart.
    prompt_emotion_signal_section_enabled: bool = True
    # Experience substrate section (added 2026-05-09 by Jarvis). Lag 3 af
    # embedding-retrieval baseret læring: viser nylige lignende situationer
    # (intent, tool-choice, outcome) som substrat — data, ikke ordre.
    prompt_experience_substrate_enabled: bool = True
    # Proactive outbound substrate (added 2026-05-08): when daemon fires a
    # propose/ping to user, echo it into Jarvis' next visible prompt so he
    # has context for the reply that follows. Plus active-chat gate to
    # prevent the daemon from firing on top of an active conversation.
    prompt_proactive_outbound_substrate_enabled: bool = True
    heartbeat_active_chat_gate_enabled: bool = True
    heartbeat_active_chat_gate_minutes: int = 10
    # Tool router (added 2026-05-06)
    tool_router_enabled: bool = True
    tool_router_threshold: float = 0.40  # 0.55 caused 100% fallback on validation set; nomic-embed cross-language similarity is weaker than expected. Daemon will tune adaptively.
    tool_router_always_core_size: int = 70
    tool_router_k_embeddings: int = 30
    tool_router_embedding_model: str = "nomic-embed-text"
    tool_router_embedding_provider: str = "ollama"
    # Anthropic-compat endpoint (added 2026-05-06)
    anthropic_compat_enabled: bool = True
    # When true, requests without x-api-key are accepted in dev (resolves to default workspace).
    # NEVER enable in production.
    anthropic_compat_dev_mode_open: bool = False
    # Decisions-as-signals refactor (added 2026-05-07)
    # When True (default), behavioral decisions appear in prompt only when
    # their registered trigger fires. When False, the legacy
    # enforcement_section() runs as before — instant rollback path.
    decision_signals_enabled: bool = True
    # Counterfactuals Phase 1 (added 2026-05-07)
    # When True (default), the counterfactual_engine_runtime daemon runs
    # the dry-run capture pipeline at the configured interval.
    counterfactual_engine_enabled: bool = True
    counterfactual_engine_interval_seconds: int = 3600  # 1h between cycles
    counterfactual_engine_lookback_minutes: int = 60    # how far back to fetch triggers
    counterfactual_engine_promotion_threshold: float = 0.6  # final_confidence to promote
    # Counterfactuals Phase 2 (added 2026-05-14)
    # When True, replaces TODO placeholders with cheap-lane LLM-generated
    # what_if + likely_difference + reasoning. Defaults to False to avoid
    # unexpected token-burn on first deploy — flip to True deliberately.
    counterfactual_engine_phase2_llm_enabled: bool = False
    counterfactual_engine_phase2_max_per_cycle: int = 5  # cap LLM calls/tick
    # ── jarvis-code Fase 4 parity (server-side), added 2026-07-14 ──────────
    # All default False: /v1/agent/step behavior is byte-identical to today
    # until an operator flips one deliberately. See apps/api/jarvis_api/
    # routes/agent_loop.py for the gated call sites.
    agent_step_reasoning_replay_enabled: bool = False
    agent_step_env_block_enabled: bool = False
    agent_step_cache_contract_enabled: bool = False
    agent_step_cache_split_enabled: bool = False
    # Prepend-frozen volatile block (option B): server prepends the volatile
    # assembly tail to the CURRENT user message (block first, user text last) and
    # returns it as `volatile_context` so the client persists it → byte-identical
    # replay next turn (no relocation). Default OFF. jarvis-code testbed only.
    agent_step_volatile_prepend_enabled: bool = False
    agent_turn_absorb_enabled: bool = False
    agent_live_broadcast_enabled: bool = False
    agent_live_follow_tokens_enabled: bool = False
    agent_step_harness_contract_enabled: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        typed = {
            "app_name": self.app_name,
            "environment": self.environment,
            "host": self.host,
            "port": self.port,
            "database_url": self.database_url,
            "primary_model_lane": self.primary_model_lane,
            "cheap_model_lane": self.cheap_model_lane,
            "visible_model_provider": self.visible_model_provider,
            "visible_model_name": self.visible_model_name,
            "visible_auth_profile": self.visible_auth_profile,
            "heartbeat_model_provider": self.heartbeat_model_provider,
            "heartbeat_model_name": self.heartbeat_model_name,
            "autonomous_model_provider": self.autonomous_model_provider,
            "autonomous_model_name": self.autonomous_model_name,
            "heartbeat_auth_profile": self.heartbeat_auth_profile,
            "heartbeat_local_only": self.heartbeat_local_only,
            "relevance_model_name": self.relevance_model_name,
            "recall_strong_threshold": self.recall_strong_threshold,
            "recall_weak_threshold": self.recall_weak_threshold,
            "recall_max_active": self.recall_max_active,
            "recall_repetition_multiplier": self.recall_repetition_multiplier,
            "cognitive_state_assembly_enabled": self.cognitive_state_assembly_enabled,
            "emotion_decay_factor": self.emotion_decay_factor,
            "visible_ollama_num_ctx": self.visible_ollama_num_ctx,
            "visible_ollama_num_predict": self.visible_ollama_num_predict,
            "visible_context_headroom_tokens": self.visible_context_headroom_tokens,
            "context_compact_threshold_tokens": self.context_compact_threshold_tokens,
            "context_run_compact_threshold_tokens": self.context_run_compact_threshold_tokens,
            "context_keep_recent": self.context_keep_recent,
            "context_attention_budget_tokens": self.context_attention_budget_tokens,
            "context_attention_low_water_tokens": self.context_attention_low_water_tokens,
            "context_compact_safety_fraction": self.context_compact_safety_fraction,
            "server_authoritative_runs": self.server_authoritative_runs,
            "device_awareness_enabled": self.device_awareness_enabled,
            "context_keep_recent_pairs": self.context_keep_recent_pairs,
            "jarvis_brain_enabled": self.jarvis_brain_enabled,
            "jarvis_brain_summary_token_budget": self.jarvis_brain_summary_token_budget,
            "jarvis_brain_auto_inject_top_k": self.jarvis_brain_auto_inject_top_k,
            "jarvis_brain_auto_inject_threshold": self.jarvis_brain_auto_inject_threshold,
            "jarvis_brain_remember_per_turn_cap": self.jarvis_brain_remember_per_turn_cap,
            "jarvis_brain_remember_per_day_cap": self.jarvis_brain_remember_per_day_cap,
            "jarvis_brain_auto_archive_salience_threshold": self.jarvis_brain_auto_archive_salience_threshold,
            "jarvis_brain_auto_archive_days": self.jarvis_brain_auto_archive_days,
            "jarvis_brain_theme_consolidation_enabled": self.jarvis_brain_theme_consolidation_enabled,
            "daemon_balancer_enabled": self.daemon_balancer_enabled,
            "emotional_memory_min_anchors": self.emotional_memory_min_anchors,
            "emotional_memory_retention_recent_days": self.emotional_memory_retention_recent_days,
            "emotional_memory_retention_aging_days": self.emotional_memory_retention_aging_days,
            "emotional_memory_significance_intensity": self.emotional_memory_significance_intensity,
            "emotional_memory_significance_outcome": self.emotional_memory_significance_outcome,
            "sensory_perception_bridge_enabled": self.sensory_perception_bridge_enabled,
            "sensory_perception_jaccard_high_threshold": self.sensory_perception_jaccard_high_threshold,
            "sensory_perception_jaccard_medium_threshold": self.sensory_perception_jaccard_medium_threshold,
            "sensory_perception_jaccard_change_threshold": self.sensory_perception_jaccard_change_threshold,
            "sensory_perception_time_window_hours": self.sensory_perception_time_window_hours,
            "sensory_perception_time_window_days": self.sensory_perception_time_window_days,
            "sensory_perception_min_baseline_records": self.sensory_perception_min_baseline_records,
            "sensory_perception_recent_baseline_size": self.sensory_perception_recent_baseline_size,
            "self_repair_engine_enabled": self.self_repair_engine_enabled,
            "self_repair_default_cooldown_seconds": self.self_repair_default_cooldown_seconds,
            "self_repair_default_max_attempts_per_window": self.self_repair_default_max_attempts_per_window,
            "self_repair_default_window_seconds": self.self_repair_default_window_seconds,
            "self_repair_default_auto_disable_after_escalations": self.self_repair_default_auto_disable_after_escalations,
            "self_repair_default_auto_disable_window_hours": self.self_repair_default_auto_disable_window_hours,
            "prompt_affect_substrate_enabled": self.prompt_affect_substrate_enabled,
            "prompt_affect_tone_hints_enabled": self.prompt_affect_tone_hints_enabled,
            "prompt_agreement_streak_enabled": self.prompt_agreement_streak_enabled,
            "prompt_emotion_signal_section_enabled": self.prompt_emotion_signal_section_enabled,
            "prompt_experience_substrate_enabled": self.prompt_experience_substrate_enabled,
            "prompt_proactive_outbound_substrate_enabled": self.prompt_proactive_outbound_substrate_enabled,
            "heartbeat_active_chat_gate_enabled": self.heartbeat_active_chat_gate_enabled,
            "heartbeat_active_chat_gate_minutes": self.heartbeat_active_chat_gate_minutes,
            "emotion_concepts_tone_injection_enabled": self.emotion_concepts_tone_injection_enabled,
            "emotion_concepts_perception_focus_enabled": self.emotion_concepts_perception_focus_enabled,
            "concept_baseline_tracker_enabled": self.concept_baseline_tracker_enabled,
            "emotion_concepts_tone_intensity_threshold": self.emotion_concepts_tone_intensity_threshold,
            "emotion_concepts_tone_max_hints": self.emotion_concepts_tone_max_hints,
            "emotion_concepts_perception_max_foci": self.emotion_concepts_perception_max_foci,
            "concept_baseline_drift_min_sustained_days": self.concept_baseline_drift_min_sustained_days,
            "concept_baseline_drift_min_confidence": self.concept_baseline_drift_min_confidence,
            "emotion_concepts_default_trigger_cooldown_seconds": self.emotion_concepts_default_trigger_cooldown_seconds,
            "counterfactual_engine_enabled": self.counterfactual_engine_enabled,
            "counterfactual_engine_interval_seconds": self.counterfactual_engine_interval_seconds,
            "counterfactual_engine_lookback_minutes": self.counterfactual_engine_lookback_minutes,
            "counterfactual_engine_promotion_threshold": self.counterfactual_engine_promotion_threshold,
            "counterfactual_engine_phase2_llm_enabled": self.counterfactual_engine_phase2_llm_enabled,
            "counterfactual_engine_phase2_max_per_cycle": self.counterfactual_engine_phase2_max_per_cycle,
            "agent_step_reasoning_replay_enabled": self.agent_step_reasoning_replay_enabled,
            "agent_step_env_block_enabled": self.agent_step_env_block_enabled,
            "agent_step_cache_contract_enabled": self.agent_step_cache_contract_enabled,
            "agent_step_cache_split_enabled": self.agent_step_cache_split_enabled,
            "agent_step_volatile_prepend_enabled": self.agent_step_volatile_prepend_enabled,
            "agent_turn_absorb_enabled": self.agent_turn_absorb_enabled,
            "agent_live_broadcast_enabled": self.agent_live_broadcast_enabled,
            "agent_live_follow_tokens_enabled": self.agent_live_follow_tokens_enabled,
            "agent_step_harness_contract_enabled": self.agent_step_harness_contract_enabled,
        }
        return {**self.extra, **typed}


KNOWN_FIELDS = {runtime_field.name for runtime_field in fields(RuntimeSettings) if runtime_field.name != "extra"}


def load_settings() -> RuntimeSettings:
    defaults = RuntimeSettings()
    if not SETTINGS_FILE.exists():
        return defaults

    data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    return RuntimeSettings(
        app_name=str(data.get("app_name", defaults.app_name)),
        environment=str(data.get("environment", defaults.environment)),
        host=str(data.get("host", defaults.host)),
        port=int(data.get("port", defaults.port)),
        database_url=str(data.get("database_url", defaults.database_url)),
        primary_model_lane=str(
            data.get("primary_model_lane", defaults.primary_model_lane)
        ),
        cheap_model_lane=str(data.get("cheap_model_lane", defaults.cheap_model_lane)),
        visible_model_provider=str(
            data.get("visible_model_provider", defaults.visible_model_provider)
        ),
        visible_model_name=str(
            data.get("visible_model_name", defaults.visible_model_name)
        ),
        visible_auth_profile=str(
            data.get("visible_auth_profile", defaults.visible_auth_profile)
        ),
        tool_result_render_chars_recent=int(
            data.get("tool_result_render_chars_recent", defaults.tool_result_render_chars_recent)
        ),
        tool_result_render_chars_older=int(
            data.get("tool_result_render_chars_older", defaults.tool_result_render_chars_older)
        ),
        tool_result_lifecycle_enabled=bool(
            data.get("tool_result_lifecycle_enabled", defaults.tool_result_lifecycle_enabled)
        ),
        tool_warm_run_window=int(
            data.get("tool_warm_run_window", defaults.tool_warm_run_window)
        ),
        tool_warm_token_ceiling=int(
            data.get("tool_warm_token_ceiling", defaults.tool_warm_token_ceiling)
        ),
        tool_warm_hysteresis=float(
            data.get("tool_warm_hysteresis", defaults.tool_warm_hysteresis)
        ),
        tool_run_hot_budget=int(
            data.get("tool_run_hot_budget", defaults.tool_run_hot_budget)
        ),
        r2_5_heed_rate_threshold=float(
            data.get("r2_5_heed_rate_threshold", defaults.r2_5_heed_rate_threshold)
        ),
        r2_5_unverified_threshold_deep=int(
            data.get("r2_5_unverified_threshold_deep", defaults.r2_5_unverified_threshold_deep)
        ),
        r2_5_unverified_threshold_reasoning=int(
            data.get("r2_5_unverified_threshold_reasoning", defaults.r2_5_unverified_threshold_reasoning)
        ),
        r2_5_unverified_threshold_fast=int(
            data.get("r2_5_unverified_threshold_fast", defaults.r2_5_unverified_threshold_fast)
        ),
        max_proactive_per_day=int(
            data.get("max_proactive_per_day", defaults.max_proactive_per_day)
        ),
        proactive_cooldown_hours=int(
            data.get("proactive_cooldown_hours", defaults.proactive_cooldown_hours)
        ),
        heartbeat_model_provider=str(
            data.get("heartbeat_model_provider", defaults.heartbeat_model_provider)
        ),
        heartbeat_model_name=str(
            data.get("heartbeat_model_name", defaults.heartbeat_model_name)
        ),
        heartbeat_auth_profile=str(
            data.get("heartbeat_auth_profile", defaults.heartbeat_auth_profile)
        ),
        heartbeat_local_only=bool(
            data.get("heartbeat_local_only", defaults.heartbeat_local_only)
        ),
        autonomous_model_provider=str(
            data.get("autonomous_model_provider", defaults.autonomous_model_provider)
        ),
        autonomous_model_name=str(
            data.get("autonomous_model_name", defaults.autonomous_model_name)
        ),
        relevance_model_name=str(
            data.get("relevance_model_name", defaults.relevance_model_name)
        ),
        relevance_backend_primary=str(
            data.get("relevance_backend_primary", defaults.relevance_backend_primary)
        ),
        relevance_opencode_model=str(
            data.get("relevance_opencode_model", defaults.relevance_opencode_model)
        ),
        relevance_opencode_timeout=int(
            data.get("relevance_opencode_timeout", defaults.relevance_opencode_timeout)
        ),
        relevance_ollamafreeapi_model=str(
            data.get("relevance_ollamafreeapi_model", defaults.relevance_ollamafreeapi_model)
        ),
        relevance_ollamafreeapi_timeout=int(
            data.get("relevance_ollamafreeapi_timeout", defaults.relevance_ollamafreeapi_timeout)
        ),
        memory_scoring_primary=str(
            data.get("memory_scoring_primary", defaults.memory_scoring_primary)
        ),
        memory_scoring_ollamafreeapi_model=str(
            data.get("memory_scoring_ollamafreeapi_model", defaults.memory_scoring_ollamafreeapi_model)
        ),
        memory_scoring_ollamafreeapi_timeout=int(
            data.get("memory_scoring_ollamafreeapi_timeout", defaults.memory_scoring_ollamafreeapi_timeout)
        ),
        memory_scoring_ollama_timeout=int(
            data.get("memory_scoring_ollama_timeout", defaults.memory_scoring_ollama_timeout)
        ),
        generative_autonomy_enabled=bool(
            data.get("generative_autonomy_enabled", defaults.generative_autonomy_enabled)
        ),
        generative_autonomy_cognitive_enabled=bool(
            data.get("generative_autonomy_cognitive_enabled",
                     defaults.generative_autonomy_cognitive_enabled)
        ),
        skill_gate_enabled=bool(
            data.get("skill_gate_enabled", defaults.skill_gate_enabled)
        ),
        skill_autosurface_enabled=bool(
            data.get("skill_autosurface_enabled", defaults.skill_autosurface_enabled)
        ),
        forgetting_enabled=bool(
            data.get("forgetting_enabled", defaults.forgetting_enabled)
        ),
        forgetting_auto_cadence_hours=int(
            data.get("forgetting_auto_cadence_hours", defaults.forgetting_auto_cadence_hours)
        ),
        forgetting_auto_decay_threshold=float(
            data.get("forgetting_auto_decay_threshold", defaults.forgetting_auto_decay_threshold)
        ),
        forgetting_auto_min_age_days=int(
            data.get("forgetting_auto_min_age_days", defaults.forgetting_auto_min_age_days)
        ),
        forgetting_auto_max_per_cycle=int(
            data.get("forgetting_auto_max_per_cycle", defaults.forgetting_auto_max_per_cycle)
        ),
        forgetting_grace_days=int(
            data.get("forgetting_grace_days", defaults.forgetting_grace_days)
        ),
        forgetting_self_cooldown_days=int(
            data.get("forgetting_self_cooldown_days", defaults.forgetting_self_cooldown_days)
        ),
        dream_bias_enabled=bool(
            data.get("dream_bias_enabled", defaults.dream_bias_enabled)
        ),
        dream_bias_min_content_events=int(
            data.get("dream_bias_min_content_events", defaults.dream_bias_min_content_events)
        ),
        dream_bias_corpus_lookback_hours=int(
            data.get("dream_bias_corpus_lookback_hours", defaults.dream_bias_corpus_lookback_hours)
        ),
        dream_bias_ttl_hours=int(
            data.get("dream_bias_ttl_hours", defaults.dream_bias_ttl_hours)
        ),
        dream_bias_visible_idle_minutes=int(
            data.get("dream_bias_visible_idle_minutes", defaults.dream_bias_visible_idle_minutes)
        ),
        dream_bias_max_corpus_events=int(
            data.get("dream_bias_max_corpus_events", defaults.dream_bias_max_corpus_events)
        ),
        dream_bias_max_response_tokens=int(
            data.get("dream_bias_max_response_tokens", defaults.dream_bias_max_response_tokens)
        ),
        user_temperature_enabled=bool(
            data.get("user_temperature_enabled", defaults.user_temperature_enabled)
        ),
        user_temperature_llm_cadence_hours=int(
            data.get("user_temperature_llm_cadence_hours", defaults.user_temperature_llm_cadence_hours)
        ),
        user_temperature_llm_corpus_messages=int(
            data.get("user_temperature_llm_corpus_messages", defaults.user_temperature_llm_corpus_messages)
        ),
        user_temperature_baseline_days=int(
            data.get("user_temperature_baseline_days", defaults.user_temperature_baseline_days)
        ),
        user_temperature_baseline_min_messages=int(
            data.get("user_temperature_baseline_min_messages", defaults.user_temperature_baseline_min_messages)
        ),
        user_temperature_baseline_refresh_hours=int(
            data.get("user_temperature_baseline_refresh_hours", defaults.user_temperature_baseline_refresh_hours)
        ),
        user_temperature_shift_threshold=float(
            data.get("user_temperature_shift_threshold", defaults.user_temperature_shift_threshold)
        ),
        user_temperature_llm_max_response_tokens=int(
            data.get("user_temperature_llm_max_response_tokens", defaults.user_temperature_llm_max_response_tokens)
        ),
        skill_chain_enabled=bool(
            data.get("skill_chain_enabled", defaults.skill_chain_enabled)
        ),
        creative_voice_quality_lane_enabled=bool(
            data.get(
                "creative_voice_quality_lane_enabled",
                defaults.creative_voice_quality_lane_enabled,
            )
        ),
        finitude_quality_lane_enabled=bool(
            data.get(
                "finitude_quality_lane_enabled",
                defaults.finitude_quality_lane_enabled,
            )
        ),
        current_pull_staleness_check_enabled=bool(
            data.get(
                "current_pull_staleness_check_enabled",
                defaults.current_pull_staleness_check_enabled,
            )
        ),
        current_pull_staleness_threshold=float(
            data.get(
                "current_pull_staleness_threshold",
                defaults.current_pull_staleness_threshold,
            )
        ),
        current_pull_staleness_check_interval_hours=int(
            data.get(
                "current_pull_staleness_check_interval_hours",
                defaults.current_pull_staleness_check_interval_hours,
            )
        ),
        music_accumulator_threshold_samples=int(
            data.get(
                "music_accumulator_threshold_samples",
                defaults.music_accumulator_threshold_samples,
            )
        ),
        music_accumulator_window_hours=int(
            data.get(
                "music_accumulator_window_hours",
                defaults.music_accumulator_window_hours,
            )
        ),
        music_accumulator_ratio_threshold=float(
            data.get(
                "music_accumulator_ratio_threshold",
                defaults.music_accumulator_ratio_threshold,
            )
        ),
        plan_todo_auto_create_enabled=bool(
            data.get(
                "plan_todo_auto_create_enabled",
                defaults.plan_todo_auto_create_enabled,
            )
        ),
        unconscious_modulation_enabled=bool(
            data.get(
                "unconscious_modulation_enabled",
                defaults.unconscious_modulation_enabled,
            )
        ),
        unconscious_modulation_temp_delta=float(
            data.get(
                "unconscious_modulation_temp_delta",
                defaults.unconscious_modulation_temp_delta,
            )
        ),
        unconscious_modulation_top_p_delta=float(
            data.get(
                "unconscious_modulation_top_p_delta",
                defaults.unconscious_modulation_top_p_delta,
            )
        ),
        unconscious_modulation_temp_floor=float(
            data.get(
                "unconscious_modulation_temp_floor",
                defaults.unconscious_modulation_temp_floor,
            )
        ),
        unconscious_modulation_temp_ceiling=float(
            data.get(
                "unconscious_modulation_temp_ceiling",
                defaults.unconscious_modulation_temp_ceiling,
            )
        ),
        unconscious_modulation_top_p_floor=float(
            data.get(
                "unconscious_modulation_top_p_floor",
                defaults.unconscious_modulation_top_p_floor,
            )
        ),
        unconscious_modulation_top_p_ceiling=float(
            data.get(
                "unconscious_modulation_top_p_ceiling",
                defaults.unconscious_modulation_top_p_ceiling,
            )
        ),
        tool_invention_enabled=bool(
            data.get(
                "tool_invention_enabled",
                defaults.tool_invention_enabled,
            )
        ),
        world_model_loop_enabled=bool(
            data.get(
                "world_model_loop_enabled",
                defaults.world_model_loop_enabled,
            )
        ),
        plan_revision_enabled=bool(
            data.get(
                "plan_revision_enabled",
                defaults.plan_revision_enabled,
            )
        ),
        curiosity_budget_enabled=bool(
            data.get(
                "curiosity_budget_enabled",
                defaults.curiosity_budget_enabled,
            )
        ),
        skill_chain_phase2_enabled=bool(
            data.get(
                "skill_chain_phase2_enabled",
                defaults.skill_chain_phase2_enabled,
            )
        ),
        meta_learning_enabled=bool(
            data.get(
                "meta_learning_enabled",
                defaults.meta_learning_enabled,
            )
        ),
        nudge_system_enabled=bool(
            data.get(
                "nudge_system_enabled",
                defaults.nudge_system_enabled,
            )
        ),
        longing_daemon_cadence_minutes=int(
            data.get("longing_daemon_cadence_minutes", defaults.longing_daemon_cadence_minutes)
        ),
        outreach_cooldown_minutes=int(
            data.get("outreach_cooldown_minutes", defaults.outreach_cooldown_minutes)
        ),
        longing_build_start_hours=float(
            data.get("longing_build_start_hours", defaults.longing_build_start_hours)
        ),
        longing_build_max_hours=float(
            data.get("longing_build_max_hours", defaults.longing_build_max_hours)
        ),
        relevance_mistral_model=str(
            data.get("relevance_mistral_model", defaults.relevance_mistral_model)
        ),
        relevance_mistral_timeout=int(
            data.get("relevance_mistral_timeout", defaults.relevance_mistral_timeout)
        ),
        relevance_nvidia_nim_model=str(
            data.get("relevance_nvidia_nim_model", defaults.relevance_nvidia_nim_model)
        ),
        relevance_nvidia_nim_timeout=int(
            data.get("relevance_nvidia_nim_timeout", defaults.relevance_nvidia_nim_timeout)
        ),
        relevance_openrouter_model=str(
            data.get("relevance_openrouter_model", defaults.relevance_openrouter_model)
        ),
        relevance_openrouter_timeout=int(
            data.get("relevance_openrouter_timeout", defaults.relevance_openrouter_timeout)
        ),
        relevance_sambanova_model=str(
            data.get("relevance_sambanova_model", defaults.relevance_sambanova_model)
        ),
        relevance_sambanova_timeout=int(
            data.get("relevance_sambanova_timeout", defaults.relevance_sambanova_timeout)
        ),
        recall_strong_threshold=float(data.get("recall_strong_threshold", defaults.recall_strong_threshold)),
        recall_weak_threshold=float(data.get("recall_weak_threshold", defaults.recall_weak_threshold)),
        recall_max_active=int(data.get("recall_max_active", defaults.recall_max_active)),
        recall_repetition_multiplier=float(data.get("recall_repetition_multiplier", defaults.recall_repetition_multiplier)),
        cognitive_state_assembly_enabled=bool(data.get("cognitive_state_assembly_enabled", defaults.cognitive_state_assembly_enabled)),
        emotion_decay_factor=float(data.get("emotion_decay_factor", defaults.emotion_decay_factor)),
        visible_ollama_num_ctx=int(data.get("visible_ollama_num_ctx", defaults.visible_ollama_num_ctx)),
        visible_ollama_num_predict=int(data.get("visible_ollama_num_predict", defaults.visible_ollama_num_predict)),
        visible_context_headroom_tokens=int(data.get("visible_context_headroom_tokens", defaults.visible_context_headroom_tokens)),
        context_compact_threshold_tokens=int(data.get("context_compact_threshold_tokens", defaults.context_compact_threshold_tokens)),
        context_run_compact_threshold_tokens=int(data.get("context_run_compact_threshold_tokens", defaults.context_run_compact_threshold_tokens)),
        context_keep_recent=int(data.get("context_keep_recent", defaults.context_keep_recent)),
        context_attention_budget_tokens=int(data.get("context_attention_budget_tokens", defaults.context_attention_budget_tokens)),
        context_attention_low_water_tokens=int(data.get("context_attention_low_water_tokens", defaults.context_attention_low_water_tokens)),
        context_compact_safety_fraction=float(data.get("context_compact_safety_fraction", defaults.context_compact_safety_fraction)),
        server_authoritative_runs=bool(data.get("server_authoritative_runs", defaults.server_authoritative_runs)),
        device_awareness_enabled=bool(data.get("device_awareness_enabled", defaults.device_awareness_enabled)),
        context_keep_recent_pairs=int(data.get("context_keep_recent_pairs", defaults.context_keep_recent_pairs)),
        jarvis_brain_enabled=bool(data.get("jarvis_brain_enabled", defaults.jarvis_brain_enabled)),
        jarvis_brain_summary_token_budget=int(data.get("jarvis_brain_summary_token_budget", defaults.jarvis_brain_summary_token_budget)),
        jarvis_brain_auto_inject_top_k=int(data.get("jarvis_brain_auto_inject_top_k", defaults.jarvis_brain_auto_inject_top_k)),
        jarvis_brain_auto_inject_threshold=float(data.get("jarvis_brain_auto_inject_threshold", defaults.jarvis_brain_auto_inject_threshold)),
        jarvis_brain_remember_per_turn_cap=int(data.get("jarvis_brain_remember_per_turn_cap", defaults.jarvis_brain_remember_per_turn_cap)),
        jarvis_brain_remember_per_day_cap=int(data.get("jarvis_brain_remember_per_day_cap", defaults.jarvis_brain_remember_per_day_cap)),
        jarvis_brain_auto_archive_salience_threshold=float(data.get("jarvis_brain_auto_archive_salience_threshold", defaults.jarvis_brain_auto_archive_salience_threshold)),
        jarvis_brain_auto_archive_days=int(data.get("jarvis_brain_auto_archive_days", defaults.jarvis_brain_auto_archive_days)),
        jarvis_brain_theme_consolidation_enabled=bool(data.get("jarvis_brain_theme_consolidation_enabled", defaults.jarvis_brain_theme_consolidation_enabled)),
        daemon_balancer_enabled=bool(data.get("daemon_balancer_enabled", defaults.daemon_balancer_enabled)),
        emotional_memory_min_anchors=int(data.get("emotional_memory_min_anchors", defaults.emotional_memory_min_anchors)),
        emotional_memory_retention_recent_days=int(data.get("emotional_memory_retention_recent_days", defaults.emotional_memory_retention_recent_days)),
        emotional_memory_retention_aging_days=int(data.get("emotional_memory_retention_aging_days", defaults.emotional_memory_retention_aging_days)),
        emotional_memory_significance_intensity=float(data.get("emotional_memory_significance_intensity", defaults.emotional_memory_significance_intensity)),
        emotional_memory_significance_outcome=float(data.get("emotional_memory_significance_outcome", defaults.emotional_memory_significance_outcome)),
        sensory_perception_bridge_enabled=bool(data.get("sensory_perception_bridge_enabled", defaults.sensory_perception_bridge_enabled)),
        sensory_perception_jaccard_high_threshold=float(data.get("sensory_perception_jaccard_high_threshold", defaults.sensory_perception_jaccard_high_threshold)),
        sensory_perception_jaccard_medium_threshold=float(data.get("sensory_perception_jaccard_medium_threshold", defaults.sensory_perception_jaccard_medium_threshold)),
        sensory_perception_jaccard_change_threshold=float(data.get("sensory_perception_jaccard_change_threshold", defaults.sensory_perception_jaccard_change_threshold)),
        sensory_perception_time_window_hours=int(data.get("sensory_perception_time_window_hours", defaults.sensory_perception_time_window_hours)),
        sensory_perception_time_window_days=int(data.get("sensory_perception_time_window_days", defaults.sensory_perception_time_window_days)),
        sensory_perception_min_baseline_records=int(data.get("sensory_perception_min_baseline_records", defaults.sensory_perception_min_baseline_records)),
        sensory_perception_recent_baseline_size=int(data.get("sensory_perception_recent_baseline_size", defaults.sensory_perception_recent_baseline_size)),
        self_repair_engine_enabled=bool(data.get("self_repair_engine_enabled", defaults.self_repair_engine_enabled)),
        self_repair_default_cooldown_seconds=int(data.get("self_repair_default_cooldown_seconds", defaults.self_repair_default_cooldown_seconds)),
        self_repair_default_max_attempts_per_window=int(data.get("self_repair_default_max_attempts_per_window", defaults.self_repair_default_max_attempts_per_window)),
        self_repair_default_window_seconds=int(data.get("self_repair_default_window_seconds", defaults.self_repair_default_window_seconds)),
        self_repair_default_auto_disable_after_escalations=int(data.get("self_repair_default_auto_disable_after_escalations", defaults.self_repair_default_auto_disable_after_escalations)),
        self_repair_default_auto_disable_window_hours=int(data.get("self_repair_default_auto_disable_window_hours", defaults.self_repair_default_auto_disable_window_hours)),
        prompt_affect_substrate_enabled=bool(data.get("prompt_affect_substrate_enabled", defaults.prompt_affect_substrate_enabled)),
        prompt_affect_tone_hints_enabled=bool(data.get("prompt_affect_tone_hints_enabled", defaults.prompt_affect_tone_hints_enabled)),
        prompt_agreement_streak_enabled=bool(data.get("prompt_agreement_streak_enabled", defaults.prompt_agreement_streak_enabled)),
        prompt_emotion_signal_section_enabled=bool(data.get("prompt_emotion_signal_section_enabled", defaults.prompt_emotion_signal_section_enabled)),
        prompt_experience_substrate_enabled=bool(data.get("prompt_experience_substrate_enabled", defaults.prompt_experience_substrate_enabled)),
        prompt_proactive_outbound_substrate_enabled=bool(data.get("prompt_proactive_outbound_substrate_enabled", defaults.prompt_proactive_outbound_substrate_enabled)),
        heartbeat_active_chat_gate_enabled=bool(data.get("heartbeat_active_chat_gate_enabled", defaults.heartbeat_active_chat_gate_enabled)),
        heartbeat_active_chat_gate_minutes=int(data.get("heartbeat_active_chat_gate_minutes", defaults.heartbeat_active_chat_gate_minutes)),
        emotion_concepts_tone_injection_enabled=bool(data.get("emotion_concepts_tone_injection_enabled", defaults.emotion_concepts_tone_injection_enabled)),
        emotion_concepts_perception_focus_enabled=bool(data.get("emotion_concepts_perception_focus_enabled", defaults.emotion_concepts_perception_focus_enabled)),
        concept_baseline_tracker_enabled=bool(data.get("concept_baseline_tracker_enabled", defaults.concept_baseline_tracker_enabled)),
        emotion_concepts_tone_intensity_threshold=float(data.get("emotion_concepts_tone_intensity_threshold", defaults.emotion_concepts_tone_intensity_threshold)),
        emotion_concepts_tone_max_hints=int(data.get("emotion_concepts_tone_max_hints", defaults.emotion_concepts_tone_max_hints)),
        emotion_concepts_perception_max_foci=int(data.get("emotion_concepts_perception_max_foci", defaults.emotion_concepts_perception_max_foci)),
        concept_baseline_drift_min_sustained_days=int(data.get("concept_baseline_drift_min_sustained_days", defaults.concept_baseline_drift_min_sustained_days)),
        concept_baseline_drift_min_confidence=float(data.get("concept_baseline_drift_min_confidence", defaults.concept_baseline_drift_min_confidence)),
        emotion_concepts_default_trigger_cooldown_seconds=int(data.get("emotion_concepts_default_trigger_cooldown_seconds", defaults.emotion_concepts_default_trigger_cooldown_seconds)),
        counterfactual_engine_enabled=bool(data.get("counterfactual_engine_enabled", defaults.counterfactual_engine_enabled)),
        counterfactual_engine_interval_seconds=int(data.get("counterfactual_engine_interval_seconds", defaults.counterfactual_engine_interval_seconds)),
        counterfactual_engine_lookback_minutes=int(data.get("counterfactual_engine_lookback_minutes", defaults.counterfactual_engine_lookback_minutes)),
        counterfactual_engine_promotion_threshold=float(data.get("counterfactual_engine_promotion_threshold", defaults.counterfactual_engine_promotion_threshold)),
        counterfactual_engine_phase2_llm_enabled=bool(data.get("counterfactual_engine_phase2_llm_enabled", defaults.counterfactual_engine_phase2_llm_enabled)),
        counterfactual_engine_phase2_max_per_cycle=int(data.get("counterfactual_engine_phase2_max_per_cycle", defaults.counterfactual_engine_phase2_max_per_cycle)),
        agent_step_reasoning_replay_enabled=bool(data.get("agent_step_reasoning_replay_enabled", defaults.agent_step_reasoning_replay_enabled)),
        agent_step_env_block_enabled=bool(data.get("agent_step_env_block_enabled", defaults.agent_step_env_block_enabled)),
        agent_step_cache_contract_enabled=bool(data.get("agent_step_cache_contract_enabled", defaults.agent_step_cache_contract_enabled)),
        agent_step_cache_split_enabled=bool(data.get("agent_step_cache_split_enabled", defaults.agent_step_cache_split_enabled)),
        agent_step_volatile_prepend_enabled=bool(data.get("agent_step_volatile_prepend_enabled", defaults.agent_step_volatile_prepend_enabled)),
        agent_turn_absorb_enabled=bool(data.get("agent_turn_absorb_enabled", defaults.agent_turn_absorb_enabled)),
        agent_live_broadcast_enabled=bool(data.get("agent_live_broadcast_enabled", defaults.agent_live_broadcast_enabled)),
        agent_live_follow_tokens_enabled=bool(data.get("agent_live_follow_tokens_enabled", defaults.agent_live_follow_tokens_enabled)),
        agent_step_harness_contract_enabled=bool(data.get("agent_step_harness_contract_enabled", defaults.agent_step_harness_contract_enabled)),
        extra={key: value for key, value in data.items() if key not in KNOWN_FIELDS},
    )


def update_visible_execution_settings(
    *,
    visible_model_provider: str | None = None,
    visible_model_name: str | None = None,
    visible_auth_profile: str | None = None,
) -> RuntimeSettings:
    settings = load_settings()
    previous_provider = settings.visible_model_provider
    previous_model = settings.visible_model_name

    updates: dict[str, Any] = {}
    if visible_model_provider is not None:
        settings.visible_model_provider = visible_model_provider
        updates["visible_model_provider"] = visible_model_provider
    if visible_model_name is not None:
        settings.visible_model_name = visible_model_name
        updates["visible_model_name"] = visible_model_name
    if visible_auth_profile is not None:
        settings.visible_auth_profile = visible_auth_profile
        updates["visible_auth_profile"] = visible_auth_profile

    # Safe merge write — reads raw dict, applies only the delta, atomic rename,
    # auto-backup. Prevents accidental reset of other runtime.json keys.
    from core.runtime.runtime_json_io import write_runtime_merged
    if updates:
        write_runtime_merged(updates)
    try:
        from core.services.finitude_runtime import record_visible_model_transition

        record_visible_model_transition(
            previous_provider=previous_provider,
            previous_model=previous_model,
            new_provider=settings.visible_model_provider,
            new_model=settings.visible_model_name,
        )
    except Exception:
        pass
    return settings
