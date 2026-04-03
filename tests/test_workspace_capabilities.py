from __future__ import annotations

import importlib
from pathlib import Path


def test_workspace_capabilities_bind_to_runtime_workspace_and_populate(isolated_runtime) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    capabilities = caps_mod.load_workspace_capabilities()

    workspace = Path(str(capabilities.get("workspace") or ""))
    assert workspace.name == "default"
    assert workspace.parent.name == "workspaces"

    authority = capabilities.get("authority") or {}
    assert authority.get("described_count", 0) >= 5
    assert authority.get("available_now_count", 0) >= 3
    assert authority.get("approval_required_count", 0) >= 2

    runtime_capabilities = {
        str(item.get("capability_id") or ""): item
        for item in capabilities.get("runtime_capabilities") or []
    }

    assert "tool:read-workspace-user-profile" in runtime_capabilities
    assert "tool:search-workspace-memory-continuity" in runtime_capabilities
    assert "tool:read-repository-readme" in runtime_capabilities
    assert "tool:propose-workspace-memory-update" in runtime_capabilities
    assert "tool:propose-external-repo-file-update" in runtime_capabilities

    assert runtime_capabilities["tool:read-workspace-user-profile"]["available_now"] is True
    assert runtime_capabilities["tool:search-workspace-memory-continuity"]["available_now"] is True
    assert runtime_capabilities["tool:read-repository-readme"]["available_now"] is True
    assert runtime_capabilities["tool:propose-workspace-memory-update"]["runtime_status"] == "approval-required"
    assert runtime_capabilities["tool:propose-workspace-memory-update"]["available_now"] is False

    contract = capabilities.get("contract") or {}
    assert contract.get("mode") == "text-capability-call"
    assert contract.get("json_tool_call_supported") is False


def test_workspace_and_external_read_capabilities_execute(isolated_runtime) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    workspace_result = caps_mod.invoke_workspace_capability("tool:read-workspace-user-profile")
    assert workspace_result["status"] == "executed"
    assert workspace_result["execution_mode"] == "workspace-file-read"
    assert (workspace_result.get("result") or {}).get("type") == "workspace-file-read"
    assert len(str((workspace_result.get("result") or {}).get("text") or "")) > 0

    external_result = caps_mod.invoke_workspace_capability("tool:read-repository-readme")
    assert external_result["status"] == "executed"
    assert external_result["execution_mode"] == "external-file-read"
    result = external_result.get("result") or {}
    assert result.get("type") == "external-file-read"
    assert str(result.get("path") or "").endswith("README.md")
    assert len(str(result.get("text") or "")) > 0


def test_write_capabilities_are_positive_truth_but_not_callable(isolated_runtime) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    capabilities = caps_mod.load_workspace_capabilities()
    gated = set(capabilities.get("approval_gated_capability_ids") or [])

    assert "tool:propose-workspace-memory-update" in gated
    assert "tool:propose-external-repo-file-update" in gated

    approval_required = caps_mod.invoke_workspace_capability("tool:propose-workspace-memory-update")
    assert approval_required["status"] == "approval-required"
    assert approval_required["execution_mode"] == "workspace-file-write"