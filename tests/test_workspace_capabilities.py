from __future__ import annotations

import importlib
import subprocess
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
    assert "tool:read-external-file-by-path" in runtime_capabilities
    assert "tool:run-non-destructive-command" in runtime_capabilities
    assert "tool:propose-workspace-memory-update" in runtime_capabilities
    assert "tool:propose-external-repo-file-update" in runtime_capabilities

    assert runtime_capabilities["tool:read-workspace-user-profile"]["available_now"] is True
    assert runtime_capabilities["tool:search-workspace-memory-continuity"]["available_now"] is True
    assert runtime_capabilities["tool:read-repository-readme"]["available_now"] is True
    assert runtime_capabilities["tool:read-external-file-by-path"]["available_now"] is True
    assert runtime_capabilities["tool:run-non-destructive-command"]["available_now"] is True
    assert runtime_capabilities["tool:propose-workspace-memory-update"]["runtime_status"] == "approval-required"
    assert runtime_capabilities["tool:propose-workspace-memory-update"]["available_now"] is False

    contract = capabilities.get("contract") or {}
    assert contract.get("mode") == "text-capability-call"
    assert contract.get("json_tool_call_supported") is False
    policy = capabilities.get("policy") or {}
    assert policy.get("mutating_exec") == "explicit-approval-required-bounded-non-sudo-only"
    assert policy.get("sudo_exec") == "explicit-approval-required-bounded-allowlist-with-short-ttl-window"


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


def test_dynamic_external_read_capability_reads_explicit_external_path(
    isolated_runtime,
    tmp_path: Path,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    external_file = tmp_path / "external-visible-read.txt"
    external_file.write_text("External capability smoke text.\n", encoding="utf-8")

    result = caps_mod.invoke_workspace_capability(
        "tool:read-external-file-by-path",
        target_path=str(external_file),
    )

    assert result["status"] == "executed"
    assert result["execution_mode"] == "external-file-read"
    payload = result.get("result") or {}
    assert payload.get("type") == "external-file-read"
    assert payload.get("path") == str(external_file.resolve())
    assert payload.get("target_source") == "invocation-argument"
    assert payload.get("workspace_scoped") is False
    assert "External capability smoke text." in str(payload.get("text") or "")


def test_dynamic_external_read_rejects_workspace_scoped_target(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    workspace_dir = Path(caps_mod.load_workspace_capabilities().get("workspace") or "")
    workspace_target = workspace_dir / "USER.md"

    result = caps_mod.invoke_workspace_capability(
        "tool:read-external-file-by-path",
        target_path=str(workspace_target),
    )

    assert result["status"] == "blocked-scope-mismatch"
    assert result["execution_mode"] == "external-file-read"


def test_non_destructive_exec_capability_runs_bounded_command(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    result = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="pwd",
    )

    assert result["status"] == "executed"
    assert result["execution_mode"] == "non-destructive-exec"
    payload = result.get("result") or {}
    assert payload.get("type") == "non-destructive-exec"
    assert payload.get("command_text") == "pwd"
    assert payload.get("command_source") == "invocation-argument"
    assert payload.get("mutation_permitted") is False
    assert payload.get("sudo_permitted") is False
    assert str(payload.get("text") or "").strip()


def test_non_destructive_exec_normalizes_tilde_home_path(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    result = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="ls -la ~",
    )

    assert result["status"] == "executed"
    payload = result.get("result") or {}
    argv = payload.get("argv") or []
    assert argv[0:2] == ["ls", "-la"]
    assert argv[-1] == str(Path.home())
    assert payload.get("normalized_command_text") == f"ls -la {Path.home()}"
    assert payload.get("path_normalization_applied") is True
    assert payload.get("normalization_source") == "tilde"


def test_non_destructive_exec_normalizes_home_env_path(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    result = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="ls -la $HOME",
    )

    assert result["status"] == "executed"
    payload = result.get("result") or {}
    argv = payload.get("argv") or []
    assert argv[0:2] == ["ls", "-la"]
    assert argv[-1] == str(Path.home())
    assert payload.get("normalized_command_text") == f"ls -la {Path.home()}"
    assert payload.get("path_normalization_applied") is True
    assert payload.get("normalization_source") == "home-env"


def test_non_destructive_exec_blocks_destructive_and_sudo_commands(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    destructive = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="rm -rf tmp",
    )
    assert destructive["status"] == "blocked-destructive-command"
    assert destructive["execution_mode"] == "non-destructive-exec"

    sudo = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="sudo ls /root",
    )
    assert sudo["status"] == "approval-required"
    assert sudo["execution_mode"] == "sudo-exec-proposal"
    proposal = sudo.get("proposal_content") or {}
    assert proposal.get("type") == "sudo-exec-proposal"
    assert proposal.get("command") == "sudo ls /root"
    assert proposal.get("requires_sudo") is True
    assert proposal.get("explicit_approval_required") is True
    assert proposal.get("not_executed") is True
    assert proposal.get("scope") == "system"
    assert proposal.get("criticality") == "high"

    shell_features = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="ls $HOME && pwd",
    )
    assert shell_features["status"] == "executed"
    assert shell_features["execution_mode"] == "non-destructive-exec"
    shell_payload = shell_features.get("result") or {}
    assert shell_payload.get("shell_mode") is True
    assert shell_payload.get("shell_segments") == [f"ls {Path.home()}", "pwd"]


