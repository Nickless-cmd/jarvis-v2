"""Skill Contract Registry — formal contracts for capabilities.

Ported concept from jarvis-agent (2026-03): formal SkillSpec, SkillManifest,
and SkillPermissionSpec dataclasses giving each capability an immutable
contract. V2 has workspace_capabilities with policy metadata, but not the
formal permission-scope contract layer.

Purpose: make each skill/tool carry its own required scopes so permission
policy can be enforced uniformly. This is a *registry layer* — it does not
replace existing tool execution. Tools that register a contract become
inspectable and governable.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SkillSpec:
    """Immutable skill identity."""

    name: str
    version: str
    description: str = ""


@dataclass(frozen=True)
class SkillPermissionSpec:
    """Required scopes for a skill to run."""

    scopes: tuple[str, ...] = ()
    requires_approval: bool = False


@dataclass
class SkillManifest:
    """Bundle of spec + permissions + schemas."""

    spec: SkillSpec
    permissions: SkillPermissionSpec
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = field(default_factory=tuple)


# Module-level registry (simple in-memory)
_registry: dict[str, SkillManifest] = {}


def register_skill(manifest: SkillManifest) -> None:
    """Register a skill manifest. Overwrites prior entry with same name."""
    _registry[manifest.spec.name] = manifest


def get_manifest(name: str) -> SkillManifest | None:
    return _registry.get(name)


def list_manifests() -> list[SkillManifest]:
    return list(_registry.values())


def check_permissions(
    name: str, granted_scopes: set[str] | list[str] | tuple[str, ...]
) -> dict[str, Any]:
    """Evaluate whether granted scopes satisfy a skill's required scopes."""
    manifest = get_manifest(name)
    if manifest is None:
        return {"found": False, "ok": False, "reason": "manifest-not-registered"}
    granted = set(granted_scopes or [])
    required = set(manifest.permissions.scopes)
    missing = sorted(required - granted)
    if missing:
        return {
            "found": True,
            "ok": False,
            "reason": "missing-scopes",
            "missing": missing,
            "requires_approval": manifest.permissions.requires_approval,
        }
    return {
        "found": True,
        "ok": True,
        "reason": "granted",
        "requires_approval": manifest.permissions.requires_approval,
    }


def _auto_register_known_skills() -> None:
    """Seed registry with contracts for well-known built-in capabilities.

    Silent no-op if something breaks — registry should not block startup.
    """
    seeds: list[SkillManifest] = [
        SkillManifest(
            spec=SkillSpec(
                name="send_webchat_message",
                version="1.0",
                description="Send a message into an active webchat session.",
            ),
            permissions=SkillPermissionSpec(
                scopes=("chat:write", "session:active"),
                requires_approval=False,
            ),
            tags=("communication", "chat"),
        ),
        SkillManifest(
            spec=SkillSpec(
                name="send_discord_dm",
                version="1.0",
                description="Send a DM to the owner via Discord gateway.",
            ),
            permissions=SkillPermissionSpec(
                scopes=("chat:write", "external:discord"),
                requires_approval=False,
            ),
            tags=("communication", "external"),
        ),
        SkillManifest(
            spec=SkillSpec(
                name="discord_channel",
                version="1.0",
                description="Search/fetch/send on Discord channels.",
            ),
            permissions=SkillPermissionSpec(
                scopes=("chat:write", "chat:read", "external:discord"),
                requires_approval=False,
            ),
            tags=("communication", "external"),
        ),
        SkillManifest(
            spec=SkillSpec(
                name="send_telegram_message",
                version="1.0",
                description="Send a Telegram message via bot.",
            ),
            permissions=SkillPermissionSpec(
                scopes=("chat:write", "external:telegram"),
                requires_approval=False,
            ),
            tags=("communication", "external"),
        ),
        SkillManifest(
            spec=SkillSpec(
                name="send_ntfy",
                version="1.0",
                description="Send ntfy notification (push) to the owner.",
            ),
            permissions=SkillPermissionSpec(
                scopes=("notify:push",),
                requires_approval=False,
            ),
            tags=("notification",),
        ),
        SkillManifest(
            spec=SkillSpec(
                name="search_sessions",
                version="1.0",
                description="Cross-channel keyword/semantic session search.",
            ),
            permissions=SkillPermissionSpec(
                scopes=("memory:read", "session:read"),
                requires_approval=False,
            ),
            tags=("memory", "search"),
        ),
        SkillManifest(
            spec=SkillSpec(
                name="browser_open",
                version="1.0",
                description="Open a URL in headless browser — read-only web access.",
            ),
            permissions=SkillPermissionSpec(
                scopes=("web:read", "browser:control"),
                requires_approval=True,
            ),
            tags=("web", "browser"),
        ),
    ]
    for m in seeds:
        try:
            register_skill(m)
        except Exception as exc:
            logger.debug("skill_contract_registry: failed to seed %s: %s", m.spec.name, exc)


_auto_register_known_skills()


def build_skill_contract_registry_surface() -> dict[str, Any]:
    """Mission Control surface."""
    manifests = list_manifests()
    by_tag: dict[str, int] = {}
    gated = 0
    for m in manifests:
        for tag in m.tags:
            by_tag[tag] = by_tag.get(tag, 0) + 1
        if m.permissions.requires_approval:
            gated += 1
    return {
        "active": len(manifests) > 0,
        "total_skills": len(manifests),
        "approval_gated": gated,
        "by_tag": by_tag,
        "skills": [
            {
                "name": m.spec.name,
                "version": m.spec.version,
                "scopes": list(m.permissions.scopes),
                "requires_approval": m.permissions.requires_approval,
                "tags": list(m.tags),
            }
            for m in manifests
        ],
        "summary": (
            f"{len(manifests)} skills registered, {gated} approval-gated"
            if manifests else "No skill contracts registered"
        ),
    }
