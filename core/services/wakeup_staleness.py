"""Mærk en fyret vækning: hvad er der sket siden den blev booket?

Bjørn 16/11-2026: «det var det her jeg mente ... Ikke afbestil. Mærk. En post
der får et flag: «muligvis forældet — sagen blev lukket 15/11 kl. 17:44». Så
fyrer den som den skal, men med beviset foran mig i stedet for gætteriet.»

Anledningen var målt samme dag: en vækning booket 15/11 kl. 16:40 med 24 timers
forsinkelse fyrede 16/11 kl. 17:40 om en sag der var afgjort få timer efter
bookingen. Posten var fuldstændig sund — den pegede bare på et verdensbillede
der ikke fandtes længere. Alle vagter i wakeup-systemet er MЕКANISKE
(`er_stadig_fyret`, `dispatch_skipped`, aldersgrænser): de ved om en post er
LEVENDE, aldrig om den er SAND.

Hvorfor mærkning og ikke afbestilling:

En scanner der selv afgør «er det her sket» kræver en dom om verden. Gætter den
forkert og afbestiller, forsvinder arbejdet UDEN SPOR — og det er præcis den
fejlform stop-fixet samme dag blev bygget for at lukke (et stop må ikke forsvinde
tavst, men det må heller ikke rejse sig selv). Mærkningen er den modsatte
bevægelse: den lægger beviset foran Jarvis, som afgør det på stedet. Tager han
fejl, står sporet stadig.

Modulet er bevidst lille og rent — samme form som `booking_dedup`: det læser, det
beslutter intet, det har ingen side-effekter og rører ingen lås. Det KAN ikke
afbestille noget, fordi det ikke har nogen skrivevej.

**Fejl mod behold.** Kan en post ikke dateres, eller kan ingen kilde læses,
returneres ``None`` — så står posten umærket og fyrer som den plejer. En
mærkning der ikke kan underbygges må ikke opstå, for så bliver den selv gætteri.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

#: Under denne alder er posten fra SAMME arbejdsgang, og «samtalen kom videre»
#: siger intet om præmissen. Målt 16/11-2026: 65 af 69 poster i lageret havde
#: en forsinkelse på under en time — de er friske og skal ikke støjes.
FRISK_MINUTTER = 60

#: Status på en side-opgave der beviser at sagen er lukket.
_LUKKEDE = ("completed", "dismissed")

_DANSK = ZoneInfo("Europe/Copenhagen")


def _dansk(vaerdi: Any) -> str:
    """ISO-streng → «15/11 17:44» i dansk tid. Tom streng hvis ulæselig.

    Dansk tid, ikke UTC: mærkningen skal kunne sammenlignes med de tidspunkter
    Bjørn selv skriver. En UTC-streng ville se ud som en anden hændelse.
    """
    from core.services.booking_dedup import til_tid

    t = til_tid(vaerdi)
    if t is None:
        return ""
    lokal = t.astimezone(_DANSK)
    return f"{lokal.day}/{lokal.month} {lokal:%H:%M}"


def _alder_tekst(minutter: float) -> str:
    if minutter < 90:
        return f"{int(round(minutter))} minutter"
    timer = minutter / 60
    if timer < 36:
        return f"{int(round(timer))} timer"
    return f"{int(round(timer / 24))} døgn"


def _side_opgave_fakta(record: dict[str, Any]) -> str | None:
    """Er den side-opgave posten peger på blevet lukket siden? Ellers ``None``."""
    task_id = str(record.get("task_id") or "").strip()
    if not task_id:
        return None
    try:
        from core.services import side_tasks

        post = side_tasks.get(task_id)
    except Exception:  # noqa: BLE001 — en ulæselig kilde må ikke opfinde et faktum
        logger.debug("wakeup_staleness: side_tasks utilgængelig", exc_info=True)
        return None
    if not post:
        return None
    status = str(post.get("status") or "")
    if status not in _LUKKEDE:
        return None
    hvornår = _dansk(post.get("resolved_at") or post.get("updated_at"))
    if not hvornår:
        return f"Side-opgaven {task_id} er lukket ({status})."
    return f"Side-opgaven {task_id} blev lukket {hvornår} ({status})."


def _senere_post_fakta(record: dict[str, Any]) -> str | None:
    """Findes der en SENERE post om samme sag der allerede er afviklet?

    Sammenligningen er ``booking_dedup.noegle`` — samme normalisering som
    dublet-værnet bruger, så to poster med samme indhold men forskellig form
    (tegnsætning, store bogstaver) rammer hinanden. Kun et EKSAKT
    indholdsmatch tæller: en løs ord-overlapning ville gøre mærkningen til en
    gætteleg, og så er den værre end ingenting.
    """
    from core.services.booking_dedup import noegle, til_tid

    egen = noegle(str(record.get("prompt") or ""))
    if not egen:
        return None
    eget_id = str(record.get("wakeup_id") or "")
    egen_tid = til_tid(record.get("scheduled_at"))
    if egen_tid is None:
        return None
    try:
        from core.services.self_wakeup import list_wakeups

        andre = list_wakeups(limit=200)
    except Exception:  # noqa: BLE001
        logger.debug("wakeup_staleness: wakeup-lageret utilgængeligt", exc_info=True)
        return None
    for post in andre:
        if str(post.get("wakeup_id") or "") == eget_id:
            continue
        if noegle(str(post.get("prompt") or "")) != egen:
            continue
        if str(post.get("status") or "") != "consumed":
            continue
        afviklet = til_tid(post.get("consumed_at") or post.get("fired_at"))
        if afviklet is None or afviklet <= egen_tid:
            continue
        return f"En senere post om samme sag blev afviklet {_dansk(afviklet)}."
    return None


def _samtale_fakta(record: dict[str, Any]) -> str | None:
    """Hvor mange ture er der afsluttet i samtalen siden posten blev booket?

    Samme regel som `in_flight_runs.stopped_for_session`: «samtalen kom videre»
    er udledt af tilstanden, ikke af et flag. Kilden er `chat_messages` og ikke
    `in_flight_runs`, fordi den sidstnævnte rydder afsluttede poster — en
    vækning med 24 timers forsinkelse ville så altid se en tom historik.
    """
    from core.services.booking_dedup import til_tid

    session_id = str(record.get("session_id") or "").strip()
    scheduled = til_tid(record.get("scheduled_at"))
    if not session_id or scheduled is None:
        return None
    try:
        from core.runtime.db_core import connect

        with connect() as conn:
            rad = conn.execute(
                "SELECT COUNT(*) FROM chat_messages "
                "WHERE session_id = ? AND role = 'assistant' AND created_at > ?",
                (session_id, scheduled.isoformat()),
            ).fetchone()
    except Exception:  # noqa: BLE001 — en ulæselig DB må ikke opfinde et faktum
        logger.debug("wakeup_staleness: samtale-opslag fejlede", exc_info=True)
        return None
    antal = int(rad[0]) if rad else 0
    if antal <= 0:
        return None
    return f"Der er afsluttet {antal} ture i denne samtale siden posten blev booket."


def maerk(record: dict[str, Any], *, nu: datetime | None = None) -> str | None:
    """Fakta om hvad der er sket siden posten blev booket — eller ``None``.

    Returnerer en tekstblok til `direktiv_for`, aldrig en beslutning. Blokken
    siger HVAD der er sket og HVOR det kan ses; den siger ikke hvad Jarvis skal
    gøre ved det, ud over at minde ham om at præmissen ikke er efterprøvet.

    ``None`` betyder «ingen mærkning» og er det sikre svar: en post vi ikke kan
    datere, eller hvis kilder ikke kan læses, fyrer som den altid har gjort.
    """
    from core.services.booking_dedup import til_tid

    scheduled = til_tid(record.get("scheduled_at"))
    if scheduled is None:
        # Uden et bookningstidspunkt kan vi ikke sige HVAD der er sket siden.
        # Fravalget er ikke forsigtighed — en mærkning uden tidsreference ville
        # være en påstand uden bevis.
        return None
    nu = nu or datetime.now(UTC)
    minutter = (nu - scheduled).total_seconds() / 60

    fakta: list[str] = []
    for kilde in (_side_opgave_fakta, _senere_post_fakta, _samtale_fakta):
        try:
            tekst = kilde(record)
        except Exception:  # noqa: BLE001 — én død kilde må ikke dræbe mærkningen
            logger.debug("wakeup_staleness: kilde %s fejlede", kilde.__name__, exc_info=True)
            continue
        if tekst:
            fakta.append(tekst)

    if minutter < FRISK_MINUTTER and not fakta:
        return None

    hoved = f"[MULIGVIS FORÆLDET] Posten blev booket {_dansk(scheduled)}"
    if minutter >= FRISK_MINUTTER:
        hoved += f" — {_alder_tekst(minutter)} før den fyrede"
    linjer = [hoved + "."]
    linjer.extend(f"- {f}" for f in fakta)
    linjer.append(
        "Præmissen er IKKE efterprøvet. Er opgaven stadig relevant? Ja → udfør "
        "den. Nej → luk med [wakeup:no-update] og skriv én linje om hvorfor. "
        "Denne mærkning afbestiller intet og beslutter intet."
    )
    return "\n".join(linjer)
