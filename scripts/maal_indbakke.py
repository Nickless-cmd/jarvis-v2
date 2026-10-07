#!/usr/bin/env python3
"""Virker indbakkens to trin? Og er 2 det rigtige tal?

Opgave 7 i `docs/superpowers/specs/2026-10-03-indbakke-som-kontrolflade-design.md`.

## Hvorfor den findes

R2's punkt 2 ventede fra 13. juni på en måling der aldrig blev lavet, og
tærsklerne blev først sat da nogen regnede efter. Skygge-registrets 24-timers
vindue stod 78 dage. `_INDBAKKE_PAAMINDELSER_FOER_BLOK = 2` er et STARTPUNKT,
ikke en måling — R2's 15 % er ikke inboxens heed-rate.

## De to heed-rater skal stå HVER FOR SIG

Det er hele pointen. Trin 1 er den høflige anmodning; trin 2 er nægtelsen. De
måler forskellige ting:

* **trin 1's heed-rate** = af de poster der fik en påmindelse, hvor mange blev
  så afgjort FØR nægtelsen? Er den høj, virker det høflige trin, og tærsklen
  kunne sættes op.
* **trin 2's heed-rate** = af de poster der faktisk blokerede, hvor mange blev
  afgjort bagefter? Er den lav, bliver nægtelsen ignoreret, og så har vi bygget
  den tredje mekanisme der skal reddes af den fjerde.

Et samlet tal over begge ville skjule præcis den forskel beslutningen hviler på.

## «released uden årsag er ikke efterlevelse»

Derfor parres hændelser per (bruger_id, post_id), og udfaldene holdes adskilt:
`done`, `drop`, `udloebet`, `afsluttet_af_kilde`, fail-open og DB-fejl. En post
der forsvandt fordi gaten var blind er ikke en post nogen reagerede på.

Kører read-only. Skriver intet.

Brug (på CT105 — `local_db_is_not_production`):

    /home/bs/miniconda3/envs/ai/bin/python scripts/maal_indbakke.py
    ... --dage 7
    ... --json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

#: Hændelserne indbakken efterlader. Navnene er dem `inbox_gate._spor` og
#: `inbox_state._spor` faktisk publicerer — ikke navne jeg synes de burde have.
#: En måling der spørger om et event der ikke findes måler nul og ser
#: fuldstændig normal ud; det er `seks_kognitive_systemer_uden_skriver` i
#: spejlvendt form.
_KINDS = (
    "inbox.registreret",
    "inbox.registrering_fejlede",
    "inbox.afgjort",
    "inbox_gate.reminded",
    "inbox_gate.blocked",
    "inbox_gate.fail_open",
)


def _iso_graense(dage: int) -> str:
    """`strftime`, ikke `datetime('now', …)`.

    `created_at` er ISO **med `T`**, og `T` sorterer EFTER mellemrum — så
    `datetime('now','-1 day')` som grænse slipper hele dagen igennem. Fælden er
    ramt fire gange i dette hus, så grænsen dannes i Python og sendes som
    parameter.
    """
    from datetime import UTC, datetime, timedelta
    return (datetime.now(UTC) - timedelta(days=max(1, int(dage)))).strftime(
        "%Y-%m-%dT%H:%M:%S")


def _haent(dage: int) -> list[dict[str, Any]]:
    from core.runtime.db import connect
    graense = _iso_graense(dage)
    pladser = ",".join("?" for _ in _KINDS)
    with connect() as conn:
        rows = conn.execute(
            f"SELECT kind, payload_json, created_at FROM events "
            f"WHERE kind IN ({pladser}) AND created_at > ? "
            f"ORDER BY created_at ASC",
            (*_KINDS, graense)).fetchall()
    ud = []
    for r in rows:
        try:
            p = json.loads(r["payload_json"] or "{}")
        except (ValueError, TypeError):
            p = {}
        ud.append({"kind": str(r["kind"]), "payload": p,
                   "created_at": str(r["created_at"])})
    return ud


def _poster_i(payload: dict[str, Any]) -> list[str]:
    """Post-id'erne i en hændelse, uanset om den bærer én eller mange."""
    if payload.get("poster"):
        return [str(x) for x in payload["poster"]]
    for n in ("kilde_id", "post_id", "id"):
        if payload.get(n):
            return [str(payload[n])]
    return []


