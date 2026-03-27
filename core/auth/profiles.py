from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.config import AUTH_PROFILES_DIR

_PROVIDER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9:-]{0,63}$")


def ensure_auth_profile(profile: str) -> Path:
    profile_dir = _profile_dir(profile)
    providers_dir = profile_dir / "providers"
    providers_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = profile_dir / "profile.json"
    if not manifest_path.exists():
        manifest_path.write_text(
            json.dumps(
                {
                    "profile": profile,
                    "created_at": _now(),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return profile_dir


def list_auth_profiles() -> list[dict[str, str]]:
    if not AUTH_PROFILES_DIR.exists():
        return []

    items: list[dict[str, str]] = []
    for profile_dir in sorted(AUTH_PROFILES_DIR.iterdir()):
        if not profile_dir.is_dir():
            continue
        manifest = _read_json(profile_dir / "profile.json")
        items.append(
            {
                "profile": str(manifest.get("profile", profile_dir.name)),
                "created_at": str(manifest.get("created_at", "")),
            }
        )
    return items


def save_provider_credentials(
    *,
    profile: str,
    provider: str,
    credentials: dict[str, Any],
) -> dict[str, Any]:
    _validate_provider(provider)
    profile_dir = ensure_auth_profile(profile)
    provider_dir = profile_dir / "providers" / provider
    provider_dir.mkdir(parents=True, exist_ok=True)

    secret_path = provider_dir / "credentials.json"
    secret_path.write_text(
        json.dumps(credentials, indent=2) + "\n",
        encoding="utf-8",
    )

    state = {
        "provider": provider,
        "profile": profile,
        "status": "active",
        "credentials_path": str(secret_path),
        "created_at": _existing_or_now(provider_dir / "state.json", "created_at"),
        "updated_at": _now(),
        "revoked_at": None,
    }
    (provider_dir / "state.json").write_text(
        json.dumps(state, indent=2) + "\n",
        encoding="utf-8",
    )
    return state


def get_provider_state(*, profile: str, provider: str) -> dict[str, Any] | None:
    _validate_provider(provider)
    state_path = _profile_dir(profile) / "providers" / provider / "state.json"
    if not state_path.exists():
        return None
    return _read_json(state_path)


def get_provider_state_view(*, profile: str, provider: str) -> dict[str, Any] | None:
    state = get_provider_state(profile=profile, provider=provider)
    if state is None:
        return None
    view = dict(state)
    view["has_real_credentials"] = provider_has_real_credentials(
        profile=profile,
        provider=provider,
    )
    view["auth_material_kind"] = get_provider_auth_material_kind(
        profile=profile,
        provider=provider,
    )
    view["oauth_state"] = get_provider_oauth_state(
        profile=profile,
        provider=provider,
    )
    view["launch_result_state"] = get_provider_launch_result_state(
        profile=profile,
        provider=provider,
    )
    view["launch_freshness"] = get_provider_launch_freshness(
        profile=profile,
        provider=provider,
    )
    view["callback_validation_state"] = get_provider_callback_validation_state(
        profile=profile,
        provider=provider,
    )
    view["exchange_readiness"] = get_provider_exchange_readiness(
        profile=profile,
        provider=provider,
    )
    view["callback_intent_consistency"] = get_provider_callback_intent_consistency(
        profile=profile,
        provider=provider,
    )
    credentials_path = Path(str(state.get("credentials_path") or ""))
    if credentials_path.exists():
        credentials = _read_json(credentials_path)
        if credentials.get("oauth_intent_id"):
            view["oauth_intent_id"] = str(credentials.get("oauth_intent_id"))
        if credentials.get("oauth_stub_id"):
            view["oauth_stub_id"] = str(credentials.get("oauth_stub_id"))
        if credentials.get("oauth_started_at"):
            view["oauth_started_at"] = str(credentials.get("oauth_started_at"))
        if credentials.get("oauth_launch_url"):
            view["oauth_launch_url"] = str(credentials.get("oauth_launch_url"))
        if credentials.get("oauth_launch_mode"):
            view["oauth_launch_mode"] = str(credentials.get("oauth_launch_mode"))
        if credentials.get("oauth_launch_started_at"):
            view["oauth_launch_started_at"] = str(credentials.get("oauth_launch_started_at"))
        if credentials.get("browser_launch_attempted_at"):
            view["browser_launch_attempted_at"] = str(
                credentials.get("browser_launch_attempted_at")
            )
        if credentials.get("browser_launch_method"):
            view["browser_launch_method"] = str(credentials.get("browser_launch_method"))
        if credentials.get("browser_launch_result"):
            view["browser_launch_result"] = str(credentials.get("browser_launch_result"))
        if "browser_launched" in credentials:
            view["browser_launched"] = bool(credentials.get("browser_launched"))
        if credentials.get("oauth_callback_received_at"):
            view["oauth_callback_received_at"] = str(
                credentials.get("oauth_callback_received_at")
            )
        if credentials.get("oauth_callback_url"):
            view["oauth_callback_url"] = str(credentials.get("oauth_callback_url"))
        if "oauth_callback_has_code" in credentials:
            view["oauth_callback_has_code"] = bool(credentials.get("oauth_callback_has_code"))
        if "oauth_callback_has_state" in credentials:
            view["oauth_callback_has_state"] = bool(credentials.get("oauth_callback_has_state"))
        if credentials.get("oauth_callback_param_keys"):
            view["oauth_callback_param_keys"] = list(credentials.get("oauth_callback_param_keys"))
    return view


def get_provider_credentials(
    *, profile: str, provider: str
) -> dict[str, Any] | None:
    state = get_provider_state(profile=profile, provider=provider)
    if state is None:
        return None

    credentials_path = Path(str(state.get("credentials_path") or ""))
    if not credentials_path.exists():
        return None
    return _read_json(credentials_path)


def provider_has_real_credentials(*, profile: str, provider: str) -> bool:
    credentials = get_provider_credentials(profile=profile, provider=provider)
    if not credentials:
        return False

    if credentials.get("real_oauth") is False:
        return False

    if any(
        bool(credentials.get(flag))
        for flag in (
            "placeholder",
            "oauth_stub",
            "oauth_launch_stub",
            "oauth_launch_intent",
            "oauth_callback_stub",
        )
    ):
        return False

    api_key = str(credentials.get("api_key") or "").strip()
    access_token = str(credentials.get("access_token") or "").strip()
    refresh_token = str(credentials.get("refresh_token") or "").strip()
    return bool(api_key or access_token or refresh_token)


def get_provider_auth_material_kind(*, profile: str, provider: str) -> str:
    state = get_provider_state(profile=profile, provider=provider)
    if state is None:
        return "missing"

    status = str(state.get("status") or "").strip()
    if status == "revoked":
        return "revoked"
    if status != "active":
        return "missing"

    credentials_path = Path(str(state.get("credentials_path") or ""))
    if not credentials_path.exists():
        return "missing"

    credentials = _read_json(credentials_path)
    if provider_has_real_credentials(profile=profile, provider=provider):
        return "real"
    if bool(credentials.get("oauth_callback_stub")):
        return "oauth-callback-stub"
    if bool(credentials.get("oauth_launch_intent")):
        return "oauth-launch-intent"
    if bool(credentials.get("oauth_launch_stub")):
        return "oauth-launch-stub"
    if bool(credentials.get("oauth_stub")):
        return "oauth-stub"
    if bool(credentials.get("placeholder")):
        return "placeholder"
    if credentials.get("real_oauth") is False:
        return "placeholder"
    return "real"


def get_provider_oauth_state(*, profile: str, provider: str) -> str:
    state = get_provider_state(profile=profile, provider=provider)
    if state is None:
        return "missing"

    status = str(state.get("status") or "").strip()
    if status == "revoked":
        return "revoked"
    if status != "active":
        return "missing"

    credentials_path = Path(str(state.get("credentials_path") or ""))
    if not credentials_path.exists():
        return "missing"

    credentials = _read_json(credentials_path)
    oauth_state = str(credentials.get("oauth_state") or "").strip()
    if oauth_state in {
        "prepared",
        "handshake-started",
        "handshake-stubbed",
        "launch-stubbed",
        "launch-intent-created",
        "browser-launch-attempted",
        "callback-received",
        "placeholder-stored",
        "real-stored",
    }:
        return oauth_state

    if bool(credentials.get("placeholder")) or credentials.get("real_oauth") is False:
        return "placeholder-stored"
    return "real-stored"


def get_provider_launch_result_state(*, profile: str, provider: str) -> str:
    state = get_provider_state(profile=profile, provider=provider)
    if state is None:
        return "not-started"

    credentials_path = Path(str(state.get("credentials_path") or ""))
    if not credentials_path.exists():
        return "not-started"

    credentials = _read_json(credentials_path)
    oauth_state = str(credentials.get("oauth_state") or "").strip()
    if oauth_state == "browser-launch-attempted":
        launch_result = str(credentials.get("browser_launch_result") or "").strip()
        if launch_result == "opened":
            return "launch-opened"
        if launch_result == "not-opened":
            return "launch-not-opened"
        return "launch-failed"
    if oauth_state == "launch-intent-created":
        return "launch-pending"
    return "not-started"


def get_provider_launch_freshness(*, profile: str, provider: str) -> str:
    state = get_provider_state(profile=profile, provider=provider)
    if state is None:
        return "not-applicable"

    credentials_path = Path(str(state.get("credentials_path") or ""))
    if not credentials_path.exists():
        return "not-applicable"

    credentials = _read_json(credentials_path)
    raw = str(
        credentials.get("browser_launch_attempted_at")
        or credentials.get("oauth_launch_started_at")
        or ""
    ).strip()
    if not raw:
        return "not-applicable"

    try:
        started_at = datetime.fromisoformat(raw)
    except ValueError:
        return "unknown"

    age_seconds = (datetime.now(UTC) - started_at).total_seconds()
    if age_seconds <= 300:
        return "fresh"
    return "stale"


def get_provider_callback_validation_state(*, profile: str, provider: str) -> str:
    state = get_provider_state(profile=profile, provider=provider)
    if state is None:
        return "not-applicable"

    credentials_path = Path(str(state.get("credentials_path") or ""))
    if not credentials_path.exists():
        return "not-applicable"

    credentials = _read_json(credentials_path)
    oauth_state = str(credentials.get("oauth_state") or "").strip()
    if oauth_state != "callback-received":
        return "not-applicable"

    has_code = bool(credentials.get("oauth_callback_has_code"))
    has_state = bool(credentials.get("oauth_callback_has_state"))
    if has_code and has_state:
        return "structurally-ready"
    if has_code:
        return "missing-state"
    if has_state:
        return "missing-code"
    return "incomplete"


def get_provider_exchange_readiness(*, profile: str, provider: str) -> str:
    state = get_provider_state(profile=profile, provider=provider)
    if state is None:
        return "not-applicable"

    credentials_path = Path(str(state.get("credentials_path") or ""))
    if not credentials_path.exists():
        return "not-applicable"

    credentials = _read_json(credentials_path)
    oauth_state = str(credentials.get("oauth_state") or "").strip()
    if oauth_state == "real-stored":
        if provider_has_real_credentials(profile=profile, provider=provider):
            return "exchange-complete"
        return "stored-without-token"
    if oauth_state != "callback-received":
        return "not-applicable"

    callback_validation_state = get_provider_callback_validation_state(
        profile=profile,
        provider=provider,
    )
    if callback_validation_state == "structurally-ready":
        return "exchange-ready"
    if callback_validation_state == "missing-code":
        return "missing-code"
    if callback_validation_state == "missing-state":
        return "missing-state"
    return "not-ready"


def get_provider_callback_intent_consistency(*, profile: str, provider: str) -> str:
    state = get_provider_state(profile=profile, provider=provider)
    if state is None:
        return "not-applicable"

    credentials_path = Path(str(state.get("credentials_path") or ""))
    if not credentials_path.exists():
        return "not-applicable"

    credentials = _read_json(credentials_path)
    oauth_state = str(credentials.get("oauth_state") or "").strip()
    if oauth_state != "callback-received":
        return "not-applicable"

    intent_id = str(credentials.get("oauth_intent_id") or "").strip()
    launch_started_at_raw = str(credentials.get("oauth_launch_started_at") or "").strip()
    callback_received_at_raw = str(credentials.get("oauth_callback_received_at") or "").strip()
    if not intent_id or not launch_started_at_raw:
        return "callback-without-intent"

    if get_provider_launch_freshness(profile=profile, provider=provider) == "stale":
        return "stale-launch"

    try:
        launch_started_at = datetime.fromisoformat(launch_started_at_raw)
        callback_received_at = datetime.fromisoformat(callback_received_at_raw)
    except ValueError:
        return "unclear"

    if callback_received_at >= launch_started_at:
        return "consistent"
    return "unclear"


def revoke_provider(*, profile: str, provider: str) -> dict[str, Any] | None:
    state = get_provider_state(profile=profile, provider=provider)
    if state is None:
        return None

    state["status"] = "revoked"
    state["updated_at"] = _now()
    state["revoked_at"] = _now()
    credentials_path = Path(str(state["credentials_path"]))
    if credentials_path.exists():
        credentials_path.unlink()

    state_path = _profile_dir(profile) / "providers" / provider / "state.json"
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def _profile_dir(profile: str) -> Path:
    if not profile or "/" in profile or "\\" in profile:
        raise ValueError("Profile name must be a simple non-empty identifier")
    return AUTH_PROFILES_DIR / profile


def _validate_provider(provider: str) -> None:
    normalized = (provider or "").strip().lower()
    if not _PROVIDER_ID_RE.fullmatch(normalized):
        raise ValueError("Provider name must be a simple lowercase identifier")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _existing_or_now(path: Path, key: str) -> str:
    if not path.exists():
        return _now()
    data = _read_json(path)
    return str(data.get(key, _now()))


def _now() -> str:
    return datetime.now(UTC).isoformat()
