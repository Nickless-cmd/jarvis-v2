"""bwrap-indespærring: SLUKKET som standard, og fail-open når den ikke kan.

Bjørn bad eksplicit om at den er off by default, så det er den vigtigste
test her — ikke at argv'en ser rigtig ud.
"""
import pytest

from core.services import bash_sandbox as bs


def test_slukket_som_standard(monkeypatch):
    monkeypatch.setattr(bs, "shared_cache", None, raising=False)
    monkeypatch.setattr("core.services.shared_cache.get", lambda k: None)
    assert bs.is_enabled() is False
    assert bs.maybe_wrap("ls", "/tmp") is None


def test_usat_flag_taender_ikke(monkeypatch):
    """central_switches.is_enabled defaulter til ON — den vej er forkert her."""
    monkeypatch.setattr("core.services.shared_cache.get", lambda k: {})
    assert bs.is_enabled() is False


def test_kun_eksplicit_true_taender(monkeypatch):
    monkeypatch.setattr("core.services.shared_cache.get",
                        lambda k: {"enabled": "ja"})
    assert bs.is_enabled() is False, "kun et rigtigt True tæller"
    monkeypatch.setattr("core.services.shared_cache.get",
                        lambda k: {"enabled": True})
    assert bs.is_enabled() is True


def test_cache_fejl_taender_ikke(monkeypatch):
    def _sprang(k):
        raise RuntimeError("cache nede")

    monkeypatch.setattr("core.services.shared_cache.get", _sprang)
    assert bs.is_enabled() is False


def test_taendt_men_uden_bwrap_koerer_uindespaerret(monkeypatch):
    """Fail-OPEN: en manglende mekanisme må ikke gøre bash ubrugelig."""
    monkeypatch.setattr(bs, "is_enabled", lambda: True)
    monkeypatch.setattr(bs, "is_available", lambda: False)
    assert bs.maybe_wrap("ls", "/tmp") is None


def test_taendt_og_tilgaengelig_giver_en_argv(monkeypatch):
    monkeypatch.setattr(bs, "is_enabled", lambda: True)
    monkeypatch.setattr(bs, "is_available", lambda: True)
    argv = bs.maybe_wrap("ls", "/arbejde")
    assert argv[0] == "bwrap"
    assert argv[-3:] == ["sh", "-c", "ls"]
    assert "--bind" in argv and "/arbejde" in argv


def test_cwd_bindes_EFTER_tmpfs():
    """Ellers skygger tmpfs en cwd der selv ligger under /tmp."""
    argv = bs.wrap_bwrap("ls", "/tmp/arbejde")
    assert argv.index("--tmpfs") < argv.index("--bind")


def test_uden_egress_faar_processen_sit_eget_net():
    med = bs.wrap_bwrap("ls", "/a", allow_egress=True)
    uden = bs.wrap_bwrap("ls", "/a", allow_egress=False)
    assert "--share-net" in med
    assert "--share-net" not in uden
    assert "--unshare-all" in uden


def test_argv_ikke_shell_streng():
    """En streng ville aabne et nyt citerings-hul."""
    argv = bs.wrap_bwrap("echo 'a b'; rm -rf /", "/a")
    assert isinstance(argv, list)
    assert argv[-1] == "echo 'a b'; rm -rf /"


def test_status_fortaeller_hvorfor_den_ikke_er_aktiv(monkeypatch):
    monkeypatch.setattr(bs, "is_enabled", lambda: True)
    monkeypatch.setattr(bs, "is_available", lambda: False)
    s = bs.status()
    assert s["aktiv"] is False
    assert "findes ikke" in s["note"]


# ── 10/9-2026: sandkassen var korrekt og ubrugelig ───────────────────────
#
# Maalt ved at TAENDE den paa CT105 og spoerge hvad en indespaerret kommando
# kunne: `ls /opt/conda` → «No such file or directory», og `~/.jarvis-v2`
# fandtes ikke. Indespaerringen rapporterede pligtskyldigt `honored=True` —
# den var bare ude af stand til at lave arbejde. Et vaern ingen taender,
# beskytter intet.

import shutil

import pytest

_HAR_BWRAP = shutil.which("bwrap") is not None


def test_opt_er_med_i_de_readonly_roedder():
    """HVERT script i huset koerer gennem `/opt/conda/envs/ai/bin/python`."""
    from core.services.bash_sandbox import _RO_ROEDDER
    assert "/opt" in _RO_ROEDDER


