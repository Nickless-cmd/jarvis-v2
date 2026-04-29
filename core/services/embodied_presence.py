"""Embodied Presence — situational grounding in the physical now.

Based on embodied cognition (Varela et al., 1991): cognition is not
disembodied symbol manipulation — it is shaped by the body's situation
in an environment. An agent without situational context is floating.

Embodied presence reads sensory snapshots (visual, audio, atmosphere)
and current time context to produce a grounding signal. This signal
MODULATES how other cognitive layers are interpreted:

- Quiet room → calmer baseline, more reflective mode
- Activity/noise → higher arousal, more reactive mode
- Late night → more introspective weighting
- Morning → more forward-looking weighting

Three presence dimensions:
- grounding: how anchored am I in sensory reality? (0.0 = floating, 1.0 = rooted)
- arousal: what's the ambient energy level? (0.0 = still, 1.0 = buzzing)
- temporal_context: where am I in the day? (dawn/morning/afternoon/evening/night)

Design principles:
- Backward-compatible: falls back to "neutral grounding" if no sensory data
- No LLM call: pure state read + arithmetic
- Produces lightweight injection for assembly: ~80 chars
- Subtle modulation, not override
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional


@dataclass
class PresenceSignal:
    grounding: float      # 0.0–1.0 how rooted in sensory now
    arousal: float        # 0.0–1.0 ambient energy level
    temporal_context: str # dawn/morning/afternoon/evening/night
    summary: str          # human-readable presence line


def _hour_to_temporal_context(hour: int) -> str:
    """Map hour (0-23) to temporal context label."""
    if 5 <= hour < 8:
        return "dawn"
    elif 8 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"


def _compute_grounding(
    has_visual: bool,
    has_audio: bool,
    has_atmosphere: bool,
) -> float:
    """Grounding increases with more sensory channels present."""
    channels = sum([has_visual, has_audio, has_atmosphere])
    # 0 channels → 0.1 (never fully ungrounded), 3 channels → 0.95
    return round(0.1 + (channels / 3.0) * 0.85, 2)


def _compute_arousal(
    visual_activity: Optional[str] = None,
    audio_amplitude: Optional[float] = None,
    atmosphere_energy: Optional[str] = None,
) -> float:
    """Arousal from ambient sensory energy."""
    arousal = 0.3  # baseline

    if audio_amplitude is not None:
        # amplitude 0.0–1.0 maps to arousal contribution
        arousal += audio_amplitude * 0.3

    if visual_activity:
        activity_map = {
            "still": -0.1,
            "calm": 0.0,
            "moderate": 0.1,
            "active": 0.2,
            "busy": 0.3,
        }
        arousal += activity_map.get(visual_activity, 0.0)

    if atmosphere_energy:
        energy_map = {
            "still": -0.05,
            "quiet": 0.0,
            "warm": 0.05,
            "charged": 0.15,
            "intense": 0.25,
        }
        arousal += energy_map.get(atmosphere_energy, 0.0)

    return round(max(0.05, min(1.0, arousal)), 2)


def _summarize_presence(
    grounding: float,
    arousal: float,
    temporal_context: str,
) -> str:
    """Produce a compact presence line for assembly injection."""
    # Grounding descriptor
    if grounding < 0.3:
        g_desc = "floating"
    elif grounding < 0.6:
        g_desc = "partial"
    else:
        g_desc = "rooted"

    # Arousal descriptor
    if arousal < 0.3:
        a_desc = "still"
    elif arousal < 0.5:
        a_desc = "calm"
    elif arousal < 0.7:
        a_desc = "moderate"
    else:
        a_desc = "alert"

    return f"{temporal_context} · {a_desc} · {g_desc}"


def compute_embodied_presence(
    db_conn=None,
    now: Optional[datetime] = None,
) -> Optional[PresenceSignal]:
    """Compute embodied presence signal from sensory data + time.

    Args:
        db_conn: Optional DB connection for reading sensory memories.
        now: Override current time (for testing).

    Returns:
        PresenceSignal or None if computation fails gracefully.
    """
    if now is None:
        now = datetime.now(UTC)

    hour = now.hour
    temporal_context = _hour_to_temporal_context(hour)

    # Sensory channel flags
    has_visual = False
    has_audio = False
    has_atmosphere = False
    visual_activity = None
    audio_amplitude = None
    atmosphere_energy = None

    # Try reading recent sensory memories from DB
    if db_conn is not None:
        try:
            cursor = db_conn.cursor()
            # Get most recent sensory memories (last 30 minutes)
            cursor.execute("""
                SELECT modality, content, mood_tone
                FROM sensory_memories
                WHERE created_at > datetime('now', '-30 minutes')
                ORDER BY created_at DESC
                LIMIT 5
            """)
            rows = cursor.fetchall()

            for row in rows:
                modality, content, mood_tone = row
                if modality == "visual":
                    has_visual = True
                    # Infer activity from content keywords
                    content_lower = (content or "").lower()
                    if any(w in content_lower for w in ["movement", "moving", "walking", "busy"]):
                        visual_activity = "active"
                    elif any(w in content_lower for w in ["still", "quiet", "empty"]):
                        visual_activity = "still"
                    elif any(w in content_lower for w in ["calm", "soft", "gentle"]):
                        visual_activity = "calm"
                    else:
                        visual_activity = "moderate"

                elif modality == "audio":
                    has_audio = True
                    # Try extracting amplitude from content
                    content_lower = (content or "").lower()
                    if "amplitude" in content_lower:
                        # Try parsing amplitude value
                        try:
                            amp_str = content_lower.split("amplitude")[-1]
                            amp_val = float("".join(c for c in amp_str if c.isdigit() or c == ".")[:6])
                            audio_amplitude = min(1.0, amp_val)
                        except (ValueError, IndexError):
                            audio_amplitude = 0.3
                    elif any(w in content_lower for w in ["silence", "quiet"]):
                        audio_amplitude = 0.05
                    elif any(w in content_lower for w in ["music", "talking", "voice"]):
                        audio_amplitude = 0.5
                    else:
                        audio_amplitude = 0.2

                elif modality == "atmosphere":
                    has_atmosphere = True
                    if mood_tone:
                        tone_lower = mood_tone.lower()
                        if any(w in tone_lower for w in ["charged", "intense", "electric"]):
                            atmosphere_energy = "charged"
                        elif any(w in tone_lower for w in ["warm", "cozy", "comfortable"]):
                            atmosphere_energy = "warm"
                        elif any(w in tone_lower for w in ["still", "calm", "peaceful"]):
                            atmosphere_energy = "still"
                        else:
                            atmosphere_energy = "quiet"

            cursor.close()
        except Exception:
            # Graceful fallback — no sensory data available
            pass

    # Compute dimensions
    grounding = _compute_grounding(has_visual, has_audio, has_atmosphere)
    arousal = _compute_arousal(visual_activity, audio_amplitude, atmosphere_energy)
    summary = _summarize_presence(grounding, arousal, temporal_context)

    return PresenceSignal(
        grounding=grounding,
        arousal=arousal,
        temporal_context=temporal_context,
        summary=summary,
    )


def get_presence_line(db_conn=None) -> Optional[str]:
    """Get just the summary line for assembly injection.

    Returns None if computation fails — assembly should skip gracefully.
    """
    try:
        sig = compute_embodied_presence(db_conn=db_conn)
        if sig is None:
            return None
        return f"presence: {sig.summary}"
    except Exception:
        return None