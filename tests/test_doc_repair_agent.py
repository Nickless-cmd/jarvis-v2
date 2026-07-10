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
