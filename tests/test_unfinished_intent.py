"""Tests for unfinished-intent detectoren (side-02afb491ea, 13/11-2026).

Dækker de tre målte rodårsager og tillægget om korte tekster:
1. «lige» står nu alene på tidsord-listen, med gradords-lookaheads
   (så/meget/sådan) og sætnings-negationsguard.
2. Spørgsmåls-guarden bor i continuation-gaten (23/6-incidenten må ikke
   gentages), mens registreringen (detect_promise_intent) springer den
   over — et løfte der bare huskes koster intet.
3. Kort tekst (<50 tegn) bruger nu også _FUTURE_ACTION_PROMISE_RE,
   så «Jeg tjekker det nu.» fanger et løfte.
"""

from __future__ import annotations

import core.services.unfinished_intent as ui


class TestLigeMatcher:
    """Rodårsag 1: «lige» alene skal matche på tidsord-listen."""

    def test_jeg_tjekker_lige_giver_traef(self):
        # Konkret sætning der fejlede 10/11-2026 kl. 16:17.
        intent = ui.detect_unfinished_intent(
            "Jeg tjekker lige at nøglerne er væk og vender tilbage med svar."
        )
        assert intent is not None
        assert intent.pattern == "future_action_promise"

    def test_lige_nu_traef_stadig(self):
        intent = ui.detect_unfinished_intent(
            "Jeg opdaterer lige nu den række der mangler i tabellen."
        )
        assert intent is not None
        assert intent.pattern == "future_action_promise"

    def test_lige_saa_ikke_traef(self):
        # «lige så» er gradsord, ikke tidsord: regex-lookahead skal afvise.
        intent = ui.detect_unfinished_intent(
            "Jeg tester lige så grundigt som sidste gang, men med de nye"
            " rækker med i tabellen."
        )
        assert intent is None

    def test_lige_meget_ikke_traef(self):
        intent = ui.detect_unfinished_intent(
            "Jeg tester lige meget med og uden cache ved at sammenligne"
            " to rækker i tabellen."
        )
        assert intent is None

    def test_lige_saaan_ikke_traef(self):
        intent = ui.detect_unfinished_intent(
            "Jeg tester lige sådan et af de gamle moduler for at"
            " sammenligne resultaterne med arkivet."
        )
        assert intent is None

    def test_negation_ikke_lige_ikke_traef(self):
        # Sætnings-negationen: «ikke» står før matchet i samme sætning.
        intent = ui.detect_unfinished_intent(
            "Jeg tjekker ikke lige den fil igen, for den er allerede"
            " verificeret."
        )
        assert intent is None


class TestGuardSplit:
    """Rodårsag 2: guarden blokerer continuation, ikke registrering."""

    def test_sporgsmaal_blokerer_continuation_ikke_registrering(self):
        t = (
            "Jeg tjekker lige at nøglerne er væk og vender tilbage med"
            " svar. Skal jeg gemme dem i arkivet igen?"
        )
        assert ui.detect_unfinished_intent(t) is None
        intent = ui.detect_promise_intent(t)
        assert intent is not None
        assert intent.pattern == "future_action_promise"

    def test_detect_promise_intent_kraver_future_action_promise(self):
        # Cliffhanger er en continuation-signatur, ikke et løfte.
        assert ui.detect_promise_intent("Her er status på det hele:") is None
        assert ui.detect_promise_intent(
            "Sådan her gør jeg det, nu kommer detaljerne..."
        ) is None

    def test_saetningsnegation_blokerer_registrering(self):
        t = "Jeg tjekker ikke lige det punkt igen, det er allerede verificeret."
        assert ui.detect_promise_intent(t) is None

    def test_saetningssporgsmaal_blokerer_registrering(self):
        # Tvetydigt løfte-til-spørgsmål registreres konservativt heller ikke:
        # sætnings-guarden gælder for registrering (kun guard-GATEN skippes).
        t = "Jeg tjekker lige tabellen nu, hvad siger du om det?"
        assert ui.detect_promise_intent(t) is None

    def test_none_input(self):
        assert ui.detect_promise_intent(None) is None
        assert ui.detect_promise_intent("") is None
        assert ui.detect_promise_intent("   ") is None


class TestKortTekstTillaeg:
    """Tillæg: future-promise-mønstret gælder også under 50 tegn."""

    def test_kort_lofte_giver_traef(self):
        intent = ui.detect_promise_intent("Jeg tjekker det nu.")
        assert intent is not None
        assert intent.pattern == "future_action_promise"

    def test_kort_negation_giver_ikke_traef(self):
        assert ui.detect_promise_intent("Jeg tjekker ikke det nu.") is None
