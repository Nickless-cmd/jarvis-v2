"""Billing / Stripe-integration (spec §21.6) — SKELET.

Stripe kræver Bjørns Stripe-konto + nøgler (STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET
i runtime.json). Uden dem returnerer ruterne 503 "billing ikke konfigureret" — så
intet brækker, og strukturen + quota_store-integrationspunktet er klar.

Når nøgler er sat:
- POST /billing/checkout → opret Stripe Checkout-session for en tier-opgradering
- POST /billing/webhook → Stripe kalder; ved checkout.session.completed grantes
  ekstra kvote / tier-skift via quota_store + users.json.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/billing", tags=["billing"])

_PRICE_TIERS = ("plus", "pro")


def _stripe_key() -> str:
    """Stripe secret fra runtime.json (aldrig hardcoded, §Secrets-håndtering)."""
    env = os.environ.get("STRIPE_SECRET_KEY")
    if env:
        return env
    try:
        from core.runtime.secrets import read_runtime_key
        return str(read_runtime_key("stripe_secret_key") or "")
    except Exception:
        return ""


def _configured() -> bool:
    return bool(_stripe_key())


class _CheckoutPayload(BaseModel):
    tier: str            # "plus" | "pro"
    user_id: str


@router.get("/status")
async def billing_status() -> dict:
    """Er billing konfigureret? (UI bruger det til at vise/skjule opgraderings-knap.)"""
    return {"configured": _configured(), "tiers": list(_PRICE_TIERS)}


@router.post("/checkout")
async def create_checkout(payload: _CheckoutPayload) -> dict:
    """Opret en Stripe Checkout-session for tier-opgradering (§21.6)."""
    if payload.tier not in _PRICE_TIERS:
        raise HTTPException(status_code=400, detail=f"ugyldig tier: {payload.tier}")
    if not _configured():
        raise HTTPException(status_code=503, detail="billing ikke konfigureret (STRIPE_SECRET_KEY mangler)")
    # TODO når Stripe er sat op: import stripe; stripe.api_key=_stripe_key();
    # session = stripe.checkout.Session.create(...); return {"url": session.url}
    raise HTTPException(status_code=501, detail="Stripe checkout endnu ikke implementeret (skelet)")


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict:
    """Stripe webhook (§21.6). Verificér signatur, grant kvote/tier ved succes."""
    if not _configured():
        raise HTTPException(status_code=503, detail="billing ikke konfigureret")
    # TODO: stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET);
    # ved event.type == "checkout.session.completed":
    #   user_id = event.data.object.metadata.user_id; tier = ...metadata.tier
    #   core.identity.users.set_tier(user_id, tier)  # + quota_store nulstil
    raise HTTPException(status_code=501, detail="webhook-håndtering endnu ikke implementeret (skelet)")