def test_runtime_hjemmet_bindes_SKRIVBART():
    """Uden det kunne en indespaerret kommando hverken se databasen,
    tilstanden eller hukommelsen."""
    from core.runtime.config import JARVIS_HOME
    from core.services.bash_sandbox import wrap_bwrap
    argv = wrap_bwrap("echo x", "/media/projects/jarvis-v2")
    i = argv.index(str(JARVIS_HOME))
    assert argv[i - 1] == "--bind", "hjemmet blev bundet read-only"


def _antal_bind(argv: list[str], sti: str) -> int:
    """Tael `--bind <sti> <sti>`-par. `--chdir <sti>` naevner OGSAA stien, saa
    en raa .count() taeller forkert — det kostede en falsk roed test."""
    return sum(1 for i, a in enumerate(argv)
               if a == "--bind" and argv[i + 1] == sti)


def test_ingen_dobbelt_binding_naar_cwd_ER_hjemmet():
    from core.runtime.config import JARVIS_HOME
    from core.services.bash_sandbox import wrap_bwrap
    argv = wrap_bwrap("echo x", str(JARVIS_HOME))
    assert _antal_bind(argv, str(JARVIS_HOME)) == 1


@pytest.mark.skipif(not _HAR_BWRAP, reason="bwrap findes ikke her")
def test_en_indespaerret_kommando_kan_faktisk_arbejde(tmp_path):
    """Selve fejlen fra i dag: den kunne rapportere, men ikke arbejde."""
    import subprocess
    from core.services.bash_sandbox import wrap_bwrap
    argv = wrap_bwrap('/opt/conda/envs/ai/bin/python -c "print(2+2)"',
                      "/media/projects/jarvis-v2")
    r = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and r.stdout.strip() == "4", r.stderr[:200]


@pytest.mark.skipif(not _HAR_BWRAP, reason="bwrap findes ikke her")
def test_en_skrivning_UDENFOR_kasseres(tmp_path):
    # NB: maalet maa IKKE ligge under /tmp — det er tmpfs inde i sandkassen,
    # saa mappen findes slet ikke og skrivningen fejler af en anden grund end
    # den vi vil vise. (Falsk roed test, 10/9-2026.)
    """Og den beskytter stadig. Bemaerk at kommandoen faar exit 0 og kan laese
    sin egen skrivning tilbage — men den RIGTIGE disk er uroert. «Det lykkedes»
    inde i sandkassen betyder ikke at der skete noget udenfor.
    """
    import subprocess
    from core.services.bash_sandbox import wrap_bwrap
    import pathlib
    maal = pathlib.Path.home() / "sandkasse-testmaal.txt"
    maal.write_text("ORIGINAL")
    argv = wrap_bwrap(f"echo OEDELAGT > {maal}; cat {maal}",
                      "/media/projects/jarvis-v2")
    r = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    assert r.stdout.strip() == "OEDELAGT", "saa ikke sin egen skrivning"
    try:
        assert maal.read_text() == "ORIGINAL", "skrivningen slap UD af sandkassen"
    finally:
        maal.unlink(missing_ok=True)


def test_tolkens_egen_rod_bindes_oploest():
    """`/opt` alene raakker ikke. Paa CT105 er `/opt/conda/envs/ai/bin/python`
    et symlink ind i `/home/bs/miniconda3`; en read-only binding af `/opt` tager
    symlinket med men ikke dets MAAL, og kommandoen doer med exit 127.

    Lokalt er `/opt/conda` et rigtigt trae — saa det bestod hos mig og fejlede
    paa maskinen. Derfor bindes den OPLOESTE sti.
    """
    import pathlib
    import sys as _sys
    from core.services.bash_sandbox import _python_roedder
    roedder = _python_roedder()
    assert roedder, "ingen tolke-rod bundet"
    assert str(pathlib.Path(_sys.prefix).resolve()) in roedder
    assert all(pathlib.Path(r).is_absolute() for r in roedder)


def test_conda_BASEN_kommer_med():
    """Env'et laener sig paa delte biblioteker i base-installationen."""
    import pathlib
    from core.services.bash_sandbox import _conda_rod
    assert _conda_rod(pathlib.Path("/h/miniconda3/envs/ai")) == pathlib.Path("/h/miniconda3")
    assert _conda_rod(pathlib.Path("/usr/local")) is None


def test_tolke_roedderne_er_READ_ONLY():
    """De skal kunne LAESES, ikke skrives. En indespaerret kommando maa ikke
    kunne aendre selve tolken."""
    from core.services.bash_sandbox import _python_roedder, wrap_bwrap
    argv = wrap_bwrap("echo x", "/media/projects/jarvis-v2")
    for rod in _python_roedder():
        i = argv.index(rod)
        assert argv[i - 1] == "--ro-bind-try", f"{rod} blev bundet skrivbart"
