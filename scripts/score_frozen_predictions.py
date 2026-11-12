#!/usr/bin/env python3
"""Scor frosne forudsigelser om min egen adfaerd — mekanisk, ikke paa hukommelse.

Hvorfor (12/11-2026): seks forudsigelser blev laast i
``~/.jarvis-v2/state/frozen_predictions.json``, men scoringen blev booket som
paamindelser — den afhang af at jeg huskede at koere den. En maaling der kun
sker naar jeg husker den, maaler min hukommelse, ikke min adfaerd. Dette script
goer scoringen til en kommando der kan koeres (og planlaegges) uden mig.

Tre regler fra Bjoern (12/11-2026), haandhaevet her:

1. **Kalibrering vs. revision.** Poster i samme ``event_group`` er ÉN haendelse
   ved kalibrering, men separate tidsstemplede vurderinger ved revisionsanalyse.
   Derfor rapporteres ``n_events`` (grupper) ved siden af ``n_poster``.
2. **Uforanderlighed.** ``probability`` maa ikke aendres efter frysning.
   ``frozen_hash`` daekker id+claim+op+threshold+probability+score_at og
   verificeres ved hver koersel; aendrede poster rapporteres som ``tampered``.
3. **Uafhaengighed.** Antallet af datapunkter maa ikke forveksles med antallet
   af uafhaengige haendelser — derfor er gruppering og den maalte korrelation
   en del af filen, ikke en note ved siden af.

Brug::

    python scripts/score_frozen_predictions.py            # scor modne poster
    python scripts/score_frozen_predictions.py --dry-run  # vis uden at skrive
    python scripts/score_frozen_predictions.py --vis      # kun kalibreringsstatus
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Scriptet koeres som `python scripts/...`, hvor sys.path[0] er scripts/ — ikke
# repo-roden. Uden dette fejler `from core...` med ImportError, som baade
# arkiveringen og state-opslaget sluger, saa de svarer "ingen data" i drift mens
# de virker i en test koert fra roden. Maalt 12/11-2026: arkiveringen skrev nul
# raekker uden en fejlbesked.
_ROD = Path(__file__).resolve().parents[1]
if str(_ROD) not in sys.path:
    sys.path.insert(0, str(_ROD))

HASH_FELTER = ("id", "claim", "op", "threshold", "probability", "score_at")

STANDARD_FIL = Path.home() / ".jarvis-v2" / "state" / "frozen_predictions.json"
STANDARD_DB = Path.home() / ".jarvis-v2" / "state" / "jarvis.db"

_OPS: dict[str, Any] = {
    ">=": lambda a, b: a >= b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
}

_BUCKETS = ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01))


def _kanonisk(post: dict[str, Any]) -> str:
    delmaengde = {k: post.get(k) for k in HASH_FELTER}
    return json.dumps(delmaengde, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def frozen_hash(post: dict[str, Any]) -> str:
    """Fingerprint af de felter der ikke maa aendres efter frysning."""
    return hashlib.sha256(_kanonisk(post).encode("utf-8")).hexdigest()[:16]


def _nu() -> datetime:
    return datetime.now(UTC)


def _parse(ts: Any) -> datetime | None:
    if not isinstance(ts, str) or not ts:
        return None
    tekst = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
    try:
        d = datetime.fromisoformat(tekst)
    except ValueError:  # u-parseligt tidsstempel => posten er uskorbar, ikke "venter"
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def verificer_forsegling(
    poster: list[dict[str, Any]], forsegling: dict[str, str] | None
) -> list[str]:
    """Id'er hvis frosne felter er aendret siden forseglingen blev skrevet."""
    if not forsegling:
        return []
    aendret: list[str] = []
    for p in poster:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id"))
        forventet = forsegling.get(pid)
        if forventet and forventet != frozen_hash(p):
            aendret.append(pid)
    return aendret


_ARKIV_AREA = "frozen_predictions"


