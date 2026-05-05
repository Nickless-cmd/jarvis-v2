from __future__ import annotations


def test_create_decision_dedupes_active_directive(monkeypatch) -> None:
    from core.services import behavioral_decisions as bd

    existing = {
        "decision_id": "dec-existing",
        "directive": "Stop after five tool calls.",
        "priority": 80,
        "status": "active",
    }
    created = []
    published = []
    monkeypatch.setattr(bd, "_db_list", lambda **kwargs: [existing])
    monkeypatch.setattr(bd, "_db_create", lambda **kwargs: created.append(kwargs) or {"decision_id": "new"})
    monkeypatch.setattr(bd.event_bus, "publish", lambda kind, payload: published.append((kind, payload)))

    result = bd.create_decision(
        directive="  stop   after five tool calls. ",
        priority=75,
        created_by="test",
    )

    assert result["decision_id"] == "dec-existing"
    assert result["deduped"] is True
    assert created == []
    assert published[0][0] == "decision.deduped"


def test_create_decision_creates_when_directive_is_new(monkeypatch) -> None:
    from core.services import behavioral_decisions as bd

    monkeypatch.setattr(bd, "_db_list", lambda **kwargs: [])
    monkeypatch.setattr(
        bd,
        "_db_create",
        lambda **kwargs: {"decision_id": "dec-new", "directive": kwargs["directive"], "priority": kwargs["priority"]},
    )
    monkeypatch.setattr(bd.event_bus, "publish", lambda *args, **kwargs: None)

    result = bd.create_decision(directive="Surface status before silence.", priority=70)

    assert result["decision_id"] == "dec-new"
    assert result.get("deduped") is None
