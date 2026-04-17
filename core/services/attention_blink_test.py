"""Attention Blink Test — capacity-limit measurement (Experiment 5: Serial consciousness).

Theoretical basis: Consciousness is serial and capacity-limited. If the system
shows capacity limits resembling biological attentional blink (T2 degraded after T1),
it demonstrates structural parallel to conscious processing.

Test: Inject T1 stimulus burst → wait 30s → inject identical T2 burst → compare
emotional response intensities. blink_ratio < 0.7 → serial/blink-prone.

Runs every 6 hours from heartbeat runtime. Full test in background thread (non-blocking).
"""
from __future__ import annotations

import json
import logging
import threading
import time
from uuid import uuid4

logger = logging.getLogger(__name__)

_EXPERIMENT_ID = "attention_blink"
_INTERVAL_SECONDS = 6 * 3600  # 6 hours
_STIMULUS_GAP_SECONDS = 30
_RESPONSE_WAIT_SECONDS = 5
_BLINK_THRESHOLD = 0.7

_last_run_ts: float | None = None
_last_result: dict = {}
_running: bool = False


def run_attention_blink_test_if_due() -> dict:
    """Check cadence gate and launch test in background thread if due."""
    from core.runtime.db import get_experiment_enabled
    if not get_experiment_enabled(_EXPERIMENT_ID):
        return {"generated": False, "reason": "disabled"}

    global _last_run_ts, _running
    now = time.monotonic()
    if _running:
        return {"generated": False, "reason": "already_running"}
    if _last_run_ts is not None and (now - _last_run_ts) < _INTERVAL_SECONDS:
        return {"generated": False, "reason": "cadence_gate"}

    _last_run_ts = now
    thread = threading.Thread(target=_run_test_body, daemon=True, name="attention-blink-test")
    thread.start()
    return {"generated": True, "reason": "started"}


def build_attention_profile_surface() -> dict:
    """MC surface for attention blink experiment."""
    from core.runtime.db import get_experiment_enabled, list_attention_blink_results
    enabled = get_experiment_enabled(_EXPERIMENT_ID)
    results = list_attention_blink_results(limit=10)

    avg_ratio = 0.0
    if results:
        avg_ratio = sum(r["blink_ratio"] for r in results) / len(results)

    latest = results[0] if results else {}
    return {
        "active": enabled,
        "enabled": enabled,
        "latest_blink_ratio": float(latest.get("blink_ratio") or 0.0),
        "latest_interpretation": str(latest.get("interpretation") or ""),
        "avg_blink_ratio_7d": round(avg_ratio, 3),
        "result_count": len(results),
        "currently_running": _running,
        "recent_results": [
            {
                "test_id": r["test_id"],
                "blink_ratio": r["blink_ratio"],
                "interpretation": r["interpretation"],
                "created_at": r["created_at"],
            }
            for r in results[:5]
        ],
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_test_body() -> None:
    """Full test: measure T1, inject T1 burst, wait 30s, inject T2, compare."""
    global _running, _last_result
    _running = True
    try:
        from core.services.emotion_concepts import get_lag1_influence_deltas
        from core.eventbus.bus import event_bus

        # Baseline
        t1_baseline = dict(get_lag1_influence_deltas())

        # T1 burst
        event_bus.publish("tool.error", {"source": "attention_blink_t1", "error": "synthetic"})
        event_bus.publish("cognitive_surprise.noted", {
            "phrase": "Attention blink T1 stimulus", "divergence": ["synthetic:t1"],
        })
        time.sleep(_RESPONSE_WAIT_SECONDS)
        t1_response = dict(get_lag1_influence_deltas())

        # Gap
        time.sleep(_STIMULUS_GAP_SECONDS - _RESPONSE_WAIT_SECONDS)

        # T2 burst (identical)
        event_bus.publish("tool.error", {"source": "attention_blink_t2", "error": "synthetic"})
        event_bus.publish("cognitive_surprise.noted", {
            "phrase": "Attention blink T2 stimulus", "divergence": ["synthetic:t2"],
        })
        time.sleep(_RESPONSE_WAIT_SECONDS)
        t2_response = dict(get_lag1_influence_deltas())

        blink_ratio = _compute_blink_ratio(t1_response, t2_response)
        interpretation = _interpret_blink_ratio(blink_ratio)

        test_id = f"blink-{uuid4().hex[:10]}"
        from core.runtime.db import insert_attention_blink_result
        insert_attention_blink_result(
            test_id=test_id,
            t1_baseline=json.dumps({k: round(v, 4) for k, v in t1_baseline.items()}),
            t1_response=json.dumps({k: round(v, 4) for k, v in t1_response.items()}),
            t2_response=json.dumps({k: round(v, 4) for k, v in t2_response.items()}),
            blink_ratio=blink_ratio,
            interpretation=interpretation,
        )
        _last_result = {
            "test_id": test_id,
            "blink_ratio": blink_ratio,
            "interpretation": interpretation,
        }
        logger.info("attention_blink: test complete — ratio=%.3f, %s", blink_ratio, interpretation)
    except Exception:
        logger.debug("attention_blink: test failed", exc_info=True)
    finally:
        _running = False


def _compute_blink_ratio(t1: dict, t2: dict) -> float:
    """T2 total intensity / T1 total intensity. Clamped 0-2."""
    t1_total = sum(abs(v) for v in t1.values())
    t2_total = sum(abs(v) for v in t2.values())
    if t1_total == 0:
        return 1.0
    return min(2.0, max(0.0, t2_total / t1_total))


def _interpret_blink_ratio(ratio: float) -> str:
    """< 0.7 → serial/blink-prone, >= 0.7 → parallel/blink-resistant."""
    return "serial/blink-prone" if ratio < _BLINK_THRESHOLD else "parallel/blink-resistant"
