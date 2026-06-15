import asyncio

import apps.api.jarvis_api.routes.account as acc
from apps.api.jarvis_api.routes.account import build_jarvis_overview


def test_build_jarvis_overview_maps_lanes():
    targets = {
        "visible": {"lane": "visible", "provider": "ollama", "model": "glm-5.1", "active": True, "credentials_ready": True},
        "cheap": {"lane": "cheap", "provider": None, "model": None, "active": False, "credentials_ready": False},
    }
    ov = build_jarvis_overview(lane_targets=lambda: targets)
    visible = next(l for l in ov["lanes"] if l["lane"] == "visible")
    assert visible["provider"] == "ollama"
    assert visible["model"] == "glm-5.1"
    assert visible["active"] is True


def test_set_visible_model_validates_membership(monkeypatch):
    monkeypatch.setattr(acc, "_current_role", lambda uid: "owner")
    monkeypatch.setattr(acc, "current_context_snapshot", lambda: {"user_id": ""})
    import core.runtime.provider_router as pr
    monkeypatch.setattr(pr, "list_provider_router_targets",
                        lambda *, lane: [{"provider": "ollama", "model": "glm-5.1"}])
    # ukendt model afvises
    res = asyncio.run(acc.account_set_visible_model({"provider": "ollama", "model": "ukendt"}))
    assert res["status"] == "error"


def test_set_visible_model_owner_only(monkeypatch):
    monkeypatch.setattr(acc, "_current_role", lambda uid: "member")
    monkeypatch.setattr(acc, "current_context_snapshot", lambda: {"user_id": "u_m"})
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        asyncio.run(acc.account_set_visible_model({"provider": "ollama", "model": "glm-5.1"}))
    assert ei.value.status_code == 403


def test_set_visible_model_applies(monkeypatch):
    monkeypatch.setattr(acc, "_current_role", lambda uid: "owner")
    monkeypatch.setattr(acc, "current_context_snapshot", lambda: {"user_id": ""})
    import core.runtime.provider_router as pr
    monkeypatch.setattr(pr, "list_provider_router_targets",
                        lambda *, lane: [{"provider": "ollama", "model": "glm-5.1"}])
    captured = {}
    monkeypatch.setattr(pr, "select_main_agent_target",
                        lambda *, provider, model, auth_profile=None: captured.update(p=provider, m=model) or {"active": True})
    res = asyncio.run(acc.account_set_visible_model({"provider": "ollama", "model": "glm-5.1"}))
    assert res["status"] == "ok"
    assert captured == {"p": "ollama", "m": "glm-5.1"}
