"""Ros og ris på Jarvis' svar — og hvad de bliver til.

Bjørn 12/9-2026: «sørg for de faktisk har en funktion der tjener ham … lad
folks ris og ros give en effekt … en gang om måneden reviewer han dem, og dem
af dem der er værd at gemme som enten læring eller overvejelser der kan hjælpe
senere, eller frasortere støj».

Indtil nu stod der i `MessageBubble.tsx`: *«Tommelen er indtil videre KUN
lokal markering. Der er ingen feedback-kanal til serveren endnu, og en knap
der lader som om den sender noget, er værre end ingen knap.»* Kommentaren var
ærlig; knappen var stadig en løgn over for den der trykkede.

## Hvorfor en wakeup og ikke en prompt-sektion

Fordi en prompt-sektion der aldrig bliver læst er husets hyppigste fejl —
`record_action` med nul kaldere, 24 kanaler slukket af en frossen blacklist,
lektier der aldrig nåede prompten. `schedule_self_wakeup` → `dispatch_due_wakeups`
er derimod en vej der ER efterprøvet ende-til-ende (Jarvis, 12/9-2026), og som
giver ham en RIGTIG tur at tænke i frem for et afsnit at skimme.

## Hvorfor den tier når der intet er

En månedlig påmindelse om nul stemmer lærer én at ignorere den månedlige
påmindelse. Tikket skriver kun en wakeup når der faktisk ligger noget.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# En måned. Ikke 30 dage til punkt og prikke — cadencen skal bare være «sjældent
# nok til at der er noget at se på, tit nok til at det stadig er aktuelt».
_KADENCE_DAGE = 30
_MAKS_I_ET_REVIEW = 60

_sidste_tick: datetime | None = None


def _sikr_tabel(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS message_feedback (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id  TEXT NOT NULL,
            session_id  TEXT NOT NULL DEFAULT '',
            user_id     TEXT NOT NULL DEFAULT '',
            vote        TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            reviewed_at TEXT NOT NULL DEFAULT ''
        )
        """
    )
    # Én stemme pr. besked pr. bruger. Uden den ville et dobbelttryk taelle to
    # gange, og et review ville se en styrke der ikke var der.
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_message_feedback_unik "
        "ON message_feedback(message_id, user_id)"
    )


def sæt_stemme(
    *, message_id: str, session_id: str = "", user_id: str = "", vote: str,
) -> dict[str, Any]:
    """Gem (eller fjern) en stemme. `vote=''` fortryder.

    At fortryde SLETTER rækken frem for at gemme en tom streng: en stemme man
    har taget tilbage er ikke data om noget, og den skal ikke tælles med i et
    review som «neutral».
    """
    from core.runtime.db import connect
    mid = str(message_id or "").strip()
    if not mid:
        return {"status": "error", "error": "message_id mangler"}
    v = str(vote or "").strip().lower()
    if v not in ("up", "down", ""):
        return {"status": "error", "error": "vote skal være up, down eller tom"}
    with connect() as conn:
        _sikr_tabel(conn)
        if not v:
            conn.execute(
                "DELETE FROM message_feedback WHERE message_id = ? AND user_id = ?",
                (mid, str(user_id or "")),
            )
            conn.commit()
            return {"status": "ok", "vote": ""}
        conn.execute(
            """
            INSERT INTO message_feedback (message_id, session_id, user_id, vote, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(message_id, user_id) DO UPDATE SET
                vote = excluded.vote, created_at = excluded.created_at, reviewed_at = ''
            """,
            (mid, str(session_id or ""), str(user_id or ""), v, _nu()),
        )
        conn.commit()
    return {"status": "ok", "vote": v}


def ugennemgåede(limit: int = _MAKS_I_ET_REVIEW) -> list[dict[str, Any]]:
    """Stemmer der endnu ikke er set på, ældste først."""
    from core.runtime.db import connect
    with connect() as conn:
        _sikr_tabel(conn)
        rows = conn.execute(
            """
            SELECT f.message_id, f.session_id, f.user_id, f.vote, f.created_at,
                   COALESCE((SELECT substr(content, 1, 400) FROM chat_messages m
                             WHERE m.message_id = f.message_id), '') AS uddrag
            FROM message_feedback f
            WHERE f.reviewed_at = ''
            ORDER BY f.created_at ASC
            LIMIT ?
            """,
            (max(1, int(limit)),),
        ).fetchall()
    return [dict(r) for r in rows]


