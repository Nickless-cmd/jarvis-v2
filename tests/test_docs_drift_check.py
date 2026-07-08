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
