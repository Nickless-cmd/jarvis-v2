"""Lageret bag indbakken: `inbox_items`.

Opgave 1 i `docs/superpowers/specs/2026-10-03-indbakke-som-kontrolflade-design.md`.

Hvorfor en EGEN tabel, og ikke `session_inbox`:
`session_inbox` er en **leveringskø**. `flush_session` sætter
`status='delivered'`, hvorefter `pending_for_session` ikke længere viser posten
— og «leveret» er ikke «afgjort». En post skal kunne stå åben efter levering,
efter en procesgenstart og uden en aktiv session, indtil nogen træffer en
afgørelse om den. Derfor en separat, idempotent kvittering.

Tre ting i skemaet er valgt mod målte fejl i huset:

* **Ensure-én-gang-per-proces.** `CREATE TABLE IF NOT EXISTS` tager eksklusiv
  lås. Målt 9/9-2026: en ensure-funktion kaldt pr. brugerbesked fra en
  daemon-tråd gav `sqlite3.OperationalError: database is locked` med ~50 %
  frekvens i suiten, fordi en samtidig `INSERT INTO chat_messages` ikke kunne
  få låsen inden `busy_timeout`. Rettelsen (ensure én gang pr. proces) stod som
  en separat opgave for den gamle tabel; den nye tabel får den fra starten frem
  for at arve fejlen.
* **Ingen payload.** Posten bærer sti OG størrelse, aldrig indhold. Et jobs
  output kan være 112 kB; lander det her, lander det i promptens hale, og så er
  kontrolfladen blevet den byrde den skulle lette.
* **Bruger er altid eksplicit.** Uden bruger-id spørges der `1 = 0` — ingen
  liste over alle brugere. Husstanden har flere brugere, og de andres
  workspaces er krypterede; en indbakke der blander dem er et databrud.
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime
from typing import Any, Final

from core.runtime.db_core import connect

# Åben = kan stadig gate (hvis ejeren er verificeret). Alt andet er terminalt.
STATUS_AABEN: Final[str] = "aaben"
STATUS_DONE: Final[str] = "done"
STATUS_DROP: Final[str] = "drop"
#: Opgave 8: posten døde af sig selv. Terminal, ikke en sletning.
STATUS_UDLOEBET: Final[str] = "udloebet"
#: Opgave 9: kilden meldte sig færdig. En NEDGRADERING — beviset slettes ikke.
STATUS_AFSLUTTET_AF_KILDE: Final[str] = "afsluttet_af_kilde"

TERMINALE_STATUSSER: Final[frozenset[str]] = frozenset({
    STATUS_DONE, STATUS_DROP, STATUS_UDLOEBET, STATUS_AFSLUTTET_AF_KILDE,
})

#: `jarvis` = verificeret som hans eget arbejde, må gate. `huset` = daemon,
#: heartbeat, recurring — må oprette, aldrig gate. `ukendt` = proveniensen kunne
#: ikke bevises; synlig, men aldrig blokerende.
EJER_JARVIS: Final[str] = "jarvis"
EJER_HUSET: Final[str] = "huset"
EJER_UKENDT: Final[str] = "ukendt"

_skema_klar = False
_skema_laas = threading.Lock()


def _nu() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_skema(conn: sqlite3.Connection) -> None:
    """DDL ÉN gang pr. proces — se modulets docstring om den eksklusive lås."""
    global _skema_klar
    if _skema_klar:
        return
    with _skema_laas:
        if _skema_klar:  # en anden tråd kom først
            return
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inbox_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bruger_id TEXT NOT NULL,
                kildetype TEXT NOT NULL,
                kilde_id TEXT NOT NULL,
                oprettende_run_id TEXT NOT NULL DEFAULT '',
                verificeret_ejer TEXT NOT NULL DEFAULT 'ukendt',
                kraever_handling INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'aaben',
                beskrivelse TEXT NOT NULL DEFAULT '',
                output_sti TEXT NOT NULL DEFAULT '',
                output_bytes INTEGER,
                paamindelser INTEGER NOT NULL DEFAULT 0,
                sidste_paamindelse_at TEXT NOT NULL DEFAULT '',
                sidste_paamindelse_tur TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                afgjort_at TEXT NOT NULL DEFAULT '',
                afgjort_grund TEXT NOT NULL DEFAULT '',
                UNIQUE (bruger_id, kildetype, kilde_id)
            )
            """
        )
        # Visningen spørger altid «åbne poster for DENNE bruger», og gaten
        # spørger det samme. Indekset bærer bruger først, fordi det er den
        # kolonne der ALDRIG er fri.
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_inbox_items_bruger_status
            ON inbox_items(bruger_id, status, id DESC)
            """
        )
        _skema_klar = True


def _post_fra_raekke(r: sqlite3.Row) -> dict[str, Any]:
    """Rækken som en typet post. `output_bytes` bevarer sin NULL.

    `None` og `0` betyder IKKE det samme: `0 B` er en ægte tom fil, mens `None`
    er «filen er væk, størrelsen kan ikke oplyses». Mappes de sammen, kan
    visningen ikke skelne dem — og så står «0 B» hvor der burde stå at
    artefaktet er forsvundet.
    """
    b = r["output_bytes"]
    return {
        "id": str(r["kilde_id"]),
        "bruger_id": str(r["bruger_id"]),
        "kildetype": str(r["kildetype"]),
        "kilde_id": str(r["kilde_id"]),
        "oprettende_run_id": str(r["oprettende_run_id"] or ""),
        "verificeret_ejer": str(r["verificeret_ejer"] or EJER_UKENDT),
        "kraever_handling": bool(r["kraever_handling"]),
        "status": str(r["status"]),
        "beskrivelse": str(r["beskrivelse"] or ""),
        "output_sti": str(r["output_sti"] or ""),
        "output_bytes": None if b is None else int(b),
        "paamindelser": int(r["paamindelser"] or 0),
        "sidste_paamindelse_at": str(r["sidste_paamindelse_at"] or ""),
        "sidste_paamindelse_tur": str(r["sidste_paamindelse_tur"] or ""),
        "created_at": str(r["created_at"] or ""),
        "afgjort_at": str(r["afgjort_at"] or ""),
        "afgjort_grund": str(r["afgjort_grund"] or ""),
    }


def opret_eller_hent(
    *,
    bruger_id: str,
    kildetype: str,
    kilde_id: str,
    oprettende_run_id: str = "",
    verificeret_ejer: str = EJER_UKENDT,
    kraever_handling: bool = False,
    beskrivelse: str = "",
    output_sti: str = "",
    output_bytes: int | None = None,
) -> dict[str, Any]:
    """Idempotent registrering. Findes posten, returneres DEN — urørt.

    Genlevering af samme notifikation må ikke nulstille påmindelsestælleren
    eller en truffet afgørelse. `INSERT OR IGNORE` plus et efterfølgende opslag
    gør begge dele i én runde uden at læse-skrive-kapløbe: taber vi kapløbet om
    indsættelsen, finder opslaget den andens række, hvilket er netop det
    idempotente svar.
    """
    bruger_id = str(bruger_id or "").strip()
    kilde_id = str(kilde_id or "").strip()
    kildetype = str(kildetype or "").strip()
    if not bruger_id or not kilde_id or not kildetype:
        return {"status": "fejl", "error": "bruger_id, kildetype og kilde_id kraeves"}
    with connect() as conn:
        _ensure_skema(conn)
        conn.execute(
            """
            INSERT OR IGNORE INTO inbox_items (
                bruger_id, kildetype, kilde_id, oprettende_run_id,
                verificeret_ejer, kraever_handling, status, beskrivelse,
                output_sti, output_bytes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (bruger_id, kildetype, kilde_id, str(oprettende_run_id or ""),
             str(verificeret_ejer or EJER_UKENDT), 1 if kraever_handling else 0,
             STATUS_AABEN, str(beskrivelse or ""), str(output_sti or ""),
             output_bytes, _nu()),
        )
        r = conn.execute(
            "SELECT * FROM inbox_items WHERE bruger_id = ? AND kildetype = ? "
            "AND kilde_id = ?",
            (bruger_id, kildetype, kilde_id),
        ).fetchone()
    if r is None:
        # Skrivningen fejlede uden at kaste. Det er husets hyppigste fejlform:
        # en fejl der bliver en vaerdi man ikke kan skelne fra et lovligt svar.
        # Her bliver den en TYPET fejl, og kalderen skal laese den.
        return {"status": "fejl", "error": "posten kunne ikke skrives eller laeses"}
    return {"status": "ok", "post": _post_fra_raekke(r)}


