"""Experience substrate — embedding-retrieval learning layer.

Three layers:
  Lag 1: experience_episodes table (append-only, structured fields)
  Lag 2: ChromaDB embedding index (auto-embed at insert, retrieve by similarity)
  Lag 3: _experience_substrate prompt section (you see past similar episodes)

Design: "Giv mig dataen, lad mig dømme" — shows similarity scores but
does NOT filter by threshold. Jarvis sees the similarity and decides
if the retrieved case is relevant.

Added 2026-05-09 per Runtime Decision Policy spec (Claude review iteration).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.config import STATE_DIR

CHROMADB_DIR = Path(STATE_DIR) / "chromadb_experience"
COLLECTION_NAME = "experience_episodes"
EMBED_MODEL = "all-MiniLM-L6-v2"  # sentence-transformers model, ~22MB, runs on CPU
MAX_RETRIEVAL = 5  # top-K episodes to retrieve for prompt section


# ── Lazy singletons ────────────────────────────────────────────────

def _get_chroma_collection():
    """Get or create the ChromaDB collection for experience episodes."""
    import chromadb
    client = chromadb.PersistentClient(path=str(CHROMADB_DIR))
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return collection


def _get_embedder():
    """Get or create the sentence-transformers embedder (lazy load)."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL)


# ── Context encoder ────────────────────────────────────────────────
# Builds the structured context string that gets embedded.
# Format per Claude's refinement: intent + active_loops + last_tools + session_phase

def build_context_for_embedding(
    *,
    context_intent: str | None = None,
    active_loops: list[str] | None = None,
    last_tools: list[str] | None = None,
    session_phase: str | None = None,
) -> str:
    """Build a structured context string for embedding similarity.

    Matches on *situation shape*, not word overlap.
    """
    parts = []
    if context_intent:
        parts.append(f"intent: {context_intent}")
    if active_loops:
        parts.append(f"active_loops: {' | '.join(active_loops)}")
    if last_tools:
        parts.append(f"last_tools: {' | '.join(last_tools)}")
    if session_phase:
        parts.append(f"session_phase: {session_phase}")
    return " | ".join(parts)


# ── Episode recording ──────────────────────────────────────────────

def record_episode(
    *,
    session_id: str,
    turn_id: str | None = None,
    context_text: str,
    context_intent: str | None = None,
    active_loops: list[str] | None = None,
    last_tools: list[str] | None = None,
    session_phase: str | None = None,
    tool_sequence: list[str],
    outcome_signals: dict[str, Any],
    user_corrected: bool = False,
) -> str:
    """Record a new experience episode: insert to DB + embed to ChromaDB.

    Returns the episode_id.
    """
    episode_id = str(uuid.uuid4())
    created_at = datetime.now(UTC).isoformat()

    # Build structured context for embedding
    embed_text = build_context_for_embedding(
        context_intent=context_intent,
        active_loops=active_loops,
        last_tools=last_tools,
        session_phase=session_phase,
    )
    # Fallback to raw context_text if no structured fields
    if not embed_text.strip():
        embed_text = context_text

    # Compute embedding
    embedder = _get_embedder()
    embedding = embedder.encode(embed_text, normalize_embeddings=True).tolist()

    # Insert to ChromaDB
    collection = _get_chroma_collection()
    chromadb_id = f"ep_{episode_id}"
    collection.add(
        ids=[chromadb_id],
        embeddings=[embedding],
        metadatas=[{
            "episode_id": episode_id,
            "session_id": session_id,
            "context_intent": context_intent or "",
            "session_phase": session_phase or "",
            "user_corrected": int(user_corrected),
            "tool_count": len(tool_sequence),
            "created_at": created_at,
        }],
        documents=[context_text[:2000]],  # cap to avoid huge docs
    )

    # Insert to SQLite
    from core.runtime.db import connect
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO experience_episodes (
                episode_id, session_id, turn_id,
                context_text, context_intent,
                active_loops_json, last_tools_json, session_phase,
                tool_sequence_json, outcome_signals_json,
                user_corrected, chromadb_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                episode_id,
                session_id,
                turn_id,
                context_text[:2000],
                context_intent,
                json.dumps(active_loops or []),
                json.dumps(last_tools or []),
                session_phase,
                json.dumps(tool_sequence),
                json.dumps(outcome_signals),
                int(user_corrected),
                chromadb_id,
                created_at,
            ),
        )

    return episode_id


# ── Retrieval ──────────────────────────────────────────────────────

