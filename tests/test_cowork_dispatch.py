"""Tests for cowork_dispatch (§18.5 runtime→app instruktioner)."""
from __future__ import annotations

import pytest


def test_build_instruction_valid() -> None:
    from core.services.cowork_dispatch import build_app_instruction
    instr = build_app_instruction(action="send_message", target_user="d-mikkel",
                                  channel="discord", payload={"text": "hej"}, requester="bjorn")
    assert instr["action"] == "send_message"
    assert instr["target_user"] == "d-mikkel"
    assert instr["channel"] == "discord"
    assert instr["payload"] == {"text": "hej"}


def test_build_instruction_invalid_action() -> None:
    from core.services.cowork_dispatch import build_app_instruction
    with pytest.raises(ValueError):
        build_app_instruction(action="rm_rf", target_user="x")


def test_build_instruction_missing_target() -> None:
    from core.services.cowork_dispatch import build_app_instruction
    with pytest.raises(ValueError):
        build_app_instruction(action="notify", target_user="")


def test_dispatch_ok() -> None:
    from core.services.cowork_dispatch import dispatch_to_app
    res = dispatch_to_app(action="notify", target_user="d-bjorn", payload={"text": "møde 15"})
    assert res["ok"] is True
    assert res["instruction"]["action"] == "notify"


def test_dispatch_invalid() -> None:
    from core.services.cowork_dispatch import dispatch_to_app
    res = dispatch_to_app(action="bogus", target_user="d-bjorn")
    assert res["ok"] is False and "reason" in res
