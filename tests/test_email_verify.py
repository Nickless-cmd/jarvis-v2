"""Tests for email-verifikation (spec 2026-06-15 §5)."""
from __future__ import annotations


def test_create_and_consume_token(isolated_runtime) -> None:
    from core.identity.email_verify import create_token, consume_token
    tok = create_token(user_id="u1", email="a@b.dk")
    assert tok and isinstance(tok, str)
    uid = consume_token(tok)
    assert uid == "u1"
    # Token kan kun bruges én gang
    assert consume_token(tok) is None


def test_expired_token_rejected(isolated_runtime) -> None:
    from core.identity import email_verify
    tok = email_verify.create_token(user_id="u2", email="c@b.dk", ttl_hours=-1)
    assert email_verify.consume_token(tok) is None


def test_rate_limit_three_per_email_per_day(isolated_runtime) -> None:
    import pytest
    from core.identity.email_verify import create_token, RateLimited
    for _ in range(3):
        create_token(user_id="u3", email="rate@b.dk")
    with pytest.raises(RateLimited):
        create_token(user_id="u3", email="rate@b.dk")


def test_send_verification_email_uses_mail_sender(isolated_runtime, monkeypatch) -> None:
    from core.identity import email_verify
    sent = {}

    def fake_send(args):
        sent.update(args)
        return {"success": True}

    monkeypatch.setattr(email_verify, "_send_mail", fake_send)
    tok = email_verify.send_verification_email(user_id="u4", email="dest@b.dk",
                                               base_url="https://jarvis.srvlab.dk")
    assert sent["to"] == "dest@b.dk"
    assert tok in sent["body"]
    assert "verify" in sent["body"]
