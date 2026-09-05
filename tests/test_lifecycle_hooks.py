"""Livscyklus-hooks server-side — paritet med jarvis-code.

jarvis-code har ni hooks omkring en tur; runtimen havde nul. Dens
`runtime_hooks.py` hedder det samme men dispatcher eventbus-hændelser — noget
helt andet.

Hooks var klient-side fordi typen `command` kører et script LOKALT, og i et
server-loop er «lokalt» containeren. Men `operator_bash` står nu på 1,2 % fejl
over 10.163 kald, så en command-hook kan nå Bjørns maskine. Derfor
`where: "operator"`.
"""
from __future__ import annotations

import json

import pytest

from core.services import lifecycle_hooks as lh


class TestMatcher:
    @pytest.mark.parametrize("m,tool,cmd,vent", [
        ("*", "bash", "", True),
        ("bash", "bash", "", True),
        ("bash", "read_file", "", False),
        ("bash|read_file", "read_file", "", True),
        ("bash|read_file", "write_file", "", False),
        ("bash(git *)", "bash", "git push", True),
        ("bash(git *)", "bash", "ls", False),
        ("bash(git *)", "read_file", "git push", False),
        ("bash(/rm -rf/)", "bash", "sudo rm -rf /", True),
        ("bash(/rm -rf/)", "bash", "ls", False),
    ])
    def test_moenstre(self, m, tool, cmd, vent):
        assert lh.matcher_matches(m, tool, cmd) is vent

    def test_uforstaaeligt_moenster_fejler_AABENT(self):
        """Et mønster man har skrevet forkert skal give støj, ikke tavshed."""
        assert lh.matcher_matches("((((", "bash", "") is True


class TestDommen:
    def test_block_vinder_over_inject(self):
        """Ellers ville rækkefølgen i en config afgøre sikkerheden."""
        d = lh.decide([{"action": "inject", "message": "a"},
                       {"action": "block", "message": "nej"}])
        assert d["action"] == "block" and "nej" in d["message"]

    def test_block_vinder_uanset_raekkefoelge(self):
        d = lh.decide([{"action": "block", "message": "nej"},
                       {"action": "inject", "message": "a"}])
        assert d["action"] == "block"

    def test_flere_injektioner_samles(self):
        """To hooks skal kunne bidrage hver sit uden at overskrive hinanden."""
        d = lh.decide([{"action": "inject", "message": "en"},
                       {"action": "inject", "message": "to"}])
        assert d["action"] == "inject" and d["message"] == "en\nto"

    def test_ingen_hooks_er_allow(self):
        assert lh.decide([])["action"] == "allow"

    def test_vrøvl_i_listen_vaelter_intet(self):
        assert lh.decide([None, "x", {"action": "inject", "message": "ok"}])["action"] == "inject"


class TestConfig:
    def test_ingen_fil_giver_tomt(self, tmp_path, monkeypatch):
        monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
        assert lh.load_hooks() == {}

    def test_ukendte_haendelser_frafiltreres(self, tmp_path, monkeypatch):
        monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "hooks.json").write_text(json.dumps({
            "hooks": {"PreToolUse": [{"type": "command", "command": "true"}],
                      "NoSuchEvent": [{"type": "command"}]}}))
        h = lh.load_hooks()
        assert "PreToolUse" in h and "NoSuchEvent" not in h

    def test_oedelagt_json_vaelter_ikke_en_tur(self, tmp_path, monkeypatch):
        monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "hooks.json").write_text("{ ikke json")
        assert lh.load_hooks() == {}


class TestEksekvering:
    def test_exit_2_blokerer(self, tmp_path, monkeypatch):
        """jarvis-codes konvention, bevaret ordret."""
        monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
        r = lh.run_hook("Stop", {"type": "command", "command": "echo nej; exit 2"}, {})
        assert r["action"] == "block" and "nej" in r["message"]

    def test_stdout_bliver_til_injektion(self, tmp_path, monkeypatch):
        monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
        r = lh.run_hook("Stop", {"type": "command", "command": "echo husk-dette"}, {})
        assert r["action"] == "inject" and r["message"] == "husk-dette"

    def test_tavs_hook_er_allow(self, tmp_path, monkeypatch):
        monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
        r = lh.run_hook("Stop", {"type": "command", "command": "true"}, {})
        assert r["action"] == "allow"

    def test_konteksten_naar_scriptet(self, tmp_path, monkeypatch):
        monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
        r = lh.run_hook("Stop", {"type": "command", "command": "cat"},
                        {"tool": "bash", "hvad": "42"})
        assert '"hvad": "42"' in r["message"]

    def test_en_hook_der_kaster_stopper_ikke_turen(self, tmp_path, monkeypatch):
        monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
        r = lh.run_hook("Stop", {"type": "command", "command": "sleep 99",
                                 "timeout_s": 0.1}, {})
        assert r["action"] == "allow"

    def test_matcher_gaelder_kun_tool_haendelser(self, tmp_path, monkeypatch):
        monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
        h = {"type": "command", "command": "echo ja", "matcher": "read_file"}
        assert lh.run_hook("PreToolUse", h, {"tool": "bash"})["action"] == "allow"
        assert lh.run_hook("Stop", h, {"tool": "bash"})["action"] == "inject"


class TestAerlighedOmHvadDerErKoblet:
    def test_kun_erklaerede_haendelser_regnes_som_koblet(self):
        """Dagens dyreste lære: et værn der ser levende ud og strukturelt ikke
        kan gøre noget, er værre end intet. En PreToolUse der svarer «block» og
        bliver ignoreret ville være præcis dét. WIRED_EVENTS siger sandheden om
        hvad der faktisk fyrer."""
        assert lh.WIRED_EVENTS <= set(lh.HOOK_EVENTS)

    def test_fire_uden_config_er_gratis(self, tmp_path, monkeypatch):
        """Den almindelige vej — ingen hooks konfigureret — må ikke koste noget."""
        monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
        assert lh.fire("PreToolUse", {"tool": "bash"})["action"] == "allow"
