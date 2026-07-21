from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from core.services.content_blocks import reconstruct_blocks_from_legacy
from core.services.tool_result_store import (
    build_tool_result_reference,
    get_tool_result,
    parse_tool_result_reference,
    save_tool_result,
)
from core.runtime.db import connect


def _load_tool_result_for_reconstruct(result_id: str) -> dict | None:
    """Serve-on-read loader: slå et gammelt tool-resultat op fra tool_result_store.
    Mapper store-formatet (nøgle ``result``) til rekonstruktionens ``content``.
    Best-effort — aldrig kast."""
    if not result_id:
        return None
    try:
        data = get_tool_result(result_id)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return {
        "tool_name": str(data.get("tool_name") or ""),
        "content": str(data.get("result") or ""),
    }


def _content_json_for_row(role: str, content: str, raw_json: object) -> list[dict]:
    """Adapter: gemt content_json parses; ellers rekonstruér fra tekst (best-effort,
    serve-on-read for gamle beskeder uden content_json)."""
    if raw_json:
        try:
            parsed = json.loads(str(raw_json))
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
    return reconstruct_blocks_from_legacy(
        role, content, load_result=_load_tool_result_for_reconstruct
    )


def create_chat_session(
    *, title: str = "New chat",
    workspace_kind: str | None = None, workspace_root: str | None = None,
    team_id: str | None = None,
) -> dict[str, object]:
    from core.runtime.db import (
        _ensure_chat_session_team_column,
        _ensure_chat_session_workspace_columns,
    )
    session_id = f"chat-{uuid4().hex}"
    created_at = datetime.now(UTC).isoformat()
    normalized_title = _normalize_title(title) or "New chat"
    with connect() as conn:
        _ensure_chat_session_workspace_columns(conn)
        _ensure_chat_session_team_column(conn)
        conn.execute(
            """
            INSERT INTO chat_sessions (session_id, title, created_at, updated_at,
                                       workspace_kind, workspace_root, team_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, normalized_title, created_at, created_at,
             (workspace_kind or None), (workspace_root or None), (team_id or None)),
        )
    return get_chat_session(session_id) or {
        "session_id": session_id,
        "title": normalized_title,
        "created_at": created_at,
        "updated_at": created_at,
        "last_message": "",
        "message_count": 0,
        "messages": [],
    }


def get_or_create_named_session(session_id: str, title: str) -> str:
    """Idempotent: sikr at en session med EKSPLICIT id findes (opret hvis ny).

    Bruges til deterministiske, roterende autonome sessioner (`auto-{origin}-{dato}`)
    så autonome runs ikke længere funneler ind i én udødelig "Autonomous"-silo. INSERT
    OR IGNORE → race-fri på tværs af api+runtime-processer. Returnerer session_id.
    Self-safe: ved fejl returneres id'et alligevel (kalder bruger det som session).
    """
    from core.runtime.db import (
        _ensure_chat_session_team_column,
        _ensure_chat_session_workspace_columns,
    )
    now = datetime.now(UTC).isoformat()
    normalized_title = _normalize_title(title) or "Autonomous"
    try:
        with connect() as conn:
            _ensure_chat_session_workspace_columns(conn)
            _ensure_chat_session_team_column(conn)
            conn.execute(
                """
                INSERT OR IGNORE INTO chat_sessions
                    (session_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, normalized_title, now, now),
            )
    except Exception:
        pass
    return session_id


def _teams():
    """Lazy-import af teams-modulet (undgår import-cyklus ved opstart)."""
    import core.services.teams as teams
    return teams


def most_recent_session_id() -> str:
    """Lightweight: session_id of the most recently updated session.

    Returns the raw session_id of the most recent session (ORDER BY updated_at
    DESC, id DESC over all sessions) via ONE query — without the per-row
    correlated subqueries + _session_summary/_preview_text formatting of every
    session that list_chat_sessions() does. Note: _session_summary renames the
    column to "id", so callers reading sessions[0]["session_id"] were silently
    getting None; this returns the real id. Used on the hot assembly path.
    """
    with connect() as conn:
        row = conn.execute(
            "SELECT session_id FROM chat_sessions ORDER BY updated_at DESC, id DESC LIMIT 1"
        ).fetchone()
    return str(row[0]) if row and row[0] else ""