def markér_gennemgået(message_ids: list[str]) -> int:
    from core.runtime.db import connect
    ids = [str(m) for m in (message_ids or []) if str(m).strip()]
    if not ids:
        return 0
    with connect() as conn:
        _sikr_tabel(conn)
        q = ",".join("?" for _ in ids)
        cur = conn.execute(
            f"UPDATE message_feedback SET reviewed_at = ? WHERE message_id IN ({q}) AND reviewed_at = ''",
            (_nu(), *ids),
        )
        conn.commit()
        return int(cur.rowcount or 0)


def byg_review_prompt(poster: list[dict[str, Any]]) -> str:
    """Den tekst Jarvis vågner op til.

    Den beder om en DOM, ikke om en opsummering: hver stemme skal ende som
    lektie, overvejelse eller støj. Uden det tredje udfald bliver alt til en
    lektie, og lektie-listen bliver ubrugelig — samme fejl som en badge der
    altid lyser.
    """
    op = sum(1 for p in poster if p.get("vote") == "up")
    ned = len(poster) - op
    linjer = [
        f"Månedens tilbagemeldinger: {op} tommel op, {ned} tommel ned.",
        "",
        "Gå dem igennem én ad gangen. For hver: er den værd at gemme som en",
        "LEKTIE (noget du gør anderledes fremover), som en OVERVEJELSE (noget",
        "der kan blive relevant senere), eller er den STØJ? Det tredje udfald er",
        "det vigtigste — uden det bliver alt til en lektie, og så er listen",
        "ubrugelig.",
        "",
        "Skriv det du beholder ned med de værktøjer du har. Resten lader du gå.",
        "",
    ]
    for p in poster:
        tegn = "👍" if p.get("vote") == "up" else "👎"
        uddrag = " ".join(str(p.get("uddrag") or "").split())[:240]
        linjer.append(f"{tegn} [{p.get('created_at', '')[:10]}] {uddrag or '(ingen tekst gemt)'}")
    return "\n".join(linjer)


def tick_feedback_review(now: datetime | None = None) -> dict[str, Any]:
    """Én gang om måneden: giv Jarvis månedens stemmer at tænke over.

    Selv-sikker og tavs når der intet er. En månedlig påmindelse om nul
    stemmer lærer én at ignorere den månedlige påmindelse.
    """
    global _sidste_tick
    nu = now or datetime.now(UTC)
    if _sidste_tick is not None and (nu - _sidste_tick) < timedelta(days=_KADENCE_DAGE):
        return {"planlagt": False, "grund": "kadence"}

    try:
        poster = ugennemgåede()
    except Exception as exc:
        logger.warning("message_feedback: kunne ikke læse stemmer: %s", exc, exc_info=True)
        return {"planlagt": False, "grund": "fejl", "fejl": str(exc)[:200]}

    # SÆT URET UANSET. Ellers ville en tom måned betyde at vi spurgte
    # databasen ved hvert eneste tick resten af måneden.
    _sidste_tick = nu
    if not poster:
        return {"planlagt": False, "grund": "ingen stemmer"}

    try:
        from core.services.self_wakeup import schedule_self_wakeup
        svar = schedule_self_wakeup(
            delay_seconds=60,
            prompt=byg_review_prompt(poster),
            reason="månedlig gennemgang af tilbagemeldinger",
        )
        if svar.get("status") == "error":
            return {"planlagt": False, "grund": "wakeup afvist", "fejl": svar.get("error")}
    except Exception as exc:
        logger.warning("message_feedback: kunne ikke planlægge review: %s", exc, exc_info=True)
        return {"planlagt": False, "grund": "fejl", "fejl": str(exc)[:200]}

    # MARKÉR FØRST NÅR DEN ER PLANLAGT. Markerede vi før, ville en afvist
    # wakeup betyde at månedens stemmer forsvandt uden at nogen så dem.
    antal = markér_gennemgået([str(p.get("message_id") or "") for p in poster])
    logger.info("message_feedback: planlagde gennemgang af %d stemme(r)", antal)
    return {"planlagt": True, "antal": antal}


def _nu() -> str:
    return datetime.now(UTC).isoformat()


def _nulstil_for_tests() -> None:
    global _sidste_tick
    _sidste_tick = None
