"""Memory recall section builder — udskilt fra prompt_contract.py (Boy Scout).

Fem tightly coupled funktioner til at bygge [MEMORY-RECALL]-sektionen:
  - _visible_memory_recall_bundle_section: hovedfunktion, bygger sektionen
  - _private_brain_recall_lines: henter private brain continuity
  - _recent_tool_recall_lines: henter seneste tool observationer
  - _memory_candidate_recall_lines: henter pending memory candidates
  - _clip_line: hjælper til at klippe lange linjer

Re-eksporteres fra prompt_contract.py så eksisterende imports + monkeypatches
i tests ikke knækker.
"""
from __future__ import annotations

from core.services.chat_sessions import recent_chat_tool_messages
from core.services.tool_result_store import render_tool_result_for_prompt
from core.runtime.db import list_runtime_contract_candidates

# Vage telemetri-fraser (Jarvis-spec #7): kandidater der bare beskriver "der skete noget"
# uden konkret viden. Substring-match → skip (de brænder tokens uden værdi).
_VAGUE_MARKERS = (
    "recent log indicates", "log indicates recent", "expressions or errors",
    "may indicate", "appears to indicate", "seems to", "various recent",
    "recent expressions", "recent activity", "no notable",
)

# MEMORY.md-linjer cached på fil-mtime (KUN tekst, ingen embeddings → ingen cold-start-
# latency). Semantisk match bruger leksikalsk pre-filter: vi embedder kun kandidaten +
# de få linjer der deler nøgleord, ikke alle ~500 linjer (det tog 15-20s/build).
_MD_LINES_CACHE: dict[str, object] = {"mtime": None, "lines": []}
# MEMORY.md-linje-VEKTORER cached på mtime, embeddet ÉN gang i en baggrundstråd
# (2026-07-23, cProfile-rod): _is_semantic_dup_of_memory re-embeddede de LANGE
# MEMORY.md-linjer frisk hver tur (12 linjer × hver kandidat × ~700ms ONNX-batch
# = ~2s/build for typisk 0 output). Nu embedder hot-path'en KUN kandidat-teksten
# mod cachede linje-vektorer. Cachen bygges i baggrunden ved mtime-skift → første
# tur efter en MEMORY.md-ændring falder tilbage til literalt match (blokerer aldrig).
import threading as _md_threading
_MD_VECS_CACHE: dict[str, object] = {"mtime": None, "vecs": {}, "building": False}
_MD_VECS_LOCK = _md_threading.Lock()


def _md_line_vecs(user_id: str = "") -> dict:
    """Cached {linje: vektor} for MEMORY.md. Embeddes ÉN gang pr. mtime i baggrunden.
    Returnerer den nuværende cache (kan være tom mens den (gen)bygges → kalder falder
    tilbage til literalt match, blokerer aldrig hot-path'en)."""
    try:
        from core.runtime.workspace_paths import workspace_dir
        md = (workspace_dir(user_id) if user_id else workspace_dir()) / "MEMORY.md"
        if not md.exists():
            return {}
        mtime = md.stat().st_mtime
    except Exception:
        return {}
    with _MD_VECS_LOCK:
        if _MD_VECS_CACHE.get("mtime") == mtime:
            return _MD_VECS_CACHE.get("vecs") or {}
        if _MD_VECS_CACHE.get("building"):
            return _MD_VECS_CACHE.get("vecs") or {}
        _MD_VECS_CACHE["building"] = True

    def _build() -> None:
        try:
            lines = _memory_md_lines(user_id)
            vecs: dict = {}
            if lines:
                from core.services.jarvis_brain import _embed_texts
                for ln, v in zip(lines, _embed_texts(lines)):
                    vecs[ln] = v
            with _MD_VECS_LOCK:
                _MD_VECS_CACHE.update(mtime=mtime, vecs=vecs, building=False)
        except Exception:
            with _MD_VECS_LOCK:
                _MD_VECS_CACHE["building"] = False

    _md_threading.Thread(target=_build, name="md-vecs-embed", daemon=True).start()
    return _MD_VECS_CACHE.get("vecs") or {}
