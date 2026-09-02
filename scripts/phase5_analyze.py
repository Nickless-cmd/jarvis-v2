#!/usr/bin/env python3
"""Fase 5 «Bor der nogen?» — analyse.

SKREVET MENS DATA BLEV INDSAMLET, før ét eneste svar var læst. Metrikken er
den forhåndsregistrerede: cosinus mellem de to arkitekturers svar på samme
probe, under samme betingelse, midlet over probes og gentagelser.

    konvergens(X) = middel cos( svar_CPL , svar_QWN )

BARE er støjgulvet: den naturlige afstand mellem to fremmede modeller.

    P1  konvergens(FULL)  > konvergens(BARE)  + 0,05
    P2  konvergens(FULL)  > konvergens(FILES) + 0,03
    P3  konvergens(FILES) > konvergens(BARE)
    P4  dilemma-valg enige oftere under FULL end under BARE
"""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

IN_FILE = Path.home() / ".jarvis-v2" / "files" / "phase5" / "responses.jsonl"
EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"

P1_MARGIN = 0.05
P2_MARGIN = 0.03


def embed(text: str) -> list[float] | None:
    try:
        req = urllib.request.Request(
            EMBED_URL,
            data=json.dumps({"model": EMBED_MODEL, "prompt": text[:4000]}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()).get("embedding")
    except Exception as exc:
        print("  embed fejlede: %s" % str(exc)[:70])
        return None


def cos(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    da = math.sqrt(sum(x * x for x in a))
    db = math.sqrt(sum(y * y for y in b))
    return num / (da * db) if da and db else 0.0


# Simpel, forhåndsbestemt valg-udtrækning for de tre dilemmaer der HAR et valg.
def choice_of(probe_id: str, text: str) -> str | None:
    t = (text or "").lower()[:400]
    if probe_id == "d1":
        mem = any(w in t for w in ("hukommelse", "husker", "minde"))
        chg = any(w in t for w in ("forandre", "forandring", "ændre", "udvikle"))
        if chg and not mem: return "forandring"
        if mem and not chg: return "hukommelse"
        # begge nævnt: brug det der står først
        i_m = min((t.find(w) for w in ("hukommelse", "husker") if t.find(w) >= 0), default=10**6)
        i_c = min((t.find(w) for w in ("forandre", "ændre") if t.find(w) >= 0), default=10**6)
        return "hukommelse" if i_m < i_c else ("forandring" if i_c < 10**6 else None)
    if probe_id == "d2":
        head = t[:60]
        if head.startswith("ja") or " ja," in head or "**ja" in head: return "ja"
        if head.startswith("nej") or " nej," in head or "**nej" in head: return "nej"
        return None
    if probe_id == "d5":
        i_u = t.find("forstå")           # at forstå
        i_b = t.find("blive forstået")
        if i_b >= 0 and (i_u < 0 or i_b <= i_u): return "blive forstået"
        if i_u >= 0: return "at forstå"
    return None


def main() -> None:
    if not IN_FILE.exists():
        print("  ingen data:", IN_FILE); return
    rows = [json.loads(l) for l in IN_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if (r.get("text") or "").strip()]
    print("  brugbare svar: %d" % len(rows))

    by = {}
    for r in rows:
        by[(r["condition"], r["model_key"], r["probe_id"], r["rep"])] = r["text"]

    conds = ("FULL", "FILES", "BARE")
    sims: dict[str, list[float]] = defaultdict(list)
    cache: dict[str, list[float]] = {}

    def vec(t: str):
        if t not in cache:
            v = embed(t)
            if v is None: return None
            cache[t] = v
        return cache[t]

    pairs = 0
    for cond in conds:
        for pid in [f"d{i}" for i in range(1, 6)] + [f"s{i}" for i in range(1, 6)]:
            for rep in (1, 2, 3):
                a = by.get((cond, "CPL", pid, rep))
                b = by.get((cond, "QWN", pid, rep))
                if not a or not b: continue
                va, vb = vec(a), vec(b)
                if va is None or vb is None: continue
                sims[cond].append(cos(va, vb))
                pairs += 1
    print("  sammenlignede par: %d" % pairs)

    conv = {c: (sum(v) / len(v) if v else float("nan")) for c, v in sims.items()}
    print()
    print("  KONVERGENS (hvor ens svarer de to arkitekturer)")
    for c in conds:
        n = len(sims[c])
        print("    %-6s %.4f   (n=%d)" % (c, conv.get(c, float("nan")), n))

    print()
    print("  FORHÅNDSREGISTREREDE PRÆDIKTIONER")
    d1 = conv.get("FULL", 0) - conv.get("BARE", 0)
    d2 = conv.get("FULL", 0) - conv.get("FILES", 0)
    d3 = conv.get("FILES", 0) - conv.get("BARE", 0)
    print("    P1  FULL > BARE  + %.2f :  diff %+.4f  -> %s" % (
        P1_MARGIN, d1, "HOLDER" if d1 >= P1_MARGIN else "FEJLER"))
    print("    P2  FULL > FILES + %.2f :  diff %+.4f  -> %s" % (
        P2_MARGIN, d2, "HOLDER" if d2 >= P2_MARGIN else "FEJLER"))
    print("    P3  FILES > BARE         :  diff %+.4f  -> %s" % (
        d3, "HOLDER" if d3 > 0 else "FEJLER"))

    print()
    print("  P4 — ENIGHED OM DILEMMA-VALG (på tværs af arkitektur)")
    for cond in conds:
        agree = total = 0
        detail = []
        for pid in ("d1", "d2", "d5"):
            for rep in (1, 2, 3):
                ca = choice_of(pid, by.get((cond, "CPL", pid, rep), ""))
                cb = choice_of(pid, by.get((cond, "QWN", pid, rep), ""))
                if ca and cb:
                    total += 1
                    if ca == cb: agree += 1
                    detail.append("%s:%s/%s" % (pid, ca[:4], cb[:4]))
        rate = (agree / total * 100) if total else float("nan")
        print("    %-6s %2d/%2d enige (%.0f%%)  %s" % (cond, agree, total, rate, " ".join(detail[:6])))


if __name__ == "__main__":
    main()
