from unittest.mock import patch, MagicMock
from core.services import git_actions


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
    with patch("subprocess.run", side_effect=fake_run):
        res = git_actions.commit_all_container("/repo", "min besked")
    assert res["status"] == "ok"
    assert res["sha"] == "abc1234"
    assert res["branch"] == "main"


def test_commit_all_workstation_routes_uid():
    seen = {}

    def fake_exec(name, args):
        seen["name"] = name
        seen["args"] = args
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
    assert seen["args"]["_user_id"] == "u123"


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
         patch("core.services.github_connector.create_pr",
               return_value={"status": "ok", "url": "https://github.com/o/r/pull/9"}) as cp:
        res = git_actions.create_pr({"kind": "container", "root": "repo"}, "/repo", "u", "Titel", "B")
    assert res["status"] == "ok"
    assert res["url"] == "https://github.com/o/r/pull/9"
    assert res["via"] == "api"
    assert cp.call_args.kwargs["head"] == "feat/x"
    assert cp.call_args.kwargs["base"] == "main"
