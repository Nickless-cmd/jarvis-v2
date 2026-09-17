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
    # 17/9-2026: explore spawner nu med auto_execute=False og koerer selv
    # barnet via execute_agent_task (spawn_med_kvittering). Svaret kommer derfra.
    monkeypatch.setattr(ar, "execute_agent_task", lambda **kw: dict(
        svar or {"agent_id": "a1", "status": "completed",
                 "messages": [{"direction": "agent->jarvis",
                               "content": "fandt det i core/x.py:42"}]}))
    return fanget


class TestExplore:
    def test_ét_felt_er_nok(self, monkeypatch):
        """Hele pointen: man beskriver hvad man leder efter, resten er ikke ens
        problem."""
        _fang(monkeypatch)
        r = _exec_explore({"query": "hvor bygges prompten", "afvent": True})
        assert r["status"] == "ok" and "core/x.py:42" in r["findings"]

    def test_query_kraeves(self):
        assert _exec_explore({})["status"] == "error"

    def test_agenten_faar_LAESE_vaerktoejer(self, monkeypatch):
        """Uden hænder ville den fabrikere — det var rodårsagen i juli."""
        f = _fang(monkeypatch)
        _exec_explore({"query": "x"})
        assert f["tool_policy"] == "read-only-runtime"
        assert f["allowed_tools"], "en agent uden værktøjer opfinder svar"

    def test_desk_workstation_session_bruger_operator_broen(self, monkeypatch):
        """En Desk code-session skal udforske det valgte klient-workspace, ikke
        en mappe med samme navn i runtime-containeren."""
        f = _fang(monkeypatch)
        import core.services.chat_sessions as sessions
        import core.services.explore_claim_check as claim_check
        monkeypatch.setattr(sessions, "get_chat_session", lambda _sid: {
            "workspace_kind": "workstation", "workspace_root": "/home/bjorn/project",
        })
        monkeypatch.setattr(claim_check, "tjek_paastande", lambda *_a, **_kw: {
            "holder": True, "kontrolleret": 0, "fejl": [],
        })
        r = _exec_explore({"query": "find prompt builder", "afvent": True,
                           "_runtime_session_id": "desk-session",
                           "_runtime_user_id": "bjorn"})
        assert r["status"] == "ok" and r["target"] == "workstation"
        assert f["tool_policy"] == "read-only-workstation"
        assert set(f["allowed_tools"]) == {
            "operator_read_file", "operator_glob", "operator_grep", "operator_list_dir",
        }
        # Delmaengde, ikke lighed: Fase 5 lagde HERKOMST i konteksten
        # (`parent_session_id`/`parent_run_id`), saa barnet kan findes under den
        # tur der foedte det. En eksakt sammenligning ville faa hver ny,
        # korrekt tilfoejelse til at se ud som en fejl.
        assert f["context"].items() >= {
            "execution_target": "workstation",
            "workspace_root": "/home/bjorn/project",
            "user_id": "bjorn", "session_id": "desk-session",
        }.items()

    def test_workstation_target_kraever_desk_workspace(self, monkeypatch):
        import core.services.chat_sessions as sessions
        monkeypatch.setattr(sessions, "get_chat_session", lambda _sid: None)
        r = _exec_explore({"query": "x", "target": "workstation",
                           "_runtime_session_id": "desk-session"})
        assert r["status"] == "error"
        assert "workstation-workspace" in r["error"]

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


def test_en_kvittering_roterer_ikke_til_naeste_model(monkeypatch):
    """17/9-2026: tog barnet over 60 s, laeste explore den tomme kvittering som
    «modellen svarede ikke» og startede NAESTE model — op til tre agenter om
    samme spoergsmaal. En kvittering skal gives videre, ikke roteres vaek."""
    import core.tools.simple_tools_native as ex  # explore slaar _explore_spawn op via facaden
    kald = []

    def _spawn(**kw):
        kald.append(kw)
        return {"status": "accepted", "agent_id": "a-sen", "hent_resultat": "get_agent"}

    monkeypatch.setattr(ex, "_explore_spawn", _spawn)
    r = _exec_explore({"query": "noget langsomt"})
    assert len(kald) == 1, "explore startede flere agenter paa en kvittering"
    assert r["status"] == "accepted" and r["agent_id"] == "a-sen"
    assert "get_agent" in r["besked"]


def test_sent_explore_svar_faar_samme_vaern_i_vaekningen(monkeypatch):
    """Et svar der lander efter kvitteringen vurderes af _vurder_svar, og dommen
    står i vækningen — et tomhændet, opdigtet svar giver en ADVARSEL."""
    import core.tools.simple_tools_native as nat
    from core.tools.simple_tools_explore import _vurder_svar, _vurdering_til_wakeup
    fanget = {}

    def _spawn(**kw):
        fanget.update(kw)
        return {"status": "accepted", "agent_id": "a-sen"}

    monkeypatch.setattr(nat, "_explore_spawn", _spawn)
    r = _exec_explore({"query": "noget langsomt"})
    assert r["status"] == "accepted"
    efter = fanget.get("efterbehandling")
    assert callable(efter), "et sent svar ville slippe uden om fabrikations-værnet"
    opdigtet = {"messages": [{"direction": "agent->jarvis", "kind": "result",
                              "content": "Det står i core/findes_ikke.py:42"}],
                "tool_call_count": 0}
    assert efter(opdigtet).startswith("ADVARSEL")
    tomt = _vurdering_til_wakeup(_vurder_svar({"messages": []}, tjek_paastande=None))
    assert "IKKE igennem" in tomt