def test_non_destructive_exec_allows_read_only_pipes_and_globbing(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    result = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="find /media/projects/jarvis-v2 -maxdepth 1 -name '*.md' | head",
    )

    assert result["status"] == "executed"
    payload = result.get("result") or {}
    assert payload.get("shell_mode") is True
    assert payload.get("mutation_permitted") is False


def test_non_destructive_exec_allows_cd_navigation_in_shell_flow(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    result = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="cd /media/projects/jarvis-v2 && git log -20 --oneline",
    )

    assert result["status"] == "executed"
    payload = result.get("result") or {}
    assert payload.get("shell_mode") is True
    assert payload.get("execution_scope") == "git-read"
    assert payload.get("repo_scoped") is True
    assert payload.get("shell_segments") == [
        "cd /media/projects/jarvis-v2",
        "git log -20 --oneline",
    ]


def test_non_destructive_exec_allows_common_system_inspection_commands(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    for command_text in ("lscpu", "lshw", "free -h", "lsblk", "df -h", "nproc", "uptime"):
        result = caps_mod.invoke_workspace_capability(
            "tool:run-non-destructive-command",
            command_text=command_text,
        )
        assert result["status"] == "executed", command_text
        payload = result.get("result") or {}
        assert payload.get("type") == "non-destructive-exec"


def test_non_destructive_exec_still_blocks_redirection_and_substitution(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    redirected = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="pwd > /tmp/out.txt",
    )
    assert redirected["status"] == "blocked-shell-redirection"

    substituted = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="echo $(pwd)",
    )
    assert substituted["status"] == "blocked-shell-substitution"


def test_mutating_exec_command_surfaces_as_approval_gated_proposal_only(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    result = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="git add README.md",
    )

    assert result["status"] == "approval-required"
    assert result["execution_mode"] == "mutating-exec-proposal"
    assert result["approval"]["required"] is True
    assert result["approval"]["granted"] is False
    proposal = result.get("proposal_content") or {}
    assert proposal.get("type") == "mutating-exec-proposal"
    assert proposal.get("command") == "git add README.md"
    assert proposal.get("scope") == "git"
    assert proposal.get("git_mutation_class") == "git-stage"
    assert proposal.get("repo_stewardship_domain") == "git"
    assert proposal.get("explicit_approval_required") is True
    assert proposal.get("not_executed") is True


