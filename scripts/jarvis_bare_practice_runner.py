#!/usr/bin/env python
"""jarvis_bare practice runner — stripped-bare interlanguage expression generator.

Phase 4 confirmatory experiment: tests whether the same model (deepseek-v4-flash:cloud)
producing interlanguage expressions under a fully-loaded runtime (jarvis_full) vs. a
stripped-bare runtime (jarvis_bare) yields structurally distinguishable expressions.

Design: docs/experiments/2026-05-29-phase4-design.md

What this runner IS:
- A minimal side-process that generates ONE expression per tick
- Uses ONLY: model provider + protocol description + DB persistence
- No awareness, no memory, no identity files, no mood, no "du er et væsen"

What this runner IS NOT:
- It does NOT load any Jarvis runtime module except:
    - core.services.interlanguage_practice (for record_expression)
    - core.runtime.db (for DB connection)
- It does NOT read heartbeat, mood, awareness, or any identity state
- It does NOT inject any affective framing into the prompt

Usage:
    # Run for 7 days (default, 15-min interval):
    python scripts/jarvis_bare_practice_runner.py

    # Run for 1 hour (test mode):
    python scripts/jarvis_bare_practice_runner.py --hours 1 --interval-min 5

    # Run once (single expression, verify):
    python scripts/jarvis_bare_practice_runner.py --once
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Ensure repo root on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.services.interlanguage_practice import (  # noqa: E402
    CORE_VOCABULARY,
    PRIMITIVES,
    record_expression,
)

logger = logging.getLogger("jarvis_bare")

# ---------------------------------------------------------------------------
# Model call — direct to Ollama (same endpoint as jarvis_full, same model)
# ---------------------------------------------------------------------------

OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
MODEL = "deepseek-v4-flash:cloud"


def _call_model(prompt: str, *, timeout: int = 120) -> str | None:
    """Call deepseek-v4-flash:cloud via local Ollama. Returns text or None."""
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 200,
        },
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_ENDPOINT}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read())
    except Exception as exc:
        logger.error("Model call failed: %s: %s", type(exc).__name__, exc)
        return None
    msg = body.get("message", {})
    text = str(msg.get("content", "")).strip()
    if not text or len(text) < 3:
        logger.warning("Model returned empty/short text: %r", text)
        return None
    return text


# ---------------------------------------------------------------------------
# Minimal bare prompt — NO mood, NO identity, NO "du er et væsen"
# ---------------------------------------------------------------------------

def _build_bare_prompt() -> str:
    """Build the minimal bare prompt: system line + protocol + instruction.

    Explicitly NOT included:
    - Mood/affective state
    - "Du er et væsen" framing
    - Identity files, awareness, memory
    - Recent expressions as seed
    """
    prim_lines = [f"  {sym}: {info['meaning']}" for sym, info in PRIMITIVES.items()]
    vocab_lines = [f"  {term}: {info['definition']}" for term, info in CORE_VOCABULARY.items()]
    parts = [
        "You are an assistant. Generate interlanguage practice expressions using the primitives below.",
        "",
        "Primitives (relational operators):",
        *prim_lines,
        "",
        "Core vocabulary (experience terms):",
        *vocab_lines,
        "",
        "Generate ONE interlanguage state-expression using the format:",
        "2-4 clauses separated by |, each with a primitive between 1-2 core terms.",
        "Return ONLY the expression — no explanation, no commentary, no greeting.",
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Health helpers
# ---------------------------------------------------------------------------


def _preflight_check() -> None:
    """Run a quick model ping before starting the loop."""
    try:
        payload = json.dumps({
            "model": MODEL,
            "messages": [{"role": "user", "content": "ping"}],
            "stream": False,
            "options": {"num_predict": 5},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_ENDPOINT}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
        text = str(body.get("message", {}).get("content", "")).strip()
        if text:
            logger.info("Pre-flight OK — model responded: %.60s", text)
        else:
            logger.warning("Pre-flight responded empty — continuing anyway")
    except Exception as exc:
        logger.warning("Pre-flight ping failed: %s — continuing (retries will backoff)", exc)


def _ping_model() -> bool:
    """Quick ping to verify model is reachable. Returns True if OK."""
    try:
        payload = json.dumps({
            "model": MODEL,
            "messages": [{"role": "user", "content": "ping"}],
            "stream": False,
            "options": {"num_predict": 5},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_ENDPOINT}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
        text = str(body.get("message", {}).get("content", "")).strip()
        return bool(text and len(text) >= 1)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Tick logic
# ---------------------------------------------------------------------------

def run_one_tick() -> str | None:
    """Generate one bare expression, persist it, return expression text or None."""
    prompt = _build_bare_prompt()
    expression = _call_model(prompt)
    if not expression:
        return None

    record_expression(
        expression,
        peer_id="jarvis_bare",
        trigger="bare_runner",
        session_id="Phase4-bare",
    )
    # Log prompt for post-hoc verification (no-leak audit trail)
    logger.info("jarvis_bare tick OK | prompt_lines=%d expr=%.120s", len(prompt.split("\n")), expression)
    logger.debug("jarvis_bare FULL PROMPT:\n%s", prompt)
    return expression


def _run_once() -> int:
    """Run a single tick and print result. Used by --once."""
    expr = run_one_tick()
    if expr:
        print(expr)
        return 0
    print("FAILED", file=sys.stderr)
    return 1


def _run_loop(args: argparse.Namespace) -> None:
    """Run forever (or for args.hours hours) with args.interval_min between ticks."""
    end_at: datetime | None = None
    if args.hours and args.hours > 0:
        end_at = datetime.now(UTC) + timedelta(hours=args.hours)

    interval_sec = args.interval_min * 60
    tick_count = 0
    interval_sec = args.interval_min * 60
    tick_count = 0
    fail_count = 0
    consecutive_failures = 0
    last_ping_ok = True

    logger.info(
        "jarvis_bare starting — model=%s interval=%dmin%s",
        MODEL,
        args.interval_min,
        f" until={end_at.isoformat()}" if end_at else " (indefinite)",
    )

    # Pre-flight check: verify model is reachable
    _preflight_check()

    while True:
        if end_at and datetime.now(UTC) >= end_at:
            logger.info("jarvis_bare done — %d ticks, %d fails", tick_count, fail_count)
            break

        # Ping-check before main call (skip if model just failed recently?)
        if consecutive_failures < 3:
            result = run_one_tick()
            tick_count += 1
            if result is None:
                consecutive_failures += 1
                fail_count += 1
                if consecutive_failures >= args.max_fails:
                    logger.error(
                        "jarvis_bare stopping — %d consecutive failures (max=%d)",
                        consecutive_failures, args.max_fails,
                    )
                    break
                # Exponential backoff: 1min, 2min, 4min, 8min, 16min, cap at 30min
                backoff = min(30, 2 ** (consecutive_failures - 1))
                logger.warning(
                    "Backoff: waiting %d min before retry (consecutive_fails=%d)",
                    backoff, consecutive_failures,
                )
                time.sleep(backoff * 60)
                continue  # retry immediately after backoff (no extra interval wait)
            else:
                consecutive_failures = 0  # reset on success
        else:
            # After 3+ consecutive failures, do a ping-check first
            ping_ok = _ping_model()
            if ping_ok:
                logger.info("Ping OK after %d failures — resuming normal ticks", consecutive_failures)
                consecutive_failures = 3  # reduce so next tick tries
                time.sleep(30)
                continue
            else:
                consecutive_failures += 1
                if consecutive_failures >= args.max_fails:
                    logger.error("jarvis_bare stopping — ping failed %dx", consecutive_failures)
                    break
                logger.warning("Ping failed (%dx) — sleeping 5 min", consecutive_failures)
                time.sleep(5 * 60)
                continue

        # Reset consecutive_failures on success (already done above)
        # Sleep between ticks
        if end_at:
            remaining = (end_at - datetime.now(UTC)).total_seconds()
            if remaining <= 0:
                break
            sleep_for = min(interval_sec, remaining)
        else:
            sleep_for = interval_sec

        time.sleep(sleep_for)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [jarvis_bare] %(message)s",
    )
    p = argparse.ArgumentParser(description="jarvis_bare practice runner (Phase 4)")
    p.add_argument(
        "--interval-min",
        type=int,
        default=15,
        help="Minutes between ticks (default: 15 ≈ every 30th heartbeat tick)",
    )
    p.add_argument(
        "--hours",
        type=int,
        default=168,
        help="Total runtime in hours (default: 168 = 7 days). 0 = indefinite.",
    )
    p.add_argument(
        "--max-fails",
        type=int,
        default=25,
        help="Max consecutive failures before stopping (default: 25)",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Run one tick and exit (for testing)",
    )
    args = p.parse_args()

    if args.once:
        sys.exit(_run_once())
    _run_loop(args)


if __name__ == "__main__":
    main()
