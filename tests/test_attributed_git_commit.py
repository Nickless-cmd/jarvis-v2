from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from core.services.attributed_git_commit import commit_with_attribution
from core.services.commit_attribution import CommitAttribution


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=check,
    )


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    (tmp_path / "one.py").write_text("one = 1\n")
    (tmp_path / "two.py").write_text("two = 1\n")
    _git(tmp_path, "add", "one.py", "two.py")
    _git(tmp_path, "commit", "-qm", "initial")
    return tmp_path


def _attribution(**overrides: str) -> CommitAttribution:
    values = {
        "actor": "codex",
        "actor_type": "agent",
        "run_id": "task-1",
        "session_id": "none",
        "origin": "delegated",
        "approved_by": "bjorn",
    }
    values.update(overrides)
    return CommitAttribution(**values)


def test_commit_with_attribution_creates_only_requested_commit(git_repo: Path) -> None:
    (git_repo / "one.py").write_text("one = 2\n")
    (git_repo / "two.py").write_text("two = 2\n")
    _git(git_repo, "add", "one.py")

    result = commit_with_attribution(
        repo=git_repo,
        message="fix: update one",
        attribution=_attribution(),
        paths=("one.py",),
    )

    assert result.returncode == 0
    body = _git(git_repo, "show", "-s", "--format=%B", "HEAD").stdout
    assert "Actor: codex" in body
    assert "Run-ID: task-1" in body
    assert "two.py" in _git(git_repo, "status", "--short").stdout


def test_executor_does_not_stage_unstaged_path(git_repo: Path) -> None:
    (git_repo / "one.py").write_text("one = 3\n")

    result = commit_with_attribution(
        repo=git_repo,
        message="fix: should not stage",
        attribution=_attribution(),
        paths=("one.py",),
    )

    assert result.returncode != 0
    assert _git(git_repo, "log", "-1", "--format=%s").stdout.strip() == "initial"


def test_executor_can_preserve_explicit_author(git_repo: Path) -> None:
    (git_repo / "one.py").write_text("one = 4\n")
    _git(git_repo, "add", "one.py")

    result = commit_with_attribution(
        repo=git_repo,
        message="fix: authored",
        attribution=_attribution(actor="jarvis", origin="interactive"),
        paths=("one.py",),
        author="Jarvis <jarvis@srvlab.dk>",
    )

    assert result.returncode == 0
    assert _git(git_repo, "show", "-s", "--format=%an <%ae>").stdout.strip() == (
        "Jarvis <jarvis@srvlab.dk>"
    )


def test_executor_rejects_invalid_attribution_before_git(git_repo: Path) -> None:
    before = _git(git_repo, "rev-parse", "HEAD").stdout.strip()

    result = commit_with_attribution(
        repo=git_repo,
        message="fix: invalid",
        attribution=_attribution(actor="attacker"),
    )

    assert result.returncode == 2
    assert "unknown Actor" in result.stderr
    assert _git(git_repo, "rev-parse", "HEAD").stdout.strip() == before


def test_executor_rewrites_managed_trailers_on_amend(git_repo: Path) -> None:
    (git_repo / "one.py").write_text("one = 5\n")
    _git(git_repo, "add", "one.py")
    first = commit_with_attribution(
        repo=git_repo,
        message="fix: first",
        attribution=_attribution(actor="opus", run_id="task-old"),
        paths=("one.py",),
    )
    assert first.returncode == 0
    old_message = _git(git_repo, "show", "-s", "--format=%B", "HEAD").stdout

    amended = commit_with_attribution(
        repo=git_repo,
        message=old_message,
        attribution=_attribution(run_id="task-new"),
        amend=True,
    )

    assert amended.returncode == 0
    body = _git(git_repo, "show", "-s", "--format=%B", "HEAD").stdout
    assert "Actor: codex" in body
    assert "Actor: opus" not in body
    assert "Run-ID: task-new" in body
    assert body.count("Run-ID:") == 1


def test_cli_imports_core_and_creates_attributed_commit(git_repo: Path) -> None:
    (git_repo / "one.py").write_text("one = 6\n")
    _git(git_repo, "add", "one.py")
    script = Path(__file__).resolve().parents[1] / "scripts" / "commit_with_attribution.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--repo",
            str(git_repo),
            "--message",
            "fix: cli",
            "--actor",
            "codex",
            "--run-id",
            "task-cli",
            "--session-id",
            "none",
            "--origin",
            "delegated",
            "--approved-by",
            "bjorn",
            "--path",
            "one.py",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "commit=" in result.stdout
    body = _git(git_repo, "show", "-s", "--format=%B", "HEAD").stdout
    assert "Actor: codex" in body
    assert "Run-ID: task-cli" in body


