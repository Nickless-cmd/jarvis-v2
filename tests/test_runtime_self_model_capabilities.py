from __future__ import annotations

import importlib


def test_runtime_self_model_surfaces_capability_registry_truth(isolated_runtime) -> None:
    self_model_mod = importlib.import_module("apps.api.jarvis_api.services.runtime_self_model")
    self_model_mod = importlib.reload(self_model_mod)

    model = self_model_mod.build_runtime_self_model()
    capability_truth = model.get("workspace_capabilities") or {}

    assert capability_truth.get("contract", {}).get("mode") == "text-capability-call"
    assert capability_truth.get("contract", {}).get("json_tool_call_supported") is False
    assert "tool:read-workspace-user-profile" in (capability_truth.get("callable_capability_ids") or [])
    assert "tool:read-external-file-by-path" in (capability_truth.get("callable_capability_ids") or [])
    assert "tool:run-non-destructive-command" in (capability_truth.get("callable_capability_ids") or [])
    assert "tool:propose-workspace-memory-update" in (capability_truth.get("approval_gated_capability_ids") or [])

    lines = self_model_mod.build_self_model_prompt_lines()
    joined = "\n".join(lines)
    assert "workspace_capabilities:" in joined
    assert "callable_capability_ids:" in joined
    assert "approval_gated_capability_ids:" in joined
    assert "json_tool_calls_not_supported" in joined
    assert "tool_call_args_contract:" in joined
    assert "argument_binding=in-tag-attributes" in joined
    assert "workspace_read=allowed" in joined
    assert "non_destructive_exec=allowed" in joined
    assert "mutating_exec=explicit-approval-required-bounded-non-sudo-only" in joined
    assert "sudo_exec=explicit-approval-required-proposal-only" in joined
    assert "mutating_exec_boundary:" in joined
