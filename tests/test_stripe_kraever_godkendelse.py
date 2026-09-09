"""Et værktøj der opretter et RIGTIGT betalingskort skal spørge først.

`stripe_create_issuing_card` stod uden nogen form for godkendelse — ikke engang
den `approval_needed` som `phone_adb_shell` har haft siden juli. Fundet 9/9-2026
ved at gennemgå de muterende værktøjer uden gate-kald.

Samme port som en kommando på Bjørns telefon: en handling der koster penge må
ikke have en lettere vej end en der læser en fil.
"""
from __future__ import annotations

import pytest

from core.tools import stripe_tools as ST


@pytest.fixture
def stripe_klar(monkeypatch):
    monkeypatch.setattr(ST, "_STRIPE_AVAILABLE", True, raising=False)
    monkeypatch.setattr(ST, "_init_stripe", lambda: "sandbox")


def test_uden_godkendelse_spoerges_der(stripe_klar):
    r = ST._exec_stripe_create_issuing_card({"currency": "usd", "amount_cents": 5000})
    assert r["status"] == "approval_needed"
    assert r["tool_name"] == "stripe_create_issuing_card"


def test_beskeden_siger_BELOEB_og_valuta(stripe_klar):
    """Man skal kunne se hvad man siger ja til."""
    r = ST._exec_stripe_create_issuing_card({"currency": "eur", "amount_cents": 12345})
    assert "123.45" in r["message"] and "EUR" in r["message"]


def test_der_oprettes_INTET_kort_uden_godkendelse(stripe_klar, monkeypatch):
    """Det afgørende: Stripe må ikke være blevet kaldt."""
    kald = []
    class _Kortholder:
        @staticmethod
        def create(**kw): kald.append("cardholder"); raise AssertionError("må ikke kaldes")
    class _Issuing:
        Cardholder = _Kortholder
    monkeypatch.setattr(ST, "stripe", type("S", (), {"issuing": _Issuing}), raising=False)
    r = ST._exec_stripe_create_issuing_card({"currency": "usd", "amount_cents": 100})
    assert r["status"] == "approval_needed" and kald == []


def test_der_ER_en_force_handler_saa_godkendelsen_ikke_loeber_i_RING():
    """Uden den ville et godkendt kald ramme approval-grenen igen og svare
    `approval_needed` på ny — godkendelsen kom frem, handlingen skete aldrig."""
    from core.tools.force_handlers import _FORCE_HANDLERS
    assert "stripe_create_issuing_card" in _FORCE_HANDLERS


def test_force_handleren_saetter_trust_flaget(monkeypatch):
    """Ellers ville den ramme sin egen approval-gren."""
    set_args = {}
    def _fake(args):
        set_args.update(args)
        return {"status": "ok"}
    monkeypatch.setattr(ST, "_exec_stripe_create_issuing_card", _fake)
    from core.tools.force_handlers import _force_stripe_create_issuing_card
    _force_stripe_create_issuing_card({"currency": "usd", "amount_cents": 100})
    assert set_args.get("_runtime_trust_all") is True


def test_en_manglende_noegle_spoerger_ikke_foerst(monkeypatch):
    """Uden nøgle er der intet at godkende — fejlen skal komme først."""
    monkeypatch.setattr(ST, "_STRIPE_AVAILABLE", True, raising=False)
    monkeypatch.setattr(ST, "_init_stripe", lambda: None)
    r = ST._exec_stripe_create_issuing_card({})
    assert r["status"] == "error"
