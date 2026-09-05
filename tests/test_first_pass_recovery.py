"""Første-pas-kure: tomt svar (resend) og tomt løfte (nudge).

Kuren mod tomme løfter findes fordi værnet strukturelt ALDRIG kunne se dem:
det bor i followup-loopet, og hele det loop ligger inde i
`if _collected_native_tool_calls:`. Et første pas med prosa og nul værktøjskald
sprang loopet over. Det var Bjørns cutoff hele 5/9.
"""
from __future__ import annotations

import pytest

from core.services.first_pass_recovery import first_pass_is_hollow, resend_target


class TestResendTarget:
    def test_deepseek_beholder_modellen_men_taber_thinking(self):
        """Thinking-bug'en er STICKY — samme model med thinking igen bliver tom igen."""
        assert resend_target("deepseek", "deepseek-v4-flash") == (
            "deepseek", "deepseek-v4-flash", "fast")

    @pytest.mark.parametrize("model", [
        "kimi-k2.7-code:cloud", "qwen3-max", "glm-5.2:cloud", "gpt-oss-120b",
    ])
    def test_andre_thinking_modeller_falder_til_non_thinking(self, model):
        """Før faldt de tilbage til SAMME sticky model → cutoff (3. jul, kimi)."""
        assert resend_target("ollama", model) == ("deepseek", "deepseek-v4-flash", "fast")

    def test_en_almindelig_model_roeres_ikke(self):
        assert resend_target("openai", "gpt-4o") == ("openai", "gpt-4o", None)

    def test_noget_vaerre_end_ventet_giver_det_uaendrede_par(self):
        assert resend_target(None, None) == (None, None, None)


class TestFirstPassIsHollow:
    def test_et_loefte_uden_vaerktoej_er_tomt(self):
        assert first_pass_is_hollow("Lad mig tjekke config'en.", 0) is True

    def test_de_faktiske_cutoffs_5_september(self):
        """Ordret fra chat_messages — begge slap forbi, fordi loopet blev sprunget over."""
        assert first_pass_is_hollow(
            "Cutoff igen — det er præcis den, vi har jagtet hele dagen. Lad mig "
            "se hvad der skete i run-tilstanden og om det er den samme HTTP "
            "400-fejl eller noget nyt. Jeg tjekker det direkte nu.", 0) is True
        assert first_pass_is_hollow(
            "Du har ret — og det er en vigtig præcisering. Lad mig grave i "
            "historikken om Smiths faktiske rolle.", 0) is True

    def test_samme_tekst_MED_et_vaerktoejskald_er_ikke_tom(self):
        assert first_pass_is_hollow("Jeg tjekker det direkte nu.", 1) is False

    def test_tomt_svar_haandteres_af_resend_kuren_ikke_denne(self):
        assert first_pass_is_hollow("", 0) is False
        assert first_pass_is_hollow("   ", 0) is False

    def test_et_svar_uden_loefte_roeres_ikke(self):
        assert first_pass_is_hollow("Ja, det er rigtigt — filen ligger i core/.", 0) is False

    def test_en_talehandling_er_ikke_et_tomt_loefte(self):
        assert first_pass_is_hollow("Lad mig forklare hvorfor det gik galt.", 0) is False

    def test_slukket_vaern_griber_ikke_ind(self, monkeypatch):
        monkeypatch.setenv("JARVIS_HOLLOW_PROMISE_GUARD", "0")
        assert first_pass_is_hollow("Lad mig tjekke config'en.", 0) is False
