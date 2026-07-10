from __future__ import annotations
from core.services.doc_repair_agent import is_allowed_doc_path

def test_allows_paths_under_docs():
    assert is_allowed_doc_path("docs/capability_matrix.md") is True
    assert is_allowed_doc_path("docs/notes/x.md") is True

def test_rejects_code_paths():
    assert is_allowed_doc_path("core/services/visible_runs.py") is False
    assert is_allowed_doc_path("apps/api/app.py") is False

def test_rejects_traversal_escape():
    assert is_allowed_doc_path("docs/../core/services/x.py") is False
    assert is_allowed_doc_path("/etc/passwd") is False
    assert is_allowed_doc_path("../secrets.txt") is False

def test_rejects_non_doc_extensions_outside_docs():
    assert is_allowed_doc_path("README.md") is False   # uden for docs/

from core.services import doc_repair_agent as dra

def test_repair_doc_rejects_non_docs_target(isolated_runtime):
    out = dra.repair_doc({"path": "core/services/x.py", "generator": None}, live=True)
    assert out["applied"] is False
    assert out["reason"] == "path-not-allowed"

def test_repair_doc_shadow_does_not_write(tmp_path, isolated_runtime, monkeypatch):
    # Deterministisk generator returnerer nyt indhold; shadow skriver ikke.
    target = {"path": "docs/_test_repair.md", "generator": "test_gen"}
    monkeypatch.setattr(dra, "_run_generator", lambda name: "NEW CONTENT")
    out = dra.repair_doc(target, live=False)
    assert out["shadow"] is True
    assert out["would_write"] is True

def test_find_stale_docs_reads_watchdog(isolated_runtime, monkeypatch):
    monkeypatch.setattr(dra, "check_docs_drift",
                        lambda **k: {"stale": True, "docs": [{"path": "docs/capability_matrix.md",
                                                              "generator": "capability_audit"}]})
    targets = dra.find_stale_docs()
    assert targets and targets[0]["path"] == "docs/capability_matrix.md"

def test_run_tick_shadow_by_default(isolated_runtime, monkeypatch):
    monkeypatch.setattr(dra, "find_stale_docs", lambda: [{"path": "docs/x.md", "generator": "g"}])
    monkeypatch.setattr(dra, "_run_generator", lambda n: "NEW")
    # gate not enforced → shadow
    monkeypatch.setattr(dra, "is_enforced", lambda nerve, klass: False)
    summary = dra.run_doc_repair_tick()
    assert summary["shadow"] is True
    assert summary["would_write"] == 1
    assert summary["applied"] == 0

def test_surface_shape(isolated_runtime, monkeypatch):
    monkeypatch.setattr(dra, "find_stale_docs", lambda: [{"path": "docs/x.md", "generator": "g"}])
    s = dra.build_doc_repair_surface()
    assert s["mode"] == "doc-repair"
    assert "enforced" in s
    assert s["summary"]["stale_count"] == 1
