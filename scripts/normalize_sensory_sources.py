#!/usr/bin/env python3
"""Normalisér kilde-navnene i Sansernes Arkiv — én gang, med tør-kørsel først.

Brug:
    python3 scripts/normalize_sensory_sources.py --dry-run   # viser mappingen
    python3 scripts/normalize_sensory_sources.py --apply     # skriver

Skriver en JSON-dump af de ramte rækkers FØR-tilstand til `backups/` inden
skrivning, så ændringen kan rulles tilbage. Dumpet er den ægte sikkerhedsnet:
en `cp` af hele DB'en er både dyrere og upålidelig (målt 28/9-2026: en 5 GB
`cp` der timede ud gav en korrupt fil i *præcis* kildestørrelse).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.runtime.db_sensory import connect  # noqa: E402
from core.services.sensory_source import CANONICAL_SOURCES, canonical_source  # noqa: E402

JARVIS_HOME = Path("/home/bs/.jarvis-v2")


def _laes_alle(conn) -> list[tuple[str, str]]:
    rows = conn.execute("SELECT id, metadata_json FROM sensory_memories").fetchall()
    return [(r[0], r[1] or "{}") for r in rows]


def _plan(rows: list[tuple[str, str]]) -> list[tuple[str, str, str, dict]]:
    """Returnér (id, gammel_json, ny_json, nye_metadata) for rækker der ændres."""
    plan = []
    for rid, mj in rows:
        try:
            meta = json.loads(mj)
        except Exception:
            meta = {}
        if not isinstance(meta, dict):
            meta = {}
        raa = meta.get("source")
        kanonisk = canonical_source(raa)
        ny = dict(meta)
        ny["source"] = kanonisk
        if raa is not None and str(raa).strip() != kanonisk:
            ny.setdefault("source_raw", str(raa))
        if ny == meta:
            continue
        plan.append(
            (rid, mj, json.dumps(ny, ensure_ascii=False), ny)
        )
    return plan


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="skriv ændringerne")
    ap.add_argument("--dry-run", action="store_true", help="vis kun mappingen")
    args = ap.parse_args()
    if not args.apply and not args.dry_run:
        ap.error("vælg --dry-run eller --apply")

    with connect() as conn:
        rows = _laes_alle(conn)
        plan = _plan(rows)

        foer = Counter()
        efter = Counter()
        for _rid, mj in rows:
            try:
                foer[str(json.loads(mj).get("source"))] += 1
            except Exception:
                foer["<ulæselig>"] += 1
        # EFTER skal tælle ALLE rækker — ikke kun de ændrede. Ellers ser det ud
        # som om arkivet kun har 427 poster, og oprydningen ser mindre ud end den er.
        aendret = {r[0] for r in plan}
        for _rid, _mj, _nj, ny in plan:
            efter[ny["source"]] += 1
        for rid, mj in rows:
            if rid in aendret:
                continue
            try:
                efter[str(json.loads(mj).get("source"))] += 1
            except Exception:
                efter["<ulæselig>"] += 1

        print(f"poster i alt:            {len(rows)}")
        print(f"poster der ændres:       {len(plan)}")
        print(f"unikke kilder før:       {len(foer)}")
        print(f"unikke kilder efter:     {len(efter)}")
        print()
        print("=== MAPPING (rå → kanonisk) ===")
        par = Counter()
        for rid, mj, nj, ny in plan:
            try:
                raa = str(json.loads(mj).get("source"))
            except Exception:
                raa = "<ulæselig>"
            par[(raa, ny["source"])] += 1
        for (raa, kan), n in sorted(par.items(), key=lambda x: -x[1]):
            print(f"{n:6d}  {raa[:48]:50s} → {kan}")

        print()
        print("=== EFTER ===")
        for k, v in efter.most_common():
            print(f"{v:6d}  {k}")

        ukendte = [k for k in efter if k not in CANONICAL_SOURCES]
        if ukendte:
            print(f"\n⚠️  kanoniske navne uden for sættet: {ukendte}")
            return 2

        if args.dry_run:
            print("\n(tør-kørsel — intet skrevet)")
            return 0

        # Dump FØR-tilstand for de ramte rækker.
        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        dump = JARVIS_HOME / "backups" / f"sensory-sources-{ts}.json"
        dump.parent.mkdir(parents=True, exist_ok=True)
        dump.write_text(
            json.dumps(
                {"rows": [{"id": r[0], "metadata_json": r[1]} for r in plan]},
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
        print(f"\ndump af før-tilstand: {dump}")

        with conn:
            conn.executemany(
                "UPDATE sensory_memories SET metadata_json = ? WHERE id = ?",
                [(nj, rid) for rid, _mj, nj, _ny in plan],
            )
        print(f"skrevet: {len(plan)} rækker")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
