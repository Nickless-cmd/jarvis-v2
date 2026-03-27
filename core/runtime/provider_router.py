from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from core.auth.profiles import (
    provider_has_real_credentials,
    save_provider_credentials,
)
from core.runtime.config import PROVIDER_ROUTER_FILE
from core.runtime.settings import load_settings, update_visible_execution_settings

_SIMPLE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9:-]{0,63}$")


def load_provider_router_registry() -> dict[str, object]:
    if not PROVIDER_ROUTER_FILE.exists():
        return _default_registry()
    data = json.loads(PROVIDER_ROUTER_FILE.read_text(encoding="utf-8"))
    providers = data.get("providers")
    models = data.get("models")
    return {
        "providers": providers if isinstance(providers, list) else [],
        "models": models if isinstance(models, list) else [],
    }


def configure_provider_router_entry(
    *,
    provider: str,
    model: str,
    auth_mode: str,
    auth_profile: str,
    base_url: str,
    api_key: str,
    lane: str,
    set_visible: bool,
) -> dict[str, object]:
    provider_id = _normalize_simple_id(provider, label="provider")
    model_name = (model or "").strip()
    if not model_name:
        raise ValueError("model must not be empty")
    auth_mode_value = _normalize_auth_mode(auth_mode)
    profile_name = _normalize_profile(auth_profile)
    base_url_value = (base_url or "").strip()
    lane_value = _normalize_lane(lane)

    registry = load_provider_router_registry()
    providers = list(registry.get("providers") or [])
    models = list(registry.get("models") or [])
    updated_at = _now()

    provider_entry = {
        "provider": provider_id,
        "auth_mode": auth_mode_value,
        "auth_profile": profile_name,
        "base_url": base_url_value,
        "enabled": True,
        "updated_at": updated_at,
    }
    _upsert_provider(providers, provider_entry)

    model_entry = {
        "provider": provider_id,
        "model": model_name,
        "lane": lane_value,
        "enabled": True,
        "updated_at": updated_at,
    }
    _upsert_model(models, model_entry)

    registry = {
        "providers": providers,
        "models": models,
    }
    PROVIDER_ROUTER_FILE.write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    credentials_saved = False
    if api_key.strip():
        save_provider_credentials(
            profile=profile_name or "default",
            provider=provider_id,
            credentials={"api_key": api_key.strip()},
        )
        credentials_saved = True

    visible_updated = False
    if set_visible:
        settings = load_settings()
        if provider_id not in {"phase1-runtime", "openai"}:
            raise ValueError(
                "set_visible currently supports only phase1-runtime or openai"
            )
        update_visible_execution_settings(
            visible_model_provider=provider_id,
            visible_model_name=model_name,
            visible_auth_profile=profile_name or settings.visible_auth_profile,
        )
        visible_updated = True

    return {
        "provider": provider_id,
        "model": model_name,
        "auth_mode": auth_mode_value,
        "auth_profile": profile_name,
        "base_url": base_url_value,
        "lane": lane_value,
        "credentials_saved": credentials_saved,
        "visible_updated": visible_updated,
        "config_path": str(PROVIDER_ROUTER_FILE),
    }


def provider_router_summary() -> dict[str, object]:
    registry = load_provider_router_registry()
    settings = load_settings()
    providers = [_provider_surface(item) for item in registry.get("providers") or []]
    models = [_model_surface(item) for item in registry.get("models") or []]
    return {
        "active": bool(providers or models),
        "source": "config.provider-router+runtime.settings+auth.profiles",
        "config_path": str(PROVIDER_ROUTER_FILE),
        "provider_count": len(providers),
        "model_count": len(models),
        "main_agent_target": main_agent_target(),
        "main_agent_selection": main_agent_selection(),
        "providers": providers[:8],
        "models": models[:12],
        "router": {
            "visible_primary": {
                "provider": settings.visible_model_provider,
                "model": settings.visible_model_name,
                "auth_profile": settings.visible_auth_profile,
            },
            "visible_fallback": {
                "provider": "phase1-runtime",
                "model": "visible-placeholder",
                "auth_profile": "",
            },
        },
        "lane_targets": provider_router_lane_targets(),
    }


def main_agent_target() -> dict[str, object]:
    target = resolve_provider_router_target(lane="visible")
    return {
        "active": bool(target.get("active")),
        "target_id": (
            "main-agent-target:"
            f"{str(target.get('provider') or 'none').strip()}:{str(target.get('model') or 'none').strip()}"
        ),
        "source": "runtime.settings+provider-router-registry",
        "selection_authority": "runtime.settings",
        "provider": target.get("provider"),
        "model": target.get("model"),
        "auth_profile": target.get("auth_profile"),
        "auth_mode": target.get("auth_mode"),
        "base_url": target.get("base_url"),
        "credentials_ready": bool(target.get("credentials_ready")),
        "fallback_provider": target.get("fallback_provider"),
        "fallback_model": target.get("fallback_model"),
    }


