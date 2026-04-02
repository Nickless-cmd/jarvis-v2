from __future__ import annotations


def test_bounded_mutation_intent_classifies_modified_paths_as_modify_file(
    isolated_runtime,
    monkeypatch,
) -> None:
    mutation_mod = isolated_runtime.bounded_mutation_intent_runtime

    monkeypatch.setattr(
        mutation_mod,
        "load_workspace_capabilities",
        lambda: {
            "runtime_capabilities": [
                {"runtime_status": "approval-required", "execution_mode": "workspace-file-write"},
                {"runtime_status": "approval-required", "execution_mode": "git-write"},
                {"runtime_status": "available", "execution_mode": "read-only"},
            ]
        },
    )

    surface = mutation_mod.build_bounded_mutation_intent_surface(
        {
            "intent_state": "formed",
            "intent_type": "inspect-working-tree",
            "approval_scope": "repo-read",
            "approval_required": True,
        },
        awareness_surface={
            "repo_observation": {
                "modified_paths": [
                    "apps/api/jarvis_api/services/tool_intent_runtime.py",
                    "tests/test_tool_intent_runtime.py",
                ],
                "deleted_paths": [],
                "untracked_paths": [],
            }
        },
    )

    assert surface["mutation_intent_state"] == "proposal-only"
    assert surface["classification"] == "modify-file"
    assert surface["mutation_near"] is True
    assert surface["proposal_only"] is True
    assert surface["execution_state"] == "not-executed"
    assert surface["execution_permitted"] is False
    assert surface["scope"]["target_files"] == [
        "apps/api/jarvis_api/services/tool_intent_runtime.py",
        "tests/test_tool_intent_runtime.py",
    ]
    assert surface["scope"]["target_paths"] == [
        "apps/api/jarvis_api/services",
        "tests",
    ]
    assert surface["scope"]["repo_mutation_scope"] == ""
    assert surface["scope"]["system_mutation_scope"] == ""
    assert surface["scope"]["sudo_required"] is False
    assert surface["capability_boundary"]["approval_required_mutation_capability_count"] == 2
    assert surface["capability_boundary"]["approval_required_mutation_classes"] == [
        "modify-file",
        "git-mutate",
    ]


def test_bounded_mutation_intent_classifies_upstream_check_as_git_mutate(
    isolated_runtime,
    monkeypatch,
) -> None:
    mutation_mod = isolated_runtime.bounded_mutation_intent_runtime

    monkeypatch.setattr(
        mutation_mod,
        "load_workspace_capabilities",
        lambda: {"runtime_capabilities": []},
    )

    surface = mutation_mod.build_bounded_mutation_intent_surface(
        {
            "intent_state": "approval-required",
            "intent_type": "inspect-upstream-divergence",
            "approval_scope": "repo-update-check",
            "approval_required": True,
        },
        awareness_surface={
            "repo_observation": {
                "branch_name": "feature/tool-intent",
                "upstream_ref": "origin/main",
                "modified_paths": [],
                "deleted_paths": [],
                "untracked_paths": [],
            }
        },
    )

    assert surface["mutation_intent_state"] == "proposal-only"
    assert surface["classification"] == "git-mutate"
    assert surface["mutation_near"] is True
    assert surface["approval_required"] is True
    assert surface["explicit_approval_required"] is True
    assert surface["scope"]["repo_mutation_scope"] == "upstream-sync:feature/tool-intent->origin/main"
    assert surface["scope"]["system_mutation_scope"] == ""
    assert surface["scope"]["sudo_required"] is False
    assert surface["scope"]["mutation_critical"] is True