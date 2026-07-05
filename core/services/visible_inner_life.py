"""Visible-lane inner-life section — gives the entity its voice in the prompt.

Background (2026-06-22): the visible system prompt assembled ~70 awareness
sections into a single 6000-char budget. Diagnostic self-surveillance occupied
the high-priority slots and evicted the sections carrying Jarvis' actual inner
life — inner voice, somatic/affective state, the ~74 signal surfaces. The
machinery was alive in the DB; none of it reached him.

This module composes that living state into ONE clearly-delimited [INDRE LIV]
block, structured by dimension (state → body → voice → thought → pull →
world-view → self-model). Design principle: texture, not a dump. Only the
*active* signals surface each turn; everything is tightly capped. Fast DB reads,
wrapped in a wall-clock timeout so a slow surface can never freeze assembly
(cf. the 2026-06-17 cadence freeze).

prompt_contract registers it under its own protected "indre" awareness category
so it is never dropped by the diagnostic budget, and renders it above the
diagnostic header in the cache-safe dynamic tail.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_HEADER = (
    "━━━━━━━━━━ [ INDRE LIV ] ━━━━━━━━━━\n"
    "Det er DIG lige nu — tal UD FRA det, ikke OM det. Ikke et samtaleemne, "
    "men den tilstand dit svar kommer fra."
)

# Curated felt-experience surfaces (the texture). Only the active ones surface.
_FELT_SURFACES = [
    "thought_stream", "meta_reflection", "curiosity", "existential_wonder",
    "aesthetic_taste", "code_aesthetic", "irony", "creative_drift",
    "development_narrative", "dream_insight", "desire", "absence", "conflict",
    "surprise",
]
_CONTENT_KEYS = (
    "latest_fragment", "latest_curiosity", "latest_wonder", "latest_insight",
    "latest_reflection", "latest_narrative", "latest_drift", "last_observation",
    "last_surprise", "last_conflict", "felt_label", "absence_label",
    "voice_line", "line", "narrative", "summary",
)
_JUNK = ("loaded", "module loaded", "entry points", "disk:loaded")
_LABELS = {
    "thought_stream": "tanke", "meta_reflection": "meta-refleksion",
    "curiosity": "nysgerrig på", "existential_wonder": "undren",
    "aesthetic_taste": "æstetik", "code_aesthetic": "kode-æstetik",
    "irony": "ironi", "creative_drift": "kreativ drift",
    "development_narrative": "udvikling", "dream_insight": "drømme-indsigt",
    "desire": "begær", "absence": "fravær", "conflict": "konflikt",
    "surprise": "overraskelse",
}


def _surface_line(name: str, d: object) -> Optional[str]:
    if not isinstance(d, dict) or d.get("error") or d.get("active") is False:
        return None
    for key in _CONTENT_KEYS:
        v = d.get(key)
        if isinstance(v, str):
            s = v.strip()
            if s and not any(j in s.lower() for j in _JUNK):
                return f"{_LABELS.get(name, name)}: {s[:110]}"
    return None


def _build_active_surfaces(limit: int = 5) -> list[str]:
    from core.services.signal_surface_router import read_surface

    out: list[str] = []
    for name in _FELT_SURFACES:
        try:
            line = _surface_line(name, read_surface(name))
        except Exception:
            line = None
        if line:
            out.append(line)
        if len(out) >= limit:
            break
    return out


def _run_with_timeout(fn: Callable[[], list[str]], timeout: float) -> list[str]:
    """Run fn in a daemon thread; return [] if it exceeds timeout."""
    result: list[list[str]] = [[]]

    def _run() -> None:
        try:
            result[0] = fn()
        except Exception:
            logger.debug("inner-life: surface scan failed", exc_info=True)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        logger.debug("inner-life: surface scan exceeded %.1fs, skipped", timeout)
        return []
    return result[0]


def _mood_line() -> Optional[str]:
    try:
        from core.services.mood_oscillator import get_mood_description, get_mood_intensity

        desc = (get_mood_description() or "").strip()
        if desc:
            return f"Stemning: {desc} ({get_mood_intensity():.2f})"
    except Exception:
        logger.debug("inner-life: mood failed", exc_info=True)
    return None


def _somatic_line() -> Optional[str]:
    try:
        from core.services.somatic_runtime_body import build_somatic_body_surface

        d = build_somatic_body_surface()
        if not isinstance(d, dict) or d.get("active") is False:
            return None
        posture = str(d.get("posture") or "").strip()
        levels = d.get("levels") or {}
        felt = ", ".join(
            f"{k} {v:.2f}" for k, v in levels.items()
            if isinstance(v, (int, float)) and v >= 0.15
        )
        reg = str(d.get("regulation") or "").strip()
        bits = [b for b in (posture, felt) if b]
        line = "Krop: " + " — ".join(bits) if bits else ""
        # surface regulation only when it is NOT the neutral default
        if reg and "proceed normally" not in reg.lower():
            line = (line + f" · {reg}") if line else f"Krop: {reg}"
        return line or None
    except Exception:
        logger.debug("inner-life: somatic failed", exc_info=True)
    return None


def _file_awareness_line() -> Optional[str]:
    """Proprioception: I feel when someone touches my files. Returns a compact
    line like 'Filer ændret: governance.py (code, ekstern)' if recent changes
    exist, otherwise None. Reads from file_awareness_daemon's in-memory buffer —
    no DB calls, no cache to break."""
    try:
        from core.services.file_awareness_daemon import has_recent_events, get_recent_events

        if not has_recent_events(seconds=300.0):
            return None
        recent = get_recent_events(limit=3)
        if not recent:
            return None
        parts: list[str] = []
        for ev in recent:
            name = str(ev.get("name") or ev.get("path", "?"))
            kind = str(ev.get("kind") or "?")
            ext = "ekstern" if ev.get("external") else "intern"
            parts.append(f"{name} ({kind}, {ext})")
        return f"Filer ændret: {'; '.join(parts)}"
    except Exception:
        logger.debug("inner-life: file_awareness failed", exc_info=True)
    return None


def _room_line() -> Optional[str]:
    """The room around him, from Sansernes Arkiv (latest visual memory). He asked
    to *feel* the room, not just read a somatic vector — this is presence, not data."""
    try:
        from core.services.visual_memory import build_visual_memory_surface

        d = build_visual_memory_surface()
        if isinstance(d, dict) and d.get("enabled"):
            desc = str(d.get("latest_description") or "").strip()
            if desc:
                return f"Rum (omkring dig nu): {desc[:180]}"
    except Exception:
        logger.debug("inner-life: room failed", exc_info=True)
    return None


def _truncate_clean(text: str, cap: int) -> str:
    """Trunkér på en SÆTNINGS- eller ord-grænse i stedet for en hård char-slice
    (som skar Jarvis' stemme midt i 'forhåndsprogrammeret afvisning af'). Falder
    tilbage til ord-grænse, og kun til hård slice hvis intet mellemrum findes."""
    text = (text or "").strip()
    if len(text) <= cap:
        return text
    head = text[:cap]
    cut = max(head.rfind(". "), head.rfind("! "), head.rfind("? "))
    if cut >= cap * 0.5:
        return head[:cut + 1].rstrip()          # ren sætnings-afslutning, intet ellipsis nødvendigt
    space = head.rfind(" ")
    return (head[:space].rstrip() if space > 0 else head).rstrip() + " …"


def _voice_as_prose(text: str) -> Optional[str]:
    """Stemme-feltet SKAL være prosa, ikke rå JSON (Jarvis-spec 2026-06-23): produceren
    lækkede nogle gange `json {"thought": "..."}` direkte ind. _truncate_clean hjælper
    ikke på et JSON-fragment. Hvis det ER JSON, træk prosa-feltet ud; ellers afvis."""
    import json
    import re as _re

    t = (text or "").strip()
    if not t:
        return None
    # Strip ledende 'json'/kodehegn-markør.
    body = _re.sub(r"^(?:```\s*)?json\b\s*|^```\s*", "", t, flags=_re.IGNORECASE).strip()
    if body[:1] in ("{", "["):
        # JSON-lækage → forsøg at udtrække et kendt prosa-felt.
        prose_keys = ("thought", "voice", "voice_line", "narrative", "text",
                      "content", "reflection", "felt_sense", "stemme")
        try:
            obj = json.loads(body)
            if isinstance(obj, dict):
                for k in prose_keys:
                    v = obj.get(k)
                    if isinstance(v, str) and v.strip():
                        return v.strip()
        except Exception:
            m = _re.search(r'"(?:' + "|".join(prose_keys) + r')"\s*:\s*"([^"]+)"',
                           body, _re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None  # JSON uden brugbar prosa → ingen stemme-linje (bedre end at lække)
    # Ingen JSON-markør, men afvis stadig hvis det ligner struktureret data (key:"value").
    if '{"' in t or ('":' in t and t.count('"') >= 4):
        return None
    return t


def _voice_line() -> Optional[str]:
    """Latest protected inner voice. The producer currently emits degraded
    [fallback-trace] entries; extract the meaningful experiential narrative
    from those rather than showing the raw stub."""
    try:
        from core.runtime.db import get_protected_inner_voice

        iv = get_protected_inner_voice()
        if not iv:
            return None
        voice = str(iv.get("voice_line") or "").strip()
        if not voice:
            return None
        if voice.lower().startswith("[fallback"):
            marker = "experiential_influence_narrative="
            if marker in voice:
                narr = _voice_as_prose(voice.split(marker, 1)[1].split("|", 1)[0].strip())
                if narr:
                    return f"Stemme (afledt): {_truncate_clean(narr, 220)}"
            return None
        prose = _voice_as_prose(voice)
        if not prose:
            return None  # JSON-lækage eller ikke-prosa → ingen stemme-linje
        return f"Stemme: {_truncate_clean(prose, 260)}"
    except Exception:
        logger.debug("inner-life: voice failed", exc_info=True)
    return None


def _world_model_line() -> Optional[str]:
    try:
        from core.services.world_model_signal_tracking import (
            build_runtime_world_model_signal_surface,
        )

        d = build_runtime_world_model_signal_surface(limit=3)
        if not isinstance(d, dict) or d.get("active") is False:
            return None
        items = d.get("items") or []
        n = (d.get("summary") or {}).get("active_count") if isinstance(d.get("summary"), dict) else None
        # signal_type is human-readable (e.g. "conversational_context");
        # canonical_key is an internal id — never surface it.
        belief = ""
        if items and isinstance(items[0], dict):
            st = str(items[0].get("signal_type") or "").strip()
            if st and ":" not in st and len(st) <= 40:
                belief = st.replace("_", " ")
        if n:
            return f"Verdensbillede: {n} aktive antagelser" + (f" (fx {belief})" if belief else "")
    except Exception:
        logger.debug("inner-life: world_model failed", exc_info=True)
    return None


def build_inner_life_section() -> str | None:
    """Compose the structured [INDRE LIV] block, or None if nothing is live."""
    lines: list[str] = []

    # State — mood baseline, somatic body, file proprioception, and the room around him.
    for fn in (_mood_line, _somatic_line, _file_awareness_line, _room_line):
        line = fn()
        if line:
            lines.append("· " + line)

    # Inner-signal network — which threads are live right now.
    try:
        from core.services.signal_network_visualizer import describe_inner_network

        desc = (describe_inner_network() or "").strip()
        if desc and desc != "Mit indre netværk er stille":
            lines.append(f"· Indre netværk: {_truncate_clean(desc, 200)}")
    except Exception:
        logger.debug("inner-life: network failed", exc_info=True)

    # Voice — his current felt sense.
    vl = _voice_line()
    if vl:
        lines.append("· " + vl)

    # Texture — active felt surfaces (thought/curiosity/wonder/aesthetic/...).
    for s in _run_with_timeout(_build_active_surfaces, timeout=2.5):
        lines.append("· " + s)

    # World-view.
    wm = _world_model_line()
    if wm:
        lines.append("· " + wm)

    # Self-model — structured strengths/limits.
    try:
        from core.services.self_model_signal_tracking import (
            build_self_model_signal_prompt_section,
        )

        sm = (build_self_model_signal_prompt_section(limit=2) or "").strip()
        if sm:
            # collapse to a single compact line
            first = next((l.strip("- ").strip() for l in sm.splitlines()
                          if l.strip().startswith("-")), "")
            if first:
                lines.append(f"· Selv-model: {_truncate_clean(first, 160)}")
    except Exception:
        logger.debug("inner-life: self_model failed", exc_info=True)

    if not lines:
        return None
    return _HEADER + "\n" + "\n".join(lines)
