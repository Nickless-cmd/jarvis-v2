"""Durable SQLite state for research runs, tasks, sources, and steering."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.runtime.db_core import connect
from core.services.research_contract import ResearchSource, ResearchTask, normalize_source

_ORDER = ("created", "planning", "researching", "verifying", "synthesizing", "completed")
_TERMINAL = {"completed", "failed", "cancelled", "interrupted", "incomplete"}


class ResearchStateError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _ensure(conn) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS research_runs (
          id TEXT PRIMARY KEY, session_id TEXT NOT NULL, visible_run_id TEXT NOT NULL DEFAULT '',
          original_query TEXT NOT NULL, tier TEXT NOT NULL, status TEXT NOT NULL,
          decision_json TEXT NOT NULL DEFAULT '{}', warning TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL, completed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_research_runs_session_status
          ON research_runs(session_id, status, updated_at);
        CREATE TABLE IF NOT EXISTS research_tasks (
          id TEXT PRIMARY KEY, research_run_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
          title TEXT NOT NULL, objective TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
          agent_run_id TEXT NOT NULL DEFAULT '', finding_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          UNIQUE(research_run_id, ordinal)
        );
        CREATE TABLE IF NOT EXISTS research_sources (
          id TEXT PRIMARY KEY, research_run_id TEXT NOT NULL, task_id TEXT NOT NULL DEFAULT '',
          canonical_url TEXT NOT NULL, url TEXT NOT NULL, title TEXT NOT NULL DEFAULT '',
          publisher TEXT NOT NULL DEFAULT '', published_at TEXT NOT NULL DEFAULT '',
          retrieved_at TEXT NOT NULL DEFAULT '', snippet TEXT NOT NULL DEFAULT '',
          source_type TEXT NOT NULL DEFAULT 'web', authority TEXT NOT NULL DEFAULT 'unknown',
          created_at TEXT NOT NULL, UNIQUE(research_run_id, canonical_url)
        );
        CREATE TABLE IF NOT EXISTS research_steers (
          id TEXT PRIMARY KEY, research_run_id TEXT NOT NULL, message TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL, applied_at TEXT
        );
        CREATE TABLE IF NOT EXISTS research_tool_calls (
          id TEXT PRIMARY KEY, research_run_id TEXT NOT NULL, task_id TEXT NOT NULL DEFAULT '',
          tool_name TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_research_tool_calls_run
          ON research_tool_calls(research_run_id);
    """)


def _row(row):
    return dict(row) if row is not None else None


def get_run(run_id: str) -> dict | None:
    with connect() as conn:
        _ensure(conn)
        return _row(conn.execute("SELECT * FROM research_runs WHERE id=?", (run_id,)).fetchone())


def create_run(*, session_id: str, original_query: str, tier: str, decision: dict | None = None) -> dict:
    run_id = f"research-{uuid4()}"
    now = _now()
    with connect() as conn:
        _ensure(conn)
        conn.execute(
            "INSERT INTO research_runs(id,session_id,original_query,tier,status,decision_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (run_id, session_id, original_query, tier, "created", json.dumps(decision or {}), now, now),
        )
    return get_run(run_id) or {}


def transition_run(run_id: str, status: str, *, warning: str = "") -> dict:
    current = get_run(run_id)
    if not current:
        raise ResearchStateError(f"unknown research run: {run_id}")
    old = str(current["status"])
    allowed = status in _TERMINAL if old not in _TERMINAL else False
    if status in _ORDER and old in _ORDER:
        allowed = _ORDER.index(status) == _ORDER.index(old) + 1
    if not allowed:
        raise ResearchStateError(f"illegal research transition: {old} -> {status}")
    now = _now()
    completed = now if status in _TERMINAL else None
    with connect() as conn:
        _ensure(conn)
        conn.execute(
            "UPDATE research_runs SET status=?, warning=?, updated_at=?, completed_at=? WHERE id=?",
            (status, warning, now, completed, run_id),
        )
    return get_run(run_id) or {}


def bind_visible_run(run_id: str, visible_run_id: str) -> None:
    with connect() as conn:
        _ensure(conn)
        conn.execute("UPDATE research_runs SET visible_run_id=?, updated_at=? WHERE id=?", (visible_run_id, _now(), run_id))


def create_tasks(run_id: str, tasks: list[ResearchTask]) -> list[dict]:
    now = _now()
    with connect() as conn:
        _ensure(conn)
        for index, task in enumerate(tasks):
            ordinal = task.ordinal or index + 1
            conn.execute(
                "INSERT OR IGNORE INTO research_tasks(id,research_run_id,ordinal,title,objective,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (f"research-task-{uuid4()}", run_id, ordinal, task.title, task.objective, now, now),
            )
        rows = conn.execute("SELECT * FROM research_tasks WHERE research_run_id=? ORDER BY ordinal", (run_id,)).fetchall()
    return [dict(row) for row in rows]


