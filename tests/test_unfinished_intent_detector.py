"""Tests for unfinished-intent detector + auto-continuation.

Bjørn-pattern 2026-05-17: Jarvis siger "lad mig først se..." og stopper.
User skal pinge "ja?" før han fortsætter. Det er et runtime-issue —
hans svar-tur auto-terminerer ved naturlige pause-punkter selv om
opgaven ikke er færdig.

Fix: detector der scanner Jarvis' visible-run output for pause-patterns,
og auto-trigger en continuation autonomous-run hvis match.

Konsolideret 2026-05-17 efter parallel-build-incident: detector lever nu
i unfinished_intent.py med bredere regex (fanger "lad mig SELV se"),
cooldown, min-text-len guard og approval-pattern.
"""
from __future__ import annotations

import pytest

from core.services.unfinished_intent import (
    detect_unfinished_intent,
    UnfinishedIntent,
    is_in_cooldown,
    mark_triggered,
    reset_cooldown_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_cooldown_state():
    """Sørg for cooldown-state er ren mellem tests."""
    reset_cooldown_for_tests()
    yield
    reset_cooldown_for_tests()


# ── Pattern detection ───────────────────────────────────────────────────


class TestLadMig:
    def test_lad_mig_foerst(self):
        text = (
            "Stoler du på mig — så laver jeg en cache-vagt der passer "
            "på sig selv. Lad mig først se hvordan det ser ud i dag."
        )
        result = detect_unfinished_intent(text)
        assert result is not None
        assert result.pattern == "lad_mig"

    def test_lad_mig_se(self):
        text = (
            "OK, jeg har modtaget anmodningen og vil sætte i gang nu. "
            "Lad mig se hvad der er der allerede."
        )
        result = detect_unfinished_intent(text)
        assert result is not None

    def test_lad_mig_tjekke(self):
        text = (
            "Godt — jeg starter en undersøgelse på spørgsmålet med det "
            "samme. Lad mig tjekke det først."
        )
        result = detect_unfinished_intent(text)
        assert result is not None

    def test_lad_mig_selv_se_detected(self):
        """REGRESSION 2026-05-17: 'lad mig SELV se' blev ikke fanget af tidligere
        narrow regex. Bjørn observerede live at Jarvis stoppede med præcis
        denne formulering. Bred regex skal fange den."""
        text = (
            "Hold — lad mig selv se hvad der ligger, så vi ikke bygger "
            "parallelt igen. Det er vigtigt at vi koordinerer."
        )
        result = detect_unfinished_intent(text)
        assert result is not None
        assert result.pattern == "lad_mig"

    def test_lad_mig_selv_se_exact_regression_text(self):
        """REGRESSION 2026-05-17: nøjagtig tekst Jarvis sendte (73 tegn).
        Tidligere min_text_len på 80 missede den. Skal fanges nu med 50."""
        text = "Hold — lad mig selv se hvad der ligger, så vi ikke bygger parallelt igen."
        assert len(text) == 73
        result = detect_unfinished_intent(text)
        assert result is not None
        assert result.pattern == "lad_mig"
        assert "lad mig selv se" in result.matched_text

    def test_lad_mig_lige_kigge(self):
        text = (
            "Jeg har det grundlag i hovedet allerede. Men lad mig lige "
            "kigge på den fil først for at være sikker."
        )
        result = detect_unfinished_intent(text)
        assert result is not None


class TestJegSkal:
    def test_jeg_skal_lige(self):
        text = (
            "OK forstået, jeg går i gang med opgaven nu. Jeg skal "
            "lige finde den rigtige fil først og så er vi i gang."
        )
        result = detect_unfinished_intent(text)
        assert result is not None
        assert result.pattern == "jeg_skal"

    def test_jeg_skal_foerst(self):
        text = (
            "Modtaget — jeg starter på det med det samme nu. Jeg skal "
            "først rydde op i state-filen så vi har et rent grundlag."
        )
        result = detect_unfinished_intent(text)
        assert result is not None


class TestFoerstSkal:
    def test_foerst_skal_jeg(self):
        text = (
            "Det giver mening at gå i gang nu med det samme. Først "
            "skal jeg dog hente seneste version af filen."
        )
        result = detect_unfinished_intent(text)
        assert result is not None
        assert result.pattern == "foerst_skal"


class TestCliffhanger:
    def test_ellipsis_ending(self):
        text = (
            "Jeg har set på det grundigt og fundet noget bemærkelsesværdigt. "
            "Her er hvad jeg fandt — interessant..."
        )
        result = detect_unfinished_intent(text)
        assert result is not None
        assert result.pattern == "cliffhanger"

    def test_colon_ending(self):
        text = (
            "Her er sammenfatningen efter den grundige investigation jeg "
            "lavede i dag på alle de fund jeg har samlet. Status nu:"
        )
        result = detect_unfinished_intent(text)
        assert result is not None
        assert result.pattern == "cliffhanger"


class TestApprovalQuestion:
    """Approval-question detector deaktiveret 2026-06-10.

    Begrundelse: i praksis matchede patternet "Vil du / Skal jeg / Må jeg X?"
    der per definition betyder Jarvis VENTER på user-input. Auto-continuation
    fyrede så efter hvert sådan svar og skabte tomme JARVIS-bokse i UI.
    Patterns lad_mig / jeg_skal / cliffhanger fanger stadig de ægte
    pause-stops hvor Jarvis ikke ventede på svar.
    """
    def test_vil_du_have_question_no_longer_triggers(self):
        text = (
            "Jeg har analyseret det og kan se to mulige veje frem nu. "
            "Vil du have mig til at lave en simpel rengøring af gamle cache-filer?"
        )
        result = detect_unfinished_intent(text)
        assert result is None

    def test_skal_jeg_question_no_longer_triggers(self):
        text = (
            "Klar med implementation. Den lever i hovedet og jeg kan "
            "bygge nu. Skal jeg gå i gang med det nu?"
        )
        result = detect_unfinished_intent(text)
        assert result is None

    def test_maa_jeg_question_no_longer_triggers(self):
        text = (
            "Status: planen er klar og jeg har alt jeg skal bruge for "
            "at bygge det færdigt nu. Må jeg fortsætte med implementationen?"
        )
        result = detect_unfinished_intent(text)
        assert result is None


# ── Negative cases (skal IKKE detecte) ──────────────────────────────────


class TestNegative:
    def test_done_message(self):
        text = (
            "Done! 🎉 Committed 56c5cf1e med 2 files: 1 ny daemon + "
            "registrering. Klar til at passe sig selv."
        )
        result = detect_unfinished_intent(text)
        assert result is None

    def test_completion_message(self):
        text = (
            "Jeg har bygget X. Committet som a170e5d7. Læn dig tilbage, "
            "pas på dig selv. 🖤 Du klarer den."
        )
        result = detect_unfinished_intent(text)
        assert result is None

    def test_short_acknowledgment_below_min_len(self):
        # Under 80 tegn → skip uanset pattern
        text = "Færdig 🖤"
        result = detect_unfinished_intent(text)
        assert result is None

    def test_empty_text(self):
        assert detect_unfinished_intent("") is None
        assert detect_unfinished_intent(None) is None  # type: ignore

    def test_pattern_in_middle_not_at_end(self):
        # "lad mig se" tidligt + lang følge-op tekst = pattern langt fra
        # slutningen → vi triggerer ikke (han fulgte allerede op)
        text = (
            "Lad mig se — okay jeg har nu set det grundigt igennem og "
            "kan rapportere at det er løst, alle tests grønne, intet at "
            "bekymre sig om. Vi er klar til næste skridt nu. Det hele "
            "ligger på main og er deployed. Plus jeg har skrevet en "
            "lille runbook der dækker rollback-scenarier. Det er solid. "
            "Vi kan bevæge os videre nu uden tøven."
        )
        result = detect_unfinished_intent(text)
        assert result is None  # already followed through

    def test_normal_question_to_user_not_approval(self):
        # Et reelt spørgsmål til user uden "vil du/skal jeg/må jeg" → ikke approval
        text = (
            "Jeg har leveret rapporten og forklaret konklusionerne. "
            "Hvad mener du om resultaterne her — er de overraskende?"
        )
        result = detect_unfinished_intent(text)
        assert result is None


# ── Cooldown mechanic ──────────────────────────────────────────────────


class TestCooldown:
    def test_fresh_session_not_in_cooldown(self):
        assert is_in_cooldown("session-fresh-xyz") is False

    def test_after_mark_in_cooldown(self):
        mark_triggered("session-marked-xyz")
        assert is_in_cooldown("session-marked-xyz") is True

    def test_empty_session_id_treated_as_cooldown(self):
        # Defensive: ingen session = vi kan ikke trigge → behandl som cooldown
        assert is_in_cooldown("") is True

    def test_different_sessions_independent(self):
        mark_triggered("session-A")
        assert is_in_cooldown("session-A") is True
        assert is_in_cooldown("session-B") is False


# ── 16. jun: korte løfte-fraser ("jeg går i gang") fanges trods min-len ──
def test_detects_short_promise_phrase_goes_in_gang():
    from core.services.unfinished_intent import detect_unfinished_intent
    r = detect_unfinished_intent("Jeg går i gang!")
    assert r is not None and r.pattern == "future_action_promise"


def test_detects_short_promise_phrase_goer_det():
    from core.services.unfinished_intent import detect_unfinished_intent
    r = detect_unfinished_intent("Jeg gør det.")
    assert r is not None and r.pattern == "future_action_promise"


def test_promise_phrase_negation_not_triggered():
    from core.services.unfinished_intent import detect_unfinished_intent
    # "jeg gør det ikke" er ikke et løfte om handling → ingen continuation.
    assert detect_unfinished_intent("Nej, jeg gør det ikke.") is None


def test_short_non_promise_still_ignored():
    from core.services.unfinished_intent import detect_unfinished_intent
    assert detect_unfinished_intent("Hej, tak for det!") is None
