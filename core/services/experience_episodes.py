"""Experience-episode collector + retrieval — embedding-based learning substrate.

Lag 1+2 of the Runtime Decision Policy design (2026-05-09).

Append-only log of (situation, tool-choice, outcome) tuples, embedded
via sentence-transformers and indexed in ChromaDB. At prompt-build
time, the visible-lane queries top-K nearest-neighbour past episodes
and surfaces them as substrate (Lag 3 — see prompt_contract.py).

Why retrieval instead of a classifier:
- 140 ground-truth labels available — well below classifier threshold
- Retrieval works from ~50 examples up
- LLM can reason about retrieved cases (substrate) vs. opaque scores
- Append-only: no training daemon, no GPU, no hot-swap, no drift
- Scales 140 → 14,000 → 140,000 with no architecture change

Public API:
    record_episode(...)         — Lag 1 collector entry point
    retrieve_similar(...)       — Lag 2 retrieval primitive (used by Lag 3)
    format_episode_for_prompt() — helper for substrate rendering

The chromadb collection lives at:
    ~/.jarvis-v2/workspaces/<workspace>/runtime/experience_chroma/
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────────
# Lazy singletons — embedding model + chroma client
# ───────────────────────────────────────────────────────────────────────

_EMBED_MODEL = None
_EMBED_LOCK = threading.Lock()
_CHROMA_CLIENT = None
_CHROMA_COLLECTION = None
_CHROMA_LOCK = threading.Lock()

# all-MiniLM-L6-v2 = 384-dim, ~80MB, fast on CPU. Same model the existing
# associative_recall path uses, so we share weights if it's already loaded.
_EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_COLLECTION_NAME = "experience_episodes"


def _get_chroma_path() -> Path:
    from core.identity.workspace_bootstrap import ensure_default_workspace

    workspace = ensure_default_workspace()
    path = workspace / "runtime" / "experience_chroma"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_embed_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is not None:
        return _EMBED_MODEL
    with _EMBED_LOCK:
        if _EMBED_MODEL is None:
            from sentence_transformers import SentenceTransformer
            _EMBED_MODEL = SentenceTransformer(_EMBED_MODEL_NAME)
    return _EMBED_MODEL


def _get_collection():
    global _CHROMA_CLIENT, _CHROMA_COLLECTION
    if _CHROMA_COLLECTION is not None:
        return _CHROMA_COLLECTION
    with _CHROMA_LOCK:
        if _CHROMA_COLLECTION is None:
            import chromadb
            _CHROMA_CLIENT = chromadb.PersistentClient(path=str(_get_chroma_path()))
            _CHROMA_COLLECTION = _CHROMA_CLIENT.get_or_create_collection(
                name=_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
    return _CHROMA_COLLECTION


# ───────────────────────────────────────────────────────────────────────
# Context-text builder — the "situation shape" that gets embedded
# ───────────────────────────────────────────────────────────────────────


def build_context_text(
    *,
    intent: str,
    active_loops: list[str] | None = None,
    last_tools: list[str] | None = None,
    session_phase: str | None = None,
) -> str:
    """Render the structured situation into the text we embed.

    Putting fields as labeled key:value lines on separate lines gives the
    embedder strong signal on each component (intent matters most, then
    active loops, then recent tool sequence). Raw user-message would be
    too noisy — different wordings of the same intent should retrieve
    each other.
    """
    parts = [f"intent: {(intent or '').strip()[:240]}"]
    if active_loops:
        parts.append("active_loops: " + ", ".join(str(x).strip()[:80] for x in active_loops[:3]))
    if last_tools:
        parts.append("last_tools: " + ", ".join(str(x).strip()[:40] for x in last_tools[:5]))
    if session_phase:
        parts.append(f"session_phase: {str(session_phase).strip()[:30]}")
    return "\n".join(parts)


# ───────────────────────────────────────────────────────────────────────
# Lag 1 — record_episode (collector hook)
# ───────────────────────────────────────────────────────────────────────


def record_episode(
    *,
    session_id: str,
    turn_id: str | None,
    intent: str,
    active_loops: list[str] | None = None,
    last_tools: list[str] | None = None,
    session_phase: str | None = None,
    tool_sequence: list[str] | None = None,
    outcome_signals: dict[str, Any] | None = None,
    user_corrected: bool = False,
) -> str | None:
    """Persist one episode to DB + chroma. Returns episode_id on success.

    Idempotent across restarts: each call generates a new episode_id.
    Failures are logged and swallowed — we never want this to crash a
    visible-run.
    """
    try:
        episode_id = f"ep-{uuid4().hex[:12]}"
        context_text = build_context_text(
            intent=intent,
            active_loops=active_loops,
            last_tools=last_tools,
            session_phase=session_phase,
        )

        from core.runtime.db import connect

        with connect() as c:
            c.execute(
                """
                INSERT INTO experience_episodes (
                    episode_id, session_id, turn_id, context_text,
                    context_intent, active_loops_json, last_tools_json,
                    session_phase, tool_sequence_json, outcome_signals_json,
                    user_corrected, chromadb_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    episode_id,
                    session_id,
                    turn_id or "",
                    context_text,
                    str(intent or "")[:240],
                    json.dumps(active_loops or [], ensure_ascii=False),
                    json.dumps(last_tools or [], ensure_ascii=False),
                    session_phase or "",
                    json.dumps(tool_sequence or [], ensure_ascii=False),
                    json.dumps(outcome_signals or {}, ensure_ascii=False),
                    1 if user_corrected else 0,
                    episode_id,  # chromadb_id == episode_id for simplicity
                    datetime.now(UTC).isoformat(),
                ),
            )
            c.commit()

        # Embed + insert into chroma. Done after DB commit so the row is
        # durable even if embedding fails (chroma can be rebuilt later).
        try:
            model = _get_embed_model()
            embedding = model.encode([context_text], normalize_embeddings=True)[0].tolist()
            collection = _get_collection()
            collection.upsert(
                ids=[episode_id],
                embeddings=[embedding],
                documents=[context_text],
                metadatas=[{
                    "session_id": session_id,
                    "turn_id": turn_id or "",
                    "session_phase": session_phase or "",
                    "user_corrected": bool(user_corrected),
                    "tool_sequence": ", ".join(tool_sequence or [])[:200],
                    "created_at": datetime.now(UTC).isoformat(),
                }],
            )
        except Exception as exc:
            logger.warning("experience_episodes: chroma upsert failed: %s", exc)

        return episode_id
    except Exception as exc:
        logger.warning("experience_episodes: record failed: %s", exc)
        return None


