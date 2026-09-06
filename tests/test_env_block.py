"""Miljø-blokken: hvor står han, og kan den slukkes?

To ting afgoer om den er en gevinst eller en byrde: at den ligger i den
VOLATILE hale (ellers braekker den prefix-cachen paa hver tur), og at den
kan slaas fra.
"""
import pytest

from core.services import env_block as eb


def test_uden_for_repo_naevnes_kun_mappe_og_os(tmp_path):
    env = eb.collect_env(str(tmp_path))
    assert env["cwd"] == str(tmp_path)
    assert "os" in env
    assert "gren" not in env, "en gren uden repo ville vaere opdigtet"


def test_i_et_repo_kommer_gren_og_renhed(tmp_path):
    import subprocess

    def g(*a):
        subprocess.run(["git", *a], cwd=tmp_path, capture_output=True)
    g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
    (tmp_path / "f.txt").write_text("x")
    g("add", "-A"); g("commit", "-qm", "start")

    env = eb.collect_env(str(tmp_path))
    assert env.get("gren")
    assert env.get("renhed") == "rent"

    (tmp_path / "f.txt").write_text("ændret")
    assert "1 ændrede filer" in eb.collect_env(str(tmp_path))["renhed"]


def test_manglende_git_vaelter_ikke(monkeypatch, tmp_path):
    """En miljoe-blok maa ALDRIG kunne forsinke eller vaelte en tur."""
    def _sprang(*a, **k):
        raise FileNotFoundError("git findes ikke")

    monkeypatch.setattr(eb.subprocess, "run", _sprang)
    env = eb.collect_env(str(tmp_path))
    assert env["cwd"] == str(tmp_path)
    assert "gren" not in env


def test_haengende_git_vaelter_ikke(monkeypatch, tmp_path):
    import subprocess

    def _timeout(*a, **k):
        raise subprocess.TimeoutExpired(cmd="git", timeout=3)

    monkeypatch.setattr(eb.subprocess, "run", _timeout)
    assert eb.collect_env(str(tmp_path))["cwd"] == str(tmp_path)


def test_kan_slukkes(monkeypatch):
    """Bjørn 6/9: «ja, med mulighed for at deaktivere»."""
    monkeypatch.setattr(eb, "is_enabled", lambda: False)
    assert eb.render_env_block() == ""


def test_taendt_som_standard(monkeypatch):
    """Modsat sandboxen: her betyder et usat flag TÆNDT."""
    monkeypatch.setattr("core.services.shared_cache.get", lambda k: None)
    assert eb.is_enabled() is True


def test_blokken_er_kort():
    """En git status med tredive stier ville koste mere end den giver."""
    tekst = eb.render_env_block()
    assert len(tekst) < 400, tekst


def test_blokken_ligger_i_den_VOLATILE_hale():
    """I det stabile praefiks ville git-status bryde cachen paa HVER tur."""
    from core.services.prompt_contract import (
        DYNAMIC_TAIL_SENTINEL,
        build_visible_chat_prompt_assembly,
    )
    a = build_visible_chat_prompt_assembly(
        provider="deepseek", model="deepseek-v4-flash",
        user_message="hej", session_id="_default")
    i_sent = a.text.find(DYNAMIC_TAIL_SENTINEL)
    i_env = a.text.find("HER STÅR DU")
    if i_env < 0:
        pytest.skip("env-blokken slukket i dette miljø")
    assert i_sent > 0
    assert i_env > i_sent, "env FØR markøren ville braekke prefix-cachen"