# ---------------------------------------------------------------------------
# Jarvis 4. sep: «git commit showed exit 1 (pre-commit hooks "Passed") and the
# tree was clean afterwards — I re-ran the commit believing it failed.»
# En commit der melder fejl efter at være lykkedes inviterer til dubletter.
# ---------------------------------------------------------------------------

def _repo_med_hook(tmp_path, hook_body: str):
    """Et rigtigt git-repo hvor en hook melder fejl EFTER at commit'en er lavet."""
    import subprocess
    repo = tmp_path / "r"
    repo.mkdir()
    run = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True)
    run("init", "-q", "-b", "main")
    run("config", "user.email", "t@t")
    run("config", "user.name", "T")
    (repo / "a.txt").write_text("1\n")
    run("add", "a.txt")
    run("commit", "-q", "-m", "start")
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(exist_ok=True)
    h = hooks / "post-commit"
    h.write_text(hook_body)
    h.chmod(0o755)
    return repo, run


def test_head_afgoer_udfaldet_ikke_exit_koden(tmp_path, monkeypatch):
    """Sandheden står i repoet, ikke i exit-koden.

    Jarvis så «exit 1» på en commit der VAR lavet og genkørte den. Jeg kunne
    ikke konstruere den situation med en rigtig hook — git ignorerer
    `post-commit`s exit-kode, og alt der fejler FØR den afbryder commit'en. Den
    mest sandsynlige forklaring er derfor en pipeline: `git commit … | grep …`
    giver exit 1 når grep intet finder, selv om commit'en lykkedes.

    Vagten koster ingenting og dækker klassen: melder git fejl, men HEAD har
    flyttet sig, ER der committet. Her tvinges den frem, fordi jeg ikke vil
    efterlade en gren der aldrig er kørt.
    """
    import subprocess
    from core.services import attributed_git_commit as m

    repo, run = _repo_med_hook(tmp_path, "#!/bin/sh\nexit 0\n")
    (repo / "a.txt").write_text("2\n")
    run("add", "a.txt")

    ægte_git = m._git
    def _git_der_lyver(root, *args, **kw):
        res = ægte_git(root, *args, **kw)
        if args and args[0] == "commit":
            res.returncode = 1          # commit'en ER lavet; kun koden lyver
        return res
    monkeypatch.setattr(m, "_git", _git_der_lyver)

    res = m.commit_with_attribution(
        repo=repo, message="test",
        attribution=m.CommitAttribution(
            actor="opus", actor_type="agent", run_id="r", session_id="none",
            origin="interactive", approved_by="bjorn"),
        paths=("a.txt",),
    )
    assert res.returncode == 0, "en lykket commit må ikke rapporteres som fejl"
    assert res.sha == run("rev-parse", "HEAD").stdout.strip()
    assert "dublet" in (res.stdout or ""), "brugeren skal advares mod at køre igen"


def test_en_ÆGTE_fejlet_commit_er_stadig_en_fejl(tmp_path):
    """Vagten må ikke gøre alle fejl til succes."""
    import subprocess
    from core.services.attributed_git_commit import commit_with_attribution, CommitAttribution

    repo, run = _repo_med_hook(tmp_path, "#!/bin/sh\nexit 0\n")
    # pre-commit der afviser → HEAD flytter sig IKKE
    pre = repo / ".git" / "hooks" / "pre-commit"
    pre.write_text("#!/bin/sh\nexit 1\n")
    pre.chmod(0o755)
    (repo / "a.txt").write_text("3\n")
    run("add", "a.txt")
    før = run("rev-parse", "HEAD").stdout.strip()

    res = commit_with_attribution(
        repo=repo, message="test",
        attribution=CommitAttribution(
            actor="opus", actor_type="agent", run_id="r", session_id="none",
            origin="interactive", approved_by="bjorn"),
        paths=("a.txt",),
    )
    assert run("rev-parse", "HEAD").stdout.strip() == før
    assert res.returncode != 0, "en commit der IKKE blev lavet skal melde fejl"
