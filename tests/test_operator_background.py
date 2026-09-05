"""Baggrunds-shells på operatørens maskine.

`run_in_background`/`bash_output`/`kill_shell` fandtes hverken i runtimen eller
i operator-sættet — tre af de fire huller i «det samme på min maskine».

jarvis-code holder et in-process Popen-register. Det kan runtimen ikke:
processen lever på en anden maskine, og et modul-globalt register krydser
alligevel ikke api/runtime-grænsen. Derfor ligger hele tilstanden som filer
på operatørens maskine, med shell_id som nøgle.
"""
from __future__ import annotations

import pytest

from core.tools import operator_background as ob


class TestIdVaern:
    def test_egne_id_er_gyldige(self):
        assert ob._valid(ob._new_id())

    @pytest.mark.parametrize("ondt", [
        "../../etc/passwd", "bg_zzz", "", "bg_" + "f" * 40, "a; rm -rf /",
    ])
    def test_fremmede_id_afvises(self, ondt):
        """shell_id går ind i kommandoer vi bygger — et løst id ville kunne
        smugle sti-fragmenter med."""
        assert not ob._valid(ondt)


def _bash(monkeypatch, svar):
    """Fang kommandoen der sendes til operator_bash."""
    fanget = {}

    async def _fake(*, command, user_id, timeout_s=20.0):
        fanget["command"] = command
        fanget["user_id"] = user_id
        return svar

    import core.tools.operator_tools as ot
    monkeypatch.setattr(ot, "operator_bash_async", _fake)
    return fanget


class TestStart:
    @pytest.mark.asyncio
    async def test_processen_loesrives(self, monkeypatch):
        """setsid + omdirigering: den skal overleve både bro-kaldet og en
        genstart af runtimen. Runs bundet til en socket er præcis dét der har
        kostet afbrudte kørsler."""
        f = _bash(monkeypatch, {"stdout": "4242\n"})
        r = await ob.start_async(command="sleep 300", user_id="u1")
        assert "setsid" in f["command"]
        assert r["pid"] == "4242" and ob._valid(r["shell_id"])

    @pytest.mark.asyncio
    async def test_kommandoen_citeres(self, monkeypatch):
        """Ellers ville et semikolon i kommandoen brække boot-linjen."""
        f = _bash(monkeypatch, {"stdout": "1\n"})
        await ob.start_async(command="echo a; rm -rf /tmp/x", user_id="u1")
        assert "'echo a; rm -rf /tmp/x'" in f["command"]

    @pytest.mark.asyncio
    async def test_cwd_citeres_ogsaa(self, monkeypatch):
        f = _bash(monkeypatch, {"stdout": "1\n"})
        await ob.start_async(command="ls", cwd="/tmp/med mellemrum", user_id="u1")
        assert "'/tmp/med mellemrum'" in f["command"]


class TestLaesning:
    @pytest.mark.asyncio
    async def test_inkrementel_med_offset(self, monkeypatch):
        """Uden offset ville turen se det samme output igen og igen."""
        f = _bash(monkeypatch, {"stdout": "__JBG__ 120 1\nnyt output\n"})
        r = await ob.read_async(shell_id="bg_" + "a" * 12, user_id="u1", since=40)
        assert "tail -c +41" in f["command"]
        assert r["output"] == "nyt output\n"
        assert r["offset"] == 120 and r["running"] is True

    @pytest.mark.asyncio
    async def test_afsluttet_shell_meldes_stoppet(self, monkeypatch):
        _bash(monkeypatch, {"stdout": "__JBG__ 9 0\nfaerdig\n"})
        r = await ob.read_async(shell_id="bg_" + "b" * 12, user_id="u1")
        assert r["running"] is False and r["output"] == "faerdig\n"

    @pytest.mark.asyncio
    async def test_ukendt_id_er_en_fejl_ikke_et_kald(self, monkeypatch):
        f = _bash(monkeypatch, {"stdout": ""})
        r = await ob.read_async(shell_id="../x", user_id="u1")
        assert "error" in r and "command" not in f

    @pytest.mark.asyncio
    async def test_stoej_uden_markoer_giver_tomt_ikke_vroevl(self, monkeypatch):
        """Svarer broen noget uventet, må vi ikke aflevere det som output."""
        _bash(monkeypatch, {"stdout": "en fejl fra broen"})
        r = await ob.read_async(shell_id="bg_" + "c" * 12, user_id="u1", since=7)
        assert r["output"] == "" and r["offset"] == 7


class TestKill:
    @pytest.mark.asyncio
    async def test_draeber_paa_pid(self, monkeypatch):
        f = _bash(monkeypatch, {"stdout": "draebt\n"})
        r = await ob.kill_async(shell_id="bg_" + "d" * 12, user_id="u1")
        assert r["killed"] is True and "kill" in f["command"]

    @pytest.mark.asyncio
    async def test_ukendt_id_roerer_intet(self, monkeypatch):
        f = _bash(monkeypatch, {"stdout": ""})
        r = await ob.kill_async(shell_id="nope", user_id="u1")
        assert r["killed"] is False and "command" not in f
