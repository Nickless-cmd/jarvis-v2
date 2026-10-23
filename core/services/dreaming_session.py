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
                # Målt 21/10-2026 02:54Z: `active[:5]` tog rå indeks 0-4, som
                # alle var fra 16/10. De upræsenterede med høj konfidens stod
                # på indeks 24-25 — præcis dem get_presentable_dream() ville
                # vælge først — og var derfor usynlige i prompten. Prioriteringen
                # findes allerede i dream_carry_over.py; her gentages den, fordi
                # overfladen returnerer _ACTIVE_DREAMS urørt.
                for d in sorted(
                    active,
                    key=lambda x: (
                        not x.get("presented", False),
                        float(x.get("confidence") or 0),
                        str(x.get("adopted_at") or ""),
                    ),
                    reverse=True,
                )[:5]
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


def _conf(value: Any, default: float = 0.0) -> float:
    """Confidence som float — carry-over bærer historisk BÅDE ``0.8`` og ``"0.8"``.

    Målt 22/10-2026: én post med streng-confidence fik hele drømme-sessionen til
    at fejle med ``Unknown format code 'f' for object of type 'str'``. Fejlen
    blev kastet fra ``_build_dream_prompt``, fanget af ``fire``-ens brede
    ``except`` og logget som «failed to fire» — så drømmen fyrede ALDRIG, så
    længe posten lå i FIFO-vinduet på fem, uden at nogen enkelt-post så forkert ud.
    """
    try:
        return float(value)
    except (TypeError, ValueError):  # ikke en fejl: en manglende eller gemt confidence skal bare give default, ikke dræbe drømmen
        return default


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
                f"(conf={_conf(d.get('confidence')):.1f}, carry={d.get('carry_count', 0)})"
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
                f"(conf={_conf(h.get('confidence')):.1f})"
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


def _registrer_dream_i_indbakken(session_id: str, content_keys: list[str]) -> None:
    """Læg drømmesessionen i indbakken som en SYNLIG, ikke-gatende post.

    Punkt 4 (15/10-2026), Bjørn: «disse drømmesession osse lander i inbak
    ellers er de usynlige for os». Sessionen fyrer i en baggrundstråd
    (`_threading.Thread` → `dispatch_system`) og har derfor intet run og intet
    `runtime.autonomous_run_completed`-event — run-closure-gaten kan slet ikke
    se den (den fyrer kun for `origin=recurring` + `task_id`). Resultatet blev
    læst af ingen.

    Kildetypen `dream` står i `IKKE_GATENDE_KILDETYPER`: posten er INFORMATION.
    Huset må oprette den, aldrig nægte en mutation på den. Idempotent pr.
    (bruger, `dream`, session_id), så et genkald ikke dublerer. Self-safe: en
    indbakke der ikke kan skrives må ikke vælte sessionen.
    """
    try:
        from core.services.inbox_state import _ejer_id, registrer_kilde

        bruger = _ejer_id()
        if not bruger:
            return
        kilder = ", ".join(str(k) for k in content_keys[:4])
        registrer_kilde(
            bruger_id=bruger,
            kildetype="dream",
            kilde_id=session_id,
            paastaaet_ejer="huset",
            beskrivelse=(
                f"Drømmesession {session_id} kørt på {len(content_keys)} "
                f"kildetyper ({kilder}). Note i ~/dreams/."
            ),
        )
    except Exception:
        logger.debug("dreaming_session: indbakke-registrering fejlede", exc_info=True)


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

        # Punkt 4 (15/10-2026): gør sessionen SYNLIG i indbakken, ellers er den
        # usynlig for både run-closure-gaten og Bjørn.
        _registrer_dream_i_indbakken(session_id, content_keys)

        # Fire the autonomous run in a background thread
        def _fire() -> None:
            try:
                from core.services.routine_trigger_adapters import dispatch_system

                def _legacy() -> None:
                    from core.services.visible_runs import start_autonomous_run

                    start_autonomous_run(message=prompt, session_id=None, origin="dream")

                dispatch_system(
                    "dream", session_id,
                    trigger_inputs={"prompt": prompt}, legacy=_legacy,
                )
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