def main_agent_selection() -> dict[str, object]:
    registry = load_provider_router_registry()
    current = main_agent_target()
    return {
        "active": True,
        "source": "runtime.settings+provider-router-registry",
        "selection_authority": "runtime.settings",
        "current_provider": current.get("provider"),
        "current_model": current.get("model"),
        "current_auth_profile": current.get("auth_profile"),
        "available_configured_targets": _configured_main_agent_targets(registry=registry),
        "confidence": "high",
    }


def select_main_agent_target(
    *,
    provider: str,
    model: str,
    auth_profile: str | None = None,
) -> dict[str, object]:
    provider_id = _normalize_simple_id(provider, label="provider")
    model_name = (model or "").strip()
    if not model_name:
        raise ValueError("model must not be empty")
    profile_name = _normalize_profile(auth_profile or "")
    registry = load_provider_router_registry()

    configured_target = _configured_target_match(
        registry=registry,
        provider=provider_id,
        model=model_name,
    )
    if configured_target is None:
        raise ValueError(
            "main agent target must exist in configured provider-router targets"
        )

    configured_profile = str(configured_target.get("auth_profile") or "").strip()
    if profile_name and configured_profile and profile_name != configured_profile:
        raise ValueError(
            "auth_profile must match the configured provider-router target profile"
        )

    settings = update_visible_execution_settings(
        visible_model_provider=provider_id,
        visible_model_name=model_name,
        visible_auth_profile=profile_name or configured_profile,
    )
    return {
        "provider": settings.visible_model_provider,
        "model": settings.visible_model_name,
        "auth_profile": settings.visible_auth_profile,
        "selection_authority": "runtime.settings",
    }


def resolve_provider_router_target(*, lane: str) -> dict[str, object]:
    normalized_lane = _normalize_lane(lane)
    registry = load_provider_router_registry()
    settings = load_settings()

    if normalized_lane == "visible":
        return {
            "active": True,
            "lane": normalized_lane,
            "source": "runtime.settings",
            "provider": settings.visible_model_provider,
            "model": settings.visible_model_name,
            "auth_profile": settings.visible_auth_profile,
            "auth_mode": _provider_auth_mode(
                provider=settings.visible_model_provider,
                registry=registry,
            ),
            "base_url": _provider_base_url(
                provider=settings.visible_model_provider,
                registry=registry,
            ),
            "credentials_ready": _credentials_ready(
                provider=settings.visible_model_provider,
                auth_profile=settings.visible_auth_profile,
            ),
            "fallback_provider": "phase1-runtime",
            "fallback_model": "visible-placeholder",
        }

    model_entry = _latest_model_for_lane(registry=registry, lane=normalized_lane)
    if not model_entry:
        return {
            "active": False,
            "lane": normalized_lane,
            "source": "provider-router-registry",
            "provider": None,
            "model": None,
            "auth_profile": None,
            "auth_mode": None,
            "base_url": None,
            "credentials_ready": False,
            "fallback_provider": None,
            "fallback_model": None,
        }

    provider = str(model_entry.get("provider") or "").strip()
    provider_entry = _provider_entry(registry=registry, provider=provider) or {}
    auth_profile = str(provider_entry.get("auth_profile") or "").strip()
    return {
        "active": True,
        "lane": normalized_lane,
        "source": "provider-router-registry",
        "provider": provider,
        "model": str(model_entry.get("model") or "").strip(),
        "auth_profile": auth_profile,
        "auth_mode": str(provider_entry.get("auth_mode") or "").strip(),
        "base_url": str(provider_entry.get("base_url") or "").strip(),
        "credentials_ready": _credentials_ready(
            provider=provider,
            auth_profile=auth_profile,
        ),
        "fallback_provider": None,
        "fallback_model": None,
    }


def provider_router_lane_targets() -> dict[str, dict[str, object]]:
    lanes = ["visible", "cheap", "coding", "premium", "local"]
    return {lane: resolve_provider_router_target(lane=lane) for lane in lanes}


def _provider_surface(item: dict[str, Any]) -> dict[str, object]:
    provider = str(item.get("provider") or "").strip()
    auth_profile = str(item.get("auth_profile") or "").strip()
    return {
        "provider": provider,
        "auth_mode": str(item.get("auth_mode") or "").strip(),
        "auth_profile": auth_profile,
        "base_url": str(item.get("base_url") or "").strip(),
        "enabled": bool(item.get("enabled", True)),
        "credentials_ready": (
            provider_has_real_credentials(profile=auth_profile, provider=provider)
            if provider and auth_profile
            else False
        ),
        "updated_at": item.get("updated_at"),
    }


def _model_surface(item: dict[str, Any]) -> dict[str, object]:
    return {
        "provider": str(item.get("provider") or "").strip(),
        "model": str(item.get("model") or "").strip(),
        "lane": str(item.get("lane") or "").strip(),
        "enabled": bool(item.get("enabled", True)),
        "updated_at": item.get("updated_at"),
    }


