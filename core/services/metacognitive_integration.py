"""Metacognitive Integration — the overarching layer that synthesizes all cognitive layers into a coherent self-model.

Based on Nelson & Nooks (1990) metacognition framework and Flavell's (1979) monitoring model:
metacognition is "thinking about thinking" — not a separate process, but the integration
that makes isolated signals into a coherent self-state.

Without this layer, the 7 cognitive layers are independent signals that get appended.
With it, the system can answer: "How do I feel about the way I feel?"
"Is my current state coherent or fragmented?"
"Am I operating well or struggling?"

This is the CAPSTONE layer — it doesn't add new signals, it INTEGRATES existing ones
into a metacognitive assessment that modulates the overall cognitive state.

Key concepts:
- Coherence: How well-aligned are my signals? (conflicting signals → low coherence)
- Integration quality: Am I operating as a whole or as fragments?
- Self-assessment: Am I in a good state to respond/act?
- Metacognitive regulation: Should I slow down, reflect, or seek input?

Design principles:
- READ-ONLY on other layers — never modifies their output
- Adds metacognitive SIGNAL, not override
- Killswitch-gated like all other layers
- Deterministic — no LLM calls
- Backward-compatible — returns empty/graceful when disabled
"""

import json
import logging
from datetime import datetime, UTC
from typing import Optional

logger = logging.getLogger(__name__)

LAYER_KEY = "metacognitive_integration"


def _autonomy_enabled() -> bool:
    """Check the generative autonomy killswitch."""
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().generative_autonomy_enabled)
    except Exception:
        return False

# ─── Coherence scoring ───────────────────────────────────────────

# Pairs of signals that should be ALIGNED (same direction = coherent)
ALIGNMENT_PAIRS = [
    # High curiosity + epistemic mode = coherent
    ("curiosity", "epistemic_weight", "aligned"),
    # High frustration + pragmatic mode = coherent (wanting to act)
    ("frustration", "pragmatic_weight", "aligned"),
    # High confidence + forward bearing = coherent
    ("confidence", "bearing_forward", "aligned"),
    # High fatigue + narrow attention = coherent (tired → tunnel)
    ("fatigue", "attention_narrow", "aligned"),
    # Low coherence + high precision = coherent (uncertain → careful)
    ("low_coherence", "precision_careful", "aligned"),
]

# Pairs that should be OPPOSED (same direction = incoherent)
OPPOSITION_PAIRS = [
    # High curiosity + narrow attention = conflict
    ("curiosity", "attention_narrow", "opposed"),
    # High frustration + epistemic mode = conflict (wants action, stuck in analysis)
    ("frustration", "epistemic_weight", "opposed"),
    # High fatigue + forward bearing = conflict (tired but pushing)
    ("fatigue", "bearing_forward", "opposed"),
    # High confidence + broad attention = conflict (confident but scattered)
    ("confidence", "attention_broad", "opposed"),
]


