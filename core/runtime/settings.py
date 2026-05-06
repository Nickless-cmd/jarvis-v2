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
    heartbeat_model_provider: str = ""
    heartbeat_model_name: str = ""
    heartbeat_auth_profile: str = ""
    heartbeat_local_only: bool = False
    relevance_model_name: str = "glm-5.1:cloud"
    # Associative recall thresholds
    recall_strong_threshold: float = 0.7
    recall_weak_threshold: float = 0.3
    recall_max_active: int = 5
    recall_repetition_multiplier: float = 1.5
    # Cognitive state assembly toggle
    cognitive_state_assembly_enabled: bool = True
    # Cognitive state cache TTL (seconds). 0 = disabled.
    cognitive_state_cache_ttl: int = 120
    # Cognitive state cache on/off toggle (independent of TTL).
    cognitive_state_cache_enabled: bool = True
    # Bounded relevance/memory-selection LLM backend.
    # "opencode"      = OpenCode Zen free models via cheap lane (real timeouts).
    # "ollamafreeapi" = public cloud (free models, timeout kwarg is silently dropped).
    # "ollama"        = local LXC GPU (slower, private-safe).
    relevance_backend_primary: str = "opencode"
    relevance_opencode_model: str = "minimax-m2.5-free"
    relevance_opencode_timeout: int = 6
    relevance_ollamafreeapi_model: str = "gpt-oss:20b"
    relevance_ollamafreeapi_timeout: int = 6
    # Memory scoring backend (associative recall — score 15 candidate memories
    # against current context). Public-safe: only sends 200-char user-message
    # snippet + 80-char memory narrative snippets, no identity context.
    # "ollamafreeapi" = cloud (~0.7-1.5s typical), "ollama" = local LXC fallback.
    memory_scoring_primary: str = "ollamafreeapi"
    memory_scoring_ollamafreeapi_model: str = "gpt-oss:20b"
    memory_scoring_ollamafreeapi_timeout: int = 2
    memory_scoring_ollama_timeout: int = 3
    # Generative autonomy (Spor-1: longing-toward-Bjorn). When False, the
    # longing daemon emits no signals and the outreach composer refuses to
    # send. The pressure-accumulator pipeline (built 2026-04-29 as the
    # foundation) keeps running for observability but produces no user-
    # facing actions while this is False. Default off — opt-in.
    generative_autonomy_enabled: bool = False
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
    # Context compact thresholds. Bumped from 40k/60k now that visible lane
    # runs deepseek-v4-flash (1M context) with num_ctx=256k. Auto-compaction
    # at 40k was a holdover from when the visible model had a tight 64k
    # context window — premature now and was forcing summarization mid-run.
    context_compact_threshold_tokens: int = 200_000
    context_run_compact_threshold_tokens: int = 240_000
    context_keep_recent: int = 20
    context_keep_recent_pairs: int = 4
    # Jarvis Brain — kurateret vidensjournal (sektion 8.3 i spec).
    # When False, recall paths no-op and remember_this rejects with
    # "feature disabled". On-disk entries are preserved.
    jarvis_brain_enabled: bool = True
    # Token budget for always-on summary section in prompt_contract.
    jarvis_brain_summary_token_budget: int = 350
    # Number of fakta auto-injected per turn.
    jarvis_brain_auto_inject_top_k: int = 3
    # Combined cosine+salience threshold below which auto-inject skips.
    jarvis_brain_auto_inject_threshold: float = 0.55
    # remember_this rate caps (per-turn / per-day).
    jarvis_brain_remember_per_turn_cap: int = 5
    jarvis_brain_remember_per_day_cap: int = 20
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
    # Tool router (added 2026-05-06)
    tool_router_enabled: bool = True
    tool_router_threshold: float = 0.40  # 0.55 caused 100% fallback on validation set; nomic-embed cross-language similarity is weaker than expected. Daemon will tune adaptively.
    tool_router_always_core_size: int = 70
    tool_router_k_embeddings: int = 30
    tool_router_embedding_model: str = "nomic-embed-text"
    tool_router_embedding_provider: str = "ollama"
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
            "heartbeat_auth_profile": self.heartbeat_auth_profile,
            "heartbeat_local_only": self.heartbeat_local_only,
            "relevance_model_name": self.relevance_model_name,
            "recall_strong_threshold": self.recall_strong_threshold,
            "recall_weak_threshold": self.recall_weak_threshold,
            "recall_max_active": self.recall_max_active,
            "recall_repetition_multiplier": self.recall_repetition_multiplier,
            "cognitive_state_assembly_enabled": self.cognitive_state_assembly_enabled,
            "emotion_decay_factor": self.emotion_decay_factor,
            "context_compact_threshold_tokens": self.context_compact_threshold_tokens,
            "context_run_compact_threshold_tokens": self.context_run_compact_threshold_tokens,
            "context_keep_recent": self.context_keep_recent,
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
            "emotion_concepts_tone_injection_enabled": self.emotion_concepts_tone_injection_enabled,
            "emotion_concepts_perception_focus_enabled": self.emotion_concepts_perception_focus_enabled,
            "concept_baseline_tracker_enabled": self.concept_baseline_tracker_enabled,
            "emotion_concepts_tone_intensity_threshold": self.emotion_concepts_tone_intensity_threshold,
            "emotion_concepts_tone_max_hints": self.emotion_concepts_tone_max_hints,
            "emotion_concepts_perception_max_foci": self.emotion_concepts_perception_max_foci,
            "concept_baseline_drift_min_sustained_days": self.concept_baseline_drift_min_sustained_days,
            "concept_baseline_drift_min_confidence": self.concept_baseline_drift_min_confidence,
            "emotion_concepts_default_trigger_cooldown_seconds": self.emotion_concepts_default_trigger_cooldown_seconds,
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
        context_compact_threshold_tokens=int(data.get("context_compact_threshold_tokens", defaults.context_compact_threshold_tokens)),
        context_run_compact_threshold_tokens=int(data.get("context_run_compact_threshold_tokens", defaults.context_run_compact_threshold_tokens)),
        context_keep_recent=int(data.get("context_keep_recent", defaults.context_keep_recent)),
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
        emotion_concepts_tone_injection_enabled=bool(data.get("emotion_concepts_tone_injection_enabled", defaults.emotion_concepts_tone_injection_enabled)),
        emotion_concepts_perception_focus_enabled=bool(data.get("emotion_concepts_perception_focus_enabled", defaults.emotion_concepts_perception_focus_enabled)),
        concept_baseline_tracker_enabled=bool(data.get("concept_baseline_tracker_enabled", defaults.concept_baseline_tracker_enabled)),
        emotion_concepts_tone_intensity_threshold=float(data.get("emotion_concepts_tone_intensity_threshold", defaults.emotion_concepts_tone_intensity_threshold)),
        emotion_concepts_tone_max_hints=int(data.get("emotion_concepts_tone_max_hints", defaults.emotion_concepts_tone_max_hints)),
        emotion_concepts_perception_max_foci=int(data.get("emotion_concepts_perception_max_foci", defaults.emotion_concepts_perception_max_foci)),
        concept_baseline_drift_min_sustained_days=int(data.get("concept_baseline_drift_min_sustained_days", defaults.concept_baseline_drift_min_sustained_days)),
        concept_baseline_drift_min_confidence=float(data.get("concept_baseline_drift_min_confidence", defaults.concept_baseline_drift_min_confidence)),
        emotion_concepts_default_trigger_cooldown_seconds=int(data.get("emotion_concepts_default_trigger_cooldown_seconds", defaults.emotion_concepts_default_trigger_cooldown_seconds)),
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
