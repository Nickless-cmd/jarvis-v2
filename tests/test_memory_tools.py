"""Tests for memory_tools write-path bruger-resolution (isolation/privacy)."""
from __future__ import annotations

import core.tools.memory_tools as mt


def test_resolve_uid_prefers_explicit(monkeypatch):
    assert mt._resolve_memory_uid("u-explicit") == "u-explicit"


def test_resolve_uid_uses_current_user_id(monkeypatch):
    import core.identity.workspace_context as wc
    monkeypatch.setattr(wc, "current_user_id", lambda: "u-ctx")
    assert mt._resolve_memory_uid() == "u-ctx"


def test_resolve_uid_falls_back_to_session_owner(monkeypatch):
    # Owner-scenariet: current_user_id() er TOM inde i run-generatoren, men
    # session_id er bundet → resolve via session-ejer.
    import core.identity.workspace_context as wc
    import core.services.chat_sessions as cs
    monkeypatch.setattr(wc, "current_user_id", lambda: "")
    monkeypatch.setattr(wc, "current_session_id", lambda: "sess-123")
    monkeypatch.setattr(cs, "get_session_owner", lambda sid: "owner-uid" if sid == "sess-123" else None)
    assert mt._resolve_memory_uid() == "owner-uid"


def test_memory_md_uses_workspace_when_uid_resolved(monkeypatch, tmp_path):
    import core.tools.memory_tools as m
    monkeypatch.setattr(m, "_resolve_memory_uid", lambda user_id=None: "bjorn")
    monkeypatch.setattr(m, "workspace_dir", lambda uid: tmp_path / "workspaces" / uid)
    p = m._memory_md()
    assert p == tmp_path / "workspaces" / "bjorn" / "MEMORY.md"


def test_memory_md_falls_back_to_shared_without_uid(monkeypatch, tmp_path):
    import core.tools.memory_tools as m
    monkeypatch.setattr(m, "_resolve_memory_uid", lambda user_id=None: "")
    monkeypatch.setattr(m, "shared_dir", lambda: tmp_path / "shared")
    p = m._memory_md()
    assert p == tmp_path / "shared" / "MEMORY.md"


# ── 2026-09-04 (memory repair, R7): section writes go through memory_md_writer ──


def test_upsert_section_matches_heading_case_insensitively(tmp_path, monkeypatch):
    from core.tools import memory_tools as mt

    p = tmp_path / "MEMORY.md"
    p.write_text("# MEMORY\n\n## Decisions\n- gammel\n", encoding="utf-8")
    monkeypatch.setattr(mt, "_memory_md", lambda user_id=None: p)
    monkeypatch.setattr(mt, "_read_memory", lambda: p.read_text(encoding="utf-8"))
    monkeypatch.setattr("core.services.memory_write_queue.enqueue_write", lambda *a, **k: None)
    out = mt._exec_memory_upsert_section({"heading": "decisions", "content": "- ny"})
    assert out["status"] == "ok" and out["action"] == "updated"
    text = p.read_text(encoding="utf-8")
    assert text.count("## ") == 1 and "- ny" in text and "- gammel" not in text
