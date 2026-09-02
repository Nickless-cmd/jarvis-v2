"""Prompt-sektioner fra de private lag — tynde, selv-sikre delegationer.

Udskilt fra ``prompt_contract.py`` (4.732 linjer) 2026-09-02 efter Boy
Scout-reglen, før blokken om fejlede autonome kørsler blev tilføjet samme sted.

Enheden er naturlig: seks funktioner der alle gør nøjagtig det samme — spørger
ét privat undersystem om en promptblok og svarer ``None`` hvis noget som helst
går galt. Ingen af dem beregner noget selv. De hørte sammen i forvejen og lå
side om side; her har de et navn.

Kontrakten er den samme for dem alle: **et privat lag må aldrig kunne vælte
prompt-bygningen.** Fejler undersystemet, forsvinder blokken — og Jarvis svarer
uden den frem for slet ikke at svare.
"""

from __future__ import annotations


def _visible_chronicle_context_section() -> str | None:
    try:
        from core.services.chronicle_engine import get_chronicle_context_for_prompt

        section = get_chronicle_context_for_prompt()
        return section or None
    except Exception:
        return None


def _visible_dream_residue_section() -> str | None:
    try:
        from core.services.dream_distillation_daemon import get_dream_residue_for_prompt

        section = get_dream_residue_for_prompt()
        return section or None
    except Exception:
        return None


def _visible_unconscious_temperature_field_section() -> str | None:
    try:
        from core.services.unconscious_temperature_field import (
            build_unconscious_temperature_hint,
        )

        section = build_unconscious_temperature_hint()
        return section or None
    except Exception:
        return None


def _visible_response_style_hint_section() -> str | None:
    """Lag 10 Site 4: response-style modifiers from user temperature field.

    Returns a soft system-prompt hint when modifiers differ from defaults.
    The model treats this as a hint, not a hard rule — adjusts response
    form (length, warmth, pace) toward the receiver's current state.
    """
    try:
        from core.services.user_temperature_engine import get_response_style_modifiers
        # Brug den AKTIVE brugers workspace, ikke hardcodet "default" — ellers fik en
        # member (fx Michelle) owner Bjørns temperatur-modifiers (multi-user-fejl).
        from core.identity.workspace_context import current_workspace_name
        mods = get_response_style_modifiers(workspace_id=current_workspace_name() or "default")
        non_default = {
            k: v for k, v in mods.items()
            if v not in ("normal", "neutral")
        }
        if not non_default:
            return None
        hint_str = ", ".join(f"{k}={v}" for k, v in non_default.items())
        return (
            f"[response_style_hint] {hint_str} "
            f"— soft adjustment based on the user's current temperature."
        )
    except Exception:
        return None


def _visible_current_pull_section() -> str | None:
    """Lag 5: inject current pull as quiet first-priority context."""
    try:
        from core.services.current_pull import get_current_pull_for_prompt

        section = get_current_pull_for_prompt()
        return section or None
    except Exception:
        return None


def _visible_visual_memory_section() -> str | None:
    """Lag 6: inject latest visual room memory + ambient sound + echo signals + morning thread.

    Combines:
    - visual (from visual_memory)
    - auditory (from ambient_sound_daemon)
    - echo themes (from session_continuity) — recurring concerns de sidste dage
    - morning thread (from session_continuity) — hvad han bærer med fra sidst

    Into a single "senses + continuity" section so Jarvis can naturally reference
    his physical surroundings AND his felt continuity with yesterday.
    """
    parts: list[str] = []
    try:
        from core.services.visual_memory import get_latest_visual_memory_for_prompt
        v = get_latest_visual_memory_for_prompt()
        if v:
            parts.append(v)
    except Exception:
        pass
    try:
        from core.services.ambient_sound_daemon import get_latest_ambient_sound_for_prompt
        a = get_latest_ambient_sound_for_prompt()
        if a:
            parts.append(a)
    except Exception:
        pass
    # Music accumulator (Lag #6 Phase 1, added 2026-05-11)
    try:
        from core.services.ambient_sound_daemon import get_music_accumulator_for_prompt
        music_line = get_music_accumulator_for_prompt()
        if music_line:
            parts.append(music_line)
    except Exception:
        pass
    try:
        from core.services.personal_project import get_project_prompt_hint
        pp = get_project_prompt_hint()
        if pp:
            parts.append(pp)
    except Exception:
        pass
    try:
        from core.services.session_continuity import get_echo_signals_for_prompt, get_latest_morning_thread
        e = get_echo_signals_for_prompt()
        if e:
            parts.append(e)
        mt = get_latest_morning_thread()
        if mt and mt.get("thread_text"):
            # Only surface if recent (within last 6 hours)
            import datetime as _dt
            from datetime import UTC as _UTC, timedelta as _td
            try:
                created = _dt.datetime.fromisoformat(
                    str(mt.get("created_at") or "").replace("Z", "+00:00")
                )
                if created.tzinfo is None:
                    created = created.replace(tzinfo=_UTC)
                if (_dt.datetime.now(_UTC) - created) < _td(hours=6):
                    parts.append(f"[morgentråd]: {str(mt['thread_text'])[:200]}")
            except Exception:
                pass
    except Exception:
        pass
    if not parts:
        return None
    return "\n".join(parts)