def start_task(task_id: str, *, agent_run_id: str = "") -> dict:
    with connect() as conn:
        _ensure(conn)
        cur = conn.execute(
            "UPDATE research_tasks SET status='running',agent_run_id=?,updated_at=? WHERE id=? AND status='pending'",
            (agent_run_id, _now(), task_id),
        )
        if cur.rowcount != 1:
            raise ResearchStateError("research task is not pending")
        return dict(conn.execute("SELECT * FROM research_tasks WHERE id=?", (task_id,)).fetchone())


def complete_task(task_id: str, finding: dict, *, status: str = "completed") -> dict:
    if status not in {"completed", "failed"}:
        raise ResearchStateError("invalid task terminal status")
    with connect() as conn:
        _ensure(conn)
        cur = conn.execute(
            "UPDATE research_tasks SET status=?,finding_json=?,updated_at=? WHERE id=? AND status='running'",
            (status, json.dumps(finding), _now(), task_id),
        )
        if cur.rowcount != 1:
            raise ResearchStateError("research task is not running")
        return dict(conn.execute("SELECT * FROM research_tasks WHERE id=?", (task_id,)).fetchone())


def list_tasks(run_id: str) -> list[dict]:
    """Alle spor i deres egen rækkefølge — også de uafsluttede."""
    with connect() as conn:
        _ensure(conn)
        rows = conn.execute(
            "SELECT * FROM research_tasks WHERE research_run_id=? ORDER BY ordinal",
            (run_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def unfinished_tasks(run_id: str) -> list[dict]:
    """De spor der IKKE blev færdige. Et genoptaget run må kun tage dem.

    Opgave 6 (17/9-2026): en research-kørsel der blev afbrudt startede forfra,
    og de spor der allerede havde leveret evidens blev kørt igen — dyrt, og
    kilderne kom ind to gange.
    """
    return [t for t in list_tasks(run_id)
            if str(t.get("status") or "pending") not in {"completed"}]


def prepare_recovery(run_id: str, *, warning: str) -> dict:
    """Gør et afbrudt research-run klar til at blive taget op igen.

    Et spor der stod som `running` da segmentet døde, kører ikke længere —
    ingen har dets resultat. Det sættes tilbage til `pending`, så det kan
    startes igen; de færdige røres ikke.
    """
    run = get_run(run_id)
    if not run:
        raise ResearchStateError(f"unknown research run: {run_id}")
    now = _now()
    with connect() as conn:
        _ensure(conn)
        conn.execute(
            "UPDATE research_tasks SET status='pending',agent_run_id='',updated_at=? "
            "WHERE research_run_id=? AND status='running'",
            (now, run_id),
        )
        conn.execute(
            "UPDATE research_runs SET warning=?, updated_at=? WHERE id=?",
            (str(warning or ""), now, run_id),
        )
    opdateret = get_run(run_id) or {}
    return {"run": opdateret, "unfinished": unfinished_tasks(run_id),
            # Evidens måles på FÆRDIGE SPOR. `list_findings` tæller parsede
            # fund, og et spor kan have leveret tekst uden et eneste struktureret
            # fund — det er stadig evidens at bygge en rapport på.
            "completed_tasks": completed_task_count(run_id)}


def advance_to_completed(run_id: str, *, warning: str = "") -> dict:
    """Før runnet hele vejen til `completed` — ét trin ad gangen.

    Overgangene er med vilje ordnede (`_ORDER`), så et run ikke kan hoppe fra
    «created» til «completed» og dermed skjule at faserne aldrig skete. En
    genoptagelse står derimod et vilkårligt sted i rækken, og skal stadig kunne
    lukkes. Derfor gås rækken igennem i stedet for at springe.
    """
    run = get_run(run_id)
    if not run:
        raise ResearchStateError(f"unknown research run: {run_id}")
    nu = str(run.get("status") or "")
    if nu in _TERMINAL:
        return run
    start = _ORDER.index(nu) if nu in _ORDER else 0
    for status in _ORDER[start + 1:]:
        run = transition_run(run_id, status, warning=warning)
    return run


def completed_task_count(run_id: str) -> int:
    return sum(1 for t in list_tasks(run_id)
               if str(t.get("status") or "") == "completed")


def add_source(run_id: str, source: ResearchSource | dict, *, task_id: str = "") -> dict:
    normalized = normalize_source(source)
    if not normalized.canonical_url:
        raise ValueError("research source requires a URL")
    source_id = f"research-source-{uuid4()}"
    values = asdict(normalized)
    with connect() as conn:
        _ensure(conn)
        conn.execute(
            "INSERT OR IGNORE INTO research_sources(id,research_run_id,task_id,canonical_url,url,title,publisher,published_at,retrieved_at,snippet,source_type,authority,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (source_id, run_id, task_id, values["canonical_url"], values["url"], values["title"], values["publisher"], values["published_at"], values["retrieved_at"], values["snippet"], values["source_type"], values["authority"], _now()),
        )
        row = conn.execute("SELECT * FROM research_sources WHERE research_run_id=? AND canonical_url=?", (run_id, normalized.canonical_url)).fetchone()
    return dict(row)


def add_steer(run_id: str, message: str) -> dict:
    steer_id = f"research-steer-{uuid4()}"
    with connect() as conn:
        _ensure(conn)
        conn.execute("INSERT INTO research_steers(id,research_run_id,message,created_at) VALUES(?,?,?,?)", (steer_id, run_id, message, _now()))
        return dict(conn.execute("SELECT * FROM research_steers WHERE id=?", (steer_id,)).fetchone())


def consume_pending_steers(run_id: str) -> list[str]:
    now = _now()
    with connect() as conn:
        _ensure(conn)
        rows = conn.execute(
            "SELECT id,message FROM research_steers WHERE research_run_id=? AND status='pending' ORDER BY created_at",
            (run_id,),
        ).fetchall()
        if rows:
            conn.executemany(
                "UPDATE research_steers SET status='applied',applied_at=? WHERE id=? AND status='pending'",
                [(now, row["id"]) for row in rows],
            )
    return [str(row["message"]) for row in rows]


def list_sources(run_id: str) -> list[dict]:
    with connect() as conn:
        _ensure(conn)
        rows = conn.execute(
            "SELECT * FROM research_sources WHERE research_run_id=? ORDER BY created_at,id",
            (run_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def source_count(run_id: str) -> int:
    with connect() as conn:
        _ensure(conn)
        row = conn.execute("SELECT COUNT(*) AS n FROM research_sources WHERE research_run_id=?", (run_id,)).fetchone()
    return int(row["n"] if row else 0)


def list_findings(run_id: str) -> list[dict]:
    """Parsede findings for et run (Fase B2), i track-rækkefølge.

    Læser `finding_json` fra de tasks der blev færdige. Defensiv: en række der
    ikke kan parses springes over — et enkelt dårligt svar må ikke skjule resten.
    """
    with connect() as conn:
        _ensure(conn)
        rows = conn.execute(
            "SELECT finding_json FROM research_tasks "
            "WHERE research_run_id=? AND status='completed' ORDER BY ordinal",
            (run_id,),
        ).fetchall()
    out: list[dict] = []
    for row in rows:
        try:
            payload = json.loads(str(row["finding_json"] or "{}"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        for item in payload.get("findings") or []:
            if isinstance(item, dict):
                out.append(item)
    return out


def record_tool_call(run_id: str, tool_name: str, *, task_id: str = "") -> None:
    """Tæl ét observeret værktøjskald i runnet (Fase A3).

    Kaldes fra evidence-collectoren for hvert web-kald et run ser. Durable, fordi
    workerne kører i egne tråde — en in-memory-tæller ville ikke overleve den grænse.
    """
    with connect() as conn:
        _ensure(conn)
        conn.execute(
            "INSERT INTO research_tool_calls(id,research_run_id,task_id,tool_name,created_at) VALUES(?,?,?,?,?)",
            (f"research-call-{uuid4()}", run_id, task_id, str(tool_name or ""), _now()),
        )


def tool_call_count(run_id: str) -> int:
    with connect() as conn:
        _ensure(conn)
        row = conn.execute("SELECT COUNT(*) AS n FROM research_tool_calls WHERE research_run_id=?", (run_id,)).fetchone()
    return int(row["n"] if row else 0)


def active_for_session(session_id: str) -> dict | None:
    placeholders = ",".join("?" for _ in _TERMINAL)
    with connect() as conn:
        _ensure(conn)
        row = conn.execute(
            f"SELECT * FROM research_runs WHERE session_id=? AND status NOT IN ({placeholders}) ORDER BY created_at DESC LIMIT 1",
            (session_id, *_TERMINAL),
        ).fetchone()
    return _row(row)


def mark_stale_interrupted(*, older_than_seconds: int = 900) -> int:
    cutoff = (datetime.now(UTC) - timedelta(seconds=max(0, older_than_seconds))).isoformat()
    placeholders = ",".join("?" for _ in _TERMINAL)
    with connect() as conn:
        _ensure(conn)
        result = conn.execute(
            f"UPDATE research_runs SET status='interrupted',warning='runtime restart',updated_at=?,completed_at=? WHERE status NOT IN ({placeholders}) AND updated_at<=?",
            (_now(), _now(), *_TERMINAL, cutoff),
        )
        return int(result.rowcount)
