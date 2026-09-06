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