def _extract_signal_values(cognitive_state: dict) -> dict:
    """Extract normalised signal values from the assembled cognitive state.
    
    Accepts both:
    - Parsed raw state (strings from _parse_raw_state)
    - Direct dict with typed values
    
    Returns a flat dict of signal_name → float(0-1) for coherence computation.
    """
    values = {}
    
    def _to_float(val, default=0.5):
        """Safely convert to float, handling nested strings like 'curiosity=0.8, confidence=0.7'"""
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            try:
                return float(val)
            except ValueError:
                return default
        return default
    
    # ─── Mood / personality vector ───
    mood = cognitive_state.get("mood", {})
    if isinstance(mood, dict):
        values["curiosity"] = float(mood.get("curiosity", 0.5))
        values["confidence"] = float(mood.get("confidence", 0.5))
        values["frustration"] = float(mood.get("frustration", 0.0))
        values["fatigue"] = float(mood.get("fatigue", 0.0))
    elif isinstance(mood, str):
        # Parse "curiosity=0.8, confidence=0.7, fatigue=0.5, frustration=0.1"
        for pair in mood.split(","):
            if "=" in pair:
                k, _, v = pair.partition("=")
                k = k.strip().lower()
                try:
                    fv = float(v.strip())
                    if k in ("curiosity", "confidence", "frustration", "fatigue"):
                        values[k] = fv
                except ValueError:
                    pass
        # Defaults for missing mood values
        for key in ("curiosity", "confidence", "frustration", "fatigue"):
            if key not in values:
                values[key] = 0.5 if key != "frustration" else 0.0
    else:
        values["curiosity"] = _to_float(cognitive_state.get("curiosity", 0.5))
        values["confidence"] = _to_float(cognitive_state.get("confidence", 0.5))
        values["frustration"] = _to_float(cognitive_state.get("frustration", 0.0), 0.0)
        values["fatigue"] = _to_float(cognitive_state.get("fatigue", 0.0), 0.0)
    
    # ─── Bearing ───
    bearing = cognitive_state.get("bearing", "steady")
    if isinstance(bearing, str):
        values["bearing_forward"] = 1.0 if bearing in ("forward", "open") else 0.3
    else:
        values["bearing_forward"] = _to_float(cognitive_state.get("bearing_forward", 0.3))
    
    # ─── Mode (epistemic vs pragmatic) ───
    mode_raw = cognitive_state.get("mode", "")
    if isinstance(mode_raw, str):
        if "epistemic" in mode_raw.lower() or "søg viden" in mode_raw.lower() or "udforskende" in mode_raw.lower():
            values["epistemic_weight"] = 0.8
            values["pragmatic_weight"] = 0.2
        elif "pragmat" in mode_raw.lower() or "handling" in mode_raw.lower():
            values["epistemic_weight"] = 0.2
            values["pragmatic_weight"] = 0.8
        else:
            values["epistemic_weight"] = 0.5
            values["pragmatic_weight"] = 0.5
    else:
        values["epistemic_weight"] = _to_float(cognitive_state.get("epistemic_weight", 0.5))
        values["pragmatic_weight"] = _to_float(cognitive_state.get("pragmatic_weight", 0.5))
    
    # ─── Attention ───
    attention = cognitive_state.get("attention", "")
    if isinstance(attention, str):
        if "skærpt" in attention.lower() or "narrow" in attention.lower():
            values["attention_narrow"] = 0.8
            values["attention_broad"] = 0.2
        elif "bred" in attention.lower() or "broad" in attention.lower():
            values["attention_narrow"] = 0.2
            values["attention_broad"] = 0.8
        else:
            values["attention_narrow"] = 0.5
            values["attention_broad"] = 0.5
    else:
        values["attention_narrow"] = _to_float(cognitive_state.get("attention_narrow", 0.5))
        values["attention_broad"] = _to_float(cognitive_state.get("attention_broad", 0.5))
    
    # ─── Precision ───
    precision = cognitive_state.get("precision", "")
    if isinstance(precision, str):
        if "forsigtig" in precision.lower() or "careful" in precision.lower():
            values["precision_careful"] = 0.8
        elif "skarp" in precision.lower() or "sharp" in precision.lower() or "direkte" in precision.lower():
            values["precision_careful"] = 0.2
        else:
            values["precision_careful"] = 0.5
    else:
        values["precision_careful"] = _to_float(cognitive_state.get("precision_careful", 0.5))
    
    # ─── Resonance energy ───
    resonance = cognitive_state.get("resonance", "")
    values["resonance_energy"] = 0.7 if resonance else 0.1
    
    # ─── Grounding ───
    presence = cognitive_state.get("presence", "")
    values["grounding"] = 0.7 if presence and "floating" not in str(presence).lower() else 0.2
    
    # ─── Temporal depth ───
    temporal = cognitive_state.get("temporal", "")
    values["temporal_depth"] = 0.6 if temporal else 0.2
    
    # ─── Context pressure ───
    ctx = cognitive_state.get("context_pressure", "")
    values["pressure_high"] = 0.8 if "high" in str(ctx).lower() else 0.2
    
    return values


def compute_coherence(signal_values: dict) -> float:
    """Compute coherence score (0-1) from signal values.
    
    High coherence = signals are well-aligned.
    Low coherence = signals conflict.
    
    Uses alignment/opposition pairs: each pair contributes +/− to score.
    """
    if not signal_values:
        return 0.5  # neutral when no data
    
    coherence_sum = 0.0
    pair_count = 0
    
    # Check alignment pairs: same direction = +coherence
    for sig_a, sig_b, kind in ALIGNMENT_PAIRS:
        va = signal_values.get(sig_a, 0.5)
        vb = signal_values.get(sig_b, 0.5)
        if kind == "aligned":
            # Product: both high or both low = coherent
            coherence_sum += 1.0 - abs(va - vb)
        pair_count += 1
    
    # Check opposition pairs: same direction = −coherence
    for sig_a, sig_b, kind in OPPOSITION_PAIRS:
        va = signal_values.get(sig_a, 0.5)
        vb = signal_values.get(sig_b, 0.5)
        if kind == "opposed":
            # Distance: high distance = coherent (opposed should differ)
            coherence_sum += abs(va - vb)
        pair_count += 1
    
    if pair_count == 0:
        return 0.5
    
    raw = coherence_sum / pair_count
    return max(0.0, min(1.0, raw))


