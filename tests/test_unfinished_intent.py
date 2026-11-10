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

    def test_cliffhanger_er_ikke_et_loefte(self):
        # Cliffhanger er en continuation-signatur, ikke et løfte. Den er derfor
        # bevidst UDEN FOR _LOFTE_PATTERNS — ellers blev ledgeren ren støj.
        assert ui.detect_promise_intent("Her er status på det hele:") is None
        assert ui.detect_promise_intent(
            "Sådan her gør jeg det, nu kommer detaljerne..."
        ) is None

    def test_saetningsnegation_blokerer_registrering(self):
        t = "Jeg tjekker ikke lige det punkt igen, det er allerede verificeret."
        assert ui.detect_promise_intent(t) is None

    def test_saetningssporgsmaal_blokerer_registrering(self):
        # REVURDERET 10/11-2026: testen brugte «Jeg tjekker lige tabellen nu,
        # hvad siger du om det?» som eksempel på et spørgsmål der skal blokere.
        # Det var for bredt — sætningen er et LØFTE i indikativ med et
        # tillægsspørgsmål, og registreringen skal huske løftet (se
        # TestSpoergendeLedEfterLoftet). Blokeringen gælder stadig når
        # sætningen ER et spørgsmål, dvs. når det spørgende led står først.
        assert ui.detect_promise_intent(
            "Er det ok at jeg tjekker tabellen nu?"
        ) is None
        # Negation gælder uændret.
        assert ui.detect_promise_intent(
            "Jeg tjekker ikke lige tabellen nu, den er verificeret."
        ) is None

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


class TestRegistreringUdenSpoergsmaalstegnGuard:
    """Rodårsag 2, anden halvdel (målt 10/11-2026).

    Den fælles sætnings-guard blokerede på ETHVERT «?», så et jeg-form-løfte
    med et retorisk spørgsmålstegn hverken blev registreret eller fanget.
    Målt: «Jeg tjekker lige at nøglerne faktisk er væk fra pending, så det
    ikke bare er din overbevisning jeg citerer?» → None fra BEGGE gater.

    Registrering koster intet, så der kræves nu BÅDE et tilbuds-ord OG et
    «?» for at blokere. Continuation er UÆNDRET: et afsluttende spørgsmål
    giver fortsat kontrollen tilbage til brugeren (23/6-incidenten).
    """

    # Den konkrete sætning fra 10/11-2026 kl. 16:17.
    REELLE = (
        "Jeg tjekker lige at nøglerne faktisk er væk fra pending, så det"
        " ikke bare er din overbevisning jeg citerer?"
    )

    def test_reelt_loefte_med_spoergsmaalstegn_registreres(self):
        intent = ui.detect_promise_intent(self.REELLE)
        assert intent is not None, "løftet forsvandt på grund af et retorisk «?»"

    def test_samme_saetning_blokerer_stadig_continuation(self):
        # Regression: spørgsmåls-guarden i continuation-gaten må IKKE løsnes.
        assert ui.detect_unfinished_intent(self.REELLE) is None

    def test_tilbud_til_brugeren_registreres_ikke(self):
        # Et tilbud er ikke et løfte — og det blokeres af tilbuds-ord + «?».
        assert ui.detect_promise_intent(
            "Vil du have at jeg tjekker nøglerne for dig?"
        ) is None
        assert ui.detect_promise_intent(
            "Skal jeg tjekke nøglerne for dig?"
        ) is None

    def test_tilbud_uden_spoergsmaalstegn_registreres(self):
        # «Først skal jeg dog hente seneste version» er en konstatering, og
        # uden «?» er den ikke et tilbud — den skal stadig kunne registreres
        # når den bærer et løfte. Måler at vi ikke genindførte den gamle
        # overblokering ved at kræve «?» fraværende.
        intent = ui.detect_promise_intent(
            "Først skal jeg lige hente seneste version, og så tjekker jeg"
            " nøglerne igennem for dig."
        )
        assert intent is not None

    def test_jeg_skal_er_ogsaa_et_loefte(self):
        # «Jeg skal lige …» klassificeres som «jeg_skal», ikke
        # «future_action_promise». Før faldt den ud af registreringen fordi
        # filteret kun accepterede sidstnævnte.
        intent = ui.detect_promise_intent(
            "Jeg skal lige tjekke nøglerne igennem inden jeg svarer dig,"
            " så vi ikke bygger videre på en forkert antagelse."
        )
        assert intent is not None
        assert intent.pattern == "jeg_skal"

    def test_negation_registreres_ikke(self):
        # Negationen gælder uændret i registrerings-tilstanden.
        assert ui.detect_promise_intent(
            "Jeg tjekker ikke lige den fil igen, for den er allerede"
            " verificeret."
        ) is None


