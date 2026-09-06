"""Hovedbogen skal kende ALLE kald, ikke kun første pas (2026-09-05).

Målt 4. september: 96 første-pas mod 380 agentiske følge-runder til DeepSeek —
hovedbogen kendte 20 % af kaldene. Hver runde sender hele samtalen igen (op til
160k tokens), så de manglende 80 % er ikke småpenge: bogført $2,28 for
1.-5. september mens saldoen faldt omkring $12.
"""
from __future__ import annotations

import inspect
import json
from contextlib import contextmanager

import pytest

from core.services import visible_followup as vf
from core.services import visible_runs


class _FakeResponse:
    def __init__(self, lines):
        self._lines = list(lines)

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return None

    def __iter__(self):
        return iter(self._lines)

    def read(self):
        return b""


@contextmanager
def _stub(monkeypatch, lines):
    import core.services.cheap_provider_runtime as cpr
    monkeypatch.setattr(cpr, "provider_runtime_defaults",
                        lambda pid: {"base_url": "https://api.deepseek.com/v1"}, raising=False)
    monkeypatch.setattr(cpr, "_require_credentials",
                        lambda **kw: {"api_key": "fake-test-key"}, raising=False)  # pragma: allowlist secret
    monkeypatch.setattr(vf.urllib_request, "urlopen", lambda req, timeout=None: _FakeResponse(lines))
    yield


# Verificeret mod den rigtige API 5/9: DeepSeek sender usage i SAMME chunk som
# finish_reason, ikke i en efterfølgende. Dræn-løkken bryder på terminal, så en
# usage-chunk BAGEFTER ville aldrig blive læst — testen skal afspejle
# virkeligheden, ikke omvendt.
_USAGE = (
    b'data: {"choices":[{"delta":{"content":"ok"}}]}\n', b"\n",
    b'data: {"choices":[{"delta":{},"finish_reason":"stop"}],'
    b'"usage":{"prompt_tokens":120000,"completion_tokens":900,'
    b'"prompt_cache_hit_tokens":100000,"prompt_cache_miss_tokens":20000}}\n', b"\n",
    b"data: [DONE]\n", b"\n",
)


def test_a_followup_round_is_written_to_the_ledger(monkeypatch):
    rows: list[dict] = []
    monkeypatch.setattr("core.costing.ledger.record_cost",
                        lambda **kw: rows.append(kw))
    with _stub(monkeypatch, _USAGE):
        list(vf.stream_visible_followup(
            provider="deepseek", model="deepseek-v4-flash",
            base_messages=[{"role": "user", "content": "hi"}], exchanges=[],
            run_id="visible-abc"))
    assert len(rows) == 1
    row = rows[0]
    assert row["lane"] == "agentic_round" and row["run_id"] == "visible-abc"
    assert row["input_tokens"] == 120000 and row["output_tokens"] == 900
    assert row["cache_hit_tokens"] == 100000 and row["cache_miss_tokens"] == 20000
    assert row["cost_usd"] > 0, "prisen skal beregnes, ikke sendes som 0"


def test_the_price_reflects_the_cache_split(monkeypatch):
    """Et cache-hit er langt billigere end en miss — det er hele pointen med
    at maale dem hver for sig."""
    from core.services.llm_pricing import compute_cost_usd
    cheap = compute_cost_usd("deepseek", "deepseek-v4-flash",
                             cache_hit_tokens=120000, cache_miss_tokens=0)
    dear = compute_cost_usd("deepseek", "deepseek-v4-flash",
                            cache_hit_tokens=0, cache_miss_tokens=120000)
    assert dear > cheap * 3


def test_a_round_without_usage_writes_nothing(monkeypatch):
    """Udbydere der ikke sender usage maa ikke give gaettede raekker."""
    rows: list[dict] = []
    monkeypatch.setattr("core.costing.ledger.record_cost", lambda **kw: rows.append(kw))
    lines = (b'data: {"choices":[{"delta":{"content":"ok"}}]}\n', b"\n",
             b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n', b"\n",
             b"data: [DONE]\n", b"\n")
    with _stub(monkeypatch, lines):
        list(vf.stream_visible_followup(
            provider="deepseek", model="deepseek-v4-flash",
            base_messages=[{"role": "user", "content": "hi"}], exchanges=[]))
    assert rows == []


def test_a_ledger_failure_never_kills_the_round(monkeypatch):
    def _boom(**_kw):
        raise RuntimeError("db nede")
    monkeypatch.setattr("core.costing.ledger.record_cost", _boom)
    with _stub(monkeypatch, _USAGE):
        events = list(vf.stream_visible_followup(
            provider="deepseek", model="deepseek-v4-flash",
            base_messages=[{"role": "user", "content": "hi"}], exchanges=[]))
    assert any(isinstance(e, vf.FollowupDone) for e in events)


def test_the_first_pass_no_longer_guesses_a_second_call():
    """`input_tokens * 2` gaettede paa PRAECIS én foelge-runde. Runderne
    bogfoerer nu selv, saa gaettet ville taelle den ene runde to gange."""
    src = inspect.getsource(visible_runs)
    assert "result.input_tokens * 2" not in src
    assert "total_input_tokens = result.input_tokens" in src
