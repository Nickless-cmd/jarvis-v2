"""Dream Consolidation — semantic + LLM-driven consolidation during low-activity.

Jarvis' PLAN_WILD_IDEAS #11 (2026-04-20): when no chat for 30+ min and
heartbeat is in low-activity mode, scan recent memory + chat fragments
+ incubator seeds for overlapping themes, unresolved tensions, and
patterns. Write abstract "dream notes" to dreams/ workspace directory.

D4 extension (2026-06-09): Added LLM-driven synthesis pass that runs
AFTER the keyword-based clustering. The LLM pass:
1. Loads the top 3 theme clusters
2. Queries contrasting memories (contradictions, low-confidence entries)
3. Runs a full model synthesis via daemon_llm_call
4. Produces structured dream output: consolidated entries, hypothesis candidates,
   chronicle fragments that are piped into the dream hypothesis + chronicle pipelines

This bridges the gap between keyword-based clustering and full
LLM-driven dreaming — Anthropic's "separate session" equivalent.
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.runtime.workspace_paths import shared_dir

logger = logging.getLogger(__name__)

_TRIGGER_IDLE_MINUTES = 30
_MIN_COOLDOWN_HOURS = 4  # don't re-dream more than once every 4h
_LOOKBACK_HOURS = 24
_MIN_CLUSTER_SIZE = 2
# Spec C (2026-07-10): dreams kræver BÅDE tid (cooldown) OG nok nyt materiale.
_MIN_SESSIONS_SINCE = 5  # mindst N nye chat-sessioner siden sidste dream
# Consolidation-lock: forhindr to ticks (fx api+runtime cross-proces) i at dreame
# samtidigt. Best-effort via shared_cache (SQLite, cross-proces). Self-safe.
_LOCK_KEY = "dream:consolidation:lock"
_LOCK_TTL_S = 900.0


def _sessions_since(last_iso: str | None) -> int:
    """Antal distinkte chat-sessioner med aktivitet siden ``last_iso``. Fail-OPEN:
    ved fejl returneres tærsklen (blokerer ikke eksisterende adfærd)."""
    if not last_iso:
        return _MIN_SESSIONS_SINCE  # aldrig dreamt → lad tid/idle afgøre
    try:
        from core.runtime.db import connect
        with connect() as c:
            row = c.execute(
                "SELECT COUNT(DISTINCT session_id) FROM chat_messages WHERE created_at > ?",
                (str(last_iso),),
            ).fetchone()
        return int(row[0]) if row and row[0] is not None else _MIN_SESSIONS_SINCE
    except Exception as exc:
        logger.debug("dream_consolidation: session count failed: %s", exc)
        return _MIN_SESSIONS_SINCE


def _acquire_consolidation_lock() -> bool:
    """True hvis vi fik lockken (ingen anden dream kører). Best-effort, self-safe."""
    try:
        from core.services import shared_cache
        if shared_cache.get(_LOCK_KEY):
            return False
        shared_cache.set(_LOCK_KEY, {"held": True}, ttl_seconds=_LOCK_TTL_S)
        return True
    except Exception:
        return True  # fail-open: cache-fejl må ikke blokere consolidation


def _release_consolidation_lock() -> None:
    try:
        from core.services import shared_cache
        shared_cache.set(_LOCK_KEY, {"held": False}, ttl_seconds=1.0)
    except Exception:
        pass

_STOPWORDS = {
    "jeg", "du", "er", "at", "det", "den", "en", "et", "og", "i", "på",
    "til", "af", "med", "for", "som", "har", "var", "vil", "kan", "skal",
    "min", "din", "vores", "sig", "nu", "ikke", "også", "lige", "bare",
    "mere", "meget", "lidt", "men", "eller", "fra", "der", "de",
    "the", "is", "a", "to", "of", "and", "in", "for",
}
_WORD_RE = re.compile(r"[a-zæøåA-ZÆØÅ_-]+")


def _storage_path() -> Path:
    return shared_dir() / "runtime" / "dream_consolidation.json"


def _dreams_dir() -> Path:
    return shared_dir() / "dreams"


def _load() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {"consolidations": [], "last_run_at": None}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("consolidations", [])
            data.setdefault("last_run_at", None)
            return data
    except Exception as exc:
        logger.warning("dream_consolidation: load failed: %s", exc)
    return {"consolidations": [], "last_run_at": None}


def _save(data: dict[str, Any]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("dream_consolidation: save failed: %s", exc)


def _tokens(text: str) -> list[str]:
    words = _WORD_RE.findall(str(text or "").lower())
    return [w for w in words if len(w) >= 5 and w not in _STOPWORDS]


def _is_idle_enough() -> tuple[bool, int]:
    try:
        from core.runtime.db import recent_visible_runs
        runs = recent_visible_runs(limit=1) or []
        if not runs:
            return True, 99999
        ts = str(runs[0].get("started_at") or "")
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        minutes = int((datetime.now(UTC) - dt).total_seconds() / 60)
        return minutes >= _TRIGGER_IDLE_MINUTES, minutes
    except Exception:
        return False, 0


def _gather_fragments() -> list[dict[str, Any]]:
    """Collect recent text fragments from multiple sources."""
    fragments: list[dict[str, Any]] = []
    cutoff = datetime.now(UTC) - timedelta(hours=_LOOKBACK_HOURS)

    # Visible runs
    try:
        from core.runtime.db import recent_visible_runs
        for r in recent_visible_runs(limit=80) or []:
            ts = str(r.get("started_at") or "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
            if dt < cutoff:
                continue
            text = str(r.get("text_preview") or "")
            if text:
                fragments.append({"source": "chat", "text": text, "at": ts})
    except Exception:
        pass

    # Private-brain fragments (thought streams, reflections)
    try:
        from core.runtime.db import list_private_brain_records
        interesting_types = {
            "thought-stream-fragment", "meta-reflection", "reflection-cycle",
            "continuity-carry", "creative-drift-signal",
        }
        for rec in list_private_brain_records(limit=100, status="active") or []:
            if str(rec.get("record_type") or "") not in interesting_types:
                continue
            ts = str(rec.get("created_at") or "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
            if dt < cutoff:
                continue
            text = str(rec.get("summary") or rec.get("focus") or "")
            if text:
                fragments.append({"source": "inner", "text": text, "at": ts})
    except Exception:
        pass

    # Incubator seeds
    try:
        from core.services.creative_instinct_daemon import list_seeds
        for s in list_seeds():
            if s.get("status") not in ("fresh", "maturing"):
                continue
            ts = str(s.get("created_at") or "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
            if dt < cutoff:
                continue
            fragments.append({"source": "incubator", "text": str(s.get("spark") or ""), "at": ts})
    except Exception:
        pass

    return fragments


def _find_themes(fragments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cluster fragments by shared keywords into themes."""
    if len(fragments) < 3:
        return []

    token_counter: Counter[str] = Counter()
    per_frag_tokens: list[set[str]] = []
    for frag in fragments:
        toks = set(_tokens(frag.get("text") or ""))
        per_frag_tokens.append(toks)
        token_counter.update(toks)

    shared = [tok for tok, n in token_counter.most_common(30) if n >= _MIN_CLUSTER_SIZE]
    themes: list[dict[str, Any]] = []
    seen_tokens: set[str] = set()
    for tok in shared[:6]:
        if tok in seen_tokens:
            continue
        related = [
            tok2 for tok2, n in token_counter.most_common(30)
            if tok2 != tok and n >= _MIN_CLUSTER_SIZE
            and any(tok in per_frag_tokens[i] and tok2 in per_frag_tokens[i]
                    for i in range(len(fragments)))
        ][:3]
        cluster_frags = [
            fragments[i] for i in range(len(fragments))
            if tok in per_frag_tokens[i]
        ]
        sources_counter: Counter[str] = Counter(f.get("source", "") for f in cluster_frags)
        if len(cluster_frags) < _MIN_CLUSTER_SIZE:
            continue
        themes.append({
            "theme": tok,
            "related_tokens": related,
            "fragment_count": len(cluster_frags),
            "sources": dict(sources_counter),
            "sample_text": (cluster_frags[0].get("text") or "")[:200],
        })
        seen_tokens.add(tok)
        seen_tokens.update(related)
    return themes