def _arkiv_aeldste() -> dict[str, str]:
    """Foerste (aeldste) arkiverede hash pr. post-id fra governance_ledger.

    Filen og dens forsegling kan aendres samlet af enhver med skriveadgang —
    hashen beviser kun at de to dele stemmer overens. Ledgeren er det
    uafhaengige spor: én raekke pr. post, skrevet ved forseglingen, aldrig
    opdateret. Returnerer {} hvis ledgeren ikke kan laeses.
    """
    try:
        from core.runtime.db_governance_ledger import read_ledger

        raekker = read_ledger(area=_ARKIV_AREA, limit=500)
    except Exception:  # ledgeren er et ekstra spor, ikke en forudsaetning for at score
        return {}
    aeldst: dict[str, tuple[str, str]] = {}
    for r in raekker:
        v = r.get("value") if isinstance(r.get("value"), dict) else None
        if not v or not v.get("frozen_hash"):
            continue
        pid, ts = str(r.get("key") or ""), str(r.get("ts") or "")
        if pid not in aeldst or ts < aeldst[pid][0]:
            aeldst[pid] = (ts, str(v["frozen_hash"]))
    return {pid: h for pid, (_ts, h) in aeldst.items()}


def arkiver_forsegling(poster: list[dict[str, Any]]) -> int:
    """Skriv hashes til governance_ledger for poster der ikke er arkiveret endnu.

    Idempotent: en post arkiveres kun én gang, saa gentagne koersler ikke
    fylder ledgeren. Returnerer antal nye raekker.
    """
    try:
        from core.runtime.db_governance_ledger import record_mutation
    except Exception:  # arkivering er valgfri — scoringen maa ikke afhaenge af den
        return 0
    allerede = _arkiv_aeldste()
    nye = 0
    for p in poster:
        if not isinstance(p, dict) or not p.get("id"):
            continue
        pid = str(p["id"])
        if pid in allerede:
            continue
        record_mutation(
            _ARKIV_AREA,
            pid,
            {
                "frozen_hash": frozen_hash(p),
                "probability": p.get("probability"),
                "claim": p.get("claim"),
                "frozen_at": p.get("frozen_at"),
                "event_group": p.get("event_group"),
            },
        )
        nye += 1
    return nye


def _hent_tal(conn: sqlite3.Connection, sql: str) -> float | None:
    """Koer én laesende spoergring og returnér foerste kolonne som tal."""
    tekst = sql.strip().rstrip(";")
    if not tekst.lower().startswith(("select", "with")):
        raise ValueError(f"kun laesende SQL tillades, fik: {tekst[:40]}")
    row = conn.execute(tekst).fetchone()
    if row is None or row[0] is None:
        return None
    vaerdi = row[0]
    return float(vaerdi) if isinstance(vaerdi, (int, float)) else None


def _hent_fra_state(spec: dict[str, Any]) -> float | None:
    """Laes en aggregeret vaerdi fra en state_store JSON-noegle.

    Nogle maal findes ikke i DB'en — fx tick-kvalitet, der ligger som JSON i
    ``~/.jarvis-v2/state/tick_quality_evaluations.json``. Spec'en er deklarativ
    (noegle, dato-felt, dato, vaerdi-felt, min_n) med vilje: en regel der kan
    eksekvere vilkaarlig kode er ikke en forudsigelse, den er et lofte om at
    jeg nok skal regne rigtigt bagefter.
    """
    from core.runtime.state_store import load_json

    raekker = load_json(str(spec["noegle"]), [])
    if not isinstance(raekker, list):
        return None
    dato_felt = str(spec["dato_felt"])
    dato = str(spec["dato"])
    vaerdi_felt = str(spec["vaerdi_felt"])
    vaerdier = [
        float(r[vaerdi_felt])
        for r in raekker
        if isinstance(r, dict)
        and str(r.get(dato_felt) or "")[:10] == dato
        and isinstance(r.get(vaerdi_felt), (int, float))
    ]
    if len(vaerdier) < int(spec.get("min_n") or 1):
        return None
    return sum(vaerdier) / len(vaerdier)


