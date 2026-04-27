"""Role registry — runtime-extensible agent roles.

Existing AGENT_ROLE_TEMPLATES in agent_runtime.py is hardcoded. This
module adds a runtime layer: load custom roles from
~/.jarvis-v2/config/custom_roles.json, merged on top of built-in
templates. This lets Jarvis (and the user) define new specialised roles
without code changes.

Custom role schema (extends built-in):
  {
    "role": "security_auditor",
    "title": "Sikkerhedsauditor",
    "system_prompt": "Du er...",
    "default_tool_policy": "read-only",
    "extends": "critic",  // optional: inherit from built-in
    "tags": ["security", "audit"]
  }

Resolved order: custom > built-in. Custom can shadow built-in by name.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CUSTOM_ROLES_PATH = Path.home() / ".jarvis-v2" / "config" / "custom_roles.json"


def _load_custom_roles() -> list[dict[str, Any]]:
    if not _CUSTOM_ROLES_PATH.exists():
        return []
    try:
        data = json.loads(_CUSTOM_ROLES_PATH.read_text(encoding="utf-8"))
        roles = data.get("roles") or []
        if not isinstance(roles, list):
            return []
        return [r for r in roles if isinstance(r, dict) and r.get("role")]
    except Exception as exc:
        logger.warning("role_registry: load failed: %s", exc)
        return []


def _builtin_roles() -> dict[str, dict[str, Any]]:
    try:
        from core.services.agent_runtime import AGENT_ROLE_TEMPLATES
        return dict(AGENT_ROLE_TEMPLATES)
    except Exception:
        return {}


def list_all_roles() -> dict[str, dict[str, Any]]:
    """Return merged dict of role_name → template (builtin + custom)."""
    merged: dict[str, dict[str, Any]] = dict(_builtin_roles())
    for custom in _load_custom_roles():
        name = str(custom.get("role") or "").strip()
        if not name:
            continue
        # Inheritance: extends="role_name" pulls defaults from base
        base_name = str(custom.get("extends") or "").strip()
        base = merged.get(base_name, {}) if base_name else {}
        resolved = dict(base)
        for k, v in custom.items():
            if k != "extends":
                resolved[k] = v
        merged[name] = resolved
    return merged


def get_role(name: str) -> dict[str, Any] | None:
    """Look up a single role by name (custom > built-in)."""
    roles = list_all_roles()
    return roles.get(str(name or ""))


def register_custom_role(
    *,
    role: str,
    title: str,
    system_prompt: str,
    default_tool_policy: str = "read-only",
    extends: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Persist a new custom role to disk. Idempotent on (role) name."""
    role = (role or "").strip()
    if not role or not title or not system_prompt:
        return {"status": "error", "error": "role, title, system_prompt required"}
    _CUSTOM_ROLES_PATH.parent.mkdir(parents=True, exist_ok=True)
    if _CUSTOM_ROLES_PATH.exists():
        try:
            data = json.loads(_CUSTOM_ROLES_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {}
    roles = list(data.get("roles") or [])
    # Replace if exists
    roles = [r for r in roles if r.get("role") != role]
    new_entry = {
        "role": role,
        "title": title,
        "system_prompt": system_prompt,
        "default_tool_policy": default_tool_policy,
    }
    if extends:
        new_entry["extends"] = extends
    if tags:
        new_entry["tags"] = list(tags)
    roles.append(new_entry)
    data["roles"] = roles
    _CUSTOM_ROLES_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"status": "ok", "role": new_entry, "total_custom_roles": len(roles)}


def _exec_list_roles(args: dict[str, Any]) -> dict[str, Any]:
    roles = list_all_roles()
    custom_names = {r.get("role") for r in _load_custom_roles()}
    return {
        "status": "ok",
        "total": len(roles),
        "roles": [
            {
                "role": name,
                "title": str(t.get("title", "")),
                "default_tool_policy": str(t.get("default_tool_policy", "")),
                "is_custom": name in custom_names,
                "tags": list(t.get("tags") or []),
            }
            for name, t in sorted(roles.items())
        ],
    }


def _exec_register_custom_role(args: dict[str, Any]) -> dict[str, Any]:
    return register_custom_role(
        role=str(args.get("role") or ""),
        title=str(args.get("title") or ""),
        system_prompt=str(args.get("system_prompt") or ""),
        default_tool_policy=str(args.get("default_tool_policy") or "read-only"),
        extends=args.get("extends"),
        tags=args.get("tags"),
    )


ROLE_REGISTRY_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_agent_roles",
            "description": "List all available agent roles (builtin + custom). Use before spawning to see what's possible.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "register_custom_role",
            "description": (
                "Define a new custom agent role. Persisted to "
                "~/.jarvis-v2/config/custom_roles.json. Custom roles can "
                "extend a built-in role (extends='critic') or stand alone. "
                "Tools that spawn agents (spawn_agent_task, convene_council) "
                "will then accept the new role."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {"type": "string", "description": "snake_case role name."},
                    "title": {"type": "string", "description": "Display name."},
                    "system_prompt": {"type": "string"},
                    "default_tool_policy": {"type": "string"},
                    "extends": {"type": "string", "description": "Optional built-in role to inherit from."},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["role", "title", "system_prompt"],
            },
        },
    },
]
