"""Hvad Bjørn gjorde ved komponistens forslag — tog han det, eller skrev han selv?

## Hvorfor det gemmes

Forslaget i komponisten bygger på Jarvis' sidste besked (fase 1, 86e1f2799).
Det lærer intet af sig selv. Bjørn 20/9-2026: «vi skal gemme brugerens valg,
dvs. om de brugte den suggested (tab) i composer eller skrev der egen besked så
næste forslag bliver mere mig/målrettet».

Valget er **binært**: blev forslaget brugt, eller ikke. Ikke «hvilken af A, B,
C valgte han» — der er kun ét forslag ad gangen.

## Hvad der ALDRIG står her

Hans egen beskedtekst. Skriver han selv i stedet for at tage forslaget, gemmes
`eget` — ét bit om at forslaget ikke blev brugt, og intet om hvad han så
skrev. Et signal om hvad der IKKE virkede kræver ikke en kopi af hvad han
sagde i stedet.

Til gengæld gemmes forslagets EGEN ordlyd og id'et på den besked det blev
udledt af. Et valg uden den kontekst er ubrugeligt: vi skal vide hvad der blev
tilbudt, for at kunne lære noget af at det blev vraget.

## Hvorfor rækken først opstår når forslaget er VIST

Et forslag der blev hentet men aldrig kom på skærmen — feltet var ikke tomt,
svaret streamede, sessionen skiftede — siger intet om hvad han ville. Talte vi
dem med, ville afvisnings-raten være et mål for hans skrivetempo frem for for
forslagets kvalitet.

## Ærligt om hvad signalet ER

Vi ved at Tab blev trykket. Vi ved ikke om forslaget blev brugt SOM DET VAR —
han kan have taget det og skrevet det halvt om inden han sendte. Der findes
ingen egentlig succes-feedback her, og tallet skal læses som «det var værd at
tage fat i», ikke som «det var rigtigt».
"""
from __future__ import annotations

import logging

from core.runtime.db_core import _now_iso, connect, skriv_med_genforsoeg

logger = logging.getLogger(__name__)

#: De fire tilstande et forslag kan ende i. `vist` er udgangspunktet; de tre
#: andre er terminale og kommer fra en tast eller en afsendt besked.
VALG: tuple[str, ...] = ("vist", "accepteret", "afvist", "eget")

_TABEL = "composer_choices"


def _sikr_tabel(conn) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {_TABEL} (
            forslag_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            forslag TEXT NOT NULL,
            kilde_besked_id TEXT NOT NULL DEFAULT '',
            valg TEXT NOT NULL DEFAULT 'vist',
            vist_at TEXT NOT NULL,
            valgt_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{_TABEL}_session ON {_TABEL} (session_id, vist_at)"
    )


def noter_vist(
    *,
    forslag_id: str,
    session_id: str,
    forslag: str,
    kilde_besked_id: str = "",
    nu: str | None = None,
) -> bool:
    """Forslaget kom på skærmen. Returnerer False hvis kaldet var ubrugeligt.

    Idempotent: samme `forslag_id` to gange (en genrender, en dobbelt-effekt)
    skal ikke kunne tælle som to forslag.
    """
    fid = (forslag_id or "").strip()
    sid = (session_id or "").strip()
    tekst = (forslag or "").strip()
    if not fid or not sid or not tekst:
        return False

    def _skriv() -> None:
        with connect() as conn:
            _sikr_tabel(conn)
            conn.execute(
                f"""
                INSERT INTO {_TABEL}
                    (forslag_id, session_id, forslag, kilde_besked_id, valg, vist_at)
                VALUES (?, ?, ?, ?, 'vist', ?)
                ON CONFLICT(forslag_id) DO NOTHING
                """,
                (fid, sid, tekst, (kilde_besked_id or "").strip(), nu or _now_iso()),
            )
            conn.commit()

    skriv_med_genforsoeg(_skriv)
    return True


def noter_valg(*, forslag_id: str, valg: str, nu: str | None = None) -> bool:
    """Hvad der skete med forslaget. Returnerer False ved et ukendt valg.

    Det FØRSTE terminale valg vinder. Tager han forslaget med Tab og retter i
    det bagefter, er svaret stadig at han tog det — en senere afsendelse må
    ikke kunne skrive `accepteret` om til `eget`.
    """
    fid = (forslag_id or "").strip()
    v = (valg or "").strip().lower()
    if not fid or v not in VALG or v == "vist":
        return False

    def _skriv() -> None:
        with connect() as conn:
            _sikr_tabel(conn)
            conn.execute(
                f"UPDATE {_TABEL} SET valg = ?, valgt_at = ? "
                f"WHERE forslag_id = ? AND valg = 'vist'",
                (v, nu or _now_iso(), fid),
            )
            conn.commit()

    skriv_med_genforsoeg(_skriv)
    return True


def seneste_valg(*, session_id: str = "", limit: int = 50) -> list[dict[str, str]]:
    """De seneste forslag og hvad der skete med dem. Til fase 3 og til at kigge."""
    with connect() as conn:
        _sikr_tabel(conn)
        if session_id.strip():
            raekker = conn.execute(
                f"SELECT * FROM {_TABEL} WHERE session_id = ? "
                f"ORDER BY vist_at DESC LIMIT ?",
                (session_id.strip(), max(int(limit), 1)),
            ).fetchall()
        else:
            raekker = conn.execute(
                f"SELECT * FROM {_TABEL} ORDER BY vist_at DESC LIMIT ?",
                (max(int(limit), 1),),
            ).fetchall()
    return [dict(r) for r in raekker]


def optaelling(*, session_id: str = "") -> dict[str, int]:
    """Hvor mange forslag endte hvor. Grundlaget for «virker det?»."""
    ud = {v: 0 for v in VALG}
    for r in seneste_valg(session_id=session_id, limit=10_000):
        v = str(r.get("valg") or "")
        if v in ud:
            ud[v] += 1
    return ud
