"""Bogføringsdækning for session-titlingens direkte Ollama-kald."""
from __future__ import annotations

import json


def test_ollama_titel_bogfoerer_faktiske_tokens(monkeypatch):
    from core.runtime import provider_router
    from core.services import session_titling as mod

    rows: list[dict] = []
    monkeypatch.setattr(
        provider_router,
        "resolve_provider_router_target",
        lambda *, lane: {
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
                    "message": {"content": "En rigtig titel"},
                    "prompt_eval_count": 800,
                    "prompt_eval_cached_count": 500,
                    "eval_count": 12,
                }
            ).encode()

    monkeypatch.setattr(mod.urllib_request, "urlopen", lambda *_a, **_kw: _Response())

    assert mod._ollama_lane_titel("Bjørn: hej") == "En rigtig titel"
    assert len(rows) == 1
    assert rows[0]["input_tokens"] == 800
    assert rows[0]["output_tokens"] == 12
    assert rows[0]["cache_hit_tokens"] == 500
    assert rows[0]["cache_miss_tokens"] == 300
    assert rows[0]["cost_usd"] > 0
