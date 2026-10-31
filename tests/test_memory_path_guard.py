"""Tests for MEMORY.md / USER.md path canonicalization in write/edit tools.

Kanonisk mappe = den per-bruger workspace prompten laeser fra (2026-09-05).
Foer da pegede skrivningerne paa shared/, som prompten aldrig laeser."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from core.tools import simple_tools


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    ws = tmp_path / "workspaces" / "default"
    ws.mkdir(parents=True)
    # 2026-09-05: kanoniseringen slaar ikke laengere op i simple_tools.WORKSPACE_DIR
    # (= shared_dir()), men i den PER-BRUGER workspace — samme opslag som prompten
    # bruger til at LAESE. Kontrakten her er uaendret: en forkert sti omdirigeres til
    # den kanoniske fil. Kun hvilken mappe der ER kanonisk har flyttet sig, og det er
    # hele pointen. Se tests/test_identity_file_write_path.py.
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setattr("core.runtime.workspace_paths.workspace_dir_or_owner", lambda: ws)
    monkeypatch.setattr(simple_tools, "WORKSPACE_DIR", ws)
    monkeypatch.setattr(simple_tools, "_AUTO_APPROVE_WRITE_PATHS", {
        str(ws / "MEMORY.md"), str(ws / "USER.md"),
    })
    monkeypatch.setattr(simple_tools, "_AUTO_APPROVE_WRITE_PREFIXES", [str(ws) + "/", "/tmp/"])
    return ws


def test_memory_write_to_wrong_path_redirects(workspace, tmp_path):
    wrong = tmp_path / "repo_root" / "MEMORY.md"
    result = simple_tools._exec_write_file({"path": str(wrong), "content": "- test\n"})
    assert result["status"] == "ok"
    assert result["path"] == str(workspace / "MEMORY.md")
    assert result["redirected_from"] == str(wrong.resolve())
    assert (workspace / "MEMORY.md").read_text() == "- test\n"
    assert not wrong.exists()


def test_user_md_also_redirects(workspace, tmp_path):
    wrong = tmp_path / "other" / "USER.md"
    result = simple_tools._exec_write_file({"path": str(wrong), "content": "hi"})
    assert result["status"] == "ok"
    assert result["path"] == str(workspace / "USER.md")
    assert result["redirected_from"] == str(wrong.resolve())


def test_correct_path_not_redirected(workspace):
    correct = workspace / "MEMORY.md"
    result = simple_tools._exec_write_file({"path": str(correct), "content": "x"})
    assert result["status"] == "ok"
    assert "redirected_from" not in result


def test_unrelated_file_not_redirected(workspace, tmp_path):
    other = tmp_path / "notes.md"
    result = simple_tools._exec_write_file({"path": str(other), "content": "x"})
    # Not auto-approved workspace, goes through approval flow — but path not mangled
    assert result.get("path") == str(other.resolve())
    assert "redirected_from" not in result


def test_edit_memory_wrong_path_redirects(workspace, tmp_path):
    """En forkert MEMORY.md-sti omdirigeres til den kanoniske fil — ved EDIT.

    ## Hvorfor der læses først (målt 31/10-2026)

    Testen blev skrevet 5/9-2026, da `edit` endnu ikke gik gennem
    read-before-write. Den indkodede derfor at en redigering lykkedes på en fil
    ingen havde læst. `edit` fik rbw 29/10, og så fejlede testen — ikke fordi
    omdirigeringen var brudt, men fordi kontrakten den værnode var den gamle
    frihed.

    Målt: omdirigeringen sker FØRST (`_canonicalize_workspace_target`), derefter
    kører guarden på det KANONISKE mål. Rækkefølgen er rigtig — den forkerte
    sti bliver aldrig guardens emne. Det der manglede var en læsning.

    At fjerne rbw for MEMORY.md for at få testen grøn ville være at sælge en
    guard for at købe en grøn vagt. Læsningen er den rigtige pris: den er
    også hvad der gør en kirurgisk redigering mulig i stedet for en blind
    overskrivning.
    """
    (workspace / "MEMORY.md").write_text("foo\n")
    wrong = tmp_path / "wrong" / "MEMORY.md"

    # Læs den KANONISKE fil — det er den guardens nøgle peger på.
    lest = simple_tools._exec_read_file({"path": str(workspace / "MEMORY.md")})
    assert lest["status"] == "ok"

    result = simple_tools._exec_edit_file({
        "path": str(wrong), "old_text": "foo", "new_text": "bar",
    })
    assert result["status"] == "ok"
    assert result["path"] == str(workspace / "MEMORY.md")
    assert result["redirected_from"] == str(wrong.resolve())
    assert (workspace / "MEMORY.md").read_text() == "bar\n"
    assert not wrong.exists(), "den forkerte sti blev oprettet alligevel"


def test_edit_af_ulaest_memory_blokeres_med_en_brugbar_besked(workspace, tmp_path):
    """Uden en læsning skal svaret være en VEJ VISERE, ikke en tavs blokering.

    Det er den fejlform der ellers er usynlig: guarden har ret, men hvis
    beskeden ikke siger hvad man skal gøre, leder den efter det forkerte.
    Beskeden skal pege på den KANONISKE sti — ikke på den forkerte man kom med.
    """
    (workspace / "MEMORY.md").write_text("foo\n")
    wrong = tmp_path / "wrong" / "MEMORY.md"
    result = simple_tools._exec_edit_file({
        "path": str(wrong), "old_text": "foo", "new_text": "bar",
    })
    assert result["status"] == "guard_blocked"
    assert str(workspace / "MEMORY.md") in result["error"], "beskeden peger ikke på den kanoniske fil"
    assert "read_file" in result["error"]
    assert (workspace / "MEMORY.md").read_text() == "foo\n", "filen blev rørt trods blokering"


def test_force_write_redirects(workspace, tmp_path):
    wrong = tmp_path / "wrong" / "MEMORY.md"
    result = simple_tools._force_write_file({"path": str(wrong), "content": "z"})
    assert result["status"] == "ok"
    assert result["path"] == str(workspace / "MEMORY.md")
    assert result["redirected_from"] == str(wrong.resolve())
