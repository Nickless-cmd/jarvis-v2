"""Git-checkpoint pr. redigeringsrunde.

Det vigtigste er hvad det IKKE gør: et checkpoint må aldrig flytte Bjørns
gren eller dukke op i hans historik. Derfor testes HEAD, grenen og
stash-listen efter en checkpoint — ikke bare at der kom en sha ud.
"""
import subprocess

import pytest

from core.services import edit_checkpoint as ec


@pytest.fixture(autouse=True)
def _ren_stak(monkeypatch):
    st: dict = {}
    monkeypatch.setattr(ec, "_load", lambda: dict(st))
    monkeypatch.setattr(ec, "_save", lambda d: (st.clear(), st.update(d)))
    yield st


@pytest.fixture
def repo(tmp_path):
    def _g(*a):
        return subprocess.run(["git", *a], cwd=tmp_path, capture_output=True, text=True)
    _g("init", "-q")
    _g("config", "user.email", "t@t")
    _g("config", "user.name", "t")
    (tmp_path / "f.txt").write_text("original\n")
    _g("add", "-A")
    _g("commit", "-qm", "start")
    return tmp_path


def test_uden_for_git_er_det_et_no_op(tmp_path):
    assert ec.checkpoint(str(tmp_path), "s1") is None


def test_rent_traee_giver_intet_checkpoint(repo):
    assert ec.checkpoint(str(repo), "s1") is None, "der er intet at fotografere"


def test_checkpoint_flytter_ikke_HEAD_og_ses_ikke_i_historikken(repo):
    def _g(*a):
        return subprocess.run(["git", *a], cwd=repo, capture_output=True,
                              text=True).stdout.strip()

    head_foer = _g("rev-parse", "HEAD")
    gren_foer = _g("rev-parse", "--abbrev-ref", "HEAD")
    (repo / "f.txt").write_text("ændret\n")

    sha = ec.checkpoint(str(repo), "s1", note="edit_file")
    assert sha

    assert _g("rev-parse", "HEAD") == head_foer, "HEAD må ALDRIG flytte sig"
    assert _g("rev-parse", "--abbrev-ref", "HEAD") == gren_foer
    assert _g("stash", "list") == "", "må ikke dukke op i stash-listen"
    # ...og arbejdstraeet er uroert af selve fotograferingen
    assert (repo / "f.txt").read_text() == "ændret\n"


def test_rollback_gendanner_filerne(repo):
    (repo / "f.txt").write_text("runde 1\n")
    ec.checkpoint(str(repo), "s1")
    (repo / "f.txt").write_text("en daarlig runde\n")

    r = ec.rollback_last("s1")
    assert r["status"] == "ok"
    assert (repo / "f.txt").read_text() == "runde 1\n"


def test_rollback_uden_checkpoints():
    assert ec.rollback_last("tom")["status"] == "error"


def test_stakken_er_pr_session(repo):
    (repo / "f.txt").write_text("a\n")
    ec.checkpoint(str(repo), "s1")
    assert ec.list_checkpoints("s2") == []
    assert len(ec.list_checkpoints("s1")) == 1


def test_bortsamlet_objekt_lover_ikke_en_tilbagerulning(repo, monkeypatch):
    """Et løst stash-objekt kan forsvinde med `git gc`."""
    (repo / "f.txt").write_text("a\n")
    ec.checkpoint(str(repo), "s1")
    monkeypatch.setattr(ec, "_objekt_findes", lambda cwd, sha: False)
    r = ec.rollback_last("s1")
    assert r["status"] == "error"
    assert "bortsamlet" in r["error"]


def test_stakken_har_et_loft(repo):
    for i in range(ec._MAX_PR_SESSION + 5):
        (repo / "f.txt").write_text(f"runde {i}\n")
        ec.checkpoint(str(repo), "s1")
    assert len(ec.list_checkpoints("s1")) == ec._MAX_PR_SESSION