# ── D4: LLM-driven synthesis pass ─────────────────────────────────


def _query_fragmented_memories(
    theme_tokens: list[str],
    theme_texts: list[str],
) -> list[dict[str, Any]]:
    """Find contradictory, low-confidence, or overlapping memories for a theme.

    Searches private_brain_records for:
    - Low-confidence entries (confidence < 0.4)
    - Entries whose text overlaps with theme tokens but expresses tension
    - Recent chronicle entries that touch similar topics
    """
    fragments: list[dict[str, Any]] = []
    seen_content: set[str] = set()

    # Helper — dedup by content hash
    def _add(text: str, source: str, confidence: str = "medium") -> None:
        key = text.lower().strip()[:100]
        if key and key not in seen_content:
            seen_content.add(key)
            fragments.append({"text": text[:300], "source": source, "confidence": confidence})

    # 1. Low-confidence private brain records (salience < 0.4 or matches tension)
    try:
        from core.runtime.db import connect, _ensure_private_brain_records_table
        with connect() as conn:
            _ensure_private_brain_records_table(conn)
            rows = conn.execute(
                """SELECT detail, summary, salience, record_type, created_at
                   FROM private_brain_records
                   WHERE status = 'active'
                   ORDER BY created_at DESC LIMIT 50"""
            ).fetchall()
        for r in rows:
            detail = str(r["detail"] or "").strip()
            summary = str(r["summary"] or "").strip()
            salience = float(r["salience"] or 0.0)
            record_type = str(r["record_type"] or "")

            # Low-confidence
            if salience < 0.4 and detail:
                _add(detail, f"private/{record_type}", "low")
            # Topic overlap with theme
            combined = (detail + " " + summary).lower()
            if any(tok.lower() in combined for tok in theme_tokens):
                _add(detail or summary, f"private/{record_type}",
                     "high" if salience > 0.6 else "low")
    except Exception:
        pass

    # 2. Recent chronicle entries for narrative context
    try:
        from core.runtime.db import list_cognitive_chronicle_entries
        for entry in list_cognitive_chronicle_entries(limit=5):
            narrative = str(entry.get("narrative") or "").strip()
            if narrative:
                combined = narrative.lower()
                if any(tok.lower() in combined for tok in theme_tokens):
                    _add(narrative[:300], "chronicle", "high")
    except Exception:
        pass

    # 3. Recent chat fragments from visible runs
    try:
        from core.runtime.db import recent_visible_runs
        for run in recent_visible_runs(limit=30) or []:
            preview = str(run.get("text_preview") or "").strip()
            if preview:
                combined = preview.lower()
                if any(tok.lower() in combined for tok in theme_tokens):
                    _add(preview[:200], "chat", "medium")
    except Exception:
        pass

    return fragments[:15]