def maal(dage: int = 7) -> dict[str, Any]:
    h = _haent(dage)

    # Pr. (bruger, post): hvad skete der, i rækkefølge?
    spor: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    pr_doegn: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for e in h:
        doegn = e["created_at"][:10]
        pr_doegn[doegn][e["kind"]] += 1
        bruger = str(e["payload"].get("bruger_id") or "")
        for pid in _poster_i(e["payload"]) or [""]:
            spor[(bruger, pid)].append(e)

    # Trin 1 og trin 2 hver for sig.
    t1_paamindt: set[tuple[str, str]] = set()
    t2_blokeret: set[tuple[str, str]] = set()
    afgjort_udfald: dict[tuple[str, str], str] = {}
    afgjort_efter_blok: set[tuple[str, str]] = set()
    for noegle, kaede in spor.items():
        blev_blokeret = False
        for e in kaede:
            k = e["kind"]
            if k == "inbox_gate.reminded":
                t1_paamindt.add(noegle)
            elif k == "inbox_gate.blocked":
                t2_blokeret.add(noegle)
                blev_blokeret = True
            elif k == "inbox.afgjort":
                afgjort_udfald[noegle] = str(e["payload"].get("udfald") or "ukendt")
                if blev_blokeret:
                    afgjort_efter_blok.add(noegle)

    # Trin 1's efterlevelse: paamindt, afgjort, og ALDRIG naaet til blokering.
    t1_efterlevet = {n for n in t1_paamindt
                     if n in afgjort_udfald and n not in t2_blokeret}
    t1_rate = (100.0 * len(t1_efterlevet) / len(t1_paamindt)) if t1_paamindt else None
    t2_rate = (100.0 * len(afgjort_efter_blok) / len(t2_blokeret)) if t2_blokeret else None

    # Hvad skete der med dem der IKKE blev afgjort? «Released uden aarsag er
    # ikke efterlevelse» — saa de taelles for sig frem for at forsvinde.
    uafgjort = [n for n in (t1_paamindt | t2_blokeret) if n not in afgjort_udfald]

    # Den nuvaerende tilstand, direkte fra tabellen. Et spor kan mangle
    # hændelser (bussen nede, en tidligere udgave uden telemetri), og saa er
    # tabellen den eneste sandhed om hvad der STAAR aabent.
    tilstand = _tilstand()

    return {
        "vindue_dage": dage,
        "haendelser_i_alt": len(h),
        "haendelser_pr_kind": {k: sum(d.get(k, 0) for d in pr_doegn.values())
                               for k in _KINDS},
        "pr_doegn": {d: dict(v) for d, v in sorted(pr_doegn.items())},
        "trin_1": {
            "poster_paamindt": len(t1_paamindt),
            "efterlevet_uden_blokering": len(t1_efterlevet),
            "heed_rate_pct": None if t1_rate is None else round(t1_rate, 1),
        },
        "trin_2": {
            "poster_blokeret": len(t2_blokeret),
            "afgjort_efter_blokering": len(afgjort_efter_blok),
            "heed_rate_pct": None if t2_rate is None else round(t2_rate, 1),
        },
        "udfald": {u: sum(1 for v in afgjort_udfald.values() if v == u)
                   for u in sorted(set(afgjort_udfald.values()))},
        "uafgjort_efter_varsel": len(uafgjort),
        "fail_open": sum(1 for e in h if e["kind"] == "inbox_gate.fail_open"),
        "registrering_fejlede": sum(
            1 for e in h if e["kind"] == "inbox.registrering_fejlede"),
        "tilstand_nu": tilstand,
        "taerskel": _taerskel(),
    }


