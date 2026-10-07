from __future__ import annotations

import pytest


def test_raa_raesonnement_gemmes_ikke_som_indtryk(isolated_runtime) -> None:
    """Målt 18/9: to poster i arkivet var hele reasoning-monologer.

    At strippe taggene ville efterlade monologen og få den til at ligne et
    ægte indtryk — værre end et tomt felt, fordi den så bliver læst som noget
    Jarvis har sanset.
    """
    from core.services.sensory_archive import record_audio

    with pytest.raises(ValueError):
        record_audio(
            "<think>\nOkay, so the user wants me to create a Danish sentence "
            "about the acoustic environment being classified as silence.\n"
        )


def test_svaret_efter_tanken_overlever(isolated_runtime) -> None:
    """Er tanken lukket, er teksten bagefter det rigtige indtryk."""
    from core.services.sensory_archive import record_atmosphere

    post = record_atmosphere(
        "<think>Brugeren vil have en dansk sætning om rummet.</think>\n"
        "Rummet ligger stille med en lav summen fra køleskabet."
    )

    assert "<think>" not in post["content"]
    assert "Brugeren vil have" not in post["content"]
    assert post["content"].startswith("Rummet ligger stille")


def test_almindeligt_indtryk_roeres_ikke(isolated_runtime) -> None:
    from core.services.sensory_archive import record_visual

    tekst = "Skarpt eftermiddagslys gennem vinduet, støv der driver i strålen."
    assert record_visual(tekst)["content"] == tekst


def test_pladsholder_er_ikke_et_indtryk(isolated_runtime) -> None:
    """«Intet mærkbart ændret» er et gyldigt udfald, men ikke et indtryk."""
    from core.services.sensory_archive import er_maettet

    assert er_maettet("Rummet føles tungt og stillestående, tiden står stille.")
    assert not er_maettet("Intet mærkbart ændret.")
    assert not er_maettet("intet maerkbart aendret")
    assert not er_maettet("")
    assert not er_maettet(None)


def test_seneste_maettede_springer_pladsholderne_over(isolated_runtime) -> None:
    """Den rige beskrivelse må ikke ligge ulæst bag fire kvitteringer."""
    from core.services.sensory_archive import record_visual, seneste_maettede

    record_visual("Aftenlys, lange skygger over bordet og en åben bog.")
    for _ in range(4):
        record_visual("Intet mærkbart ændret.")

    fundet = seneste_maettede(modality="visual")

    assert fundet is not None
    assert fundet["content"].startswith("Aftenlys")


def test_seneste_maettede_tier_naar_alt_er_pladsholder(isolated_runtime) -> None:
    """Ingen mættet post i vinduet → sig ingenting, grav ikke i forgårs."""
    from core.services.sensory_archive import record_visual, seneste_maettede

    for _ in range(3):
        record_visual("Intet mærkbart ændret.")

    assert seneste_maettede(modality="visual", kig=3) is None


def test_oversigten_viser_maettede_ikke_kvitteringer(isolated_runtime) -> None:
    """Fem kvitteringer i træk fik læsefladen til at se tom ud."""
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services.sensory_archive import summarize_for_context

    # Eksplicitte tidsstempler. Skrives alle syv inden for samme sekund, er
    # rækkefølgen blandt ens timestamps udefineret, og testen ville måle sin
    # egen fixture i stedet for sorteringen.
    def _skriv(minut: int, tekst: str) -> None:
        insert_sensory_memory(
            modality="visual",
            content=tekst,
            timestamp=f"2026-09-18T10:{minut:02d}:00+00:00",
        )

    _skriv(1, "Morgenlys over bordet, en kop damper stadig.")
    _skriv(2, "Skyggerne er vandret hen over gulvet siden sidst.")
    for nr in range(3, 8):
        _skriv(nr, "Intet mærkbart ændret.")

    oversigt = summarize_for_context(limit=3)

    assert oversigt["total"] == 7, "tællingen dækker HELE arkivet"
    assert oversigt["substantive_in_window"] == 2
    assert [r["content"][:12] for r in oversigt["recent"]] == ["Skyggerne er", "Morgenlys ov"]


