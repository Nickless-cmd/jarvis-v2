import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "docs_audit", Path(__file__).resolve().parents[1] / "scripts" / "docs_audit.py")
da = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(da)


def test_extract_references_paths_and_symbols():
    text = "See `core/services/foo.py` and call `do_the_thing` in apps/api/x.py"
    refs = da.extract_references(text)
    assert "core/services/foo.py" in refs["paths"]
    assert "apps/api/x.py" in refs["paths"]
    assert "do_the_thing" in refs["symbols"]


def test_liveness_resolved_ratio(tmp_path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "alive.py").write_text("x")
    refs = {"paths": ["core/alive.py", "core/dead.py"]}
    live = da.liveness(refs, repo_root=tmp_path)
    assert live["resolved"] == 1 and live["total"] == 2 and live["ratio"] == 0.5


def test_liveness_no_paths():
    assert da.liveness({"paths": []})["ratio"] is None


def test_detect_superseded_newer_wins():
    docs = [
        {"path": "old.md", "title": "arkitektur", "headings": {"a", "b", "c"}, "days": 200},
        {"path": "new.md", "title": "arkitektur", "headings": {"a", "b", "c"}, "days": 5},
    ]
    sup = da.detect_superseded(docs)
    assert sup.get("old.md") == "new.md" and "new.md" not in sup


def test_classify_all_refs_dead_old_is_foraeldet():
    cat, conf, basis = da.classify_heuristic(
        path="x.md", refs={"paths": ["core/gone.py"]}, live={"resolved": 0, "total": 1, "ratio": 0.0},
        days=200, superseded_by=None, is_superpowers=False, shipped=False)
    assert cat == "forældet"


def test_classify_recent_alive_is_faerdig():
    cat, _c, _b = da.classify_heuristic(
        path="x.md", refs={"paths": ["core/a.py"]}, live={"resolved": 1, "total": 1, "ratio": 1.0},
        days=3, superseded_by=None, is_superpowers=False, shipped=False)
    assert cat == "færdig"


def test_classify_superseded_is_droppet():
    cat, _c, _b = da.classify_heuristic(
        path="x.md", refs={"paths": []}, live={"ratio": None}, days=10,
        superseded_by="y.md", is_superpowers=False, shipped=False)
    assert cat == "droppet"


def test_classify_superpowers_shipped_is_faerdig():
    cat, _c, _b = da.classify_heuristic(
        path="p.md", refs={"paths": ["core/x.py"]}, live={"ratio": 1.0, "resolved": 1, "total": 1},
        days=2, superseded_by=None, is_superpowers=True, shipped=True)
    assert cat == "færdig"


def test_classify_ambiguous_is_needs_review():
    cat, _c, _b = da.classify_heuristic(
        path="x.md", refs={"paths": []}, live={"ratio": None}, days=3,
        superseded_by=None, is_superpowers=False, shipped=False)
    assert cat == "needs_review"


def test_stamp_frontmatter_prepends_when_absent():
    out = da.stamp_frontmatter("# Title\n\nbody", {"status": "færdig", "audited": "2026-07-08"})
    assert out.startswith("---\n") and "status: færdig" in out and "# Title" in out


def test_stamp_frontmatter_idempotent_and_preserves_other_keys():
    src = "---\nname: keepme\nstatus: old\n---\n# Title\n"
    once = da.stamp_frontmatter(src, {"status": "forældet"})
    twice = da.stamp_frontmatter(once, {"status": "forældet"})
    assert once == twice                 # idempotent
    assert "name: keepme" in once        # unrelated key preserved
    assert "status: forældet" in once and "status: old" not in once


def test_render_manifest_md_has_rows():
    entries = [{"path": "a.md", "category": "færdig", "basis": "b", "superseded_by": None}]
    md = da.render_manifest_md(entries)
    assert "a.md" in md and "færdig" in md
