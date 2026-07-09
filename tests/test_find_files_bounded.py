"""Regression: find_files' **-glob must be BOUNDED (prune heavy dirs + deadline).

Rådet/streaming-undersøgelse 9. jul: den gamle pathlib.glob-gren havde hverken pruning
eller timeout → et `**`-mønster på repo-roden gik i node_modules/.git i minutter (målt
884s live) → run'et så "hængt/cutoff" ud og blev afbrudt. Denne test låser fixet: glob
prunes tunge mapper, respekterer korrekt **-semantik, og er tids-bundet.
"""
from __future__ import annotations

import os
import time

from core.tools.simple_tools_web import _exec_find_files, _glob_to_regex, _FIND_PRUNE_DIRS


def test_glob_regex_semantics():
    # ** krydser mapper; * gør ikke.
    assert _glob_to_regex("**/*moltbook*").match("a/b/c/xmoltbookY")
    assert _glob_to_regex("**/*.py").match("core/services/x.py")
    assert _glob_to_regex("src/**/*.py").match("src/a/b/c.py")
    assert not _glob_to_regex("*.py").match("a/b.py")        # * må ikke krydse /
    assert _glob_to_regex("*.py").match("b.py")


def test_glob_prunes_heavy_dirs_and_is_fast(tmp_path):
    # Byg et træ med en tung node_modules-mappe + en rigtig fil dybt nede.
    heavy = tmp_path / "node_modules" / "pkg" / "deep"
    heavy.mkdir(parents=True)
    for i in range(50):
        (heavy / f"moltbook_{i}.js").write_text("x")   # matcher mønstret MEN i pruned dir
    real = tmp_path / "src" / "app"
    real.mkdir(parents=True)
    (real / "moltbook_note.md").write_text("y")        # den ægte match

    t = time.monotonic()
    r = _exec_find_files({"pattern": "**/*moltbook*", "path": str(tmp_path)})
    dt = time.monotonic() - t

    assert r["status"] == "ok"
    assert dt < 10, f"skulle være hurtig, tog {dt}s"
    # node_modules-matches er PRUNET væk; kun den ægte fil under src/ tælles.
    assert r["match_count"] == 1, r
    assert "moltbook_note.md" in r["text"]
    assert "node_modules" not in r["text"]


def test_prune_set_covers_find_branch_exclusions():
    # Paritet med find-subprocess-grenens udelukkelser.
    for d in (".git", "node_modules", "__pycache__", ".claude"):
        assert d in _FIND_PRUNE_DIRS


def test_deadline_stops_unbounded_walk(tmp_path, monkeypatch):
    # Med deadline=0 skal walk'en stoppe straks og markere timed_out.
    import core.tools.simple_tools_web as stw
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "x.txt").write_text("z")
    monkeypatch.setattr(stw, "MAX_BASH_SECONDS", 0)
    r = _exec_find_files({"pattern": "**/*.txt", "path": str(tmp_path)})
    assert r["status"] == "ok"
    assert r["timed_out"] is True
