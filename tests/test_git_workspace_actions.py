from __future__ import annotations

import subprocess

import pytest


def _repo(tmp_path):
    """Et rigtigt lille git-repo. Mocks kan ikke se om argumenterne er gyldige."""
    r = tmp_path / "repo"
    r.mkdir()
    kør = lambda *a: subprocess.run(["git", "-C", str(r), *a], capture_output=True, text=True)
    kør("init", "-b", "main")
    kør("config", "user.email", "t@t")
    kør("config", "user.name", "t")
    (r / "f.txt").write_text("hej\n")
    kør("add", ".")
    kør("commit", "-m", "start")
    return r


def test_lister_branches_og_ved_hvor_den_staar(tmp_path) -> None:
    from core.services.git_workspace_actions import checkout_branch, list_branches

    r = _repo(tmp_path)
    checkout_branch(kind="container", root=str(r), navn="ny-ting", opret=True)

    svar = list_branches(kind="container", root=str(r))

    assert svar["ok"] is True
    assert svar["current"] == "ny-ting"
    assert set(svar["local"]) == {"main", "ny-ting"}


def test_skifter_tilbage(tmp_path) -> None:
    from core.services.git_workspace_actions import checkout_branch

    r = _repo(tmp_path)
    checkout_branch(kind="container", root=str(r), navn="gren", opret=True)
    svar = checkout_branch(kind="container", root=str(r), navn="main")

    assert svar["ok"] is True
    assert svar["current"] == "main"


def test_sandheden_er_HEAD_bagefter_ikke_exitkoden(tmp_path) -> None:
    """En branch der ikke findes må ikke rapporteres som et skift."""
    from core.services.git_workspace_actions import checkout_branch

    r = _repo(tmp_path)
    svar = checkout_branch(kind="container", root=str(r), navn="findes-ikke")

    assert svar["ok"] is False


@pytest.mark.parametrize("ondt", ["-rf", "", "   "])
def test_afviser_navne_der_ville_blive_laest_som_flag(tmp_path, ondt) -> None:
    """Et navn der starter med bindestreg ville git læse som et FLAG."""
    from core.services.git_workspace_actions import checkout_branch

    r = _repo(tmp_path)
    svar = checkout_branch(kind="container", root=str(r), navn=ondt)

    assert svar["ok"] is False
    assert "error" in svar


def test_opretter_worktree_og_bekraefter_paa_listen(tmp_path) -> None:
    from core.services.git_workspace_actions import create_worktree

    r = _repo(tmp_path)
    svar = create_worktree(kind="container", root=str(r), navn="sidespor")

    assert svar["ok"] is True
    assert svar["path"] == ".worktrees/sidespor"
    assert (r / ".worktrees" / "sidespor").is_dir()


def test_tom_rod_giver_ikke_et_falsk_ja() -> None:
    from core.services.git_workspace_actions import list_branches

    svar = list_branches(kind="container", root="")

    assert svar["ok"] is False
    assert svar["local"] == []


# ── En fejl skal sige HVAD der gik galt ──────────────────────────────────
#
# Bjørn 18/9-2026: «main dropdown fejler med kunne ikke indlæse branches».
# Den besked var husets egen, ikke serverens, og den dækkede over tre helt
# forskellige ting: broen nede, mappen findes ikke, mappen er ikke et repo.
# Kun den ene af dem kan han selv rette — så beskeden skal skelne.


def test_siger_hvorfor_naar_mappen_ikke_er_et_repo(tmp_path) -> None:
    from core.services.git_workspace_actions import list_branches

    tom = tmp_path / "ikke-et-repo"
    tom.mkdir()

    svar = list_branches(kind="container", root=str(tom))

    assert svar["ok"] is False
    # Git's egen formulering, ikke en vi har fundet på.
    assert "repository" in svar["error"].lower()


def test_tom_rod_siger_at_der_mangler_en_mappe() -> None:
    from core.services.git_workspace_actions import list_branches

    assert "ingen mappe" in list_branches(kind="container", root="")["error"].lower()


def test_broens_egen_begrundelse_naar_helt_op(monkeypatch, tmp_path) -> None:
    """Workstation-vejen svarede `ok:false` UDEN grund — den tavshed var fejlen."""
    import core.services.git_workspace_actions as g
    # `_koer_over_bro` importerer LOKALT fra chat-modulet (kreds-undgåelse), så
    # patchen skal sidde på kilden — ikke på `g`, hvor navnet ikke findes.
    import apps.api.jarvis_api.routes.chat as chat

    monkeypatch.setattr(
        chat, "_operator_exec",
        lambda navn, args: {"status": "error", "error": "bridge_disconnected"},
    )

    svar = g.list_branches(kind="workstation", root=str(tmp_path), uid="u1")

    assert svar["ok"] is False
    assert "bridge_disconnected" in svar["error"]
