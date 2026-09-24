"""Jarvis' EGET forslag til Bjørns næste besked — skrevet i hans egen tur.

## Hvorfor denne tabel findes

Forslaget i komponisten blev født som en lille lokal model (qwen3:4b) der
læser Jarvis' seneste besked og gætter hvad Bjørn kunne skrive. Det er en
fremmed stemme i Jarvis' mund: linjen står i HANS skrivefelt, men ordene er
en andens.

Bjørn 24/9-2026: «i chatview er det dig selv der sætter ord på runderne...
det burde endelig osse være dig der kommer med forslag i composer?»

Pointen er rigtig, og mekanismen findes allerede: når en runde er ét kald og
Jarvis selv har skrevet beskrivelsen, nægter etiket-modellen at skrive noget —
HANS linje står alene. Det er den asymmetri der mangler i komponisten.

## Hvorfor det gemmes og ikke skrives direkte

Jarvis kan ikke skrive i et felt der endnu ikke er tomt — forslaget hører til
den NÆSTE besked, og den findes ikke mens han taler. Han lægger det derfor
ned mens han er i turen (`suggest_next_message`), og komponisten henter det
når feltet er tomt og svaret er færdigt.

## Hvorfor ÉN række pr. forslag, og hvorfor den forbruges

Forslaget hører til ÉN tur. Lå det og ventede, ville næste turs slutning
kunne gribe et forældet forslag — skrevet til en samtale der er kørt videre.
Derfor forbruges det ved læsning (`tag_forslag`): hentet er hentet, og næste
hentning falder tilbage til den lokale model. Et forslag der bliver hentet
to gange (to vinduer) giver ét rigtigt og ét fra qwen — det er den rigtige
pris, for det forkerte ville være at vise ham noget der ikke passer længere.
"""
from __future__ import annotations

import logging
from uuid import uuid4

from core.runtime.db_core import _now_iso, connect, skriv_med_genforsoeg

logger = logging.getLogger(__name__)

_TABEL = "composer_jarvis_forslag"

#: Et forslag er en hel besked, ikke et essay. Samme loft som den lokale
#: models output (`composer_suggest.MAKS_TEGN` er 80) — holdes her, så et
#: forslag fra Jarvis ikke kan fylde pladsholderen med et afsnit.
MAKS_TEGN: int = 120


def _sikr_tabel(conn) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_TABEL} (
            forslag_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            forslag TEXT NOT NULL,
            kilde_besked_id TEXT NOT NULL DEFAULT '',
            skrevet_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{_TABEL}_session "
        f"ON {_TABEL} (session_id, skrevet_at)"
    )


def _rens(tekst: str) -> str:
    """Én linje, uden omsluttende anførselstegn, afkortet ved et ordskel."""
    s = " ".join((tekst or "").split())
    for a, b in (('"', '"'), ("'", "'"), ("«", "»"), ("“", "”")):
        if len(s) >= 2 and s.startswith(a) and s.endswith(b):
            s = s[1:-1].strip()
    if len(s) > MAKS_TEGN:
        klip = s[:MAKS_TEGN]
        mellemrum = klip.rfind(" ")
        s = (klip[:mellemrum] if mellemrum > 0 else klip).rstrip()
    return s


def gem_forslag(
    *,
    session_id: str,
    forslag: str,
    kilde_besked_id: str = "",
    nu: str | None = None,
) -> str:
    """Læg Jarvis' forslag ned for sessionen. Returnerer `forslag_id` (""=ugyldigt).

    Der er ingen «overskriv»-semantik: to forslag i samme session er to
    forslag. `tag_forslag` tager det NYESTE, så et forslag der bliver skrevet
    senere i turen vinder over et tidligere — hvilket er rigtigt, for det
    senere er skrevet med mere af turen bag sig.
    """
    sid = (session_id or "").strip()
    tekst = _rens(forslag)
    if not sid or not tekst:
        return ""
    fid = f"cj-{uuid4().hex[:16]}"

    def _skriv() -> None:
        with connect() as conn:
            _sikr_tabel(conn)
            conn.execute(
                f"""
                INSERT INTO {_TABEL}
                    (forslag_id, session_id, forslag, kilde_besked_id, skrevet_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (fid, sid, tekst, (kilde_besked_id or "").strip(), nu or _now_iso()),
            )
            conn.commit()

    skriv_med_genforsoeg(_skriv)
    return fid


def tag_forslag(*, session_id: str) -> dict[str, str] | None:
    """Tag det nyeste forslag for sessionen — og SLET det. Éngangsbrug.

    Sletningen er hvad der binder forslaget til én tur: er det hentet, findes
    det ikke mere, og en senere turs slutning kan ikke gribe et forældet bud.
    `rowcount`-tjekket gør det atomisk nok for to samtidige hentninger: kun
    den ene kan slette rækken, den anden får `None`.
    """
    sid = (session_id or "").strip()
    if not sid:
        return None

    def _tag() -> dict[str, str] | None:
        with connect() as conn:
            _sikr_tabel(conn)
            raekke = conn.execute(
                f"SELECT forslag_id, forslag, kilde_besked_id, skrevet_at "
                f"FROM {_TABEL} WHERE session_id = ? "
                f"ORDER BY skrevet_at DESC, rowid DESC LIMIT 1",
                (sid,),
            ).fetchone()
            if not raekke:
                return None
            fid = str(raekke["forslag_id"])
            slettet = conn.execute(
                f"DELETE FROM {_TABEL} WHERE forslag_id = ?", (fid,)
            )
            if slettet.rowcount == 0:
                # En anden hentning nåede den først.
                return None
            conn.commit()
            return dict(raekke)

    return skriv_med_genforsoeg(_tag)


def kig_forslag(*, session_id: str) -> dict[str, str] | None:
    """Det nyeste forslag UDEN at forbruge det — til bekræftelse efter skriv."""
    sid = (session_id or "").strip()
    if not sid:
        return None
    with connect() as conn:
        _sikr_tabel(conn)
        raekke = conn.execute(
            f"SELECT forslag_id, forslag, kilde_besked_id, skrevet_at "
            f"FROM {_TABEL} WHERE session_id = ? "
            f"ORDER BY skrevet_at DESC, rowid DESC LIMIT 1",
            (sid,),
        ).fetchone()
    return dict(raekke) if raekke else None