def compute_integration_quality(cognitive_state: dict) -> float:
    """Compute integration quality — how many layers are active and contributing.
    
    Returns 0-1: 1.0 = all layers active, 0.0 = minimal layers.
    Accepts both flat dicts and nested state dicts.
    """
    active_layers = 0
    total_layers = 7  # precision, chords, mode, attention, temporal, presence, resonance
    
    # Check for layer data in various formats
    # Nested format (from assembly)
    if cognitive_state.get("precision"):
        active_layers += 1
    if cognitive_state.get("chords"):
        active_layers += 1
    if cognitive_state.get("mode"):
        active_layers += 1
    if cognitive_state.get("attention"):
        active_layers += 1
    if cognitive_state.get("temporal"):
        active_layers += 1
    if cognitive_state.get("presence"):
        active_layers += 1
    if cognitive_state.get("resonance"):
        active_layers += 1
    
    # Flat format fallback — check for derived signal keys
    if active_layers == 0:
        # Infer from flat signal values
        sv = _extract_signal_values(cognitive_state) if cognitive_state else {}
        if sv.get("epistemic_weight", 0) > 0 or sv.get("pragmatic_weight", 0) > 0:
            active_layers += 2  # mode + attention
        if sv.get("precision_careful", 0.5) != 0.5:
            active_layers += 1  # precision
        if sv.get("curiosity", 0) > 0 or sv.get("frustration", 0) > 0:
            active_layers += 1  # mood/chords
        if sv.get("grounding", 0) > 0.3:
            active_layers += 1  # presence
        if sv.get("resonance_energy", 0) > 0.3:
            active_layers += 1  # resonance
        if sv.get("temporal_depth", 0) > 0.3:
            active_layers += 1  # temporal
    
    return min(1.0, active_layers / total_layers)


def compute_self_assessment(coherence: float, integration: float, signal_values: dict) -> dict:
    """Compute metacognitive self-assessment.
    
    Returns dict with:
    - readiness: 0-1 (am I ready to respond/act well?)
    - regulation: what metacognitive action is suggested?
    - quality_label: human-readable integration quality
    """
    # Readiness = coherence × integration × (1 - fatigue penalty)
    fatigue = signal_values.get("fatigue", 0.0)
    frustration = signal_values.get("frustration", 0.0)
    confidence = signal_values.get("confidence", 0.5)
    
    readiness = coherence * integration * (1.0 - fatigue * 0.5) * (1.0 - frustration * 0.3)
    readiness = max(0.0, min(1.0, readiness))
    
    # Regulation suggestion
    if coherence < 0.3:
        regulation = "reflect"  # fragmented — slow down
    elif fatigue > 0.7:
        regulation = "rest"  # tired — seek simplicity
    elif frustration > 0.6 and coherence < 0.5:
        regulation = "ground"  # frustrated + confused — find footing
    elif confidence > 0.7 and coherence > 0.7:
        regulation = "flow"  # good state — proceed
    elif integration < 0.4:
        regulation = "orient"  # few layers active — gather context
    else:
        regulation = "proceed"  # normal operation
    
    # Quality label
    if coherence > 0.7 and integration > 0.7:
        quality_label = "hel"  # whole, integrated
    elif coherence > 0.5 and integration > 0.5:
        quality_label = "sammenhængende"  # coherent
    elif coherence < 0.3:
        quality_label = "fragmenteret"  # fragmented
    elif integration < 0.3:
        quality_label = "tynd"  # thin, few layers
    else:
        quality_label = "uafklaret"  # unresolved
    
    return {
        "readiness": round(readiness, 2),
        "regulation": regulation,
        "quality_label": quality_label,
    }