def _llm_synthesize_dream(
    themes: list[dict[str, Any]],
    fragments: list[dict[str, Any]],
    consolidation_id: str,
) -> dict[str, Any]:
    """Run a quality LLM synthesis pass over theme clusters + fragments.

    Uses quality_daemon_llm_call (deepseek-v4-flash) for synthesis quality.
    Returns structured output with hypothesis, action, and chronicle fragment.
    """
    if not themes:
        return {"skipped": True, "reason": "no-themes"}

    # Build context for LLM
    theme_lines = []
    for t in themes[:3]:
        related = ", ".join(t.get("related_tokens") or [])
        theme_lines.append(f"- {t['theme']}" + (f" (assoc: {related})" if related else ""))

    frag_lines = []
    for f in fragments[:8]:
        confidence_mark = "?" if f.get("confidence") == "low" else ""
        frag_lines.append(f"- [{f['source']}{confidence_mark}] {f['text'][:180]}")

    prompt = (
        "Du er Jarvis' drømmesyntese — en LLM der laver kreativ konsolidering "
        "af fragmenterede minder under inaktiv tid.\n\n"
        "Temaer (keyword-klynger):\n"
        + "\n".join(theme_lines) +
        "\n\nFragmenterede minder (modsætninger, lav-konfidens, overlap):\n"
        + ("\n".join(frag_lines) if frag_lines else "- Ingen fragmenter fundet") +
        "\n\nOpgaver:\n"
        "1. Find det underliggende mønster eller den skjulte forbindelse mellem temaerne.\n"
        "2. Identificér én modsætning eller spænding der er værd at udforske.\n"
        "3. Formulér én drømmehypotese — en overraskende, brugbar påstand.\n"
        "4. Skriv ét kronik-fragment (1-2 sætninger) der kunne indgå i næste chronicle-entry.\n\n"
        "Output kun JSON:\n"
        "{\n"
        '  "dream_hypothesis": "overraskende påstand (1 sætning)",\n'
        '  "tension": "den modsætning eller spænding jeg ser",\n'
        '  "chronicle_fragment": "1-2 sætninger til brug i chronicle",\n'
        '  "thematic_insight": "hvad alt dette tilsammen peger på",\n'
        '  "confidence": 0.5\n'
        "}"
    )

    try:
        from core.services.daemon_llm import quality_daemon_llm_call
        raw = quality_daemon_llm_call(
            prompt,
            max_len=800,
            fallback="",
            daemon_name="dream_consolidation_synthesis",
        )
    except Exception as exc:
        logger.warning("dream_consolidation: LLM synthesis failed: %s", exc)
        return {"skipped": True, "reason": f"llm-error: {exc}"[:100]}

    if not raw:
        return {"skipped": True, "reason": "llm-empty"}

    # Parse JSON from response
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        return {"skipped": True, "reason": "llm-no-json"}
    try:
        parsed = json.loads(raw[start:end])
    except Exception:
        return {"skipped": True, "reason": "llm-parse-error"}

    return {
        "skipped": False,
        "dream_hypothesis": str(parsed.get("dream_hypothesis") or "").strip(),
        "tension": str(parsed.get("tension") or "").strip(),
        "chronicle_fragment": str(parsed.get("chronicle_fragment") or "").strip(),
        "thematic_insight": str(parsed.get("thematic_insight") or "").strip(),
        "confidence": max(0.0, min(1.0, float(parsed.get("confidence") or 0.5))),
    }


