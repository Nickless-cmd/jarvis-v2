#!/usr/bin/env python3
"""Reproducérbart latency/concurrency-benchmark for Ollama-lanen.

Formål: måle baseline FØR vi udnytter 3-samtidig-aktivet, og re-køre efter hver
etappe (parallelle interne lanes, council/swarm, synlig-lane-race) så vi kan se
om hver ændring rent faktisk flytter tallene — og revertere hvis ikke.

Kører raw mod Ollama (http://127.0.0.1:11434) = infra-loftet, uden Jarvis-
pipeline-støj. Gratis (Bjørns abon.). Ingen deepseek-API-kald.

Brug:
    python scripts/bench_ollama_concurrency.py                 # default glm-5.1:cloud
    python scripts/bench_ollama_concurrency.py --model deepseek-v4-flash:cloud
    python scripts/bench_ollama_concurrency.py --label "etappe-1-efter"

Output er en JSON-blok der kan gemmes pr. etappe og diffes.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

URL = "http://127.0.0.1:11434/api/chat"
CHAT_PROMPT = "Skriv 3 sætninger om havet."
LOOP_PROMPT = "Svar kort: hvad er det næste logiske skridt? (ét ord)"


def _call(model: str, stream: bool, prompt: str) -> tuple[float | None, float]:
    """Returnér (ttft, total) i sekunder. ttft=None for non-stream."""
    body = json.dumps(
        {"model": model, "stream": stream,
         "messages": [{"role": "user", "content": prompt}]}
    ).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    ttft: float | None = None
    r = urllib.request.urlopen(req)
    if stream:
        for line in r:
            if line.strip():
                if ttft is None:
                    ttft = time.time() - t0
                if json.loads(line).get("done"):
                    break
        return ttft, time.time() - t0
    r.read()
    return None, time.time() - t0


def _median(xs: list[float]) -> float:
    return round(statistics.median(xs), 3)


def bench_chat(model: str, n: int = 5) -> dict:
    """Chat-responsivitet: TTFT + fuld svartid (streaming), median af n."""
    ttfts, totals = [], []
    for _ in range(n):
        ttft, total = _call(model, True, CHAT_PROMPT)
        ttfts.append(ttft or 0.0)
        totals.append(total)
    return {"runs": n, "ttft_median_s": _median(ttfts), "total_median_s": _median(totals)}


def bench_sequential_loop(model: str, rounds: int = 3, n: int = 3) -> dict:
    """Agentisk kompounding: `rounds` sekventielle kald (hver venter på forrige)."""
    walls = []
    for _ in range(n):
        t0 = time.time()
        for _ in range(rounds):
            _call(model, False, LOOP_PROMPT)
        walls.append(time.time() - t0)
    return {"rounds": rounds, "runs": n, "wall_median_s": _median(walls)}


def bench_concurrency(model: str, ks: tuple[int, ...] = (1, 2, 3, 4)) -> dict:
    """Concurrency-skalering: K parallelle kald, wall-clock pr. K.

    Hvis 3-samtidig holder, er wall(3) ≈ wall(1). Når wall(K) begynder at stige
    lineært, er loftet nået."""
    out = {}
    for k in ks:
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=k) as ex:
            list(ex.map(lambda _: _call(model, False, LOOP_PROMPT), range(k)))
        out[f"k{k}_wall_s"] = round(time.time() - t0, 3)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="glm-5.1:cloud")
    ap.add_argument("--label", default="baseline")
    args = ap.parse_args()

    result = {
        "label": args.label,
        "model": args.model,
        "chat": bench_chat(args.model),
        "sequential_loop": bench_sequential_loop(args.model),
        "concurrency": bench_concurrency(args.model),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
