from __future__ import annotations

import sys
import types


def test_semantic_indexer_handles_sensory_event_without_starting_threads(monkeypatch):
    from core.services import semantic_indexer
    from core.services import semantic_memory

    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        semantic_memory,
        "index_memory",
        lambda **kwargs: calls.append(kwargs) or True,
    )

    fake_db_sensory = types.SimpleNamespace(
        get_sensory_memory=lambda sid: {
            "id": sid,
            "content": "A clear workspace screenshot.",
            "modality": "visual",
        }
    )
    monkeypatch.setitem(sys.modules, "core.runtime.db_sensory", fake_db_sensory)

    semantic_indexer._handle_sensory({"id": "sensory-1"})

    assert calls == [
        {
            "source_table": "sensory_memories",
            "source_id": "sensory-1",
            "content": "A clear workspace screenshot.",
            "modality": "visual",
        }
    ]


def test_semantic_indexer_handles_private_brain_event_with_summary_and_detail(
    monkeypatch,
):
    from core.runtime import db
    from core.services import semantic_indexer
    from core.services import semantic_memory

    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        semantic_memory,
        "index_memory",
        lambda **kwargs: calls.append(kwargs) or True,
    )
    monkeypatch.setattr(
        db,
        "get_private_brain_record",
        lambda rid: {
            "record_id": rid,
            "summary": "Decision pattern held.",
            "detail": "Verification happened before mutation.",
            "record_type": "decision",
        },
    )

    semantic_indexer._handle_private_brain({"record_id": "brain-1"})

    assert calls == [
        {
            "source_table": "private_brain_records",
            "source_id": "brain-1",
            "content": "Decision pattern held.\nVerification happened before mutation.",
            "modality": "decision",
        }
    ]


def test_inheritance_seed_writes_only_collected_sections(tmp_path, monkeypatch):
    from core.identity import workspace_bootstrap
    from core.services import inheritance_seed

    monkeypatch.setattr(
        workspace_bootstrap,
        "ensure_default_workspace",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        inheritance_seed,
        "_collect_sections",
        lambda: [
            ("Uafsluttede tanke-forslag", ["Review partial service proof."]),
            ("Tom sektion", []),
        ],
    )

    assert inheritance_seed.write_inheritance_seed() is True

    path = tmp_path / "INHERITANCE_SEED.md"
    text = path.read_text(encoding="utf-8")
    assert "# Inheritance Seed" in text
    assert "Review partial service proof." in text
    assert "Tom sektion" not in text
    assert "Dette er ikke en to-do liste. Det er en åbning." in text


def test_inheritance_seed_read_returns_empty_when_missing(tmp_path, monkeypatch):
    from core.identity import workspace_bootstrap
    from core.services import inheritance_seed

    monkeypatch.setattr(
        workspace_bootstrap,
        "ensure_default_workspace",
        lambda: tmp_path,
    )

    assert inheritance_seed.read_inheritance_seed() == ""
