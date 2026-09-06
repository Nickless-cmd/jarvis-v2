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


class TestKoblingen:
    """`UserPromptSubmit` er den første af de ni der kobles. Stedet er valgt
    fordi BEGGE domme kan honoreres: `run.user_message` er stadig foranderlig,
    og intet er bygget endnu."""

    def test_userpromptsubmit_er_erklaeret_koblet(self):
        assert "UserPromptSubmit" in lh.WIRED_EVENTS

    def test_kun_koblede_haendelser_erklaeres(self):
        """Erklæringen må ikke love mere end koden gør."""
        assert lh.WIRED_EVENTS <= set(lh.HOOK_EVENTS)

    def test_de_endnu_ikke_koblede_er_IKKE_erklaeret(self):
        """Vagten der holder erklæringen ærlig. En hændelse der svarer «block»
        og bliver ignoreret ville være værre end ingen hook — den ser ud til at
        virke. Listen krymper efterhånden som hver enkelt kan HONORERES."""
        for e in ("SessionEnd", "PreCompact", "SubagentStop", "Notification"):
            assert e not in lh.WIRED_EVENTS

    def test_koden_kalder_faktisk_fire_for_den(self):
        """Erklæringen alene er ikke nok — dagens dyreste lære er kode der ser
        levende ud uden at være koblet."""
        import pathlib
        kilde = pathlib.Path("core/services/visible_runs.py").read_text()
        assert '"UserPromptSubmit"' in kilde
        assert "WIRED_EVENTS" in kilde


class TestOperatorHooks:
    """Hooks skal kunne nå Bjørns maskine — ellers er pariteten ikke reel.

    FEJL FANGET LIVE: første udgave brugte `asyncio.run()` i den synkrone vej.
    Den kaster inde i et kørende event-loop, og et bredt except slugte det, så
    operator-hooks fejlede tavst hver gang. Bro-kaldet er en coroutine på
    uvicorns hovedloop, og hook'en kaldes FRA det loop — man kan ikke blokere
    på noget der har brug for tråden man holder.
    """

    def test_synkron_vej_afviser_operator_i_stedet_for_at_fejle_tavst(
            self, tmp_path, monkeypatch):
        monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
        r = lh.run_hook("Stop", {"type": "command", "where": "operator",
                                 "command": "echo hej"}, {})
        assert r["action"] == "allow"

    @pytest.mark.asyncio
    async def test_fire_async_koerer_operator_hooken(self, tmp_path, monkeypatch):
        monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "hooks.json").write_text(json.dumps({
            "hooks": {"Stop": [{"type": "command", "where": "operator",
                                "command": "echo fra-maskinen"}]}}))
        fanget = {}

        async def _fake(*, command, user_id, timeout_s=20.0):
            fanget["command"] = command
            return {"stdout": "fra-maskinen", "exit_code": 0}

        import core.tools.operator_tools as ot
        monkeypatch.setattr(ot, "operator_bash_async", _fake)
        d = await lh.fire_async("Stop", {"x": 1}, user_id="u1")
        assert d["action"] == "inject" and d["message"] == "fra-maskinen"
        assert "JARVIS_HOOK_CONTEXT" in fanget["command"]

    @pytest.mark.asyncio
    async def test_container_hooks_virker_stadig_via_fire_async(
            self, tmp_path, monkeypatch):
        monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "hooks.json").write_text(json.dumps({
            "hooks": {"Stop": [{"type": "command", "command": "echo lokalt"}]}}))
        d = await lh.fire_async("Stop", {})
        assert d["action"] == "inject" and d["message"] == "lokalt"

    @pytest.mark.asyncio
    async def test_doed_bro_stopper_ikke_turen(self, tmp_path, monkeypatch):
        monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "hooks.json").write_text(json.dumps({
            "hooks": {"Stop": [{"type": "command", "where": "operator",
                                "command": "echo x"}]}}))
        import core.tools.operator_tools as ot
        monkeypatch.setattr(
            ot, "operator_bash_async",
            lambda **kw: (_ for _ in ()).throw(RuntimeError("bro nede")))
        assert (await lh.fire_async("Stop", {}))["action"] == "allow"


