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


from core.memory import memory_topic_store as mts

def test_write_confirmed_then_read(isolated_runtime):
    out = mts.write_topic_confirmed("alpha", title="Alpha", hook="om alpha",
                                    body="# Alpha\n\nfuld krop", name="default")
    assert out["confirmed"] is True
    assert mts.read_topic("alpha", name="default") == "# Alpha\n\nfuld krop"

def test_read_missing_returns_none(isolated_runtime):
    assert mts.read_topic("does-not-exist", name="default") is None

def test_read_rejects_bad_slug(isolated_runtime):
    assert mts.read_topic("..", name="default") is None

def test_write_bad_slug_not_confirmed(isolated_runtime):
    out = mts.write_topic_confirmed("!!!", title="x", hook="y", body="z", name="default")
    assert out["confirmed"] is False
    assert out["reason"] == "bad-slug"


from core.identity.workspace_bootstrap import workspace_memory_paths

def _index_text(name="default"):
    from core.memory.memory_topic_store import topic_index_path_for
    p = topic_index_path_for(name=name)
    return p.read_text(encoding="utf-8") if p.exists() else ""

def test_write_confirmed_upserts_index_line(isolated_runtime):
    mts.write_topic_confirmed("alpha", title="Alpha", hook="om alpha",
                              body="krop", name="default")
    idx = _index_text()
    assert "(curated/alpha.md)" in idx
    assert "Alpha" in idx and "om alpha" in idx

def test_index_upsert_is_idempotent(isolated_runtime):
    mts.write_topic_confirmed("alpha", title="Alpha", hook="h1", body="b1", name="default")
    mts.write_topic_confirmed("alpha", title="Alpha", hook="h2", body="b2", name="default")
    idx = _index_text()
    assert idx.count("(curated/alpha.md)") == 1     # opdateret, ikke dubleret
    assert "h2" in idx and "h1" not in idx          # nyeste hook vinder

def test_index_untouched_when_body_write_fails(isolated_runtime, monkeypatch):
    # Simulér krops-skriv-fejl → index maa ALDRIG opdateres.
    def _boom(*a, **k): raise OSError("disk full")
    monkeypatch.setattr("pathlib.Path.write_text", _boom)
    out = mts.write_topic_confirmed("beta", title="Beta", hook="h", body="b", name="default")
    assert out["confirmed"] is False
    assert "(curated/beta.md)" not in _index_text()
