"""Persistence for the visible-lane projection tables.

Split out of core/runtime/db.py per the boy-scout rule. Owns the schema for
`visible_runs` and `visible_work_notes` (ensure_visible_tables) plus the
recent-read helpers, the work-note upsert, and the cross-session continuity
projection built on top of them.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db_core import connect
from core.services.visible_preview_crypto import reveal_preview


def ensure_visible_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visible_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL UNIQUE,
            lane TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT NOT NULL,
            text_preview TEXT,
            error TEXT,
            capability_id TEXT,
            user_id TEXT NOT NULL DEFAULT ''
        )
        """
    )
    if not any(row[1] == "user_id" for row in conn.execute("PRAGMA table_info(visible_runs)")):
        conn.execute("ALTER TABLE visible_runs ADD COLUMN user_id TEXT NOT NULL DEFAULT ''")
    # Doven migration (14/11-2026): scopet var indtil da kun en parameter og
    # stod ikke på rækken, så det var usynligt hvilken prompt-variant turen
    # havde kørt. Scopet skifter promptens FØRSTE tegn — to varianter deler
    # intet cache-prefix — så uden kolonnen kan et koldt prefix ikke henføres
    # til et scope-skift. Eksisterende rækker får '' (ukendt), hvilket er
    # sandt: vi ved det ikke for dem.
    if not any(row[1] == "tool_scope" for row in conn.execute("PRAGMA table_info(visible_runs)")):
        conn.execute("ALTER TABLE visible_runs ADD COLUMN tool_scope TEXT NOT NULL DEFAULT ''")
    # Genoptagelses-kaeden paa rækken (25/11-2026). Tallet fandtes kun i
    # `in_flight_runs`-journalen, som ryddes — så et forløb med ni kørsler på én
    # besked kunne ikke måles bagefter, kun rekonstrueres af kodelæsning.
    # `recovery_attempt` er hvor mange genoptagelser der lå før denne kørsel,
    # `recovery_task_id` hvilken opgave den fortsatte, og `recovery_wake_kind`
    # om den blev startet af en agent-vækning frem for af et afbrudt run.
    for _kol, _def in (
        ("recovery_attempt", "INTEGER NOT NULL DEFAULT 0"),
        ("recovery_task_id", "TEXT NOT NULL DEFAULT ''"),
        ("recovery_wake_kind", "TEXT NOT NULL DEFAULT ''"),
    ):
        if not any(row[1] == _kol for row in conn.execute("PRAGMA table_info(visible_runs)")):
            conn.execute(f"ALTER TABLE visible_runs ADD COLUMN {_kol} {_def}")
    conn.execute(
        # Tidsvinduet. `hollow_promise_census` slaar modellen op med
        # `? BETWEEN r.started_at AND r.finished_at ORDER BY r.started_at DESC
        # LIMIT 1` — uden indeks blev det SCAN r + TEMP B-TREE FOR ORDER BY for
        # HVER ydre raekke. Maalt 26/9-2026 paa CT105: 28,4 ms pr. opslag mod
        # 19.883 raekker, gange 72.224 ydre raekker = 34 minutter for ÉN
        # gennemgang. Paa en kopi af samme tabel bringer dette indeks opslaget
        # under timer-oploesning, altsaa hele scanningen til ~0,1 s.
        """
        CREATE INDEX IF NOT EXISTS idx_visible_runs_vindue
        ON visible_runs(started_at, finished_at)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visible_work_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id TEXT NOT NULL UNIQUE,
            work_id TEXT NOT NULL,
            run_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            lane TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            user_message_preview TEXT,
            capability_id TEXT,
            work_preview TEXT,
            projection_source TEXT,
            created_at TEXT NOT NULL,
            finished_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visible_work_units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_id TEXT NOT NULL UNIQUE,
            run_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            lane TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT NOT NULL,
            user_message_preview TEXT,
            capability_id TEXT,
            work_preview TEXT
        )
        """
    )


