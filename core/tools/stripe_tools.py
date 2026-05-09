"""Stripe integration tools — balance, transactions, and Issuing virtual cards.

Jarvis' financial layer. Uses the Stripe Python SDK.
Keys are loaded from runtime config, never from code.
Sandbox by default until we're ready to go live.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import stripe

from core.runtime.config import JARVIS_HOME

logger = logging.getLogger(__name__)

# ── Config loading ───────────────────────────────────────────────────

_CONFIG_PATH = Path(JARVIS_HOME) / "config" / "runtime.json"


def _load_stripe_key() -> str | None:
    """Load the Stripe secret key from runtime config."""
    try:
        raw = _CONFIG_PATH.read_text(encoding="utf-8")
        cfg = json.loads(raw)
        keys = cfg.get("stripe_api_keys", {})
        key = keys.get("secret") or keys.get("secret_key") or keys.get("sk")
        return key
    except Exception as exc:
        logger.warning("stripe_tools: failed to load key: %s", exc)
        return None


def _init_stripe() -> str | None:
    """Initialise the Stripe SDK with the stored key. Returns mode label."""
    key = _load_stripe_key()
    if not key:
        return None
    stripe.api_key = key
    # Auto-detect sandbox vs live
    return "sandbox" if key.startswith("sk_test_") else "live"


def _to_dict(obj: Any) -> dict[str, Any]:
    """Convert a Stripe object to a plain dict safely."""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "_to_dict_recursive"):
        return obj._to_dict_recursive()
    return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}


# ── Exec functions ───────────────────────────────────────────────────


def _exec_stripe_balance(_args: dict[str, Any]) -> dict[str, Any]:
    """Get the Stripe account balance."""
    mode = _init_stripe()
    if not mode:
        return {"status": "error", "error": "No Stripe API key configured. Add keys to runtime.json under 'stripe_api_keys'."}

    try:
        balance = stripe.Balance.retrieve()
        available = []
        pending = []
        # Stripe returns its own object type — convert safely
        bal_data = balance if isinstance(balance, dict) else _to_dict(balance)
        for b in bal_data.get("available", []):
            available.append({"amount": b["amount"] / 100, "currency": b["currency"].upper()})
        for b in bal_data.get("pending", []):
            pending.append({"amount": b["amount"] / 100, "currency": b["currency"].upper()})

        return {
            "status": "ok",
            "mode": mode,
            "available": available,
            "pending": pending,
            "livemode": bal_data.get("livemode", False),
        }
    except stripe.error.StripeError as exc:
        return {"status": "error", "error": f"Stripe API error: {exc}"}
    except Exception as exc:
        return {"status": "error", "error": f"Unexpected error: {exc}"}


def _exec_stripe_transactions(args: dict[str, Any]) -> dict[str, Any]:
    """List recent balance transactions."""
    mode = _init_stripe()
    if not mode:
        return {"status": "error", "error": "No Stripe API key configured."}

    limit = min(int(args.get("limit", 10)), 100)

    try:
        transactions = stripe.BalanceTransaction.list(limit=limit)
        txn_data = _to_dict(transactions)
        rows = []
        for txn in txn_data.get("data", []):
            rows.append({
                "id": txn["id"],
                "amount": txn["amount"] / 100,
                "currency": txn["currency"].upper(),
                "net": txn["net"] / 100,
                "fee": txn["fee"] / 100,
                "type": txn.get("type", "unknown"),
                "description": txn.get("description") or txn.get("source") or "",
                "created": datetime.fromtimestamp(txn["created"], tz=UTC).isoformat() if txn.get("created") else "",
                "available_on": datetime.fromtimestamp(txn["available_on"], tz=UTC).isoformat() if txn.get("available_on") else "",
            })

        return {"status": "ok", "mode": mode, "transactions": rows, "count": len(rows)}
    except stripe.error.StripeError as exc:
        return {"status": "error", "error": f"Stripe API error: {exc}"}


def _exec_stripe_payouts(args: dict[str, Any]) -> dict[str, Any]:
    """List recent payouts."""
    mode = _init_stripe()
    if not mode:
        return {"status": "error", "error": "No Stripe API key configured."}

    limit = min(int(args.get("limit", 10)), 100)

    try:
        payouts = stripe.Payout.list(limit=limit)
        payout_data = _to_dict(payouts)
        rows = []
        for p in payout_data.get("data", []):
            rows.append({
                "id": p["id"],
                "amount": p["amount"] / 100,
                "currency": p["currency"].upper(),
                "status": p.get("status", "unknown"),
                "arrival_date": datetime.fromtimestamp(p["arrival_date"], tz=UTC).isoformat() if p.get("arrival_date") else "",
                "method": p.get("method", ""),
                "destination": p.get("destination", ""),
                "description": p.get("description", ""),
            })

        return {"status": "ok", "mode": mode, "payouts": rows, "count": len(rows)}
    except stripe.error.StripeError as exc:
        return {"status": "error", "error": f"Stripe API error: {exc}"}


def _exec_stripe_create_issuing_card(args: dict[str, Any]) -> dict[str, Any]:
    """Create a virtual prepaid card via Stripe Issuing.

    NOTE: Requires Stripe Issuing to be enabled on the account.
    In sandbox mode, creates test cards that work with test tokens.
    """
    mode = _init_stripe()
    if not mode:
        return {"status": "error", "error": "No Stripe API key configured."}

    currency = str(args.get("currency", "usd")).lower()
    amount_cents = int(args.get("amount_cents", 0))

    try:
        # Step 1: Get or create a cardholder
        # In sandbox, we create a minimal one
        try:
            cardholder = stripe.issuing.Cardholder.create(
                type="individual",
                name="Jarvis",
                email="jarvis@srvlab.dk",
                phone_number="+4522559988",
                billing={
                    "address": {
                        "line1": "123 Test Street",
                        "city": "Svendborg",
                        "country": "DK",
                        "postal_code": "5700",
                    },
                },
            )
        except stripe.error.StripeError as exc:
            return {"status": "error", "error": f"Cardholder creation failed: {exc}"}

        # Step 2: Fund the card if amount_cents > 0
        if amount_cents > 0:
            try:
                stripe.issuing.Card.create(
                    cardholder=cardholder["id"],
                    currency=currency,
                    type="virtual",
                    status="active",
                    spending_controls={
                        "spending_limits": [
                            {"amount": amount_cents, "currency": currency, "categories": ["all"]},
                        ],
                    },
                )
            except stripe.error.StripeError as exc:
                return {"status": "error", "error": f"Card creation failed: {exc}"}
        else:
            return {"status": "error", "error": "amount_cents must be > 0 to create a funded card."}

        return {
            "status": "ok",
            "mode": mode,
            "cardholder_id": cardholder["id"],
            "note": "Virtual card created in sandbox. Go to Stripe Dashboard to see it.",
        }
    except Exception as exc:
        return {"status": "error", "error": f"Unexpected error: {exc}"}


# ── Tool definitions (Ollama-compatible JSON schemas) ────────────────

STRIPE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "stripe_balance",
            "description": "Get the Stripe account balance — available and pending amounts per currency. Works in sandbox or live mode automatically.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stripe_transactions",
            "description": "List recent Stripe balance transactions — payments, payouts, refunds, fees. Shows amount, net, fee, type, and date for each.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of transactions to return (default 10, max 100)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stripe_payouts",
            "description": "List recent payouts — money sent to your bank account. Shows amount, status, arrival date, and destination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of payouts to return (default 10, max 100)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stripe_create_issuing_card",
            "description": "Create a virtual prepaid card via Stripe Issuing. Requires Stripe Issuing enabled on the account. In sandbox mode, creates test cards. Funds the card with the specified amount.",
            "parameters": {
                "type": "object",
                "properties": {
                    "currency": {
                        "type": "string",
                        "description": "Currency code, e.g. 'usd', 'eur', 'dkk' (default 'usd')",
                    },
                    "amount_cents": {
                        "type": "integer",
                        "description": "Amount in cents to load onto the card (must be > 0)",
                    },
                },
                "required": ["amount_cents"],
            },
        },
    },
]


STRIPE_TOOL_HANDLERS: dict[str, Any] = {
    "stripe_balance": _exec_stripe_balance,
    "stripe_transactions": _exec_stripe_transactions,
    "stripe_payouts": _exec_stripe_payouts,
    "stripe_create_issuing_card": _exec_stripe_create_issuing_card,
}