class TestVaerktoejsHooks:
    """`PreToolUse` er den stærkeste af de ni: den kan stoppe en handling FØR
    den sker. Derfor er den også den der stiller det største krav — «block»
    skal kunne honoreres, ellers må hændelsen ikke fyre."""

    def test_begge_er_erklaeret_koblet(self):
        assert {"PreToolUse", "PostToolUse"} <= lh.WIRED_EVENTS

    def test_koblingen_findes_FAKTISK_i_eksekveringen(self):
        """Erklæringen alene er ikke nok."""
        import pathlib
        kilde = pathlib.Path("core/services/visible_tool_exec.py").read_text()
        assert '"PreToolUse"' in kilde and '"PostToolUse"' in kilde
        assert "fire_async" in kilde

    def test_blokeret_kald_udelades_fra_eksekvering(self):
        """Filteret skal fjerne kaldet, ikke bare undlade at annoncere det."""
        import pathlib
        kilde = pathlib.Path("core/services/visible_tool_exec.py").read_text()
        assert "_kald_til_exec" in kilde
        assert "_exec_fn,\n                _kald_til_exec," in kilde

    def test_blokeret_kald_faar_et_svar(self):
        """Uden et resultat ville modellen vente på noget der aldrig kommer."""
        import pathlib
        kilde = pathlib.Path("core/services/visible_tool_exec.py").read_text()
        assert "blokeret af hook" in kilde
        assert '"status": "blocked"' in kilde

    def test_matcher_gaelder_paa_vaerktoejs_haendelser(self, tmp_path, monkeypatch):
        """En hook der kun gælder bash må ikke fyre på read_file."""
        monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
        h = {"type": "command", "command": "exit 2", "matcher": "bash"}
        assert lh.run_hook("PreToolUse", h, {"tool": "read_file"})["action"] == "allow"
        assert lh.run_hook("PreToolUse", h, {"tool": "bash"})["action"] == "block"

    @pytest.mark.asyncio
    async def test_kun_matchende_hooks_koeres_i_fire_async(self, tmp_path, monkeypatch):
        monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "hooks.json").write_text(json.dumps({
            "hooks": {"PreToolUse": [
                {"type": "command", "command": "exit 2", "matcher": "bash"}]}}))
        assert (await lh.fire_async("PreToolUse", {"tool": "read_file"}))["action"] == "allow"
        assert (await lh.fire_async("PreToolUse", {"tool": "bash"}))["action"] == "block"


class TestStopOgSessionStart:
    """`Stop` er den eneste hændelse hvor «block» betyder BLIV VED — turen er
    ved at slutte, så der er intet at forhindre, kun noget at fortsætte."""

    def test_begge_er_erklaeret(self):
        assert {"Stop", "SessionStart"} <= lh.WIRED_EVENTS

    def test_stop_er_koblet_hvor_turen_slutter(self):
        import pathlib
        kilde = pathlib.Path("core/services/visible_runs.py").read_text()
        stop = kilde.index('"Stop" in _lh_stop.WIRED_EVENTS')
        brud = kilde.index("# No more tool calls — this round produced")
        assert stop < brud, "Stop skal fyre FØR turen brydes"

    def test_stop_har_et_loft_paa_én_genoptagelse(self):
        """En hook der altid siger «bliv ved» må ikke holde turen i live for evigt."""
        import pathlib
        kilde = pathlib.Path("core/services/visible_runs.py").read_text()
        assert "_stop_hook_resumed = False" in kilde
        assert "not _stop_hook_resumed" in kilde

    def test_sessionstart_honorerer_KUN_inject(self):
        """At nægte en hel session ved dens første ord er en større magt end en
        hook bør have — og «bliv ved» hører til Stop."""
        import pathlib
        kilde = pathlib.Path("core/services/visible_runs.py").read_text()
        afsnit = kilde[kilde.index("SessionStart-hook"):kilde.index("UserPromptSubmit-hook")]
        assert 'action") == "inject"' in afsnit
        assert 'action") == "block"' not in afsnit

    def test_sessionstart_fyrer_kun_paa_foerste_tur(self):
        import pathlib
        kilde = pathlib.Path("core/services/visible_runs.py").read_text()
        afsnit = kilde[kilde.index("SessionStart-hook"):kilde.index("UserPromptSubmit-hook")]
        assert "_foerste" in afsnit and "recent_chat_session_messages" in afsnit


def test_stop_begraensningen_er_dokumenteret():
    """Stop sidder inde i det agentiske loop, og det loop kører kun når første
    pas gav tool-kald. Et rent tekstsvar når det aldrig. Målt live — og det skal
    stå i koden, ikke kun i en commit-besked, ellers tror næste læser at Stop
    fyrer på hver tur."""
    import inspect
    kilde = inspect.getsource(lh)
    assert "VIGTIG BEGRAENSNING" in kilde
    assert "agentiske loop" in kilde
