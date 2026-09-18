#!/usr/bin/env python
"""Hvad består Jarvis' perception af — og hvor meget af den er hans egen støj?

Baggrund (18/9-2026): Jarvis' perception var næsten udelukkende hans egen
maskinstøj — ~44.000 perceptions i døgnet, cirka 31 i minuttet, hvoraf 81 % var
hans egne værktøjskald og 0,6 % det han faktisk ser og hører.

Gentagne signaler dæmpes nu i to trin: `b9713e1eb` tog værktøjsresultaterne,
`cbb769396` tog læringsreglerne. Reglen er den samme for begge — første gang et
værktøj eller en regel ses inden for 60 minutter tæller som en ændring,
gentagelser gør ikke, og `tool-error` er undtaget.

Dette script måler om dæmpningen holdt, på ægte data over et helt døgn.

**Tæl altid over et TIDSVINDUE, aldrig over et rækkeantal.** Den første
opgørelse her i huset talte på de 3.000 nyeste rækker og gav «tool 54,8 %,
policy 35,2 %, sanset 1,6 %». Alle tre tal var forkerte, fordi de 3.000 rækker
tilfældigvis dækkede en atypisk periode — og et af dem blev brugt som grundlag
for en beslutning. Derfor tager scriptet `--timer`/`--siden` og ikke `--limit`.

    python scripts/perception_mix.py               # sidste 24 timer
    python scripts/perception_mix.py --timer 48    # andet vindue
    python scripts/perception_mix.py --siden 2026-09-18T13:31:34

Tallene kommer fra `emotional_memory_anchors` (anchor_type='perceptual_event'),
som er dér perceptions faktisk persisteres — der findes ingen egen tabel.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:  # allow `python scripts/perception_mix.py` standalone
    sys.path.insert(0, str(REPO))


def _hent(siden: str) -> tuple[Counter, Counter, int]:
    from core.runtime.db_core import connect

    kinds: Counter = Counter()
    typer: Counter = Counter()
    with connect() as conn:
        raekker = conn.execute(
            "SELECT context_features_json FROM emotional_memory_anchors "
            "WHERE anchor_type='perceptual_event' AND captured_at >= ?",
            (siden,),
        ).fetchall()
    for (rå,) in raekker:
        try:
            d = json.loads(rå or "{}")
        except (TypeError, ValueError):
            kinds["uparsbar"] += 1
            continue
        kinds[str(d.get("event_kind") or "?")] += 1
        typer[str(d.get("change_type") or "?")] += 1
    return kinds, typer, len(raekker)


def _tabel(navn: str, taelling: Counter, i_alt: int) -> None:
    print(f"\n  {navn:<44}{'antal':>8}{'andel':>9}")
    print("  " + "-" * 61)
    for nøgle, v in taelling.most_common():
        andel = (v / i_alt * 100) if i_alt else 0.0
        print(f"  {nøgle:<44}{v:>8}{andel:>8.1f}%")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--timer", type=float, default=24.0, help="vinduets længde (standard 24)")
    p.add_argument("--siden", default="", help="ISO-tidspunkt; tilsidesætter --timer")
    args = p.parse_args()

    siden = args.siden.strip() or (
        datetime.now(UTC) - timedelta(hours=args.timer)
    ).isoformat()

    kinds, typer, i_alt = _hent(siden)
    print(f"\nPerceptions siden {siden}")
    print(f"I alt: {i_alt}")
    if not i_alt:
        print("\n  Ingen perceptions i vinduet.")
        return 0

    _tabel("event_kind (hvor perceptionen kom fra)", kinds, i_alt)
    _tabel("change_type (hvad den blev til)", typer, i_alt)

    # Det ene tal hele øvelsen handler om.
    sanset = kinds.get("memory.sensory.recorded", 0)
    vaerktoej = kinds.get("tool.completed", 0)
    print(
        f"\n  Sanset (øjne/ører): {sanset} ({sanset / i_alt * 100:.1f} %)"
        f"   ·   værktøjsstøj: {vaerktoej} ({vaerktoej / i_alt * 100:.1f} %)"
    )
    print("\n  Nulpunkt før dæmpningen — målt over TIDSVINDUER 18/9 kl. ~15:")
    print(f"    {'vindue':<10}{'perceptions':>12}{'policy':>16}{'tool':>17}{'sanset':>14}")
    for navn, i, pol, to, sa in (
        ("24 timer", "44.434", "3.785 (8,5 %)", "36.175 (81,4 %)", "245 (0,6 %)"),
        ("7 dage", "62.707", "4.424 (7,1 %)", "51.248 (81,7 %)", "634 (1,0 %)"),
        ("30 dage", "88.076", "6.924 (7,9 %)", "66.857 (75,9 %)", "1.475 (1,7 %)"),
    ):
        print(f"    {navn:<10}{i:>12}{pol:>16}{to:>17}{sa:>14}")
    print("    Dæmpet: værktøjer b9713e1eb 13:31 UTC · regler cbb769396 ~15:30 UTC")
    print(
        "\n  Bemærk: andelen kan stige uden at noget er blevet bedre — falder\n"
        "  totalvolumen, stiger procenten af sig selv. Læs det absolutte antal\n"
        "  sanseindtryk ved siden af andelen.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