def test_git_mutation_commands_land_in_bounded_repo_stewardship_classes(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    cases = [
        ("git add README.md", "git-stage"),
        ('git commit -m "msg"', "git-commit"),
        ("git push", "git-sync"),
        ("git pull", "git-sync"),
        ("git checkout main", "git-branch-switch"),
        ("git switch feature-x", "git-branch-switch"),
        ("git reset HEAD~1", "git-history-rewrite"),
        ("git rebase main", "git-history-rewrite"),
        ("git stash", "git-stash"),
    ]

    for command_text, expected_class in cases:
        result = caps_mod.invoke_workspace_capability(
            "tool:run-non-destructive-command",
            command_text=command_text,
        )
        assert result["status"] == "approval-required"
        assert result["execution_mode"] == "mutating-exec-proposal"
        proposal = result.get("proposal_content") or {}
        assert proposal.get("scope") == "git"
        assert proposal.get("git_mutation_class") == expected_class
        assert proposal.get("repo_stewardship_domain") == "git"
        assert proposal.get("not_executed") is True


def test_git_read_exec_commands_are_allowed_as_bounded_inspection(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    status = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="git status",
    )
    assert status["status"] == "executed"
    status_payload = status.get("result") or {}
    assert status_payload.get("type") == "non-destructive-exec"
    assert status_payload.get("execution_classification") == "git-read-allowed"
    assert status_payload.get("execution_scope") == "git-read"
    assert status_payload.get("repo_scoped") is True
    assert status_payload.get("mutation_permitted") is False

    diff_stat = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="git diff --stat",
    )
    assert diff_stat["status"] == "executed"
    diff_payload = diff_stat.get("result") or {}
    assert diff_payload.get("execution_classification") == "git-read-allowed"
    assert diff_payload.get("execution_scope") == "git-read"


def test_git_read_exec_commands_allow_git_c_repo_scoping(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    repo_root = Path("/media/projects/jarvis-v2")

    status = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text=f"git -C {repo_root} status",
    )
    assert status["status"] == "executed"
    status_payload = status.get("result") or {}
    assert status_payload.get("execution_classification") == "git-read-allowed"
    assert status_payload.get("execution_scope") == "git-read"
    assert status_payload.get("repo_scoped") is True

    log_result = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text=f"git -C {repo_root} log --oneline -n 20",
    )
    assert log_result["status"] == "executed"
    log_payload = log_result.get("result") or {}
    assert log_payload.get("execution_classification") == "git-read-allowed"
    assert log_payload.get("execution_scope") == "git-read"

    short_log = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text=f"git -C {repo_root} log -20 --oneline",
    )
    assert short_log["status"] == "executed"
    short_log_payload = short_log.get("result") or {}
    assert short_log_payload.get("execution_classification") == "git-read-allowed"

    show_stat = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text=f"git -C {repo_root} show --stat -n 1",
    )
    assert show_stat["status"] == "executed"
    show_payload = show_stat.get("result") or {}
    assert show_payload.get("execution_classification") == "git-read-allowed"

    top_level = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text=f"git -C {repo_root} rev-parse --show-toplevel",
    )
    assert top_level["status"] == "executed"
    top_level_payload = top_level.get("result") or {}
    assert top_level_payload.get("execution_classification") == "git-read-allowed"


def test_git_mutation_and_destructive_git_commands_do_not_execute(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    proposal = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="git pull",
    )
    assert proposal["status"] == "approval-required"
    assert proposal["execution_mode"] == "mutating-exec-proposal"
    proposal_content = proposal.get("proposal_content") or {}
    assert proposal_content.get("scope") == "git"
    assert proposal_content.get("not_executed") is True

    blocked = caps_mod.invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="git clean -fd",
    )
    assert blocked["status"] == "blocked-git-destructive"
    assert blocked["execution_mode"] == "non-destructive-exec"


