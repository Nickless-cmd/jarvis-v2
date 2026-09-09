"""Projektions-runtime — rene, versionerede folder over session-ledgeren.

Spec: `docs/specs/2026-09-08-deepseek-harness-lessons-for-jarvis.md`, Fase 1.

## Hvad en projektion er, og hvad den ikke er

En projektion er en REN funktion af ledger-hændelser: `(tilstand, hændelse) →
tilstand`. Den må ikke læse andet, og den må ikke skrive andet end sit eget
resultat. Dét er hele grunden til at den kan genskabes fra ingenting — og
grunden til at et cache-tab aldrig kan ændre sandheden.

Gap G i spec'en beskriver hvad vi havde i stedet: projektions-TABELLER og en
TTL-cache, men ingen registrering, ingen version-invalidering, intet fælles
`as_of_seq` og ingen deterministisk genafspilning. En cache reducerer
poll-omkostning; den etablerer ikke projektions-semantik.

## Checkpointet og genafspilningen

Hver (session, projektion) har ét checkpoint: hvor langt er den foldet, og med
hvilken version af folden. To ting følger af det:

* **Version-skifte kasserer resultatet.** Ændrer folden sig, er den gamle
  udregning ikke længere den samme funktion af de samme hændelser. Så foldes
  der forfra fra sekvens 0 frem for at bygge videre på noget der blev til efter
  andre regler.

* **Et nedbrud mellem arbejdet og markøren må ikke fordoble noget.** Derfor er
  kontrakten at folden er IDEMPOTENT pr. hændelse: at køre den igen på en
  hændelse den allerede har set, må ikke ændre resultatet. Så er en gentagelse
  harmløs, og markøren behøver ikke være atomisk med arbejdet.

## Cache-fejl må ikke ændre sandhed

Kan checkpointet ikke læses, foldes der fra 0. Det er langsommere og altid
rigtigt. Det modsatte — at antage at man er længere fremme end man er — ville
tabe hændelser i stilhed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable

logger = logging.getLogger(__name__)

#: (tilstand, hændelse) → tilstand. Skal være ren og idempotent pr. hændelse.
Fold = Callable[[Any, dict[str, Any]], Any]


@dataclass(frozen=True)
class Projection:
    navn: str
    version: str
    fold: Fold
    #: Starttilstanden. Kaldes ved hver genfoldning, så to kørsler ikke deler
    #: et muterbart objekt — dét ville gøre folden urent uden at det kunne ses.
    start: Callable[[], Any]


_REGISTER: dict[str, Projection] = {}


def register(navn: str, *, version: str, fold: Fold,
             start: Callable[[], Any] = dict) -> None:
    """Registrér en projektion. Samme navn to gange er en fejl, ikke en erstatning.

    En stille erstatning ville betyde at hvilken fold der gælder afhænger af
    import-rækkefølgen — og dét er nøjagtig den slags dobbelt-sandhed
    registret findes for at forhindre.
    """
    n = str(navn or "").strip()
    if not n:
        raise ValueError("projektionen skal have et navn")
    if n in _REGISTER and _REGISTER[n].version != str(version):
        raise ValueError(f"projektionen {n!r} er allerede registreret med en anden version")
    _REGISTER[n] = Projection(navn=n, version=str(version), fold=fold, start=start)


def registered() -> list[str]:
    return sorted(_REGISTER)


def _unregister_all_for_tests() -> None:
    _REGISTER.clear()


# ── checkpoint ───────────────────────────────────────────────────────────

def _ensure_checkpoint_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projection_checkpoints (
            session_id TEXT NOT NULL,
            projection TEXT NOT NULL,
            version TEXT NOT NULL,
            as_of_seq INTEGER NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (session_id, projection)
        )
        """
    )


def checkpoint(session_id: str, navn: str) -> dict[str, Any] | None:
    """Hvor langt er denne projektion foldet for denne session?"""
    from core.runtime.db import connect
    try:
        with connect() as conn:
            _ensure_checkpoint_table(conn)
            row = conn.execute(
                "SELECT version, as_of_seq, updated_at FROM projection_checkpoints "
                "WHERE session_id = ? AND projection = ?",
                (str(session_id or ""), str(navn or "")),
            ).fetchone()
    except Exception:
        # Kan checkpointet ikke læses, foldes der fra 0. Langsommere og altid
        # rigtigt; det modsatte ville tabe hændelser i stilhed.
        logger.warning("projection_runtime: checkpoint utilgaengeligt", exc_info=True)
        return None
    if row is None:
        return None
    return {"version": str(row[0]), "as_of_seq": int(row[1]), "updated_at": str(row[2])}


