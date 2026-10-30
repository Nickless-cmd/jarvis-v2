"""commit_attributed — beskeden må ikke fortolkes af en shell.

Målt 30/10-2026: ``bash "git commit -m '<besked>'"`` skar ``running`` ud af
en commit-besked, fordi bash udførte backticks som kommando-substitution FØR
git så beskeden. Reglen om at bruge en quoted heredoc stod i prompten den
tur. Værnet her er ikke en påmindelse — det er en anden handlingsvej:
beskeden er et JSON-argument og skrives til en temp-fil som ``git commit -F``
læser. Denne suite holder på at den vej ikke fortolker noget.
"""

from __future__ import annotations

import subprocess

import pytest

from core.tools.commit_attributed_tool import (
    COMMIT_ATTRIBUTED_TOOL_DEFINITIONS,
    COMMIT_ATTRIBUTED_TOOL_HANDLERS,
    _exec_commit_attributed,
)


def _git(repo, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.fixture()
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.name", "Test")
    _git(r, "config", "user.email", "t@t.dk")
    (r / "a.txt").write_text("x\n", encoding="utf-8")
    return r


def test_backticks_og_variabler_overlever_i_beskeden(repo):
    """Det konkrete tab: ordet inde i backticks forsvandt ud af beskeden."""
    besked = 'fix(turn): `running` er ikke terminalt — $HOME og "citation"'
    result = _exec_commit_attributed({"message": besked, "repo": str(repo)})

    assert result["status"] == "ok", result
    gemt = _git(repo, "log", "-1", "--format=%B").stdout
    assert "`running`" in gemt
    assert "$HOME" in gemt
    assert '"citation"' in gemt


def test_attribution_er_jarvis_ikke_bjorn(repo):
    """Actor-feltet afgør hvem commit'en tilskrives — det må ikke arve Bjørns."""
    result = _exec_commit_attributed({"message": "chore: test", "repo": str(repo)})
    assert result["status"] == "ok", result

    gemt = _git(repo, "log", "-1", "--format=%B").stdout
    assert "Actor: jarvis" in gemt
    assert "Actor-Type: agent" in gemt
    assert "Approved-By: bjorn" in gemt
    assert "Actor: bjorn" not in gemt


def test_tom_besked_afvises(repo):
    result = _exec_commit_attributed({"message": "   ", "repo": str(repo)})
    assert result["status"] == "error"
    assert "message" in result["error"]


def test_ingen_aendringer_giver_nochange(repo):
    (repo / "a.txt").write_text("x\n", encoding="utf-8")
    _exec_commit_attributed({"message": "chore: første", "repo": str(repo)})

    result = _exec_commit_attributed({"message": "chore: anden", "repo": str(repo)})
    assert result["status"] == "nochange", result


def test_kun_valgte_filer_committes(repo):
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    (repo / "b.txt").write_text("b\n", encoding="utf-8")

    result = _exec_commit_attributed(
        {"message": "feat: kun a", "files": ["a.txt"], "repo": str(repo)}
    )
    assert result["status"] == "ok", result

    filer = _git(repo, "show", "--name-only", "--format=", "HEAD").stdout.split()
    assert "a.txt" in filer
    assert "b.txt" not in filer


def test_vaerktoejet_er_registreret():
    """Et værktøj der ikke kan kaldes er teater — navnet skal stå begge steder."""
    navne = [
        d.get("function", {}).get("name")
        for d in COMMIT_ATTRIBUTED_TOOL_DEFINITIONS
    ]
    assert navne == ["commit_attributed"]
    assert "commit_attributed" in COMMIT_ATTRIBUTED_TOOL_HANDLERS

    from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS

    katalog = [d.get("function", {}).get("name") for d in TOOL_DEFINITIONS]
    assert katalog.count("commit_attributed") == 1
    assert "commit_attributed" in _TOOL_HANDLERS
