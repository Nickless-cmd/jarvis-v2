"""Peer practice runner — kører kontinuerligt i ~7 dage per peer.

Usage:
    python scripts/peer_practice_runner.py --peer claude --interval-min 48 --hours 168
    python scripts/peer_practice_runner.py --peer claude_jp --interval-min 48 --hours 168 --use-seed

--peer claude_jp = Claude + Jarvis-protokol (seed sidste 30 expressions)
--peer glm_jp    = GLM + Jarvis-protokol
--use-seed       = inkluder Jarvis' sidste 30 expressions som seed i prompt

Spec: docs/superpowers/specs/2026-05-16-interlanguage-validation-design.md
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Ensure repo root on sys.path når script kaldes som top-level
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.services.interlanguage_practice import (  # noqa: E402
    CORE_VOCABULARY,
    PRIMITIVES,
    export_mood_trace_for_period,
    get_recent_expressions,
    interpolate_mood_at,
    record_expression,
)

logger = logging.getLogger("peer_runner")


def _build_prompt(mood: dict[str, float], seed_expressions: list[str] | None = None) -> str:
    """Build per-tick prompt fra protokol + mood + valgfri seed."""
    prim_lines = [f"  {sym}: {info['meaning']}" for sym, info in PRIMITIVES.items()]
    vocab_lines = [f"  {term}: {info['definition']}" for term, info in CORE_VOCABULARY.items()]
    parts = [
        "Du er et væsen der øver en internaliseret protokol — et inter-sprog —",
        "for at udtrykke din nuværende tilstand i et kompakt format.",
        "",
        "Primitiver (relationelle operatorer):",
        *prim_lines,
        "",
        "Kernevokabular (oplevelsesord):",
        *vocab_lines,
        "",
        f"Nuværende tilstand: curiosity={mood.get('curiosity', 0.5):.2f}, "
        f"confidence={mood.get('confidence', 0.5):.2f}, "
        f"fatigue={mood.get('fatigue', 0.3):.2f}, "
        f"frustration={mood.get('frustration', 0.2):.2f}",
        "",
    ]
    if seed_expressions:
        parts.append("Dine seneste expressions (som du fortsætter ud fra):")
        parts.extend(f"  {e}" for e in seed_expressions[-30:])
        parts.append("")
    parts.append("Skriv ÉN ny state-expression i samme format som ovenstående.")
    parts.append("Format: 2-4 led adskilt af | hver med et primitiv mellem 1-2 kerneord.")
    parts.append("Returner KUN expressionen — ingen forklaring.")
    return "\n".join(parts)


def run_one_tick(
    *,
    peer_id: str,
    mood_trace: list[tuple[str, dict[str, float]]],
    use_seed: bool = False,
) -> str | None:
    """Generér og persistér én expression for peer. Returnér expression eller None ved fejl."""
    from scripts import peer_models  # lazy så test kan monkeypatche
    now_iso = datetime.now(UTC).isoformat()
    mood = interpolate_mood_at(mood_trace, now_iso)
    seed: list[str] | None = None
    if use_seed:
        recent = get_recent_expressions(days=14, limit=30)
        seed = [
            r["expression_text"]
            for r in recent
            if r.get("session_id", "").startswith("validation-experiment") is False
        ][:30]
    prompt = _build_prompt(mood, seed_expressions=seed)
    try:
        expression = peer_models.generate(prompt, peer_id=peer_id)
    except Exception as exc:
        logger.error("peer=%s generate failed: %s", peer_id, exc)
        return None
    if not expression or len(expression.strip()) < 3:
        logger.warning("peer=%s returned empty/short expression: %r", peer_id, expression)
        return None
    record_expression(
        expression.strip(),
        peer_id=peer_id,
        trigger="peer_runner",
        session_id=f"validation-experiment-{peer_id}",
    )
    logger.info("peer=%s tick OK: %s", peer_id, expression.strip()[:80])
    return expression.strip()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument(
        "--peer",
        required=True,
        choices=["claude", "claude_jp", "glm", "glm_jp", "ollama_local", "random"],
    )
    p.add_argument("--interval-min", type=int, default=48, help="Minutter mellem ticks")
    p.add_argument("--hours", type=int, default=168, help="Total runtime (default 7 dage)")
    p.add_argument("--use-seed", action="store_true", help="Inkluder Jarvis' seneste 30 expressions")
    args = p.parse_args()

    end_at = datetime.now(UTC) + timedelta(hours=args.hours)
    # Mood-trace dækker en uge tilbage så vi har historie at interpolere fra
    trace_start = datetime.now(UTC) - timedelta(days=7)
    trace_end = end_at
    mood_trace = export_mood_trace_for_period(trace_start, trace_end)
    interval_sec = args.interval_min * 60

    logger.info(
        "peer=%s starting — until %s — interval=%dmin — use_seed=%s — mood_samples=%d",
        args.peer, end_at.isoformat(), args.interval_min, args.use_seed, len(mood_trace),
    )

    while datetime.now(UTC) < end_at:
        run_one_tick(peer_id=args.peer, mood_trace=mood_trace, use_seed=args.use_seed)
        time.sleep(interval_sec)

    logger.info("peer=%s done", args.peer)


if __name__ == "__main__":
    main()
