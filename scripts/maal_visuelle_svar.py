#!/usr/bin/env python
"""Hvor ofte svarer Jarvis VISUELT? — nulpunkt og dagsserie.

Baggrund: desk har renderet ```mermaid-hegn til SVG siden foraaret
(`MermaidBlock.tsx`), og intet sted i prompten naevnte det. Maalt 6/10-2026:
**0 af 10.774 assistent-beskeder** — han har aldrig emitteret ét hegn.
Kapabiliteten var bygget og utalt.

Et foerste opslag gav 3 traef og blev meldt som «0,03 %». Det var FORKERT: de
tre var en `compact_marker` og to `tool`-resultater fra 2/10, fordi
forespoergslen ikke filtrerede paa `role`. Derfor filtrerer dette script
eksplicit — et tal om HANS adfaerd maa kun taelle hans egne beskeder.

Prompten siger det nu (`prompt_sections/output_discipline.py`). Dette script er
den anden halvdel: uden et tal foer og efter er «vi fortalte ham det» en
paastand, ikke en maaling.

Koeres paa CT105:
    /opt/conda/envs/ai/bin/python scripts/maal_visuelle_svar.py [--dage 14]
"""

from __future__ import annotations

import argparse
import os
import sqlite3

#: Hegn vi kan TEGNE. `diagram_fences` tælles for sig: et hegn vi ikke kan
#: rendere er ikke et visuelt svar, uanset hvor godt det er ment.
_TEGNEBARE = ("```mermaid",)


def _conn() -> sqlite3.Connection:
    sti = os.path.expanduser("~/.jarvis-v2/state/jarvis.db")
    c = sqlite3.connect("file:" + sti + "?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c


def dagsserie(c: sqlite3.Connection, dage: int) -> list[dict[str, object]]:
    """Pr. dag: assistent-beskeder, heraf med et tegnebart hegn, og raten.

    Graensen er `strftime`-formateret, ikke `datetime('now', …)`: `created_at` er
    ISO med `T`, og `T` sorterer EFTER mellemrum, saa mellemrums-formatet
    slipper hele graense-dagen igennem.
    """
    like = " OR ".join(["content LIKE ?"] * len(_TEGNEBARE))
    rows = c.execute(
        f"""SELECT substr(created_at, 1, 10) AS dag,
                   COUNT(*) AS beskeder,
                   SUM(CASE WHEN {like} THEN 1 ELSE 0 END) AS visuelle
            FROM chat_messages
            WHERE role = 'assistant'
              AND created_at >= strftime('%Y-%m-%dT%H:%M:%S', 'now', ?)
            GROUP BY dag ORDER BY dag""",
        (*[f"%{m}%" for m in _TEGNEBARE], f"-{int(dage)} days"),
    ).fetchall()
    ud = []
    for r in rows:
        n = int(r["beskeder"] or 0)
        v = int(r["visuelle"] or 0)
        ud.append({"dag": r["dag"], "beskeder": n, "visuelle": v,
                   "pct": round(100.0 * v / n, 2) if n else 0.0})
    return ud


def i_alt(c: sqlite3.Connection) -> dict[str, object]:
    like = " OR ".join(["content LIKE ?"] * len(_TEGNEBARE))
    r = c.execute(
        f"""SELECT COUNT(*) AS beskeder,
                   SUM(CASE WHEN {like} THEN 1 ELSE 0 END) AS visuelle
            FROM chat_messages WHERE role = 'assistant'""",
        tuple(f"%{m}%" for m in _TEGNEBARE),
    ).fetchone()
    n = int(r["beskeder"] or 0)
    v = int(r["visuelle"] or 0)
    return {"beskeder": n, "visuelle": v,
            "pct": round(100.0 * v / n, 3) if n else 0.0}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dage", type=int, default=14)
    a = p.parse_args()
    with _conn() as c:
        alt = i_alt(c)
        print("ALLE TIDER: %d assistent-beskeder, %d med et tegnebart hegn (%.3f %%)"
              % (alt["beskeder"], alt["visuelle"], alt["pct"]))
        print()
        print("%-12s %9s %9s %7s" % ("dag", "beskeder", "visuelle", "pct"))
        for d in dagsserie(c, a.dage):
            print("%-12s %9d %9d %6.2f%%" % (d["dag"], d["beskeder"], d["visuelle"], d["pct"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
