"""Tests for `repo_recall` — værktøjet og dets registrering.

Det afgørende er ikke at funktionen kan søge (det dækkes i test_repo_index),
men at værktøjet faktisk er NÅELIGT: i definitions, i dispatcheren og i
kerne-inventaret. Et værktøj der findes men ikke kan ses, er samme fejl som
`explore` og `spawn_agent_task` havde (målt 6/9 og 23/9-2026).
"""
from __future__ import annotations

import pytest

from core.tools import repo_recall_tool as rt


@pytest.fixture()
def fake_repo(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "ARKITEKTUR.md").write_text(
        "# Arkitektur\n\n## Centralen\n\nCentralen er Jarvis' indre liv.\n", encoding="utf-8"
    )
    monkeypatch.setenv("JARVIS_REPO_ROOT", str(root))
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path / "home"))
    from core.services import repo_index as ri
    monkeypatch.setattr(ri, "_embed_ollama", lambda texts: None)
    monkeypatch.setattr(ri, "_schedule_background_build", lambda: None)
    return root


def test_query_er_paakraevet():
    result = rt._exec_repo_recall({})
    assert result["status"] == "error"
    assert "query" in result["error"].lower()


def test_resultatform(fake_repo):
    result = rt._exec_repo_recall({"query": "Centralen", "limit": 3})
    assert result["status"] == "ok"
    assert result["count"] == len(result["results"])
    if result["results"]:
        hit = result["results"][0]
        for key in ("text", "source", "section", "score", "method"):
            assert key in hit


def test_ukendt_sti_giver_tomt_resultat(fake_repo):
    result = rt._exec_repo_recall({"query": "Centralen", "path": "findes/ikke"})
    assert result["status"] == "ok"
    assert result["count"] == 0


def test_limit_klemmes_til_maks():
    """Et absurd limit må ikke kunne tvinge 10.000 resultater ud."""
    result = rt._exec_repo_recall({"query": "x", "limit": 9999})
    # Ingen indeks i denne test — men kaldet må ikke fejle på parameteren.
    assert result["status"] in {"ok", "error"}
    assert len(result.get("results") or []) <= 25


def test_vaerktoej_er_i_definitions():
    from core.tools.simple_tools import get_tool_definitions

    names = {
        ((d.get("function") or {}).get("name") or d.get("name") or "")
        for d in (get_tool_definitions() or [])
    }
    assert "repo_recall" in names


def test_vaerktoej_er_i_dispatcheren():
    from core.tools.simple_tools import _TOOL_HANDLERS

    assert "repo_recall" in _TOOL_HANDLERS
    assert _TOOL_HANDLERS["repo_recall"] is rt._exec_repo_recall


def test_vaerktoej_staar_i_kerne_inventaret():
    """Kerne-kataloget er dét Jarvis læser når han spørger «hvad kan jeg»."""
    from core.services.tool_catalog import _CORE_TOOL_GROUPS

    flat = {name for _grp, names in _CORE_TOOL_GROUPS for name in names}
    assert "repo_recall" in flat
    # ...og `recall` selv, som manglede i gruppen indtil 23/10-2026.
    assert "recall" in flat


def test_vaerktoej_er_tilladt_i_chat_og_code():
    from core.tools.tool_scoping import CHAT_MODE_TOOLS_BASE, CODE_MODE_TOOLS_BASE

    assert "repo_recall" in CHAT_MODE_TOOLS_BASE
    assert "repo_recall" in CODE_MODE_TOOLS_BASE


def test_vaerktoej_er_tilladt_for_autonome_runs():
    from core.tools.autonomous_tool_policy import AUTONOMOUS_TOOLS

    assert "repo_recall" in AUTONOMOUS_TOOLS
