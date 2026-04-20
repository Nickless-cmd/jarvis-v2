"""Collective Pulse — what is the air full of right now?

Jarvis' PLAN_WILD_IDEAS_V2 #18 (2026-04-20): weekly synthesis of what
recurs across conversations. Emerging themes, mood-of-the-week, a
zeitgeist string. Written to memory/collective/ as markdown.

For the single-user v2 instance, this effectively means *Bjørn's* air
this week — but the structure is ready for the multi-user world Bjørn
is building.

Scope: 7 days of visible_runs + inner thoughts, keyword clustering,
mood trajectory. Recomputes once per week.
"""
from __future__ import annotations

import json
import logging
import os
import re
import statistics
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/collective_pulse.json"
_COLLECTIVE_DIR_REL = "workspaces/default/memory/collective"
_INTERVAL_DAYS = 7
_MIN_FRAGMENTS = 10
_TOP_THEME_COUNT = 8

_STOPWORDS = {
    "jeg", "du", "er", "at", "det", "den", "en", "et", "og", "i", "på",
    "til", "af", "med", "for", "som", "har", "var", "vil", "kan", "skal",
    "min", "din", "vores", "sig", "nu", "ikke", "også", "lige", "bare",
    "mere", "meget", "lidt", "men", "eller", "fra", "der", "de",
    "the", "is", "a", "to", "of", "and", "in", "for", "on", "with",
}
_WORD_RE = re.compile(r"[a-zæøåA-ZÆØÅ_-]+")