def test_approved_non_sudo_mutating_exec_runs_for_exact_approved_command(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    source = Path("/tmp/jarvis_mutating_exec_source.txt")
    target = Path("/tmp/jarvis_mutating_exec_target.txt")
    source.write_text("bounded mutating exec\n", encoding="utf-8")
    if target.exists():
        target.unlink()

    proposed = isolated_runtime.mission_control.mc_invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text=f"cp {source} {target}",
    )
    assert proposed["status"] == "approval-required"
    assert proposed["execution_mode"] == "mutating-exec-proposal"

    request_id = str((isolated_runtime.db.latest_capability_approval_request(
        execution_mode="mutating-exec-proposal",
        include_executed=False,
    ) or {}).get("request_id") or "")
    assert request_id

    approved = isolated_runtime.mission_control.mc_approve_capability_request(request_id)
    assert approved["request"]["status"] == "approved"

    executed = isolated_runtime.mission_control.mc_execute_capability_request(request_id)

    assert executed["ok"] is True
    assert executed["status"] == "executed"
    assert executed["invocation"]["execution_mode"] == "mutating-exec"
    result = executed["invocation"].get("result") or {}
    assert result.get("type") == "mutating-exec"
    assert result.get("command_text") == f"cp {source} {target}"
    assert result.get("mutation_permitted") is True
    assert result.get("sudo_permitted") is False
    assert result.get("external_mutation_permitted") is True
    assert target.read_text(encoding="utf-8") == "bounded mutating exec\n"


def test_tools_guidance_is_updated_in_default_and_template_for_exec_capability() -> None:
    default_tools = Path("/media/projects/jarvis-v2/workspace/default/TOOLS.md").read_text(
        encoding="utf-8"
    )
    template_tools = Path("/media/projects/jarvis-v2/workspace/templates/TOOLS.md").read_text(
        encoding="utf-8"
    )

    assert "tool:run-non-destructive-command" in default_tools
    assert "## EXEC_COMMAND: run non-destructive command" in default_tools
    assert "## EXEC_COMMAND: run non-destructive command" in template_tools
    assert "command_from: user-message" in default_tools
    assert "command_from: user-message" in template_tools
    assert "Tiny bounded git read/inspect commands such as `git status`, `git diff --stat`, `git diff --name-only`, `git log --oneline -n N`, and `git branch --show-current` are allowed." in default_tools
    assert "Common system-inspection commands such as `lscpu`, `lshw`, `free`, `lsblk`, `df`, `lspci`, `nvidia-smi`, `nproc`, `uptime`, and `hostnamectl` are also allowed." in default_tools
    assert "allows a tiny bounded git read/inspect subset" in template_tools
    assert "allows common system-inspection commands such as `lscpu`, `lshw`, `free`, `lsblk`, `df`, `lspci`, `nvidia-smi`, `nproc`, `uptime`, and `hostnamectl`" in template_tools
    assert "permits read-only shell composition such as pipes, `&&`, `||`, `;`, and globbing when every segment stays non-destructive" in template_tools
    assert "runtime classifies it into a small repo stewardship set such as `git-stage`, `git-commit`, `git-sync`, `git-branch-switch`, `git-history-rewrite`, `git-stash`, or `git-other-mutate`." in default_tools
    assert "runtime classifies it into a small repo stewardship set such as `git-stage`, `git-commit`, `git-sync`, `git-branch-switch`, `git-history-rewrite`, `git-stash`, or `git-other-mutate`." in template_tools
    assert "`git clean` stays blocked." in default_tools
    assert "`git clean` stays blocked." in template_tools
    assert "exact bounded non-sudo command" in default_tools
    assert "exact bounded non-sudo command" in template_tools
    assert "tiny bounded sudo allowlist" in default_tools
    assert "tiny bounded sudo allowlist" in template_tools
    assert "short auto-expiring sudo approval window" in default_tools
    assert "short auto-expiring sudo approval window" in template_tools


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


