"""search_sessions tool — cross-channel session search with keyword and semantic modes."""
from __future__ import annotations

from typing import Any

from core.runtime.db import connect
from core.services.chat_sessions import parse_channel_from_session_title

TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_sessions",
        "description": (
            "Search across all past chat sessions from all channels (Discord, Telegram, webchat). "
            "Supports keyword matching and semantic similarity search. "
            "Use to recall what was discussed on a specific channel, or to find conversations about a topic."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for — a topic, phrase, or concept.",
                },
                "mode": {
                    "type": "string",
                    "enum": ["keyword", "semantic", "both"],
                    "description": "Search mode. 'keyword' = exact phrase match, 'semantic' = meaning-based, 'both' = combined (default).",
                },
                "channel": {
                    "type": "string",
                    "enum": ["discord", "telegram", "webchat", "all"],
                    "description": "Filter by channel. Default: 'all'.",
                },
                "since": {
                    "type": "string",
                    "description": "Only return results after this ISO date, e.g. '2026-04-01'.",
                },
                "until": {
                    "type": "string",
                    "description": "Only return results before this ISO date, e.g. '2026-04-20'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 10, max 30).",
                },
            },
            "required": ["query"],
        },
    },
}

_CHANNEL_TITLE_PATTERNS: dict[str, str] = {
    "discord": "Discord%",
    "telegram": "Telegram%",
    "webchat": "New chat",
}


def _channel_title_filter(channel: str) -> tuple[str, list[Any]]:
    if channel == "all" or channel not in _CHANNEL_TITLE_PATTERNS:
        return ("", [])
    pattern = _CHANNEL_TITLE_PATTERNS[channel]
    if channel == "webchat":
        return ("AND (s.title = ? OR s.title IS NULL)", [pattern])
    return ("AND s.title LIKE ?", [pattern])


def _row_to_result(row: Any, *, match_type: str) -> dict[str, Any]:
    content = str(row["content"] or "")
    title = str(row["session_title"] or row["session_id"] or "")
    channel_type, channel_detail = parse_channel_from_session_title(title)
    return {
        "message_id": row["message_id"],
        "session_id": row["session_id"],
        "session_title": title,
        "channel": channel_type,
        "channel_detail": channel_detail,
        "role": row["role"],
        "content": content[:2000] + ("…" if len(content) > 2000 else ""),
        "created_at": str(row["created_at"] or "")[:19],
        "match_type": match_type,
    }


def _keyword_search(
    query: str,
    *,
    channel: str,
    since: str | None,
    until: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    channel_clause, channel_params = _channel_title_filter(channel)
    date_clauses: list[str] = []
    date_params: list[str] = []
    if since:
        date_clauses.append("AND m.created_at >= ?")
        date_params.append(since)
    if until:
        date_clauses.append("AND m.created_at <= ?")
        date_params.append(until)

    sql = f"""
        SELECT m.message_id, m.role, m.content, m.created_at, m.session_id,
               s.title AS session_title
        FROM chat_messages m
        LEFT JOIN chat_sessions s ON s.session_id = m.session_id
        WHERE m.content LIKE ?
          AND m.role IN ('user', 'assistant')
          {channel_clause}
          {' '.join(date_clauses)}
        ORDER BY m.id DESC
        LIMIT ?
    """
    params: list[Any] = [f"%{query}%"] + channel_params + date_params + [limit]

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [_row_to_result(row, match_type="keyword") for row in rows]


def _embed_query(text: str) -> list[float] | None:
    """Embed text via Ollama. Returns None if unavailable."""
    try:
        import json
        import urllib.request

        payload = json.dumps({"model": "nomic-embed-text", "prompt": text}).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/embeddings",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())["embedding"]
    except Exception:
        return None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _semantic_search(
    query: str,
    *,
    channel: str,
    since: str | None,
    until: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    query_embedding = _embed_query(query)
    if query_embedding is None:
        return []

    channel_clause, channel_params = _channel_title_filter(channel)
    date_clauses: list[str] = []
    date_params: list[str] = []
    if since:
        date_clauses.append("AND m.created_at >= ?")
        date_params.append(since)
    if until:
        date_clauses.append("AND m.created_at <= ?")
        date_params.append(until)

    sql = f"""
        SELECT m.message_id, m.role, m.content, m.created_at, m.session_id,
               s.title AS session_title
        FROM chat_messages m
        LEFT JOIN chat_sessions s ON s.session_id = m.session_id
        WHERE m.role IN ('user', 'assistant')
          {channel_clause}
          {' '.join(date_clauses)}
        ORDER BY m.id DESC
        LIMIT 300
    """
    params: list[Any] = channel_params + date_params

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    if not rows:
        return []

    scored: list[tuple[float, Any]] = []
    for row in rows:
        content = str(row["content"] or "")[:800]
        row_embedding = _embed_query(content)
        if row_embedding is None:
            continue
        score = _cosine_similarity(query_embedding, row_embedding)
        scored.append((score, row))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [_row_to_result(row, match_type="semantic") for _, row in scored[:limit]]


def _merge_results(
    keyword_results: list[dict],
    semantic_results: list[dict],
    limit: int,
) -> list[dict]:
    seen: set[str] = set()
    merged: list[dict] = []
    for r in semantic_results:
        mid = r["message_id"]
        if mid not in seen:
            seen.add(mid)
            merged.append({**r, "match_type": "semantic"})
    for r in keyword_results:
        mid = r["message_id"]
        if mid not in seen:
            seen.add(mid)
            merged.append({**r, "match_type": "keyword"})
        else:
            for m in merged:
                if m["message_id"] == mid:
                    m["match_type"] = "both"
    return merged[:limit]


def exec_search_sessions(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query") or "").strip()
    if not query:
        return {"status": "error", "error": "query is required"}

    mode = str(args.get("mode") or "both")
    channel = str(args.get("channel") or "all")
    since = args.get("since") or None
    until = args.get("until") or None
    limit = min(int(args.get("limit") or 10), 30)

    try:
        keyword_results: list[dict] = []
        semantic_results: list[dict] = []
        fallback_note = ""

        if mode in ("keyword", "both"):
            keyword_results = _keyword_search(
                query, channel=channel, since=since, until=until, limit=limit
            )

        if mode in ("semantic", "both"):
            semantic_results = _semantic_search(
                query, channel=channel, since=since, until=until, limit=limit
            )
            if not semantic_results and mode == "semantic":
                fallback_note = " (Ollama unavailable, no semantic results)"
            elif not semantic_results and mode == "both":
                fallback_note = " (semantic unavailable, keyword only)"

        if mode == "both":
            results = _merge_results(keyword_results, semantic_results, limit)
        elif mode == "semantic":
            results = semantic_results or keyword_results
        else:
            results = keyword_results

        if not results:
            return {
                "status": "ok",
                "count": 0,
                "text": f"No sessions found matching '{query}'{fallback_note}",
                "results": [],
            }

        lines = [f"Found {len(results)} result(s) for '{query}'{fallback_note}:\n"]
        for r in results:
            ts = r["created_at"][:16]
            ch = r["channel_detail"] or r["channel"]
            lines.append(f"[{ts}] {r['role'].upper()} via {ch} ({r['match_type']}):\n{r['content']}\n")

        return {
            "status": "ok",
            "count": len(results),
            "results": results,
            "text": "\n".join(lines),
        }

    except Exception as exc:
        return {"status": "error", "error": str(exc)}
