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


def test_workspace_write_proposal_content_is_persisted_with_approval_request(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    result = caps_mod.invoke_workspace_capability(
        "tool:propose-workspace-memory-update",
        write_content="Bounded proposal content for MEMORY.md.\n",
    )

    assert result["status"] == "approval-required"
    proposal_content = result.get("proposal_content") or {}
    assert proposal_content.get("state") == "bounded-content-ready"
    assert proposal_content.get("target") == "MEMORY.md"
    assert proposal_content.get("content") == "Bounded proposal content for MEMORY.md.\n"
    assert proposal_content.get("fingerprint")

    latest_request = isolated_runtime.db.latest_capability_approval_request(
        execution_mode="workspace-file-write",
        include_executed=False,
    )
    assert latest_request is not None
    assert latest_request["proposal_target_path"] == "MEMORY.md"
    assert latest_request["proposal_content"] == "Bounded proposal content for MEMORY.md.\n"
    assert latest_request["proposal_content_summary"]
    assert latest_request["proposal_content_fingerprint"] == proposal_content.get("fingerprint")
    assert latest_request["proposal_content_source"] == "explicit-write-content"


def test_approved_workspace_write_executes_only_with_explicit_content(isolated_runtime) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    workspace_dir = Path(caps_mod.load_workspace_capabilities().get("workspace") or "")
    target = workspace_dir / "MEMORY.md"
    before = target.read_text(encoding="utf-8")

    blocked = caps_mod.invoke_workspace_capability(
        "tool:propose-workspace-memory-update",
        approved=True,
    )
    assert blocked["status"] == "blocked-missing-write-content"
    assert target.read_text(encoding="utf-8") == before

    executed = caps_mod.invoke_workspace_capability(
        "tool:propose-workspace-memory-update",
        approved=True,
        write_content="Approved workspace write.\nScoped to MEMORY.md only.\n",
    )
    assert executed["status"] == "executed"
    assert executed["execution_mode"] == "workspace-file-write"
    result = executed.get("result") or {}
    assert result.get("type") == "workspace-file-write"
    assert result.get("path") == "MEMORY.md"
    assert result.get("workspace_scoped") is True
    assert target.read_text(encoding="utf-8") == "Approved workspace write.\nScoped to MEMORY.md only.\n"


def test_external_write_capability_stays_closed_even_when_approved(isolated_runtime) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    result = caps_mod.invoke_workspace_capability(
        "tool:propose-external-repo-file-update",
        approved=True,
        write_content="should not be written\n",
    )

    assert result["status"] == "not-runnable"
    assert result["execution_mode"] == "external-file-write"


def test_approved_workspace_write_request_executes_using_stored_proposal_content(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    workspace_dir = Path(caps_mod.load_workspace_capabilities().get("workspace") or "")
    target = workspace_dir / "MEMORY.md"

    proposed = isolated_runtime.mission_control.mc_invoke_workspace_capability(
        "tool:propose-workspace-memory-update",
        write_content="Stored approved proposal content.\n",
    )
    request_id = str((isolated_runtime.db.latest_capability_approval_request(
        execution_mode="workspace-file-write",
        include_executed=False,
    ) or {}).get("request_id") or "")
    assert request_id

    approved = isolated_runtime.mission_control.mc_approve_capability_request(request_id)
    assert approved["request"]["status"] == "approved"

    executed = isolated_runtime.mission_control.mc_execute_capability_request(request_id)

    assert executed["ok"] is True
    assert executed["status"] == "executed"
    assert target.read_text(encoding="utf-8") == "Stored approved proposal content.\n"


def test_workspace_write_execution_rejects_content_mismatch_against_approved_proposal(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    _ = isolated_runtime.mission_control.mc_invoke_workspace_capability(
        "tool:propose-workspace-memory-update",
        write_content="Approved proposal baseline.\n",
    )
    request_id = str((isolated_runtime.db.latest_capability_approval_request(
        execution_mode="workspace-file-write",
        include_executed=False,
    ) or {}).get("request_id") or "")
    assert request_id
    _ = isolated_runtime.mission_control.mc_approve_capability_request(request_id)

    executed = isolated_runtime.mission_control.mc_execute_capability_request(
        request_id,
        write_content="Different content.\n",
    )

    assert executed["ok"] is False
    assert executed["status"] == "proposal-content-mismatch"
