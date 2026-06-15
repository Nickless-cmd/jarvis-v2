"""Tests for tool_chip_payload (spec 2026-06-15)."""
from __future__ import annotations

from core.services.tool_chip_payload import build_tool_capability_payload


def test_includes_args_and_result() -> None:
    p = build_tool_capability_payload(
        tool="web_search", status="ok",
        arguments={"query": "vejr"}, result_text="3 resultater",
    )
    assert p["type"] == "tool_result"
    assert p["tool"] == "web_search"
    assert p["status"] == "ok"
    assert p["arguments"] == {"query": "vejr"}
    assert p["result_text"] == "3 resultater"


def test_strips_internal_keys() -> None:
    p = build_tool_capability_payload(
        tool="x", status="ok",
        arguments={"query": "a", "_runtime_user_id": "u1", "session_id": "s", "_runtime_trust_all": True},
        result_text="",
    )
    assert p["arguments"] == {"query": "a"}


def test_truncates_long_arg_value() -> None:
    p = build_tool_capability_payload(
        tool="x", status="ok",
        arguments={"text": "a" * 1000}, result_text="", arg_value_cap=600,
    )
    assert len(p["arguments"]["text"]) == 601  # 600 + ellipsis
    assert p["arguments"]["text"].endswith("…")


def test_truncates_long_result() -> None:
    p = build_tool_capability_payload(
        tool="x", status="ok", arguments={}, result_text="b" * 5000, result_cap=4000,
    )
    assert p["result_text"].startswith("b" * 4000)
    assert "trunkeret" in p["result_text"]


def test_handles_non_dict_args() -> None:
    p = build_tool_capability_payload(tool="x", status="ok", arguments=None, result_text="r")
    assert p["arguments"] == {}
    assert p["result_text"] == "r"
