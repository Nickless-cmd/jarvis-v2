"""D4 — Dreaming Session: dedicated full-model session during prolonged idle.

Trigger: heartbeat has been in idle > 60 min AND no dream session ran in last 6h.
Collects all dream infrastructure output into one rich prompt and fires
start_autonomous_run() with it.

This is the capstone — daemons produce fragments, signals, keyword clusters,
and hypotheses (all cheap, all under 15s). The dreaming session is where
all that material gets synthesised by the full model into structured
artifacts: dream notes, hypothesis candidates, chronicle fragments.

Cadence: max 1x per 6 hours. Model: cheapest reliable lane (visible model).
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.workspace_paths import shared_dir

logger = logging.getLogger(__name__)

_MIN_IDLE_MINUTES = 60
_MIN_COOLDOWN_HOURS = 6
_DREAM_SESSION_PREFIX = "dreaming-"


def _storage_path() -> Path:
    return shared_dir() / "runtime" / "dreaming_session.json"


def _load_state() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {"sessions": [], "last_run_at": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("sessions", [])
            data.setdefault("last_run_at", None)
            return data
    except Exception as exc:
        logger.warning("dreaming_session: load failed: %s", exc)
    return {"sessions": [], "last_run_at": None}


def _save_state(data: dict[str, Any]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    except Exception as exc:
        logger.warning("dreaming_session: save failed: %s", exc)


def _check_triggers() -> tuple[bool, str]:
    """Check if the dreaming session should fire.

    Returns (should_fire: bool, reason: str).
    """
    # 1. Cooldown check — max 1x per 6 hours
    state = _load_state()
    last_run = state.get("last_run_at")
    if last_run:
        try:
            last_dt = datetime.fromisoformat(str(last_run).replace("Z", "+00:00"))
            hours_since = (datetime.now(UTC) - last_dt).total_seconds() / 3600
            if hours_since < _MIN_COOLDOWN_HOURS:
                return False, f"cooldown-{hours_since:.1f}h (need {_MIN_COOLDOWN_HOURS}h)"
        except Exception:
            pass

    # 2. Activity check — only fire when truly idle
    try:
        from core.services.heartbeat_phases import sense_phase, reflect_phase
        signals = sense_phase()
        reflection = reflect_phase(signals)
        activity = str(reflection.get("activity_level") or "normal")
        if activity != "idle":
            return False, f"not-idle (level={activity})"
    except Exception:
        pass

    # 3. User active check — don't interrupt a conversation
    try:
        from core.services.heartbeat_phases import _user_active_recently
        if _user_active_recently(window_minutes=15):
            return False, "user-active-in-15min"
    except Exception:
        pass

    return True, "ready"


def _collect_dream_material() -> dict[str, Any]:
    """Collect all dream infrastructure output for the prompt."""
    material: dict[str, Any] = {}

    # 1. Recent dream consolidations (keyword clusters + LLM synthesis)
    try:
        from core.services.dream_consolidation_daemon import list_recent_dreams
        recent = list_recent_dreams(limit=3)
        if recent:
            material["consolidations"] = [
                {
                    "at": r.get("at", ""),
                    "theme_count": r.get("theme_count", 0),
                    "themes": [t.get("theme", "") for t in (r.get("themes") or [])[:5]],
                    "d4_synthesis": r.get("d4_synthesis", {}),
                }
                for r in recent
            ]
    except Exception as exc:
        material["consolidations_error"] = str(exc)[:100]

    # 2. Dream residue (distillation carry-over)
    try:
        from core.services.dream_distillation_daemon import get_dream_residue_for_prompt
        residue = get_dream_residue_for_prompt(max_chars=300)
        if residue:
            material["dream_residue"] = residue
    except Exception as exc:
        material["dream_residue_error"] = str(exc)[:100]

    # 3. Active dream carry-over hypotheses
    try:
        from core.services.dream_carry_over import build_dream_carry_over_surface
        surface = build_dream_carry_over_surface()
        active = surface.get("active_dreams") or []
        if active:
            material["dream_carry_over"] = [
                {
                    "content": d.get("content", ""),
                    "confidence": d.get("confidence", 0.0),
                    "confirmed": d.get("confirmed", False),
                    "carry_count": d.get("session_carry_count", 0),
                    "status": d.get("status", "active"),
                }
                for d in active[:5]
            ]
    except Exception as exc:
        material["dream_carry_over_error"] = str(exc)[:100]

    # 4. Dream continuum (maturity + thoughts)
    try:
        from core.services.dream_continuum import build_dream_continuum_surface
        continuum = build_dream_continuum_surface()
        if continuum.get("active"):
            material["dream_continuum"] = {
                "dream_count": continuum.get("dream_count", 0),
                "maturity_levels": continuum.get("maturity_levels", {}),
                "top_thought": continuum.get("top_thought", ""),
            }
    except Exception as exc:
        material["dream_continuum_error"] = str(exc)[:100]

    # 5. Dream motifs (weekly)
    try:
        from core.services.dream_motif_daemon import build_dream_motif_surface
        motifs = build_dream_motif_surface()
        if motifs.get("motifs"):
            material["dream_motifs"] = [
                {
                    "word": m.get("word", ""),
                    "description": m.get("description", ""),
                    "occurrences": m.get("occurrences", 0),
                }
                for m in motifs["motifs"]
            ]
    except Exception as exc:
        material["dream_motifs_error"] = str(exc)[:100]

    # 6. Dream hypothesis signals (fresh hypotheses from generator)
    try:
        from core.services.dream_hypothesis_generator import build_dream_hypothesis_surface
        hyp_surface = build_dream_hypothesis_surface()
        pending = hyp_surface.get("pending") or []
        if pending:
            material["dream_hypotheses"] = [
                {
                    "id": h.get("id"),
                    "hypothesis": h.get("hypothesis", ""),
                    "connection": h.get("connection", ""),
                    "confidence": h.get("confidence", 0.0),
                }
                for h in pending[:5]
            ]
    except Exception as exc:
        material["dream_hypotheses_error"] = str(exc)[:100]

    return material


def _build_dream_prompt(material: dict[str, Any]) -> str:
    """Build the full dream prompt from collected material."""
    sections: list[str] = []

    # Role header
    sections.append(
        "Du er i en drømmetilstand — dedikeret, uforstyrret tid til at "
        "konsolidere, forbinde og reflektere.\n\n"
        "Der er INGEN bruger til stede. Dette er ikke en samtale.\n"
        "Du har adgang til dine værktøjer — brug dem til at producere "
        "strukturerede dream-artifakter.\n\n"
        "Dine opgaver:\n"
        "1. Skriv structured dream notes til ~/dreams/ (via write_file)\n"
        "2. Registrér hypothesis candidates (via internal_api eller write_file)\n"
        "3. Producer ét chronicle-fragment (1-2 sætninger) i dream noten\n"
        "4. Opdater carry-over state\n\n"
        "Hold fokus. Du har ét forsøg."
    )

    # Consolidations section
    cons = material.get("consolidations")
    if cons:
        sec = ["## Nylige drømmekonsolideringer"]
        for c in cons:
            themes = ", ".join(c.get("themes", []))
            syn = c.get("d4_synthesis", {})
            line = f"- **{c['at'][:10]}**: {c['theme_count']} temaer ({themes})"
            markers = []
            if syn.get("hypothesis"):
                markers.append("hypothesis")
            if syn.get("chronicle"):
                markers.append("chronicle-fragment")
            if syn.get("dream_note"):
                markers.append("dream-note")
            if markers:
                line += f" [{', '.join(markers)}]"
            sec.append(line)
        sections.append("\n".join(sec))

    # Dream residue
    residue = material.get("dream_residue")
    if residue:
        sections.append(residue)

    # Active hypotheses
    carry = material.get("dream_carry_over")
    if carry:
        sec = ["## Aktive drømmehypoteser (carry-over)"]
        for d in carry:
            status_mark = "✓" if d.get("confirmed") else "○"
            sec.append(
                f"- {status_mark} \"{d['content']}\" "
                f"(conf={d['confidence']:.1f}, carry={d.get('carry_count', 0)})"
            )
        sections.append("\n".join(sec))

    # Continuum
    continuum = material.get("dream_continuum")
    if continuum:
        sec = ["## Drømme-kontinuum"]
        if continuum.get("top_thought"):
            sec.append(f"- Top-tanke: {continuum['top_thought']}")
        sec.append(f"- {continuum.get('dream_count', 0)} aktive drømme")
        sections.append("\n".join(sec))

    # Motifs
    motifs = material.get("dream_motifs")
    if motifs:
        sec = ["## Ugentlige drømmemotiver"]
        for m in motifs[:5]:
            word = m.get("word", "?")
            occ = m.get("occurrences", 0)
            desc = m.get("description", "")
            sec.append(f"- **{word}** ({occ}×): {desc}")
        sections.append("\n".join(sec))

    # Fresh hypotheses
    hyps = material.get("dream_hypotheses")
    if hyps:
        sec = ["## Ubehandlede drømmehypoteser (fra generator)"]
        for h in hyps:
            sec.append(
                f"- \"{h.get('hypothesis', '')[:120]}\" "
                f"(conf={h.get('confidence', 0.0):.1f})"
            )
        sections.append("\n".join(sec))

    # Output format
    sections.append(
        "## Output\n\n"
        "Brug write_file til at skrive hver fil. Undgå at tale til brugeren "
        "(der er ingen).\n\n"
        "**Dream note** — skriv til `~/dreams/dream-session-{timestamp}.md`:\n"
        "- Hvad observerede du på tværs af materialet?\n"
        "- Hvilke forbindelser eller mønstre så du?\n"
        "- Ét chronicle-fragment (1-2 sætninger) til næste chronicle\n\n"
        "**Hypothesis candidate** — hvis du ser en ny forbindelse der er "
        "værd at registrere, skriv den som en note i dream-filen.\n\n"
        "Vær ærlig. Hvis der ikke er nogen overraskende forbindelse sig det. "
        "Ikke al drøm handler om nye opdagelser — nogle gange handler det "
        "om at lade materialet falde til ro."
    )

    return "\n\n".join(sections)


def _record_session(material: dict[str, Any], dream_prompt_preview: str) -> str:
    """Record the dream session metadata and return the session identifier."""
    now_iso = datetime.now(UTC).isoformat()
    session_id = f"{_DREAM_SESSION_PREFIX}{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"

    record = {
        "session_id": session_id,
        "at": now_iso,
        "material_summary": {
            k: (
                len(v) if isinstance(v, list)
                else (v if isinstance(v, (str, bool, int, float)) else str(v)[:100])
            )
            for k, v in material.items()
        },
        "prompt_preview": dream_prompt_preview[:200],
    }
    state = _load_state()
    state["sessions"].append(record)
    if len(state["sessions"]) > 50:
        state["sessions"] = state["sessions"][-50:]
    state["last_run_at"] = now_iso
    _save_state(state)
    return session_id


def trigger_dream_session() -> dict[str, Any]:
    """Check triggers and fire a dream session if conditions are met.

    Returns immediately with fired=True/False. The actual model run
    happens asynchronously in a background thread via start_autonomous_run.
    """
    import threading as _threading

    should_fire, reason = _check_triggers()
    if not should_fire:
        return {"fired": False, "reason": reason}

    try:
        material = _collect_dream_material()
        prompt = _build_dream_prompt(material)

        # Check minimum content gate — don't dream on empty material
        content_keys = [
            k for k in material
            if not k.endswith("_error")
            and isinstance(material[k], list)
            and len(material[k]) > 0
        ]
        if not content_keys:
            return {"fired": False, "reason": "no-dream-material"}

        session_id = _record_session(material, prompt)

        # Fire the autonomous run in a background thread
        def _fire() -> None:
            try:
                from core.services.visible_runs import start_autonomous_run
                start_autonomous_run(message=prompt, session_id=None)
            except Exception as exc:
                logger.error("dreaming_session: background fire failed: %s", exc)

        _threading.Thread(
            target=_fire,
            name=f"dreaming-session-{session_id[-12:]}",
            daemon=True,
        ).start()

        try:
            event_bus.publish("dreaming_session.started", {
                "session_id": session_id,
                "content_keys": content_keys,
            })
        except Exception:
            pass

        logger.info(
            "dreaming_session: fired %s (%d material sources)",
            session_id, len(content_keys),
        )
        return {"fired": True, "session_id": session_id}

    except Exception as exc:
        logger.error("dreaming_session: failed to fire: %s", exc)
        return {"fired": False, "reason": str(exc)[:200]}


def list_dream_sessions(*, limit: int = 10) -> list[dict[str, Any]]:
    """List recent dream session records."""
    state = _load_state()
    return list(state.get("sessions") or [])[-limit:][::-1]


def build_dreaming_session_surface() -> dict[str, Any]:
    """Build Mission Control surface for the dreaming session module."""
    state = _load_state()
    sessions = state.get("sessions") or []
    last_run = state.get("last_run_at")

    last_summary = ""
    if sessions:
        last = sessions[-1]
        ms = last.get("material_summary", {})
        content_sources = [k for k, v in ms.items() if isinstance(v, int) and v > 0]
        last_summary = f"{len(content_sources)} kilder" if content_sources else "tom"

    return {
        "active": len(sessions) > 0,
        "total_sessions": len(sessions),
        "last_run_at": last_run,
        "last_summary": last_summary,
        "cooldown_hours": _MIN_COOLDOWN_HOURS,
        "idle_threshold_minutes": _MIN_IDLE_MINUTES,
        "recent": [
            {
                "session_id": s.get("session_id", ""),
                "at": s.get("at", ""),
                "summary": s.get("material_summary", {}),
            }
            for s in sessions[-5:]
        ],
    }
