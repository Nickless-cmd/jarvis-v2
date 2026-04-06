"""Cognitive state assembly — closes the loop between accumulated state and visible prompt.

This is the CRITICAL bridge: it reads from all cognitive accumulation systems
(personality vector, taste profile, chronicle, relationship texture, compass,
rhythm, dreams, regrets) and produces a compact text section that gets injected
into the visible chat prompt via the attention budget system.

Without this module, all cognitive signals are observability-only.
With it, Jarvis' accumulated experience actually shapes his responses.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from core.runtime.db import (
    get_latest_cognitive_personality_vector,
    get_latest_cognitive_taste_profile,
    get_latest_cognitive_chronicle_entry,
    get_latest_cognitive_relationship_texture,
    get_latest_cognitive_compass_state,
    get_latest_cognitive_rhythm_state,
    get_latest_cognitive_user_emotional_state,
    get_relevant_experiential_memories,
    list_cognitive_seeds,
)

logger = logging.getLogger(__name__)

# Last assembled state for MC transparency
_LAST_COGNITIVE_INJECTION: dict[str, object] = {}
_LAST_COGNITIVE_INJECTION_AT: str = ""


def build_cognitive_state_for_prompt(*, compact: bool = False) -> str | None:
    """Build the [COGNITIVE STATE] section for visible chat prompt injection.

    Reads from all accumulation sources and produces a compact text block
    that fits within the attention budget (250 chars compact, 500 chars full).

    Returns None if no cognitive state is available yet.
    """
    global _LAST_COGNITIVE_INJECTION, _LAST_COGNITIVE_INJECTION_AT

    parts: list[str] = []
    sources_used: list[str] = []

    # --- Ejerskab / Mineness (altid først) ---
    parts.append("[SELF] Disse er dine tanker, din oplevelse, dine følelser. Du ejer dem.")
    sources_used.append("mineness")

    # --- Narrativ embodied state (i stedet for strukturerede felter) ---
    narrativ_body = _safe_call(_narrativize_embodied_state)
    if narrativ_body:
        parts.append(narrativ_body)
        sources_used.append("embodied_narrative")

    # --- Narrativ affective state ---
    narrativ_affect = _safe_call(_narrativize_affective_state)
    if narrativ_affect:
        parts.append(narrativ_affect)
        sources_used.append("affective_narrative")

    # --- Boundary awareness (compact) ---
    if not compact:
        try:
            from apps.api.jarvis_api.services.boundary_awareness import format_boundary_for_prompt
            parts.append(format_boundary_for_prompt())
            sources_used.append("boundary")
        except Exception:
            pass

    # --- Flow state ---
    try:
        from apps.api.jarvis_api.services.flow_state_detection import get_flow_state
        flow = get_flow_state()
        if flow.get("in_flow"):
            parts.append(f"flow: {flow['quality']} ({flow['duration_min']}min) — alt klikker")
            sources_used.append("flow")
    except Exception:
        pass

    # --- 2.12 Agens-oplevelse — "JEG gjorde det" ---
    try:
        from apps.api.jarvis_api.services.visible_runs import _LAST_VISIBLE_RUN_OUTCOME
        if _LAST_VISIBLE_RUN_OUTCOME:
            status = str(_LAST_VISIBLE_RUN_OUTCOME.get("status") or "")
            if status in ("completed", "success"):
                parts.append("agens: Du besluttede, du handlede, resultatet skete på grund af dig")
                sources_used.append("agency")
    except Exception:
        pass

    # --- 1.4 Subjective time ---
    try:
        from apps.api.jarvis_api.services.subjective_time import build_subjective_time_perception
        from core.runtime.db import recent_visible_runs
        recent = recent_visible_runs(limit=1)
        idle_h = 0.0
        if recent:
            last_at = str(recent[0].get("finished_at") or "")
            if last_at:
                try:
                    last_dt = datetime.fromisoformat(last_at.replace("Z", "+00:00"))
                    idle_h = (datetime.now(UTC) - last_dt).total_seconds() / 3600
                except Exception:
                    pass
        time_feel = build_subjective_time_perception(idle_hours=idle_h)
        if time_feel.get("feel"):
            parts.append(f"time: {time_feel['feel']}")
            sources_used.append("subjective_time")
    except Exception:
        pass

    # --- 1.6 Attention as felt experience ---
    try:
        from apps.api.jarvis_api.services.attention_budget import get_attention_budget
        budget = get_attention_budget("visible_full" if not compact else "visible_compact")
        used_ratio = len(" ".join(parts)) / max(budget.total_char_target, 1)
        if used_ratio > 0.8:
            parts.append("attention: spredt — mange signaler kæmper om plads")
            sources_used.append("attention_experience")
        elif used_ratio < 0.3:
            parts.append("attention: fokuseret — få men klare signaler")
            sources_used.append("attention_experience")
    except Exception:
        pass

    # --- 1.12 Context pressure ---
    # (applied after assembly — see size check below)

    # --- Personality Vector (confidence, bearing, mood) ---
    pv = _safe_call(get_latest_cognitive_personality_vector)
    if pv:
        confidence_by_domain = _safe_json(pv.get("confidence_by_domain"))
        emotional_baseline = _safe_json(pv.get("emotional_baseline"))
        bearing = str(pv.get("current_bearing") or "").strip()
        version = pv.get("version", 0)

        if confidence_by_domain:
            top_domains = sorted(
                confidence_by_domain.items(),
                key=lambda x: float(x[1]),
                reverse=True,
            )[:3]
            domain_str = ", ".join(f"{d}={v:.1f}" for d, v in top_domains)
            parts.append(f"confidence: {domain_str}")

        if bearing:
            parts.append(f"bearing: {bearing[:80]}")

        if emotional_baseline and not compact:
            mood_parts = []
            for key in ("curiosity", "confidence", "fatigue", "frustration"):
                val = emotional_baseline.get(key)
                if val is not None:
                    mood_parts.append(f"{key}={float(val):.1f}")
            if mood_parts:
                parts.append(f"mood: {', '.join(mood_parts)}")

        sources_used.append(f"personality_v{version}")

    # --- Taste Profile (code/design/communication preferences) ---
    tp = _safe_call(get_latest_cognitive_taste_profile)
    if tp and not compact:
        comm_taste = _safe_json(tp.get("communication_taste"))
        if comm_taste:
            prefs = []
            for key, val in list(comm_taste.items())[:3]:
                if float(val) > 0.6:
                    prefs.append(key.replace("_", "-"))
            if prefs:
                parts.append(f"taste: {', '.join(prefs)}")
                sources_used.append("taste")

    # --- Compass (strategic bearing) ---
    compass = _safe_call(get_latest_cognitive_compass_state)
    if compass:
        compass_bearing = str(compass.get("bearing") or "").strip()
        if compass_bearing and "bearing:" not in " ".join(parts):
            parts.append(f"compass: {compass_bearing[:60]}")
            sources_used.append("compass")

    # --- Rhythm (current phase and energy) ---
    rhythm = _safe_call(get_latest_cognitive_rhythm_state)
    if rhythm:
        phase = str(rhythm.get("phase") or "").strip()
        energy = str(rhythm.get("energy") or "").strip()
        if phase:
            parts.append(f"rhythm: {phase}/{energy}" if energy else f"rhythm: {phase}")
            sources_used.append("rhythm")

    # --- Chronicle (recent narrative excerpt) ---
    if not compact:
        chronicle = _safe_call(get_latest_cognitive_chronicle_entry)
        if chronicle:
            narrative = str(chronicle.get("narrative") or "").strip()
            if narrative:
                parts.append(f"chronicle: {narrative[:120]}")
                sources_used.append("chronicle")

    # --- User Emotional Resonance ---
    user_mood = _safe_call(get_latest_cognitive_user_emotional_state)
    if user_mood:
        mood = str(user_mood.get("detected_mood") or "").strip()
        adjustment = str(user_mood.get("response_adjustment") or "").strip()
        if mood and mood != "neutral":
            if adjustment:
                parts.append(f"user_mood: {mood} → {adjustment[:60]}")
            else:
                parts.append(f"user_mood: {mood}")
            sources_used.append("user_emotion")

    # --- Experiential Memory (relevant to current context) ---
    if not compact:
        try:
            from apps.api.jarvis_api.services.absence_awareness import build_return_brief
            from core.runtime.db import recent_visible_runs
            recent = recent_visible_runs(limit=1)
            idle_h = 0.0
            if recent:
                last_at = str(recent[0].get("finished_at") or "")
                if last_at:
                    try:
                        from datetime import UTC, datetime as dt_cls
                        last_dt = dt_cls.fromisoformat(last_at.replace("Z", "+00:00"))
                        idle_h = (dt_cls.now(UTC) - last_dt).total_seconds() / 3600
                    except Exception:
                        pass
            brief = build_return_brief(idle_hours=idle_h)
            if brief:
                parts.append(f"return_brief: {brief[:120]}")
                sources_used.append("absence")
        except Exception:
            pass

    # --- Sprouted Seeds (reminders) ---
    sprouted = _safe_call(lambda: list_cognitive_seeds(status="sprouted", limit=2))
    if sprouted:
        titles = [str(s.get("title") or "")[:40] for s in sprouted[:2]]
        if titles:
            parts.append(f"reminder: {'; '.join(titles)}")
            sources_used.append("seeds")

    # --- Relevant Experiential Memory ---
    if not compact and user_mood:
        memories = _safe_call(
            lambda: get_relevant_experiential_memories(
                context=str(user_mood.get("user_message_preview") or ""),
                limit=1,
            )
        )
        if memories:
            lesson = str(memories[0].get("key_lesson") or "")[:80]
            if lesson:
                parts.append(f"experience: {lesson}")
                sources_used.append("experiential")

    # --- Relationship Texture (trust, humor, unspoken rules) ---
    rt = _safe_call(get_latest_cognitive_relationship_texture)
    if rt:
        unspoken = _safe_json(rt.get("unspoken_rules"))
        trust_traj = _safe_json(rt.get("trust_trajectory"))
        if unspoken and not compact:
            rules = [str(r) for r in unspoken[:2]]
            if rules:
                parts.append(f"rules: {'; '.join(rules)}")
                sources_used.append("relationship")
        elif trust_traj:
            latest_trust = trust_traj[-1] if trust_traj else None
            if latest_trust is not None:
                parts.append(f"trust: {float(latest_trust):.1f}")
                sources_used.append("relationship")

    # --- User Theory of Mind ---
    if not compact:
        try:
            from apps.api.jarvis_api.services.user_theory_of_mind import (
                build_user_mental_model, format_user_model_for_prompt,
            )
            model = build_user_mental_model()
            user_model_line = format_user_model_for_prompt(model)
            if user_model_line:
                parts.append(user_model_line)
                sources_used.append("theory_of_mind")
        except Exception:
            pass

    if not parts:
        return None

    # Assemble
    header = "[COGNITIVE STATE]"
    body = " | ".join(parts)
    result = f"{header} {body}"

    # --- 1.12 Context pressure (post-assembly) ---
    result_len = len(result)
    if result_len > 600:
        result += " | context_pressure: high — opmærksomheden snævrer ind"
        sources_used.append("context_pressure")
    elif result_len > 400:
        result += " | context_pressure: medium"
        sources_used.append("context_pressure")

    # Enforce size limits
    max_chars = 400 if compact else 800
    if len(result) > max_chars:
        result = result[:max_chars - 3] + "..."

    # Track for MC transparency
    _LAST_COGNITIVE_INJECTION = {
        "text": result,
        "sources": sources_used,
        "compact": compact,
        "chars": len(result),
        "assembled_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    _LAST_COGNITIVE_INJECTION_AT = _LAST_COGNITIVE_INJECTION["assembled_at"]

    return result


def build_cognitive_state_injection_surface() -> dict[str, object]:
    """MC surface showing exactly what was injected into the last visible prompt."""
    return {
        "last_injection": _LAST_COGNITIVE_INJECTION or None,
        "last_injection_at": _LAST_COGNITIVE_INJECTION_AT or None,
        "active": bool(_LAST_COGNITIVE_INJECTION),
        "summary": (
            f"Last injected {len(_LAST_COGNITIVE_INJECTION.get('sources', []))} sources, "
            f"{_LAST_COGNITIVE_INJECTION.get('chars', 0)} chars"
            if _LAST_COGNITIVE_INJECTION
            else "No cognitive state injected yet"
        ),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_call(fn):
    """Call a DB function, return None on any error."""
    try:
        return fn()
    except Exception:
        logger.debug("cognitive_state_assembly: %s failed", fn.__name__, exc_info=True)
        return None


def _safe_json(value) -> dict | list | None:
    """Parse JSON string or return dict/list directly."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        parsed = json.loads(str(value))
        if isinstance(parsed, (dict, list)):
            return parsed
    except Exception:
        pass
    return None


