#!/usr/bin/env python3
"""Mål hvor stor en del af Ollamas faktiske forbrug der står i ``costs``.

HVORFOR. Ollamas eget API (``GET https://ollama.com/api/usage``) er den eneste
uafhængige sandhed om hvad der faktisk blev brugt. ``costs`` er vores regnskab.
Dækningen mellem dem er det tal der afgør om bogføringen virker — ikke antallet
af rækker, og ikke om koden "står på disken".

Målt 24/11-2026: dækningen var 0-6 % om natten og 99-100 % i timerne efter at
de cirkulære ``_cache_split``-importer blev fjernet. Kurven knækkede hvor fixene
landede. Dette script er det der kan afgøre om knækket holder en hel nat.

BRUG
    python3 scripts/ollama_daekning.py                    # sidste 24 timer
    python3 scripts/ollama_daekning.py --hours 12
    python3 scripts/ollama_daekning.py --since 2026-11-24T20:00:00Z
    python3 scripts/ollama_daekning.py --json             # maskinlæsbart

VIGTIGT OM TOLKNING
- Ollama bucket'er i hele timer; vi grupperer ``costs`` på samme timegrænse.
- ``usage_usd`` fra Ollama er deres egen prisberegning. Vores ``cost_usd``
  bruger vores prisliste. USD-dækningen kan derfor afvige selv ved fuld
  kald-dækning — læs kald- og token-dækningen først.
- Timer hvor Ollama rapporterer 0 kald er udeladt af gennemsnittet; de ville
  trække det mod nul uden at sige noget.
- En time der slutter EFTER ``now`` er delvis og markeres ``(delvis)``.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

RUNTIME_CONFIG = Path.home() / ".jarvis-v2" / "config" / "runtime.json"
DB_PATH = Path.home() / ".jarvis-v2" / "state" / "jarvis.db"
USAGE_URL = "https://ollama.com/api/usage"


def _api_key() -> str:
    data = json.loads(RUNTIME_CONFIG.read_text())
    key = str(data.get("ollama_api_key") or "").strip()
    if not key:
        raise SystemExit(f"ollama_api_key mangler i {RUNTIME_CONFIG}")
    return key


def _range_for(hours: int) -> str:
    """Ollama accepterer KUN ``24h``, ``7d`` og ``30d`` (målt 24/11-2026).

    Et vilkårligt ``6h`` giver HTTP 400 ``range must be 24h, 7d, or 30d``. Vi
    vælger den mindste gyldige range der dækker vinduet og filtrerer bagefter
    på ``since``.
    """
    if hours <= 24:
        return "24h"
    if hours <= 168:
        return "7d"
    return "30d"


def hent_ollama(hours: int) -> dict:
    """Ollamas eget forbrug, pr. time."""
    req = urllib.request.Request(
        f"{USAGE_URL}?range={_range_for(hours)}",
        headers={"Authorization": f"Bearer {_api_key()}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Ollama svarede HTTP {exc.code}: {exc.read()[:300]!r}")


def hent_vores(since: str) -> dict[str, dict]:
    """Vores ``costs``-rækker for ollama, grupperet på time (UTC)."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            """
            SELECT substr(created_at, 1, 13) AS timen,
                   count(*),
                   coalesce(sum(input_tokens), 0),
                   coalesce(sum(output_tokens), 0),
                   coalesce(sum(cost_usd), 0)
            FROM costs
            WHERE provider = 'ollama' AND created_at >= ?
            GROUP BY timen
            ORDER BY timen
            """,
            (since,),
        ).fetchall()
    finally:
        conn.close()
    return {
        r[0]: {"kald": r[1], "in": r[2], "out": r[3], "usd": r[4]} for r in rows
    }


def _pct(a: float, b: float) -> str:
    if b <= 0:
        return "  —  "
    return f"{100.0 * a / b:5.1f}%"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hours", type=int, default=24, help="vindue i timer (default 24)")
    ap.add_argument("--since", help="ISO-tid; overstyrer --hours for vores side")
    ap.add_argument("--json", action="store_true", help="maskinlæsbart output")
    args = ap.parse_args()

    ollama = hent_ollama(args.hours)
    now = datetime.now(UTC)
    since = args.since or (
        now - timedelta(hours=args.hours)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    vores = hent_vores(since)

    linjer: list[dict] = []
    since_time = since[:13]
    for b in ollama.get("buckets") or []:
        start = str(b.get("from") or "")[:13]
        if not start:
            continue
        # API'et giver hele dage/24h-buckets; skær det der ligger før vinduet væk.
        if start < since_time:
            continue
        v = vores.get(start, {"kald": 0, "in": 0, "out": 0, "usd": 0.0})
        o_tok = int(b.get("input_tokens") or 0) + int(b.get("output_tokens") or 0)
        v_tok = int(v["in"]) + int(v["out"])
        slut = str(b.get("until") or "")
        delvis = bool(slut) and slut > now.strftime("%Y-%m-%dT%H:%M:%S")
        linjer.append(
            {
                "time": start,
                "delvis": delvis,
                "o_kald": int(b.get("request_count") or 0),
                "v_kald": int(v["kald"]),
                "o_tok": o_tok,
                "v_tok": v_tok,
                "o_usd": float(b.get("usage_usd") or 0.0),
                "v_usd": float(v["usd"]),
            }
        )

    if args.json:
        print(json.dumps({"range": args.hours, "hours": linjer}, indent=2))
        return 0

    tot = ollama.get("totals") or {}
    print(
        f"Ollama ({args.hours}t): {tot.get('request_count', 0)} kald, "
        f"${float(tot.get('usage_usd') or 0):.4f}, "
        f"in={tot.get('input_tokens', 0):,} out={tot.get('output_tokens', 0):,}"
    )
    print(f"Vores vindue: fra {since}")
    print()
    print("time(UTC)          oll_kald vores  daek%   oll_tok     vores_tok   tok%")
    print("-" * 78)
    sum_o = sum_v = sum_ot = sum_vt = 0
    sum_ou = sum_vu = 0.0
    for r in linjer:
        mark = " (delvis)" if r["delvis"] else ""
        print(
            f"{r['time']:<18} {r['o_kald']:>6} {r['v_kald']:>6} {_pct(r['v_kald'], r['o_kald']):>7} "
            f"{r['o_tok']:>11,} {r['v_tok']:>11,} {_pct(r['v_tok'], r['o_tok']):>7}{mark}"
        )
        sum_o += r["o_kald"]
        sum_v += r["v_kald"]
        sum_ot += r["o_tok"]
        sum_vt += r["v_tok"]
        sum_ou += r["o_usd"]
        sum_vu += r["v_usd"]
    print("-" * 78)
    print(
        f"{'SUM':<18} {sum_o:>6} {sum_v:>6} {_pct(sum_v, sum_o):>7} "
        f"{sum_ot:>11,} {sum_vt:>11,} {_pct(sum_vt, sum_ot):>7}"
    )
    print(
        f"{'USD':<18} {sum_ou:>6.4f} {sum_vu:>6.4f} {_pct(sum_vu, sum_ou):>7}"
    )
    fulde = [r for r in linjer if r["o_kald"] > 0 and not r["delvis"]]
    if fulde:
        gns = 100.0 * sum(r["v_kald"] for r in fulde) / sum(r["o_kald"] for r in fulde)
        gns_t = 100.0 * sum(r["v_tok"] for r in fulde) / max(
            1, sum(r["o_tok"] for r in fulde)
        )
        print()
        print(
            f"Gennemsnit over {len(fulde)} hele timer med trafik: "
            f"{gns:.1f}% af kald, {gns_t:.1f}% af tokens"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