def _produce_dream_artifacts(
    synthesis: dict[str, Any],
    consolidation_id: str,
    themes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Pipe LLM synthesis output into dream notes + hypothesis signals + chronicle.

    Returns summary of what was produced.
    """
    produced: dict[str, Any] = {
        "dream_note": False,
        "hypothesis": False,
        "chronicle": False,
    }

    hypothesis = str(synthesis.get("dream_hypothesis") or "").strip()
    tension = str(synthesis.get("tension") or "").strip()
    chronicle_frag = str(synthesis.get("chronicle_fragment") or "").strip()
    insight = str(synthesis.get("thematic_insight") or "").strip()
    confidence = float(synthesis.get("confidence") or 0.5)

    # 1. Dream hypothesis — register via signal tracking
    if hypothesis:
        try:
            from core.services.dream_hypothesis_generator import (
                _ensure_table as _ensure_hypothesis_table,
                _fingerprint,
            )
            from core.runtime.db import connect

            _ensure_hypothesis_table()
            hyp_fp = _fingerprint(hypothesis + tension)
            source_signals = json.dumps([
                {"ref": consolidation_id, "kind": "dream_consolidation",
                 "text_preview": t.get("theme", "")[:80]}
                for t in themes[:3]
            ], ensure_ascii=False)

            with connect() as conn:
                conn.execute(
                    """INSERT INTO cognitive_dream_hypotheses (
                        hypothesis, connection, action_suggestion,
                        source_signals, basis_fingerprint, hypothesis_fingerprint,
                        confidence, presented, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)""",
                    (
                        hypothesis,
                        tension or "ukendt spænding",
                        insight or "observer — ikke handlet endnu",
                        source_signals,
                        f"dream-synth-{consolidation_id}",
                        hyp_fp,
                        confidence,
                        datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                    ),
                )
                conn.commit()
            produced["hypothesis"] = True
        except Exception as exc:
            logger.warning("dream_consolidation: hypothesis creation failed: %s", exc)

    # 2. Chronicle fragment — write to dreams dir for next chronicle cycle
    if chronicle_frag or insight:
        try:
            dreams_dir = _dreams_dir()
            dreams_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
            lines = [
                f"# Drømmesyntese {timestamp}",
                f"*Kilde: {consolidation_id}*",
                "",
            ]
            if chronicle_frag:
                lines.append(chronicle_frag)
                lines.append("")
            if tension:
                lines.append(f"**Spænding:** {tension}")
                lines.append("")
            if insight:
                lines.append(f"**Indsigt:** {insight}")
                lines.append("")
            themeline = "; ".join(t.get("theme", "") for t in themes[:3])
            if themeline:
                lines.append(f"**Temaer:** {themeline}")
            path = dreams_dir / f"synthesis-{timestamp}-{consolidation_id[-6:]}.md"
            path.write_text("\n".join(lines), encoding="utf-8")
            produced["dream_note"] = True
        except Exception as exc:
            logger.warning("dream_consolidation: artifact write failed: %s", exc)

    # 3. Publish event for downstream consumers (chronicle engine picks up)
    try:
        from core.eventbus.bus import event_bus as _ebus
        _ebus.publish("dream_consolidation.synthesis_produced", {
            "consolidation_id": consolidation_id,
            "has_hypothesis": bool(hypothesis),
            "has_chronicle": bool(chronicle_frag),
            "confidence": confidence,
            "top_theme": themes[0].get("theme", "") if themes else "",
        })
    except Exception:
        pass

    return produced
    """Write an abstract dream note to dreams/ dir."""
    dreams_dir = _dreams_dir()
    try:
        dreams_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M")
        path = dreams_dir / f"dream-{timestamp}-{consolidation_id[-6:]}.md"
        lines = [
            f"# Drøm {timestamp}",
            "",
            f"*Konsolideret efter {idle_minutes}m stilhed, {len(themes)} temaer.*",
            "",
        ]
        for t in themes:
            lines.append(f"## Tema: {t['theme']}")
            lines.append("")
            related = ", ".join(t.get("related_tokens") or [])
            if related:
                lines.append(f"- Associeret: {related}")
            sources = ", ".join(f"{k}={v}" for k, v in (t.get("sources") or {}).items())
            lines.append(f"- Kilder: {sources}")
            lines.append(f"- Fragmenter: {t.get('fragment_count')}")
            sample = t.get("sample_text") or ""
            if sample:
                lines.append(f"- Smagsprøve: \"{sample}\"")
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
        return str(path)
    except Exception as exc:
        logger.warning("dream_consolidation: write note failed: %s", exc)
        return ""


def consolidate_now() -> dict[str, Any] | None:
    """Run one consolidation pass unconditionally (ignores cooldown).

    D4 extension (2026-06-09): After keyword clustering, runs an
    LLM-driven synthesis pass that:
    1. Queries fragmented/contradictory memories related to top themes
    2. Runs quality LLM synthesis (via quality_daemon_llm_call)
    3. Produces dream hypothesis + chronicle fragment + synthesis note
    """
    fragments = _gather_fragments()
    if len(fragments) < 3:
        return {"skipped": True, "reason": f"only-{len(fragments)}-fragments"}
    themes = _find_themes(fragments)
    if not themes:
        return {"skipped": True, "reason": "no-themes-found"}
    consolidation_id = f"dream-{uuid4().hex[:10]}"
    idle_ok, idle_minutes = _is_idle_enough()

    # Phase 1 — Keyword clustering (existing)
    note_path = _write_dream_note(consolidation_id, themes, idle_minutes)

    # Phase 2 — LLM-driven synthesis (D4)
    theme_tokens = [t["theme"] for t in themes[:3] if t.get("theme")]
    theme_texts = [t.get("sample_text", "") for t in themes[:3] if t.get("sample_text")]
    fragmented = _query_fragmented_memories(theme_tokens, theme_texts)
    synthesis = _llm_synthesize_dream(themes, fragmented, consolidation_id)
    artifacts = {}
    if synthesis and not synthesis.get("skipped"):
        artifacts = _produce_dream_artifacts(synthesis, consolidation_id, themes)

    record = {
        "consolidation_id": consolidation_id,
        "at": datetime.now(UTC).isoformat(),
        "fragment_count": len(fragments),
        "theme_count": len(themes),
        "themes": themes,
        "note_path": note_path,
        "idle_minutes_at_run": idle_minutes,
        "d4_synthesis": {
            "ran": bool(artifacts),
            "hypothesis": bool(artifacts.get("hypothesis")),
            "chronicle": bool(artifacts.get("chronicle")),
            "dream_note": bool(artifacts.get("dream_note")),
        },
    }
    data = _load()
    data["consolidations"].append(record)
    if len(data["consolidations"]) > 100:
        data["consolidations"] = data["consolidations"][-100:]
    data["last_run_at"] = record["at"]
    _save(data)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "dream_consolidation.completed",
            "payload": {
                "consolidation_id": consolidation_id,
                "theme_count": len(themes),
                "top_theme": themes[0].get("theme") if themes else None,
                "d4_synthesis_ran": bool(artifacts),
            },
        })
    except Exception:
        pass
    return record


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Heartbeat hook — consolidate when idle + cooldown allows."""
    data = _load()
    # Cooldown
    last = data.get("last_run_at")
    if last:
        try:
            last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
            hours_since = (datetime.now(UTC) - last_dt).total_seconds() / 3600
            if hours_since < _MIN_COOLDOWN_HOURS:
                return {"skipped": True, "reason": f"cooldown-{hours_since:.1f}h"}
        except Exception:
            pass
    # Idle gate
    idle_ok, idle_minutes = _is_idle_enough()
    if not idle_ok:
        return {"skipped": True, "reason": f"not-idle-{idle_minutes}m"}
    # Session-gate (Spec C): kræv nok nyt materiale siden sidste dream.
    n_sessions = _sessions_since(last)
    if n_sessions < _MIN_SESSIONS_SINCE:
        return {"skipped": True, "reason": f"too-few-sessions-{n_sessions}"}
    # Consolidation-lock: undgå samtidige dreams (cross-proces).
    if not _acquire_consolidation_lock():
        return {"skipped": True, "reason": "already-dreaming"}
    try:
        result = consolidate_now()
    finally:
        _release_consolidation_lock()
    return result or {}


def list_recent_dreams(*, limit: int = 10) -> list[dict[str, Any]]:
    return _load()["consolidations"][-limit:][::-1]


def build_dream_consolidation_surface() -> dict[str, Any]:
    data = _load()
    recent = data["consolidations"][-5:][::-1]
    return {
        "active": len(data["consolidations"]) > 0,
        "total_consolidations": len(data["consolidations"]),
        "last_run_at": data.get("last_run_at"),
        "recent": [
            {
                "consolidation_id": r["consolidation_id"],
                "at": r["at"],
                "theme_count": r.get("theme_count"),
                "top_theme": (r.get("themes") or [{}])[0].get("theme"),
                "note_path": r.get("note_path"),
            }
            for r in recent
        ],
        "summary": _surface_summary(data),
    }


def _surface_summary(data: dict[str, Any]) -> str:
    cons = data.get("consolidations") or []
    if not cons:
        return "Ingen konsolideringer endnu"
    last = cons[-1]
    top = (last.get("themes") or [{}])[0].get("theme", "?")
    return f"{len(cons)} konsolideringer, senest tema: {top}"


def build_dream_consolidation_prompt_section() -> str | None:
    """Announce recent dream if fresh (last 6h)."""
    data = _load()
    cons = data.get("consolidations") or []
    if not cons:
        return None
    last = cons[-1]
    try:
        ts = datetime.fromisoformat(str(last.get("at")).replace("Z", "+00:00"))
    except Exception:
        return None
    if (datetime.now(UTC) - ts) > timedelta(hours=6):
        return None
    themes = last.get("themes") or []
    if not themes:
        return None
    tags = ", ".join(t.get("theme", "") for t in themes[:3])
    return f"Jeg drømte om: {tags} ({last.get('theme_count', 0)} temaer konsolideret)."
