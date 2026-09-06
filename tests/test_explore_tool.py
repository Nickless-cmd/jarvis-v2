"""Explore — bred, læse-kun undersøgelse med beslutningerne truffet på forhånd.

MÅLT: 36 dispatch-kørsler i systemets samlede levetid, 35 fra én
fejlfindings-session. Motoren fejlede ikke — den blev bare aldrig grebet efter.
`spawn_agent_task` kan det hele, men kræver at man først beslutter sig om
system_prompt, role, allowed_tools, tool_policy og budget_tokens.
"""
from __future__ import annotations

import pytest

from core.tools.simple_tools_native import _exec_explore, _exec_spawn_agent_task


def _fang(monkeypatch, svar=None):
    fanget = {}

    def _fake(**kw):
        fanget.update(kw)
        return svar or {"agent_id": "a1", "status": "completed",
                        "messages": [{"direction": "agent->jarvis",
                                      "content": "fandt det i core/x.py:42"}]}

    import core.services.agent_runtime as ar
    monkeypatch.setattr(ar, "spawn_agent_task", _fake)
    return fanget


class TestExplore:
    def test_ét_felt_er_nok(self, monkeypatch):
        """Hele pointen: man beskriver hvad man leder efter, resten er ikke ens
        problem."""
        _fang(monkeypatch)
        r = _exec_explore({"query": "hvor bygges prompten"})
        assert r["status"] == "ok" and "core/x.py:42" in r["findings"]

    def test_query_kraeves(self):
        assert _exec_explore({})["status"] == "error"

    def test_agenten_faar_LAESE_vaerktoejer(self, monkeypatch):
        """Uden hænder ville den fabrikere — det var rodårsagen i juli."""
        f = _fang(monkeypatch)
        _exec_explore({"query": "x"})
        assert f["tool_policy"] == "read-only-runtime"
        assert f["allowed_tools"], "en agent uden værktøjer opfinder svar"

    def test_ingen_budget_klemme(self, monkeypatch):
        """0 = ubegrænset, med max_turns som net. En klemme her ville gentage
        juli-fejlen: agenten brænder budgettet på tool-kald og når aldrig frem
        til et svar."""
        f = _fang(monkeypatch)
        _exec_explore({"query": "x"})
        assert f["budget_tokens"] == 0

    def test_bredden_vejleder_men_klemmer_ikke(self, monkeypatch):
        f = _fang(monkeypatch)
        _exec_explore({"query": "x", "breadth": "thorough"})
        assert "grundigt" in f["goal"]
        assert f["budget_tokens"] == 0, "bredde må ikke blive et loft"

    def test_ukendt_bredde_falder_til_medium(self, monkeypatch):
        f = _fang(monkeypatch)
        r = _exec_explore({"query": "x", "breadth": "vanvittigt"})
        assert r["breadth"] == "vanvittigt" and "flere steder" in f["goal"]

    def test_prompten_forbyder_gaetteri(self, monkeypatch):
        f = _fang(monkeypatch)
        _exec_explore({"query": "x"})
        assert "aldrig" in f["system_prompt"].lower()

    def test_en_fejl_bliver_et_svar_ikke_en_exception(self, monkeypatch):
        import core.services.agent_runtime as ar
        monkeypatch.setattr(ar, "spawn_agent_task",
                            lambda **kw: (_ for _ in ()).throw(RuntimeError("nede")))
        assert _exec_explore({"query": "x"})["status"] == "error"


class TestDispatchRettelser:
    def test_budget_klemmen_er_vaek(self, monkeypatch):
        """Værktøjs-laget klemte til default 2000 / loft 8000 — præcis den
        strangulering juli-fixet fjernede i motoren. Rettelsen var lavet ét lag
        nede og overlevede ikke herop."""
        f = _fang(monkeypatch)
        _exec_spawn_agent_task({"goal": "x"})
        assert f["budget_tokens"] == 0

    def test_et_hoejt_budget_klippes_ikke_til_8000(self, monkeypatch):
        f = _fang(monkeypatch)
        _exec_spawn_agent_task({"goal": "x", "budget_tokens": 50000})
        assert f["budget_tokens"] == 50000

    def test_svaret_klippes_ikke_ved_1200(self, monkeypatch):
        """En god agent leverede 3.751 tegn; 1200 var en tredjedel af svaret."""
        langt = "f" * 5000
        _fang(monkeypatch, {"agent_id": "a1", "status": "completed",
                            "messages": [{"direction": "agent->jarvis",
                                          "content": langt}]})
        r = _exec_spawn_agent_task({"goal": "x"})
        assert len(r["reply"]) == 5000
