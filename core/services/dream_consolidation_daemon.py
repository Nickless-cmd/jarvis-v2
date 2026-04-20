"""Dream Consolidation — semantic consolidation during low-activity.

Jarvis' PLAN_WILD_IDEAS #11 (2026-04-20): when no chat for 30+ min and
heartbeat is in low-activity mode, scan recent memory + chat fragments
+ incubator seeds for overlapping themes, unresolved tensions, and
patterns. Write abstract "dream notes" to dreams/ workspace directory.

This is a *structural* consolidator — clustering by shared keywords over
recent content. Not an LLM dreamer. The output is compact notes that
Jarvis can reference next active session ("jeg drømte om X").
"""
from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/dream_consolidation.json"
_DREAMS_DIR_REL = "workspaces/default/dreams"
_TRIGGER_IDLE_MINUTES = 30
_MIN_COOLDOWN_HOURS = 4  # don't re-dream more than once every 4h
_LOOKBACK_HOURS = 24
_MIN_CLUSTER_SIZE = 2

_STOPWORDS = {
    "jeg", "du", "er", "at", "det", "den", "en", "et", "og", "i", "på",
    "til", "af", "med", "for", "som", "har", "var", "vil", "kan", "skal",
    "min", "din", "vores", "sig", "nu", "ikke", "også", "lige", "bare",
    "mere", "meget", "lidt", "men", "eller", "fra", "der", "de",
    "the", "is", "a", "to", "of", "and", "in", "for",
}
_WORD_RE = re.compile(r"[a-zæøåA-ZÆØÅ_-]+")


def _jarvis_home() -> Path:
    return Path(os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2"))


def _storage_path() -> Path:
    return _jarvis_home() / _STORAGE_REL


def _dreams_dir() -> Path:
    return _jarvis_home() / _DREAMS_DIR_REL


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


def _write_dream_note(consolidation_id: str, themes: list[dict[str, Any]], idle_minutes: int) -> str:
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
    """Run one consolidation pass unconditionally (ignores cooldown)."""
    fragments = _gather_fragments()
    if len(fragments) < 3:
        return {"skipped": True, "reason": f"only-{len(fragments)}-fragments"}
    themes = _find_themes(fragments)
    if not themes:
        return {"skipped": True, "reason": "no-themes-found"}
    consolidation_id = f"dream-{uuid4().hex[:10]}"
    idle_ok, idle_minutes = _is_idle_enough()
    note_path = _write_dream_note(consolidation_id, themes, idle_minutes)
    record = {
        "consolidation_id": consolidation_id,
        "at": datetime.now(UTC).isoformat(),
        "fragment_count": len(fragments),
        "theme_count": len(themes),
        "themes": themes,
        "note_path": note_path,
        "idle_minutes_at_run": idle_minutes,
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
    result = consolidate_now()
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