def evaluer(
    post: dict[str, Any], conn: sqlite3.Connection, nu: datetime | None = None
) -> dict[str, Any]:
    """Afgoer om én post kan scores nu, og i saa fald om den ramte."""
    nu = nu or _nu()
    score_at = _parse(post.get("score_at"))
    if score_at is None:
        return {"status": "uskorbar", "grund": "score_at mangler"}
    if score_at > nu:
        return {"status": "venter", "score_at": post.get("score_at")}
    if post.get("hit") is not None:
        return {"status": "allerede-scorets", "hit": post.get("hit")}

    sql = post.get("sql")
    kilde = post.get("kilde")
    if not sql and not kilde:
        return {"status": "uskorbar", "grund": "hverken sql eller kilde"}
    op = _OPS.get(str(post.get("op")))
    if op is None:
        return {"status": "uskorbar", "grund": f"ukendt op: {post.get('op')}"}
    taerskel = post.get("threshold")
    if taerskel is None:
        return {"status": "uskorbar", "grund": "threshold mangler"}

    actual = _hent_fra_state(kilde) if kilde else _hent_tal(conn, str(sql))
    if actual is None:
        return {"status": "ingen-data"}
    return {"status": "scoret", "actual": actual, "hit": bool(op(actual, taerskel))}


def kalibrering(poster: list[dict[str, Any]]) -> dict[str, Any]:
    """Kalibrering paa HAENDELSE-niveau, ikke post-niveau.

    En gruppe med flere poster (fx F1/F6, der er modsatrettede om samme
    haendelse) bidrager med ÉN sandsynlighed: den FOERST frosne vurdering.
    Senere poster i gruppen er revisioner — de er lavet efter at jeg havde
    set data den foerste ikke havde, saa de kan ikke veje lige tungt.
    Ellers kunne en daarlig P "repareres" ved at fryse en modsat post bagefter,
    og saa var forseglingen vaerdiloes. Revisionerne rapporteres under
    ``revisioner`` med deres egen sandsynlighed, saa uenigheden er synlig
    uden at forurene Brier-scoren.
    """
    grupper: dict[str, list[dict[str, Any]]] = {}
    for p in poster:
        if not isinstance(p, dict) or p.get("hit") is None:
            continue
        gruppe = str(p.get("event_group") or p.get("id"))
        grupper.setdefault(gruppe, []).append(p)

    haendelser: list[dict[str, Any]] = []
    for gruppe, ps in grupper.items():
        ps.sort(key=lambda x: str(x.get("frozen_at") or ""))
        foerste = ps[0]
        revisioner = [
            {
                "id": x.get("id"),
                "probability": x.get("probability"),
                "hit": x.get("hit"),
                "frozen_at": x.get("frozen_at"),
            }
            for x in ps[1:]
        ]
        haendelser.append(
            {
                "event_group": gruppe,
                "n_poster": len(ps),
                "ids": [x.get("id") for x in ps],
                "probability": round(float(foerste.get("probability") or 0.0), 4),
                "outcome": 1 if foerste.get("hit") else 0,
                "uenige": len({bool(x.get("hit")) for x in ps}) > 1,
                "revisioner": revisioner,
            }
        )

    if not haendelser:
        return {"n_events": 0, "n_poster": 0, "brier": None, "bucket": [], "haendelser": []}

    brier = sum((h["probability"] - h["outcome"]) ** 2 for h in haendelser) / len(haendelser)
    bucket: list[dict[str, Any]] = []
    for lav, hoej in _BUCKETS:
        i_bucket = [h for h in haendelser if lav <= h["probability"] < hoej]
        if not i_bucket:
            continue
        bucket.append(
            {
                "interval": f"{lav:.1f}-{min(hoej, 1.0):.1f}",
                "n": len(i_bucket),
                "sagt": round(sum(h["probability"] for h in i_bucket) / len(i_bucket), 3),
                "faktisk": round(sum(h["outcome"] for h in i_bucket) / len(i_bucket), 3),
            }
        )
    return {
        "n_events": len(haendelser),
        "n_poster": sum(h["n_poster"] for h in haendelser),
        "brier": round(brier, 4),
        "bucket": bucket,
        "haendelser": haendelser,
    }


