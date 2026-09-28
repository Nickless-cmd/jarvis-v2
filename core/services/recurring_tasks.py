"""Recurring tasks service — lets Jarvis schedule repeating reminders/actions.

A background poller (60s interval) checks for due recurring tasks, fires them
via session notification + initiative queue (same delivery as scheduled_tasks),
then advances next_fire_at by the task's interval_minutes.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.runtime import db as runtime_db

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 60
_poller_thread: threading.Thread | None = None
_poller_stop = threading.Event()


# ── DB helpers (self-contained, no db.py modification needed) ────────────────

def _ensure_table() -> None:
    with runtime_db.connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recurring_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL UNIQUE,
                focus TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'jarvis-tool',
                status TEXT NOT NULL DEFAULT 'active',
                interval_minutes INTEGER NOT NULL,
                next_fire_at TEXT NOT NULL,
                last_fired_at TEXT NOT NULL DEFAULT '',
                fire_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                user_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_recurring_tasks_status_next
            ON recurring_tasks(status, next_fire_at)
            """
        )
        # Notif-routing spec §3.5: leverings-kanal pr. task (auto|mobile|desktop|
        # push|discord|telegram). Idempotent ALTER — CREATE IF NOT EXISTS rører
        # ikke eksisterende tabeller.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(recurring_tasks)").fetchall()}
        if "channel" not in cols:
            conn.execute("ALTER TABLE recurring_tasks ADD COLUMN channel TEXT NOT NULL DEFAULT 'auto'")
        # Ugedage (Bjoern 28/9-2026: «begraens medicin-paamindelserne til
        # hverdage»). '' = alle dage, praecis som foer — ALLE eksisterende
        # raekker er derfor uaendrede, og kun de opgaver der eksplicit saettes
        # rammes. Idempotent ALTER, samme moenster som channel ovenfor.
        if "weekdays" not in cols:
            conn.execute("ALTER TABLE recurring_tasks ADD COLUMN weekdays TEXT NOT NULL DEFAULT ''")
        conn.commit()


def set_channel(task_id: str, channel: str) -> bool:
    """Sæt leverings-kanal på en recurring task. Returnerer True hvis opdateret."""
    from core.services.notification_router import VALID_CHANNELS
    ch = (channel or "").strip().lower()
    if ch not in VALID_CHANNELS:
        raise ValueError(f"ugyldig kanal '{ch}' (skal være {sorted(VALID_CHANNELS)})")
    _ensure_table()
    with runtime_db.connect() as conn:
        cur = conn.execute(
            "UPDATE recurring_tasks SET channel = ?, updated_at = ? WHERE task_id = ?",
            (ch, datetime.now(UTC).isoformat(), str(task_id)),
        )
        conn.commit()
        return cur.rowcount > 0


def set_weekdays(task_id: str, weekdays: str) -> bool:
    """Sæt hvilke ugedage en task må fyre på. ``''`` = alle dage (uændret).

    Rammer kun affyringer FREMAD: den planlagte tid står hvor den står, og næste
    gang ``_advance`` regner, springer den udenom de dage der ikke er valgt.
    Derfor røres ``next_fire_at`` ikke her — at flytte den ville rykke
    klokkeslættet, og det er ikke det man beder om.

    Kaster på ukendt ugedag (se ``parse_weekdays``) i stedet for at falde
    tilbage til «alle dage».
    """
    _ensure_table()
    ud = parse_weekdays(weekdays)
    with runtime_db.connect() as conn:
        cur = conn.execute(
            "UPDATE recurring_tasks SET weekdays = ?, updated_at = ? WHERE task_id = ?",
            (ud, datetime.now(UTC).isoformat(), str(task_id)),
        )
        conn.commit()
        return cur.rowcount > 0