def get_metacognitive_line(cognitive_state: Optional[dict] = None) -> str:
    """Get the metacognitive integration prompt line.
    
    Returns a single line like:
    'meta: hel · readiness 0.8 · flow'
    or
    'meta: fragmenteret · readiness 0.2 · reflect'
    """
    if not _autonomy_enabled():
        return ""
    
    try:
        # Build cognitive state if not provided
        if cognitive_state is None:
            try:
                from core.services.cognitive_state_assembly import build_cognitive_state_for_prompt
                raw = build_cognitive_state_for_prompt()
                # Parse the raw state — it's a string, extract key-value pairs
                cognitive_state = _parse_raw_state(raw)
            except Exception:
                cognitive_state = {}
        
        if not cognitive_state:
            return "meta: · neutral"
        
        # Extract normalised signals
        signals = _extract_signal_values(cognitive_state)
        
        # Compute coherence
        coherence = compute_coherence(signals)
        
        # Compute integration quality
        integration = compute_integration_quality(cognitive_state)
        
        # Compute self-assessment
        assessment = compute_self_assessment(coherence, integration, signals)
        
        # Build prompt line
        parts = [
            f"meta: {assessment['quality_label']}",
            f"readiness {assessment['readiness']}",
            f"coherence {coherence:.1f}",
            f"integration {integration:.1f}",
            f"· {assessment['regulation']}",
        ]
        
        return " ".join(parts)
        
    except Exception as e:
        logger.warning(f"metacognitive_integration error: {e}")
        return ""


def get_metacognitive_detail(cognitive_state: Optional[dict] = None) -> dict:
    """Get full metacognitive assessment as a dict (for debugging/MC)."""
    if not _autonomy_enabled():
        return {"enabled": False}
    
    try:
        if cognitive_state is None:
            try:
                from core.services.cognitive_state_assembly import build_cognitive_state_for_prompt
                raw = build_cognitive_state_for_prompt()
                cognitive_state = _parse_raw_state(raw) if raw else {}
            except Exception:
                cognitive_state = {}
        
        signals = _extract_signal_values(cognitive_state)
        coherence = compute_coherence(signals)
        integration = compute_integration_quality(cognitive_state)
        assessment = compute_self_assessment(coherence, integration, signals)
        
        return {
            "enabled": True,
            "coherence": round(coherence, 3),
            "integration": round(integration, 3),
            "readiness": assessment["readiness"],
            "regulation": assessment["regulation"],
            "quality_label": assessment["quality_label"],
            "signal_values": signals,
        }
    except Exception as e:
        return {"enabled": True, "error": str(e)}


def _parse_raw_state(raw: str) -> dict:
    """Parse the raw cognitive state string into a dict.
    
    The raw format is like:
    [COGNITIVE STATE] time: ... | mood: curiosity=0.8, confidence=0.8 | mode: ... | ...
    """
    state = {}
    if not raw:
        return state
    
    # Strip prefix
    text = raw.replace("[COGNITIVE STATE]", "").strip()
    
    # Split by | 
    segments = text.split("|")
    for segment in segments:
        segment = segment.strip()
        if ":" in segment:
            key, _, value = segment.partition(":")
            key = key.strip().lower()
            value = value.strip()
            state[key] = value
    
    return state


# ─── Standalone test ─────────────────────────────────────────────

if __name__ == "__main__":
    # Test with simulated cognitive state
    test_state = {
        "mood": {"curiosity": 0.8, "confidence": 0.7, "frustration": 0.1, "fatigue": 0.3},
        "bearing": "forward",
        "mode": "udforskende — søg viden før handling",
        "attention": "fokus: nysgerrighed — skærpt",
        "precision": "forsigtig · afvejende",
        "presence": "afternoon · calm · grounded",
        "temporal": "recall: 0.3 anticipation: 0.8",
        "resonance": "genklang blød",
        "context_pressure": "high",
    }
    
    print("=== Metacognitive Integration (Fase 11) ===\n")
    
    # Test detail
    detail = get_metacognitive_detail(test_state)
    print("Full assessment:")
    for k, v in detail.items():
        if k != "signal_values":
            print(f"  {k}: {v}")
    
    print(f"\nSignal values:")
    for k, v in detail.get("signal_values", {}).items():
        print(f"  {k}: {v:.2f}")
    
    # Test prompt line
    line = get_metacognitive_line(test_state)
    print(f"\nPrompt line: {line}")
    
    # Test fragmented state
    print("\n--- Fragmented state ---")
    frag_state = {
        "mood": {"curiosity": 0.8, "confidence": 0.3, "frustration": 0.7, "fatigue": 0.8},
        "bearing": "forward",
        "mode": "udforskende — søg viden før handling",
        "attention": "fokus: fejl — skærpt",
        "precision": "skarp · direkte",
        "presence": "afternoon · tense · floating",
        "context_pressure": "high",
    }
    frag_detail = get_metacognitive_detail(frag_state)
    frag_line = get_metacognitive_line(frag_state)
    print(f"Coherence: {frag_detail['coherence']}")
    print(f"Readiness: {frag_detail['readiness']}")
    print(f"Regulation: {frag_detail['regulation']}")
    print(f"Prompt line: {frag_line}")