def test_capability_results_are_normalized_for_success_and_approval(isolated_runtime) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    executed = caps_mod.invoke_workspace_capability(
        "tool:read-workspace-memory",
    )
    assert executed["status"] == "executed"
    assert executed["ok"] is True
    assert executed["error"] is False
    assert executed["status_family"] == "success"
    assert executed["message"] == executed["detail"]
    assert str(executed["detail"]).strip()

    approval = caps_mod.invoke_workspace_capability("tool:propose-workspace-memory-update")
    assert approval["status"] == "approval-required"
    assert approval["ok"] is False
    assert approval["error"] is False
    assert approval["status_family"] == "approval"
    assert approval["message"] == approval["detail"]
    assert "approval" in str(approval["detail"]).lower()


def test_capability_results_are_normalized_for_missing_capabilities(isolated_runtime) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    missing = caps_mod.invoke_workspace_capability("tool:does-not-exist")

    assert missing["status"] == "not-found"
    assert missing["ok"] is False
    assert missing["error"] is True
    assert missing["status_family"] == "missing"
    assert missing["message"] == missing["detail"]
    assert str(missing["detail"]).strip()


def test_workspace_memory_write_merges_without_deleting_existing_content(isolated_runtime) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    merged = caps_mod._merge_workspace_memory_content(
        existing_content="## Curated Memory\n\n- Existing fact.\n",
        incoming_content="- Existing fact.\n- New fact.\n",
    )

    assert "- Existing fact." in merged
    assert "- New fact." in merged
    assert merged.count("- Existing fact.") == 1


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


def test_approved_sudo_exec_runs_for_exact_approved_command(
    isolated_runtime,
    monkeypatch,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    workspace_dir = Path(caps_mod.load_workspace_capabilities().get("workspace") or "")
    target = workspace_dir / "sudo_exec_target.txt"
    target.write_text("sudo execution target\n", encoding="utf-8")

    def _fake_run_bounded_command(*, argv, workspace_dir):
        return subprocess.CompletedProcess(argv, 0, "", ""), None

    monkeypatch.setattr(caps_mod, "_run_bounded_command", _fake_run_bounded_command)

    proposed = isolated_runtime.mission_control.mc_invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text=f"sudo chmod 600 {target}",
    )
    assert proposed["status"] == "approval-required"
    assert proposed["execution_mode"] == "sudo-exec-proposal"

    request_id = str((isolated_runtime.db.latest_capability_approval_request(
        execution_mode="sudo-exec-proposal",
        include_executed=False,
    ) or {}).get("request_id") or "")
    assert request_id

    approved = isolated_runtime.mission_control.mc_approve_capability_request(request_id)
    assert approved["request"]["status"] == "approved"

    executed = isolated_runtime.mission_control.mc_execute_capability_request(request_id)
    assert executed["ok"] is True
    assert executed["status"] == "executed"
    assert executed["invocation"]["execution_mode"] == "sudo-exec"
    result = executed["invocation"].get("result") or {}
    assert result.get("type") == "sudo-exec"
    assert result.get("command_text") == f"sudo chmod 600 {target}"
    assert result.get("workspace_scoped") is True
    assert result.get("mutation_permitted") is True
    assert result.get("sudo_permitted") is True
    assert result.get("external_mutation_permitted") is False


def test_approved_sudo_exec_outside_allowlist_stays_blocked(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    proposed = isolated_runtime.mission_control.mc_invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text="sudo ls /root",
    )
    assert proposed["status"] == "approval-required"
    assert proposed["execution_mode"] == "sudo-exec-proposal"

    request_id = str((isolated_runtime.db.latest_capability_approval_request(
        execution_mode="sudo-exec-proposal",
        include_executed=False,
    ) or {}).get("request_id") or "")
    assert request_id

    approved = isolated_runtime.mission_control.mc_approve_capability_request(request_id)
    assert approved["request"]["status"] == "approved"

    executed = isolated_runtime.mission_control.mc_execute_capability_request(request_id)
    assert executed["ok"] is False
    assert executed["status"] == "blocked-sudo-command-class"


