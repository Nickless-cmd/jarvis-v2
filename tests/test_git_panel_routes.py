"""Git-panelets ruter, mod et RIGTIGT lille git-repo (som test_git_workspace_actions).

Mocks kan ikke se om git-argumenterne er gyldige, så repoet er ægte. Det eneste
der erstattes er `_mål` — owner-gaten og repo-opslaget i chat.py — så ruterne
peger på et tmp-repo i stedet for serverens eget.
"""
from __future__ import annotations

import subprocess

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.jarvis_api.routes import git_panel
from core.services.commit_attribution import MANAGED_TRAILERS


def _git(r, *a):
    return subprocess.run(["git", "-C", str(r), *a], capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-b", "main")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    (r / "f.txt").write_text("hej\n")
    _git(r, "add", ".")
    _git(r, "commit", "-m", "start")
    return r


@pytest.fixture
def klient(repo, monkeypatch):
    monkeypatch.setattr(git_panel, "_mål", lambda kind, root: ("container", str(repo), ""))
    app = FastAPI()
    app.include_router(git_panel.router)
    return TestClient(app)


P = "/chat/git-panel"


# ── rene parsere ────────────────────────────────────────────────────────────

def test_parse_status_laeser_branch_tracking_og_filer() -> None:
    tekst = (
        "## main...origin/main [ahead 2, behind 1]\n"
        "M  staged.py\n"
        " M ændret.py\n"
        "MM begge.py\n"
        "?? ny.py\n"
        'R  gammel.py -> "nyt navn.py"\n'
        "UU konflikt.py\n"
    )
    s = git_panel.parse_status(tekst)
    assert (s["branch"], s["upstream"], s["ahead"], s["behind"]) == ("main", "origin/main", 2, 1)
    by = {f["path"]: f for f in s["files"]}
    assert by["staged.py"]["staged"] and not by["staged.py"]["unstaged"]
    assert by["ændret.py"]["unstaged"] and not by["ændret.py"]["staged"]
    assert by["begge.py"]["staged"] and by["begge.py"]["unstaged"]
    assert by["ny.py"]["untracked"]
    assert by["nyt navn.py"]["old_path"] == "gammel.py"
    assert by["konflikt.py"]["conflict"]
    assert s["dirty"] == 6


def test_parse_status_uden_upstream_og_afkoblet_head() -> None:
    assert git_panel.parse_status("## main\n")["upstream"] == ""
    assert git_panel.parse_status("## No commits yet on main\n")["branch"] == "main"
    s = git_panel.parse_status("## HEAD (no branch)\n")
    assert s["detached"] and s["branch"] == "HEAD"


def test_parse_worktrees_markerer_hovedtraeet() -> None:
    tekst = (
        "worktree /a\nHEAD abcdef1234567890\nbranch refs/heads/main\n\n"
        "worktree /b\nHEAD 1111111111111111\ndetached\n"
    )
    t = git_panel.parse_worktrees(tekst)
    assert [x["path"] for x in t] == ["/a", "/b"]
    assert t[0]["main"] and t[0]["branch"] == "main"
    assert not t[1]["main"] and t[1]["detached"]


@pytest.mark.parametrize("farlig", ["", "-rf", "/etc/passwd", "../uden", "a/../../b"])
def test_rens_sti_afviser_flag_absolutte_og_opadgaaende(farlig) -> None:
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as e:
        git_panel.rens_sti(farlig)
    assert e.value.status_code == 400


# ── status ──────────────────────────────────────────────────────────────────

def test_status_paa_rent_repo(klient) -> None:
    d = klient.get(f"{P}/status").json()
    assert d["ok"] is True
    assert d["branch"] == "main"
    assert d["dirty"] == 0 and d["files"] == []


def test_status_ser_aendret_og_ny_fil(klient, repo) -> None:
    (repo / "f.txt").write_text("hej\nmere\n")
    (repo / "ny fil.txt").write_text("x\n")
    d = klient.get(f"{P}/status").json()
    by = {f["path"]: f for f in d["files"]}
    assert by["f.txt"]["unstaged"] and not by["f.txt"]["staged"]
    assert by["ny fil.txt"]["untracked"]  # sti med mellemrum overlever citeringen


# ── diff ────────────────────────────────────────────────────────────────────

def test_diff_for_en_fil_viser_kun_den_fil(klient, repo) -> None:
    (repo / "f.txt").write_text("hej\nmere\n")
    (repo / "g.txt").write_text("g\n")
    _git(repo, "add", "g.txt")
    _git(repo, "commit", "-m", "g")
    (repo / "g.txt").write_text("g2\n")
    d = klient.get(f"{P}/diff", params={"path": "f.txt"}).json()
    assert d["ok"] and "+mere" in d["diff"]
    assert "g.txt" not in d["diff"]


def test_samlet_diff_head_indeholder_alle_tracked(klient, repo) -> None:
    (repo / "f.txt").write_text("andet\n")
    d = klient.get(f"{P}/diff", params={"mode": "head"}).json()
    assert d["ok"] and "f.txt" in d["diff"]


def test_diff_af_ny_ukendt_fil(klient, repo) -> None:
    (repo / "ny.txt").write_text("nyt indhold\n")
    d = klient.get(f"{P}/diff", params={"path": "ny.txt"}).json()
    assert d["ok"] and "+nyt indhold" in d["diff"]


def test_diff_staged_adskilles_fra_unstaged(klient, repo) -> None:
    (repo / "f.txt").write_text("staged\n")
    _git(repo, "add", "f.txt")
    (repo / "f.txt").write_text("staged\nefterfoelgende\n")
    st = klient.get(f"{P}/diff", params={"path": "f.txt", "mode": "staged"}).json()["diff"]
    un = klient.get(f"{P}/diff", params={"path": "f.txt", "mode": "unstaged"}).json()["diff"]
    assert "+staged" in st and "efterfoelgende" not in st
    assert "+efterfoelgende" in un


def test_diff_afviser_ugyldig_mode_og_sti(klient) -> None:
    assert klient.get(f"{P}/diff", params={"mode": "vrøvl"}).status_code == 400
    assert klient.get(f"{P}/diff", params={"path": "../x"}).status_code == 400


def test_diff_afkortes_og_siger_det(klient, repo, monkeypatch) -> None:
    monkeypatch.setattr(git_panel, "MAX_DIFF_TEGN", 50)
    (repo / "f.txt").write_text("linje\n" * 200)
    d = klient.get(f"{P}/diff", params={"path": "f.txt"}).json()
    assert d["truncated"] is True and len(d["diff"]) == 50


# ── stage / unstage ─────────────────────────────────────────────────────────

def test_stage_og_unstage_flytter_filen_mellem_sektionerne(klient, repo) -> None:
    (repo / "f.txt").write_text("ændret\n")

    assert klient.post(f"{P}/stage", json={"paths": ["f.txt"]}).json()["ok"] is True
    f = klient.get(f"{P}/status").json()["files"][0]
    assert f["staged"] and not f["unstaged"]

    assert klient.post(f"{P}/unstage", json={"paths": ["f.txt"]}).json()["ok"] is True
    f = klient.get(f"{P}/status").json()["files"][0]
    assert f["unstaged"] and not f["staged"]
    # Unstage må aldrig rør indholdet.
    assert (repo / "f.txt").read_text() == "ændret\n"


def test_stage_kun_den_valgte_fil(klient, repo) -> None:
    (repo / "a.txt").write_text("a\n")
    (repo / "b.txt").write_text("b\n")
    klient.post(f"{P}/stage", json={"paths": ["a.txt"]})
    by = {f["path"]: f for f in klient.get(f"{P}/status").json()["files"]}
    assert by["a.txt"]["staged"] and not by["b.txt"]["staged"]


def test_stage_alle(klient, repo) -> None:
    (repo / "a.txt").write_text("a\n")
    (repo / "b.txt").write_text("b\n")
    klient.post(f"{P}/stage", json={"all": True})
    assert all(f["staged"] for f in klient.get(f"{P}/status").json()["files"])


def test_unstage_paa_repo_uden_commits_stager_ikke_en_sletning(tmp_path, monkeypatch) -> None:
    r = tmp_path / "tomt"
    r.mkdir()
    _git(r, "init", "-b", "main")
    (r / "x.txt").write_text("x\n")
    _git(r, "add", "x.txt")
    monkeypatch.setattr(git_panel, "_mål", lambda k, rt: ("container", str(r), ""))
    app = FastAPI(); app.include_router(git_panel.router)
    c = TestClient(app)
    assert c.post(f"{P}/unstage", json={"paths": ["x.txt"]}).json()["ok"] is True
    assert (r / "x.txt").exists()
    assert c.get(f"{P}/status").json()["files"][0]["untracked"]


def test_stage_kraever_paths_eller_all_og_afviser_flag(klient) -> None:
    assert klient.post(f"{P}/stage", json={"paths": []}).status_code == 400
    assert klient.post(f"{P}/stage", json={"paths": ["--all"]}).status_code == 400


# ── commit ──────────────────────────────────────────────────────────────────

def test_commit_tager_kun_staged_og_saetter_alle_trailere(klient, repo) -> None:
    (repo / "a.txt").write_text("a\n")
    (repo / "b.txt").write_text("b\n")
    klient.post(f"{P}/stage", json={"paths": ["a.txt"]})

    d = klient.post(f"{P}/commit", json={"message": "feat: tilføj a"}).json()
    assert d["ok"] is True and d["sha"]

    forrige = _git(repo, "show", "--name-only", "--format=", "HEAD").stdout.split()
    assert forrige == ["a.txt"]  # b.txt blev IKKE med
    krop = _git(repo, "log", "-1", "--format=%B").stdout
    for trailer in MANAGED_TRAILERS:
        assert f"{trailer}: " in krop, trailer
    # b.txt er stadig ucommittet
    assert [f["path"] for f in klient.get(f"{P}/status").json()["files"]] == ["b.txt"]


def test_commit_uden_staged_afvises_og_laver_ingen_commit(klient, repo) -> None:
    foer = _git(repo, "rev-parse", "HEAD").stdout
    (repo / "a.txt").write_text("a\n")  # ikke staged
    d = klient.post(f"{P}/commit", json={"message": "tom"}).json()
    assert d["ok"] is False and "staged" in d["error"].lower()
    assert _git(repo, "rev-parse", "HEAD").stdout == foer


def test_commit_klientens_egne_trailere_overskriver_ikke_attributionen(klient, repo) -> None:
    (repo / "a.txt").write_text("a\n")
    klient.post(f"{P}/stage", json={"paths": ["a.txt"]})
    klient.post(f"{P}/commit", json={"message": "x\n\nActor: opus\nActor-Type: agent"})
    krop = _git(repo, "log", "-1", "--format=%B").stdout
    assert krop.count("Actor: ") == 1 and "Actor: bjorn" in krop


def test_commit_afviser_tom_besked(klient) -> None:
    assert klient.post(f"{P}/commit", json={"message": "   "}).status_code == 400


# ── log ─────────────────────────────────────────────────────────────────────

def test_log_nyeste_foerst_og_respekterer_graense(klient, repo) -> None:
    for i in range(3):
        (repo / "f.txt").write_text(f"{i}\n")
        _git(repo, "commit", "-am", f"ændring {i}")
    d = klient.get(f"{P}/log", params={"limit": 2}).json()
    assert [c["subject"] for c in d["commits"]] == ["ændring 2", "ændring 1"]
    assert d["commits"][0]["short"] and d["commits"][0]["author"] == "t"


def test_log_paa_repo_uden_commits_er_tom_ikke_fejl(tmp_path, monkeypatch) -> None:
    r = tmp_path / "tomt"; r.mkdir(); _git(r, "init", "-b", "main")
    monkeypatch.setattr(git_panel, "_mål", lambda k, rt: ("container", str(r), ""))
    app = FastAPI(); app.include_router(git_panel.router)
    d = TestClient(app).get(f"{P}/log").json()
    assert d == {"ok": True, "commits": []}


# ── push ────────────────────────────────────────────────────────────────────

@pytest.fixture
def med_remote(repo, tmp_path):
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)], capture_output=True)
    _git(repo, "remote", "add", "origin", str(bare))
    return bare


