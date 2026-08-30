from unittest.mock import patch, MagicMock
from core.services import git_actions
from core.services.attributed_git_commit import AttributedCommitResult


def _cp(rc=0, out="", err=""):
    m = MagicMock()
    m.returncode = rc
    m.stdout = out
    m.stderr = err
    return m


def test_commit_all_container_ok():
    # args = ["git", "-C", repo, <subcmd>, ...] → subkommando er args[3].
    def fake_run(args, **kw):
        sub = args[3] if len(args) > 3 else ""
        if sub == "rev-parse":
            return _cp(0, "abc1234\n")
        if sub == "branch":
            return _cp(0, "main\n")
        return _cp(0, "")
    with patch("subprocess.run", side_effect=fake_run), patch.object(
        git_actions,
        "commit_with_attribution",
        return_value=AttributedCommitResult(0, sha="abc1234"),
    ) as commit:
        res = git_actions.commit_all_container("/repo", "min besked")
    assert res["status"] == "ok"
    assert res["sha"] == "abc1234"
    assert res["branch"] == "main"
    attribution = commit.call_args.kwargs["attribution"]
    assert attribution.actor == "bjorn"
    assert attribution.origin == "interactive"
    assert attribution.approved_by == "bjorn"


def test_commit_all_workstation_routes_uid():
    seen = []

    def fake_exec(name, args):
        seen.append((name, args))
        cmd = args["command"]
        if "rev-parse" in cmd:
            return {"status": "ok", "result": {"stdout": "def5678\n", "exit_code": 0}}
        if "branch --show-current" in cmd:
            return {"status": "ok", "result": {"stdout": "feat/x\n", "exit_code": 0}}
        return {"status": "ok", "result": {"stdout": "", "stderr": "", "exit_code": 0}}

    with patch.object(git_actions, "_operator_exec", side_effect=fake_exec):
        res = git_actions.commit_all_workstation("/home/u/proj", "u123", "msg")
    assert res["status"] == "ok"
    assert res["sha"] == "def5678"
    assert all(args["_user_id"] == "u123" for _, args in seen)
    commit_cmd = next(
        args["command"] for _, args in seen
        if "commit_with_attribution.py" in args["command"]
    )
    assert "--actor bjorn" in commit_cmd
    assert "--origin interactive" in commit_cmd
    assert "--approved-by bjorn" in commit_cmd
    assert "git commit" not in commit_cmd


def test_commit_all_dispatch():
    with patch.object(git_actions, "commit_all_container", return_value={"status": "ok"}) as c, \
         patch.object(git_actions, "commit_all_workstation", return_value={"status": "ok"}) as w:
        git_actions.commit_all({"kind": "container", "root": "repo"}, "/repo", "u", "m")
        git_actions.commit_all({"kind": "workstation", "root": "/p"}, "/repo", "u", "m")
    c.assert_called_once()
    w.assert_called_once()


def test_parse_remote_owner_repo():
    assert git_actions.parse_owner_repo("git@github.com:Nickless-cmd/jarvis-v2.git") == "Nickless-cmd/jarvis-v2"
    assert git_actions.parse_owner_repo("https://github.com/o/r.git") == "o/r"
    assert git_actions.parse_owner_repo("https://github.com/o/r") == "o/r"
    assert git_actions.parse_owner_repo("") == ""


def test_create_pr_container_api_path():
    def fake_run(args, **kw):
        sub = args[3] if len(args) > 3 else ""
        if sub == "symbolic-ref":
            return _cp(0, "refs/remotes/origin/main\n")
        if sub == "branch":
            return _cp(0, "feat/x\n")  # ikke på default → ingen ny branch
        if sub == "remote":
            return _cp(0, "git@github.com:o/r.git\n")
        return _cp(0, "")
    with patch("subprocess.run", side_effect=fake_run), \
         patch.object(
             git_actions,
             "commit_with_attribution",
             return_value=AttributedCommitResult(0, sha="abc1234"),
         ) as commit, \
         patch("core.services.github_connector.create_pr",
               return_value={"status": "ok", "url": "https://github.com/o/r/pull/9"}) as cp:
        res = git_actions.create_pr({"kind": "container", "root": "repo"}, "/repo", "u", "Titel", "B")
    assert res["status"] == "ok"
    assert res["url"] == "https://github.com/o/r/pull/9"
    assert res["via"] == "api"
    assert cp.call_args.kwargs["head"] == "feat/x"
    assert cp.call_args.kwargs["base"] == "main"
    assert commit.call_args.kwargs["attribution"].actor == "bjorn"


def test_create_pr_workstation_uses_attributed_cli_before_push():
    commands = []

    def fake_exec(name, args):
        command = args["command"]
        commands.append(command)
        stdout = ""
        if "symbolic-ref" in command:
            stdout = "refs/remotes/origin/main\n"
        elif "branch --show-current" in command:
            stdout = "feat/x\n"
        elif "remote get-url" in command:
            stdout = "git@github.com:o/r.git\n"
        return {
            "status": "ok",
            "result": {"stdout": stdout, "stderr": "", "exit_code": 0},
        }

    with patch.object(git_actions, "_operator_exec", side_effect=fake_exec), patch(
        "core.services.github_connector.create_pr",
        return_value={"status": "ok", "url": "https://github.com/o/r/pull/10"},
    ):
        result = git_actions.create_pr(
            {"kind": "workstation", "root": "/home/u/proj"},
            "/repo",
            "u123",
            "Titel med mellemrum",
            "Body",
        )

    assert result["status"] == "ok"
    commit_index = next(
        index for index, command in enumerate(commands)
        if "commit_with_attribution.py" in command
    )
    push_index = next(
        index for index, command in enumerate(commands)
        if "push -u origin" in command
    )
    assert commit_index < push_index
    assert "--actor bjorn" in commands[commit_index]
    assert "'Titel med mellemrum'" in commands[commit_index]
