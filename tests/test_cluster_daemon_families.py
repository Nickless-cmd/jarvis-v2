"""Tests for core/services/cluster_daemon_families.py — infra-familien (#10).

Baggrund (2026-08-30): familiens dokumentation påstod at mail_checker var
"RULES (IMAP poll, no LLM)" og at familien slet ikke havde noget LLM-medlem.
Det passede ikke — dæmonen kalder ``daemon_llm_call`` én gang pr. handlingsværdig
mail og kan sende auto-svar. Den slags dokumentations-drift gør forbruget usynligt,
så testene her binder de påstande vi faktisk læner os op ad: cadencerne og det
faktum at mail_checker koster LLM-kald.
"""

from __future__ import annotations

import pytest

from core.services import cluster_daemon_families as cdf


@pytest.fixture(autouse=True)
def _clean_throttle() -> None:
    cdf._INFRA_THROTTLE.clear()


# --- self-throttle ---------------------------------------------------------

def test_first_call_is_always_ready() -> None:
    assert cdf._infra_throttle_ready("noget", 15) is True


def test_second_call_inside_the_window_is_throttled() -> None:
    assert cdf._infra_throttle_ready("noget", 15) is True
    assert cdf._infra_throttle_ready("noget", 15) is False


def test_zero_minute_cadence_is_always_ready() -> None:
    assert cdf._infra_throttle_ready("hver-gang", 0) is True
    assert cdf._infra_throttle_ready("hver-gang", 0) is True


def test_throttle_keys_are_independent() -> None:
    assert cdf._infra_throttle_ready("a", 15) is True
    assert cdf._infra_throttle_ready("b", 15) is True, "et medlems tick må ikke kvæle et andets"
    assert cdf._infra_throttle_ready("a", 15) is False


def test_elapsed_window_becomes_ready_again(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [1_000_000.0]
    monkeypatch.setattr(cdf.time, "time", lambda: now[0])
    assert cdf._infra_throttle_ready("m", 15) is True
    now[0] += 14 * 60
    assert cdf._infra_throttle_ready("m", 15) is False
    now[0] += 2 * 60
    assert cdf._infra_throttle_ready("m", 15) is True


# --- mail_checker-dispatchen ----------------------------------------------

def test_mail_checker_reports_throttled_without_touching_imap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Andet kald inden for vinduet må ikke åbne en IMAP-forbindelse."""
    calls = []
    import core.services.mail_checker_daemon as mcd
    monkeypatch.setattr(mcd, "tick_mail_checker_daemon", lambda: calls.append(1) or {"checked": True})

    first = cdf._infra_mail_checker_live({})
    second = cdf._infra_mail_checker_live({})

    assert first == {"checked": True}
    assert second == {"status": "throttled", "cadence_minutes": 15}
    assert len(calls) == 1


def test_mail_checker_cadence_is_15_minutes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cadencen står i dokumentationen — bind den, så den ikke driver."""
    import core.services.mail_checker_daemon as mcd
    monkeypatch.setattr(mcd, "tick_mail_checker_daemon", lambda: {"checked": True})
    cdf._infra_mail_checker_live({})
    assert cdf._infra_mail_checker_live({})["cadence_minutes"] == 15


def test_a_failing_mail_checker_is_not_swallowed_silently(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dispatchen selv fanger ikke — familien gør det, og registrerer fejlen."""
    import core.services.mail_checker_daemon as mcd

    def boom() -> dict:
        raise RuntimeError("imap nede")

    monkeypatch.setattr(mcd, "tick_mail_checker_daemon", boom)
    with pytest.raises(RuntimeError):
        cdf._infra_mail_checker_live({})


# --- dokumentations-drift: mail_checker KOSTER LLM-kald -------------------

def test_mail_checker_really_does_call_an_llm() -> None:
    """Regressionsværn mod at påstanden "no LLM" sniger sig tilbage.

    Så længe dæmonen importerer ``daemon_llm_call`` er familien ikke gratis, og
    dokumentationen skal sige det.
    """
    import core.services.mail_checker_daemon as mcd
    assert hasattr(mcd, "daemon_llm_call")
    assert hasattr(mcd, "_send_auto_reply"), "den kan også sende mail — det er ikke 'rules only'"


def test_infra_family_builds_with_no_gated_members() -> None:
    fam = cdf.build_infra_family()
    assert fam.family_name == cdf.INFRA_FAMILY
    assert list(fam.members) == [], "alle otte medlemmer kører ubetinget, ikke bag gaten"
