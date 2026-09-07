#!/usr/bin/env python3
"""Aflæs sonden: honorerer providerne ``tool_choice="required"``?

Baggrund 7/9-2026. Vagten mod tomme løfter tvinger en runde med
``tool_choice="required"`` når Jarvis lover noget uden at kalde et værktøj.
I 8 af 36 tilfælde kom der stadig nul kald. Bjørn: «det er random.. til tider
sker det osse for flash uden syn» — og tallene gav ham ret (vision 11/15,
flash uden syn 13/16), så det er ikke en model der mangler evnen.

Tre forklaringer er udelukket ved måling: værktøjerne mangler ikke (70
annonceres), ``tool_choice`` sættes faktisk, og de FEJLENDE ture har mindre
kontekst end de lykkedes. Tilbage står providerens eget svar. Det er dét
`runtime.forced_tool_choice_probe` fanger, og dét denne rapport læser.

Sådan læses tallene:

  finish_reason=stop  + tekst   modellen VALGTE prosa på trods af `required`
                                → providerne håndhæver den ikke
  finish_reason=length          modellen løb tør undervejs
                                → et budget-problem, ikke et lydigheds-problem
  tools=0                       værktøjerne kom slet ikke med (ville være en
                                helt tredje fejl — den er udelukket i dag)
  thinking_fra                  KONSTANT True på tvungne runder (DeepSeek
                                afviser ellers med HTTP 400). Kan derfor ikke
                                forklare forskellen — men skifter den nogensinde
                                til False, er dét i sig selv et fund.

Kør:  python scripts/forced_tool_choice_report.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

DB = Path.home() / ".jarvis-v2" / "state" / "jarvis.db"
KIND = "runtime.forced_tool_choice_probe"


def _rows() -> list[dict]:
    if not DB.exists():
        print(f"Ingen database på {DB}", file=sys.stderr)
        return []
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        raa = con.execute(
            "SELECT created_at, payload_json FROM events WHERE kind=? ORDER BY created_at",
            (KIND,),
        ).fetchall()
    finally:
        con.close()
    ud = []
    for ts, p in raa:
        try:
            d = json.loads(p)
        except (ValueError, TypeError):
            continue
        d["created_at"] = ts
        ud.append(d)
    return ud


def main() -> int:
    rk = _rows()
    if not rk:
        print("Ingen målinger endnu. Sonden fyrer kun på tvungne runder "
              "(~12 i døgnet), så giv den lidt tid.")
        return 0

    honoreret = [r for r in rk if r.get("honoreret")]
    nej = [r for r in rk if not r.get("honoreret")]
    print(f"{len(rk)} tvungne runder — {len(honoreret)} kaldte et værktøj "
          f"({100 * len(honoreret) // max(len(rk), 1)} %), {len(nej)} gjorde ikke.\n")

    pr_model: Counter = Counter()
    kald_pr_model: Counter = Counter()
    for r in rk:
        m = str(r.get("model") or "?")
        pr_model[m] += 1
        if r.get("honoreret"):
            kald_pr_model[m] += 1
    print("pr. model:")
    for m, n in pr_model.most_common():
        print(f"  {m:<34} {kald_pr_model[m]:>3} af {n:>3}")

    if nej:
        print("\nrunder hvor `required` IKKE blev honoreret:")
        print(f"  {'tidspunkt':<20}{'finish':<10}{'tekst':>7}{'tools':>7}  model")
        for r in nej[-20:]:
            print(f"  {str(r.get('created_at'))[:19]:<20}"
                  f"{str(r.get('finish_reason') or '-'):<10}"
                  f"{int(r.get('text_chars') or 0):>7}"
                  f"{int(r.get('tools_advertised') or 0):>7}  "
                  f"{r.get('model')}")
        grunde = Counter(str(r.get("finish_reason") or "-") for r in nej)
        print("\n  fordelt på finish_reason:", dict(grunde))
        if grunde.get("stop"):
            print("  → «stop» med tekst betyder at providerne ikke håndhæver `required`.")
        if grunde.get("length"):
            print("  → «length» betyder at modellen løb tør — et budget-problem.")
        if any(int(r.get("tools_advertised") or 0) == 0 for r in nej):
            print("  → tools=0: værktøjerne kom slet ikke med. Helt anden fejl.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
