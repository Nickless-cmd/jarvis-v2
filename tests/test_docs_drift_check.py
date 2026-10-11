# tests/test_docs_drift_check.py
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "docs_drift_check", Path(__file__).resolve().parents[1] / "scripts" / "docs_drift_check.py")
d = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d)


def test_broken_links_flags_missing_and_passes_valid(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "real.md").write_text("hello")
    good = docs / "a.md"
    good.write_text("[ok](real.md) and [ext](https://x.y) and [anchor](#top)")
    bad = docs / "b.md"
    bad.write_text("[gone](does_not_exist.md)")
    out = d.broken_links(docs)
    targets = {(o["doc"].split("/")[-1], o["target"]) for o in out}
    assert ("b.md", "does_not_exist.md") in targets
    assert not any(o["doc"].endswith("a.md") for o in out)


def test_norm_collapses_dates():
    assert d._norm("Generated 2026-07-08 x") == d._norm("Generated 2020-01-01 x")
    assert d._norm("Generated 2026-07-08 x") != d._norm("Generated 2026-07-08 y")


def test_real_repo_has_no_hard_drift():
    # Guards the committed tree: generated docs match their generators and no links dangle.
    rep = d.run_check()
    assert rep["counts"]["hard"] == 0, rep["hard"][:20]


# ── Vagten skal kunne ses SIGE NEJ (20/9-2026) ──────────────────────────────
def test_gate_afviser_naar_der_er_haard_drift(monkeypatch, capsys):
    """Testfilen dækkede opdagelsen, men aldrig afvisningen.

    En vagt hvis nej ingen har set, er en vagt man ikke ved virker. Den her
    blokerede fire af mine commits i dag — men det vidste vi kun fordi jeg
    tilfældigvis ramte den.
    """
    import sys

    import scripts.docs_drift_check as d
    monkeypatch.setattr(d, "staged_paths", lambda: ["core/x.py"])
    monkeypatch.setattr(d, "hard_drift", lambda staged: [
        {"generator": "api_docs_gen", "kind": "stale", "path": "docs/reference/api/x.md"}])
    monkeypatch.setattr(sys, "argv", ["docs_drift_check.py", "--check"])
    assert d.main() == 1
    ud = capsys.readouterr().out
    assert "1 HARD drift" in ud
    assert "api_docs_gen" in ud          # den skal sige HVILKEN generator


def test_gate_gaar_igennem_uden_drift(monkeypatch, capsys):
    import sys

    import scripts.docs_drift_check as d
    monkeypatch.setattr(d, "staged_paths", lambda: [])
    monkeypatch.setattr(d, "hard_drift", lambda staged: [])
    monkeypatch.setattr(sys, "argv", ["docs_drift_check.py", "--check"])
    assert d.main() == 0
    assert "clean" in capsys.readouterr().out


# ── Historiske træer holdes ude af prose-checken, men IKKE af link-checken (11/10-2026) ──
def test_prose_drift_skips_historical_records(tmp_path):
    """A decision note (docs/notes/) and a changelog describe what was or will be — their
    paths are aspirational/past by design, so the SOFT prose check must not flag them."""
    docs = tmp_path / "docs"
    (docs / "notes" / "foreslaaet" / "arkitektur").mkdir(parents=True)
    (docs / "live.md").write_text("see `core/services/gone.py`")
    (docs / "notes" / "foreslaaet" / "arkitektur" / "2026-01-01-x.md").write_text(
        "see `core/services/gone.py`")
    (docs / "COMMIT_HISTORY.md").write_text("see `core/services/gone.py`")
    out = d.prose_drift(docs, tmp_path)
    flagged = {o["doc"].split("/")[-1] for o in out}
    assert "live.md" in flagged                # a live doc is still checked
    assert "2026-01-01-x.md" not in flagged    # note: skipped
    assert "COMMIT_HISTORY.md" not in flagged  # changelog: skipped


def test_broken_links_still_covers_historical_trees(tmp_path):
    """The HARD link check must NOT inherit the prose filter: a broken link in a note is
    still a broken link — the filter is deliberately scoped to the SOFT prose family."""
    docs = tmp_path / "docs"
    (docs / "notes").mkdir(parents=True)
    (docs / "notes" / "n.md").write_text("[gone](does_not_exist.md)")
    out = d.broken_links(docs)
    assert any(o["doc"].endswith("n.md") for o in out)


# ── To falske positiver i _PATH_RE (målt og rettet 11/10-2026) ──────────────
def test_prose_path_re_does_not_truncate_tsx(tmp_path):
    """`ts` stood before `tsx` in the alternation, so `CodeView.tsx` was cut to a
    nonexistent `CodeView.ts` — a false positive on a file that does exist."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "live.md").write_text("see `apps/jarvis-desk/src/views/CodeView.tsx`")
    (tmp_path / "apps" / "jarvis-desk" / "src" / "views").mkdir(parents=True)
    (tmp_path / "apps" / "jarvis-desk" / "src" / "views" / "CodeView.tsx").write_text("x")
    out = d.prose_drift(docs, tmp_path)
    assert out == [], out


def test_prose_path_re_ignores_paths_nested_in_longer_paths(tmp_path):
    """A path embedded in someone ELSE's absolute path is not ours to judge:
    `/home/bs/.../packages/core/session/README.md` matched `core/session/README.md`."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "live.md").write_text(
        "- `/home/bs/Skrivebord/deepseek-harness/packages/core/session/README.md`")
    out = d.prose_drift(docs, tmp_path)
    assert out == [], out