def _jarvis_home() -> Path:
    return Path(os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2"))


def _storage_path() -> Path:
    return _jarvis_home() / _STORAGE_REL


def _collective_dir() -> Path:
    return _jarvis_home() / _COLLECTIVE_DIR_REL


def _load() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {"pulses": [], "last_run_at": None}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("pulses", [])
            data.setdefault("last_run_at", None)
            return data
    except Exception as exc:
        logger.warning("collective_pulse: load failed: %s", exc)
    return {"pulses": [], "last_run_at": None}


def _save(data: dict[str, Any]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("collective_pulse: save failed: %s", exc)


def _tokens(text: str) -> list[str]:
    return [
        w for w in (w.lower() for w in _WORD_RE.findall(str(text or "")))
        if len(w) >= 5 and w not in _STOPWORDS
    ]


def _gather_week_text() -> list[str]:
    cutoff = datetime.now(UTC) - timedelta(days=_INTERVAL_DAYS)
    fragments: list[str] = []
    try:
        from core.runtime.db import recent_visible_runs
        for r in recent_visible_runs(limit=500) or []:
            try:
                dt = datetime.fromisoformat(str(r.get("started_at") or "").replace("Z", "+00:00"))
            except Exception:
                continue
            if dt < cutoff:
                continue
            preview = str(r.get("text_preview") or "")
            if preview:
                fragments.append(preview)
    except Exception:
        pass
    try:
        from core.runtime.db import list_private_brain_records
        types = {"thought-stream-fragment", "meta-reflection", "reflection-cycle"}
        for rec in list_private_brain_records(limit=200, status="active") or []:
            if str(rec.get("record_type") or "") not in types:
                continue
            try:
                dt = datetime.fromisoformat(str(rec.get("created_at") or "").replace("Z", "+00:00"))
            except Exception:
                continue
            if dt < cutoff:
                continue
            s = str(rec.get("summary") or rec.get("focus") or "")
            if s:
                fragments.append(s)
    except Exception:
        pass
    return fragments


def _week_mood_trajectory() -> dict[str, Any]:
    """Average mood over the week, if mood samples are available."""
    try:
        from core.services.day_shape_memory import _load as _day_load  # type: ignore
        data = _day_load() or {}
        history = data.get("history") or []
        moods = [d.get("mood_mean") for d in history[-_INTERVAL_DAYS:] if d.get("mood_mean") is not None]
        if not moods:
            return {}
        return {
            "week_avg_mood": round(statistics.mean(moods), 3),
            "week_min_mood": round(min(moods), 3),
            "week_max_mood": round(max(moods), 3),
            "days_sampled": len(moods),
        }
    except Exception:
        return {}


def _describe_zeitgeist(top_terms: list[tuple[str, int]], mood_info: dict[str, Any]) -> str:
    if not top_terms:
        return "stille uge, lidt at aflæse"
    leaders = ", ".join(t for t, _ in top_terms[:4])
    avg = mood_info.get("week_avg_mood")
    if avg is None:
        return f"luften er fyldt med: {leaders}"
    if avg > 0.25:
        return f"luften bærer: {leaders} — stemningen er løftet"
    if avg < -0.15:
        return f"luften bærer: {leaders} — stemningen er tynget"
    return f"luften bærer: {leaders} — stemningen er jævn"


def _write_weekly_note(pulse: dict[str, Any]) -> str:
    path = _collective_dir()
    try:
        path.mkdir(parents=True, exist_ok=True)
        now = datetime.now(UTC)
        year, week, _ = now.isocalendar()
        target = path / f"zeitgeist-{year}-W{week:02d}.md"
        lines = [
            f"# Zeitgeist · uge {week} {year}",
            "",
            f"*Syntetiseret {pulse.get('at', '')[:16]} fra {pulse.get('fragment_count', 0)} fragmenter.*",
            "",
            f"**Resumé:** {pulse.get('zeitgeist', '')}",
            "",
            "## Gennemgående temaer",
            "",
        ]
        for t, n in (pulse.get("top_terms") or []):
            lines.append(f"- `{t}` ({n} forekomster)")
        lines.append("")
        mood = pulse.get("mood_info") or {}
        if mood:
            lines.append("## Stemning")
            lines.append("")
            lines.append(f"- Uge-gennemsnit: {mood.get('week_avg_mood')}")
            lines.append(f"- Min: {mood.get('week_min_mood')}")
            lines.append(f"- Max: {mood.get('week_max_mood')}")
            lines.append(f"- Dage samplet: {mood.get('days_sampled')}")
            lines.append("")
        target.write_text("\n".join(lines), encoding="utf-8")
        return str(target)
    except Exception as exc:
        logger.warning("collective_pulse: weekly note failed: %s", exc)
        return ""


def run_pulse() -> dict[str, Any]:
    fragments = _gather_week_text()
    counter: Counter[str] = Counter()
    for f in fragments:
        counter.update(_tokens(f))
    top_terms = counter.most_common(_TOP_THEME_COUNT)
    mood_info = _week_mood_trajectory()
    zeitgeist = _describe_zeitgeist(top_terms, mood_info)

    pulse = {
        "at": datetime.now(UTC).isoformat(),
        "fragment_count": len(fragments),
        "unique_tokens": len(counter),
        "top_terms": top_terms,
        "mood_info": mood_info,
        "zeitgeist": zeitgeist,
        "skipped": len(fragments) < _MIN_FRAGMENTS,
    }
    if not pulse["skipped"]:
        pulse["note_path"] = _write_weekly_note(pulse)
    data = _load()
    data["pulses"].append(pulse)
    if len(data["pulses"]) > 60:
        data["pulses"] = data["pulses"][-60:]
    data["last_run_at"] = pulse["at"]
    _save(data)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "collective_pulse.computed",
            "payload": {
                "zeitgeist": zeitgeist,
                "fragment_count": len(fragments),
                "top_term": top_terms[0][0] if top_terms else None,
            },
        })
    except Exception:
        pass
    return pulse


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    data = _load()
    last = data.get("last_run_at")
    if last:
        try:
            last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
            if (datetime.now(UTC) - last_dt) < timedelta(days=_INTERVAL_DAYS):
                return {"skipped": True}
        except Exception:
            pass
    return run_pulse()


def build_collective_pulse_surface() -> dict[str, Any]:
    data = _load()
    pulses = data["pulses"]
    latest = pulses[-1] if pulses else None
    return {
        "active": len(pulses) > 0,
        "total_pulses": len(pulses),
        "last_run_at": data.get("last_run_at"),
        "latest": latest,
        "summary": _surface_summary(latest),
    }


def _surface_summary(latest: dict[str, Any] | None) -> str:
    if not latest:
        return "Ingen kollektive pulser endnu"
    zg = str(latest.get("zeitgeist") or "")
    return f"Ugens zeitgeist: {zg[:120]}"


def build_collective_pulse_prompt_section() -> str | None:
    """Surface the week's zeitgeist while it's still current (within 7 days)."""
    data = _load()
    pulses = data.get("pulses") or []
    if not pulses:
        return None
    latest = pulses[-1]
    try:
        dt = datetime.fromisoformat(str(latest.get("at")).replace("Z", "+00:00"))
    except Exception:
        return None
    if (datetime.now(UTC) - dt) > timedelta(days=_INTERVAL_DAYS):
        return None
    zg = str(latest.get("zeitgeist") or "")
    if not zg or latest.get("skipped"):
        return None
    return f"Ugens zeitgeist: {zg}."