class TestTilbudUdenForListenRegistreresIkke:
    """Regression målt 10/11-2026 af reviewer, verificeret af mig.

    Første forsøg på at løsne «?»-guarden krævede BÅDE et tilbuds-ord OG et
    «?». Det lod spørgsmål som «Er det ok at jeg genstarter serveren nu?»
    blive registreret som løfter — og ledger-prompten siger «Hvis nej, så GØR
    det nu», så et ubesvaret spørgsmål blev til en ordre om at handle. Det er
    23/6-fejlen ad en ny vej.

    Retningen er nu den modsatte: et «?» blokerer stadig, medmindre sætningen
    er en jeg-form-handling i indikativ.
    """

    def test_spoergsmaal_uden_tilbudsord_registreres_ikke(self):
        for t in (
            "Er det ok at jeg genstarter serveren nu?",
            "Giver det mening at jeg tester det nu?",
            "Hvad med at jeg kører testsuiten igen nu?",
            "Ønsker du at jeg sletter filen nu?",
        ):
            assert ui.detect_promise_intent(t) is None, t

    def test_spoergende_led_efter_loftet_ophaever_det_ikke(self):
        # REVURDERET 10/11-2026. Denne test hed «…_blokerer» og hævdede at et
        # spørgende led midt i sætningen ophævede løftet. Det var for bredt:
        # sætningen er et LØFTE i indikativ («Jeg tjekker lige tabellen nu»)
        # med et tillægsspørgsmål («hvad siger du om det?»). At spørge hvad
        # Bjørn synes ophæver ikke at jeg tjekker — og registreringen findes
        # netop for at holde mig ansvarlig for det jeg sagde jeg ville gøre.
        #
        # Målt før rettelsen: reglen tabte løftet i BEGGE gater. For
        # continuation er det stadig korrekt (jeg venter på svar).
        intent = ui.detect_promise_intent(
            "Jeg tjekker lige tabellen nu, hvad siger du om det?"
        )
        assert intent is not None, "et ægte løfte forsvandt på et tillægsspørgsmål"
        assert intent.pattern in ui._LOFTE_PATTERNS
        # Continuation skal fortsat vente på svar — den er ikke ændret.
        assert ui.detect_unfinished_intent(
            "Jeg tjekker lige tabellen nu, hvad siger du om det?"
        ) is None


class TestHandoffRegistreresIkke:
    """Regression målt 10/11-2026: registreringen sprang handoff-guarden over.

    En handoff («så sig til», «lad mig vide», «giv besked») er Jarvis der
    bevidst giver kontrollen tilbage — ikke en uafsluttet opgave. Uden guarden
    blev «…hvis der er andet, jeg skal kigge på, så sig til.» registreret som
    et løfte om at kigge på noget.

    Målt i HEAD før rettelsen: både continuation OG registrering misfyrede på
    «Lad mig vide, hvis du vil have mig til at tjekke noget mere i morgen.» —
    fordi mønstret krævede at frasen stod HELT til sidst, og et komma efter
    frasen brød matchningen.
    """

    def test_handoff_ved_afslutning_registreres_ikke(self):
        assert ui.detect_promise_intent(
            "Alt er gennemgået og verificeret grundigt, hvis der er andet"
            " jeg skal kigge på, så sig til."
        ) is None

    def test_handoff_med_komma_og_bisaetning_registreres_ikke(self):
        # Den form der slap igennem: komma efter frasen + fortsat bisætning.
        assert ui.detect_promise_intent(
            "Lad mig vide, hvis du vil have mig til at tjekke noget mere"
            " i morgen."
        ) is None
        assert ui.detect_promise_intent(
            "Giv mig besked, hvis der er noget du vil have kigget på i morgen."
        ) is None

    def test_handoff_blokerer_ogsaa_continuation(self):
        # Samme utæthed ramte continuation — den er ikke kun registreringens.
        assert ui.detect_unfinished_intent(
            "Lad mig vide, hvis du vil have mig til at tjekke noget mere"
            " i morgen."
        ) is None

    def test_aegte_pause_efter_handoff_frasen_registreres(self):
        # Guarden må ikke dræbe et ægte løfte: her er der ingen handoff, kun
        # en jeg-form-handling der fortsætter.
        intent = ui.detect_promise_intent(
            "Jeg skal lige tjekke nøglerne igennem en ekstra gang for at"
            " være helt sikker på at de er væk fra pending-listen nu."
        )
        assert intent is not None
