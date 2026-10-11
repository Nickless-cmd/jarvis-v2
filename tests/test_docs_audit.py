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


# ── 11/10-2026: udvidelsen. Audit'et meldte «gaps: []» mens 241 levende docs bar
# døde stier. Mønsteret fangede kun core|apps|scripts, og opløsningen kendte kun
# repo-roden — så `../tests/x.py`, `tests/…`, `docs/…` og skills-relative stier
# blev aldrig set. Testene her låser den brede fangst og den rigtige opløsning.

def test_extract_references_catches_more_prefixes():
    refs = da.extract_references("Se `tests/test_x.py`, `docs/guide.md` og `src/App.tsx`.")
    assert "tests/test_x.py" in refs["paths"]
    assert "docs/guide.md" in refs["paths"]
    assert "src/App.tsx" in refs["paths"]


def test_extract_references_ignores_urls():
    # Et link er en kildehenvisning, ikke en påstand om at filen ligger i træet.
    refs = da.extract_references("Se https://github.com/x/y/blob/main/core/gone.py for detaljer")
    assert "core/gone.py" not in refs["paths"]


def test_liveness_relative_to_doc_dir(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "real.py").write_text("x")
    live = da.liveness({"paths": ["../tests/real.py"]}, repo_root=tmp_path,
                       doc_rel="docs/sub/x.md")
    assert live["resolved"] == 1 and live["ratio"] == 1.0


def test_liveness_suffix_match_against_tree(tmp_path):
    # `src/App.tsx` er en ÆGTE fil — den ligger bare under apps/mobile. Uden
    # suffix-opløsningen ville den stå som død.
    (tmp_path / "apps" / "mobile" / "src").mkdir(parents=True)
    (tmp_path / "apps" / "mobile" / "src" / "App.tsx").write_text("x")
    live = da.liveness({"paths": ["src/App.tsx"]}, repo_root=tmp_path, doc_rel="docs/x.md")
    assert live["resolved"] == 1


def test_liveness_runtime_home(tmp_path):
    runtime = tmp_path / "home"
    (runtime / "config").mkdir(parents=True)
    (runtime / "config" / "runtime.json").write_text("{}")
    live = da.liveness({"paths": ["~/.jarvis-v2/config/runtime.json"]},
                       repo_root=tmp_path / "repo", runtime_root=runtime)
    assert live["resolved"] == 1


def test_dead_paths_reports_missing(tmp_path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "alive.py").write_text("x")
    dead = da.dead_paths({"paths": ["core/alive.py", "core/gone.py"]},
                         repo_root=tmp_path, doc_rel="docs/x.md")
    assert dead == ["core/gone.py"]


def test_absolute_system_path_is_unverifiable_not_dead(tmp_path):
    # /etc og /tmp ligger uden for træet. Vi kan ikke sige de er døde — kun at
    # vi ikke kan se dem herfra.
    dead = da.dead_paths({"paths": ["/etc/nginx/nginx.conf"]}, repo_root=tmp_path, doc_rel="x.md")
    assert dead == []


def test_audit_surfaces_dead_paths(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "loegn.md").write_text("# T\n\nSe `core/gone.py`.\n")
    monkeypatch.setattr(da, "DOCS_ROOT", tmp_path / "docs")
    monkeypatch.setattr(da, "SKILLS_ROOT", tmp_path / ".claude" / "skills")
    monkeypatch.setattr(da, "REPO_ROOT", tmp_path)
    res = da.audit()
    assert res["dead_paths_total"] == 1
    assert res["docs"][0]["dead_paths"] == ["core/gone.py"]
