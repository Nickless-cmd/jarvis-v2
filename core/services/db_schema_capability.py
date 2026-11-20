"""database-skema opslag — fra selvrapport til måling.

## Hvorfor den findes

MÅLT 20/11-2026: domænet «database-skema opslag» stod på 0,40 i 1.002
vektorer med præcis ÉN selvrapporteret flytning (0,40 → 0,44). Ingen mekanisk
måling bag. Læringsplanen gjorde det derfor til et mål der hverken kunne
arbejdes med eller lukkes — samme familie som `face recognition` (0,35 i alle
1.011 vektorer) og `souls-build analyse` (0,45 → 0,38 og så stille).

## Hvad der måles — og hvad der IKKE måles

Ikke «er jeg god til SQL». Det spørgsmål har ingen deterministisk sandhed, og
et tal derpå ville være endnu en selvrapport.

Det der KAN måles er den fejl jeg faktisk lavede to gange natten til
20/11-2026: jeg gættede en kolonne — `costs.timestamp` — som ikke findes.
Den heder `created_at`. Kaldet fejlede, og jeg måtte køre det om.

Derfor: **to uafhængige læsninger af samme skema skal give samme svar.**

1. `PRAGMA table_info(<tabel>)` — SQLites egen beskrivelse.
2. `SELECT * FROM <tabel> LIMIT 0` → `cursor.description` — hvad forespørgsels-
   planlæggeren faktisk mener tabellen indeholder.

Er de uenige, lyver den ene vej, og et opslag efter den ville gætte.

Dertil en negativ kontrol: en kolonne der ikke findes SKAL give en fejl.
Ellers fanger opslaget ingenting, og så er det ikke et opslag — det er en
streng der altid siger ja.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)

#: Domænet i `confidence_by_domain`. Stavningen SKAL matche vektoren, ellers
#: skrives der et nyt domæne ved siden af det gamle.
DOMAIN = "database-skema opslag"

#: Et grønt run beviser det målte, ikke det umålte. Samme loft som
#: `desk_render_capability._CAP`: et instrumentelt run må ikke gøre et domæne
#: «færdigt».
_CAP = 0.85

#: Kolonnenavn der med garanti ikke findes. Skal give `OperationalError`.
_FALSK_KOLONNE = "kolonne_der_ikke_findes_9f3a"


def _quoted(name: str) -> str:
    """Tabelnavn som dobbelt-citeret identifier, med intern citering escaped."""
    return '"' + str(name).replace('"', '""') + '"'


def measure(*, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Mål om skema-opslaget giver samme svar ad to uafhængige veje.

    `conn` er sømmens test-punkt: givet en forbindelse måles DER. Uden den
    åbnes den levende base read-only — aldrig skrive-tilstand, så målingen
    ikke kan låse for uvicorn.
    """
    own = conn is None
    if own:
        try:
            from core.runtime.db_core import DB_PATH

            conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        except (sqlite3.Error, ImportError) as exc:  # registreres som afvigelse i resultatet — ikke slugt
            return {"measured": False, "reason": f"kunne ikke åbne basen: {exc}"}

    assert conn is not None
    try:
        try:
            tabeller = [
                str(r[0])
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
            ]
        except sqlite3.Error as exc:  # registreres som afvigelse i resultatet — ikke slugt
            return {"measured": False, "reason": f"sqlite_master uleselig: {exc}"}

        tabeller = [t for t in tabeller if not t.startswith("sqlite_")]
        if not tabeller:
            # Tom tabel-liste betyder forkert basesti, ikke tom base.
            return {"measured": False, "reason": "ingen tabeller — forkert basesti?"}

        afvigelser: list[str] = []
        tjekket = 0
        for tabel in tabeller:
            q = _quoted(tabel)
            try:
                pragma = [str(r[1]) for r in conn.execute(f"PRAGMA table_info({q})")]
            except sqlite3.Error as exc:  # registreres som afvigelse i resultatet — ikke slugt
                afvigelser.append(f"{tabel}: PRAGMA fejlede: {exc}")
                continue
            try:
                cur = conn.execute(f"SELECT * FROM {q} LIMIT 0")
                beskrivelse = [str(d[0]) for d in (cur.description or [])]
            except sqlite3.Error as exc:  # registreres som afvigelse i resultatet — ikke slugt
                afvigelser.append(f"{tabel}: SELECT LIMIT 0 fejlede: {exc}")
                continue
            tjekket += 1
            if pragma != beskrivelse:
                afvigelser.append(
                    f"{tabel}: PRAGMA={pragma[:8]} vs SELECT={beskrivelse[:8]}"
                )

        if tjekket == 0:
            return {
                "measured": False,
                "reason": "ingen tabel kunne læses ad begge veje",
                "mismatches": afvigelser[:5],
            }

        # Negativ kontrol: findes den falske kolonne alligevel, fanger opslaget
        # intet — og så er en «grøn» måling værdiløs.
        negativ_ok = False
        try:
            conn.execute(
                f"SELECT {_FALSK_KOLONNE} FROM {_quoted(tabeller[0])} LIMIT 0"
            )
        except sqlite3.Error:  # registreres som afvigelse i resultatet — ikke slugt
            negativ_ok = True

        ok = not afvigelser and negativ_ok
        confidence = round(_CAP, 3) if ok else round(_CAP * tjekket / (tjekket + len(afvigelser)), 3)
        if not negativ_ok:
            confidence = min(confidence, 0.5)
        return {
            "measured": True,
            "ok": ok,
            "tables_checked": tjekket,
            "tables_ok": tjekket - len(afvigelser),
            "mismatches": afvigelser[:10],
            "negative_control_ok": negativ_ok,
            "confidence": confidence,
            "cap": _CAP,
        }
    finally:
        if own:
            try:
                conn.close()
            except sqlite3.Error:  # harmloes: forbindelsen er allerede lukket eller aldrig aabnet
                pass


def record(*, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Mål og skriv resultatet ind i domænet. Ét kald = én målt sandhed."""
    from core.services.capability_measurement import set_domain_confidence

    result = measure(conn=conn)
    if not result.get("measured"):
        return result  # intet målt -> intet skrevet. Tavshed er ikke 0,40.

    evidence = (
        f"{result['tables_ok']}/{result['tables_checked']} tabeller: PRAGMA "
        f"table_info og SELECT-beskrivelse gav samme kolonneliste; "
        f"negativ-kontrol {'afviste' if result['negative_control_ok'] else 'FANGEDE IKKE'} "
        f"en falsk kolonne"
    )
    result["record"] = set_domain_confidence(
        DOMAIN, float(result["confidence"]), evidence=evidence
    )
    return result
