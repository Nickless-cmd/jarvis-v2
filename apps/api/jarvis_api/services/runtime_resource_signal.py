"""Runtime resource awareness signal.

Surfaces compact token / cost / lane telemetry to Jarvis' own prompts
so he has bounded awareness of how much budget he is consuming. He
previously had no way to see this — only Mission Control rendered
costing data, and his own prompts had no resource signal at all.

Bounded by design: this is a cheap projection, not a full ledger
dump. Only the most recent activity and today's totals are surfaced.
"""

from __future__ import annotations

from datetime import UTC, datetime

from core.costing.ledger import recent_costs, telemetry_summary


def build_runtime_resource_signal_surface() -> dict[str, object]:
    summary = telemetry_summary()
    rows = recent_costs(limit=40)
    today_iso = datetime.now(UTC).date().isoformat()
    today_rows = [r for r in rows if str(r.get("created_at") or "").startswith(today_iso)]

    today_input = sum(int(r.get("input_tokens") or 0) for r in today_rows)
    today_output = sum(int(r.get("output_tokens") or 0) for r in today_rows)
    today_cost = sum(float(r.get("cost_usd") or 0.0) for r in today_rows)

    latest = rows[0] if rows else {}
    lanes_today = sorted({str(r.get("lane") or "") for r in today_rows if r.get("lane")})
    providers_today = sorted({str(r.get("provider") or "") for r in today_rows if r.get("provider")})

    pressure = _derive_pressure(today_input + today_output, today_cost)

    return {
        "active": bool(rows),
        "today": {
            "runs": len(today_rows),
            "input_tokens": today_input,
            "output_tokens": today_output,
            "total_tokens": today_input + today_output,
            "cost_usd": round(today_cost, 4),
            "lanes": lanes_today,
            "providers": providers_today,
        },
        "lifetime": {
            "rows": int(summary.get("cost_rows") or 0),
            "input_tokens": int(summary.get("input_tokens") or 0),
            "output_tokens": int(summary.get("output_tokens") or 0),
            "total_cost_usd": round(float(summary.get("total_cost_usd") or 0.0), 4),
        },
        "latest": {
            "lane": str(latest.get("lane") or ""),
            "provider": str(latest.get("provider") or ""),
            "model": str(latest.get("model") or ""),
            "input_tokens": int(latest.get("input_tokens") or 0),
            "output_tokens": int(latest.get("output_tokens") or 0),
            "cost_usd": float(latest.get("cost_usd") or 0.0),
            "created_at": str(latest.get("created_at") or ""),
        },
        "pressure": pressure,
    }


def _derive_pressure(today_total_tokens: int, today_cost_usd: float) -> str:
    """Bounded heuristic for runtime resource pressure.

    Free local models always read as "low" regardless of token count.
    Paid lanes escalate as cost rises. Conservative thresholds — this
    is meant as a hint, not a hard limit.
    """
    if today_cost_usd <= 0.0:
        if today_total_tokens >= 5_000_000:
            return "high-volume-free-lane"
        if today_total_tokens >= 1_000_000:
            return "medium-volume-free-lane"
        return "low"
    if today_cost_usd >= 5.0:
        return "high"
    if today_cost_usd >= 1.0:
        return "medium"
    return "low"


def build_runtime_resource_prompt_section() -> str | None:
    surface = build_runtime_resource_signal_surface()
    if not surface.get("active"):
        return None
    today = surface.get("today") or {}
    latest = surface.get("latest") or {}
    pressure = str(surface.get("pressure") or "low")
    lines = [
        "Runtime resource awareness (bounded telemetry, internal-only):",
        (
            f"- today: runs={today.get('runs') or 0}"
            f" | tokens={today.get('total_tokens') or 0}"
            f" (in={today.get('input_tokens') or 0}/out={today.get('output_tokens') or 0})"
            f" | cost=${today.get('cost_usd') or 0.0:.4f}"
            f" | pressure={pressure}"
        ),
    ]
    if latest.get("model"):
        lines.append(
            f"- latest: lane={latest.get('lane') or 'unknown'}"
            f" | provider={latest.get('provider') or 'unknown'}"
            f" | model={latest.get('model') or 'unknown'}"
        )
    return "\n".join(lines)