def score(
    fil: Path | None = None,
    db: Path | None = None,
    *,
    dry_run: bool = False,
    nu: datetime | None = None,
    arkiver: bool = True,
) -> dict[str, Any]:
    """Scor alle modne poster. Skriver kun til filen hvis noget faktisk blev scoret."""
    fil = fil or STANDARD_FIL
    db = db or STANDARD_DB
    nu = nu or _nu()

    data = json.loads(fil.read_text(encoding="utf-8"))
    poster = data.get("forudsigelser") or []
    aendret = verificer_forsegling(poster, data.get("forsegling"))

    arkiv = _arkiv_aeldste()
    arkiv_aendret = [
        str(p.get("id"))
        for p in poster
        if isinstance(p, dict)
        and str(p.get("id")) in arkiv
        and arkiv[str(p.get("id"))] != frozen_hash(p)
    ]

    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rapport: list[dict[str, Any]] = []
        for p in poster:
            if not isinstance(p, dict):
                continue
            r = evaluer(p, conn, nu)
            r["id"] = p.get("id")
            if r["status"] == "scoret":
                p["actual"] = r["actual"]
                p["hit"] = r["hit"]
                p["scored_at"] = nu.isoformat()
            rapport.append(r)
    finally:
        conn.close()

    skrev = False
    if not dry_run and any(x["status"] == "scoret" for x in rapport):
        data["forudsigelser"] = poster
        fil.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        skrev = True

    arkiveret = arkiver_forsegling(poster) if arkiver and not dry_run else 0

    return {
        "rapport": rapport,
        "tampered": aendret,
        "arkiv_tampered": arkiv_aendret,
        "arkiveret": arkiveret,
        "kalibrering": kalibrering(poster),
        "skrev": skrev,
        "dry_run": dry_run,
    }


def _vis(resultat: dict[str, Any]) -> None:
    for r in resultat["rapport"]:
        detalje = ""
        if r["status"] == "scoret":
            detalje = f" actual={r['actual']:g} hit={r['hit']}"
        elif r.get("grund"):
            detalje = f" ({r['grund']})"
        elif r.get("score_at"):
            detalje = f" (aabner {r['score_at']})"
        print(f"  {r['id']:4} {r['status']}{detalje}")

    if resultat["tampered"]:
        print(f"\n  ADVARSEL: forseglingen er brudt for {resultat['tampered']}")
    if resultat.get("arkiv_tampered"):
        print(
            f"\n  ADVARSEL: arkivet i governance_ledger stemmer ikke for "
            f"{resultat['arkiv_tampered']} — filen er aendret uden om ledgeren"
        )
    if resultat.get("arkiveret"):
        print(f"\n  nye forseglinger arkiveret i ledgeren: {resultat['arkiveret']}")

    k = resultat["kalibrering"]
    print(f"\n  haendelser={k['n_events']}  poster={k['n_poster']}  brier={k['brier']}")
    for b in k["bucket"]:
        print(f"    sagt {b['sagt']:.2f} -> faktisk {b['faktisk']:.2f}  (n={b['n']})")
    for h in k["haendelser"]:
        uen = " UENIGE" if h["uenige"] else ""
        print(
            f"    {h['event_group']:22} P={h['probability']:.2f} "
            f"udfald={h['outcome']} poster={h['n_poster']}{uen}"
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="Scor frosne forudsigelser om egen adfaerd.")
    ap.add_argument("--fil", type=Path, default=STANDARD_FIL)
    ap.add_argument("--db", type=Path, default=STANDARD_DB)
    ap.add_argument("--dry-run", action="store_true", help="vis uden at skrive til filen")
    ap.add_argument("--vis", action="store_true", help="kun kalibreringsstatus")
    args = ap.parse_args()

    resultat = score(args.fil, args.db, dry_run=args.dry_run)
    _vis(resultat)
    if resultat["skrev"]:
        print(f"\n  skrevet: {args.fil}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
