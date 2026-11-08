"""Én nøgle for «er dette allerede booket?».

Bjørn 8/11-2026: «dine bookninger uanset hvad det er kræver du eller systemet
læser de eksisterende først så du ikk ender med dobbelt bookninger».

Anledningen var målt samme dag: to opfølgningsopgaver til samme dato (8/12) om
samme sag, oprettet 17 minutter fra hinanden, fordi hver booking-vej skrev uden
at læse først. `side_tasks.flag` (via `finding_key`) og `behavioral_decisions`
havde allerede hvert sit dedup; `self_wakeup` og `scheduled_tasks` havde intet.

Modulet er bevidst lille: normalisering og sammenligning. Det booker intet selv,
har ingen side-effekter og rører ingen lås — hver booking-vej beholder sin egen
lås og sit eget lager. Det er med vilje: en fælles skriver ville slå to lagre
sammen for at løse et problem der kun handler om at LÆSE.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, Iterable

#: Hvor tæt to bookinger med SAMME indhold skal ligge for at være én.
#:
#: 60 minutter er valgt ud fra den konkrete fejl: de to opfølgninger 8/11 lå 17
#: minutter fra hinanden og pegede på samme tidspunkt. To ens bookinger mere
#: end en time fra hinanden kan være to bevidste kontrolpunkter (fx «tjek
#: deploy om 5 min» og «tjek deploy om 3 timer») — dem må vi ikke slå sammen.
DUBLET_VINDUE_MINUTTER = 60

#: Alt der ikke er bogstav eller tal erstattes med mellemrum, så «RYKKER:
#: GDPR!» og «rykker gdpr» bliver samme nøgle.
_IKKE_INDHOLD = re.compile(r"[^\w\s]", re.UNICODE)
_MANGE_MELLEMRUM = re.compile(r"\s+")


def noegle(tekst: str) -> str:
    """Indholdet uden form: små bogstaver, ingen tegnsætning, ét mellemrum."""
    t = (tekst or "").casefold()
    t = _IKKE_INDHOLD.sub(" ", t)
    return _MANGE_MELLEMRUM.sub(" ", t).strip()


def til_tid(vaerdi: Any) -> datetime | None:
    """ISO-streng eller datetime → tidszone-bevidst datetime. Ellers ``None``."""
    if isinstance(vaerdi, datetime):
        return vaerdi if vaerdi.tzinfo else vaerdi.replace(tzinfo=UTC)
    if not vaerdi:
        return None
    try:
        d = datetime.fromisoformat(str(vaerdi).replace("Z", "+00:00"))
    except (TypeError, ValueError):  # en utolkelig tid ER svaret «ved det ikke»
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def find_dublet(
    *,
    tekst: str,
    tid: Any,
    eksisterende: Iterable[dict[str, Any]],
    tekst_felt: str,
    tid_felt: str,
    vindue_minutter: int = DUBLET_VINDUE_MINUTTER,
    session: str | None = None,
    session_felt: str = "session_id",
) -> dict[str, Any] | None:
    """Returnér den post der allerede DÆKKER denne booking, eller ``None``.

    Kun et hit på BÅDE indhold og tidspunkt tæller. Mangler et tidspunkt på
    enten den nye eller den gamle post, meldes der IKKE dublet: uden tid kan vi
    ikke skelne «samme kontrol to gange» fra «en dublet», og en forkert
    sammenslåing skjuler en booking — det er værre end en ekstra.

    ``session`` afgrænser til ÉN samtale. Det er ikke kosmetik: en vækning
    tilhører den samtale der bad om den, og to samtaler der hver bestiller
    «tjek deploy» har to forpligtelser — ikke én. Målt 8/11-2026, da den
    første version uden dette skel slog to samtidige bookinger sammen og
    brød `test_to_samtidige_skrivere_taber_ikke_hinanden`: den ene forsvandt
    i tavshed, hvilket er præcis den fejl dedup skal forhindre.

    ``session=None`` betyder «sammenlign ikke på samtale» — kun til brug hvor
    posten ikke har en samtale at høre til.
    """
    ny = noegle(tekst)
    if not ny:
        return None
    ny_tid = til_tid(tid)
    if ny_tid is None:
        return None
    ny_sid = str(session or "").strip() if session is not None else None
    for post in eksisterende:
        if noegle(str(post.get(tekst_felt) or "")) != ny:
            continue
        if ny_sid is not None:
            if str(post.get(session_felt) or "").strip() != ny_sid:
                continue
        gammel_tid = til_tid(post.get(tid_felt))
        if gammel_tid is None:
            continue
        if abs((ny_tid - gammel_tid).total_seconds()) <= vindue_minutter * 60:
            return post
    return None
