"""Visible Jarvis' værktøjer til hjernen.

Tools:
  - remember_this: skriv en post i hjernen (5/turn, 20/day cap)
  - search_jarvis_brain: embedding-søg (visibility-filtreret)
  - read_brain_entry: hent fuld content for én post
  - archive_brain_entry: arkivér post
  - adopt_brain_proposal: stempl en daemon-foreslået post som rigtig hjerne
  - discard_brain_proposal: smid forslag væk

Spec: docs/superpowers/specs/2026-05-02-jarvis-brain-design.md sektion 4 + 5.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

JARVIS_BRAIN_TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "remember_this",
            "description": "Skriv en post i Jarvis' egen hjerne. Brug til indsigter, fakta, observationer du vil huske. Har rate-limits (5/turn, 20/dag).",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["fakta", "indsigt", "observation", "reference"], "description": "Type af post"},
                    "title": {"type": "string", "description": "Kort titel"},
                    "content": {"type": "string", "description": "Indhold (max 4096 chars)"},
                    "visibility": {"type": "string", "enum": ["public_safe", "personal", "intimate"], "description": "Synlighed"},
                    "domain": {"type": "string", "description": "Domæne, fx 'self', 'projects', 'relationships'"},
                    "related": {"type": "array", "items": {"type": "string"}, "description": "Relaterede emner"},
                    "source_url": {"type": "string", "description": "Kilde-URL"},
                    "source_chronicle": {"type": "string", "description": "Kilde-chronicle"},
                },
                "required": ["kind", "title", "content", "visibility", "domain"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_jarvis_brain",
            "description": "Søg i Jarvis' hjerne med semantisk search. Returnerer excerpts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Søgetekst"},
                    "kinds": {"type": "array", "items": {"type": "string"}, "description": "Filtrér på typer"},
                    "limit": {"type": "integer", "description": "Max resultater (default 5)"},
                    "domain": {"type": "string", "description": "Filtrér på domæne"},
                    "include_archived": {"type": "boolean", "description": "Inkluder arkiverede"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_brain_entry",
            "description": "Hent fuld content for én brain entry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entry_id": {"type": "string", "description": "Entry ID"},
                },
                "required": ["entry_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "archive_brain_entry",
            "description": "Arkivér en brain entry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entry_id": {"type": "string", "description": "Entry ID"},
                    "reason": {"type": "string", "description": "Årsag til arkivering"},
                },
                "required": ["entry_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adopt_brain_proposal",
            "description": "Adoptér en pending brain proposal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "proposal_id": {"type": "string", "description": "Proposal ID"},
                    "edits": {"type": "object", "description": "Valgfrie rettelser"},
                },
                "required": ["proposal_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "discard_brain_proposal",
            "description": "Kassér en pending brain proposal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "proposal_id": {"type": "string", "description": "Proposal ID"},
                    "reason": {"type": "string", "description": "Årsag"},
                },
                "required": ["proposal_id"],
            },
        },
    },
]

# Default caps; overridable via RuntimeSettings (Task 17 wires this).
_DEFAULT_PER_TURN_CAP = 5
_DEFAULT_PER_DAY_CAP = 20

# In-memory counters. Genstart nulstiller — det er ok, dag-cap er soft beskyttelse.
_turn_counts: dict[str, int] = defaultdict(int)
_day_counts: dict[str, int] = defaultdict(int)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _day_key(now: datetime) -> str:
    return now.strftime("%Y-%m-%d")


def _get_caps() -> tuple[int, int]:
    """Read caps from RuntimeSettings if available, else defaults."""
    try:
        from core.runtime.settings import load_settings  # type: ignore
        s = load_settings()
        return (
            getattr(s, "jarvis_brain_remember_per_turn_cap", _DEFAULT_PER_TURN_CAP),
            getattr(s, "jarvis_brain_remember_per_day_cap", _DEFAULT_PER_DAY_CAP),
        )
    except Exception:
        return (_DEFAULT_PER_TURN_CAP, _DEFAULT_PER_DAY_CAP)


# ---------------------------------------------------------------------------
# Executors — wrappers for simple_tools import
# ---------------------------------------------------------------------------


def _exec_remember_this(args: dict[str, Any]) -> dict[str, Any]:
    """Executor for remember_this tool."""
    session_id = ""
    try:
        from core.services.chat_sessions import get_active_session_id  # type: ignore
        session_id = get_active_session_id() or ""
    except Exception:
        pass
    return remember_this(
        kind=args["kind"],
        title=args["title"],
        content=args["content"],
        visibility=args["visibility"],
        domain=args["domain"],
        session_id=session_id,
        turn_id=f"{session_id}:{_now().isoformat()}",
        related=args.get("related"),
        source_url=args.get("source_url"),
        source_chronicle=args.get("source_chronicle"),
    )


def _exec_search_jarvis_brain(args: dict[str, Any]) -> dict[str, Any]:
    """Executor for search_jarvis_brain tool."""
    return search_jarvis_brain(
        query=args["query"],
        kinds=args.get("kinds"),
        limit=args.get("limit", 5),
        domain=args.get("domain"),
        include_archived=args.get("include_archived", False),
    )


def _exec_read_brain_entry(args: dict[str, Any]) -> dict[str, Any]:
    """Executor for read_brain_entry tool."""
    return read_brain_entry(args["entry_id"])


def _exec_archive_brain_entry(args: dict[str, Any]) -> dict[str, Any]:
    """Executor for archive_brain_entry tool."""
    return archive_brain_entry(
        args["entry_id"],
        reason=args.get("reason", "manual"),
    )


def _exec_adopt_brain_proposal(args: dict[str, Any]) -> dict[str, Any]:
    """Executor for adopt_brain_proposal tool."""
    return adopt_brain_proposal(
        args["proposal_id"],
        edits=args.get("edits"),
    )


def _exec_discard_brain_proposal(args: dict[str, Any]) -> dict[str, Any]:
    """Executor for discard_brain_proposal tool."""
    return discard_brain_proposal(
        args["proposal_id"],
        reason=args.get("reason", ""),
    )


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def remember_this(
    *,
    kind: str,
    title: str,
    content: str,
    visibility: str,
    domain: str,
    session_id: str,
    turn_id: str,
    related: list[str] | None = None,
    source_url: str | None = None,
    source_chronicle: str | None = None,
) -> dict[str, Any]:
    """Skriv en post i Jarvis' egen hjerne.

    Returnerer dict med status="ok" og id, eller status="error" med detalje.
    """
    now = _now()

    # Validation
    if kind not in {"fakta", "indsigt", "observation", "reference"}:
        return {"status": "error", "error": "validation_failed",
                "details": f"invalid kind: {kind}"}
    if visibility not in {"public_safe", "personal", "intimate"}:
        return {"status": "error", "error": "validation_failed",
                "details": f"invalid visibility: {visibility}"}
    if not title.strip():
        return {"status": "error", "error": "validation_failed",
                "details": "empty title"}
    if len(content) > 4096:
        return {"status": "error", "error": "validation_failed",
                "details": "content too long (max 4096 bytes)"}

    # Rate limits
    per_turn_cap, per_day_cap = _get_caps()
    turn_key = f"{session_id}:{turn_id}"
    if _turn_counts[turn_key] >= per_turn_cap:
        return {"status": "error", "error": "rate_limit_turn",
                "details": f"max {per_turn_cap} per turn"}
    day_key = _day_key(now)
    if _day_counts[day_key] >= per_day_cap:
        return {"status": "error", "error": "rate_limit_day",
                "details": f"max {per_day_cap} per day"}

    # Persist
    try:
        from core.services import jarvis_brain
        new_id = jarvis_brain.write_entry(
            kind=kind, title=title, content=content,
            visibility=visibility, domain=domain,
            trigger="spontaneous", related=related or [],
            source_url=source_url, source_chronicle=source_chronicle,
            now=now,
        )
    except Exception as exc:
        return {"status": "error", "error": "disk_write_failed",
                "details": str(exc)}

    _turn_counts[turn_key] += 1
    _day_counts[day_key] += 1

    return {"status": "ok", "id": new_id}


def search_jarvis_brain(
    *,
    query: str,
    session_visibility_ceiling: str = "personal",
    kinds: list[str] | None = None,
    limit: int = 5,
    domain: str | None = None,
    include_archived: bool = False,
) -> dict[str, Any]:
    """Søg Jarvis' egen hjerne. Returnerer excerpts; brug read_brain_entry for fuld content.

    Filtrér automatisk på visibility ceiling.
    Bumper salience for hver returneret entry.
    Inkluderer hidden_by_visibility-count så Jarvis ved at noget blev skjult.
    """
    from core.services import jarvis_brain
    try:
        results = jarvis_brain.search_brain(
            query_text=query,
            kinds=kinds,
            visibility_ceiling=session_visibility_ceiling,
            limit=limit,
            domain=domain,
            include_archived=include_archived,
        )
    except Exception as exc:
        return {"status": "error", "error": "search_failed", "details": str(exc)}

    # Bump salience for hver returneret entry (best-effort)
    now = _now()
    for e in results:
        try:
            jarvis_brain.bump_salience(e.id, now=now)
        except Exception:
            pass

    # Tæl hidden — kør samme query med ceiling=intimate og diff
    hidden_count = 0
    if session_visibility_ceiling != "intimate":
        try:
            full = jarvis_brain.search_brain(
                query_text=query,
                kinds=kinds,
                visibility_ceiling="intimate",
                limit=max(limit * 3, 15),
                domain=domain,
                include_archived=include_archived,
            )
            full_ids = {e.id for e in full}
            visible_ids = {e.id for e in results}
            hidden_count = max(0, len(full_ids - visible_ids))
        except Exception:
            pass

    out = []
    for e in results:
        out.append({
            "id": e.id,
            "kind": e.kind,
            "title": e.title,
            "domain": e.domain,
            "created_at": e.created_at.isoformat(),
            "excerpt": e.content[:200] + ("…" if len(e.content) > 200 else ""),
        })
    return {
        "status": "ok",
        "results": out,
        "hidden_by_visibility": hidden_count,
    }


def read_brain_entry(entry_id: str) -> dict[str, Any]:
    """Hent fuld content for én brain entry."""
    from core.services import jarvis_brain
    try:
        e = jarvis_brain.read_entry(entry_id)
    except KeyError:
        return {"status": "error", "error": "not_found"}
    except Exception as exc:
        return {"status": "error", "error": "read_failed", "details": str(exc)}
    return {
        "status": "ok",
        "entry": {
            "id": e.id,
            "kind": e.kind,
            "title": e.title,
            "content": e.content,
            "visibility": e.visibility,
            "domain": e.domain,
            "created_at": e.created_at.isoformat(),
            "salience_bumps": e.salience_bumps,
            "related": e.related,
            "status_field": e.status,
            "superseded_by": e.superseded_by,
        },
    }


def archive_brain_entry(entry_id: str, *, reason: str = "manual") -> dict[str, Any]:
    """Mark entry as archived and move file to _archive/<kind>/."""
    from core.services import jarvis_brain
    try:
        jarvis_brain.archive_entry(entry_id, reason=reason)
    except KeyError:
        return {"status": "error", "error": "not_found"}
    except Exception as exc:
        return {"status": "error", "error": "archive_failed", "details": str(exc)}
    return {"status": "ok"}


def adopt_brain_proposal(
    proposal_id: str, edits: dict | None = None,
) -> dict[str, Any]:
    """Flyt en pending proposal til den rigtige kind/-mappe og stempel som visible_jarvis.

    Pending proposal file → kind/<filename>.md
    proposal status: pending → adopted
    Inserts new active row in brain_index.
    """
    from core.services import jarvis_brain

    conn = jarvis_brain.connect_index()
    try:
        row = conn.execute(
            "SELECT path, status FROM brain_proposals WHERE id = ?",
            (proposal_id,),
        ).fetchone()
        if row is None:
            return {"status": "error", "error": "not_found"}
        if row[1] != "pending":
            return {
                "status": "error",
                "error": "not_pending",
                "details": f"current status: {row[1]}",
            }
        rel_path = row[0]
    finally:
        conn.close()

    pending_path = jarvis_brain._workspace_root() / rel_path
    fm, body = jarvis_brain.parse_frontmatter(pending_path)
    edits = edits or {}
    fm.update(edits)
    fm["trigger"] = "adopted_proposal"
    fm["created_by"] = "visible_jarvis"
    now = _now()
    fm["updated_at"] = now.isoformat()

    e = jarvis_brain.entry_from_frontmatter(fm, body)
    md = jarvis_brain.render_entry_markdown(e)
    new_path = jarvis_brain.brain_dir() / e.kind / pending_path.name
    jarvis_brain._atomic_write(new_path, md)
    if pending_path.exists():
        pending_path.unlink()

    new_rel = str(new_path.relative_to(jarvis_brain._workspace_root()))
    fhash = jarvis_brain._file_hash(md)
    conn = jarvis_brain.connect_index()
    try:
        # Insert as active brain entry
        conn.execute(
            """INSERT OR REPLACE INTO brain_index
               (id, path, kind, visibility, domain, title,
                created_at, updated_at, last_used_at,
                salience_base, salience_bumps, status,
                superseded_by, file_hash, embedding, embedding_dim, indexed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,'active',?,?,NULL,NULL,?)""",
            (
                e.id, new_rel, e.kind, e.visibility, e.domain, e.title,
                jarvis_brain._iso(e.created_at), jarvis_brain._iso(now), None,
                e.salience_base, e.salience_bumps, e.superseded_by,
                fhash, jarvis_brain._iso(now),
            ),
        )
        conn.execute(
            "UPDATE brain_proposals SET status='adopted', adopted_at=?, "
            "adopted_by='visible_jarvis' WHERE id=?",
            (jarvis_brain._iso(now), proposal_id),
        )
        conn.commit()
    finally:
        conn.close()

    return {"status": "ok", "id": e.id, "path": new_rel}


def discard_brain_proposal(
    proposal_id: str, *, reason: str = "",
) -> dict[str, Any]:
    """Slet en pending proposal og log reason."""
    from core.services import jarvis_brain

    conn = jarvis_brain.connect_index()
    try:
        row = conn.execute(
            "SELECT path FROM brain_proposals WHERE id = ?",
            (proposal_id,),
        ).fetchone()
        if row is None:
            return {"status": "error", "error": "not_found"}
        rel_path = row[0]
        pending_path = jarvis_brain._workspace_root() / rel_path
        if pending_path.exists():
            pending_path.unlink()
        conn.execute(
            "UPDATE brain_proposals SET status='discarded', adopted_at=?, "
            "adopted_by='visible_jarvis' WHERE id=?",
            (_now().isoformat(), proposal_id),
        )
        conn.commit()
    finally:
        conn.close()
    return {"status": "ok", "reason_logged": reason}
