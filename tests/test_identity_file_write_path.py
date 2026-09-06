"""Skrivning og læsning af MEMORY.md/USER.md skal ramme SAMME fil (5/9-2026).

Målt før: `WORKSPACE_DIR = shared_dir()` sendte enhver `edit_file`/`write_file`
på MEMORY.md og USER.md til `~/.jarvis-v2/shared/`, mens prompten læser
`workspaces/<bruger>/`. Jarvis' egne redigeringer af sin brugerprofil landede i
en fil han aldrig læser; MEMORY.md-kopierne drev fra hinanden, og 24 linjer
fandtes til sidst kun i den ulæste.

Disse tests holder de to sider sammen — også i stub-tilfældet, hvor begge
sider skal blive enige om at shared vinder.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.services.prompt_sections.workspace_files import _resolve_with_shared_fallback
from core.tools.simple_tools import (
    _canonicalize_workspace_target,
    canonical_identity_file_path,
)

RICH = "x" * 4000  # klart over stub-grænsen på 500 bytes


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    ws = tmp_path / "workspaces" / "bjorn"
    shared = tmp_path / "shared"
    ws.mkdir(parents=True)
    shared.mkdir(parents=True)
    monkeypatch.setattr("core.runtime.workspace_paths.workspace_dir_or_owner", lambda: ws)
    return {"ws": ws, "shared": shared}


@pytest.mark.parametrize("name", ["MEMORY.md", "USER.md"])
def test_write_lands_where_the_prompt_reads(home, name):
    (home["ws"] / name).write_text(RICH, encoding="utf-8")
    (home["shared"] / name).write_text(RICH + "extra", encoding="utf-8")
    read_path = _resolve_with_shared_fallback(home["ws"] / name).resolve()
    write_path = canonical_identity_file_path(name)
    assert write_path == read_path
    assert write_path.parent == home["ws"], "arbejdskopien er den kanoniske"


@pytest.mark.parametrize("name", ["MEMORY.md", "USER.md"])
def test_they_agree_even_when_shared_wins(home, name):
    """Stub-tilfældet: en tynd workspace-kopi betyder at BEGGE sider skal
    pege på shared — ellers er skrivningen usynlig for en ny bruger."""
    (home["ws"] / name).write_text("stub", encoding="utf-8")
    (home["shared"] / name).write_text(RICH, encoding="utf-8")
    read_path = _resolve_with_shared_fallback(home["ws"] / name).resolve()
    write_path = canonical_identity_file_path(name)
    assert write_path == read_path == (home["shared"] / name).resolve()


@pytest.mark.parametrize("name", ["MEMORY.md", "USER.md"])
def test_a_wrong_path_is_redirected_to_the_canonical_one(home, name):
    (home["ws"] / name).write_text(RICH, encoding="utf-8")
    wrong = Path("/media/projects/jarvis-v2") / name
    target, redirected_from = _canonicalize_workspace_target(wrong)
    assert target == canonical_identity_file_path(name)
    assert redirected_from == str(wrong)


def test_the_canonical_path_is_not_touched(home):
    (home["ws"] / "MEMORY.md").write_text(RICH, encoding="utf-8")
    canonical = canonical_identity_file_path("MEMORY.md")
    target, redirected_from = _canonicalize_workspace_target(canonical)
    assert target == canonical and redirected_from is None


@pytest.mark.parametrize("name", ["SOUL.md", "IDENTITY.md", "notes.md"])
def test_other_files_are_left_alone(home, name):
    """Kun MEMORY.md og USER.md er per-relation. SOUL/IDENTITY bor i shared og
    maa ikke omdirigeres af denne mekanisme."""
    somewhere = Path("/tmp/et-andet-sted") / name
    target, redirected_from = _canonicalize_workspace_target(somewhere)
    assert target == somewhere and redirected_from is None


def test_the_new_target_still_needs_no_approval(home):
    """~/.jarvis-v2/ er allerede auto-approve-praefiks — flytningen maa ikke
    begynde at udloese godkendelses-kort for hans egen hukommelse."""
    from core.tools.simple_tools import _AUTO_APPROVE_WRITE_PREFIXES
    (home["ws"] / "MEMORY.md").write_text(RICH, encoding="utf-8")
    path = str(canonical_identity_file_path("MEMORY.md"))
    assert any(path.startswith(p) for p in _AUTO_APPROVE_WRITE_PREFIXES)


def test_a_broken_resolver_falls_back_instead_of_raising(home, monkeypatch):
    def _boom():
        raise RuntimeError("ingen bruger-kontekst")
    monkeypatch.setattr("core.runtime.workspace_paths.workspace_dir_or_owner", _boom)
    assert canonical_identity_file_path("MEMORY.md").name == "MEMORY.md"