def test_push_saetter_upstream_foerste_gang_og_pusher_nye_commits(klient, repo, med_remote) -> None:
    d = klient.post(f"{P}/push", json={}).json()
    assert d["ok"] is True and d["set_upstream"] is True

    (repo / "f.txt").write_text("ny\n")
    _git(repo, "commit", "-am", "mere")
    assert klient.get(f"{P}/status").json()["ahead"] == 1

    d = klient.post(f"{P}/push", json={}).json()
    assert d["ok"] is True and d["set_upstream"] is False
    assert klient.get(f"{P}/status").json()["ahead"] == 0
    oppe = subprocess.run(["git", "-C", str(med_remote), "log", "-1", "--format=%s", "main"],
                          capture_output=True, text=True).stdout.strip()
    assert oppe == "mere"


def test_push_uden_remote_fejler_med_git_begrundelse(klient) -> None:
    d = klient.post(f"{P}/push", json={}).json()
    assert d["ok"] is False and d["error"]


def test_push_afvises_paa_afkoblet_head(klient, repo, med_remote) -> None:
    _git(repo, "checkout", "--detach")
    d = klient.post(f"{P}/push", json={}).json()
    assert d["ok"] is False and "HEAD" in d["error"]


# ── worktrees ───────────────────────────────────────────────────────────────