def _run_user_scope(
    user_id: str | None, include_unassigned: bool,
) -> tuple[str, tuple]:
    """WHERE-fragment + parametre for bruger-scoping af runs.

    Samme form som `_approval_user_scope`, saa de to koeer scoper ens.

    - `user_id=None` → intet filter (interne daemoner: de SKAL se alt).
    - owner (`include_unassigned=True`) → egne runs PLUS dem uden ejer;
      systemets egne autonome koersler har ingen user_id og hoerer til ham.
    - andre → kun deres egne.
    """
    uid = str(user_id or "").strip()
    if not uid:
        return "1=1", ()
    if include_unassigned:
        return "(user_id = ? OR user_id IS NULL OR user_id = '')", (uid,)
    return "user_id = ?", (uid,)


def recent_visible_runs(
    limit: int = 5,
    *,
    user_id: str | None = None,
    include_unassigned: bool = False,
    include_running: bool = False,
) -> list[dict[str, object]]:
    """De seneste runs. UDEN `user_id` er der intet filter.

    Scopingen er OPT-IN (6/9-2026): funktionen har 43 kaldere, og langt de
    fleste er daemoner der med rette skal se hele billedet. Men ruten
    `/mc/runs` returnerede ALLE brugeres runs til enhver autentificeret
    kalder — usynligt med én bruger, en aegte eksponering i det oejeblik der
    er en member eller gaest. Ruten sender nu kalderens identitet med.
    """
    scope_sql, scope_params = _run_user_scope(user_id, include_unassigned)
    # 12/9-2026: `visible_runs` får nu en `running`-række i det øjeblik et run
    # STARTER (persist_visible_run_start). De 43 kaldere her læser «den sidste
    # tur» og har altid fået en AFLUTTET række — en halvfærdig række med tom
    # `text_preview` ville ændre deres billede. Vi holder derfor den gamle
    # kontrakt som default og lader kalderen tilvælge igangværende runs
    # eksplicit (companion_presence har sin egen query til dét spørgsmål).
    if not include_running:
        scope_sql = f"({scope_sql}) AND status != 'running'"
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                run_id,
                lane,
                provider,
                model,
                status,
                started_at,
                finished_at,
                text_preview,
                error,
                capability_id
            FROM visible_runs
            WHERE {scope}
            ORDER BY id DESC
            LIMIT ?
            """.format(scope=scope_sql),
            (*scope_params, max(limit, 1)),
        ).fetchall()
    return [
        {
            "run_id": row["run_id"],
            "lane": row["lane"],
            "provider": row["provider"],
            "model": row["model"],
            "status": row["status"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "text_preview": reveal_preview(row["text_preview"], user_id),
            "error": reveal_preview(row["error"], user_id),
            "capability_id": row["capability_id"],
        }
        for row in rows
    ]


def recent_visible_work_notes(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                n.note_id,
                n.work_id,
                n.run_id,
                n.status,
                n.lane,
                n.provider,
                n.model,
                n.user_message_preview,
                n.capability_id,
                n.work_preview,
                n.projection_source,
                n.created_at,
                n.finished_at,
                r.user_id AS _owner
            FROM visible_work_notes AS n
            LEFT JOIN visible_runs AS r ON r.run_id = n.run_id
            ORDER BY n.id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "note_id": row["note_id"],
            "work_id": row["work_id"],
            "run_id": row["run_id"],
            "status": row["status"],
            "lane": row["lane"],
            "provider": row["provider"],
            "model": row["model"],
            # Ejeren slås op på rækkens run_id — kalderen er typisk en daemon
            # uden user_id, og så kan nøglen aldrig bevises.
            "user_message_preview": reveal_preview(row["user_message_preview"], row["_owner"]),
            "capability_id": row["capability_id"],
            "work_preview": reveal_preview(row["work_preview"], row["_owner"]),
            "projection_source": row["projection_source"],
            "created_at": row["created_at"],
            "finished_at": row["finished_at"],
        }
        for row in rows
    ]


def recent_visible_work_units(limit: int = 5) -> list[dict[str, object]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                u.work_id,
                u.run_id,
                u.status,
                u.lane,
                u.provider,
                u.model,
                u.started_at,
                u.finished_at,
                u.user_message_preview,
                u.capability_id,
                u.work_preview,
                r.user_id AS _owner
            FROM visible_work_units AS u
            LEFT JOIN visible_runs AS r ON r.run_id = u.run_id
            ORDER BY u.id DESC
            LIMIT ?
            """,
            (max(limit, 1),),
        ).fetchall()
    return [
        {
            "work_id": row["work_id"],
            "run_id": row["run_id"],
            "status": row["status"],
            "lane": row["lane"],
            "provider": row["provider"],
            "model": row["model"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "user_message_preview": reveal_preview(row["user_message_preview"], row["_owner"]),
            "capability_id": row["capability_id"],
            "work_preview": reveal_preview(row["work_preview"], row["_owner"]),
        }
        for row in rows
    ]


def record_visible_work_note(
    *,
    note_id: str,
    work_id: str,
    run_id: str,
    status: str,
    lane: str,
    provider: str,
    model: str,
    user_message_preview: str = "",
    capability_id: str = "",
    work_preview: str = "",
    projection_source: str = "",
    created_at: str,
    finished_at: str,
) -> dict[str, object]:
    from core.services import chat_crypto
    from core.services.visible_preview_crypto import protect_preview
    with connect() as conn:
        owner = conn.execute("SELECT user_id FROM visible_runs WHERE run_id=?", (run_id,)).fetchone()
        member = chat_crypto.medlem_for_raekke(user_id=str(owner[0] or "")) if owner else None
        stored_user_preview = protect_preview(user_message_preview, member)
        stored_work_preview = protect_preview(work_preview, member)
        conn.execute(
            """
            INSERT INTO visible_work_notes (
                note_id,
                work_id,
                run_id,
                status,
                lane,
                provider,
                model,
                user_message_preview,
                capability_id,
                work_preview,
                projection_source,
                created_at,
                finished_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                note_id=excluded.note_id,
                work_id=excluded.work_id,
                status=excluded.status,
                lane=excluded.lane,
                provider=excluded.provider,
                model=excluded.model,
                user_message_preview=excluded.user_message_preview,
                capability_id=excluded.capability_id,
                work_preview=excluded.work_preview,
                projection_source=excluded.projection_source,
                created_at=excluded.created_at,
                finished_at=excluded.finished_at
            """,
            (
                note_id,
                work_id,
                run_id,
                status,
                lane,
                provider,
                model,
                stored_user_preview,
                capability_id,
                stored_work_preview,
                projection_source,
                created_at,
                finished_at,
            ),
        )
        conn.commit()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                note_id,
                work_id,
                run_id,
                status,
                lane,
                provider,
                model,
                user_message_preview,
                capability_id,
                work_preview,
                projection_source,
                created_at,
                finished_at
            FROM visible_work_notes
            WHERE run_id = ?
            LIMIT 1
            """,
            (run_id,),
        ).fetchone()
    if row is None:
        raise RuntimeError("visible work note was not persisted")
    return {
        "note_id": row["note_id"],
        "work_id": row["work_id"],
        "run_id": row["run_id"],
        "status": row["status"],
        "lane": row["lane"],
        "provider": row["provider"],
        "model": row["model"],
        "user_message_preview": row["user_message_preview"],
        "capability_id": row["capability_id"],
        "work_preview": row["work_preview"],
        "projection_source": row["projection_source"],
        "created_at": row["created_at"],
        "finished_at": row["finished_at"],
    }


def visible_session_continuity() -> dict[str, object]:
    # recent_capability_invocations stays in core.runtime.db (mega-orchestrator
    # table). Import lazily to avoid an import cycle: db.py imports this module
    # at its bottom.
    from core.runtime.db import recent_capability_invocations

    # Use visible_work_notes (which carry both user_message_preview AND
    # work_preview) instead of plain visible_runs (which only have the
    # assistant text). This makes the recent_run_summaries actually
    # carry the dialog context between sessions instead of being a
    # one-sided assistant log.
    recent_notes = recent_visible_work_notes(limit=3)
    recent_runs = recent_visible_runs(limit=3) if not recent_notes else []
    recent_invocations = recent_capability_invocations(limit=2)
    latest_note = recent_notes[0] if recent_notes else {}
    latest_run = recent_runs[0] if recent_runs else {}
    recent_capability_ids = [
        capability_id
        for item in recent_invocations
        if (capability_id := str(item.get("capability_id") or "").strip())
    ]
    recent_run_summaries = [
        {
            "run_id": item.get("run_id"),
            "status": item.get("status"),
            "finished_at": item.get("finished_at"),
            "capability_id": item.get("capability_id"),
            "user_message_preview": item.get("user_message_preview"),
            "text_preview": item.get("work_preview"),
        }
        for item in recent_notes
    ] or [
        {
            "run_id": item.get("run_id"),
            "status": item.get("status"),
            "finished_at": item.get("finished_at"),
            "capability_id": item.get("capability_id"),
            "user_message_preview": None,
            "text_preview": item.get("text_preview"),
        }
        for item in recent_runs
    ]
    latest_payload = latest_note or latest_run or {}
    return {
        "active": bool(latest_payload or recent_invocations),
        "source": "persisted-visible-work-notes+capability-invocations"
        if recent_notes
        else "persisted-visible-runs+capability-invocations",
        "latest_run_id": latest_payload.get("run_id"),
        "latest_status": latest_payload.get("status"),
        "latest_finished_at": latest_payload.get("finished_at"),
        "latest_text_preview": latest_payload.get("work_preview")
        or latest_payload.get("text_preview"),
        "latest_user_message_preview": latest_payload.get("user_message_preview"),
        "latest_capability_id": latest_payload.get("capability_id"),
        "recent_capability_ids": recent_capability_ids,
        "recent_run_summaries": recent_run_summaries,
        "included_run_rows": len(recent_notes) or len(recent_runs),
        "included_capability_rows": len(recent_invocations),
    }


def stamp_recovery_chain(
    run_id: str,
    *,
    recovery_attempt: int = 0,
    recovery_limit: int = 0,
    recovery_task_id: str = "",
    wake_kind: str = "",
    reason: str = "",
) -> bool:
    """Skriv genoptagelses-kaeden paa kørslens række, så den kan måles bagefter.

    HVORFOR (25/11-2026): kæden boede kun i `in_flight_runs`-journalen, som
    `_ryd_afsluttede` rydder. Da Bjørn spurgte hvorfor ni kørsler havde svaret
    på én besked, kunne journalen ikke vise det — den var tom, og svaret blev en
    rekonstruktion fra koden i stedet for et tal. En tæller der forsvinder før
    nogen kan læse den, kan ikke bruges til at bremse noget.

    Skriver via UPDATE, ikke INSERT: rækken findes allerede når segmentet
    afregnes, og en manglende række må ikke opfindes her (en række uden
    `finished_at` ville se ud som en kørsel der stadig løb).
    """
    rid = str(run_id or "").strip()
    if not rid:
        return False
    try:
        with connect() as conn:
            cur = conn.execute(
                """
                UPDATE visible_runs
                   SET recovery_attempt = ?,
                       recovery_task_id = ?,
                       recovery_wake_kind = ?
                 WHERE run_id = ?
                """,
                (max(0, int(recovery_attempt or 0)), str(recovery_task_id or ""),
                 str(wake_kind or ""), rid),
            )
            return bool(cur.rowcount)
    except Exception:
        # Bevidst ikke tavs: en kaede der ikke kan maales er praecis den tilstand
        # der gjorde spoergsmaalet ubesvarligt. Men den maa ikke vaelte turen.
        import logging
        logging.getLogger(__name__).warning(
            "kunne ikke stemple genoptagelses-kaeden paa %s (attempt=%s limit=%s grund=%s)",
            rid[:24], recovery_attempt, recovery_limit, str(reason)[:40], exc_info=True)
        return False