def _gem_checkpoint(session_id: str, navn: str, version: str, as_of_seq: int) -> None:
    from core.runtime.db import connect
    try:
        with connect() as conn:
            _ensure_checkpoint_table(conn)
            conn.execute(
                "INSERT INTO projection_checkpoints "
                "(session_id, projection, version, as_of_seq, updated_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(session_id, projection) DO UPDATE SET "
                "version = excluded.version, as_of_seq = excluded.as_of_seq, "
                "updated_at = excluded.updated_at",
                (str(session_id), str(navn), str(version), int(as_of_seq),
                 datetime.now(UTC).isoformat()),
            )
    except Exception:
        # En tabt markør koster en genfoldning, ikke en forkert tilstand.
        logger.warning("projection_runtime: kunne ikke gemme checkpoint", exc_info=True)


# ── foldning ─────────────────────────────────────────────────────────────

def project(session_id: str, navn: str, *, force_refold: bool = False) -> dict[str, Any]:
    """Fold sessionens hændelser gennem projektionen og ryk markøren frem.

    Returnerer `{state, as_of_seq, refolded, events}` — `refolded` siger om der
    blev foldet fra 0 (ny projektion, version-skifte eller tabt markør).
    """
    from core.runtime.db_session_ledger import read_session_events

    p = _REGISTER.get(str(navn or ""))
    if p is None:
        raise KeyError(f"ukendt projektion: {navn!r}")

    cp = None if force_refold else checkpoint(session_id, p.navn)
    genfoldet = cp is None or cp["version"] != p.version
    fra = 0 if genfoldet else int(cp["as_of_seq"])

    tilstand = p.start()
    haendelser = read_session_events(session_id, from_seq=fra)
    seq = fra
    for e in haendelser:
        tilstand = p.fold(tilstand, e)
        seq = int(e["seq"])

    _gem_checkpoint(session_id, p.navn, p.version, seq)
    return {"state": tilstand, "as_of_seq": seq,
            "refolded": genfoldet, "events": len(haendelser)}


def snapshot(session_id: str, navne: list[str] | None = None) -> dict[str, Any]:
    """Fold FLERE projektioner og giv dem ÉT fælles `as_of_seq`.

    Spec'ens krav: «every multi-key snapshot has one `as_of_seq`». Uden det
    kunne to celler i samme øjebliksbillede beskrive to forskellige tidspunkter
    — og en læser ville ikke kunne se det.

    Skæringen er den LAVESTE af de foldede sekvenser. At vælge den højeste ville
    love mere end den mindst opdaterede celle kan holde.
    """
    valgte = [n for n in (navne or registered()) if n in _REGISTER]
    celler: dict[str, Any] = {}
    seqs: list[int] = []
    for n in valgte:
        r = project(session_id, n)
        celler[n] = r["state"]
        seqs.append(int(r["as_of_seq"]))
    return {"cells": celler, "as_of_seq": min(seqs) if seqs else 0}


def run_for_session(session_id: str, navne: list[str] | None = None) -> dict[str, Any]:
    """Kør alle registrerede projektioner for én session.

    Dette er det kald der gør en `ledger`-session brugbar. Uden det er
    `chat_messages` en projektion ingen genopbygger — og så ville de 61 læsere
    stille vise gammelt indhold efter et skifte. Ingen fejl, ingen tom skærm:
    bare en samtale der holdt op med at ændre sig.

    Kaldes fra `SessionHandle.flush()`, fordi handlet er den eneste sanktionerede
    vej til at skrive i en kanonisk ledger-session. Så gælder «hver append
    følges af en projektion» for enhver skriver der bruger den rigtige vej —
    frem for at være noget hvert kaldested skulle huske.
    """
    ud: dict[str, Any] = {}
    for n in (navne or registered()):
        try:
            r = project(session_id, n)
            ud[n] = {"as_of_seq": r["as_of_seq"], "events": r["events"]}
        except Exception as e:
            # Én projektion der fejler, må ikke stoppe de andre. Fejlen står i
            # svaret OG i loggen — en projektion der tier, er værre end en der
            # er bagud, fordi ingen kan se forskel på den og en der er ajour.
            logger.warning("projection_runtime: %r fejlede for %s", n, session_id,
                           exc_info=True)
            ud[n] = {"fejl": f"{type(e).__name__}: {e}"}
    return ud