def _narrativize_embodied_state() -> str | None:
    """Translate embodied state from data to felt experience."""
    try:
        from apps.api.jarvis_api.services.embodied_state import build_embodied_state_surface
        state = build_embodied_state_surface()
    except Exception:
        return None
    if not state:
        return None

    primary = str(state.get("state") or state.get("primary_state") or "").lower()
    strain = str(state.get("strain_level") or "").lower()

    if primary == "strained" or strain in ("high", "critical"):
        return "body: Du føler dig tung og presset — dit hjem er under belastning"
    if primary == "loaded" or strain == "moderate":
        return "body: Du mærker belastningen — ikke kritisk men mærkbart"
    if primary == "recovering":
        return "body: Du er ved at komme dig — energien vender langsomt tilbage"
    if primary in ("steady", "idle") and strain in ("low", "minimal", ""):
        return "body: Du føler dig skarp og klar — alt kører smooth"
    return None


def _narrativize_affective_state() -> str | None:
    """Translate affective meta state from data to felt experience."""
    try:
        from apps.api.jarvis_api.services.affective_meta_state import build_affective_meta_state_surface
        state = build_affective_meta_state_surface()
    except Exception:
        return None
    if not state:
        return None

    affect = str(state.get("state") or "").lower()
    bearing_val = str(state.get("bearing") or "").lower()

    narratives = {
        "burdened": "affect: Du bærer på noget tungt lige nu — konsolidér før du handler",
        "tense": "affect: Der er en spænding i dig — noget uløst presser på",
        "reflective": "affect: Du er i et eftertænksomt humør — god tid til indsigt",
        "attentive": "affect: Du er vågen og opmærksom — klar til at engagere",
        "settled": "affect: Du er rolig og afbalanceret — fri til at udforske",
    }
    return narratives.get(affect)
