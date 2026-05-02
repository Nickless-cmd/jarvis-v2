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


# ---------------------------------------------------------------------------
# Consolidation Phase 3: theme consolidation + kill-switch (Task 14)
# ---------------------------------------------------------------------------


_THEME_REJECT_THRESHOLD = 3


def _state_path():
    """Override target in tests via monkeypatch."""
    from core.services import jarvis_brain
    from pathlib import Path
    return Path(jarvis_brain._state_root()) / "brain_daemon_state.json"


def _read_state() -> dict:
    import json
    p = _state_path()
    if not p.exists():
        return {"theme_rejection_streak": 0, "theme_paused": False}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"theme_rejection_streak": 0, "theme_paused": False}


def _write_state(state: dict) -> None:
    import json
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    tmp.replace(p)


def record_proposal_rejection(phase: str, *, proposal_id: str) -> None:
    """Track rejection. After 3 in a row for 'theme' phase, auto-pause."""
    if phase != "theme":
        return  # only theme phase has streak-tracking in v1
    state = _read_state()
    state["theme_rejection_streak"] = state.get("theme_rejection_streak", 0) + 1
    if state["theme_rejection_streak"] >= _THEME_REJECT_THRESHOLD:
        state["theme_paused"] = True
        try:
            from core.eventbus.events import emit  # type: ignore
            emit(
                "jarvis_brain.theme_consolidation_paused",
                {
                    "reason": f"{_THEME_REJECT_THRESHOLD} consecutive rejections",
                    "last_rejected_id": proposal_id,
                },
            )
        except Exception:
            pass
    _write_state(state)


def record_proposal_acceptance(phase: str, *, proposal_id: str) -> None:
    """Reset rejection streak on acceptance."""
    if phase != "theme":
        return
    state = _read_state()
    state["theme_rejection_streak"] = 0
    _write_state(state)


def is_theme_consolidation_paused() -> bool:
    return bool(_read_state().get("theme_paused", False))


def resume_theme_consolidation() -> None:
    """Manuel reaktivering. Nulstiller streak + paused flag."""
    state = _read_state()
    state["theme_paused"] = False
    state["theme_rejection_streak"] = 0
    _write_state(state)


def _run_theme_consolidation_pass() -> int:
    """Søndags-pass: group observations efter domain, find temaer.

    Stub i v1: returner 0. Faktisk implementering tilføjes senere når vi har
    nok data til at træne prompten.
    """
    return 0


def run_theme_consolidation_if_active() -> int:
    """Kør tema-pass hvis ikke paused. Returnerer antal forslag genereret."""
    if is_theme_consolidation_paused():
        logger.info("theme consolidation paused — skipping")
        return 0
    return _run_theme_consolidation_pass()


# ---------------------------------------------------------------------------
# Summary regeneration (Task 15)
# ---------------------------------------------------------------------------


_SUMMARY_PROMPT = """\
Du genererer en kompakt opsummering af Jarvis' egen vidensjournal.
Den vises i toppen af hans bevidsthed som "ting jeg ved nu".

Krav:
- Maks 300 tokens
- Inddel i sektioner med fed: **Engineering:**, **Selv:**, **Relationer:**, **Verden:**
- Brug 1.-person ("Jeg har lært...", "Jeg ved...")
- Spring sektioner over hvis der ikke er noget at sige
- Vær konkret men kompakt

Aktive poster:
{entries_summary}

Returnér JSON: {{"summary": "<markdown-prosa>"}}
"""


def regenerate_summary(*, target_visibility: str = "personal") -> int:
    """Regenererer state/jarvis_brain_summary.md.

    Kun entries med visibility ≤ target_visibility tæller med.
    Privacy-routing: target_visibility == "public_safe" → free API ok;
    ellers lokal Ollama (intet personal/intimate til ekstern API).
    Returnerer antal entries summeret over (0 hvis intet eller fejl).
    """
    from datetime import datetime, timezone
    from core.services import jarvis_brain
    from core.services.jarvis_brain_visibility import LEVEL

    ceiling = LEVEL[target_visibility]

    conn = jarvis_brain.connect_index()
    try:
        rows = conn.execute(
            "SELECT title, kind, domain, visibility FROM brain_index "
            "WHERE status='active' ORDER BY domain, kind"
        ).fetchall()
    finally:
        conn.close()

    eligible = [r for r in rows if LEVEL[r[3]] <= ceiling]
    if not eligible:
        return 0

    bullet_lines = "\n".join(
        f"- [{kind}/{domain}] {title}" for title, kind, domain, _ in eligible
    )
    prompt = _SUMMARY_PROMPT.format(entries_summary=bullet_lines)

    # Privacy routing
    if target_visibility == "public_safe":
        result = _call_ollamafreeapi(prompt)
    else:
        result = _call_local_ollama(prompt)

    if not result or "summary" not in result:
        logger.warning("summary regeneration failed (no LLM result)")
        return 0

    now = datetime.now(timezone.utc)
    summary_md = (
        f"# Hvad jeg ved nu — opdateret {now.strftime('%Y-%m-%d %H:%M')}\n\n"
        + str(result["summary"])
    )
    out_path = jarvis_brain._state_root() / "jarvis_brain_summary.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text(summary_md, encoding="utf-8")
    tmp.replace(out_path)
    return len(eligible)


# ---------------------------------------------------------------------------
# Auto-archive low-salience entries (Task 16)
# ---------------------------------------------------------------------------


_AUTO_ARCHIVE_THRESHOLD = 0.05
_AUTO_ARCHIVE_MIN_DAYS = 90


def auto_archive_low_salience() -> int:
    """Arkivér entries hvis effective_salience < 0.05 i ≥ 90 dage.

    Skip references (de er ankre — arkiveres aldrig automatisk).
    Emits 'jarvis_brain.auto_archive_pass' event with telemetry.
    Returnerer antal arkiverede.
    """
    from datetime import datetime, timezone
    from core.services import jarvis_brain

    now = datetime.now(timezone.utc)
    conn = jarvis_brain.connect_index()
    try:
        rows = conn.execute(
            "SELECT id, kind FROM brain_index WHERE status='active'"
        ).fetchall()
    finally:
        conn.close()

    archived = 0
    total_active = len(rows)
    for entry_id, kind in rows:
        if kind == "reference":
            continue  # references arkiveres aldrig automatisk
        try:
            entry = jarvis_brain.read_entry(entry_id)
        except Exception:
            continue
        eff = jarvis_brain.compute_effective_salience(entry, now)
        if eff >= _AUTO_ARCHIVE_THRESHOLD:
            continue
        last = entry.last_used_at or entry.created_at
        days_low = (now - last).days
        if days_low < _AUTO_ARCHIVE_MIN_DAYS:
            continue
        try:
            jarvis_brain.archive_entry(entry_id, reason="auto: low salience 90+ days")
            archived += 1
        except Exception as exc:
            logger.warning("auto-archive failed for %s: %s", entry_id, exc)

    # Telemetri til eventbus
    try:
        from core.eventbus.events import emit  # type: ignore
        emit(
            "jarvis_brain.auto_archive_pass",
            {
                "archived_count": archived,
                "total_active_before": total_active,
            },
        )
    except Exception:
        pass

    return archived
