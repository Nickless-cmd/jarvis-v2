"""Per-request cache-telemetri (core/services/cache_telemetry.py, 2026-06-30).

Verificér at prefix-signaturen er deterministisk + følsom (tool-ændring → ny hash),
og at record_visible_cache skriver en korrekt JSONL-linje + er self-safe.
"""
from __future__ import annotations

import json

from core.services import cache_telemetry as ct


def test_prefix_signature_deterministic_and_tool_sensitive():
    tools_a = [{"type": "function", "function": {"name": "f", "parameters": {}}}]
    tools_b = [{"type": "function", "function": {"name": "g", "parameters": {}}}]
    sha1, n1 = ct.prefix_signature("system", tools_a)
    sha2, n2 = ct.prefix_signature("system", tools_a)
    sha3, _ = ct.prefix_signature("system", tools_b)
    assert sha1 and sha1 == sha2          # deterministisk
    assert n1 == n2 and n1 > 0
    assert sha1 != sha3                    # tool-ændring → ny hash (cache-breaker)


def test_prefix_signature_key_order_invariant():
    # sort_keys → samme indhold i forskellig dict-rækkefølge giver SAMME hash.
    a = [{"type": "function", "function": {"name": "f", "parameters": {}}}]
    b = [{"function": {"parameters": {}, "name": "f"}, "type": "function"}]
    assert ct.prefix_signature("s", a)[0] == ct.prefix_signature("s", b)[0]


def test_record_writes_jsonl_line(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    ct.record_visible_cache(
        run_id="visible-abc", round_index=3, autonomous=False, lane="visible",
        provider="deepseek", model="deepseek-v4-flash",
        prefix_sha="deadbeef", prefix_len=12345, cache_hit=90000, cache_miss=1000,
    )
    log = tmp_path / "logs" / "cache_telemetry.jsonl"
    row = json.loads(log.read_text().strip())
    assert row["run_id"] == "visible-abc"
    assert row["round"] == 3
    assert row["prefix_sha"] == "deadbeef"
    assert row["hit"] == 90000 and row["miss"] == 1000
    assert row["pct"] == round(100.0 * 90000 / 91000, 1)


def test_record_is_self_safe_on_bad_input(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    # Ingen exception selv med rod-input.
    ct.record_visible_cache(run_id=None, round_index="x", cache_hit=None)  # type: ignore[arg-type]


def test_zero_total_pct_is_zero(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    ct.record_visible_cache(run_id="r", cache_hit=0, cache_miss=0)
    row = json.loads((tmp_path / "logs" / "cache_telemetry.jsonl").read_text().strip())
    assert row["pct"] == 0.0
