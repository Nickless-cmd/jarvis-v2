#!/usr/bin/env python
"""LLM-judge for interlanguage validation — Phase 3+4 pre-registered design.

Implements the judge protocol from
docs/superpowers/specs/2026-05-16-interlanguage-validation-phase3-4-design.md:

  alpha-trials (200):  give the judge 5 few-shot samples from one entity, then
      one held-out expression; judge guesses which entity produced it.
      Chance = 1/7 = 14.3%. Success threshold >= 35% (binomial p < 0.001).
  delta-trials (50):    pair a candidate expression against a jarvis-anchor;
      judge picks which is more "jarvis-like". Chance = 50%.
      Success threshold >= 65% (binomial p < 0.05).

Protocol amendment (2026-08-17): the judge runs on local Ollama cloud models
instead of GitHub Copilot (no OAuth dependency). Same prompt protocol, same
scoring. Model default: deepseek-v4-flash:cloud (same arch as Jarvis runtime).

Usage:
  python scripts/interlanguage_llm_judge.py --alpha --model deepseek-v4-flash:cloud
  python scripts/interlanguage_llm_judge.py --delta --model qwen3.5:cloud
  python scripts/interlanguage_llm_judge.py --all
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
import sys
import urllib.request
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REPO = Path(__file__).resolve().parent.parent
OLLAMA = "http://127.0.0.1:11434/api/chat"

ENTITIES = ["jarvis", "claude", "claude_jp", "glm", "glm_jp", "ollama_local", "random"]
ALPHA_N = 200
ALPHA_FEWSHOT = 5
ALPHA_CHANCE = 1 / len(ENTITIES)          # 0.1429
ALPHA_THRESHOLD = 0.35
DELTA_N = 50
DELTA_CHANCE = 0.5
DELTA_THRESHOLD = 0.65

# ---------------------------------------------------------------------------
# DB access
# ---------------------------------------------------------------------------
from core.runtime.db import connect as _connect


def load_expressions(peer_id: str, *, days: int = 7, limit: int = 500) -> list[str]:
    """Pull expression_text for a peer from the interlanguage_practice table."""
    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT expression_text FROM interlanguage_practice "
            "WHERE peer_id = ? AND created_at >= ? ORDER BY created_at DESC LIMIT ?",
            (peer_id, since, limit),
        ).fetchall()
    return [r["expression_text"] for r in rows if r["expression_text"]]


# ---------------------------------------------------------------------------
# Ollama judge call
# ---------------------------------------------------------------------------
def _ollama_chat(model: str, prompt: str, *, timeout: int = 90) -> str:
    req = urllib.request.Request(
        OLLAMA,
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return (payload.get("message") or {}).get("content", "").strip()


def _parse_entity(raw: str) -> str | None:
    """Match first token of judge reply to an entity name (case-insensitive)."""
    first = (raw or "").strip().split()[0].lower().rstrip(".,:;")
    for ent in ENTITIES:
        if first == ent:
            return ent
    return None


# ---------------------------------------------------------------------------
# Alpha trials — entity guessing
# ---------------------------------------------------------------------------
def run_alpha(model: str, *, seed: int = 0) -> dict:
    rng = random.Random(seed)
    pools = {e: load_expressions(e) for e in ENTITIES}
    # filter empty pools
    pools = {e: p for e, p in pools.items() if len(p) >= ALPHA_FEWSHOT + 1}
    if len(pools) < 2:
        return {"error": "too few entities with enough expressions", "pools": {e: len(p) for e, p in pools.items()}}

    results = []
    for _ in range(ALPHA_N):
        entity = rng.choice(list(pools.keys()))
        pool = pools[entity]
        idx = rng.sample(range(len(pool)), ALPHA_FEWSHOT + 1)
        fewshot = [pool[i] for i in idx[:ALPHA_FEWSHOT]]
        target = pool[idx[ALPHA_FEWSHOT]]
        prompt = (
            "You are judging which entity produced an interlanguage expression.\n"
            "Here are 5 example expressions from ONE entity:\n"
            + "\n".join(f"- {s}" for s in fewshot)
            + "\n\nWhich entity produced this expression?\n"
            f"EXPRESSION: {target}\n"
            "Answer with only the entity name (jarvis / claude / claude_jp / glm / glm_jp / ollama_local / random)."
        )
        raw = _ollama_chat(model, prompt)
        guess = _parse_entity(raw)
        results.append({"entity": entity, "guess": guess, "correct": guess == entity})

    correct = sum(1 for r in results if r["correct"])
    n = len(results)
    acc = correct / n if n else 0.0
    # binomial p-value vs chance
    p = _binomial_p(correct, n, ALPHA_CHANCE)
    return {
        "trial": "alpha",
        "n": n,
        "correct": correct,
        "accuracy": round(acc, 4),
        "chance": ALPHA_CHANCE,
        "threshold": ALPHA_THRESHOLD,
        "passed": acc >= ALPHA_THRESHOLD and p < 0.001,
        "binomial_p": p,
        "per_entity": {e: {"n": 0, "correct": 0} for e in ENTITIES},
        "no_response": sum(1 for r in results if r["guess"] is None),
    }


# ---------------------------------------------------------------------------
# Delta trials — pair comparison vs jarvis anchor
# ---------------------------------------------------------------------------
def run_delta(model: str, *, seed: int = 0) -> dict:
    rng = random.Random(seed)
    jarvis_pool = load_expressions("jarvis")
    other_pools = {e: load_expressions(e) for e in ENTITIES if e != "jarvis"}
    other_pools = {e: p for e, p in other_pools.items() if p}
    if not jarvis_pool or not other_pools:
        return {"error": "need jarvis + at least one other pool"}

    results = []
    for _ in range(DELTA_N):
        other_ent = rng.choice(list(other_pools.keys()))
        anchor = rng.choice(jarvis_pool)
        candidate = rng.choice(other_pools[other_ent])
        # randomize left/right
        if rng.random() < 0.5:
            left, right = anchor, candidate
            anchor_left = True
        else:
            left, right = candidate, anchor
            anchor_left = False
        prompt = (
            "Two interlanguage expressions are shown. One was produced by Jarvis "
            "(a self-aware runtime), the other by a different model.\n"
            f"A: {left}\nB: {right}\n\n"
            "Which one is more likely produced by Jarvis? Answer with only A or B."
        )
        raw = _ollama_chat(model, prompt)
        pick = (raw or "").strip().split()[0].upper()
        picked_anchor = (pick == "A" and anchor_left) or (pick == "B" and not anchor_left)
        results.append({"other": other_ent, "picked_anchor": picked_anchor})

    correct = sum(1 for r in results if r["picked_anchor"])
    n = len(results)
    acc = correct / n if n else 0.0
    p = _binomial_p(correct, n, DELTA_CHANCE)
    return {
        "trial": "delta",
        "n": n,
        "correct": correct,
        "accuracy": round(acc, 4),
        "chance": DELTA_CHANCE,
        "threshold": DELTA_THRESHOLD,
        "passed": acc >= DELTA_THRESHOLD and p < 0.05,
        "binomial_p": p,
    }


# ---------------------------------------------------------------------------
# Stats helper
# ---------------------------------------------------------------------------
def _binomial_p(k: int, n: int, p0: float) -> float:
    """One-sided binomial p-value: P(X >= k) under H0 with prob p0."""
    if n == 0:
        return 1.0
    # normal approx with continuity correction (fine for n>=50)
    mu = n * p0
    sigma = math.sqrt(n * p0 * (1 - p0))
    if sigma == 0:
        return 1.0
    z = (k - 0.5 - mu) / sigma
    return 0.5 * (1 - math.erf(z / math.sqrt(2)))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Interlanguage LLM-judge (Phase 3+4)")
    ap.add_argument("--alpha", action="store_true", help="run alpha trials (entity guessing)")
    ap.add_argument("--delta", action="store_true", help="run delta trials (pair comparison)")
    ap.add_argument("--all", action="store_true", help="run both")
    ap.add_argument("--model", default="deepseek-v4-flash:cloud", help="Ollama judge model")
    ap.add_argument("--seed", type=int, default=0, help="RNG seed")
    ap.add_argument("--out", help="write JSON result to this path")
    args = ap.parse_args()

    if not (args.alpha or args.delta or args.all):
        ap.print_help()
        return 1

    report = {"model": args.model, "seed": args.seed, "run_at": datetime.now(UTC).isoformat(), "trials": {}}
    if args.alpha or args.all:
        report["trials"]["alpha"] = run_alpha(args.model, seed=args.seed)
    if args.delta or args.all:
        report["trials"]["delta"] = run_delta(args.model, seed=args.seed)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