def hent(*, bruger_id: str, kilde_id: str) -> dict[str, Any] | None:
    """Én post for ÉN bruger. Ingen bruger ⇒ None, aldrig en anden brugers."""
    bruger_id = str(bruger_id or "").strip()
    kilde_id = str(kilde_id or "").strip()
    if not bruger_id or not kilde_id:
        return None
    with connect() as conn:
        _ensure_skema(conn)
        r = conn.execute(
            "SELECT * FROM inbox_items WHERE bruger_id = ? AND kilde_id = ?",
            (bruger_id, kilde_id),
        ).fetchone()
    return None if r is None else _post_fra_raekke(r)


def liste(
    *,
    bruger_id: str,
    kun_aabne: bool = True,
    maks: int = 500,
) -> list[dict[str, Any]]:
    """Poster for ÉN bruger. Tom bruger ⇒ tom liste, ALDRIG alle brugeres.

    `list_pending_for_current_user()` læser alle ved tom kontekst, og
    `list_wakeups()` er global. Den slags implicit kontekst er grunden til at
    denne funktion kræver bruger-id som nøgleord uden standardværdi.
    """
    bruger_id = str(bruger_id or "").strip()
    if not bruger_id:
        return []
    sql = "SELECT * FROM inbox_items WHERE bruger_id = ?"
    p: list[Any] = [bruger_id]
    if kun_aabne:
        sql += " AND status = ?"
        p.append(STATUS_AABEN)
    sql += " ORDER BY id ASC LIMIT ?"
    p.append(max(int(maks), 1))
    with connect() as conn:
        _ensure_skema(conn)
        rows = conn.execute(sql, tuple(p)).fetchall()
    return [_post_fra_raekke(r) for r in rows]


