"""Self-scoped API for Desk Chat Flow presentation preferences."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from core.services.chat_flow_preferences import (
    ChatFlowIdentityError,
    ack_chat_flow_onboarding,
    claim_chat_flow_onboarding,
    get_chat_flow_state,
    record_chat_flow_observation,
    record_chat_flow_suggestion,
    resolve_chat_flow_principal,
    set_chat_flow_state,
)

router = APIRouter(prefix="/api/chat-flow", tags=["chat-flow"])


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PreferenceUpdate(_StrictModel):
    preference: Literal["living", "calm", "adaptive"] | None = None
    suggestions_enabled: bool | None = None


class OnboardingClaim(_StrictModel):
    run_id: str = Field(min_length=1, max_length=200)


class OnboardingAck(_StrictModel):
    claim_id: str = Field(min_length=1, max_length=200)


class Observation(_StrictModel):
    meaningful_steps: int = Field(ge=0, le=10_000)
    expanded_work: bool = False
    manual_override: Literal["living", "calm"] | None = None


class SuggestionOutcome(_StrictModel):
    kind: Literal["living", "calm"]
    outcome: Literal["accepted", "rejected", "dismissed"]


def _principal() -> str:
    try:
        return resolve_chat_flow_principal()
    except ChatFlowIdentityError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/preferences")
def preferences_get() -> dict:
    return get_chat_flow_state(_principal())


@router.patch("/preferences")
def preferences_patch(payload: PreferenceUpdate) -> dict:
    if payload.preference is None and payload.suggestions_enabled is None:
        raise HTTPException(status_code=400, detail="preference or suggestions_enabled required")
    return set_chat_flow_state(
        _principal(),
        preference=payload.preference,
        suggestions_enabled=payload.suggestions_enabled,
        explicit=payload.preference is not None,
    )


@router.post("/onboarding/claim")
def onboarding_claim(payload: OnboardingClaim) -> dict:
    return claim_chat_flow_onboarding(_principal(), payload.run_id)


@router.post("/onboarding/ack")
def onboarding_ack(payload: OnboardingAck) -> dict:
    try:
        return ack_chat_flow_onboarding(_principal(), payload.claim_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/observations")
def observations_post(payload: Observation) -> dict:
    return record_chat_flow_observation(
        _principal(),
        meaningful_steps=payload.meaningful_steps,
        expanded_work=payload.expanded_work,
        manual_override=payload.manual_override,
    )


@router.post("/suggestions/outcome")
def suggestion_outcome(payload: SuggestionOutcome) -> dict:
    return record_chat_flow_suggestion(
        _principal(), kind=payload.kind, outcome=payload.outcome
    )
