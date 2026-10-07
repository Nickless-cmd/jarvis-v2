"""Tests for workspace_trust (trusted-folder gate)."""
from core.services import workspace_trust as wt


def test_untrusted_by_default():
    assert wt.is_trusted("u1", "container", "core") is False


def test_set_and_clear_trust():
    wt.set_trusted("u1", "container", "core", True)
    assert wt.is_trusted("u1", "container", "core") is True
    wt.set_trusted("u1", "container", "core", False)
    assert wt.is_trusted("u1", "container", "core") is False


def test_trust_is_per_user_and_root():
    wt.set_trusted("u1", "container", "apps", True)
    assert wt.is_trusted("u1", "container", "apps") is True
    assert wt.is_trusted("u2", "container", "apps") is False
    assert wt.is_trusted("u1", "container", "core") is False


def test_guard_allows_non_write_tools():
    wt.set_trust_context(kind="container", root="core", trusted=False)
    try:
        assert wt.guard_code_write("read_file") is None
        assert wt.guard_code_write("operator_read_file") is None
    finally:
        wt.clear_trust_context()


def test_guard_blocks_write_in_untrusted_workspace():
    wt.set_trust_context(kind="container", root="core", trusted=False)
    try:
        msg = wt.guard_code_write("write_file")
        assert msg is not None and "ikke betroet" in msg
        assert wt.guard_code_write("operator_bash") is not None
    finally:
        wt.clear_trust_context()


def test_guard_allows_write_in_trusted_workspace():
    wt.set_trust_context(kind="container", root="core", trusted=True)
    try:
        assert wt.guard_code_write("write_file") is None
        assert wt.guard_code_write("bash") is None
    finally:
        wt.clear_trust_context()


def test_guard_noop_without_context():
    wt.clear_trust_context()
    assert wt.guard_code_write("write_file") is None


# ── Arven: en undermappe af en betroet rod (3/10-2026) ────────────────────
#
# Bjoern: «det foerst melder desk trusted folder fejl». En side-opgave starter
# i sin EGEN git-worktree under repoet, og mappen findes ikke naar han trykker
# tillid paa repoet — navnet dannes af opgavens titel. Et noejagtigt match
# kunne derfor aldrig passe.

import os


def test_en_worktree_under_en_betroet_rod_er_betroet(tmp_path):
    """Selve fejlen han saa."""
    repo = tmp_path / "repo"
    (repo / ".worktrees" / "side-fix-tests").mkdir(parents=True)
    wt.set_trusted("arv1", "workstation", str(repo), True)
    assert wt.is_trusted("arv1", "workstation", str(repo / ".worktrees" / "side-fix-tests")) is True


def test_arven_gaelder_ogsaa_en_mappe_der_ikke_findes_endnu(tmp_path):
    """Worktree'en oprettes EFTER tillidsbeslutningen. Kraevede arven at stien
    fandtes, ville den foerste tur stadig fejle."""
    repo = tmp_path / "repo2"
    repo.mkdir()
    wt.set_trusted("arv2", "workstation", str(repo), True)
    assert wt.is_trusted("arv2", "workstation", str(repo / ".worktrees" / "endnu-ikke")) is True


def test_en_SYMLINK_ud_af_roden_foelger_IKKE_med(tmp_path):
    """Graensen for arven. Uden `realpath` ville en symlink inde i en betroet
    mappe vaere en vej ud af sandkassen — stien ser ud som om den ligger under
    roden, men peger andre steder."""
    repo = tmp_path / "repo3"
    repo.mkdir()
    udenfor = tmp_path / "udenfor"
    udenfor.mkdir()
    (udenfor / "hemmeligt.txt").write_text("x")
    link = repo / "smutvej"
    os.symlink(udenfor, link)
    wt.set_trusted("arv3", "workstation", str(repo), True)
    assert wt.is_trusted("arv3", "workstation", str(link)) is False
    assert wt.is_trusted("arv3", "workstation", str(link / "hemmeligt.txt")) is False


def test_en_naboMAPPE_med_samme_praefiks_arver_ikke(tmp_path):
    """`/media/x-ondsindet` maa ikke matche `/media/x`. En bar `startswith`
    ville sige ja."""
    repo = tmp_path / "jarvis-v2"
    repo.mkdir()
    nabo = tmp_path / "jarvis-v2-ondsindet"
    nabo.mkdir()
    wt.set_trusted("arv4", "workstation", str(repo), True)
    assert wt.is_trusted("arv4", "workstation", str(nabo)) is False


def test_arven_krydser_ikke_bruger_eller_scope(tmp_path):
    """Tillid er pr. (bruger, scope, rod) — arven maa ikke lave en genvej."""
    repo = tmp_path / "repo5"
    (repo / "under").mkdir(parents=True)
    wt.set_trusted("arv5", "workstation", str(repo), True)
    assert wt.is_trusted("arv5", "workstation", str(repo / "under")) is True
    assert wt.is_trusted("en-anden", "workstation", str(repo / "under")) is False
    assert wt.is_trusted("arv5", "container", str(repo / "under")) is False


def test_relative_og_absolutte_stier_blandes_ikke(tmp_path, monkeypatch):
    """`realpath` paa en relativ sti afhaenger af processens ARBEJDSMAPPE, og
    det maa en tillids-afgoerelse ikke.

    Testen staar i den mappe hvor forskellen er synlig: uden vagten ville
    "x" oploeses til `tmp_path/x`, og saa ville den absolutte `tmp_path/x/y`
    ligge under den — altsaa ville svaret skifte med hvor processen tilfaeldigvis
    befinder sig. Foerste udgave af denne test stod i repo-roden og bestod
    BEGGE veje; den maalte ingenting.
    """
    (tmp_path / "x" / "y").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    assert wt.er_under(str(tmp_path / "x" / "y"), "x") is False
    assert wt.er_under("x/y", str(tmp_path / "x")) is False
    # Og kontrollen: BEGGE absolutte i samme mappe ER under.
    assert wt.er_under(str(tmp_path / "x" / "y"), str(tmp_path / "x")) is True


def test_punkt_som_rod_aegter_ikke_alt():
    """«.» ville ellers goere enhver relativ sti til sit barn."""
    assert wt.er_under("core/services", ".") is False


def test_en_relativ_undermappe_arver(tmp_path):
    """Container-scope bruger repo-relative navne — arven skal virke der ogsaa."""
    wt.set_trusted("arv6", "container", "apps/api", True)
    assert wt.is_trusted("arv6", "container", "apps/api/jarvis_api") is True
    assert wt.is_trusted("arv6", "container", "apps/ui") is False