def afgoer(
    *,
    bruger_id: str,
    kilde_id: str,
    ny_status: str,
    grund: str = "",
) -> dict[str, Any]:
    """Sæt en terminal status. Idempotent: en allerede afgjort post ændres IKKE.

    Returnerer typet: `ok` (vi afgjorde den nu), `allerede` (den var afgjort —
    med den status den HAR, ikke den vi bad om), `ukendt` (ingen sådan post for
    denne bruger) eller `fejl`. Aldrig prosa, og `ukendt` må aldrig komme ud som
    en succes: et ukendt id der melder «ok» er præcis den fejlform huset rammer
    oftest.
    """
    bruger_id = str(bruger_id or "").strip()
    kilde_id = str(kilde_id or "").strip()
    if ny_status not in TERMINALE_STATUSSER:
        return {"status": "fejl", "error": f"ikke en terminal status: {ny_status}"}
    if not bruger_id or not kilde_id:
        return {"status": "fejl", "error": "bruger_id og kilde_id kraeves"}
    with connect() as conn:
        _ensure_skema(conn)
        r = conn.execute(
            "SELECT * FROM inbox_items WHERE bruger_id = ? AND kilde_id = ?",
            (bruger_id, kilde_id),
        ).fetchone()
        if r is None:
            return {"status": "ukendt", "id": kilde_id}
        nuv = str(r["status"])
        if nuv in TERMINALE_STATUSSER:
            return {"status": "allerede", "id": kilde_id, "havde": nuv}
        # `status = 'aaben'` i WHERE gør skrivningen atomar mod en samtidig
        # afgørelse: taber vi kapløbet, rammer UPDATE nul rækker, og vi melder
        # `allerede` frem for at overskrive den andens afgørelse.
        cur = conn.execute(
            "UPDATE inbox_items SET status = ?, kraever_handling = 0, "
            "afgjort_at = ?, afgjort_grund = ? "
            "WHERE bruger_id = ? AND kilde_id = ? AND status = ?",
            (ny_status, _nu(), str(grund or ""), bruger_id, kilde_id, STATUS_AABEN),
        )
        if cur.rowcount == 0:
            r2 = conn.execute(
                "SELECT status FROM inbox_items WHERE bruger_id = ? AND kilde_id = ?",
                (bruger_id, kilde_id),
            ).fetchone()
            return {"status": "allerede", "id": kilde_id,
                    "havde": str(r2["status"]) if r2 else "ukendt"}
    return {"status": "ok", "id": kilde_id, "ny_status": ny_status}


def noter_paamindelse(*, bruger_id: str, kilde_id: str, tur: str) -> dict[str, Any]:
    """Tæl ÉN leveret påmindelse. Samme tur to gange tæller ÉN gang.

    Tælleren skal være durabel og per post: en volatil tæller nulstillede sig
    ved en procesgenstart, og påmindelsen kom aldrig. Og `tur`-nøglen findes
    fordi trin 1 ikke må fyre i hver runde — uden den ville en enkelt tur kunne
    tælle sig op til tærsklen alene og springe hele den høflige anmodning over.
    """
    bruger_id = str(bruger_id or "").strip()
    kilde_id = str(kilde_id or "").strip()
    tur = str(tur or "").strip()
    if not bruger_id or not kilde_id or not tur:
        return {"status": "fejl", "error": "bruger_id, kilde_id og tur kraeves"}
    with connect() as conn:
        _ensure_skema(conn)
        cur = conn.execute(
            "UPDATE inbox_items SET paamindelser = paamindelser + 1, "
            "sidste_paamindelse_at = ?, sidste_paamindelse_tur = ? "
            "WHERE bruger_id = ? AND kilde_id = ? AND status = ? "
            "AND sidste_paamindelse_tur != ?",
            (_nu(), tur, bruger_id, kilde_id, STATUS_AABEN, tur),
        )
        if cur.rowcount == 0:
            r = conn.execute(
                "SELECT * FROM inbox_items WHERE bruger_id = ? AND kilde_id = ?",
                (bruger_id, kilde_id),
            ).fetchone()
            if r is None:
                return {"status": "ukendt", "id": kilde_id}
            if str(r["sidste_paamindelse_tur"]) == tur:
                return {"status": "samme_tur", "id": kilde_id,
                        "paamindelser": int(r["paamindelser"] or 0)}
            return {"status": "ikke_aaben", "id": kilde_id, "havde": str(r["status"])}
        r = conn.execute(
            "SELECT paamindelser FROM inbox_items WHERE bruger_id = ? AND kilde_id = ?",
            (bruger_id, kilde_id),
        ).fetchone()
    return {"status": "ok", "id": kilde_id,
            "paamindelser": int(r["paamindelser"]) if r else 0}