def list_chat_sessions(*, user_id: str | None = None) -> list[dict[str, object]]:
    """List chat sessions, optionally filtered to one user.

    When user_id is given, only returns sessions that have AT LEAST ONE
    message stamped with that user_id. This is the privacy guard for
    multi-user JarvisX: Bjørn shouldn't see Mikkel's chats and vice
    versa. Sessions where no user_id was ever recorded (older webchat
    rows) are EXCLUDED from a filtered query — they're either ambiguous
    or owner-only and should be approached explicitly via the unfiltered
    API.

    user_id=None preserves the legacy behavior (return everything) so
    Mission Control and other internal callers aren't affected.
    """
    uid = (user_id or "").strip()
    if uid:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    s.session_id,
                    s.title,
                    s.created_at,
                    s.updated_at,
                    COALESCE((
                        SELECT content
                        FROM chat_messages m
                        WHERE m.session_id = s.session_id
                        ORDER BY m.id DESC
                        LIMIT 1
                    ), '') AS last_message,
                    COALESCE((
                        SELECT COUNT(*)
                        FROM chat_messages m2
                        WHERE m2.session_id = s.session_id
                    ), 0) AS message_count,
                    s.workspace_kind
                FROM chat_sessions s
                WHERE (
                    EXISTS (
                        SELECT 1 FROM chat_messages mu
                        WHERE mu.session_id = s.session_id
                          AND mu.user_id = ?
                    )
                    OR """ + _teams().team_scope_sql("s") + """
                )
                ORDER BY s.updated_at DESC, s.id DESC
                """,
                (uid, uid),
            ).fetchall()
        return [_session_summary(dict(row)) for row in rows]
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                s.session_id,
                s.title,
                s.created_at,
                s.updated_at,
                COALESCE((
                    SELECT content
                    FROM chat_messages m
                    WHERE m.session_id = s.session_id
                    ORDER BY m.id DESC
                    LIMIT 1
                ), '') AS last_message,
                COALESCE((
                    SELECT COUNT(*)
                    FROM chat_messages m2
                    WHERE m2.session_id = s.session_id
                ), 0) AS message_count,
                s.workspace_kind
            FROM chat_sessions s
            ORDER BY s.updated_at DESC, s.id DESC
            """
        ).fetchall()
    return [_session_summary(dict(row)) for row in rows]