def _latest_model_for_lane(
    *, registry: dict[str, object], lane: str
) -> dict[str, object] | None:
    lane_models = [
        item
        for item in registry.get("models") or []
        if bool(item.get("enabled", True))
        and str(item.get("lane") or "").strip() == lane
        and str(item.get("provider") or "").strip()
        and str(item.get("model") or "").strip()
    ]
    if not lane_models:
        return None
    lane_models.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    return lane_models[0]


def _configured_main_agent_targets(
    *, registry: dict[str, object]
) -> list[dict[str, object]]:
    targets: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()

    for item in registry.get("models") or []:
        if not bool(item.get("enabled", True)):
            continue
        provider = str(item.get("provider") or "").strip()
        model = str(item.get("model") or "").strip()
        if not provider or not model:
            continue
        key = (provider, model)
        if key in seen:
            continue
        seen.add(key)
        provider_entry = _provider_entry(registry=registry, provider=provider) or {}
        auth_profile = str(provider_entry.get("auth_profile") or "").strip()
        targets.append(
            {
                "provider": provider,
                "model": model,
                "auth_mode": str(provider_entry.get("auth_mode") or "").strip() or None,
                "auth_profile": auth_profile or None,
                "base_url": str(provider_entry.get("base_url") or "").strip() or None,
                "credentials_ready": _credentials_ready(
                    provider=provider,
                    auth_profile=auth_profile,
                ),
                "readiness_hint": _readiness_hint(
                    provider=provider,
                    auth_mode=str(provider_entry.get("auth_mode") or "").strip(),
                    auth_profile=auth_profile,
                ),
            }
        )

    targets.sort(key=lambda item: (str(item["provider"]), str(item["model"])))
    return targets[:12]


def _configured_target_match(
    *, registry: dict[str, object], provider: str, model: str
) -> dict[str, object] | None:
    for item in _configured_main_agent_targets(registry=registry):
        if str(item.get("provider") or "").strip() != provider:
            continue
        if str(item.get("model") or "").strip() != model:
            continue
        return item
    return None


def _readiness_hint(*, provider: str, auth_mode: str, auth_profile: str) -> str:
    normalized_auth_mode = (auth_mode or "").strip()
    if provider == "phase1-runtime":
        return "configured"
    if _credentials_ready(provider=provider, auth_profile=auth_profile):
        return "auth-ready"
    if normalized_auth_mode in {"api-key", "oauth"}:
        return "auth-required"
    if normalized_auth_mode in {"none", ""}:
        return "configured"
    return "unknown"


def _provider_entry(*, registry: dict[str, object], provider: str) -> dict[str, object] | None:
    for item in registry.get("providers") or []:
        if not bool(item.get("enabled", True)):
            continue
        if str(item.get("provider") or "").strip() == provider:
            return item
    return None


def _provider_auth_mode(*, provider: str, registry: dict[str, object]) -> str | None:
    entry = _provider_entry(registry=registry, provider=provider)
    if not entry:
        return None
    return str(entry.get("auth_mode") or "").strip() or None


def _provider_base_url(*, provider: str, registry: dict[str, object]) -> str | None:
    entry = _provider_entry(registry=registry, provider=provider)
    if not entry:
        return None
    return str(entry.get("base_url") or "").strip() or None


def _credentials_ready(*, provider: str, auth_profile: str) -> bool:
    if not provider:
        return False
    if provider == "phase1-runtime":
        return True
    if not auth_profile:
        return False
    return provider_has_real_credentials(profile=auth_profile, provider=provider)


def _upsert_provider(items: list[dict[str, object]], entry: dict[str, object]) -> None:
    provider = str(entry["provider"])
    for index, item in enumerate(items):
        if str(item.get("provider") or "") == provider:
            items[index] = entry
            return
    items.append(entry)


def _upsert_model(items: list[dict[str, object]], entry: dict[str, object]) -> None:
    provider = str(entry["provider"])
    model = str(entry["model"])
    for index, item in enumerate(items):
        if (
            str(item.get("provider") or "") == provider
            and str(item.get("model") or "") == model
        ):
            items[index] = entry
            return
    items.append(entry)


def _default_registry() -> dict[str, object]:
    return {
        "providers": [],
        "models": [],
    }


def _normalize_simple_id(value: str, *, label: str) -> str:
    normalized = (value or "").strip().lower()
    if not _SIMPLE_ID_RE.fullmatch(normalized):
        raise ValueError(f"{label} must be a simple lowercase identifier")
    return normalized


def _normalize_auth_mode(value: str) -> str:
    normalized = (value or "none").strip().lower()
    if normalized not in {"none", "api-key", "oauth"}:
        raise ValueError("auth_mode must be one of: none, api-key, oauth")
    return normalized


def _normalize_profile(value: str) -> str:
    normalized = (value or "").strip()
    if any(part in normalized for part in ("/", "\\")):
        raise ValueError("auth_profile must be a simple profile name")
    return normalized


def _normalize_lane(value: str) -> str:
    normalized = (value or "visible").strip().lower()
    if normalized not in {"visible", "cheap", "coding", "premium", "local"}:
        return "visible"
    return normalized


def _now() -> str:
    return datetime.now(UTC).isoformat()
