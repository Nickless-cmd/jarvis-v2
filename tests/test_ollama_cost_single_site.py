"""Regression: ét native Ollama-providerkald giver præcis én costs-række."""

from __future__ import annotations

import json
import types


def _fake_ollama_http(monkeypatch) -> None:
    import core.services.cheap_provider_runtime_adapters as adapters

    payload = json.dumps(
        {
            "message": {"content": "OK"},
            "prompt_eval_count": 700,
            "prompt_eval_cached_count": 450,
            "eval_count": 18,
        }
    ).encode("utf-8")

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return payload

    monkeypatch.setattr(
        adapters,
        "urllib_request",
        types.SimpleNamespace(
            Request=adapters.urllib_request.Request,
            urlopen=lambda *_args, **_kwargs: _Response(),
        ),
    )


def _cost_rows(provider: str, model: str) -> list[dict[str, object]]:
    import core.costing.ledger as ledger

    with ledger.connect() as conn:
        rows = conn.execute(
            "SELECT lane, provider, model, input_tokens, output_tokens "
            "FROM costs WHERE provider=? AND model=? ORDER BY id",
            (provider, model),
        ).fetchall()
    return [dict(row) for row in rows]


def test_selection_ollama_provider_call_records_exactly_one_cost_row(
    isolated_runtime, monkeypatch
) -> None:
    """Mutation caught: restoring selection.record_cost for owned Ollama results."""
    import core.services.cheap_provider_runtime_selection as selection

    provider = "ollama-a2"
    model = "single-site-selection:cloud"
    _fake_ollama_http(monkeypatch)
    monkeypatch.setattr(
        selection,
        "select_cheap_lane_target",
        lambda **_kwargs: {
            "active": True,
            "provider": provider,
            "model": model,
            "auth_profile": "account2",
            "base_url": "https://ollama.test",
        },
    )
    monkeypatch.setattr(selection, "_record_provider_success", lambda **_kwargs: None)

    selection.execute_cheap_lane_via_pool(message="hej")

    rows = _cost_rows(provider, model)
    assert rows == [
        {
            "lane": "cheap",
            "provider": provider,
            "model": model,
            "input_tokens": 700,
            "output_tokens": 18,
        }
    ]


def test_balancer_ollama_provider_call_records_exactly_one_cost_row(
    isolated_runtime, monkeypatch, tmp_path
) -> None:
    """Mutation caught: restoring balancer.record_cost for owned Ollama results."""
    import core.services.cheap_lane_balancer as balancer

    provider = "ollama-a2"
    model = "single-site-balancer:cloud"
    slot = balancer.BalancerSlot(
        provider=provider,
        model=model,
        auth_profile="account2",
        base_url="https://ollama.test",
        rpm_limit=None,
        daily_limit=None,
        is_public_proxy=False,
    )
    _fake_ollama_http(monkeypatch)
    monkeypatch.setattr(balancer, "_state_path", lambda: tmp_path / "state.json")
    monkeypatch.setattr(balancer, "build_slot_pool", lambda: [slot])

    result = balancer.call_balanced(prompt="hej", daemon_name="regression")

    assert result["status"] == "ok"
    rows = _cost_rows(provider, model)
    assert rows == [
        {
            "lane": "cheap",
            "provider": provider,
            "model": model,
            "input_tokens": 700,
            "output_tokens": 18,
        }
    ]


def test_role_primary_ollama_provider_call_records_exactly_one_cost_row(
    isolated_runtime, monkeypatch
) -> None:
    """Mutation caught: primary-direct must honour the adapter's ownership."""
    import core.runtime.provider_router as provider_router
    import core.services.cheap_provider_runtime as runtime
    from core.services.non_visible_lane_execution import execute_with_role_or_fallback

    provider = "ollama-a2"
    model = "single-site-primary:cloud"
    _fake_ollama_http(monkeypatch)
    monkeypatch.setattr(
        provider_router,
        "load_provider_router_registry",
        lambda: {
            "providers": [
                {
                    "provider": provider,
                    "auth_profile": "account2",
                    "base_url": "https://ollama.test",
                }
            ]
        },
    )
    monkeypatch.setattr(
        runtime,
        "provider_runtime_defaults",
        lambda _provider: {"base_url": "https://ollama.test"},
    )

    result = execute_with_role_or_fallback(
        message="hej", provider=provider, model=model, lane="primary"
    )

    assert result["execution_mode"] == "role-primary-direct"
    assert _cost_rows(provider, model) == [
        {
            "lane": "cheap",
            "provider": provider,
            "model": model,
            "input_tokens": 700,
            "output_tokens": 18,
        }
    ]


def test_daemon_ollama_provider_call_records_exactly_one_cost_row(
    isolated_runtime, monkeypatch, tmp_path
) -> None:
    """Mutation caught: daemon wrapper must not rebook an owned provider result."""
    import core.services.cheap_lane_balancer as balancer
    import core.services.daemon_llm as daemon_llm

    provider = "ollama-a2"
    model = "single-site-daemon:cloud"
    slot = balancer.BalancerSlot(
        provider=provider,
        model=model,
        auth_profile="account2",
        base_url="https://ollama.test",
        rpm_limit=None,
        daily_limit=None,
        is_public_proxy=False,
    )
    _fake_ollama_http(monkeypatch)
    monkeypatch.setattr(balancer, "_state_path", lambda: tmp_path / "state.json")
    monkeypatch.setattr(balancer, "build_slot_pool", lambda: [slot])
    monkeypatch.setattr(daemon_llm, "_get_cache_ttl", lambda _name: 0)

    text = daemon_llm.daemon_llm_call("hej", daemon_name="regression")

    assert text == "OK"
    assert _cost_rows(provider, model) == [
        {
            "lane": "cheap",
            "provider": provider,
            "model": model,
            "input_tokens": 700,
            "output_tokens": 18,
        }
    ]
