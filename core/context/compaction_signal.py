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


def _cache():
    """Det delte lager — importeret lazy, saa try kun har én sætning."""
    from core.services import shared_cache
    return shared_cache


def _ejer_identitet() -> str:
    """Denne proces' identitet: ``<pid>:<starttid>`` — eller "" hvis ukendt.

    Markøren skal bære HVEM der satte den, ikke kun hvornaar. Se `er_i_gang`.
    """
    try:
        from core.services.in_flight_runs import current_owner
        return str(current_owner() or "")
    except Exception:  # uden en ejer-identitet maa markoeren stadig kunne saettes
        return ""


def marker_start(session_id: str) -> None:
    """Komprimering startet for sessionen. Kaster aldrig."""
    sid = (session_id or "").strip()
    if not sid:
        return
    try:
        import time

        _cache().set(
            _noegle(sid),
            {"startet": time.time(), "owner": _ejer_identitet()},
            ttl_seconds=_TTL_SEK,
        )
    except Exception:  # et nede lager maa ikke stoppe komprimeringen
        # Indikatoren mister sit
        # signal, men arbejdet bliver gjort.
        pass


def marker_slut(session_id: str) -> None:
    """Komprimering faerdig — ogsaa naar den fejlede. Kaster aldrig."""
    sid = (session_id or "").strip()
    if not sid:
        return
    try:
        _cache().delete(_noegle(sid))
    except Exception:  # et nede lager maa ikke blokere afslutningen
        pass


def er_i_gang(session_id: str) -> bool:
    """Koerer der en komprimering for sessionen i NOGEN proces?"""
    sid = (session_id or "").strip()
    if not sid:
        return False
    try:
        markoer = _cache().get(_noegle(sid))
    except Exception:  # uden et laesbart lager er der intet signal at vise
        return False
    if markoer is None:
        return False
    # BAERER MARKOEREN EN DOED PROCES? (19/10-2026)
    #
    # TTL'en alene kunne ikke svare paa det her: maalt 19/10 blev markoeren sat
    # 18:08:10 og API'et genstartet 18:08:19 — ni sekunder senere. Ingen
    # komprimerings-proces koerte, alligevel viste desk «komprimerer...» indtil
    # TTL'en udloeb 18:18:10. Et nedbrud efterlader ikke en indikator der lyser
    # i ti minutter; det efterlader et spoergsmaal vi kan besvare.
    #
    # Kun ``False`` afviser. ``None`` betyder «kunne ikke afgoeres», og et gæt
    # maa ikke slukke en indikator for en komprimering der faktisk koerer —
    # samme regel som `owner_still_alive` selv foelger.
    #
    # FALDGRUBE (fra opgaven): `shared_cache` deles mellem api (8080) og
    # runtime (8011). `owner` er den proces der SATTE markoeren — aldrig den
    # der laeser den. En markoer sat af runtime maa ikke afvises fordi api'ets
    # pid staar i den anden ende af spoergsmaalet.
    owner = ""
    if isinstance(markoer, dict):
        owner = str(markoer.get("owner") or "")
    if owner:
        try:
            from core.services.in_flight_runs import owner_still_alive
            if owner_still_alive(owner) is False:
                # Processen findes ikke. Ryd markoeren, saa naeste poll ikke
                # skal spoerge igen — og saa en ny komprimering kan saette en
                # frisk markoer uden at arve den doede.
                try:
                    _cache().delete(_noegle(sid))
                except Exception:  # rydning er en optimering, ikke et krav
                    pass
                return False
        except Exception:  # kan vi ikke spoerge, staar markoeren som foer
            return True
    return True


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
    except Exception:  # uden en laesbar base er der ingen markoer at vise
        return ""
