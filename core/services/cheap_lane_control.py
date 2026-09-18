"""Audited operator commands for Cheap Lane."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from core.runtime.db_cheap_lane_control import (
    finalize_cheap_lane_audit,
    record_cheap_lane_audit,
)
from core.services.cheap_provider_runtime_selection import select_cheap_lane_target


class ControlError(RuntimeError):
    pass


class ControlAuditError(ControlError):
    pass


class ControlRevisionConflict(ControlError):
    pass


class ControlScopeError(ControlError):
    pass


class ControlTargetNotFound(ControlError):
    pass


@dataclass(frozen=True)
class CheapLaneCommand:
    action: str
    target: str
    reason: str = ""
    expected_revision: str = ""
    parameters: dict[str, object] = field(default_factory=dict)


def _revision(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def _split_model(target: str) -> tuple[str, str]:
    parts = target.split("/", 1)
    if len(parts) != 2 or not all(part.strip() for part in parts):
        raise ControlScopeError("model target skal vaere provider/model")
    return parts[0].strip(), parts[1].strip()


def _registry_state(action: str, target: str) -> dict[str, object]:
    from core.services.provider_registry_admin import fuld_registrering

    registry = fuld_registrering()
    if action.startswith("provider."):
        return next(
            (dict(row) for row in registry["udbydere"] if row["provider"] == target),
            {},
        )
    if action.startswith("model.") or action == "routing-bias.set":
        provider, model = _split_model(target)
        return next(
            (dict(row) for row in registry["modeller"]
             if row["provider"] == provider and row["model"] == model),
            {},
        )
    return {}


def _authoritative_result(command: CheapLaneCommand, mutation: dict[str, object]) -> dict[str, object]:
    if command.action == "quota.set":
        provider, _profile = _split_model(command.target)
        return _registry_state("provider.deactivate", provider) or mutation
    if command.action in {
        "provider.deactivate", "provider.activate", "provider.delete", "provider.add",
        "model.deactivate", "model.activate", "model.delete", "model.add",
        "routing-bias.set",
    }:
        return _registry_state(command.action, command.target) or mutation
    return mutation


def _before(command: CheapLaneCommand) -> dict[str, object]:
    if command.action.startswith(("lane.", "provider.pause", "provider.resume",
                                  "provider.drain", "slot.pause", "slot.resume",
                                  "slot.drain")):
        from core.services.cheap_lane_admission import admission_snapshot

        scope = command.action.split(".", 1)[0]
        target = "cheap" if scope == "lane" else command.target
        return admission_snapshot(scope=scope, target=target)
    if command.action == "retention.set":
        from core.runtime.runtime_json_io import read_runtime_raw

        raw = read_runtime_raw()
        return {
            "metadata_days": raw.get("cheap_lane_metadata_retention_days", 60),
            "payload_days": raw.get("cheap_lane_payload_retention_days", 7),
        }
    return _registry_state(command.action, command.target)


def _require_reason(command: CheapLaneCommand) -> None:
    persistent = (
        ".deactivate", ".delete", ".add", "quota.set", "retention.set",
        "routing-bias.set",
    )
    if any(command.action.endswith(item) if item.startswith(".") else command.action == item
           for item in persistent) and not command.reason.strip():
        raise ControlScopeError("reason er paakraevet for vedvarende eller destruktive handlinger")


def _require_cheap_scope(command: CheapLaneCommand) -> None:
    registry_actions = {
        "provider.deactivate", "provider.activate", "provider.delete",
        "model.deactivate", "model.activate", "model.delete", "routing-bias.set",
    }
    if command.action not in registry_actions:
        return
    from core.services.provider_registry_admin import fuld_registrering

    models = list(fuld_registrering().get("modeller") or [])
    if command.action.startswith("provider."):
        owned = [row for row in models if row.get("provider") == command.target]
        if not owned:
            raise ControlTargetNotFound(f"ukendt udbyder: {command.target}")
        if any(str(row.get("lane") or "") != "cheap" for row in owned):
            raise ControlScopeError(
                "provideren ejer modeller uden for Cheap Lane og kan ikke styres samlet her"
            )
    else:
        provider, model = _split_model(command.target)
        row = next((row for row in models
                    if row.get("provider") == provider and row.get("model") == model), None)
        if row is None:
            raise ControlTargetNotFound(f"ukendt model: {provider}/{model}")
        if str(row.get("lane") or "") != "cheap":
            raise ControlScopeError("modellen er ikke i Cheap Lane")


def _admission_mutation(command: CheapLaneCommand) -> dict[str, object]:
    from core.services.cheap_lane_admission import (
        AdmissionRevisionConflict,
        set_admission_mode,
    )

    scope, verb = command.action.split(".", 1)
    mode = {"pause": "paused", "resume": "active", "drain": "draining"}[verb]
    target = "cheap" if scope == "lane" else command.target
    try:
        return set_admission_mode(
            scope=scope, target=target, mode=mode,
            expected_revision=command.expected_revision,
        )
    except AdmissionRevisionConflict as exc:
        raise ControlRevisionConflict(str(exc)) from exc


def _registry_mutation(command: CheapLaneCommand) -> tuple[dict[str, object], dict[str, object] | None]:
    from core.services import provider_registry_admin as admin

    action = command.action
    params = command.parameters
    pool_refresh: dict[str, object] | None = None
    if action in {"provider.deactivate", "provider.activate"}:
        result = admin.saet_udbyder_aktiv(
            provider=command.target, aktiv=action == "provider.activate", grund=command.reason
        )
    elif action == "provider.delete":
        result = admin.fjern_udbyder(provider=command.target)
    elif action in {"model.deactivate", "model.activate"}:
        provider, model = _split_model(command.target)
        result = admin.saet_model_aktiv(
            provider=provider, model=model,
            aktiv=action == "model.activate", grund=command.reason,
        )
    elif action == "model.delete":
        provider, model = _split_model(command.target)
        result = admin.fjern_model(provider=provider, model=model)
    elif action in {"provider.add", "model.add"}:
        result = admin.tilfoej(
            provider=str(params.get("provider") or command.target),
            model=str(params.get("model") or ""),
            lane=str(params.get("lane") or "cheap"),
            auth_mode=str(params.get("auth_mode") or "api_key"),
            auth_profile=str(params.get("auth_profile") or "default"),
            base_url=str(params.get("base_url") or ""),
            api_key=str(params.get("api_key") or ""),
        )
    elif action == "quota.set":
        from core.services.cheap_lane_quotas import set_quota_policy

        provider, profile = _split_model(command.target)
        result = set_quota_policy(
            provider=provider, auth_profile=profile,
            windows=list(params.get("windows") or []),
        )
    elif action == "routing-bias.set":
        provider, model = _split_model(command.target)
        result = admin.saet_routing_bias(
            provider=provider, model=model, bias=float(params.get("bias") or 0),
        )
    else:
        raise ControlScopeError(f"unsupported registry action: {action}")
    if result.get("status") != "ok":
        raise ControlTargetNotFound(str(result.get("fejl") or "control target not found"))
    if action != "quota.set":
        from core.services.cheap_lane_balancer import refresh_pool

        pool_refresh = refresh_pool()
    return dict(result), pool_refresh


def _mutate(command: CheapLaneCommand) -> tuple[dict[str, object], dict[str, object] | None]:
    if command.action in {
        "lane.pause", "lane.resume", "lane.drain",
        "provider.pause", "provider.resume", "provider.drain",
        "slot.pause", "slot.resume", "slot.drain",
    }:
        return _admission_mutation(command), None
    if command.action in {
        "provider.deactivate", "provider.activate", "provider.delete", "provider.add",
        "model.deactivate", "model.activate", "model.delete", "model.add",
        "quota.set", "routing-bias.set",
    }:
        return _registry_mutation(command)
    if command.action in {"slot.reset-breaker", "slot.release-cooldown"}:
        from core.services.cheap_lane_balancer import reset_slot

        return reset_slot(command.target), None
    if command.action == "retention.set":
        metadata = int(command.parameters.get("metadata_days") or 0)
        payload = int(command.parameters.get("payload_days") or 0)
        if not 1 <= metadata <= 365 or not 1 <= payload <= 30 or payload > metadata:
            raise ControlScopeError("retention skal vaere metadata 1..365, payload 1..30 og payload <= metadata")
        from core.runtime.runtime_json_io import write_runtime_merged

        write_runtime_merged({
            "cheap_lane_metadata_retention_days": metadata,
            "cheap_lane_payload_retention_days": payload,
        })
        return {"metadata_days": metadata, "payload_days": payload}, None
    if command.action == "probe":
        provider, model = _split_model(command.target)
        from core.services.cheap_provider_runtime_selection import test_provider_target

        return test_provider_target(
            provider=provider, model=model,
            auth_profile=str(command.parameters.get("auth_profile") or "default"),
            base_url=str(command.parameters.get("base_url") or ""),
        ), None
    raise ControlScopeError(f"unsupported Cheap Lane action: {command.action}")


def apply_control(command: CheapLaneCommand, actor: str) -> dict[str, object]:
    _require_reason(command)
    _require_cheap_scope(command)
    before = _before(command)
    if command.expected_revision and not command.action.startswith(("lane.", "provider.pause",
                                                                     "provider.resume", "provider.drain",
                                                                     "slot.pause", "slot.resume", "slot.drain")):
        if command.expected_revision != _revision(before):
            raise ControlRevisionConflict("Cheap Lane state changed since it was read")
    correlation_id = str(uuid4())
    try:
        audit_id = record_cheap_lane_audit(
            actor=actor, action=command.action, target=command.target,
            reason=command.reason, before=before, after={}, result="intent",
            correlation_id=correlation_id,
        )
    except Exception as exc:
        raise ControlAuditError("could not persist control intent") from exc
    try:
        mutation_result, pool_refresh = _mutate(command)
        resulting_state = _authoritative_result(command, mutation_result)
    except Exception as exc:
        try:
            finalize_cheap_lane_audit(
                audit_id, after={}, result="failed", error_code=type(exc).__name__
            )
        except Exception as audit_exc:
            raise ControlAuditError("control failed and audit could not be finalized") from audit_exc
        raise
    try:
        finalize_cheap_lane_audit(audit_id, after=resulting_state, result="completed")
    except Exception as exc:
        raise ControlAuditError("mutation completed but audit finalization failed") from exc
    try:
        from core.eventbus.bus import event_bus

        event_bus.publish("runtime.cheap_lane_control_changed", {
            "audit_id": audit_id, "action": command.action,
            "target": command.target, "result": "completed",
        })
    except Exception:
        pass
    return {
        "audit_id": audit_id,
        "status": "ok",
        "resulting_state": resulting_state,
        "revision": _revision(resulting_state),
        "pool_refresh": pool_refresh,
    }


def simulate_route(task_kind: str, skip_providers: frozenset[str]) -> dict[str, object]:
    return select_cheap_lane_target(
        task_kind=task_kind, skip_providers=skip_providers,
        persist_trace=False,
    )