def _make_snippet(content: str, query: str, width: int = 140) -> str:
    """Byg et kort uddrag centreret om første match (case-insensitive)."""
    content = (content or "").replace("\n", " ").strip()
    q = (query or "").strip().lower()
    if not q:
        return content[:width].strip()
    i = content.lower().find(q)
    if i < 0:
        return content[:width].strip()
    start = max(0, i - width // 3)
    end = min(len(content), i + len(query) + width // 2)
    snip = content[start:end].strip()
    return ("…" if start > 0 else "") + snip + ("…" if end < len(content) else "")


def search_chat_sessions(
    query: str, *, user_id: str | None = None, limit: int = 30,
) -> list[dict[str, object]]:
    """Søg sessioner på titel ELLER besked-indhold (user/assistant).

    Returnerer [{session_id, title, snippet, updated_at}], nyeste først.
    Scoping pr. bruger som list_chat_sessions: user_id sat → kun sessioner
    med mindst én besked stemplet med det user_id. user_id=None → alt.
    """
    q = (query or "").strip()
    if not q:
        return []
    like = f"%{q}%"
    lim = max(1, min(int(limit or 30), 50))
    uid = (user_id or "").strip()

    # BUNDET SØGNING (Bjørn 9. jul, "search_sessions hænger"): den gamle query brugte en KORRELERET
    # EXISTS-subquery PR. session (`content LIKE '%q%'` er ikke-indekserbar → fuld scan af
    # chat_messages × N sessioner = O(sessioner×beskeder) → minutter på en stor tabel → run/stream
    # hang, samme klasse som find_files. Nu: ÉT scan af chat_messages (nyeste-først, tidlig LIMIT så
    # SQLite kan stoppe) + separat titel-match. Plus en progress-handler-vagt der ABORTERER en løbsk
    # scan efter et fast budget, så søgningen ALDRIG kan hænge (fail-safe → delvise/tomme resultater).
    def _install_abort_budget(conn: sqlite3.Connection, max_ops: int = 8_000_000) -> None:
        state = {"n": 0}
        def _cb() -> int:
            state["n"] += 1
            return 1 if state["n"] > max_ops else 0   # !=0 → aborter query (OperationalError)
        try:
            conn.set_progress_handler(_cb, 20000)
        except Exception:
            pass

    by_session: dict[str, dict[str, object]] = {}
    with connect() as conn:
        _install_abort_budget(conn)
        # (1) besked-indholds-match — ÉT scan, nyeste-først, tidlig LIMIT.
        content_sql = (
            "SELECT m.session_id, s.title, s.updated_at, m.content AS snippet "
            "FROM chat_messages m JOIN chat_sessions s ON s.session_id = m.session_id "
            "WHERE m.content LIKE ? AND m.role IN ('user','assistant')"
        )
        params: list[object] = [like]
        if uid:
            content_sql += " AND m.user_id = ?"
            params.append(uid)
        content_sql += " ORDER BY m.id DESC LIMIT ?"
        params.append(lim * 4)   # lidt hovedrum til dedup pr. session
        # (2) titel-match — lille tabel; ved uid kræv mindst én besked fra brugeren.
        title_sql = "SELECT s.session_id, s.title, s.updated_at, NULL AS snippet FROM chat_sessions s WHERE s.title LIKE ?"
        title_params: list[object] = [like]
        if uid:
            title_sql += " AND EXISTS (SELECT 1 FROM chat_messages mu WHERE mu.session_id = s.session_id AND mu.user_id = ?)"
            title_params.append(uid)
        title_sql += " ORDER BY s.updated_at DESC, s.id DESC LIMIT ?"
        title_params.append(lim)
        try:
            rows = list(conn.execute(content_sql, tuple(params)).fetchall())
            rows += list(conn.execute(title_sql, tuple(title_params)).fetchall())
        except sqlite3.OperationalError:
            rows = []   # abort-budget ramt → fail-safe (hellere tomt end hængende)

    for row in rows:
        d = dict(row)
        sid = str(d.get("session_id") or "")
        if not sid or sid in by_session:
            continue   # nyeste vundet (content-match kommer før titel; begge er nyeste-først)
        snippet_src = str(d.get("snippet") or d.get("title") or "")
        by_session[sid] = {
            "session_id": sid,
            "title": d.get("title") or "Samtale",
            "snippet": _make_snippet(snippet_src, q),
            "updated_at": d.get("updated_at"),
        }
    out = sorted(by_session.values(), key=lambda r: str(r.get("updated_at") or ""), reverse=True)
    return out[:lim]


def get_chat_session(session_id: str) -> dict[str, object] | None:
    normalized = (session_id or "").strip()
    if not normalized:
        return None
    with connect() as conn:
        session = conn.execute(
            """
            SELECT session_id, title, created_at, updated_at,
                   workspace_kind, workspace_root
            FROM chat_sessions
            WHERE session_id = ?
            """,
            (normalized,),
        ).fetchone()
        if session is None:
            return None
        messages = conn.execute(
            """
            SELECT message_id, role, content, content_json, created_at
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (normalized,),
        ).fetchall()
    message_items = [
        {
            "id": str(row["message_id"]),
            "role": str(row["role"]),
            "content": str(row["content"]),
            "content_json": _content_json_for_row(
                str(row["role"]), str(row["content"]), row["content_json"]),
            "ts": _time_label(str(row["created_at"])),
            "created_at": str(row["created_at"]),
        }
        for row in messages
    ]
    summary = _session_summary(
        {
            **dict(session),
            "last_message": message_items[-1]["content"] if message_items else "",
            "message_count": len(message_items),
        }
    )
    return {
        **summary,
        "workspace_kind": dict(session).get("workspace_kind"),
        "workspace_root": dict(session).get("workspace_root"),
        "messages": message_items,
    }


def set_session_workspace(session_id: str, *, kind: str | None, root: str | None) -> None:
    """Bind (eller skift) en sessions Code-mode workspace."""
    from core.runtime.db import _ensure_chat_session_workspace_columns
    sid = (session_id or "").strip()
    if not sid:
        return
    with connect() as conn:
        _ensure_chat_session_workspace_columns(conn)
        conn.execute(
            "UPDATE chat_sessions SET workspace_kind = ?, workspace_root = ? WHERE session_id = ?",
            (kind or None, root or None, sid),
        )
        conn.commit()


def append_chat_message(
    *,
    session_id: str,
    role: str,
    content: str,
    created_at: str | None = None,
    tool_name: str | None = None,
    tool_arguments: dict[str, object] | None = None,
    user_id: str | None = None,
    workspace_name: str | None = None,
    reasoning_content: str = "",
    content_json: str | None = None,
) -> dict[str, object]:
    normalized_session = (session_id or "").strip()
    if not normalized_session:
        raise ValueError("session_id must not be empty")
    normalized_role = (role or "").strip()
    if normalized_role not in {"user", "assistant", "tool", "compact_marker"}:
        raise ValueError("role must be user, assistant, tool, or compact_marker")
    normalized_content = str(content or "").strip()
    if not normalized_content:
        raise ValueError("content must not be empty")

    timestamp = created_at or datetime.now(UTC).isoformat()

    # Cross-client dedup (2026-07-12): sessioner holdes af serveren og DELES på tværs
    # af live-klienter (desk chat/code, mobil-companion, jarvis-code) der mirror/stream
    # til hinanden. Den SAMME brugerbesked kan derfor lande her to gange (mirror/retry)
    # → modellen ser beskeden dobbelt ("jeg fik din besked to gange"). Verificeret i
    # prod: 249 på-hinanden-følgende identiske bruger-dubletter, nogle 3× i træk.
    # Dedup ved konvergens-punktet: hvis den SENESTE besked i sessionen er en IDENTISK
    # brugerbesked inden for vinduet (= intet assistent-svar imellem), er det en dublet
    # → returnér den eksisterende række uden at indsætte igen (og uden at dobbelt-fyre
    # feel-layer-signalerne nedenfor). Fanger IKKE ægte gentagelser: de har et
    # assistent-svar imellem, så seneste besked er 'assistant', ikke 'user'.
    if normalized_role == "user":
        try:
            _dup = _recent_duplicate_user_message(normalized_session, normalized_content, timestamp)
        except Exception:
            _dup = None
        if _dup is not None:
            print(f"[chat] dedup: droppede dublet-brugerbesked session={normalized_session[:20]} "
                  f"len={len(normalized_content)}", flush=True)
            return _dup

    # Feel-layer: let incoming user text produce a micro-resonance signal
    # BEFORE meaning-making. Fire-and-forget — never break chat persistence.
    if normalized_role == "user":
        try:
            from core.services.text_resonance import resonate
            resonate(normalized_content, source=f"chat:{normalized_session}")
        except Exception:
            pass
        # Lag 10: structural temperature stream — per-message synchronous
        # signal computation. Fire-and-forget, never block chat persistence.
        try:
            from core.services.user_temperature_engine import run_structural_stream
            run_structural_stream(
                workspace_id="default",
                message=normalized_content,
                message_at=timestamp,
            )
        except Exception:
            pass
        # emotion-trigger: warmth/playfulness/tenderness from user-message content
        try:
            from core.services.emotion_concepts_channel_triggers import (
                on_channel_message_appended,
            )
            on_channel_message_appended({
                "session_id": normalized_session,
                "message": {"role": "user", "content": normalized_content},
            })
        except Exception:
            pass

    if normalized_role == "tool" and not parse_tool_result_reference(normalized_content):
        normalized_tool_name = (tool_name or _infer_tool_name_from_content(normalized_content) or "tool").strip()
        result_id = save_tool_result(
            normalized_tool_name,
            tool_arguments or {},
            normalized_content,
            created_at=timestamp,
        )
        normalized_content = build_tool_result_reference(
            result_id,
            tool_name=normalized_tool_name,
            summary=normalized_content,
        )
    message_id = f"message-{uuid4().hex}"
    with connect() as conn:
        exists = conn.execute(
            "SELECT session_id, title FROM chat_sessions WHERE session_id = ?",
            (normalized_session,),
        ).fetchone()
        if exists is None:
            raise ValueError("chat session not found")

        # Resolve user_id + workspace_name in this priority order:
        # 1. Explicit caller-provided values (used by discord_gateway when
        #    persisting the inbound user message *before* the worker thread
        #    sets the workspace_context — without this, user-authored rows
        #    end up with empty user_id and the model can't tell speakers apart).
        # 2. Current ContextVar (set by start_autonomous_run for assistant turns).
        # 3. Empty fallback.
        _user_id = (user_id or "").strip()
        _workspace_name = (workspace_name or "").strip()
        if not _user_id or not _workspace_name:
            try:
                from core.identity.workspace_context import (
                    current_user_id as _cuid,
                    current_workspace_name as _cwn,
                )
                if not _user_id:
                    _user_id = _cuid() or ""
                if not _workspace_name:
                    _workspace_name = _cwn() or ""
            except Exception:
                pass

        conn.execute(
            """
            INSERT INTO chat_messages (message_id, session_id, role, content,
                                        user_id, workspace_name,
                                        reasoning_content, content_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (message_id, normalized_session, normalized_role, normalized_content,
             _user_id, _workspace_name, str(reasoning_content or ""),
             content_json, timestamp),
        )

        next_title = str(exists["title"])
        if normalized_role == "user" and next_title == "New chat":
            next_title = _normalize_title(normalized_content) or next_title

        conn.execute(
            """
            UPDATE chat_sessions
            SET title = ?, updated_at = ?
            WHERE session_id = ?
            """,
            (next_title, timestamp, normalized_session),
        )

    return {
        "id": message_id,
        "role": normalized_role,
        "content": normalized_content,
        "reasoning_content": str(reasoning_content or ""),
        "content_json": content_json,
        "ts": _time_label(timestamp),
        "created_at": timestamp,
    }


_DEDUP_WINDOW_SECONDS = 900  # 15 min: fanger mirror/retry + perceived-failure-resends


def _recent_duplicate_user_message(
    session_id: str, content: str, now_ts: str
) -> dict[str, object] | None:
    """Returnér den seneste besked-række HVIS den er en identisk brugerbesked inden
    for dedup-vinduet (intet assistent-svar imellem), ellers None. Self-safe."""
    with connect() as conn:
        row = conn.execute(
            """
            SELECT message_id, role, content, reasoning_content, content_json, created_at
            FROM chat_messages
            WHERE session_id = ? AND role != 'compact_marker'
            ORDER BY id DESC LIMIT 1
            """,
            (session_id,),
        ).fetchone()
    if row is None or str(row["role"]) != "user" or str(row["content"]) != content:
        return None
    try:
        prev = datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00"))
        now = datetime.fromisoformat(str(now_ts).replace("Z", "+00:00"))
        if (now - prev).total_seconds() > _DEDUP_WINDOW_SECONDS:
            return None  # for gammel → behandl som ny (sikkerheds-ventil)
    except Exception:
        pass  # kan ikke parse tid → seneste er identisk user, dedup konservativt
    return {
        "id": str(row["message_id"]),
        "role": "user",
        "content": content,
        "reasoning_content": str(row["reasoning_content"] or ""),
        "content_json": row["content_json"],
        "ts": _time_label(str(row["created_at"])),
        "created_at": str(row["created_at"]),
    }


def _infer_tool_name_from_content(content: str) -> str:
    normalized = str(content or "").strip()
    if normalized.startswith("[") and "]:" in normalized:
        return normalized[1:].split("]:", 1)[0].strip()
    return ""


def recent_chat_session_messages(session_id: str, *, limit: int = 12) -> list[dict[str, str]]:
    normalized = (session_id or "").strip()
    if not normalized:
        return []
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content, created_at, user_id, reasoning_content
            FROM chat_messages
            WHERE session_id = ? AND role != 'compact_marker'
            ORDER BY id DESC
            LIMIT ?
            """,
            (normalized, max(limit, 1)),
        ).fetchall()
    return [
        {
            "role": str(row["role"]),
            "content": str(row["content"]),
            "created_at": str(row["created_at"]),
            "user_id": str(row["user_id"] or ""),
            "reasoning_content": str(row["reasoning_content"] or ""),
        }
        for row in reversed(rows)
    ]


def chat_session_messages_since_last_compact(
    session_id: str,
    *,
    max_total: int = 4000,
) -> list[dict[str, str]]:
    """Hent ALT efter seneste compact_marker (eller hele session hvis ingen).

    2026-06-09 (cache-fix): den anden variant
    `recent_chat_session_messages_by_user_turns` har sliding-window adfærd
    der bryder DeepSeek prefix-cache hver tur (ældste turn dropped + nyeste
    appended → 0% transcript-cache). Den her er growing-window: prefix er
    stabilt mellem turns, kun nye beskeder ændrer det. Når compact rammer
    (200K tokens default), opdateres compact_marker og dette starter forfra
    med kortere historie.

    Net effekt: cache hit rate på transcript-delen forventes >80% mellem
    compactions, vs ~0% med sliding-window.
    """
    normalized = (session_id or "").strip()
    if not normalized:
        return []
    with connect() as conn:
        # Find seneste compact_marker id (hvis nogen)
        marker_row = conn.execute(
            "SELECT id FROM chat_messages WHERE session_id = ? "
            "AND role = 'compact_marker' ORDER BY id DESC LIMIT 1",
            (normalized,),
        ).fetchone()
        if marker_row is not None:
            since_id = int(marker_row["id"])
            rows = conn.execute(
                """
                SELECT id, role, content, created_at, user_id, reasoning_content
                FROM chat_messages
                WHERE session_id = ? AND role != 'compact_marker' AND id > ?
                ORDER BY id ASC LIMIT ?
                """,
                (normalized, since_id, max_total),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, role, content, created_at, user_id, reasoning_content
                FROM chat_messages
                WHERE session_id = ? AND role != 'compact_marker'
                ORDER BY id ASC LIMIT ?
                """,
                (normalized, max_total),
            ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "role": str(row["role"]),
            "content": str(row["content"]),
            "created_at": str(row["created_at"]),
            "user_id": str(row["user_id"] or ""),
            "reasoning_content": str(row["reasoning_content"] or ""),
        }
        for row in rows
    ]


def recent_chat_session_messages_by_user_turns(
    session_id: str,
    *,
    user_turns: int = 30,
    max_total: int = 4000,
) -> list[dict[str, str]]:
    """Hent de seneste N *user-turns* og alt der hører til dem.

    Anchor er user-beskeder: vi finder id'et på den N'te-seneste user
    message og returnerer alt med id >= det (user, assistant, tool —
    `compact_marker` ekskluderes). Det betyder at "30 turns" rent
    faktisk = 30 reelle samtale-runder, ikke 30 tilfældige rows hvor
    de fleste kan være interne tool-resultater fra en enkelt agentic
    runde.

    Baggrund (2026-06-09): den gamle `recent_chat_session_messages(
    limit=60)` tællte alle roller. I tool-tunge sessions (3-8 tool
    calls per assistant-svar) endte 54 ud af 60 slots med at være
    tool-rows, så kun ~6 ægte user/assistant turns overlevede ud i
    prompt'en. Det er den arkitektoniske rod til "Jarvis husker kun
    5-6 beskeder afbag."

    `max_total` er en hård safety-cap der bevarer de *nyeste* rows
    hvis en enkelt user-turn fylder absurd meget (autonomous loop,
    skill-chain). 4000 rows × selv 1500 chars gennemsnit = ~6 MB, og
    derefter rammer vi auto-compact alligevel.
    """
    normalized = (session_id or "").strip()
    if not normalized:
        return []
    user_turns = max(user_turns, 1)
    with connect() as conn:
        anchor_row = conn.execute(
            """
            SELECT id FROM chat_messages
            WHERE session_id = ? AND role = 'user'
            ORDER BY id DESC LIMIT 1 OFFSET ?
            """,
            (normalized, user_turns - 1),
        ).fetchone()
        if anchor_row is None:
            # Færre user-turns end ønsket — tag bare alle non-marker rows
            rows = conn.execute(
                """
                SELECT role, content, created_at, user_id, reasoning_content
                FROM chat_messages
                WHERE session_id = ? AND role != 'compact_marker'
                ORDER BY id ASC
                LIMIT ?
                """,
                (normalized, max_total),
            ).fetchall()
        else:
            anchor_id = int(anchor_row["id"])
            rows = conn.execute(
                """
                SELECT role, content, created_at, user_id, reasoning_content
                FROM chat_messages
                WHERE session_id = ? AND role != 'compact_marker' AND id >= ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (normalized, anchor_id, max_total),
            ).fetchall()
    return [
        {
            "role": str(row["role"]),
            "content": str(row["content"]),
            "created_at": str(row["created_at"]),
            "user_id": str(row["user_id"] or ""),
            "reasoning_content": str(row["reasoning_content"] or ""),
        }
        for row in rows
    ]


def _ensure_compact_marker_git_sha_column() -> None:
    """Add git_sha column to chat_messages if it doesn't exist (idempotent migration)."""
    try:
        from core.runtime.db import connect as _connect
        with _connect() as _conn:
            _conn.execute(
                "ALTER TABLE chat_messages ADD COLUMN git_sha TEXT NOT NULL DEFAULT ''"
            )
    except Exception:
        pass  # Column already exists


def store_compact_marker(
    session_id: str,
    summary_text: str,
    git_sha: str = "",
) -> str:
    """Store a compact marker for the session. Returns the marker message_id.

    If git_sha is provided, it's stored alongside the marker for later
    freshness checks (Lag B — see core/context/compact_ground_truth.py).
    """
    _ensure_compact_marker_git_sha_column()
    normalized_session = (session_id or "").strip()
    if not normalized_session:
        raise ValueError("session_id must not be empty")
    normalized_content = str(summary_text or "").strip()
    if not normalized_content:
        raise ValueError("summary_text must not be empty")
    normalized_git_sha = (git_sha or "").strip()
    timestamp = datetime.now(UTC).isoformat()
    marker_id = f"compact-{uuid4().hex}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages (message_id, session_id, role, content, git_sha, created_at)
            VALUES (?, ?, 'compact_marker', ?, ?, ?)
            """,
            (marker_id, normalized_session, normalized_content, normalized_git_sha, timestamp),
        )
    return marker_id


def get_compact_marker_with_sha(session_id: str) -> tuple[str | None, str | None]:
    """Return (summary, git_sha) of the most recent compact marker, or (None, None)."""
    try:
        _ensure_compact_marker_git_sha_column()
    except Exception:
        pass
    normalized = (session_id or "").strip()
    if not normalized:
        return (None, None)
    with connect() as conn:
        row = conn.execute(
            """
            SELECT content, git_sha FROM chat_messages
            WHERE session_id = ? AND role = 'compact_marker'
            ORDER BY id DESC
            LIMIT 1
            """,
            (normalized,),
        ).fetchone()
    if row:
        return (str(row["content"]), str(row["git_sha"]) if row["git_sha"] else None)
    return (None, None)


def get_compact_marker(session_id: str) -> str | None:
    """Return the most recent compact marker summary for the session, or None."""
    normalized = (session_id or "").strip()
    if not normalized:
        return None
    with connect() as conn:
        row = conn.execute(
            """
            SELECT content FROM chat_messages
            WHERE session_id = ? AND role = 'compact_marker'
            ORDER BY id DESC
            LIMIT 1
            """,
            (normalized,),
        ).fetchone()
    return str(row["content"]) if row else None


def recent_chat_tool_messages(session_id: str, *, limit: int = 6) -> list[dict[str, str]]:
    normalized = (session_id or "").strip()
    if not normalized:
        return []
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content, created_at
            FROM chat_messages
            WHERE session_id = ? AND role = 'tool'
            ORDER BY id DESC
            LIMIT ?
            """,
            (normalized, max(limit, 1)),
        ).fetchall()
    return [
        {
            "role": str(row["role"]),
            "content": str(row["content"]),
            "created_at": str(row["created_at"]),
        }
        for row in reversed(rows)
    ]


def rename_chat_session(session_id: str, *, title: str) -> dict[str, object] | None:
    normalized = (session_id or "").strip()
    new_title = _normalize_title(title) or "New chat"
    if not normalized:
        return None
    now = datetime.now(UTC).isoformat()
    with connect() as conn:
        conn.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE session_id = ?",
            (new_title, now, normalized),
        )
    return get_chat_session(normalized)


