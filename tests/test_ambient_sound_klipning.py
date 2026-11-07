"""Lyd-indtryk maa ikke klippes midt i en saetning.

MAALT 7/11-2026: 83 af 99 lyd-poster i 30 dage sluttede midt i et ord, og den
laengste var praecis 80 tegn — fordi ``daemon_llm_call(max_len=80)`` klipper
haardt ved tegnet. Fixet hævede grænsen til 240 og klipper derefter ved en
saetningsgraense.

Fixet ligger paa main, men der var INGEN test der værner det: den eksisterende
``test_ambient_sound_daemon.py`` tjekker kun at en anden funktion importeres,
og den gør det ved at grepe kildekilden. Saetter nogen ``max_len`` tilbage til
80, er der intet der fælder det — og fejlen er usynlig, fordi et halvt led
LIGNER et indtryk (det har længde).

Testene her maaler ADFÆRD, ikke konstanten: de kalder ``_interpret_sound`` med
en patchet LLM og ser hvad der kommer ud.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.services import ambient_sound_daemon as asd

# En dansk beskrivelse der er 130+ tegn — altsaa laengere end den gamle graense
# paa 80. Den skal komme HELT igennem, ellers er fixet rullet tilbage.
_LANG = (
    "Der er en daempet summen fra koekkenet, og et enkelt klirren fra en kop "
    "der saettes paa bordet. Udenfor hoeres regnen let mod ruden."
)


def _kald(monkeypatch, svar: str) -> str:
    """Kald _interpret_sound med en patchet LLM der returnerer `svar`."""

    def fake_call(prompt: str, *, max_len: int = 200, fallback: str = "", daemon_name: str = "") -> str:
        # Efterlign daemon_llm_call's haarde klipning — det er netop den
        # opfoersel der gjorde skaden, saa testen skal baere den.
        return (svar or "")[:max_len]

    monkeypatch.setattr("core.services.daemon_llm.daemon_llm_call", fake_call)
    return asd._interpret_sound(
        category="ambient",
        amplitude_mean=0.12,
        amplitude_std=0.03,
        now=datetime(2026, 11, 7, 22, 0, tzinfo=UTC),
    )


def test_lang_dansk_saetning_kommer_helt_igennem(monkeypatch):
    """Regressionen: en beskrivelse over 80 tegn maa ikke klippes ved 80."""
    tekst = _kald(monkeypatch, _LANG)
    assert tekst, "LLM-svaret forsvandt — intet indtryk"
    assert len(tekst) > 80, (
        f"indtrykket blev klippet ved {len(tekst)} tegn — graensen er sat tilbage "
        f"til den blinde 80-tegns klipning"
    )
    assert tekst.rstrip(".") == _LANG.rstrip("."), (
        "beskrivelsen blev aendret selv om den passede inden for graensen"
    )


def test_klipper_ved_saetningsgraense_ikke_midt_i_ordet(monkeypatch):
    """For lang tekst skal slutte ved en saetning, ikke midt i et ord."""
    lang = " ".join(["Dette er en saetning om lyd."] * 20)  # ~560 tegn
    tekst = _kald(monkeypatch, lang)
    assert tekst, "ingen tekst tilbage"
    assert tekst.endswith(".") or tekst.endswith("…"), (
        f"indtrykket slutter midt i et ord: ...{tekst[-40:]!r}"
    )
    # Et afkortet indtryk skal baere sin egen markering, ikke bare stoppe.
    if not tekst.endswith("."):
        assert tekst.endswith("…")


def test_uden_saetningsgraense_markeres_som_afkortet(monkeypatch):
    """Kan der ikke klippes ved en graense, skal teksten MARKERES afkortet.

    Et halvt led uden markering er vaerre end ingenting: det ligner et
    faerdigt indtryk.
    """
    uden_punktum = "ord " * 100  # 400 tegn, nul saetningsslutninger
    tekst = _kald(monkeypatch, uden_punktum)
    assert tekst.endswith("…"), (
        f"afkortet tekst uden markering: ...{tekst[-40:]!r}"
    )


def test_prompt_ekko_giver_tom_tekst(monkeypatch):
    """Gentager modellen sin instruktion, maa den ikke blive et indtryk.

    Fixturen er en AEGTE post fra `sensory_memories` (maalt 7/11-2026), ikke en
    opfundet streng. En selvkomponeret «Beskriv lyden …»-tekst slap igennem
    alle moenstre og gjorde testen roed af den forkerte grund — moenstrene er
    med vilje smalle, saa en fixture skal komme fra producentens virkelige
    returform.
    """
    ekko = (
        "Okay, lad os dykke ned i, hvad øret ville bemærke ved et akustisk "
        "snapshot som dette"
    )
    assert _kald(monkeypatch, ekko) == ""
