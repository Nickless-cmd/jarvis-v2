"""Tests for core/services/prompt_dump.py (30/9-2026).

Dækker: inert uden sentinel, fuld payload (messages+tools+params) med sentinel,
rotation latest→prev, og at funktionen er self-safe (kaster aldrig).
"""
from __future__ import annotations

import json
from pathlib import Path

from core.services import prompt_dump as pd


def test_inert_without_sentinel(tmp_path, monkeypatch):
    monkeypatch.setattr(pd, "_SENTINEL", str(tmp_path / "nope"))
    monkeypatch.setattr(pd, "_DUMP_DIR", str(tmp_path / "dumps"))
    assert pd.is_armed() is False
    pd.dump_payload(provider="p", model="m", messages=[{"role": "user", "content": "x"}])
    assert not (tmp_path / "dumps").exists()


def test_dumps_full_payload_with_sentinel(tmp_path, monkeypatch):
    sentinel = tmp_path / "armed"
    sentinel.write_text("")
    monkeypatch.setattr(pd, "_SENTINEL", str(sentinel))
    monkeypatch.setattr(pd, "_DUMP_DIR", str(tmp_path / "dumps"))

    msgs = [{"role": "system", "content": "hej"}, {"role": "user", "content": "Bjørn"}]
    tools = [{"type": "function", "function": {"name": "read_file"}}]
    pd.dump_payload(
        provider="deepseek", model="deepseek-v4-flash", messages=msgs,
        tools=tools, params={"temperature": 0.7}, lane="visible-stream", round_index=0,
    )

    latest = Path(tmp_path / "dumps" / "latest.json")
    assert latest.exists()
    got = json.loads(latest.read_text(encoding="utf-8"))
    # Værktøjslisten SKAL med — det var hele grunden til modulet.
    assert got["tools"] == tools
    assert got["messages"] == msgs
    assert got["params"] == {"temperature": 0.7}
    assert got["provider"] == "deepseek"
    assert got["lane"] == "visible-stream"


def test_rotates_latest_to_prev(tmp_path, monkeypatch):
    sentinel = tmp_path / "armed"
    sentinel.write_text("")
    monkeypatch.setattr(pd, "_SENTINEL", str(sentinel))
    monkeypatch.setattr(pd, "_DUMP_DIR", str(tmp_path / "dumps"))

    pd.dump_payload(provider="p", model="m", messages=[{"role": "user", "content": "først"}])
    pd.dump_payload(provider="p", model="m", messages=[{"role": "user", "content": "anden"}])

    prev = json.loads((tmp_path / "dumps" / "prev.json").read_text(encoding="utf-8"))
    latest = json.loads((tmp_path / "dumps" / "latest.json").read_text(encoding="utf-8"))
    assert prev["messages"][0]["content"] == "først"
    assert latest["messages"][0]["content"] == "anden"


def test_never_raises_on_bad_input(tmp_path, monkeypatch):
    sentinel = tmp_path / "armed"
    sentinel.write_text("")
    monkeypatch.setattr(pd, "_SENTINEL", str(sentinel))
    # Umulig mappe (en fil hvor der skal være en mappe) → skal sluge fejlen.
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    monkeypatch.setattr(pd, "_DUMP_DIR", str(blocker / "sub"))
    pd.dump_payload(provider="p", model="m", messages=None)  # må ikke kaste
