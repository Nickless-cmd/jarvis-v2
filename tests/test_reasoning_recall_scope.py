from __future__ import annotations

from core.identity.workspace_context import user_context


def _enable_scoped_recall() -> None:
    from core.services.scoped_recall_policy import set_recall_enabled

    set_recall_enabled(True)


def test_reasoning_recall_is_user_scoped_and_lexically_ranked(isolated_runtime) -> None:
    from core.services.reasoning_store import capture_conclusion, recall_reasoning

    _enable_scoped_recall()
    with user_context(discord_id="user-a"):
        capture_conclusion(source="manual", conclusion_text="OAuth token rotation procedure")
        capture_conclusion(source="manual", conclusion_text="Unrelated garden notes")
    with user_context(discord_id="user-b"):
        capture_conclusion(source="manual", conclusion_text="OAuth secret belonging to B")

    with user_context(discord_id="user-a"):
        rows = recall_reasoning(query_text="oauth token", limit=10)

    assert [row["conclusion_text"] for row in rows] == ["OAuth token rotation procedure"]
    assert rows[0]["ranking_method"] == "lexical"


def test_reasoning_recall_disabled_returns_standard_shape_without_db(monkeypatch) -> None:
    from core.services import reasoning_store

    monkeypatch.setattr(reasoning_store.scoped_recall_policy, "recall_enabled", lambda: False)
    monkeypatch.setattr(
        reasoning_store,
        "connect",
        lambda: (_ for _ in ()).throw(AssertionError("DB must not be touched")),
    )

    result = reasoning_store.recall_reasoning(query_text="anything")

    assert result == {
        "status": "disabled",
        "path": "reasoning_recall",
        "results": [],
        "count": 0,
    }


def test_reasoning_capture_event_contains_no_content_or_record_id(
    isolated_runtime, monkeypatch
) -> None:
    from core.services import reasoning_store

    published: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(
        reasoning_store.event_bus,
        "publish",
        lambda kind, payload: published.append((kind, payload)),
    )
    with user_context(discord_id="user-a"):
        reasoning_store.capture_conclusion(
            source="manual",
            conclusion_text="private reasoning text",
            emit_event=True,
        )

    assert published
    assert published[0][1] == {
        "source": "manual",
        "confidence": 0.0,
        "owner_scoped": True,
    }
