from __future__ import annotations

import json
from dataclasses import dataclass

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
    # Emotion decay
    emotion_decay_factor: float = 0.97
    # Context compact thresholds
    context_compact_threshold_tokens: int = 40_000
    context_run_compact_threshold_tokens: int = 60_000
    context_keep_recent: int = 20
    context_keep_recent_pairs: int = 4

    def to_dict(self) -> dict[str, str | int | bool]:
        return {
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
        }


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
    )


def update_visible_execution_settings(
    *,
    visible_model_provider: str | None = None,
    visible_model_name: str | None = None,
    visible_auth_profile: str | None = None,
) -> RuntimeSettings:
    settings = load_settings()

    if visible_model_provider is not None:
        settings.visible_model_provider = visible_model_provider
    if visible_model_name is not None:
        settings.visible_model_name = visible_model_name
    if visible_auth_profile is not None:
        settings.visible_auth_profile = visible_auth_profile

    SETTINGS_FILE.write_text(
        json.dumps(settings.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return settings
