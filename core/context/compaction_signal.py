"""Er sessionen ved at blive komprimeret — og hvornaar blev den det sidst?

Bjoern 18/9-2026: «liveness indikatoren over composer viser ingen tegn paa der
bliver komprimeret» og «"samtalen er blevet komprimeret" bliver kun vist hvis
man manuelt opdaterer».

## Hvorfor flaget ikke kunne ses

Baggrunds-komprimeringen satte `_compact_inflight` — et almindeligt `set` i
hukommelsen. Desk spoerger `/chat/context-usage` hvert 6. sekund, og ruten
kigger i DET set. Men prompten bygges fra flere steder: den synlige tur, cache-
warmeren og assembly-prewarm-loekken, fordelt paa to processer (jarvis-api og
jarvis-runtime). Et flag sat i den ene er usynligt i den anden. Maalt paa
komprimeringen kl. 22:20 den 18/9: den koerte ~74 sekunder — tolv polls — og
desk saa den aldrig.

Det er samme faelde som bro-registret (`bridge_presence`): tilstand der skal
kunne ses paa tvaers af processer, skal ligge i det delte lager. Derfor spejles
flaget her til `shared_cache` med en TTL. TTL'en er vigtig: et nedbrud midt i en
komprimering maa ikke efterlade en indikator der lyser for evigt.

## Hvorfor markoeren kraevede opdatering

Intet fortalte klienten at en ny markoer var skrevet. Komprimeringen koerer i
baggrunden EFTER turen, saa den kom aldrig med i turens egen stroem.
`seneste_komprimering` giver tidspunktet for den seneste markoer; naar det
skifter, ved klienten at den skal hente beskederne igen.
"""
from __future__ import annotations

from typing import Any

_PRAEFIKS = "compaction:inflight:"

# En komprimering har taget op til ~75 s (maalt 18/9). 10 minutter er langt
# over det, men kort nok til at et nedbrud ikke efterlader en indikator der
# lyser resten af aftenen.
_TTL_SEK = 600.0


def _noegle(session_id: str) -> str:
    return _PRAEFIKS + (session_id or "").strip()


def marker_start(session_id: str) -> None:
    """Komprimering startet for sessionen. Kaster aldrig."""
    sid = (session_id or "").strip()
    if not sid:
        return
    try:
        import time

        from core.services import shared_cache
        shared_cache.set(_noegle(sid), {"startet": time.time()}, ttl_seconds=_TTL_SEK)
    except Exception:
        # Et nede lager maa ikke stoppe komprimeringen. Indikatoren mister sit
        # signal, men arbejdet bliver gjort.
        pass


def marker_slut(session_id: str) -> None:
    """Komprimering faerdig — ogsaa naar den fejlede. Kaster aldrig."""
    sid = (session_id or "").strip()
    if not sid:
        return
    try:
        from core.services import shared_cache
        shared_cache.delete(_noegle(sid))
    except Exception:
        pass


def er_i_gang(session_id: str) -> bool:
    """Koerer der en komprimering for sessionen i NOGEN proces?"""
    sid = (session_id or "").strip()
    if not sid:
        return False
    try:
        from core.services import shared_cache
        return shared_cache.get(_noegle(sid)) is not None
    except Exception:
        return False


def seneste_komprimering(session_id: str) -> str:
    """Tidspunktet for sessionens seneste komprimerings-markoer, ellers "".

    Klienten sammenligner mod sidste kendte vaerdi. Et skift betyder at der er
    kommet en markoer siden sidst — og at beskederne skal hentes igen for at den
    kan ses.
    """
    sid = (session_id or "").strip()
    if not sid:
        return ""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            row: Any = conn.execute(
                "SELECT created_at FROM chat_messages"
                " WHERE session_id = ? AND role = 'compact_marker'"
                " ORDER BY id DESC LIMIT 1",
                (sid,),
            ).fetchone()
        if not row:
            return ""
        return str(row[0] or "")
    except Exception:
        return ""
