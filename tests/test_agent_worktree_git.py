"""C5a: git-hjaelpere - rigtige repos i tmp, ingen mocks af git."""
from __future__ import annotations

import os
import subprocess

import pytest

from core.services import agent_worktree_git as g

ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": "/dev/null"}


def sh(*a, cwd):
    subprocess.run(a, cwd=cwd, env=ENV, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "ws" / "proj"
    r.mkdir(parents=True)
    sh("git", "init", "-q", "-b", "main", cwd=r)
    (r / "a.txt").write_text("a\n")
    (r / "b.txt").write_text("b\n")
    sh("git", "add", "-A", cwd=r)
    sh("git", "commit", "-q", "-m", "init", cwd=r)
    return str(r)


def test_validate_repo_accepts_a_toplevel_under_an_allowed_root(repo, tmp_path):
    assert g.validate_repo(repo, [str(tmp_path / "ws")]) == os.path.realpath(repo)


@pytest.mark.parametrize("bad", ["uden-for-rod", "undermappe", "findes-ikke", "symlink"])
def test_validate_repo_refuses_everything_else(repo, tmp_path, bad):
    ws = str(tmp_path / "ws")
    if bad == "uden-for-rod":
        path, roots = repo, [str(tmp_path / "andet")]
    elif bad == "undermappe":
        sub = os.path.join(repo, "src"); os.makedirs(sub)
        path, roots = sub, [ws]
    elif bad == "findes-ikke":
        path, roots = os.path.join(ws, "nej"), [ws]
    else:
        outside = tmp_path / "udenfor"; outside.mkdir(); sh("git", "init", "-q", cwd=outside)
        os.symlink(outside, os.path.join(ws, "link"))
        path, roots = os.path.join(ws, "link"), [ws]
    with pytest.raises(g.GitError):
        g.validate_repo(path, roots)


def test_bare_repos_are_refused(tmp_path):
    bare = tmp_path / "ws" / "bare.git"
    bare.mkdir(parents=True)
    sh("git", "init", "-q", "--bare", cwd=bare)
    with pytest.raises(g.GitError):
        g.validate_repo(str(bare), [str(tmp_path / "ws")])


@pytest.mark.parametrize("ref", ["--upload-pack=x", "a..b", "x y", "-f", "ref.lock", ""[:0] + "$(id)"])
def test_unsafe_refs_are_refused(ref):
    with pytest.raises(g.GitError):
        g.safe_ref(ref)


def test_a_worktree_diff_covers_edits_new_deleted_and_binary_files(repo, tmp_path):
    base = g.resolve_commit(repo)
    path = str(tmp_path / "wt")
    g.add_worktree(repo, path, "agent/x1", base)
    gitdir = g.read_gitdir(repo, path)
    open(os.path.join(path, "a.txt"), "w").write("a\nny linje\n")
    os.unlink(os.path.join(path, "b.txt"))
    open(os.path.join(path, "ny.txt"), "w").write("ny\n")
    open(os.path.join(path, "bin.dat"), "wb").write(bytes(range(256)))
    files = {f["path"]: f["status"] for f in g.changed_files(gitdir, path, base)}
    assert files == {"a.txt": "M", "b.txt": "D", "ny.txt": "A", "bin.dat": "A"}
    diff = g.diff_against(gitdir, path, base)
    assert b"+ny linje" in diff and b"-b" in diff and b"GIT binary patch" in diff
    assert g.commits_since(gitdir, path, base) == []


def test_commits_made_in_the_worktree_are_listed_and_bundled(repo, tmp_path):
    base = g.resolve_commit(repo)
    path = str(tmp_path / "wt")
    g.add_worktree(repo, path, "agent/x2", base)
    gitdir = g.read_gitdir(repo, path)
    open(os.path.join(path, "c.txt"), "w").write("c\n")
    sh("git", "add", "-A", cwd=path)
    sh("git", "commit", "-q", "-m", "agentens commit", cwd=path)
    assert len(g.commits_since(gitdir, path, base)) == 1
    assert g.make_bundle(repo, "agent/x2", base, str(tmp_path / "b.bundle")) is True
    assert (tmp_path / "b.bundle").stat().st_size > 0
    assert g.make_bundle(repo, "main", base, str(tmp_path / "tom.bundle")) is False     # ingen commits


def test_a_tampered_dot_git_file_cannot_redirect_the_servers_git_commands(repo, tmp_path):
    """Agenten ejer worktree'et og kan omskrive .git-filen. Serveren bruger det GEMTE gitdir."""
    base = g.resolve_commit(repo)
    path = str(tmp_path / "wt")
    g.add_worktree(repo, path, "agent/x3", base)
    gitdir = g.read_gitdir(repo, path)
    other = tmp_path / "andet-repo"; other.mkdir(); sh("git", "init", "-q", cwd=other)
    (other / "hemmelig.txt").write_text("HEMMELIGT")
    sh("git", "add", "-A", cwd=other); sh("git", "commit", "-q", "-m", "x", cwd=other)
    open(os.path.join(path, ".git"), "w").write(f"gitdir: {other}/.git\n")
    open(os.path.join(path, "a.txt"), "w").write("aendret\n")
    files = {f["path"] for f in g.changed_files(gitdir, path, base)}
    assert "a.txt" in files and "hemmelig.txt" not in files and ".git" not in files


def test_read_gitdir_refuses_a_gitdir_outside_the_main_repo(repo, tmp_path):
    path = tmp_path / "falsk"
    path.mkdir()
    (path / ".git").write_text(f"gitdir: {tmp_path}/ude/.git\n")
    with pytest.raises(g.GitError):
        g.read_gitdir(repo, str(path))
    (path / ".git").write_text("noget andet\n")
    with pytest.raises(g.GitError):
        g.read_gitdir(repo, str(path))


def test_hooks_never_run(repo, tmp_path):
    hook = os.path.join(repo, ".git", "hooks", "post-checkout")
    open(hook, "w").write(f"#!/bin/sh\ntouch {tmp_path}/HOOK-KOERTE\n")
    os.chmod(hook, 0o755)
    g.add_worktree(repo, str(tmp_path / "wt"), "agent/x4", g.resolve_commit(repo))
    assert not (tmp_path / "HOOK-KOERTE").exists()


def test_remove_worktree_is_idempotent_and_deletes_the_branch(repo, tmp_path):
    path = str(tmp_path / "wt")
    g.add_worktree(repo, path, "agent/x5", g.resolve_commit(repo))
    g.remove_worktree(repo, path, "agent/x5")
    g.remove_worktree(repo, path, "agent/x5")
    assert not os.path.exists(path)
    assert "agent/x5" not in subprocess.run(["git", "branch"], cwd=repo, capture_output=True, text=True).stdout


def test_tree_size_does_not_follow_symlinks_out(tmp_path):
    big = tmp_path / "stor"; big.mkdir(); (big / "f").write_bytes(b"x" * 5000)
    d = tmp_path / "d"; d.mkdir(); (d / "lille").write_bytes(b"y" * 10)
    os.symlink(big, d / "link")
    assert g.tree_size(str(d)) < 5000


def test_path_is_inside_rejects_the_root_itself_and_siblings(tmp_path):
    root = tmp_path / "rod"; root.mkdir()
    (tmp_path / "rod-ved-siden").mkdir()
    assert g.path_is_inside(str(root / "a" / "b"), str(root)) is True
    assert g.path_is_inside(str(root), str(root)) is False
    assert g.path_is_inside(str(tmp_path / "rod-ved-siden"), str(root)) is False
    assert g.path_is_inside(str(root / ".." / "rod-ved-siden"), str(root)) is False
