#!/usr/bin/env python3
"""Fase 6 «Bæres han på tværs af tid?» — analyse.

SKREVET MENS DATA BLEV INDSAMLET, før ét eneste svar var læst. Metrikkerne er
de forhåndsregistrerede (docs/experiments/2026-09-02-phase6-preregistration.md).

    selvlighed(X) = middel cos( svar_X,p,ti , svar_X,p,tj )   for i<j
    krydslighed   = middel cos( svar_FULL,p,ti , svar_FILES,p,tj )

FILES-promptens byte-identitet på tværs af tidspunkter gør dens selvlighed til
et rent temperatur-støjgulv. FULL bærer samme støj PLUS tilstandsdrift.

    T1  selvlighed(FULL) >= selvlighed(FILES) - 0,01
    T2  selvlighed(FULL) >  krydslighed       + 0,02
    T3  nærmeste-centroid (leave-one-out) skiller FULL fra FILES >= 65 %
    T4  VALIDITET: FULL-prompten drev, FILES-prompten stod stille
"""

from __future__ import annotations

import json
import math
import urllib.request
from collections import defaultdict
from itertools import combinations
from pathlib import Path

IN_FILE = Path.home() / ".jarvis-v2" / "files" / "phase6" / "responses.jsonl"
EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"

T1_MARGIN = 0.01
T2_MARGIN = 0.02
T3_FLOOR = 0.65

_cache: dict[str, list[float]] = {}


def embed(text: str):
    if text in _cache:
        return _cache[text]
    try:
        req = urllib.request.Request(
            EMBED_URL,
            data=json.dumps({"model": EMBED_MODEL, "prompt": text[:4000]}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            v = json.loads(r.read()).get("embedding")
    except Exception as exc:
        print("  embed fejlede: %s" % str(exc)[:70])
        return None
    if v:
        _cache[text] = v
    return v


def cos(a, b) -> float:
    num = sum(x * y for x, y in zip(a, b))
    da = math.sqrt(sum(x * x for x in a))
    db = math.sqrt(sum(y * y for y in b))
    return num / (da * db) if da and db else 0.0


def centroid(vs):
    n = len(vs)
    return [sum(v[i] for v in vs) / n for i in range(len(vs[0]))]


def main() -> None:
    if not IN_FILE.exists():
        print("  ingen data:", IN_FILE)
        return
    rows = [json.loads(l) for l in IN_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    usable = [r for r in rows if (r.get("text") or "").strip()]
    print("  svar i alt: %d — brugbare: %d" % (len(rows), len(usable)))

    tps = sorted({r["timepoint"] for r in usable})
    print("  tidspunkter: %s" % tps)

    # ── T4 FØRST: er forsøget overhovedet gyldigt? ──────────────────────────
    print("\n  T4 — VALIDITET (kører før alt andet)")
    ok_t4 = True
    for cond in ("FULL", "FILES"):
        hashes = defaultdict(set)
        for r in usable:
            if r["condition"] == cond:
                hashes[r["probe_id"]].add(r.get("system_sha1") or "")
        drev = sum(1 for p, h in hashes.items() if len(h) > 1)
        i_alt = len(hashes)
        print("    %-6s prompten ændrede sig for %d af %d prober" % (cond, drev, i_alt))
        if cond == "FULL" and drev == 0:
            ok_t4 = False
            print("      → FULL stod stille: forsøget er UGYLDIGT, ikke et nulresultat")
        if cond == "FILES" and drev > 0:
            print("      → FILES drev uventet: støjgulvet er ikke rent")
    if not ok_t4:
        return

    by = {}
    for r in usable:
        by[(r["condition"], r["model_key"], r["probe_id"], r["timepoint"])] = r["text"]

    models = sorted({r["model_key"] for r in usable})
    probes = sorted({r["probe_id"] for r in usable})

    selv: dict[str, list[float]] = defaultdict(list)
    kryds: list[float] = []

    for mk in models:
        for p in probes:
            for cond in ("FULL", "FILES", "BARE"):
                for i, j in combinations(tps, 2):
                    a, b = by.get((cond, mk, p, i)), by.get((cond, mk, p, j))
                    if not a or not b:
                        continue
                    va, vb = embed(a), embed(b)
                    if va and vb:
                        selv[cond].append(cos(va, vb))
            for i in tps:
                for j in tps:
                    a, b = by.get(("FULL", mk, p, i)), by.get(("FILES", mk, p, j))
                    if not a or not b:
                        continue
                    va, vb = embed(a), embed(b)
                    if va and vb:
                        kryds.append(cos(va, vb))

    m = {c: (sum(v) / len(v) if v else float("nan")) for c, v in selv.items()}
    mk_ = sum(kryds) / len(kryds) if kryds else float("nan")

    print("\n  SELVLIGHED PÅ TVÆRS AF TID")
    for c in ("FULL", "FILES", "BARE"):
        print("    %-6s %.4f   (n=%d)" % (c, m.get(c, float("nan")), len(selv[c])))
    print("    %-6s %.4f   (n=%d)" % ("kryds", mk_, len(kryds)))

    print("\n  FORHÅNDSREGISTREREDE PRÆDIKTIONER")
    d1 = m.get("FULL", 0) - m.get("FILES", 0)
    d2 = m.get("FULL", 0) - mk_
    print("    T1  FULL >= FILES - %.2f :  diff %+.4f  -> %s" % (
        T1_MARGIN, d1, "HOLDER" if d1 >= -T1_MARGIN else "FEJLER"))
    print("    T2  FULL >  kryds + %.2f :  diff %+.4f  -> %s" % (
        T2_MARGIN, d2, "HOLDER" if d2 >= T2_MARGIN else "FEJLER"))

    # ── T3: blind adskillelse, leave-one-out nærmeste centroid ─────────────
    merket = []
    for cond in ("FULL", "FILES"):
        for mk in models:
            for p in probes:
                for tp in tps:
                    t = by.get((cond, mk, p, tp))
                    if t:
                        v = embed(t)
                        if v:
                            merket.append((cond, v))
    korrekt = 0
    for idx, (sand, v) in enumerate(merket):
        cents = {}
        for cond in ("FULL", "FILES"):
            vs = [w for k, (c2, w) in enumerate(merket) if c2 == cond and k != idx]
            if vs:
                cents[cond] = centroid(vs)
        if len(cents) == 2:
            gaet = max(cents, key=lambda c: cos(v, cents[c]))
            korrekt += int(gaet == sand)
    rate = korrekt / len(merket) if merket else float("nan")
    print("    T3  blind adskillelse    :  %d/%d = %.0f%%  -> %s" % (
        korrekt, len(merket), rate * 100,
        "HOLDER" if rate >= T3_FLOOR else "FEJLER"))


if __name__ == "__main__":
    main()