def delete_chat_session(session_id: str) -> bool:
    normalized = (session_id or "").strip()
    if not normalized:
        return False
    with connect() as conn:
        conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (normalized,))
        conn.execute("DELETE FROM chat_sessions WHERE session_id = ?", (normalized,))
    return True


def _session_summary(row: dict[str, object]) -> dict[str, object]:
    return {
        "id": str(row.get("session_id") or ""),
        "title": str(row.get("title") or "New chat"),
        "created_at": str(row.get("created_at") or ""),
        "updated_at": str(row.get("updated_at") or ""),
        "last_message": _preview_text(str(row.get("last_message") or "")) or "Ready",
        "message_count": int(row.get("message_count") or 0),
        "workspace_kind": (str(row.get("workspace_kind")) if row.get("workspace_kind") else None),
    }


def _normalize_title(value: str) -> str:
    text = " ".join((value or "").split()).strip()
    if not text:
        return ""
    return text[:48] + ("…" if len(text) > 48 else "")


def _preview_text(value: str) -> str:
    text = " ".join((value or "").split()).strip()
    if not text:
        return ""
    return text[:64] + ("…" if len(text) > 64 else "")


def _time_label(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return value
    return dt.astimezone().strftime("%I:%M %p")


def parse_channel_from_session_title(title: str | None) -> tuple[str, str | None]:
    """Parse channel type and detail from a session title.

    Returns (channel_type, channel_detail) where channel_type is one of:
    'discord', 'telegram', 'webchat', 'unknown'.

    Examples:
        "Discord DM"         -> ("discord", "DM")
        "Discord #123456789" -> ("discord", "#123456789")
        "Telegram DM"        -> ("telegram", "DM")
        "New chat"           -> ("webchat", None)
        None                 -> ("webchat", None)
        "Something weird"    -> ("unknown", None)
    """
    if not title or title.strip() in ("New chat", ""):
        return ("webchat", None)
    t = title.strip()
    if t == "Discord DM":
        return ("discord", "DM")
    if t.startswith("Discord #"):
        return ("discord", t[len("Discord "):])
    if t.startswith("Discord"):
        return ("discord", None)
    if t == "Telegram DM":
        return ("telegram", "DM")
    if t.startswith("Telegram"):
        return ("telegram", None)
    return ("unknown", None)


def get_session_owner(session_id: str) -> str | None:
    """Ejeren = user_id paa den seneste besked i sessionen der HAR et stempel.
    Returnerer None for ustemplede (legacy) sessioner."""
    sid = (session_id or "").strip()
    if not sid:
        return None
    from core.runtime.db import connect
    with connect() as c:
        row = c.execute(
            """SELECT user_id FROM chat_messages
               WHERE session_id=? AND user_id IS NOT NULL AND user_id<>''
               ORDER BY rowid DESC LIMIT 1""",
            (sid,),
        ).fetchone()
    return row[0] if row else None
