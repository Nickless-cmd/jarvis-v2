"""`search` må ikke læse store binære filer igennem (12/11-2026).

Målt på CT105: et autonomt run kaldte search med path=~/.jarvis-v2/state, som indeholder
jarvis.db (6,65 GB). `rg` findes IKKE på CT105, så `search` bruger `grep -rEnH` — og grep
læser en binær fil HELE vejen igennem for at afgøre om den matcher («Binary file … matches»).
6,65 GB gennem page cache løftede servicens memory-peak til 6,5 GB. `-I`
(`--binary-files=without-match`) stopper efter første buffer, når grep ser NUL-bytes.
"""
from __future__ import annotations

import shutil
import subprocess

import pytest

from core.tools import simple_tools_web as w

pytestmark = pytest.mark.skipif(shutil.which("grep") is None, reason="kræver grep")


@pytest.fixture
def uden_rg(monkeypatch):
    """CT105 har ikke ripgrep; test den vej der faktisk kører der."""
    real = subprocess.run

    def _run(argv, *a, **k):
        if argv[:1] == ["which"]:
            return subprocess.CompletedProcess(argv, 1, "", "")
        return real(argv, *a, **k)

    monkeypatch.setattr(w.subprocess, "run", _run)


def test_en_binaer_fil_giver_hverken_traef_eller_bliver_laest_igennem(tmp_path, uden_rg):
    # NUL i de første bytes = binær, men mønsteret står LÆNGERE nede i filen. Uden -I
    # finder grep det og melder «Binary file matches»; med -I springes filen over.
    (tmp_path / "db.sqlite").write_bytes(b"SQLite format 3\x00" + b"\x00" * 4096 + b"naalen-i-hoebunken\n")
    (tmp_path / "tekst.log").write_text("her står naalen-i-hoebunken i almindelig tekst\n", encoding="utf-8")

    r = w._exec_search({"pattern": "naalen-i-hoebunken", "path": str(tmp_path)})

    assert r["status"] == "ok"
    assert r["match_count"] == 1
    assert "tekst.log" in r["text"] and "db.sqlite" not in r["text"]
    assert "Binary file" not in r["text"]


def test_almindelig_tekst_findes_stadig(tmp_path, uden_rg):
    (tmp_path / "a.py").write_text("def hej():\n    return 1\n", encoding="utf-8")

    r = w._exec_search({"pattern": "def hej", "path": str(tmp_path)})

    assert r["match_count"] == 1 and "a.py" in r["text"]


def test_grep_faar_flagene_der_springer_binaere_filer_over(tmp_path, monkeypatch):
    """Argumentlisten, så en refaktor ikke stille fjerner dem."""
    set_: list[list[str]] = []

    def _run(argv, *a, **k):
        if argv[:1] == ["which"]:
            return subprocess.CompletedProcess(argv, 1, "", "")
        set_.append(list(argv))
        return subprocess.CompletedProcess(argv, 1, "", "")

    monkeypatch.setattr(w.subprocess, "run", _run)
    w._exec_search({"pattern": "x", "path": str(tmp_path)})

    grep = next(a for a in set_ if a[0] == "grep")
    assert any(a.startswith("-") and not a.startswith("--") and "I" in a for a in grep), "mangler -I"
    for glob in ("*.db", "*.sqlite*", "*-wal", "*-shm"):
        assert f"--exclude={glob}" in grep
