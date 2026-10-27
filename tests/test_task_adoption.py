from __future__ import annotations


def test_task_adoption_hint_is_empty_when_contract_is_off(monkeypatch):
    from core.services.prompt_sections import task_adoption

    monkeypatch.setattr(
        "core.services.agent_contract_service.capability_enabled", lambda: False,
    )
    assert task_adoption.task_adoption_hint() == ""


def test_task_adoption_hint_names_only_the_contract_path(monkeypatch):
    from core.services.prompt_sections import task_adoption

    monkeypatch.setattr(
        "core.services.agent_contract_service.capability_enabled", lambda: True,
    )
    hint = task_adoption.task_adoption_hint()
    assert "`Task`" in hint
    assert "spawn_agent_task" not in hint
    assert "scout_agent" not in hint
    assert "dispatch_code_mode_task" not in hint


def test_task_adoption_hint_fails_closed(monkeypatch):
    from core.services.prompt_sections import task_adoption

    def _broken() -> bool:
        raise RuntimeError("state unavailable")

    monkeypatch.setattr(
        "core.services.agent_contract_service.capability_enabled", _broken,
    )
    assert task_adoption.task_adoption_hint() == ""