def _taerskel() -> dict[str, Any]:
    try:
        from core.runtime.settings import load_settings
        s = load_settings()
        return {"inbox_gate_enabled": bool(getattr(s, "inbox_gate_enabled", True)),
                "paamindelser_foer_blok": int(
                    getattr(s, "inbox_paamindelser_foer_blok", 2))}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def _tilstand() -> dict[str, Any]:
    """Hvad STAAR der i tabellen lige nu, uanset hvad sporet siger?"""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            rows = conn.execute(
                "SELECT status, verificeret_ejer, count(*) n, "
                "sum(kraever_handling) gatende, max(paamindelser) maks_paamindelser "
                "FROM inbox_items GROUP BY status, verificeret_ejer").fetchall()
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
    return {f"{r['status']}/{r['verificeret_ejer']}": {
        "antal": int(r["n"]), "gatende": int(r["gatende"] or 0),
        "maks_paamindelser": int(r["maks_paamindelser"] or 0)} for r in rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dage", type=int, default=7)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = maal(a.dage)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0

    print(f"INDBAKKEN — {r['vindue_dage']} doegn, {r['haendelser_i_alt']} haendelser")
    t = r["taerskel"]
    print(f"  kontakt: {t.get('inbox_gate_enabled')}   "
          f"taerskel: {t.get('paamindelser_foer_blok')} paamindelser foer blok")
    for navn, d in (("TRIN 1 (paamindelsen)", r["trin_1"]),
                    ("TRIN 2 (naegtelsen)", r["trin_2"])):
        rate = d["heed_rate_pct"]
        n = d.get("poster_paamindt", d.get("poster_blokeret", 0))
        print(f"\n  {navn}: {n} post(er)")
        if rate is None:
            # ET NUL ER IKKE EN RATE. Uden denne linje ville «0,0 %» og «der
            # var ingen at maale paa» se fuldstaendig ens ud — og det er
            # praecis den forveksling der fik R2's punkt 2 til at vente i tre
            # maaneder.
            print("    heed-rate: KAN IKKE MAALES (ingen poster naaede dette trin)")
        else:
            print(f"    heed-rate: {rate} %")
    if r["udfald"]:
        print("\n  udfald:", ", ".join(f"{k}={v}" for k, v in r["udfald"].items()))
    print(f"  uafgjort efter varsel: {r['uafgjort_efter_varsel']}")
    print(f"  fail-open: {r['fail_open']}   "
          f"registrering fejlede: {r['registrering_fejlede']}")
    print("\n  TILSTAND NU (fra tabellen, ikke fra sporet):")
    if not r["tilstand_nu"]:
        print("    tabellen er tom")
    for k, v in sorted(r["tilstand_nu"].items()):
        if isinstance(v, dict):
            print(f"    {k:34} {v['antal']:>4} stk, {v['gatende']} gatende, "
                  f"maks {v['maks_paamindelser']} paamindelser")
        else:
            print(f"    {k}: {v}")
    print("\n  Hvert kind for sig (et nul her kan betyde at sporet mangler):")
    for k, n in r["haendelser_pr_kind"].items():
        print(f"    {k:34} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def registrer_vindue(timer: float = 72.0) -> dict[str, Any]:
    """Opgave 7 trin 3: registrér maalevinduet, saa paamindelsen melder.

    Hvorfor det ikke bare er en note i en commit-besked: skygge-registrets
    24-timers vindue stod **78 dage**, og registret VIDSTE det hele tiden —
    ingen visning gjorde det til et tal nogen saa. Rettelsen fra 2/10 gav
    registret en durabel klokke, saa den melder naar vinduet er modent.

    72 timer, ikke 24: taersklen afhaenger af at BEGGE heed-rater kan maales,
    og trin 2 naas kun af en post der har faaet to paamindelser i to
    forskellige ture. Paa et doegn med faa mutationer ville der ikke vaere
    noget at maale paa — og et nul der bliver laest som en rate er praecis det
    `maal()` ovenfor er bygget til at forhindre.
    """
    try:
        from core.services.shadow_experiment_registry import register_experiment
        register_experiment(
            "inbox_gate_to_trins", timer,
            note=("Opgave 7: maal BEGGE heed-rater hver for sig foer "
                  "inbox_paamindelser_foer_blok=2 kan forsvares. "
                  "Koer: scripts/maal_indbakke.py --dage 3"))
    except Exception as exc:  # noqa: BLE001
        return {"status": "fejl", "error": str(exc)}
    return {"status": "ok", "vindue_timer": timer}