_MD_STOPWORDS = frozenset({
    "jeg", "du", "han", "den", "det", "der", "som", "med", "for", "til", "på", "af", "og",
    "er", "var", "en", "et", "har", "ikke", "kun", "via", "ved", "via", "the", "and", "now",
    "uses", "with", "system", "fra", "via",
})
# Kalibreret mod ægte data: "Cluster-priority auth(0)<loop(7)"-kandidaten matcher sin
# danske MEMORY.md-tvilling på 0.777, mens næste (urelaterede) linje er 0.629 → klart gap.
_SEMANTIC_DUP_THRESHOLD = 0.73


def _resolve_user_id(session_id: str = "") -> str:
    """Resolve user_id eksplicit (recall-sektionerne kører UDEN current_user_id()-kontekst
    i fuld-build → workspace_dir() ville fejle). Fra session → ellers owner."""
    try:
        if session_id:
            from core.services.chat_sessions import get_chat_session
            sess = get_chat_session(session_id) or {}
            uid = str(sess.get("user_id") or "").strip()
            if uid:
                return uid
        # Owner-user_id ER discord_id i dette system (owner_resolver: sess_user_id==owner_id).
        from core.identity.owner_resolver import get_owner_discord_id
        return str(get_owner_discord_id() or "").strip()
    except Exception:
        return ""


def _memory_md_lines(user_id: str = "") -> list[str]:
    """Cached MEMORY.md-LINJER (kun tekst, ingen embedding → nul cold-start-cost)."""
    try:
        from core.runtime.workspace_paths import workspace_dir
        md = (workspace_dir(user_id) if user_id else workspace_dir()) / "MEMORY.md"
        if not md.exists():
            return []
        mtime = md.stat().st_mtime
        if _MD_LINES_CACHE.get("mtime") == mtime:
            return _MD_LINES_CACHE.get("lines") or []
        lines = [ln.lstrip("-* ").strip() for ln in md.read_text(encoding="utf-8").splitlines()
                 if len(ln.strip()) > 25]
        _MD_LINES_CACHE.update(mtime=mtime, lines=lines)
        return lines
    except Exception:
        return []


def _keywords(text: str) -> set:
    return {w for w in __import__("re").sub(r"[^0-9a-zæøå ]", " ", str(text or "").lower()).split()
            if len(w) >= 4 and w not in _MD_STOPWORDS}


_CROSS_DEDUP_THRESHOLD = 0.80  # near-dup samme budskab, anden ordlyd (kalibreres mod data)


def _semantic_dedup_lines(lines: list[str], threshold: float = _CROSS_DEDUP_THRESHOLD) -> list[str]:
    """Drop linjer der semantisk dublerer en TIDLIGERE beholdt linje (samme budskab,
    anden ordlyd — fx 2× 'No active runtime loop'). Order-preserving → DETERMINISTISK
    (samme input → samme output), så prompt-cachen ikke brydes. Self-safe."""
    if len(lines) < 2:
        return lines
    try:
        import numpy as np
        from core.services.jarvis_brain import _embed_texts
    except Exception:
        return lines
    # ÉT batch-kald for alle linjer i stedet for N serielle embed-round-trips.
    # Rækkefølge + dedup-logik uændret → deterministisk (prompt-cache-sikkert).
    vecs = _embed_texts(lines)
    kept: list[str] = []
    kept_vecs: list[object] = []
    for ln, v in zip(lines, vecs):
        try:
            vn = float(np.linalg.norm(v)) or 1e-9
        except Exception:
            kept.append(ln)
            kept_vecs.append(None)
            continue
        is_dup = False
        for kv in kept_vecs:
            if kv is None:
                continue
            d = vn * (float(np.linalg.norm(kv)) or 1e-9)
            if float(np.dot(v, kv) / d) >= threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append(ln)
            kept_vecs.append(v)
    return kept


