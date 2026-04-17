"""Smoke test for core.services.runtime_resource_signal.

The runtime resource surface should aggregate today's token and cost rows into
both a structured surface and a prompt-friendly summary.
"""

from datetime import UTC, datetime

from core.services import runtime_resource_signal


def test_runtime_resource_surface_aggregates_today_rows(monkeypatch) -> None:
    today = datetime.now(UTC).date().isoformat()
    monkeypatch.setattr(
        runtime_resource_signal,
        "telemetry_summary",
        lambda: {
            "cost_rows": 3,
            "input_tokens": 900,
            "output_tokens": 600,
            "total_cost_usd": 1.25,
        },
    )
    monkeypatch.setattr(
        runtime_resource_signal,
        "recent_costs",
        lambda limit=40: [
            {
                "lane": "visible",
                "provider": "openai",
                "model": "gpt-5.4",
                "input_tokens": 400,
                "output_tokens": 200,
                "cost_usd": 0.75,
                "created_at": f"{today}T10:00:00+00:00",
            },
            {
                "lane": "heartbeat",
                "provider": "openai",
                "model": "gpt-5.4-mini",
                "input_tokens": 100,
                "output_tokens": 50,
                "cost_usd": 0.50,
                "created_at": f"{today}T11:00:00+00:00",
            },
        ],
    )

    surface = runtime_resource_signal.build_runtime_resource_signal_surface()
    prompt = runtime_resource_signal.build_runtime_resource_prompt_section()

    assert surface["today"]["runs"] == 2
    assert surface["pressure"] == "medium"
    assert prompt is not None and "pressure=medium" in prompt
