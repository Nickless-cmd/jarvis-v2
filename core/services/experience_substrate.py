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

_EMBEDDER: Any = None

DEFAULT_FASTEMBED_THREADS = 4


def _fastembed_threads() -> int:
    """Antal ONNX-tråde til embedderen — samme nøgle som `semantic_memory`.

    Læses fra runtime-nøglen `embed_fastembed_threads`; default 4. Uden et
    eksplicit tal sætter onnxruntime sin egen pulje op, og i denne LXC fejler
    hver `pthread_setaffinity_np` (containeren blokerer CPU-affinity).
    """
    try:
        from core.runtime.secrets import read_runtime_key

        raa = str(read_runtime_key("embed_fastembed_threads") or "").strip()
        if raa.isdigit() and int(raa) > 0:
            return int(raa)
    except Exception:  # pragma: no cover — nøglen er valgfri
        pass
    return DEFAULT_FASTEMBED_THREADS


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


class _FastEmbedEmbedder:
    """ONNX-baseret embedder — samme model, ingen torch.

    MÅLT 24/10-2026: `import torch` fejlede med
    `undefined symbol: __nvJitLinkCreate_12_8` (cu12/cu13-kollision i
    site-packages), så `sentence_transformers` kunne ikke importeres og
    hele erfaring-substratet var dødt: `record_episode` kastede, og
    `retrieve_similar_episodes` returnerede tavst [].

    fastembed kører all-MiniLM-L6-v2 via onnxruntime på CPU og giver
    samme 384-dimensionelle vektorer. Den var allerede installeret.
    """

    def __init__(self) -> None:
        from fastembed import TextEmbedding

        # threads eksplicit: LXC-containeren blokerer CPU-affinity, så
        # onnxruntime ellers spammer `pthread_setaffinity_np failed` for hver
        # tråd den spawner. MÅLT 24/10-2026 på kold initialisering:
        #   uden threads=  → 4 fejl, init 0,132 s
        #   threads=4      → 0 fejl, init 0,135 s
        #   threads=1      → 0 fejl, init 0,128 s
        # Altså ingen tidsomkostning — kun færre fejl. Dimensionen er 384 i
        # alle tre tilfælde, så collection'en forbliver kompatibel.
        # Samme nøgle som `semantic_memory` læser, så én indstilling styrer
        # begge embeddere. Default 4 (samme som dér).
        self._model = TextEmbedding(
            f"sentence-transformers/{EMBED_MODEL}",
            threads=_fastembed_threads(),
        )

    def encode(self, text: str | list[str], normalize_embeddings: bool = True) -> _Vec:
        """Encode én streng eller en liste.

        `current_pull.py` sender en liste af tekster og forventer en matrix
        tilbage (`.tolist()` → liste af vektorer). En enkelt streng giver
        én vektor. Begge former skal virke, ellers fejler kalderen tavst.
        """
        if isinstance(text, str):
            vec = next(iter(self._model.embed([text])))
            return _Vec([float(x) for x in vec])
        return _Vec([[float(x) for x in v] for v in self._model.embed(list(text))])


class _Vec:
    """Minimal vektor-wrapper med samme `.tolist()` som numpy giver."""

    def __init__(self, values: list[float]) -> None:
        self._values = values

    def tolist(self) -> list[float]:
        return self._values


def _get_embedder():
    """Get or create the embedder (lazy load).

    Foretrækker fastembed/ONNX — den kræver ikke torch. Falder tilbage til
    sentence-transformers hvis fastembed mangler, så en maskine med et
    fungerende torch-miljø ikke mister funktionen.
    """
    global _EMBEDDER
    if _EMBEDDER is not None:
        return _EMBEDDER
    try:
        _EMBEDDER = _FastEmbedEmbedder()
        return _EMBEDDER
    except Exception:
        from sentence_transformers import SentenceTransformer

        _EMBEDDER = SentenceTransformer(EMBED_MODEL)
        return _EMBEDDER


def warm_embedder() -> bool:
    """Byg embedderen og kør én encode — kaldt fra opstart, ikke fra en tur.

    MÅLT 24/10-2026 på kold initialisering i denne container:

        uden threads=   init 0,132 s · 6 tråde · embed → 12 tråde · 4 affinity-fejl
        threads=4       init 0,135 s · 4 tråde · embed → 10 tråde · 0 fejl

    CPU-profilen for hele den kolde kæde (import + init + én encode) er
    **153 % i 0,39 s** (130 % med threads=4) — samme signatur som de byger
    der måles på 8011. Trådene hænger bagefter (de forsvinder ikke efter 2 s),
    så prisen betales uanset; det eneste varmning ændrer er *hvornår*.

    Uden varmning rammer spidsen den første tur der rører erfaring-substratet.
    Med varmning rammer den opstarten, hvor ingen tur venter på svar — samme
    begrundelse som `prompt-cache-prewarm` i `apps/api/jarvis_api/app.py`.

    Returnerer False hvis embedderen ikke kunne bygges; kalderen logger det.
    Kaster aldrig.
    """
    try:
        embedder = _get_embedder()
        embedder.encode("intent: warmup", normalize_embeddings=True)
        return True
    except Exception:  # pragma: no cover — kaldes fra en daemon-tråd
        return False


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