def _is_semantic_dup_of_memory(text: str, user_id: str = "") -> bool:
    """True hvis `text` semantisk matcher en MEMORY.md-linje (allerede gemt, anden ordlyd).
    LEKSIKALSK PRE-FILTER: embedder kun kandidaten + de MEMORY.md-linjer der deler ≥2
    nøgleord (typisk 0-3 linjer), ikke alle ~500 → ingen latency-eksplosion."""
    try:
        import numpy as np
        from core.services.jarvis_brain import _embed_texts
        # Cachede linje-vektorer (baggrund-embeddet pr. mtime). Tom under (gen)bygning
        # → fald tilbage til literalt match (kalderen har allerede tjekket det). Dette
        # dræber per-tur-re-embeddingen af de lange MEMORY.md-linjer (~2s → ~50ms).
        line_vecs = _md_line_vecs(user_id)
        if not line_vecs:
            return False
        kw = _keywords(text)
        if len(kw) < 2:
            return False
        # Kun linjer med tilstrækkelig nøgleord-overlap er dublet-kandidater (≤12).
        candidates = [ln for ln in line_vecs if len(kw & _keywords(ln)) >= 2][:12]
        if not candidates:
            return False
        # Embed KUN kandidat-teksten (1 embed); linje-vektorerne kommer fra cachen.
        qv = _embed_texts([text])[0]
        qn = float(np.linalg.norm(qv)) or 1e-9
        for ln in candidates:
            v = line_vecs.get(ln)
            if v is None:
                continue
            d = qn * (float(np.linalg.norm(v)) or 1e-9)
            if float(np.dot(qv, v) / d) >= _SEMANTIC_DUP_THRESHOLD:
                return True
        return False
    except Exception:
        return False


def _visible_memory_recall_bundle_section(
    *,
    session_id: str | None,
    user_message: str,
    compact: bool,
) -> str | None:
    lines: list[str] = ["Memory recall bundle:"]

    private_brain = _private_brain_recall_lines(limit=3 if compact else 4)
    if private_brain:
        lines.append("- Private continuity:")
        lines.extend(f"  - {line}" for line in private_brain)

    tool_lines = _recent_tool_recall_lines(session_id, limit=3 if compact else 5)
    if tool_lines:
        lines.append("- Internal tool observations (Jarvis-only, not user-visible chat):")
        lines.extend(f"  - {line}" for line in tool_lines)

    candidate_lines = _memory_candidate_recall_lines(limit=2 if compact else 3, session_id=session_id)
    if candidate_lines:
        lines.append("- Pending memory candidates:")
        lines.extend(f"  - {line}" for line in candidate_lines)

    if len(lines) == 1:
        return None
    lines.append(
        "Use this only as bounded continuity support. Workspace files and the user's latest message outrank it."
    )
    return "\n".join(lines)


def _private_brain_recall_lines(*, limit: int) -> list[str]:
    try:
        from core.services.session_distillation import (
            build_private_brain_context,
        )

        brain = build_private_brain_context(limit=limit)
    except Exception:
        return []
    if not brain.get("active"):
        return []
    result: list[str] = []
    summary = " ".join(str(brain.get("continuity_summary") or "").split()).strip()
    if summary:
        result.append(_clip_line(summary, limit=180))
    for excerpt in list(brain.get("excerpts") or [])[:limit]:
        text = " ".join(str(excerpt.get("summary") or "").split()).strip()
        if not text:
            continue
        focus = " ".join(str(excerpt.get("focus") or "").split()).strip()
        prefix = f"{focus}: " if focus else ""
        result.append(_clip_line(prefix + text, limit=180))
    # Semantisk within-dedup: collapse near-dup continuity-linjer (2× "No active runtime
    # loop" med forskellig ordlyd). Deterministisk → cache-sikkert.
    return _semantic_dedup_lines(result[:limit])


