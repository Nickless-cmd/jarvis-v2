"""Turen må ikke slutte mens en baggrunds-shell stadig producerer.

`operator_run_in_background` er ubrugelig uden det her: man starter en kommando,
turen slutter med det samme, og resultatet ses aldrig — præcis den sygdom resten
af dagen har handlet om.
"""
from __future__ import annotations

import pytest

from core.services import background_resume as br


@pytest.fixture(autouse=True)
def _ren_state(monkeypatch):
    """Runtime-state i hukommelsen, så tests ikke rører den rigtige DB."""
    lager: dict = {}
    import core.runtime.db_core as db
    monkeypatch.setattr(db, "get_runtime_state_value",
                        lambda k, d=None: lager.get(k, d))
    monkeypatch.setattr(db, "set_runtime_state_value",
                        lambda k, v, **kw: lager.__setitem__(k, v))
    return lager


class TestSporing:
    def test_shell_knyttes_til_sessionen(self):
        br.note_started("s1", "bg_a")
        assert [s["shell_id"] for s in br.tracked("s1")] == ["bg_a"]

    def test_samme_shell_registreres_ikke_to_gange(self):
        br.note_started("s1", "bg_a")
        br.note_started("s1", "bg_a")
        assert len(br.tracked("s1")) == 1

    def test_sessioner_blandes_ikke(self):
        br.note_started("s1", "bg_a")
        br.note_started("s2", "bg_b")
        assert [s["shell_id"] for s in br.tracked("s2")] == ["bg_b"]

    def test_loft_pr_session(self):
        """En tur må ikke drukne i baggrunds-støj."""
        for i in range(20):
            br.note_started("s1", f"bg_{i:012d}")
        assert len(br.tracked("s1")) == br._MAX_PR_SESSION

    def test_tom_session_eller_shell_ignoreres(self):
        br.note_started("", "bg_a")
        br.note_started("s1", "")
        assert br.tracked("") == [] and br.tracked("s1") == []

    def test_oprydning(self):
        br.note_started("s1", "bg_a")
        br.forget_session("s1")
        assert br.tracked("s1") == []


def _laesning(monkeypatch, svar):
    async def _fake(*, shell_id, user_id, since=0, timeout_s=20.0):
        return dict(svar.get(shell_id, {}), shell_id=shell_id)
    import core.tools.operator_background as ob
    monkeypatch.setattr(ob, "read_async", _fake)


class TestGenoptagelse:
    @pytest.mark.asyncio
    async def test_nyt_output_giver_en_note(self, monkeypatch):
        br.note_started("s1", "bg_a")
        _laesning(monkeypatch, {"bg_a": {"output": "linje-1\n", "offset": 8,
                                         "running": True}})
        note = await br.poll_async("s1", "u1")
        assert "bg_a" in note and "linje-1" in note

    @pytest.mark.asyncio
    async def test_en_shell_der_bare_koerer_giver_INTET(self, monkeypatch):
        """Kernen. Uden det ville turen aldrig kunne slutte — den ville
        genoptage i det uendelige på «den kører stadig»."""
        br.note_started("s1", "bg_a")
        _laesning(monkeypatch, {"bg_a": {"output": "", "offset": 0, "running": True}})
        assert await br.poll_async("s1", "u1") == ""

    @pytest.mark.asyncio
    async def test_afslutning_er_ogsaa_en_aendring(self, monkeypatch):
        br.note_started("s1", "bg_a")
        _laesning(monkeypatch, {"bg_a": {"output": "", "offset": 0, "running": False}})
        note = await br.poll_async("s1", "u1")
        assert "FAERDIG" in note

    @pytest.mark.asyncio
    async def test_samme_output_rapporteres_kun_EN_gang(self, monkeypatch):
        """Offset skal skride frem, ellers gentages det samme hver runde."""
        br.note_started("s1", "bg_a")
        _laesning(monkeypatch, {"bg_a": {"output": "hej\n", "offset": 4,
                                         "running": True}})
        assert await br.poll_async("s1", "u1") != ""
        _laesning(monkeypatch, {"bg_a": {"output": "", "offset": 4,
                                         "running": True}})
        assert await br.poll_async("s1", "u1") == ""

    @pytest.mark.asyncio
    async def test_afsluttet_shell_spoerges_ikke_igen(self, monkeypatch):
        br.note_started("s1", "bg_a")
        _laesning(monkeypatch, {"bg_a": {"output": "", "offset": 0, "running": False}})
        await br.poll_async("s1", "u1")
        kald = []

        async def _taeller(*, shell_id, user_id, since=0, timeout_s=20.0):
            kald.append(shell_id)
            return {"output": "", "offset": 0, "running": False}

        import core.tools.operator_background as ob
        monkeypatch.setattr(ob, "read_async", _taeller)
        await br.poll_async("s1", "u1")
        assert kald == []

    @pytest.mark.asyncio
    async def test_ingen_shells_er_gratis(self, monkeypatch):
        assert await br.poll_async("tom-session", "u1") == ""

    @pytest.mark.asyncio
    async def test_en_doed_bro_afslutter_turen_normalt(self, monkeypatch):
        br.note_started("s1", "bg_a")
        import core.tools.operator_background as ob
        monkeypatch.setattr(
            ob, "read_async",
            lambda **kw: (_ for _ in ()).throw(RuntimeError("bro nede")))
        assert await br.poll_async("s1", "u1") == ""


class TestNoten:
    def test_siger_hvad_der_SKETE_ikke_hvad_han_skal(self):
        """En instruks ville gøre den til en tvang; han skal selv vurdere om
        outputtet ændrer noget."""
        n = br.build_note([{"shell_id": "bg_a", "output": "ok", "finished": False}])
        assert "[BAGGRUND]" in n
        assert "skal" not in n.lower()

    def test_langt_output_afkortes(self):
        n = br.build_note([{"shell_id": "bg_a", "output": "x" * 5000,
                            "finished": False}])
        assert "afkortet" in n and len(n) < 2400
