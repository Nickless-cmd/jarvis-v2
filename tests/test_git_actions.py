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