def _row_to_dict(row) -> dict:
    keys = row.keys() if hasattr(row, "keys") else []
    return {
        "task_id": row["task_id"],
        "focus": row["focus"],
        "source": row["source"],
        "status": row["status"],
        "interval_minutes": row["interval_minutes"],
        "next_fire_at": row["next_fire_at"],
        "last_fired_at": row["last_fired_at"],
        "fire_count": row["fire_count"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "user_id": (row["user_id"] if "user_id" in keys else None),
        # '' = alle dage — ogsaa for raekker skrevet foer kolonnen fandtes.
        "weekdays": (row["weekdays"] if "weekdays" in keys else ""),
    }


def _scope() -> str:
    """Bruger-id til streng per-bruger-scope (#154). "" = ingen scope (fallback)."""
    from core.services.user_scope import scope_uid
    return scope_uid()


def _create(*, task_id: str, focus: str, source: str, interval_minutes: int,
            next_fire_at: str, now: str, weekdays: str = "") -> None:
    with runtime_db.connect() as conn:
        conn.execute(
            """
            INSERT INTO recurring_tasks
              (task_id, focus, source, status, interval_minutes, next_fire_at, created_at, updated_at, user_id, weekdays)
            VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?, ?)
            """,
            (task_id, focus, source, interval_minutes, next_fire_at, now, now, _scope() or None, weekdays),
        )
        conn.commit()


def _get_due(now_iso: str) -> list[dict]:
    with runtime_db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM recurring_tasks WHERE status = 'active' AND next_fire_at <= ? ORDER BY next_fire_at ASC LIMIT 20",
            (now_iso,),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


# ── Ugedage ──────────────────────────────────────────────────────────────────

# ISO-numre: mandag = 1 … soendag = 7. Baade tal og tre-bogstavs navne, dansk
# og engelsk, fordi det er saadan man skriver det naar man ikke taenker over det.
_UGEDAG_TAL = {
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
    "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 7,
    "man": 1, "tir": 2, "ons": 3, "tor": 4, "fre": 5, "lor": 6, "son": 7,
}
_ALLE_DAGE = {"", "all", "alle", "every", "hver", "dagligt", "daily", "altid"}
_HVERDAGE = {"weekdays", "weekday", "hverdage", "hverdag", "ugedage",
             "man-fre", "mon-fri", "mandag-fredag"}
_WEEKEND = {"weekend", "weekenden", "weekends", "sat-sun", "lor-son"}


def parse_weekdays(raw: object) -> str:
    """Normalisér ugedage til ``'1,2,3,4,5'`` (ISO: mandag = 1). ``''`` = alle.

    Tager imod det man naturligt skriver: ``'man-fre'``, ``'1,2,3,4,5'``,
    ``'mon,wed,fri'``, ``'weekend'``, ``'alle'``.

    Ukendt input KASTER. En tastefejl maa ikke tavst blive til «alle dage» —
    saa fyrer paamindelsen i weekenden alligevel, og fejlen er usynlig.
    """
    s = str(raw or "").strip().lower()
    if s in _ALLE_DAGE:
        return ""
    if s in _HVERDAGE:
        return "1,2,3,4,5"
    if s in _WEEKEND:
        return "6,7"
    ud: set[int] = set()
    for del_ in s.replace(" ", "").split(","):
        if not del_:
            continue
        if "-" in del_:
            a, _, b = del_.partition("-")
            na, nb = _UGEDAG_TAL.get(a), _UGEDAG_TAL.get(b)
            if na and nb:
                i = na
                while True:
                    ud.add(i)
                    if i == nb:
                        break
                    i = i % 7 + 1
        else:
            n = _UGEDAG_TAL.get(del_)
            if n:
                ud.add(n)
    if not ud:
        raise ValueError(
            f"ukendt ugedag {raw!r} — brug fx 'man-fre', '1,2,3,4,5' eller 'weekend'"
        )
    return ",".join(str(n) for n in sorted(ud))


def _ugedage(raw: object) -> set[int]:
    """Ugedagene som et sæt ISO-tal (mandag = 1). Tomt sæt = alle dage.

    Læser den gemte form (``'1,2,3,4,5'``). Skrald ignoreres frem for at
    kaste: en raekke fra foer kolonnen fandtes er ``''`` og skal bare virke.
    """
    s = str(raw or "").strip()
    if not s:
        return set()
    ud: set[int] = set()
    for d in s.split(","):
        try:
            n = int(d)
        except ValueError:  # skrald i den gemte kolonne — se docstring; ignorer frem for at kaste
            continue
        if 1 <= n <= 7:
            ud.add(n)
    return ud


def _ryk_til_ugedag(tid: datetime, trin: timedelta, ugedage: set[int] | None) -> datetime:
    """Ryk frem i hele INTERVALLER til en dag brugeren har valgt.

    Loekken er afgraenset: uden ugedage returnerer den straks (alle eksisterende
    opgaver), og selv et ugentligt sæt rammes inden for faa trin. Graensen paa
    400 er der for at en fejlkonfigureret opgave ikke kan henge polleren.
    """
    if not ugedage:
        return tid
    for _ in range(400):
        if tid.isoweekday() in ugedage:
            return tid
        tid = tid + trin
    return tid


def _naeste_tid(planlagt_iso: str, interval_minutes: int, now: datetime,
                ugedage: set[int] | None = None) -> datetime:
    """Næste affyring — regnet fra den PLANLAGTE tid, ikke fra den faktiske.

    ## Hvorfor det ikke er det samme

    Før stod der ``now + interval``. `now` er det tidspunkt opgaven faktisk
    fyrede, og dermed blev enhver forsinkelse permanent: en opgave der skulle
    køre 05:40, men først blev plukket 07:40, fik 07:40 som sit nye
    tidspunkt — i morgen, og alle dage derefter.

    MÅLT 13/9-2026: Bjørns morgenbrief (`rec-2a7fcce8e0`, dagligt) var planlagt
    05:40, fyrede 07:40:54, og stod bagefter til 07:40 næste dag. Det samme for
    Mikkels morgenvejr. Driften kan kun gå én vej — senere — så et dagligt
    morgenbrev vandrer mod middag, én travl morgen ad gangen.

    ## Hvorfor den springer frem i hele intervaller

    Har maskinen været nede et døgn, er der ti forfaldne tidspunkter bagud. At
    sætte næste tid til det første af dem ville give en byge af affyringer der
    alle skulle indhentes. Vi springer derfor frem i hele intervaller til det
    første tidspunkt der ligger i fremtiden: tidspunktet PÅ DAGEN holdes, og
    der affyres én gang.
    """
    trin = timedelta(minutes=max(1, int(interval_minutes)))
    try:
        naeste = datetime.fromisoformat(str(planlagt_iso))
    except Exception:
        # Ukendt planlagt tid — så er det bedste vi kan gøre det gamle.
        return _ryk_til_ugedag(now + trin, trin, ugedage)
    if naeste.tzinfo is None:
        naeste = naeste.replace(tzinfo=UTC)
    if naeste > now:
        # Fyrede før tid (eller uret gik baglæns): rør ikke ved planen.
        return _ryk_til_ugedag(naeste + trin, trin, ugedage)
    # Spring frem i hele intervaller — bevarer tidspunktet på dagen.
    spring = int((now - naeste) / trin) + 1
    return _ryk_til_ugedag(naeste + trin * spring, trin, ugedage)


def _advance(task_id: str, interval_minutes: int, now: datetime,
             planlagt_iso: str = "", ugedage: set[int] | None = None) -> None:
    next_fire = _naeste_tid(planlagt_iso, interval_minutes, now, ugedage).isoformat()
    now_iso = now.isoformat()
    with runtime_db.connect() as conn:
        conn.execute(
            """
            UPDATE recurring_tasks
            SET next_fire_at = ?, last_fired_at = ?, fire_count = fire_count + 1, updated_at = ?
            WHERE task_id = ?
            """,
            (next_fire, now_iso, now_iso, task_id),
        )
        conn.commit()


def _cancel(task_id: str, now_iso: str) -> bool:
    # Bruger-vendt: et medlem må ikke kunne annullere en andens task.
    uid = _scope()
    with runtime_db.connect() as conn:
        if uid:
            cur = conn.execute(
                "UPDATE recurring_tasks SET status = 'cancelled', updated_at = ? "
                "WHERE task_id = ? AND status != 'cancelled' AND user_id = ?",
                (now_iso, task_id, uid),
            )
        else:
            cur = conn.execute(
                "UPDATE recurring_tasks SET status = 'cancelled', updated_at = ? "
                "WHERE task_id = ? AND status != 'cancelled'",
                (now_iso, task_id),
            )
        conn.commit()
        return cur.rowcount > 0


def _list(limit: int = 50) -> list[dict]:
    # Bruger-vendt liste → kun egne tasks.
    uid = _scope()
    with runtime_db.connect() as conn:
        if uid:
            rows = conn.execute(
                "SELECT * FROM recurring_tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (uid, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM recurring_tasks ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _get_one(task_id: str) -> dict | None:
    uid = _scope()
    with runtime_db.connect() as conn:
        if uid:
            row = conn.execute(
                "SELECT * FROM recurring_tasks WHERE task_id = ? AND user_id = ?",
                (task_id, uid),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM recurring_tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
    return _row_to_dict(row) if row else None


# ── Public service API ────────────────────────────────────────────────────────

def create_recurring_task(
    *,
    focus: str,
    interval_minutes: int,
    source: str = "jarvis-tool",
    delay_minutes: int = 0,
    weekdays: str = "",
) -> dict:
    """Schedule a recurring task. Returns task info dict.

    ``weekdays`` (Bjoern 28/9-2026: «begraens medicin-paamindelserne til
    hverdage»): hvilke ugedage opgaven maa fyre paa — ``'man-fre'``,
    ``'1,2,3,4,5'``, ``'weekend'``. Tom = alle dage, praecis som foer, saa alle
    eksisterende opgaver er uaendrede. Klokkeslaettet bevares: en hverdagsoppgave
    springer weekenden over frem for at flytte sig.

    Foerste affyring (fix 18/9-2026): en EKSPLICIT ``delay_minutes`` vinder over
    intervallet. Foer stod der ``max(delay_minutes, interval_minutes)``, saa et
    stort interval slugte en lille forsinkelse: en engangs-paamindelse med
    ``delay=13 dage`` + ``interval=365 dage`` fyrede foerst om ET AAR (maalt
    18/9-2026). ``delay_minutes=0`` betyder uaendret "foerste affyring efter ét
    interval" — alle eksisterende tasks har delay 0 og er derfor upaavirkede.

    Den absolute forsinkelse spiller sammen med ``_naeste_tid``: efter foerste
    affyring holdes tidspunktet PAA DAGEN, saa en daglig opgave med delay starter
    paa det valgte klokkeslaet og bliver der.
    """
    _ensure_table()
    now = datetime.now(UTC)
    if delay_minutes > 0:
        first_fire = now + timedelta(minutes=max(delay_minutes, 1))
    else:
        first_fire = now + timedelta(minutes=max(interval_minutes, 1))
    ud = parse_weekdays(weekdays)
    ugedage = _ugedage(ud)
    if ugedage:
        # Foerste affyring maa heller ikke lande paa en fridag. Vi rykker i hele
        # DAGE — ikke i hele intervaller — saa klokkeslaettet bevares: en
        # paamindelse sat loerdag morgen skal ramme mandag morgen, ikke mandag
        # kl. 00:30 fordi intervallet tilfaeldigt var en time.
        first_fire = _ryk_til_ugedag(first_fire, timedelta(days=1), ugedage)
    task_id = f"rec-{uuid4().hex[:10]}"
    focus = focus[:300].strip() or "Recurring reminder"
    _create(
        task_id=task_id,
        focus=focus,
        source=source,
        interval_minutes=interval_minutes,
        next_fire_at=first_fire.isoformat(),
        now=now.isoformat(),
        weekdays=ud,
    )
    logger.info("recurring_tasks: created %s every %dm weekdays=%r focus=%r",
                task_id, interval_minutes, ud or "alle", focus[:60])
    return {
        "task_id": task_id,
        "focus": focus,
        "interval_minutes": interval_minutes,
        "next_fire_at": first_fire.isoformat(),
        "weekdays": ud,
        "status": "active",
    }


def cancel_recurring_task(task_id: str) -> bool:
    _ensure_table()
    ok = _cancel(task_id, datetime.now(UTC).isoformat())
    if ok:
        logger.info("recurring_tasks: cancelled %s", task_id)
    return ok


def list_recurring_tasks() -> list[dict]:
    _ensure_table()
    return _list()


def get_recurring_tasks_state() -> dict:
    """Summary for observability / Mission Control."""
    _ensure_table()
    tasks = _list()
    active = [t for t in tasks if t["status"] == "active"]
    cancelled = [t for t in tasks if t["status"] == "cancelled"]
    return {
        "active": active,
        "cancelled_count": len(cancelled),
        "total": len(tasks),
    }


# ── Poller ────────────────────────────────────────────────────────────────────

def _fire_due() -> None:
    _ensure_table()
    now = datetime.now(UTC)
    due = _get_due(now.isoformat())
    if not due:
        return

    # Recurring tasks should EXECUTE the focus (autonomously do the work)
    # rather than just send themselves as a reminder. Without this, a task
    # like "Send morgenbriefing til Bjørn kl 07:00 via Discord: vejr, nyheder,
    # noget inspirerende" would just deliver the focus text back to the user
    # as a notification — useless. Triggering an autonomous run lets Jarvis
    # use his tools (discord_channel.send, web_search etc.) to actually carry
    # out the task. The focus becomes the user-message of an autonomous run.
    from core.services.visible_runs import start_autonomous_run

    for task in due:
        task_id = str(task["task_id"])
        focus = str(task["focus"])
        interval_minutes = int(task["interval_minutes"])
        channel = str(task.get("channel") or "auto")
        ugedage = _ugedage(task.get("weekdays"))
        if ugedage and now.isoweekday() not in ugedage:
            # I dag er ikke en valgt ugedag. Ryk videre UDEN at fyre: en
            # paamindelse der fyrer loerdag fordi maskinen var nede fredag er
            # praecis den stoej brugeren bad os undgaa. Uden dette led ville
            # raekken desuden blive ved med at vaere forfalden og fylde koen.
            _advance(task_id, interval_minutes, now,
                     str(task.get('next_fire_at') or ''), ugedage)
            logger.info("recurring_tasks: %s springer over — ugedag %s ikke i %r",
                        task_id, now.isoweekday(), task.get("weekdays"))
            continue
        # channel != 'auto' => brugeren har valgt en specifik leverings-kanal.
        # Run-completion-notifikationens kanal-routing deles med wakeup-deferral
        # (run-vs-notification-design, spec §3.5) — kanalen er gemt + settbar nu.
        # #154-followup: affyr i task-EJERENS kontekst (ikke som owner), så et
        # medlems gentagne task kører i medlemmets workspace + scopes til deres
        # egne data. Bruger den offentlige hybrid-resolver (legacy + SQLite).
        token = _enter_owner_context(str(task.get("user_id") or ""))
        try:
            # Use autonomous run as the PRIMARY execution path.
            # Push to initiative queue only as a fallback signal — but do NOT
            # let both paths produce a user-visible message independently.
            start_autonomous_run(message=focus, session_id=None, origin="recurring")
            _advance(task_id, interval_minutes, now,
                     str(task.get('next_fire_at') or ''), ugedage)
            logger.info(
                "recurring_tasks: fired %s as autonomous run (every %dm) user=%s",
                task_id, interval_minutes, task.get("user_id") or "-",
            )
        except Exception as exc:
            logger.error("recurring_tasks: error firing %s: %s", task_id, exc)
        finally:
            _exit_owner_context(token)


def _enter_owner_context(user_id: str):
    """Sæt workspace-konteksten til task-ejeren for affyringen. Returnerer en
    reset-token (eller None hvis ingen kontekst sættes). Fail-soft."""
    if not user_id:
        return None
    try:
        from core.identity.workspace_context import set_context
        from core.runtime.workspace_paths import workspace_dir
        ws = workspace_dir(user_id).name  # hybrid resolver (legacy + SQLite)
        return set_context(workspace_name=ws, user_id=user_id, user_display_name="")
    except Exception:
        return None


def _exit_owner_context(token) -> None:
    if token is None:
        return
    try:
        from core.identity.workspace_context import reset_context
        reset_context(token)
    except Exception:
        pass


def _poller_loop() -> None:
    while not _poller_stop.is_set():
        try:
            _fire_due()
        except Exception as exc:
            logger.error("recurring_tasks: poller error: %s", exc)
            # A loop that fails every tick still looks alive from outside; make
            # persistent failure visible to the Central drift-monitor. Self-safe:
            # observe errors never touch loop behaviour (still logs + spins on).
            try:
                from core.services.central_private_observe import (
                    observe_operational_liveness,
                )
                observe_operational_liveness("recurring_tasks", "error", None)
            except Exception:
                pass
        _poller_stop.wait(_POLL_INTERVAL_SECONDS)


def start_recurring_tasks_service() -> None:
    global _poller_thread
    _poller_stop.clear()
    t = threading.Thread(target=_poller_loop, daemon=True, name="recurring-tasks-poller")
    t.start()
    _poller_thread = t
    logger.info("recurring_tasks: service started (poll interval %ds)", _POLL_INTERVAL_SECONDS)


def stop_recurring_tasks_service() -> None:
    _poller_stop.set()
    logger.info("recurring_tasks: service stopped")