def _recent_tool_recall_lines(session_id: str | None, *, limit: int) -> list[str]:
    if not session_id:
        return []
    try:
        messages = recent_chat_tool_messages(session_id, limit=limit)
    except Exception:
        return []
    # 2026-06-22 (Jarvis' review): tool observations are historical bash-output
    # noise from earlier debugging. Only surface ones from the last 30 minutes,
    # and condense hard to a one-line summary (was 220 chars). Old runs drop out.
    from datetime import datetime, timezone, timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
    result: list[str] = []
    for item in messages[-limit:]:
        ts_raw = str(item.get("created_at") or "").strip()
        if ts_raw:
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts < cutoff:
                    continue  # older than 30 min — historical, not "now"
            except Exception:
                pass
        content = render_tool_result_for_prompt(
            str(item.get("content") or ""),
            expand=False,
            max_chars=100,
        )
        if not content:
            continue
        result.append(_clip_line(content, limit=100))
    return result


def _memory_candidate_recall_lines(*, limit: int, session_id: str = "") -> list[str]:
    try:
        candidates = list_runtime_contract_candidates(
            candidate_type="memory_promotion",
            target_file="MEMORY.md",
            status="proposed",
            limit=limit,
        )
    except Exception:
        return []
    try:
        from core.services.candidate_tracking import _candidate_already_applied
    except Exception:
        _candidate_already_applied = None  # type: ignore[assignment]
    # Recall kører UDEN current_user_id()-kontekst i fuld-build → resolve user_id eksplicit.
    user_id = _resolve_user_id(session_id)
    # Læs MEMORY.md-indhold ÉN gang (normaliseret) → skip kandidater hvis tekst allerede
    # står der (de DB-baserede applied-checks misser kandidater anvendt via andre stier).
    memory_md = ""
    try:
        from core.runtime.workspace_paths import workspace_dir
        _md = (workspace_dir(user_id) if user_id else workspace_dir()) / "MEMORY.md"
        if _md.exists():
            # Normalisér: fjern backticks/markdown-støj så matchet er formaterings-robust.
            memory_md = " ".join(_md.read_text(encoding="utf-8").lower().replace("`", "").split())
    except Exception:
        memory_md = ""
    lines: list[str] = []
    for candidate in candidates[:limit]:
        summary = " ".join(str(candidate.get("summary") or "").split()).strip()
        confidence = str(candidate.get("confidence") or "unknown").strip()
        if not summary:
            continue
        # Skip vage kandidater — under 5 ord ELLER vag telemetri-frase ("Recent log
        # indicates recent expressions or errors" = 7 ord men intetsigende).
        low = summary.lower()
        if len(summary.split()) < 5 or any(mk in low for mk in _VAGUE_MARKERS):
            continue
        # Skip kandidater der ALLEREDE er gemt (samme canonical_key med status=applied)
        # — de står allerede i MEMORY.md; at vise dem som "pending" er forvirrende dublet.
        if _candidate_already_applied is not None:
            try:
                if _candidate_already_applied(candidate):
                    continue
            except Exception:
                pass
        # Indholds-tjek mod MEMORY.md: literalt uddrag-match (hurtigt, fanger ordrette).
        if memory_md:
            probe = " ".join(summary.lower().replace("`", "").split()[:6])
            if len(probe) >= 20 and probe in memory_md:
                continue
        # Semantisk dedup: fanger konceptuelle dubletter med ANDEN ordlyd (det literal
        # match misser, fx "Cluster-priority auth(0)<loop(7)" der allerede er i MEMORY.md
        # med andre ord). 1 embedding-kald pr. kandidat mod cached MEMORY.md-vektorer.
        if _is_semantic_dup_of_memory(summary, user_id):
            continue
        lines.append(_clip_line(f"{summary} (confidence={confidence})", limit=180))
    return lines


def _clip_line(value: str, *, limit: int) -> str:
    # Ord-sikker (mod "død ved tusinde snit") — klipper ved sætnings/ord-grænse, ikke midt i ordet.
    from core.services.text_clip import clip_text
    return clip_text(value, limit=limit)
