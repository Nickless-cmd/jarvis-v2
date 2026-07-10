from __future__ import annotations
from core.memory.memory_topic_store import sanitize_slug, curated_path_for

def test_sanitize_keeps_safe_chars():
    assert sanitize_slug("Project Alpha!") == "project-alpha"
    assert sanitize_slug("já_vis-2") == "j-_vis-2" or sanitize_slug("já_vis-2") == "ja_vis-2"

def test_sanitize_rejects_empty():
    assert sanitize_slug("") is None
    assert sanitize_slug("!!!") is None
    assert sanitize_slug("   ") is None

def test_curated_path_stays_in_user_curated_dir(isolated_runtime):
    p = curated_path_for("my-topic", name="default")
    assert p is not None
    assert p.name == "my-topic.md"
    assert p.parent.name == "curated"

def test_curated_path_rejects_traversal(isolated_runtime):
    # Et slug der forsoeger at escape via traversal saniteres til uskadeligt ELLER afvises.
    assert curated_path_for("../../etc/passwd", name="default") is None or \
           curated_path_for("../../etc/passwd", name="default").parent.name == "curated"
    assert curated_path_for("..", name="default") is None
