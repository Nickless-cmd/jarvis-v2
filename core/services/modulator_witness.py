"""Witness surface for hidden behavior modulators.

These layers change later behavior without always appearing as visible
prompt text. This surface makes their current causal pressure inspectable
in Mission Control.
"""
from __future__ import annotations

from typing import Any


def _item(
    *,
    name: str,
    active: bool,
    current_effect: dict[str, object],
    evidence: list[dict[str, object]],
    confidence: float,
    allowed_effects: list[str],
    source: str,
) -> dict[str, object]:
    return {
        "name": name,
        "active": bool(active),
        "current_effect": current_effect,
        "evidence": evidence,
        "confidence": max(0.0, min(1.0, float(confidence))),
        "allowed_effects": allowed_effects,
        "source": source,
    }


def _safe_call(fn, default):
    try:
        return fn()
    except Exception:
        return default


def build_modulator_witness_surface(*, workspace_id: str = "default") -> dict[str, object]:
    """Return active hidden modulators and the effects they are allowed to have."""
    items: list[dict[str, object]] = []

    dream_bias = _safe_call(
        lambda: __import__(
            "core.services.dream_bias_engine",
            fromlist=["get_active_dream_bias"],
        ).get_active_dream_bias(workspace_id=workspace_id),
        None,
    )
    if dream_bias:
        items.append(
            _item(
                name="dream_bias",
                active=True,
                current_effect={
                    "attention_bias": dream_bias.get("attention_bias") or {},
                    "threshold_bias": dream_bias.get("threshold_bias") or {},
                    "intensity": dream_bias.get("intensity"),
                },
                evidence=[
                    {"field": "last_dream_at", "value": dream_bias.get("last_dream_at")},
                    {"field": "ttl_expires_at", "value": dream_bias.get("ttl_expires_at")},
                    {"field": "accumulated_count", "value": dream_bias.get("accumulated_count")},
                    {"field": "source_kinds", "value": dream_bias.get("source_kinds") or []},
                ],
                confidence=min(1.0, max(0.2, float(dream_bias.get("intensity") or 0.0))),
                allowed_effects=[
                    "heartbeat_prompt_awareness",
                    "open_loop_surface_limit",
                    "self_review_surface_limit",
                    "visible_empty_round_budget",
                    "self_critique_cadence",
                ],
                source="core.services.dream_bias_engine",
            )
        )

    temperature = _safe_call(
        lambda: __import__(
            "core.services.user_temperature_engine",
            fromlist=["get_active_field", "get_response_style_modifiers"],
        ).get_active_field(workspace_id=workspace_id),
        None,
    )
    style_modifiers = _safe_call(
        lambda: __import__(
            "core.services.user_temperature_engine",
            fromlist=["get_response_style_modifiers"],
        ).get_response_style_modifiers(workspace_id=workspace_id),
        {"preferred_length": "normal", "warmth": "neutral", "pace": "normal"},
    )
    if temperature:
        items.append(
            _item(
                name="user_temperature",
                active=True,
                current_effect={
                    "response_style": style_modifiers,
                    "field_texture": temperature.get("field_texture"),
                    "field_intensity": temperature.get("field_intensity"),
                    "field_conflict": bool(temperature.get("field_conflict")),
                },
                evidence=[
                    {"field": "field_valens", "value": temperature.get("field_valens")},
                    {"field": "field_arousal", "value": temperature.get("field_arousal")},
                    {"field": "struct_texture", "value": temperature.get("struct_texture")},
                    {"field": "llm_texture", "value": temperature.get("llm_texture")},
                    {"field": "last_structural_at", "value": temperature.get("last_structural_at")},
                    {"field": "last_llm_at", "value": temperature.get("last_llm_at")},
                ],
                confidence=max(
                    0.1,
                    min(
                        1.0,
                        float(temperature.get("struct_confidence") or 0.0),
                        float(temperature.get("llm_confidence") or 1.0),
                    ),
                ),
                allowed_effects=[
                    "heartbeat_prompt_awareness",
                    "visible_response_style_hint",
                    "unconscious_sampling_modulation_input",
                ],
                source="core.services.user_temperature_engine",
            )
        )

    sampling = _safe_call(
        lambda: __import__(
            "core.services.unconscious_modulation",
            fromlist=["compute_unconscious_modulation"],
        ).compute_unconscious_modulation(
            base_temperature=None,
            base_top_p=None,
            workspace_id=workspace_id,
        ),
        (0.7, 1.0),
    )
    base_sampling = (0.7, 1.0)
    sampling_changed = tuple(round(float(x), 4) for x in sampling) != base_sampling
    items.append(
        _item(
            name="unconscious_sampling",
            active=sampling_changed,
            current_effect={
                "temperature": sampling[0],
                "top_p": sampling[1],
                "base_temperature": base_sampling[0],
                "base_top_p": base_sampling[1],
            },
            evidence=[
                {"field": "derived_from", "value": "user_temperature"},
                {"field": "changed_from_base", "value": sampling_changed},
            ],
            confidence=0.8 if sampling_changed else 0.4,
            allowed_effects=["visible_llm_temperature", "visible_llm_top_p"],
            source="core.services.unconscious_modulation",
        )
    )

    affect_overrides: dict[str, Any] = _safe_call(
        lambda: __import__(
            "core.services.affect_modulation",
            fromlist=["compute_affect_modulated_params"],
        ).compute_affect_modulated_params(),
        {},
    )
    items.append(
        _item(
            name="affect_modulation",
            active=bool(affect_overrides),
            current_effect={"overrides": affect_overrides},
            evidence=[
                {"field": "override_count", "value": len(affect_overrides)},
                {"field": "override_keys", "value": sorted(affect_overrides.keys())},
            ],
            confidence=0.75 if affect_overrides else 0.35,
            allowed_effects=[
                "max_tool_calls_per_turn",
                "pause_before_respond_ms",
                "response_length_target",
                "search_depth",
                "investigate_before_answer",
            ],
            source="core.services.affect_modulation",
        )
    )

    active = [item for item in items if item.get("active")]
    return {
        "active": bool(active),
        "items": items,
        "summary": {
            "count": len(items),
            "active_count": len(active),
            "active_names": [str(item["name"]) for item in active],
        },
    }