# ───────────────────────────────────────────────────────────────────────
# Lag 2 — retrieve_similar (retrieval primitive)
# ───────────────────────────────────────────────────────────────────────


def retrieve_similar(
    *,
    intent: str,
    active_loops: list[str] | None = None,
    last_tools: list[str] | None = None,
    session_phase: str | None = None,
    k: int = 5,
) -> list[dict[str, Any]]:
    """Return up to K nearest-neighbour past episodes for the current shape.

    Each result dict has:
        episode_id, similarity (cosine 0-1), context_text,
        tool_sequence (list), outcome_signals (dict),
        user_corrected (bool), age_minutes (int), session_phase

    Returns [] on any failure — never raises into the prompt path.
    """
    try:
        query_text = build_context_text(
            intent=intent,
            active_loops=active_loops,
            last_tools=last_tools,
            session_phase=session_phase,
        )
        model = _get_embed_model()
        q_emb = model.encode([query_text], normalize_embeddings=True)[0].tolist()
        collection = _get_collection()
        # k_eff: don't ask for more than the collection has
        try:
            count = collection.count()
        except Exception:
            count = 0
        if count == 0:
            return []
        k_eff = max(1, min(int(k), count))
        result = collection.query(
            query_embeddings=[q_emb],
            n_results=k_eff,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        logger.debug("experience_episodes: retrieve failed: %s", exc)
        return []

    ids_list = (result.get("ids") or [[]])[0]
    if not ids_list:
        return []

    distances = (result.get("distances") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]

    # Hydrate full episode rows from DB for tool_sequence + outcome_signals.
    out: list[dict[str, Any]] = []
    try:
        from core.runtime.db import connect

        placeholders = ",".join("?" for _ in ids_list)
        with connect() as c:
            rows = {
                r["episode_id"]: r
                for r in c.execute(
                    f"SELECT * FROM experience_episodes WHERE episode_id IN ({placeholders})",
                    ids_list,
                ).fetchall()
            }
    except Exception:
        rows = {}

    now = datetime.now(UTC)
    for i, ep_id in enumerate(ids_list):
        # cosine distance → similarity (1 - d); chromadb returns squared
        # distance for some configs, but we set hnsw:space=cosine.
        try:
            similarity = max(0.0, 1.0 - float(distances[i]))
        except Exception:
            similarity = 0.0

        row = rows.get(ep_id)
        tool_sequence: list[str] = []
        outcome_signals: dict[str, Any] = {}
        user_corrected = False
        age_minutes = 0
        session_phase = ""
        ctx_text = documents[i] if i < len(documents) else ""

        if row is not None:
            try:
                tool_sequence = json.loads(row["tool_sequence_json"] or "[]")
            except Exception:
                tool_sequence = []
            try:
                outcome_signals = json.loads(row["outcome_signals_json"] or "{}")
            except Exception:
                outcome_signals = {}
            user_corrected = bool(row["user_corrected"])
            session_phase = str(row["session_phase"] or "")
            try:
                created = datetime.fromisoformat(str(row["created_at"]))
                age_minutes = int((now - created).total_seconds() / 60)
            except Exception:
                age_minutes = 0
            ctx_text = str(row["context_text"] or ctx_text)

        out.append({
            "episode_id": ep_id,
            "similarity": round(similarity, 3),
            "context_text": ctx_text,
            "tool_sequence": tool_sequence,
            "outcome_signals": outcome_signals,
            "user_corrected": user_corrected,
            "age_minutes": age_minutes,
            "session_phase": session_phase,
        })

    # Sort by similarity descending (chroma returns sorted, but be defensive).
    out.sort(key=lambda x: -x["similarity"])
    return out


# ───────────────────────────────────────────────────────────────────────
# Lag 3 helper — single-line render of one episode for substrate
# ───────────────────────────────────────────────────────────────────────


def format_episode_for_prompt(ep: dict[str, Any], *, max_chars: int = 200) -> str:
    """Compact substrate line describing one retrieved episode.

    Format: ``sim=0.72 (3h ago, mid-task): tools=[bash, edit_file] →
              tick=0.78, errors=0, corrected=no``

    Designed to be read as a single line in a prompt section. Lag 3
    (the prompt-section builder) joins these with newlines.
    """
    sim = ep.get("similarity", 0.0)
    age = ep.get("age_minutes", 0)
    age_str = (
        f"{age}m" if age < 60 else
        f"{age // 60}h" if age < 60 * 24 else
        f"{age // (60 * 24)}d"
    )
    phase = ep.get("session_phase") or "—"
    tools = ep.get("tool_sequence") or []
    tools_str = ", ".join(tools[:4])
    if len(tools) > 4:
        tools_str += "…"
    outcome = ep.get("outcome_signals") or {}
    parts = []
    if "tick_quality" in outcome:
        parts.append(f"tick={outcome['tick_quality']}")
    if outcome.get("tool_errors") is not None:
        parts.append(f"errors={outcome['tool_errors']}")
    if outcome.get("decision_review_verdict"):
        parts.append(f"review={outcome['decision_review_verdict']}")
    if ep.get("user_corrected"):
        parts.append("corrected=yes")
    outcome_str = ", ".join(parts) if parts else "no signals"

    line = (
        f"sim={sim:.2f} ({age_str} ago, {phase}): "
        f"tools=[{tools_str}] → {outcome_str}"
    )
    return line[:max_chars]


