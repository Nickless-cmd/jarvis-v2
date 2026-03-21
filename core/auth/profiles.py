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
    view["auth_material_kind"] = get_provider_auth_material_kind(
        profile=profile,
        provider=provider,
    )
    return view


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
    if bool(credentials.get("placeholder")):
        return "placeholder"
    if credentials.get("real_oauth") is False:
        return "placeholder"
    return "real"


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
