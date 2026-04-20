"""Automation DSL — declarative triggers → actions.

Ported from jarvis-ai (2026-03): a small structured language for defining
automations. An Automation binds a TriggerSpec (schedule or webhook) to an
ActionSpec (llm_prompt for now, extensible). Expirable and channel-scoped.

This is a *registry layer* — it stores definitions and exposes query/
lifecycle APIs. Execution (actually firing the trigger and running the
action) can be wired in later via a runner that polls due automations.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

logger = logging.getLogger(__name__)


TriggerType = Literal["schedule", "webhook", "event"]
ActionType = Literal["llm_prompt", "call_tool", "post_message"]
ChannelType = Literal["webchat", "discord", "telegram", "ntfy", "internal"]


@dataclass(frozen=True)
class TriggerSpec:
    type: TriggerType
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionSpec:
    type: ActionType
    prompt_template: str = ""
    title: str | None = None
    vars: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AutomationDSL:
    name: str
    description: str
    trigger: TriggerSpec
    action: ActionSpec
    channel: ChannelType = "internal"
    expires_in_hours: int | None = None


class AutomationDSLValidationError(ValueError):
    pass


_VALID_TRIGGERS: tuple[str, ...] = ("schedule", "webhook", "event")
_VALID_ACTIONS: tuple[str, ...] = ("llm_prompt", "call_tool", "post_message")
_VALID_CHANNELS: tuple[str, ...] = ("webchat", "discord", "telegram", "ntfy", "internal")

_STORAGE_REL = "workspaces/default/runtime/automations.json"


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load() -> list[dict[str, Any]]:
    path = _storage_path()
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception as exc:
        logger.warning("automation_dsl: load failed: %s", exc)
    return []


def _save(items: list[dict[str, Any]]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("automation_dsl: save failed: %s", exc)


def validate_automation(raw: dict[str, Any]) -> AutomationDSL:
    """Validate and construct an AutomationDSL from a raw dict."""
    if not isinstance(raw, dict):
        raise AutomationDSLValidationError("automation must be an object")

    name = str(raw.get("name") or "").strip()
    if not name:
        raise AutomationDSLValidationError("name is required")

    description = str(raw.get("description") or "")[:500]
    channel = str(raw.get("channel") or "internal")
    if channel not in _VALID_CHANNELS:
        raise AutomationDSLValidationError(f"channel must be one of {_VALID_CHANNELS}")

    trigger_raw = raw.get("trigger") or {}
    trigger_type = str(trigger_raw.get("type") or "").strip()
    if trigger_type not in _VALID_TRIGGERS:
        raise AutomationDSLValidationError(f"trigger.type must be one of {_VALID_TRIGGERS}")
    trigger_config = trigger_raw.get("config") or {}
    if not isinstance(trigger_config, dict):
        raise AutomationDSLValidationError("trigger.config must be a dict")
    trigger = TriggerSpec(type=trigger_type, config=dict(trigger_config))  # type: ignore[arg-type]

    action_raw = raw.get("action") or {}
    action_type = str(action_raw.get("type") or "").strip()
    if action_type not in _VALID_ACTIONS:
        raise AutomationDSLValidationError(f"action.type must be one of {_VALID_ACTIONS}")
    prompt_template = str(action_raw.get("prompt_template") or "")[:5000]
    title = action_raw.get("title")
    if title is not None:
        title = str(title)[:120]
    action_vars = action_raw.get("vars") or {}
    if not isinstance(action_vars, dict):
        raise AutomationDSLValidationError("action.vars must be a dict")
    action = ActionSpec(  # type: ignore[arg-type]
        type=action_type, prompt_template=prompt_template, title=title, vars=dict(action_vars)
    )

    expires = raw.get("expires_in_hours")
    if expires is not None:
        try:
            expires = int(expires)
            if expires <= 0:
                raise ValueError
        except Exception:
            raise AutomationDSLValidationError("expires_in_hours must be positive int or None")

    return AutomationDSL(
        name=name[:120],
        description=description,
        trigger=trigger,
        action=action,
        channel=channel,  # type: ignore[arg-type]
        expires_in_hours=expires,
    )


def register_automation(dsl: AutomationDSL) -> str:
    """Persist an AutomationDSL. Returns automation_id."""
    items = _load()
    auto_id = f"auto-{uuid4().hex[:12]}"
    now = datetime.now(UTC)
    expires_at = None
    if dsl.expires_in_hours is not None:
        expires_at = (now + timedelta(hours=int(dsl.expires_in_hours))).isoformat()
    items.append({
        "automation_id": auto_id,
        "name": dsl.name,
        "description": dsl.description,
        "trigger": asdict(dsl.trigger),
        "action": asdict(dsl.action),
        "channel": dsl.channel,
        "expires_in_hours": dsl.expires_in_hours,
        "expires_at": expires_at,
        "status": "active",
        "created_at": now.isoformat(),
        "last_fired_at": None,
        "fire_count": 0,
    })
    _save(items)
    return auto_id


def deactivate_automation(automation_id: str) -> bool:
    items = _load()
    for item in items:
        if item.get("automation_id") == automation_id:
            item["status"] = "inactive"
            _save(items)
            return True
    return False


def list_automations(*, status: str | None = None) -> list[dict[str, Any]]:
    items = _load()
    if status:
        items = [i for i in items if i.get("status") == status]
    return items


def _expire_due() -> int:
    """Mark expired automations as inactive. Returns count of newly expired."""
    items = _load()
    now = datetime.now(UTC)
    expired = 0
    changed = False
    for item in items:
        if item.get("status") != "active":
            continue
        exp = item.get("expires_at")
        if not exp:
            continue
        try:
            exp_dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
        except Exception:
            continue
        if exp_dt <= now:
            item["status"] = "expired"
            expired += 1
            changed = True
    if changed:
        _save(items)
    return expired


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Heartbeat hook — expire due automations, no other side-effects here."""
    expired = _expire_due()
    return {"expired": expired}


def build_automation_dsl_surface() -> dict[str, Any]:
    items = _load()
    active = [i for i in items if i.get("status") == "active"]
    inactive = [i for i in items if i.get("status") == "inactive"]
    expired = [i for i in items if i.get("status") == "expired"]
    return {
        "active": len(active) > 0,
        "total": len(items),
        "active_count": len(active),
        "inactive_count": len(inactive),
        "expired_count": len(expired),
        "recent_active": [
            {
                "automation_id": i["automation_id"],
                "name": i["name"],
                "trigger_type": i.get("trigger", {}).get("type"),
                "action_type": i.get("action", {}).get("type"),
                "channel": i.get("channel"),
                "expires_at": i.get("expires_at"),
            }
            for i in active[-5:]
        ],
        "summary": (
            f"{len(active)} aktive automations, {len(expired)} udløbet"
            if items else "Ingen automations registreret"
        ),
    }
