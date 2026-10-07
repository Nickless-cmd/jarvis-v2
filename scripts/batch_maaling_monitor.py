#!/usr/bin/env python3
"""Monitor paa vaerktoejer pr. agentisk runde. Tier medmindre tallet rykker.

HVORFOR DEN FINDES
------------------
5/10-2026 blev instruktionen om at batche uafhaengige vaerktoejskald deployet
(`720d3a607`). Bjoern spurgte: «men husker du det om et par dage? for jeg goer
ikk.» Svaret var nej — min kontekst doer. En maaling der afhaenger af at et
menneske eller en session husker den, er ikke en maaling.

Derfor denne: den koerer dagligt, skriver serien til en log, og siger KUN til
naar et tal har forladt sit stoejgulv. Tier den, er der intet at sige.

Den baerer TO maalinger, hver med sin egen dom og sit eget notifikations-ref:
vaerktoejer pr. runde (batch-instruktionen) og raesonnerings-A/B'en. De er
uafhaengige — en dom paa den ene siger intet om den anden.

TAERSKLERNE
-----------
Basislinjen blev maalt FOER deployet, over 15 dage: **1,54 vaerktoejer pr.
runde med spredning 0,10** (spaend 1,32-1,72). Derfor:

  over 1,64  → instruktionen landede
  under 1,44 → den gjorde det modsatte (ogsaa et svar, og vigtigere)
  imellem    → stilhed

Det er ÉN spredning. Mindre end det er ikke en aendring, og 4/10 naaede jeg
to modsatte konklusioner om samme tal fordi jeg jagtede en effekt under
stoejgulvet. Se memory `uaendret_er_ikke_altid_til_stede`.

**Og en stille dag maa ikke kunne fyre den.** En dag taeller kun med hvis den
har mindst MIN_RUNDER runder; den stilleste dag i basislinjen havde 464. Uden
kravet kunne tre runder paa en soendag afgoere sagen. Det er `beacon_vagt.py`'s
laere: der skal VARIGHED til, ikke én proeve.

GENTAGELSER
-----------
Ingen tilstandsfil. `notifikationer.opret()` er idempotent paa (slags, ref),
saa et stabilt `ref` pr. dom giver én notifikation nogensinde — ogsaa hvis
jobbet koerer hver dag i et aar. Databasen ejer tilstanden; monitoren ejer
ingen.

Koer paa Jarvis-hosten (CT105). Cron, én gang dagligt:
  17 9 * * * /opt/conda/envs/ai/bin/python3 /media/projects/jarvis-v2/scripts/batch_maaling_monitor.py
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, __file__.rsplit("/scripts/", 1)[0])
from scripts.maal_raesonnering_ab import (  # noqa: E402
    DEPLOY as AB_DEPLOY,
    armdata,
    runder_pr_run_pr_dag,
)
from scripts.maal_vaerktoejer_pr_runde import DB_PATH, dagsserie  # noqa: E402
from core.services.raesonnering_eksperiment import ARM_DAEMPET, ARM_FULD  # noqa: E402

HOME = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
LOG_PATH = HOME / "logs" / "vaerktoej_batch.jsonl"

BASISLINJE = 1.54
SPREDNING = 0.10
OVER = BASISLINJE + SPREDNING      # 1.64
UNDER = BASISLINJE - SPREDNING     # 1.44
MIN_RUNDER = 200                   # en stille dag taeller ikke med
DAGE_I_SNIT = 3


def vurder(
    serie: list[sqlite3.Row] | list[dict],
    *,
    dage: int = DAGE_I_SNIT,
    min_runder: int = MIN_RUNDER,
) -> tuple[str | None, float | None, int]:
    """Returnerer (dom, snit, antal_taellende_dage).

    Dommen er "landede", "faldt" eller None. None betyder BAADE «i stoejen»
    og «for lidt data» — og de to maa ikke blandes sammen udenfor, derfor
    returneres antallet af taellende dage ved siden af.
    """
    taeller = [
        r for r in serie
        if (r["runder"] or 0) >= min_runder and r["pr_runde"]
    ][-dage:]
    if len(taeller) < dage:
        return None, None, len(taeller)
    snit = sum(float(r["pr_runde"]) for r in taeller) / len(taeller)
    if snit > OVER:
        return "landede", snit, len(taeller)
    if snit < UNDER:
        return "faldt", snit, len(taeller)
    return None, snit, len(taeller)


#: En arm der ikke blev daempet raesonnerer stadig. Taersklen er lav med vilje:
#: `thinking: disabled` gav 0 i alle tre probe-koersler, saa et tal over dette
#: betyder at knappen ikke blev drejet — ikke at effekten er lille.
_RAESON_MAA_VAERE_UNDER = 50
#: Mindst saa mange dage med data i BEGGE arme foer noget sammenlignes.
_AB_MIN_DAGE = 3
#: Gulv under stoej-taersklen, i runder pr. run. To grunde: en spredning
#: udregnet paa 3-5 dage kan tilfaeldigt blive naesten nul, og en forskel under
#: en halv runde er ikke vaerd at vaekke nogen for. Basislinjen svinger 8,8-14,9
#: runder/run over fjorten dage, saa 0,5 er konservativt.
_AB_STOEJ_GULV = 0.5


def _spredning(tal: list[float]) -> float:
    if len(tal) < 2:
        return 0.0
    snit = sum(tal) / len(tal)
    return (sum((x - snit) ** 2 for x in tal) / (len(tal) - 1)) ** 0.5


def vurder_ab(arme: dict) -> tuple[str | None, str]:
    """Returnerer (dom, linje). Dommen er "knappen_virker_ikke", "forskel" eller None.

    Raekkefoelgen er ikke tilfaeldig: virker knappen ikke, maa der IKKE siges
    noget om kvalitet. En arm der ikke blev daempet viser «ingen forskel» af
    den forkerte grund, og det er vaerre end slet ingen maaling.
    """
    d, f = arme.get(ARM_DAEMPET), arme.get(ARM_FULD)
    if not d or not f:
        return None, "kun én arm har data"

    raeson = sorted(d["raeson"])
    median = raeson[len(raeson) // 2] if raeson else 0
    if median > _RAESON_MAA_VAERE_UNDER:
        return "knappen_virker_ikke", (
            f"den daempede arm raesonnerer stadig (median {median} tokens over "
            f"{d['runder']} runder) — forsoeget maaler ikke det det tror"
        )

    serie_d = runder_pr_run_pr_dag(d)
    serie_f = runder_pr_run_pr_dag(f)
    if len(serie_d) < _AB_MIN_DAGE or len(serie_f) < _AB_MIN_DAGE:
        return None, (f"for lidt data: {len(serie_d)} daempede dage, "
                      f"{len(serie_f)} fulde (kraever {_AB_MIN_DAGE})")

    snit_d = sum(serie_d) / len(serie_d)
    snit_f = sum(serie_f) / len(serie_f)
    # Taersklen er stoejen selv, ikke et oenske — samme regel som batch-maalingen
    # — men med et gulv, saa en tilfaeldigt lille spredning ikke goer enhver
    # forskel til et fund.
    stoej = max(_spredning(serie_d), _spredning(serie_f), _AB_STOEJ_GULV)
    forskel = snit_d - snit_f
    linje = (f"runder/run: daempet {snit_d:.2f} mod fuld {snit_f:.2f} "
             f"(forskel {forskel:+.2f}, taerskel {stoej:.2f})")
    if abs(forskel) > stoej:
        return "forskel", linje
    return None, linje


def _besked(dom: str, snit: float) -> tuple[str, str]:
    retning = "landede" if dom == "landede" else "gik den gale vej"
    titel = f"Batch-maalingen {retning}: {snit:.2f} vaerktoejer pr. runde"
    tekst = (
        "[SYSTEM — IKKE FRA BJOERN] Automatisk maaling, ikke skrevet af et menneske.\n\n"
        f"Instruktionen om at batche uafhaengige vaerktoejskald blev deployet 5/10-2026 "
        f"(720d3a607) med basislinjen 1,54 +/- 0,10 vaerktoejer pr. runde, maalt over "
        f"15 dage FOER deployet.\n\n"
        f"Tre-dages-snittet er nu {snit:.2f}, altsaa "
        f"{'over 1,64' if dom == 'landede' else 'under 1,44'} — uden for stoejgulvet.\n\n"
        f"Hele serien: scripts/maal_vaerktoejer_pr_runde.py --dage 14 (koer paa CT105).\n"
        f"Baggrunden: hvert vaerktoejskald koster en runde, og en runde koster ~7,7 s."
    )
    return titel, tekst


def _ab_besked(dom: str, linje: str) -> tuple[str, str, str]:
    """(ref, titel, tekst). Ref'et er stabilt pr. dom, saa hver dom siges ÉN gang."""
    if dom == "knappen_virker_ikke":
        titel = "Raesonnerings-A/B maaler ikke det det tror"
        krop = (
            "Den daempede arm raesonnerer stadig, saa knappen blev ikke drejet. "
            "Et resultat herfra ville vise «ingen forskel» af den forkerte grund.\n\n"
            f"{linje}\n\n"
            "Tjek `raesonnering_daempet_procent` i runtime.json og at "
            "`daemp_krop` naas i foelge-runderne."
        )
    else:
        titel = "Raesonnerings-A/B: der ER en forskel paa armene"
        krop = (
            "Runder pr. run skiller sig nu ud mellem armene ud over "
            "dag-til-dag-spredningen. Flere runder i den daempede arm betyder "
            "at han famler mere uden raesonnering; faerre betyder at "
            "raesonneringen ikke bar sin vaegt.\n\n"
            f"{linje}\n\n"
            "Hele billedet: scripts/maal_raesonnering_ab.py --dage 14 (paa CT105). "
            "`raesonnering_daempet_procent = 0` slukker forsoeget."
        )
    tekst = ("[SYSTEM — IKKE FRA BJOERN] Automatisk maaling, ikke skrevet af et "
             "menneske.\n\n" + krop)
    return f"raesonnering-ab:{dom}", titel, tekst


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DB_PATH)
    ap.add_argument("--toer", action="store_true", help="maal og print, notificer ikke")
    args = ap.parse_args()

    if not args.db.exists():
        print(f"ingen database paa {args.db}", file=sys.stderr)
        return 2

    serie = dagsserie(args.db, 14)
    dom, snit, taellende = vurder(serie)
    arme = armdata(args.db, dage=14, siden=AB_DEPLOY)
    ab_dom, ab_linje = vurder_ab(arme)
    nu = datetime.now(UTC).isoformat(timespec="seconds")
    linje = {"ts": nu, "snit_3d": snit, "taellende_dage": taellende, "dom": dom,
             "basislinje": BASISLINJE, "spredning": SPREDNING,
             "ab_dom": ab_dom, "ab": ab_linje,
             "ab_runder": {a: b["runder"] for a, b in arme.items()}}

    if not args.toer:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(linje, ensure_ascii=False) + "\n")

    print(f"{nu} batch: snit={snit} dage={taellende} dom={dom or 'i stoejen'}")
    print(f"{nu} a/b  : {ab_linje} dom={ab_dom or 'i stoejen'}")

    beskeder: list[tuple[str, str, str]] = []
    if dom is not None:
        titel, tekst = _besked(dom, float(snit))
        beskeder.append((f"vaerktoej-batch:{dom}", titel, tekst))
    if ab_dom is not None:
        beskeder.append(_ab_besked(ab_dom, ab_linje))

    if not beskeder:
        return 0
    if args.toer:
        for ref, titel, _ in beskeder:
            print(f"VILLE NOTIFICERE [{ref}]: {titel}")
        return 0

    from core.identity.owner_resolver import owner_user_id
    from core.services import notifikationer
    for ref, titel, tekst in beskeder:
        nid = notifikationer.opret(
            user_id=owner_user_id(), slags="maaling",
            kilde="batch_maaling_monitor", titel=titel, tekst=tekst, ref=ref,
        )
        print(f"{nu} notifikation {ref} = {nid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
