"""Jarvis Brain background daemon — tre uafhængige loops.

Loops:
  - reindex_loop: scanner brain_dir hver 5. min, opdaterer index, embedder pending
  - consolidation_loop: dagligt, finder duplikater + modsigelser + temaer
  - summary_loop: regenererer always-on summary efter meningsfulde ændringer
  - auto_archive: dagligt, arkiverer entries med low salience >90 dage

Spec: docs/superpowers/specs/2026-05-02-jarvis-brain-design.md sektion 7.
"""
from __future__ import annotations
import logging
import threading

logger = logging.getLogger("jarvis_brain_daemon")

_REINDEX_INTERVAL_SECONDS = 300  # 5 min


# ---------------------------------------------------------------------------
# Reindex loop (Task 11)
# ---------------------------------------------------------------------------


def reindex_once() -> int:
    """Et enkelt reindex-pass. Returnerer antal file changes opdaget."""
    from core.services import jarvis_brain
    n = jarvis_brain.rebuild_index_from_files()
    embedded = jarvis_brain.embed_pending_entries()
    if n or embedded:
        logger.info("reindex_once: %s file changes, %s embeddings", n, embedded)
    return n


def reindex_loop(stop_event: threading.Event) -> None:
    """Long-running loop. Stops cleanly when stop_event is set."""
    while not stop_event.is_set():
        try:
            reindex_once()
        except Exception as exc:
            logger.warning("reindex_loop iteration failed: %s", exc)
        stop_event.wait(_REINDEX_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Consolidation Phase 1: duplicate detection (Task 12)
# ---------------------------------------------------------------------------


def find_duplicate_proposals(
    *, threshold: float = 0.92, kinds: list[str] | None = None,
) -> list[tuple[str, str, float]]:
    """Returnerer liste af (a_id, b_id, similarity) hvor sim ≥ threshold.

    Default: kun fakta og observation. Indsigt + reference er for
    individuelle til auto-dedup.
    Threshold 0.92 er bevidst streng — falske positiver er værre end
    missede dubletter.
    """
    import numpy as np
    from core.services import jarvis_brain

    kinds = kinds or ["fakta", "observation"]
    conn = jarvis_brain.connect_index()
    try:
        ph = ",".join("?" * len(kinds))
        rows = conn.execute(
            f"SELECT id, embedding, embedding_dim FROM brain_index "
            f"WHERE status='active' AND kind IN ({ph}) AND embedding IS NOT NULL",
            kinds,
        ).fetchall()
    finally:
        conn.close()

    entries: list[tuple[str, "np.ndarray"]] = []
    for eid, blob, dim in rows:
        v = np.frombuffer(blob, dtype=np.float32).reshape(dim)
        norm = float(np.linalg.norm(v)) or 1e-9
        entries.append((eid, v / norm))

    pairs: list[tuple[str, str, float]] = []
    for i, (a_id, a_v) in enumerate(entries):
        for b_id, b_v in entries[i + 1 :]:
            sim = float(np.dot(a_v, b_v))
            if sim >= threshold:
                pairs.append((a_id, b_id, sim))
    return pairs


# ---------------------------------------------------------------------------
# Consolidation Phase 2: contradiction detection (privacy-routed) (Task 13)
# ---------------------------------------------------------------------------


_CONTRADICTION_PROMPT = """\
Givet to udsagn:
A: "{a_title}: {a_content}"
B: "{b_title}: {b_content}"

Modsiger de hinanden? Svar JSON: {{"contradicts": bool, "reason": str}}
"""


def _call_ollamafreeapi(prompt: str) -> dict | None:
    """Free OllamaFreeAPI — public-safe job. Returns parsed JSON or None on fail."""
    try:
        from core.services.cheap_provider_runtime import execute_public_safe_cheap_lane
        result = execute_public_safe_cheap_lane(message=prompt)
        text = str(result.get("text") or "")
        return _parse_json_loose(text)
    except Exception as exc:
        logger.warning("ollamafreeapi call failed: %s", exc)
        return None


def _call_local_ollama(prompt: str) -> dict | None:
    """Direct local Ollama call — for personal/intimate jobs that must not leak."""
    try:
        import httpx
        from core.services.semantic_memory import _ollama_base_url
        # Use a local-only chat model. Default to qwen2.5:7b-instruct-q4_K_M
        # but allow override via provider router.
        base = _ollama_base_url()
        # Find the configured chat model on this Ollama instance.
        model = _resolve_local_chat_model() or "qwen2.5:7b-instruct"
        resp = httpx.post(
            f"{base}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": "json",
            },
            timeout=120.0,
        )
        if resp.status_code != 200:
            logger.warning("local ollama HTTP %s", resp.status_code)
            return None
        text = str((resp.json().get("message") or {}).get("content") or "")
        return _parse_json_loose(text)
    except Exception as exc:
        logger.warning("local ollama call failed: %s", exc)
        return None


def _resolve_local_chat_model() -> str | None:
    """Find configured local-lane chat model from provider router (best-effort)."""
    try:
        from core.runtime.provider_router import resolve_provider_router_target
        target = resolve_provider_router_target(lane="local")
        if str(target.get("provider", "")).lower() == "ollama":
            m = str(target.get("model") or "").strip()
            return m or None
    except Exception:
        pass
    return None


def _parse_json_loose(text: str) -> dict | None:
    """Parse JSON from possibly noisy LLM output. Looks for first {...} block."""
    import json
    import re
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    # Find first {...} block
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _llm_contradiction_check(a, b) -> dict | None:
    """Privacy-routed contradiction check.

    If max(a.visibility, b.visibility) > public_safe, route to LOCAL ollama.
    Otherwise OllamaFreeAPI is fine.

    Personal/intimate content NEVER leaves the house.
    """
    from core.services.jarvis_brain_visibility import LEVEL as _VIS
    max_lvl = max(_VIS[a.visibility], _VIS[b.visibility])
    prompt = _CONTRADICTION_PROMPT.format(
        a_title=a.title, a_content=a.content,
        b_title=b.title, b_content=b.content,
    )
    if max_lvl == 0:
        return _call_ollamafreeapi(prompt)
    return _call_local_ollama(prompt)