# ── Kvitterings-gaten: skrivesiden lukket (28/9-2026) ────────────────────────
#
# Læsesiden (`er_maettet`) har filtreret kvitteringer fra siden 18/9 — men
# arkivet blev ved med at fyldes, og filteret skjulte det bagefter. Her er det
# samme spørgsmål flyttet til det ene punkt alle skrivninger går igennem.


def test_pladsholder_arkiveres_ikke(isolated_runtime) -> None:
    """«Intet mærkbart ændret.» er svaret på at der ikke var noget at se.

    Målt 28/9-2026: 45 sådanne poster i arkivet, den nyeste 26/9 — og hanen
    skrev videre, fordi `visual_memory_daemon` arkiverede hvert svar uanset.
    """
    from core.services.sensory_archive import count, record_visual

    foer = count()
    post = record_visual("Intet mærkbart ændret.")

    assert post["skipped"] is True
    assert post["reason"] == "kvittering"
    assert count() == foer, "arkivet vokser ikke af en kvittering"


def test_silence_lyt_arkiveres_ikke(isolated_runtime) -> None:
    """Et lyt der endte i `silence` er ikke et indtryk — der var intet at høre.

    Målt 28/9-2026: 24 sådanne poster, nyeste 26/9.
    """
    from core.services.sensory_archive import count, record_audio

    foer = count()
    post = record_audio(
        "Jeg lyttede til rummet. Klassifikation: silence "
        "(amplitude 0.0000±0.0000)."
    )

    assert post["skipped"] is True
    assert count() == foer


def test_rigtigt_indtryk_arkiveres_uændret(isolated_runtime) -> None:
    """Gaten må ikke fange det den skal beskytte."""
    from core.services.sensory_archive import record_visual

    tekst = "Skarpt eftermiddagslys gennem vinduet, støv der driver i strålen."
    post = record_visual(tekst)

    assert "skipped" not in post
    assert post["content"] == tekst
    assert post["id"]


def test_en_lyd_der_faktisk_var_noget_arkiveres(isolated_runtime) -> None:
    """Kun `silence` er en kvittering — musik er en sansning."""
    from core.services.sensory_archive import record_audio

    post = record_audio(
        "Jeg lyttede til rummet. Klassifikation: music "
        "(amplitude 0.0312±0.0081)."
    )

    assert "skipped" not in post
    assert post["id"]


def test_mode_always_gendanner_den_gamle_adfaerd(isolated_runtime, monkeypatch) -> None:
    """Indstillingen skal kunne skrues tilbage — ellers er den ikke en beslutning."""
    from core.services import sensory_archive

    monkeypatch.setattr(sensory_archive, "_kvittering_mode", lambda: "always")
    post = sensory_archive.record_visual("Intet mærkbart ændret.")

    assert "skipped" not in post
    assert post["id"]


def test_ukendt_mode_falder_til_skip(monkeypatch) -> None:
    """En slåfejl i indstillingen må ikke åbne hanen igen."""
    from core.services import sensory_archive

    class _Falsk:
        sensory_receipt_archive_mode = "altid-agtig-slåfejl"

    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: _Falsk())
    assert sensory_archive._kvittering_mode() == "skip"


def test_er_kvittering_fanger_begge_familier() -> None:
    from core.services.sensory_archive import er_kvittering

    assert er_kvittering("Intet mærkbart ændret.")
    assert er_kvittering("Ingen ændring.")
    assert er_kvittering(
        "Jeg lyttede til rummet. Klassifikation: silence (amplitude 0.0)."
    )
    assert er_kvittering("Lydbillede: silence")
    assert er_kvittering("")
    assert not er_kvittering("Rummet ligger stille med en lav summen fra køleskabet.")
    # Grænsen: en BESKRIVELSE der nævner 'silence' er et indtryk, ikke en
    # kvittering. Reglen skal være snæver nok til at lade den stå — målt
    # 28/9-2026: arkivet har flere af dem, og de beskriver noget.
    assert not er_kvittering(
        "En akustisk snapshot med kategori 'silence' betyder, at der er en "
        "meget lav lydintensitet i rummet lige nu."
    )


