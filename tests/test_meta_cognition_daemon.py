"""Bölge 2 routing-dækning for core/services/meta_cognition_daemon.py (form-dommer choke-point).

Verificerer at daemonens LLM-kald nu går gennem daemon_llm-choke-pointet (daemon_llm_call),
så form-dommeren + TTL-cachen fanger gentagne kald. Import-smoke + kilde-assertion.
"""
from __future__ import annotations

import importlib
from pathlib import Path


def test_module_imports():
    assert importlib.import_module("core.services.meta_cognition_daemon") is not None


def test_routes_through_form_judge_chokepoint():
    src = Path("core/services/meta_cognition_daemon.py").read_text(encoding="utf-8")
    assert "daemon_llm_call" in src, "Bölge 2: meta_cognition_daemon skal rute LLM-kald gennem daemon_llm_call"


def test_ollama_fallback_bogfoerer_faktiske_tokens(monkeypatch):
    import json
    from core.runtime import provider_router
    from core.services import daemon_llm
    from core.services import meta_cognition_daemon as mod

    rows: list[dict] = []
    monkeypatch.setattr(daemon_llm, "daemon_llm_call", lambda *_a, **_kw: "")
    monkeypatch.setattr(
        provider_router,
        "resolve_provider_router_target",
        lambda *, lane: {
            "active": True,
            "provider": "ollama",
            "model": "deepseek-v4.1-flash:cloud",
            "base_url": "https://ollama.test",
        },
    )
    monkeypatch.setattr(
        "core.costing.ledger.record_cost", lambda **kw: rows.append(kw)
    )

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def read(self):
            return json.dumps(
                {
                    "message": {"content": "Jeg observerer mig selv."},
                    "prompt_eval_count": 900,
                    "prompt_eval_cached_count": 600,
                    "eval_count": 25,
                }
            ).encode()

    monkeypatch.setattr(mod.urllib_request, "urlopen", lambda *_a, **_kw: _Response())

    assert mod._call_meta_llm("prompt") == "Jeg observerer mig selv."
    assert len(rows) == 1
    assert rows[0]["input_tokens"] == 900
    assert rows[0]["output_tokens"] == 25
    assert rows[0]["cache_hit_tokens"] == 600
    assert rows[0]["cache_miss_tokens"] == 300
    assert rows[0]["cost_usd"] > 0
