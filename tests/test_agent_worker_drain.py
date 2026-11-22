"""En agent i sandbox-worker-mode skal ogsaa kunne modtage beskeder midt i et run (22/11-2026).

MAALT 22/11-2026 i kilden: `run_tool_loop` blev kaldt fra to steder.

* `agent_runtime_base.py` (in-process) sendte `drain_inbox` med.
* `agent_worker_main.py` (sandbox-worker) gjorde IKKE.

Workeren er sandboxet — ingen DB, ingen credentials — saa den kan ikke selv laese
`agent_messages`. Indbakken maa derfor laeses af brokeren paa server-siden og leveres
over RPC. Uden det modtager et run i worker-mode nul beskeder midt i turen, og
`send_agent_to_agent` ville svare «laeses ved modtagerens naeste runde» om en runde
der aldrig laeser.

Testene her beviser baade broker-siden (opslaget) og koblingen i workerens kald.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.services.agent_worker_runner import _Broker

REPO = Path(__file__).resolve().parents[1]


def _broker(*, agent: dict) -> _Broker:
    """En broker uden `__init__`: vi maaler `_drain`, ikke hele I/O-opsaetningen."""
    b = _Broker.__new__(_Broker)
    b.agent = agent
    b._drain_fn = None
    return b


def test_drain_laeser_indbakken_for_en_kontraktbundet_agent(monkeypatch):
    kaldt = {}

    def fake_make_inbox_drain(agent_id, *, since=""):
        kaldt["agent_id"] = agent_id
        return lambda: ["[fra agent-b] kig i config"]

    monkeypatch.setattr(
        "core.services.agent_contract_service.make_inbox_drain", fake_make_inbox_drain
    )
    b = _broker(agent={"agent_id": "agent-a", "owner_user_id": "1246415163603816499"})
    assert b._drain() == ["[fra agent-b] kig i config"]
    assert kaldt["agent_id"] == "agent-a"


def test_drain_bygges_kun_en_gang(monkeypatch):
    """Drain-funktionen holder sin egen cursor; en ny pr. runde ville gentage historik."""
    antal = {"n": 0}

    def fake_make_inbox_drain(agent_id, *, since=""):
        antal["n"] += 1
        return lambda: []

    monkeypatch.setattr(
        "core.services.agent_contract_service.make_inbox_drain", fake_make_inbox_drain
    )
    b = _broker(agent={"agent_id": "agent-a", "owner_user_id": "u1"})
    b._drain()
    b._drain()
    assert antal["n"] == 1


@pytest.mark.parametrize(
    "agent",
    [
        {"agent_id": "", "owner_user_id": "u1"},
        {"agent_id": "agent-a", "owner_user_id": ""},
        {"agent_id": "agent-a", "owner_user_id": "legacy_unscoped"},
    ],
)
def test_en_agent_uden_contrakt_faar_ingen_indbakke(agent):
    """Samme guard som in-process-stien: legacy-agenter har ingen kontrakt at levere til."""
    assert _broker(agent=agent)._drain() == []


def test_brokeren_svarer_paa_drain_oppen(monkeypatch):
    """Workeren kalder `drain` over RPC; brokeren skal kende oppen, ellers doer runnet."""
    b = _broker(agent={"agent_id": "agent-a", "owner_user_id": "u1"})
    monkeypatch.setattr(b, "_drain", lambda: ["[fra jarvis] ret dig mod ho ejre"])
    assert b.handle({"op": "drain"}) == ["[fra jarvis] ret dig mod ho ejre"]


def test_workerens_loekkekald_baerer_drain_inbox():
    """Koblingen selv: kaldet i `main()` skal sende `drain_inbox`.

    Laest som AST og ikke som grep — en kommentar eller et andet kald ville ellers
    kunne tilfredsstille en tekstsoegning uden at parameteren blev sendt.
    """
    tree = ast.parse((REPO / "core/services/agent_worker_main.py").read_text())
    kald = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", "") == "run_tool_loop"
    ]
    assert len(kald) == 1, f"forventede praecis ét run_tool_loop-kald, fandt {len(kald)}"
    navne = {kw.arg for kw in kald[0].keywords}
    assert "drain_inbox" in navne, f"drain_inbox mangler i workerens kald: {sorted(navne)}"
    vaerdi = next(kw.value for kw in kald[0].keywords if kw.arg == "drain_inbox")
    assert isinstance(vaerdi, ast.Attribute) and vaerdi.attr == "drain", ast.dump(vaerdi)


def test_rpcio_har_en_drain_metode():
    """Workeren skal kunne kalde indbakken uden DB — metoden sender `drain` over socket'en."""
    tree = ast.parse((REPO / "core/services/agent_worker_main.py").read_text())
    rpcio = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "RpcIO"
    )
    metoder = {n.name for n in rpcio.body if isinstance(n, ast.FunctionDef)}
    assert "drain" in metoder, f"RpcIO mangler drain: {sorted(metoder)}"