# ── Stillads-gaten (målt 5/10-2026) ─────────────────────────────────────────
#
# 50 af 2.775 poster var ikke sanseindtryk men modellens gengivelse af sin
# opgave eller en anmeldelse af sit eget svar. Familien er selvforstærkende:
# den forrige beskrivelse føres tilbage ind i prompten, så et ekko bliver til
# næste ekko. Målt 13/9 tre poster i træk, hvor den sidste citerer den forrige.


def test_prompt_ekko_gemmes_ikke_som_indtryk(isolated_runtime) -> None:
    """Det engelske spor er det største — modellen tænker højt på engelsk."""
    from core.services.sensory_archive import record_visual

    with pytest.raises(ValueError):
        record_visual(
            "We need answer in Danish only. Need describe changes since "
            "previous observation 18 min ago. We have only one image."
        )


def test_dansk_prompt_ekko_gemmes_ikke_som_indtryk(isolated_runtime) -> None:
    """Samme ekko på dansk: «Vi skal beskrive ændringer siden …»."""
    from core.services.sensory_archive import record_visual

    with pytest.raises(ValueError):
        record_visual(
            "Vi skal beskrive ændringer siden sidste observation (for 24 min "
            "siden). Sidste beskrivelse var «Intet mærkbart ændret.»"
        )


def test_2_person_prompt_ekko_fanges(isolated_runtime) -> None:
    """Modellen vendte instruktionen mod LÆSEREN (målt 7/10-2026).

    Familien «brugeren vil/beder/spørger» dækkede kun 3. person. Posten fra
    6/10 skrev «… siger 13:04, beder du om en beskrivelse af rummet som om,
    det er kl. 23:00» og gik fri — ekkoet ligger MIDT i en ægte sætning.
    """
    from core.services.sensory_archive import record_visual

    post = record_visual(
        "Billedet viser en stue i sort-hvide eller gråtoner, hvilket giver "
        "rummet en steril, næsten overvågningsagtig karakter. Selvom "
        "tidsstemplet øverst til venstre siger 13:04, beder du om en "
        "beskrivelse af rummet som om, det er kl. 23:00.\n\n"
        "**Lys og skygger:**\nRummet er præget af et fladt, diffust lys."
    )

    assert post["content"].startswith("Billedet viser en stue")
    assert "beder du om" not in post["content"]
    assert "23:00" not in post["content"]


def test_indtrykket_FORAN_ekkoet_bevares(isolated_runtime) -> None:
    """Grænsen: et ægte indtryk foran ekkoet må ikke ryge med.

    Målt 27/9-2026 begyndte en post med en rigtig beskrivelse og fortsatte med
    prompten ordret. At afvise hele posten ville tabe det første afsnit.
    """
    from core.services.sensory_archive import record_visual

    post = record_visual(
        "Billedet viser en stue med to personer. Den ene står foroverbøjet "
        "ved et sofabord. Udenfor er det mørkt.\n\n"
        "Spørgsmålet: Beskriv hvad der er ændret siden sidste observation. "
        "Svar kun på dansk."
    )

    assert post["content"].startswith("Billedet viser en stue")
    assert "Spørgsmålet" not in post["content"]
    assert "Svar kun" not in post["content"]


def test_halvt_led_efter_klip_afvises(isolated_runtime) -> None:
    """Et afklippet led er værre end ingenting — det ligner et indtryk.

    «Da billedet er helt sort, må jeg bruge» er over længdekravet og ville
    slippe igennem, hvis klippet ikke rykkede tilbage til en sætningsgrænse.
    """
    from core.services.sensory_archive import record_visual

    with pytest.raises(ValueError):
        record_visual(
            "Da billedet er helt sort, må jeg bruge min fantasi til at skabe "
            "en scene, hvor rummet er præget af mørke."
        )


def test_svar_preamble_stryges_men_indtrykket_beholdes(isolated_runtime) -> None:
    """Målt 5/10-2026: 19 poster indledte med «Her er en beskrivelse af …».

    Anmeldelsen er stillads; indtrykket bagefter er ægte. Derfor stryges den
    frem for at posten afvises.
    """
    from core.services.sensory_archive import record_visual

    post = record_visual(
        "Her er en præcis beskrivelse af rummet baseret på billedet:\n\n"
        "Rummet er badet i et intenst, monokromatisk rødt lys."
    )

    assert post["content"].startswith("Rummet er badet")
    assert "Her er en" not in post["content"]