def test_worktrees_lister_hovedtraeet_og_nyt_traeet(klient, repo, tmp_path) -> None:
    _git(repo, "worktree", "add", str(tmp_path / "wt"), "-b", "side")
    d = klient.get(f"{P}/worktrees").json()
    assert d["ok"] is True
    grene = {t["branch"] for t in d["worktrees"]}
    assert grene == {"main", "side"}
    hoved = next(t for t in d["worktrees"] if t["main"])
    assert hoved["current"] is True and hoved["branch"] == "main"


# ── auth ────────────────────────────────────────────────────────────────────

def test_ruterne_gaar_gennem_maal_og_ikke_fra_klientens_sti(repo, monkeypatch) -> None:
    """Owner-gaten sidder i `_mål`. Afvises den, må ingen git-kommando køre."""
    from fastapi import HTTPException

    def afvis(kind, root):
        raise HTTPException(status_code=403, detail="owner only")

    kørt = []
    monkeypatch.setattr(git_panel, "_mål", afvis)
    monkeypatch.setattr(git_panel, "_git", lambda *a, **k: kørt.append(a) or (True, [""]))
    app = FastAPI(); app.include_router(git_panel.router)
    c = TestClient(app)
    assert c.get(f"{P}/status").status_code == 403
    assert c.post(f"{P}/stage", json={"paths": ["f.txt"]}).status_code == 403
    assert c.post(f"{P}/push", json={}).status_code == 403
    assert kørt == []
