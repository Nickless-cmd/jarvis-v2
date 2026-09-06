"""Afbrydelses-noten må ikke blive samtale-historik modellen efterligner.

MÅLT 5/9-2026: 45 stubs på tværs af systemet, klumpet — 16 i én session, så 8,
7, 4, 2. Klumpningen ER symptomet. Med tre i træk i én session svarede DeepSeek
på en helt almindelig prompt ved at skrive den SAMME sætning igen: komplet
delta-strøm, `first_pass_status: completed`, `native_tool_call_count: 0`.

Ét ægte cut avlede derfra en uendelig række falske. Brugeren oplever konstante
afbrydelser; i virkeligheden blev han afbrudt én gang og papegøjer siden.
"""
from __future__ import annotations

import pytest

from core.services.interruption_notice import (
    INTERRUPTION_NOTICE,
    is_interruption_notice,
    strip_interruption_notices,
)


class TestGenkendelse:
    def test_genkender_sin_egen_tekst(self):
        """Skriveren og filteret deler konstanten — driver de fra hinanden,
        bliver filteret stille virkningsløst."""
        assert is_interruption_notice(INTERRUPTION_NOTICE)

    def test_taaler_smaa_variationer(self):
        assert is_interruption_notice("Jeg blev afbrudt midt i det.")
        assert is_interruption_notice("  Jeg blev afbrudt midt i det — prøv igen  ")

    @pytest.mark.parametrize("aegte", [
        "Jeg har læst filen og fandt fejlen i linje 42.",
        "Kommandoen kører nu i baggrunden på din maskine.",
        "",
        "   ",
    ])
    def test_aegte_svar_roeres_ikke(self, aegte):
        assert not is_interruption_notice(aegte)

    def test_lang_tekst_er_ikke_noten(self):
        """Et langt svar der TILFÆLDIGVIS nævner en afbrydelse er et ægte svar."""
        lang = ("Jeg blev afbrudt midt i det tidligere, og her er hvad jeg nåede: "
                + "detaljer " * 80)
        assert not is_interruption_notice(lang)


class TestFiltrering:
    def test_noten_fjernes_fra_modellens_historik(self):
        h = [{"role": "user", "content": "hej"},
             {"role": "assistant", "content": INTERRUPTION_NOTICE},
             {"role": "assistant", "content": "rigtigt svar"}]
        ud = strip_interruption_notices(h)
        assert [m["content"] for m in ud] == ["hej", "rigtigt svar"]

    def test_flere_stubs_i_traek_fjernes_alle(self):
        """Det var netop tre i træk der udløste efterligningen."""
        h = [{"role": "user", "content": "a"}] + [
            {"role": "assistant", "content": INTERRUPTION_NOTICE} for _ in range(3)]
        assert len(strip_interruption_notices(h)) == 1

    def test_BRUGERENS_egne_ord_bevares(self):
        """Skriver Bjørn selv at han blev afbrudt, er det en ægte ytring."""
        h = [{"role": "user", "content": "du blev afbrudt midt i det igen"}]
        assert strip_interruption_notices(h) == h

    def test_tool_beskeder_roeres_ikke(self):
        h = [{"role": "tool", "content": "[bash]: ok"}]
        assert strip_interruption_notices(h) == h

    def test_tom_historik(self):
        assert strip_interruption_notices([]) == []

    def test_vroevl_vaelter_ikke_prompten(self):
        """Filteret sidder i prompt-bygningen — det må aldrig kaste."""
        h = [None, "ikke en dict", {"role": "assistant"}]
        assert len(strip_interruption_notices(h)) == 3