def test_anmeldelse_MIDT_I_bevarer_begge_sider(isolated_runtime) -> None:
    """Har anmeldelsen indtryk på BEGGE sider, må ingen af dem tabe.

    Målt 21/8-2026: «Det er sent på aftenen … Her er en detaljeret
    beskrivelse: **Lys og skygger:** …». Både at klippe foran og bagved ville
    tabe et ægte afsnit.
    """
    from core.services.sensory_archive import record_visual

    post = record_visual(
        "Det er sent på aftenen, og rummet er præget af en dæmpet atmosfære. "
        "Her er en detaljeret beskrivelse:\n\n"
        "**Lys og skygger:** Belysningen er kunstig og uensartet."
    )

    assert "Det er sent på aftenen" in post["content"]
    assert "**Lys og skygger:**" in post["content"]
    assert "Her er en detaljeret" not in post["content"]


def test_her_er_ingen_er_et_indtryk(isolated_runtime) -> None:
    """Falsk-positiv-vagten. «Her er ingen mennesker» er en gyldig sansning.

    Uden den ville et værn mod stillads spise rigtige beskrivelser af tomme
    rum — og det er dyere end at overse et ekko.
    """
    from core.services.sensory_archive import record_visual

    tekst = "Her er ingen mennesker i rummet, kun et bord og en stol."
    assert record_visual(tekst)["content"] == tekst


def test_anmeldelse_uden_kolon_taeller_til_saetningsslut(isolated_runtime) -> None:
    """Anmeldelsen slutter ikke altid med kolon.

    Målt 20/9-2026: «Her er en sansebeskrivelse af rummet, baseret på det
    visuelle indtryk. Det føles som at træde ind i en stille tidslomme.» —
    uden sætningsslut-faldt tilbage ville hele den rige beskrivelse blive
    kasseret, fordi der ikke findes noget kolon at klippe ved.
    """
    from core.services.sensory_archive import record_visual

    post = record_visual(
        "Her er en sansebeskrivelse af rummet, baseret på det visuelle "
        "indtryk. Det føles som at træde ind i en stille, uafsluttet "
        "tidslomme."
    )

    assert post["content"].startswith("Det føles som at træde ind")
    assert "sansebeskrivelse" not in post["content"]


# ── Kolon-hullet og ræsonnement uden tags (målt 5/10-2026) ──────────────────
#
# Oprydningen 5/10 bragte arkivet til 2.744 poster — men der stod fem tilbage.
# De faldt i to huller, og begge blev målt mod hele arkivet før koden blev rørt.


def test_kolon_foran_anmeldelsen_fanges(isolated_runtime) -> None:
    """Kolon-hullet: `active_sensing` skriver «… Visuelt: Her er en beskrivelse».

    Den gamle grænse krævede `(?<=[.!?])`, så et kolon foran anmeldelsen slap
    igennem. Målt 5/10-2026: tre poster, den ældste 16/5 — de havde ligget der
    i månedsvis.
    """
    from core.services.sensory_archive import record_mixed

    post = record_mixed(
        "Jeg så og lyttede samtidig. Visuelt: Her er en beskrivelse af rummets "
        "stemning, set gennem sanserne, med fokus på hvad der føles anderledes "
        "og dragende lige nu:\n\n"
        "Det første, der rammer, er lyset. Det føles ikke længere bare som "
        "dagslys, men som en intens, næsten elektrisk energi."
    )

    assert "Her er en beskrivelse" not in post["content"]
    assert "Det første, der rammer, er lyset" in post["content"]


def test_kolon_alene_aabner_ikke_gaten(isolated_runtime) -> None:
    """Falsk-positiv-vagten for kolon-ændringen.

    Grænsen er udvidet til at tage kolon — men navneords-kravet står. Et kolon
    alene gør ikke «her er» til et signal, og en beskrivelse af et TOMT rum er
    stadig et indtryk.
    """
    from core.services.sensory_archive import record_visual

    tekst = "Bordet står tomt. Hylder: Her er ingen bøger tilbage, kun støv."
    assert record_visual(tekst)["content"] == tekst