def test_sudo_exec_execution_rejects_command_mismatch_against_approved_proposal(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    workspace_dir = Path(caps_mod.load_workspace_capabilities().get("workspace") or "")
    target = workspace_dir / "sudo_exec_mismatch_target.txt"
    target.write_text("sudo execution mismatch target\n", encoding="utf-8")

    _ = isolated_runtime.mission_control.mc_invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text=f"sudo chmod 600 {target}",
    )
    request_id = str((isolated_runtime.db.latest_capability_approval_request(
        execution_mode="sudo-exec-proposal",
        include_executed=False,
    ) or {}).get("request_id") or "")
    assert request_id
    _ = isolated_runtime.mission_control.mc_approve_capability_request(request_id)

    executed = isolated_runtime.mission_control.mc_execute_capability_request(
        request_id,
        command_text=f"sudo chmod 644 {target}",
    )

    assert executed["ok"] is False
    assert executed["status"] == "proposal-content-mismatch"


def test_pending_sudo_exec_can_reuse_active_approval_window(
    isolated_runtime,
    monkeypatch,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    workspace_dir = Path(caps_mod.load_workspace_capabilities().get("workspace") or "")
    target_one = workspace_dir / "sudo_exec_window_one.txt"
    target_two = workspace_dir / "sudo_exec_window_two.txt"
    target_one.write_text("window one\n", encoding="utf-8")
    target_two.write_text("window two\n", encoding="utf-8")

    def _fake_run_bounded_command(*, argv, workspace_dir):
        return subprocess.CompletedProcess(argv, 0, "", ""), None

    monkeypatch.setattr(caps_mod, "_run_bounded_command", _fake_run_bounded_command)

    proposed_one = isolated_runtime.mission_control.mc_invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text=f"sudo chmod 600 {target_one}",
    )
    assert proposed_one["execution_mode"] == "sudo-exec-proposal"
    request_one = str((isolated_runtime.db.latest_capability_approval_request(
        execution_mode="sudo-exec-proposal",
        include_executed=False,
    ) or {}).get("request_id") or "")
    assert request_one
    _ = isolated_runtime.mission_control.mc_approve_capability_request(request_one)
    executed_one = isolated_runtime.mission_control.mc_execute_capability_request(request_one)
    assert executed_one["ok"] is True

    proposed_two = isolated_runtime.mission_control.mc_invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text=f"sudo chmod 644 {target_two}",
    )
    assert proposed_two["status"] == "approval-required"
    request_two = str((isolated_runtime.db.latest_capability_approval_request(
        execution_mode="sudo-exec-proposal",
        include_executed=False,
    ) or {}).get("request_id") or "")
    assert request_two and request_two != request_one

    executed_two = isolated_runtime.mission_control.mc_execute_capability_request(request_two)

    assert executed_two["ok"] is True
    assert executed_two["status"] == "executed"
    assert executed_two["request"]["status"] == "approved"
    assert executed_two["invocation"]["execution_mode"] == "sudo-exec"


def test_mutating_exec_execution_rejects_command_mismatch_against_approved_proposal(
    isolated_runtime,
) -> None:
    caps_mod = importlib.import_module("core.tools.workspace_capabilities")
    caps_mod = importlib.reload(caps_mod)

    source = Path("/tmp/jarvis_mutating_exec_mismatch_source.txt")
    target = Path("/tmp/jarvis_mutating_exec_mismatch_target.txt")
    source.write_text("fingerprint baseline\n", encoding="utf-8")

    _ = isolated_runtime.mission_control.mc_invoke_workspace_capability(
        "tool:run-non-destructive-command",
        command_text=f"cp {source} {target}",
    )
    request_id = str((isolated_runtime.db.latest_capability_approval_request(
        execution_mode="mutating-exec-proposal",
        include_executed=False,
    ) or {}).get("request_id") or "")
    assert request_id
    _ = isolated_runtime.mission_control.mc_approve_capability_request(request_id)

    executed = isolated_runtime.mission_control.mc_execute_capability_request(
        request_id,
        command_text=f"chmod 644 {source}",
    )

    assert executed["ok"] is False
    assert executed["status"] == "proposal-content-mismatch"
