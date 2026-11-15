"""Rutinens egen samtale — fladen hvor man kan SE hvad den gjorde, og svare den.

MÅLT 15/11-2026: 190 rutine-kørsler, **nul** med en session. Rutinerne kører som
baggrundsrun, så deres arbejde lå udelukkende i ``routine_runs.result`` — usynligt
fra enhver samtaleflade. Bjørn: «så jeg kan aldrig se hvad der sker i sessionerne».

To slags sessioner, fordi to slags rutiner har deres arbejde to forskellige steder:

- **Personlige rutiner** har deres kørsler i ``routine_runs``. De får deres EGEN
  session ``routine-{id}``, og hver kørsel skrives ind i den som opgave + svar.
  Sessionen er et spejl af kørslerne, ikke en ny sandhed: ``routine_runs`` er
  stadig det der blev kørt.
- **System-rutiner** (dream/heartbeat/wakeup) har nul ``routine_runs`` — deres
  spor ligger i de autonome sessioner ``auto-{origin}-{dato}``. Dem peger vi på
  frem for at kopiere: en kopi ville være en anden sandhed end den der kørte.

Skrivningen er idempotent pr. ``run_id``: en kørsel der skrives to gange (fx fordi
workeren genoptog efter et lease-tab) må ikke give to svar i transcripten.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

SESSION_PREFIX = "routine-"

#: System-rutinernes id bærer deres oprindelse: ``routine_system_heartbeat`` →
#: ``heartbeat``. Bruges som fallback når ``trigger_config.producer`` mangler.
_SYSTEM_ORIGINS = ("dream", "heartbeat", "wakeup")


def routine_session_id(routine_id: str) -> str:
    """Den deterministiske session for én rutine."""
    return f"{SESSION_PREFIX}{str(routine_id or '').strip()}"


def origin_for_routine(routine_id: str, trigger_config: Any = None) -> str:
    """Hvilken autonom oprindelse rutinen arbejder under — eller ``''``.

    ``trigger_config.producer`` er den autoritative kilde. Id-suffikset er
    fallback, fordi de tre system-rutiner blev oprettet før feltet fandtes.
    """
    producer = ""
    if isinstance(trigger_config, dict):
        producer = str(trigger_config.get("producer") or "").strip().lower()
    if producer:
        return producer
    rid = str(routine_id or "").strip().lower()
    for origin in _SYSTEM_ORIGINS:
        if rid.endswith(origin) or f"_{origin}" in rid:
            return origin
    return ""


def ensure_routine_session(routine_id: str, *, title: str, owner_user_id: str = "") -> str:
    """Sikr at rutinens session findes. Idempotent (INSERT OR IGNORE)."""
    from core.services.chat_sessions import get_or_create_named_session

    sid = routine_session_id(routine_id)
    navn = str(title or "").strip() or str(routine_id or "").strip() or "Rutine"
    # Titlen bærer «Rutine · » foran, så den kan kendes i sessionslisten uden at
    # slå rutinen op. Uden mærket ligner den en almindelig samtale.
    if not navn.lower().startswith("rutine"):
        navn = f"Rutine · {navn}"
    try:
        return get_or_create_named_session(sid, navn[:200])
    except Exception as exc:  # pragma: no cover — self-safe, som helperen selv
        logger.warning("routine session create failed for %s: %s", routine_id, type(exc).__name__)
        return sid


def _felt(obj: Any, key: str) -> Any:
    """Læs et felt fra både en dataclass/række og en dict."""
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _har_identisk(session_id: str, role: str, content: str) -> bool:
    """Findes beskeden allerede i sessionen?

    Indholdsbaseret, fordi ``append_chat_message`` — den vej appen selv bruger —
    genererer sit eget ``message_id``. Det fanger en genoptaget kørsel og en
    gentaget efterfyldning. Det fanger IKKE to forskellige kørsler der gav
    præcis samme tekst; de lægges sammen til én linje i transcripten. Det er
    acceptabelt: ``routine_runs`` er stadig den autoritative log, og alternativet
    (et eget id-marker i ``content_json``) ville blande sig i hvordan klienten
    læser beskeden.
    """
    from core.runtime.db_core import connect

    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM chat_messages WHERE session_id=? AND role=? AND content=? LIMIT 1",
            (session_id, role, content),
        ).fetchone()
    return row is not None


def append_run(
    session_id: str,
    *,
    run_id: str,
    instruction: str = "",
    result: str = "",
    created_at: str = "",
) -> bool:
    """Skriv én kørsel ind i rutinens session som opgave + svar.

    Returnerer ``True`` hvis der blev skrevet noget. Fejler aldrig hårdt: en
    manglende transcript-post må ikke vælte den kørsel der faktisk lykkedes.

    Skriver gennem ``append_chat_message`` — samme funktion som ``/chat/stream``
    bruger til at persistere en besked. Målt 15/11-2026: ledger-vejen
    (``ledger_write_path.append_message``) svarede «skrevet» for en ny session,
    men der kom **ingen** række i ``chat_messages``, så fladen ville være tom.
    Den tavse succes er grunden til at denne funktion skriver ad den vej der
    beviseligt materialiserer rækken.
    """
    from core.services.chat_sessions import append_chat_message

    sid = str(session_id or "").strip()
    rid = str(run_id or "").strip()
    if not sid or not rid:
        return False
    ts = str(created_at or datetime.now(UTC).isoformat())
    tekst = str(result or "").strip() or "(kørslen gav intet svar)"
    try:
        # SVARET er kørselens markør. Opgaven kan ikke være det: hver kørsel af
        # samme rutine har samme instruks, så en indholds-dedup på opgave-linjen
        # ville slette hele historikken efter første kørsel (målt 15/11-2026 —
        # efterfyldningen gav 2 linjer i stedet for 4).
        if _har_identisk(sid, "assistant", tekst):
            return False
        opgave = str(instruction or "").strip()
        if opgave:
            append_chat_message(
                session_id=sid, role="user", content=opgave, created_at=ts,
            )
        append_chat_message(
            session_id=sid, role="assistant", content=tekst, created_at=ts,
        )
        return True
    except Exception as exc:
        logger.warning("routine transcript write failed for %s: %s", rid, type(exc).__name__)
        return False


def backfill(
    session_id: str,
    runs: list[Any] | None,
    *,
    instruction: str = "",
    limit: int = 40,
) -> int:
    """Skriv de seneste kørsler ind i en NY rutine-session.

    Sessionen blev først oprettet 15/11-2026, så alt hvad rutinen lavede før den
    dag findes kun i ``routine_runs``. Uden denne efterfyldning ville fladen se
    tom ud for en rutine der har kørt i ugevis.

    ``limit`` måler antal KØRSLER, ikke beskeder — hver kørsel giver op til to.
    """
    items = list(runs or [])
    if not items:
        return 0
    skrevet = 0
    for run in items[-max(1, int(limit)):]:
        rid = str(_felt(run, "run_id") or "")
        if not rid:
            continue
        svar = _felt(run, "result")
        if isinstance(svar, bytes):
            svar = svar.decode("utf-8", "replace")
        opgave = _felt(run, "instruction")
        if isinstance(opgave, bytes):
            opgave = opgave.decode("utf-8", "replace")
        if append_run(
            session_id,
            run_id=rid,
            instruction=str(opgave or instruction or ""),
            result=str(svar or ""),
            created_at=str(_felt(run, "created_at") or ""),
        ):
            skrevet += 1
    return skrevet