def retrieve_similar_episodes(
    *,
    context_intent: str | None = None,
    active_loops: list[str] | None = None,
    last_tools: list[str] | None = None,
    session_phase: str | None = None,
    context_text: str = "",
    k: int = MAX_RETRIEVAL,
    min_score: float = 0.0,
) -> list[dict[str, Any]]:
    """Retrieve top-K similar experience episodes from ChromaDB.

    Returns list of dicts with:
        episode_id, session_id, context_text, context_intent, session_phase,
        tool_sequence, outcome_signals, user_corrected, similarity, created_at

    Returns empty list on cold start (no episodes yet) or no matches.
    """
    embed_text = build_context_for_embedding(
        context_intent=context_intent,
        active_loops=active_loops,
        last_tools=last_tools,
        session_phase=session_phase,
    )
    if not embed_text.strip():
        embed_text = context_text
    if not embed_text.strip():
        return []

    try:
        embedder = _get_embedder()
        query_emb = embedder.encode(embed_text, normalize_embeddings=True).tolist()

        collection = _get_chroma_collection()
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=k,
            include=["metadatas", "documents", "distances"],
        )
    except Exception:
        return []

    if not results or not results.get("ids") or not results["ids"][0]:
        return []

    episodes = []
    from core.runtime.db import connect
    with connect() as conn:
        for i, chroma_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i] if results.get("metadatas") else {}
            doc = results["documents"][0][i] if results.get("documents") else ""
            distance = results["distances"][0][i] if results.get("distances") else 1.0
            similarity = 1.0 - distance  # cosine distance → similarity

            if similarity < min_score:
                continue

            episode_id = meta.get("episode_id", "")
            if not episode_id:
                continue

            # Fetch full row from DB for details
            row = conn.execute(
                "SELECT * FROM experience_episodes WHERE episode_id = ?",
                (episode_id,),
            ).fetchone()
            if not row:
                continue

            episodes.append({
                "episode_id": row["episode_id"],
                "session_id": row["session_id"],
                "context_text": row["context_text"],
                "context_intent": row["context_intent"],
                "session_phase": row["session_phase"],
                "tool_sequence": json.loads(row["tool_sequence_json"] or "[]"),
                "outcome_signals": json.loads(row["outcome_signals_json"] or "{}"),
                "user_corrected": bool(row["user_corrected"]),
                "similarity": round(similarity, 3),
                "created_at": row["created_at"],
            })

    return episodes


# ── Prompt section builder ─────────────────────────────────────────

def build_experience_substrate_section(
    *,
    context_intent: str | None = None,
    active_loops: list[str] | None = None,
    last_tools: list[str] | None = None,
    session_phase: str | None = None,
    user_message: str = "",
    k: int = MAX_RETRIEVAL,
) -> str | None:
    """Build the _experience_substrate prompt section.

    Shows top-K past similar episodes with similarity scores.
    Designed to be injected into visible prompt as awareness section.

    Returns None if cold start (no episodes) — silent skip.
    """
    episodes = retrieve_similar_episodes(
        context_intent=context_intent,
        active_loops=active_loops,
        last_tools=last_tools,
        session_phase=session_phase,
        context_text=user_message,
        k=k,
    )

    if not episodes:
        return None

    lines = []
    lines.append("[EXPERIENCE SUBSTRATE]")
    lines.append(f"Past {len(episodes)} similar situations (cosine similarity):")

    for i, ep in enumerate(episodes, 1):
        sim = ep["similarity"]
        intent = ep["context_intent"] or "—"
        phase = ep["session_phase"] or "—"
        tools = ep["tool_sequence"]
        outcome = ep["outcome_signals"]
        corrected = " ⚠ CORRECTED" if ep["user_corrected"] else ""

        # Compact outcome summary
        outcome_parts = []
        for key in ("tick_quality", "decision_review_verdict", "tool_errors"):
            val = outcome.get(key)
            if val is not None and val != "" and val != "null":
                outcome_parts.append(f"{key}={val}")
        outcome_str = ", ".join(outcome_parts) if outcome_parts else "—"

        tool_str = ", ".join(tools[-3:]) if tools else "—"
        tool_str = tool_str[:80]  # cap

        lines.append(
            f"  [{i}] sim={sim:.2f} | intent: {intent} | phase: {phase} "
            f"| tools: {tool_str} | outcome: {{{outcome_str}}}{corrected}"
        )

    return "\n".join(lines) + "\n"