def test_raesonnement_uden_tags_afvises(isolated_runtime) -> None:
    """Modellen skriver sin EGEN nummererede plan ind som indtryk.

    Uden `<think>`-tags, så `_uden_raa_tanke` ser ingenting. Målt 5/10-2026:
    to poster (1/10), den ene 4.567 tegn ren tankerække — «1. **Analyser
    brugerens anmodning:** … 6. **Endelig polering**».
    """
    from core.services.sensory_archive import record_visual

    with pytest.raises(ValueError):
        record_visual(
            "1.  **Analyser brugerens anmodning:**\n"
            "    *   **Kontekst:** Brugeren kigger på et billede af et rum.\n"
            "2.  **Analyser billedet (Visuel inspektion):**\n"
            "    *   **Belysning:** Meget kontrastfyldt."
        )


def test_wrapper_uden_indhold_afvises(isolated_runtime) -> None:
    """En rest der KUN er `active_sensing`s wrapper-lag er ikke et indtryk.

    «Jeg så og lyttede samtidig. Visuelt: 1.» er 39 tegn — over længdekravet —
    men der står intet bag laget. Målt 5/10-2026: post `931e8920` slap igennem
    som en sansning på præcis den form, efter at ekkoet var klippet væk.
    """
    from core.services.sensory_archive import record_mixed

    with pytest.raises(ValueError):
        record_mixed(
            "Jeg så og lyttede samtidig. Visuelt: 1.  **Analyser brugerens "
            "anmodning:**\n    *   **Kontekst:** Brugeren kigger på et billede."
        )


# ── klip ved sætningsgrænse (målt 6/10-2026) ─────────────────────────────


def test_klip_rykker_tilbage_til_saetningsgraense() -> None:
    """Klippet må ikke efterlade et halvt led.

    Målt 6/10-2026: 818 poster (30% af arkivet) var klippet midt i en sætning,
    fordi `_MAX_DESC_CHARS=300` skar blindt mens `num_predict: 150` tillod
    ~450-600 tegn. Et halvt led LIGNER et indtryk — det har længde, og «…»
    læses som stil — men det er et svar der aldrig blev færdigt.
    """
    from core.services.sensory_archive import klip_ved_saetningsgraense

    tekst = "Lyset falder skråt ind. Støvet driver i strålen. En stol står tom."
    hel = klip_ved_saetningsgraense(tekst, 40)
    assert hel == "Lyset falder skråt ind."
    assert hel.endswith(".")
    # Grænsen er den SIDSTE der ligger før pos — ikke den nærmeste efter.
    assert klip_ved_saetningsgraense(tekst, 60) == "Lyset falder skråt ind. Støvet driver i strålen."


def test_klip_uden_graense_giver_intet_indtryk() -> None:
    """Er der ingen sætningsgrænse før `pos`, findes der intet indtryk.

    At returnere det halve led ville være værre end ingenting — det ville blive
    arkiveret som en sansning. Tomt tvinger kalderen til at vælge.
    """
    from core.services.sensory_archive import klip_ved_saetningsgraense

    assert klip_ved_saetningsgraense("et langt led uden nogen afslutning", 20) == ""


def test_vision_vejen_klipper_ved_graense_ikke_blindt() -> None:
    """Værn: genindføres den blinde klipning som PRIMÆR vej, fejler denne.

    Kilden læses, fordi fejlen var netop at `text[:300] + "…"` stod i
    `_describe_via_ollama` — ikke i arkivet. Et kald til funktionen er ikke
    nok; den skal også BRUGES. Den blinde klipning må kun stå som fallback
    (når der slet ingen sætningsgrænse findes).
    """
    import inspect

    from core.services import visual_memory

    kilde = inspect.getsource(visual_memory._describe_via_ollama)
    assert "klip_ved_saetningsgraense(" in kilde, "vision-vejen klipper blindt igen"
    # Fallback-linjen skal være bundet til `hel if hel else` — står den frit,
    # er den blevet den primære vej igen.
    assert "hel if hel else" in kilde, "den blinde klipning er tilbage som primær vej"
