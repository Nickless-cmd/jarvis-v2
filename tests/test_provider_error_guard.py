"""Tests for core/services/provider_error_guard.py.

Regressionsværn for 30-08-2026: aihubmix' kvote-afvisning blev gemt som et
ASSISTENT-svar i Bjørns samtale, og kørslen talte som ``completed``. En udbyders
fejlbesked må aldrig stå som Jarvis' svar.
"""

from __future__ import annotations

import pytest

from core.services.provider_error_guard import describe, looks_like_provider_error

# Den ægte tekst der udløste værnet — ordret fra chat_messages 2026-08-30T10:04:26Z.
AIHUBMIX = (
    "Sorry, to prevent abuse of free resources, accounts that have not been "
    "recharged can only try 10 times. You can increase the free quota after "
    "recharging; https://console.aihubmix.com/topup…"
)


def test_the_real_incident_is_caught() -> None:
    assert looks_like_provider_error(AIHUBMIX) is True


@pytest.mark.parametrize(
    "text",
    [
        "Rate limit exceeded. Please try again later.",
        '{"error": {"message": "insufficient quota", "type": "invalid_request_error"}}',
        "Your account balance is insufficient. Top up at https://example.com/billing",
        "Invalid API key provided.",
        "Model not found: deepseek-v9-turbo",
        "Service unavailable, please try again later.",
        "Error: 429 Too Many Requests",
    ],
)
def test_provider_errors_are_caught(text: str) -> None:
    assert looks_like_provider_error(text) is True


@pytest.mark.parametrize(
    "text",
    [
        # Jarvis SKRIVER om kvoter — må aldrig kasseres.
        "Jeg har rettet fejlen i cheap-lanen — kvoten på aihubmix var opbrugt, "
        "så jeg flyttede den til NAT64-vejen. Testene er grønne.",
        # Den falske positiv der afslørede at længdegrænsen alene ikke rakte.
        "Her er en gennemgang af jeres rate limits: deepseek har 60 kald/min, groq "
        "har 30. Jeg foreslår at vi fordeler belastningen, og at du overvejer at "
        "recharge kontoen hos aihubmix hvis I vil have mere headroom.",
        "Opgaven er løst. Filerne er committet og pushet.",
        "Jeg kan ikke nå api'et lige nu — der er en fejl i routingen som jeg undersøger.",
        # Jarvis skriver også engelsk ind imellem.
        "(Task completed — ready for next instructions.)",
        "I've fixed the quota handling in the cheap lane and added a test for the "
        "rate limit path.",
    ],
)
def test_real_replies_are_not_caught(text: str) -> None:
    assert looks_like_provider_error(text) is False


def test_danish_beats_error_signals() -> None:
    """Udbydere svarer aldrig på dansk — det er det stærkeste enkeltsignal."""
    dansk = ("Kvoten er opbrugt og rate limit exceeded på den konto, så jeg "
             "skifter til en anden udbyder.")
    assert looks_like_provider_error(dansk) is False


def test_long_english_prose_is_not_an_error() -> None:
    """En lang engelsk forklaring er et svar, ikke en fejlbesked."""
    long_text = ("The rate limit on that provider is fairly generous, but if you "
                 "keep hitting it you can recharge the account or spread the load "
                 "across the pool. " * 4)
    assert len(long_text) > 320
    assert looks_like_provider_error(long_text) is False


@pytest.mark.parametrize("text", ["", "   ", None])
def test_empty_is_safe(text) -> None:
    assert looks_like_provider_error(text) is False


def test_describe_is_bounded_and_safe() -> None:
    d = describe(AIHUBMIX)
    assert len(d) <= 158
    assert "\n" not in d
    assert describe("") == ""
    assert describe(None) == ""
