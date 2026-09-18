from __future__ import annotations

import json

import pytest


@pytest.fixture
def cheap_registry(tmp_path, monkeypatch):
    path = tmp_path / "provider_router.json"
    path.write_text(json.dumps({
        "providers": [{
            "provider": "groq", "enabled": True, "auth_profile": "default",
        }],
        "models": [{
            "provider": "groq", "model": "llama", "lane": "cheap", "enabled": True,
        }],
    }), encoding="utf-8")
    import core.runtime.config as cfg
    import core.runtime.provider_router as router
    import core.services.provider_registry_admin as admin
    monkeypatch.setattr(cfg, "PROVIDER_ROUTER_FILE", path, raising=False)
    monkeypatch.setattr(router, "PROVIDER_ROUTER_FILE", path, raising=False)
    monkeypatch.setattr(admin, "_fil", lambda: path)
    monkeypatch.setattr(router, "load_provider_router_registry",
                        lambda: json.loads(path.read_text(encoding="utf-8")))
    monkeypatch.setattr(router, "_credentials_ready", lambda **_kw: True)
    return path


def test_pause_is_temporary_but_deactivate_is_persistent(isolated_runtime, cheap_registry):
    from core.services.cheap_lane_control import CheapLaneCommand, apply_control

    paused = apply_control(CheapLaneCommand(
        action="provider.pause", target="groq", reason="test"
    ), actor="owner")
    registry = json.loads(cheap_registry.read_text(encoding="utf-8"))
    assert paused["resulting_state"]["mode"] == "paused"
    assert registry["providers"][0]["enabled"] is True

    disabled = apply_control(CheapLaneCommand(
        action="provider.deactivate", target="groq", reason="test"
    ), actor="owner")
    registry = json.loads(cheap_registry.read_text(encoding="utf-8"))
    assert disabled["resulting_state"]["enabled"] is False
    assert registry["providers"][0]["enabled"] is False


def test_success_is_not_returned_when_audit_fails(
    isolated_runtime, cheap_registry, monkeypatch
):
    import core.services.cheap_lane_control as control

    monkeypatch.setattr(
        control, "record_cheap_lane_audit",
        lambda **_kw: (_ for _ in ()).throw(OSError("disk")),
    )
    with pytest.raises(control.ControlAuditError):
        control.apply_control(control.CheapLaneCommand(
            action="quota.set", target="groq/default", reason="budget",
            parameters={"windows": [{
                "period": "month", "unit": "tokens", "limit": 1_000_000,
            }]},
        ), actor="owner")


def test_revision_conflict_prevents_mutation(isolated_runtime, cheap_registry):
    from core.services.cheap_lane_control import (
        CheapLaneCommand,
        ControlRevisionConflict,
        apply_control,
    )

    with pytest.raises(ControlRevisionConflict):
        apply_control(CheapLaneCommand(
            action="provider.deactivate", target="groq", reason="test",
            expected_revision="stale",
        ), actor="owner")
    assert json.loads(cheap_registry.read_text(encoding="utf-8"))["providers"][0]["enabled"]


def test_route_simulation_does_not_persist_trace(isolated_runtime, monkeypatch):
    import core.services.cheap_lane_control as control

    seen = {}
    monkeypatch.setattr(control, "select_cheap_lane_target", lambda **kwargs: seen.update(kwargs) or {
        "provider": "groq", "model": "llama", "active": True,
    })
    result = control.simulate_route(task_kind="background", skip_providers=frozenset())
    assert result["provider"] == "groq"
    assert seen["persist_trace"] is False


def test_provider_control_rejects_cross_lane_blast_radius(
    isolated_runtime, cheap_registry
):
    data = json.loads(cheap_registry.read_text(encoding="utf-8"))
    data["models"].append({
        "provider": "groq", "model": "visible", "lane": "visible", "enabled": True,
    })
    cheap_registry.write_text(json.dumps(data), encoding="utf-8")
    from core.services.cheap_lane_control import (
        CheapLaneCommand,
        ControlScopeError,
        apply_control,
    )

    with pytest.raises(ControlScopeError):
        apply_control(CheapLaneCommand(
            action="provider.deactivate", target="groq", reason="test",
        ), actor="owner")
