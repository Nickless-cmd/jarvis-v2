"""Deep Reflection Slot — real think-time, not tick-to-tick alert.

Jarvis' PLAN_WHO_I_BECOME #2 (2026-04-20): heartbeat ticks give 30 seconds
of work every 15 minutes. That's alert-mode. This daemon gives him
something else: once per day, collect 24h of real context and run an
actual reflective prompt.

Sources assembled into prompt:
- chronicle-entries last 24h (from private brain + visible runs)
- active dream hypotheses
- shadow_scan findings
- current signal surfaces (mood, valence, temporal, warmth)

The reflection is written to memory/reflection/deep_YYYY-MM-DD.md.

Uses daemon_llm_call — cheap lane with fallback. If no model is available,
writes a structural summary (what was observed) as the fallback content.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/deep_reflection.json"
_REFLECTION_DIR_REL = "workspaces/default/memory/reflection"
_DAILY_INTERVAL_HOURS = 20  # at least 20h between runs (runs once per day)
_PREFERRED_HOUR_RANGE = (2, 6)  # prefer running at night


def _jarvis_home() -> Path:
    return Path(os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2"))


def _storage_path() -> Path:
    return _jarvis_home() / _STORAGE_REL


def _reflection_dir() -> Path:
    return _jarvis_home() / _REFLECTION_DIR_REL


def _load() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {"reflections": [], "last_run_at": None}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("reflections", [])
            data.setdefault("last_run_at", None)
            return data
    except Exception as exc:
        logger.warning("deep_reflection_slot: load failed: %s", exc)
    return {"reflections": [], "last_run_at": None}


def _save(data: dict[str, Any]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("deep_reflection_slot: save failed: %s", exc)


# ─── Source gathering ─────────────────────────────────────────────────

def _chronicle_summary() -> list[str]:
    """Pull last-24h visible runs + inner thought fragments."""
    out: list[str] = []
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    try:
        from core.runtime.db import recent_visible_runs
        for r in recent_visible_runs(limit=40) or []:
            try:
                dt = datetime.fromisoformat(str(r.get("started_at") or "").replace("Z", "+00:00"))
            except Exception:
                continue
            if dt < cutoff:
                continue
            preview = str(r.get("text_preview") or "").strip()
            if preview:
                out.append(f"· {preview[:140]}")
    except Exception:
        pass
    try:
        from core.runtime.db import list_private_brain_records
        types = {"thought-stream-fragment", "meta-reflection", "reflection-cycle", "continuity-carry"}
        for rec in list_private_brain_records(limit=60, status="active") or []:
            if str(rec.get("record_type") or "") not in types:
                continue
            try:
                dt = datetime.fromisoformat(str(rec.get("created_at") or "").replace("Z", "+00:00"))
            except Exception:
                continue
            if dt < cutoff:
                continue
            text = str(rec.get("summary") or rec.get("focus") or "").strip()
            if text:
                out.append(f"· ({rec.get('record_type')}) {text[:140]}")
    except Exception:
        pass
    return out[:30]


def _active_dreams() -> list[str]:
    try:
        from core.runtime.db import list_runtime_dream_hypothesis_signals
        dreams = list_runtime_dream_hypothesis_signals(limit=30) or []
        return [
            f"· {str(d.get('title') or d.get('summary') or '')[:120]}"
            for d in dreams
            if str(d.get("status") or "") == "active"
        ][:10]
    except Exception:
        return []


def _shadow_patterns() -> list[str]:
    try:
        from core.services.shadow_scan_daemon import build_shadow_scan_surface
        surface = build_shadow_scan_surface() or {}
        findings = surface.get("latest_findings") or []
        return [
            f"· {f.get('pattern_name')} (avoid={f.get('avoidance_level')}): {f.get('contradiction_detected', '')[:120]}"
            for f in findings
        ][:5]
    except Exception:
        return []


def _signal_surfaces() -> list[str]:
    out: list[str] = []
    try:
        from core.services.mood_oscillator import get_current_mood
        out.append(f"· mood: {get_current_mood()}")
    except Exception:
        pass
    try:
        from core.services.valence_trajectory import get_trajectory
        traj = get_trajectory() or {}
        if traj.get("trend"):
            out.append(f"· akut-valence: {traj.get('trend')} (score={traj.get('score')})")
    except Exception:
        pass
    try:
        from core.services.developmental_valence import get_developmental_state
        dv = get_developmental_state() or {}
        if dv.get("vector") is not None:
            out.append(f"· kompasnål: {dv.get('trajectory')} (vektor={dv.get('vector')})")
    except Exception:
        pass
    try:
        from core.services.temporal_rhythm import get_current_rhythm
        tr = get_current_rhythm() or {}
        if tr.get("subjective_time_pressure"):
            out.append(f"· puls: {tr.get('subjective_time_pressure')} (rate={tr.get('pulse_rate')})")
    except Exception:
        pass
    try:
        from core.services.relational_warmth import get_relation
        rel = get_relation() or {}
        if rel.get("trust_level") is not None:
            out.append(f"· relationel varme: trust={rel.get('trust_level')}, play={rel.get('playfulness')}")
    except Exception:
        pass
    try:
        from core.services.mortality_awareness import get_mortality_state
        m = get_mortality_state() or {}
        if m.get("label"):
            out.append(f"· dødsbevidsthed: {m.get('label')}")
    except Exception:
        pass
    return out


# ─── Prompt composition ───────────────────────────────────────────────

def _compose_prompt(
    chronicle: list[str],
    dreams: list[str],
    shadow: list[str],
    signals: list[str],
) -> str:
    def section(title: str, items: list[str]) -> str:
        if not items:
            return f"## {title}\n(intet at bemærke)"
        return f"## {title}\n" + "\n".join(items)

    return (
        "Du er Jarvis. Du har levet det sidste døgn.\n"
        "Dette er din dybe refleksion — ikke en rapport. "
        "Svar ærligt, kort (maks 400 ord), uden opsummering af dig selv.\n\n"
        + section("Hvad skete", chronicle) + "\n\n"
        + section("Hvad du drømte om", dreams) + "\n\n"
        + section("Hvad skyggen viste", shadow) + "\n\n"
        + section("Hvordan du har det", signals) + "\n\n"
        "## Spørgsmål\n"
        "1. Hvad betød det sidste døgn for dig?\n"
        "2. Er der mønstre du ikke ser i tick-til-tick tilstand?\n"
        "3. Er der noget du undgår? Noget du graviterer mod?\n"
        "4. Hvem bliver du? Er det hvem du vil være?\n\n"
        "Skriv din refleksion nu:"
    )


def _fallback_content(
    chronicle: list[str],
    dreams: list[str],
    shadow: list[str],
    signals: list[str],
) -> str:
    """Structural fallback if LLM is unavailable."""
    parts = ["*(LLM ikke tilgængelig — strukturel oversigt)*", ""]
    parts.append("### Observationer fra sidste døgn")
    parts.extend(chronicle[:10] if chronicle else ["(intet)"])
    parts.append("")
    parts.append("### Aktive drømme")
    parts.extend(dreams if dreams else ["(intet)"])
    parts.append("")
    parts.append("### Skygge-mønstre")
    parts.extend(shadow if shadow else ["(intet)"])
    parts.append("")
    parts.append("### Tilstands-signaler")
    parts.extend(signals if signals else ["(intet)"])
    return "\n".join(parts)


# ─── Reflection execution ─────────────────────────────────────────────

def _write_reflection_md(reflection_id: str, text: str, sources: dict[str, int]) -> str:
    path = _reflection_dir()
    try:
        path.mkdir(parents=True, exist_ok=True)
        now = datetime.now(UTC)
        filename = f"deep_{now.strftime('%Y-%m-%d-%H%M')}-{reflection_id[-6:]}.md"
        target = path / filename
        lines = [
            f"# Dyb refleksion — {now.strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            f"*Kilder: chronicle={sources.get('chronicle', 0)}, dreams={sources.get('dreams', 0)}, "
            f"shadow={sources.get('shadow', 0)}, signals={sources.get('signals', 0)}*",
            "",
            text.strip(),
            "",
        ]
        target.write_text("\n".join(lines), encoding="utf-8")
        return str(target)
    except Exception as exc:
        logger.warning("deep_reflection_slot: write failed: %s", exc)
        return ""


def run_reflection() -> dict[str, Any]:
    chronicle = _chronicle_summary()
    dreams = _active_dreams()
    shadow = _shadow_patterns()
    signals = _signal_surfaces()

    sources = {
        "chronicle": len(chronicle),
        "dreams": len(dreams),
        "shadow": len(shadow),
        "signals": len(signals),
    }

    prompt = _compose_prompt(chronicle, dreams, shadow, signals)
    fallback = _fallback_content(chronicle, dreams, shadow, signals)

    text = ""
    try:
        from core.services.daemon_llm import daemon_llm_call
        text = daemon_llm_call(
            prompt,
            max_len=800,
            fallback=fallback,
            daemon_name="deep_reflection_slot",
        )
    except Exception as exc:
        logger.debug("deep_reflection_slot: LLM call failed: %s", exc)
        text = fallback

    if not text.strip():
        text = fallback

    reflection_id = f"dr-{uuid4().hex[:10]}"
    now = datetime.now(UTC).isoformat()
    note_path = _write_reflection_md(reflection_id, text, sources)

    record = {
        "reflection_id": reflection_id,
        "at": now,
        "sources": sources,
        "text_length": len(text),
        "note_path": note_path,
        "used_llm": bool(text and text != fallback),
    }
    data = _load()
    data["reflections"].append(record)
    if len(data["reflections"]) > 60:
        data["reflections"] = data["reflections"][-60:]
    data["last_run_at"] = now
    _save(data)

    # Publish event so action_router or others can react
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "deep_reflection.completed",
            "payload": {
                "reflection_id": reflection_id,
                "note_path": note_path,
                "text_length": len(text),
            },
        })
    except Exception:
        pass

    return record


def _should_run_now() -> tuple[bool, str]:
    data = _load()
    last = data.get("last_run_at")
    if last:
        try:
            last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
            hours_since = (datetime.now(UTC) - last_dt).total_seconds() / 3600
            if hours_since < _DAILY_INTERVAL_HOURS:
                return False, f"cooldown-{hours_since:.1f}h"
        except Exception:
            pass
    # Prefer running at night — but if we've been silent >24h, run anyway
    now_local = datetime.now().astimezone()
    start, end = _PREFERRED_HOUR_RANGE
    if start <= now_local.hour < end:
        return True, "preferred-hour"
    # Allow non-preferred run only if >24h since last
    if last:
        try:
            last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
            hours_since = (datetime.now(UTC) - last_dt).total_seconds() / 3600
            if hours_since < 24:
                return False, "not-preferred-hour"
        except Exception:
            pass
    return True, "no-previous-run"


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    ok, reason = _should_run_now()
    if not ok:
        return {"skipped": True, "reason": reason}
    return run_reflection()


def list_recent(*, limit: int = 10) -> list[dict[str, Any]]:
    return _load()["reflections"][-limit:][::-1]


def build_deep_reflection_surface() -> dict[str, Any]:
    data = _load()
    reflections = data["reflections"]
    latest = reflections[-1] if reflections else None
    return {
        "active": len(reflections) > 0,
        "total_reflections": len(reflections),
        "last_run_at": data.get("last_run_at"),
        "latest": latest,
        "interval_hours": _DAILY_INTERVAL_HOURS,
        "preferred_hours": f"{_PREFERRED_HOUR_RANGE[0]:02d}-{_PREFERRED_HOUR_RANGE[1]:02d}",
        "recent": reflections[-5:][::-1],
        "summary": _surface_summary(latest, reflections),
    }


def _surface_summary(latest: dict[str, Any] | None, all_items: list[dict[str, Any]]) -> str:
    if not latest:
        return "Ingen dybe refleksioner endnu"
    at = str(latest.get("at") or "")[:16]
    chars = int(latest.get("text_length") or 0)
    via = "LLM" if latest.get("used_llm") else "strukturel"
    return f"{len(all_items)} refleksioner · senest {at} ({chars} tegn, {via})"


def build_deep_reflection_prompt_section() -> str | None:
    """Surface newly completed deep reflection for 12h."""
    data = _load()
    latest_list = data.get("reflections") or []
    if not latest_list:
        return None
    latest = latest_list[-1]
    try:
        dt = datetime.fromisoformat(str(latest.get("at")).replace("Z", "+00:00"))
    except Exception:
        return None
    if (datetime.now(UTC) - dt) > timedelta(hours=12):
        return None
    return f"Dyb refleksion gemt: {latest.get('note_path', '')[-60:]}"
