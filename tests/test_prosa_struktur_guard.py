"""Testene for den mekaniske prosa-struktur-kontrol.

Hver test er mutationsprøvet: den adfærd testen påstår at måle er slået fra, og
testen er set fejle. En grøn test der ikke kan slås fra måler ingenting.

Baggrund (målt 25/10-2026, Bjørn): reglen står i ``CHAT_FORMAT_CORE`` og blev
brudt i samme svar hvor den blev citeret. En model-baseret korrektur gav nul
effekt (commit ``4b473aecd``) — derfor måles det mekanisk.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.services import prosa_struktur_guard as g  # noqa: E402


# ── 1. Den case Bjørn klagede over ─────────────────────────────────────────

def test_prosa_opremsning_under_overskrift_flagges() -> None:
    """«en lang smøre til næste section» — tre led i én løbende linje.

    MUTATION: sæt MIN_LED = 99 → intet flag → fejler.
    """
    tekst = (
        "## 🩺 Hvad jeg fandt\n\n"
        "Jeg kiggede på rækkerne, og fejlen sad i guarden og ikke i rendereren, "
        "og den var allerede rettet i den kode der kørte, så det var ikke noget "
        "jeg kunne gøre noget ved den aften.\n"
    )
    fejl = g.fejl_i_prosa(tekst)
    assert len(fejl) == 1
    assert "Hvad jeg fandt" in fejl[0]
    assert "punktopstilling" in fejl[0]


def test_tre_led_uden_overskrift_flagges_ikke() -> None:
    """Uden overskrift er der ingen «section» at smøre til.

    MUTATION: fjern overskrift-kravet (behandl hele teksten som én sektion)
    → dette flagges → fejler.
    """
    tekst = (
        "Jeg kiggede på rækkerne, og fejlen sad i guarden og ikke i rendereren, "
        "og den var allerede rettet i den kode der kørte, så det var ikke noget "
        "jeg kunne gøre noget ved den aften.\n"
    )
    assert g.fejl_i_prosa(tekst) == []


# ── 2. Det modsatte: god struktur må ikke rammes ───────────────────────────

def test_punktopstilling_flagges_ikke() -> None:
    """Listen ER svaret på problemet — den må ikke flagges.

    MUTATION: fjern `_er_struktureret`-gaten → blokken måles som prosa → fejler.
    """
    tekst = (
        "## 🩺 Hvad jeg fandt\n\n"
        "Jeg kiggede på rækkerne, og fejlen sad i guarden og ikke i rendereren, "
        "og den var allerede rettet.\n\n"
        "- guarden målte det rigtige\n"
        "- rendereren gjorde det rigtige\n"
        "- koden var i drift\n"
    )
    assert g.fejl_i_prosa(tekst) == []


def test_kort_afsnit_flagges_ikke() -> None:
    """Et kort afsnit kan ikke rumme tre reelle led.

    MUTATION: sæt MIN_AFSNIT_TEGN = 0 → det korte afsnit måles → fejler.
    """
    tekst = "## Titel\n\nA, B og C.\n"
    assert g.fejl_i_prosa(tekst) == []


def test_kodeblok_med_kommentar_er_ikke_en_sektion() -> None:
    """`# kommentar` i et bash-eksempel er ikke en overskrift i svaret.

    MUTATION: fjern fence-sporet i `_blokke_med_overskrift` → kommentaren
    bliver overskrift og den efterfølgende prosa måles under den → fejler.
    """
    tekst = (
        "## Koden\n\n"
        "```bash\n"
        "# sæt DB_PATH til prod\n"
        "export DB_PATH=/home/bs/.jarvis-v2/state/jarvis.db\n"
        "```\n\n"
        "Det virker fordi, og det er meningen, og det er testet grundigt nok "
        "til at jeg tør sige det højt uden forbehold her.\n"
    )
    assert g.fejl_i_prosa(tekst) == []


def test_tabel_og_citat_flagges_ikke() -> None:
    """Strukturerede blokke er allerede struktur.

    MUTATION: fjern `_TABEL_RE`/`_CITAT_RE` fra `_er_struktureret` → fejler.
    """
    tekst = (
        "## Tal\n\n"
        "| form | før | nu |\n|---|---|---|\n| bar | 1 | 2 |\n| fenced | 3 | 4 |\n\n"
        "> citeret tekst, med komma, og med mere, og endnu et led her i citatet "
        "som ellers ville blive målt som prosa hvis citatet ikke blev sprunget over.\n"
    )
    assert g.fejl_i_prosa(tekst) == []


# ── 3. Talord-vejen: «tre ting» uden liste ────────────────────────────────

def test_talt_antal_uden_liste_flagges() -> None:
    """Når svaret selv siger «tre ting», skal de tre ting kunne skimmes.

    MUTATION: fjern `_TALORD_RE`-grenen → intet flag → fejler.
    """
    tekst = (
        "## 🩺 Fundet\n\n"
        "Der var tre ting galt i den kode der kørte den aften, og de hang sammen "
        "på en måde som gjorde at den ene skjulte den anden for os.\n"
    )
    fejl = g.fejl_i_prosa(tekst)
    assert len(fejl) == 1
    assert "Fundet" in fejl[0]


def test_talt_antal_med_liste_flagges_ikke() -> None:
    tekst = (
        "## 🩺 Fundet\n\n"
        "Der var tre ting galt i den kode der kørte den aften.\n\n"
        "- guarden\n- rendereren\n- kørslen\n"
    )
    assert g.fejl_i_prosa(tekst) == []


# ── 4. Måleapparatet selv ────────────────────────────────────────────────

def test_antal_led_taeller_og_forbindelsen() -> None:
    """«A, B og C» er tre led, ikke to.

    MUTATION: fjern `_OG_RE`-tillægget → 2 → fejler.
    """
    assert g._antal_led("A, B og C") == 3
    assert g._antal_led("A, B, C og D") == 4
    assert g._antal_led("én ting uden komma") == 0


def test_fed_overskrift_taelles_som_sektion() -> None:
    """`**Fed linje**` alene er en overskrift i den form svarene bruger.

    MUTATION: fjern `_FED_OVERSKRIFT_RE` → intet flag → fejler.
    """
    tekst = (
        "**Hvad jeg fandt**\n\n"
        "Jeg kiggede på rækkerne, og fejlen sad i guarden og ikke i rendereren, "
        "og den var allerede rettet i den kode der kørte, så det var ikke noget "
        "jeg kunne gøre noget ved den aften.\n"
    )
    fejl = g.fejl_i_prosa(tekst)
    assert len(fejl) == 1
    assert "Hvad jeg fandt" in fejl[0]


def test_tom_tekst_giver_ingen_fejl() -> None:
    assert g.fejl_i_prosa("") == []
    assert g.fejl_i_prosa("bare en linje uden struktur") == []


# ── 5. De tre former Bjørn pegede på 2/11-2026 ────────────────────────────
#
# «det sværeste er faktisk at få dig til at formatere din tekst beder.. altså
# i chat mode.. prøv og læg mærke til under den sidste kode boks». Han pegede
# på tre ting i samme svar: fed tekst i overskriftens plads, fem tal i to
# sætninger, og en kodeblok der indeholdt commits som løbende prosa.


def test_pseudo_overskrift_flagges() -> None:
    """Fed tekst der indleder et afsnit og fortsætter som brødtekst.

    MUTATION: fjern `_pseudo_overskrift`-gaten → intet flag → fejler.
    """
    tekst = (
        "## Hvad dagen viser\n\n"
        "**Så et hul på to timer.** 17:00 til 19:16 blev der ikke committet "
        "noget — det var mens vi læste prompt-filerne igennem sammen.\n"
    )
    fejl = g.fejl_i_prosa(tekst)
    assert len(fejl) == 1
    assert "pseudo-overskrift" in fejl[0]
    assert "Så et hul på to timer" in fejl[0]


def test_fedt_enkeltord_er_ikke_en_pseudo_overskrift() -> None:
    """«**Nej.** Det holder ikke.» er fremhævning, ikke en overskrift.

    MUTATION: fjern `len(fed.split()) < 3`-gaten → flagges → fejler.
    """
    tekst = (
        "## Svar\n\n"
        "**Nej.** Det holder ikke, og det er der en grund til som jeg kan vise "
        "dig hvis du vil se den.\n"
    )
    assert g.fejl_i_prosa(tekst) == []


def test_talmur_flagges() -> None:
    """Fem tal i én sætning uden liste eller tabel at aflæse dem i.

    MUTATION: sæt MIN_TAL = 99 → intet flag → fejler.
    """
    tekst = (
        "## Status\n\n"
        "Systemet kører på 8 kerner med 32 GB hukommelse fordelt over 4 "
        "containere hvor den største bruger 12 GB og den mindste kun 2 GB mens "
        "resten står stille.\n"
    )
    fejl = g.fejl_i_prosa(tekst)
    assert len(fejl) == 1
    assert "talmur" in fejl[0]


def test_klokkeslaet_er_ikke_en_talmur() -> None:
    """«kl. 12:38:27» er ét klokkeslæt, ikke tre tal.

    MUTATION: fjern `_TIDSSTEMPEL_RE`-oprydningen → de to tidsstempler tæller
    som seks tal → afsnittet når MIN_TAL → fejler.
    """
    tekst = (
        "## Kørsel\n\n"
        "Kørslen startede kl. 12:38:27 og sluttede kl. 12:40:50 uden en "
        "enkelt fejl undervejs i det forløb som du bad mig om at følge helt "
        "til dørs her.\n"
    )
    assert g.fejl_i_prosa(tekst) == []


def test_kodeblok_uden_kode_flagges() -> None:
    """En fence der bærer prosa er en terminal-attrap, ikke kode.

    MUTATION: fjern `_indeholder_kode`-gaten → intet flag → fejler.
    """
    tekst = (
        "## Commits\n\n"
        "```\n"
        "16:01 8d862890d fix(nudge): auto-sessioner fik 58 af 112 injektioner\n"
        "16:03 27ff5569b feat(desk): godkendelses-kortet følger tema og accent\n"
        "```\n"
    )
    fejl = g.fejl_i_prosa(tekst)
    assert len(fejl) == 1
    assert "kodeblok" in fejl[0]


def test_rigtig_kodeblok_flagges_ikke() -> None:
    """Ægte kode må ikke «rettes» til prosa.

    MUTATION: fjern `_STI_RE`/`_KODE_TEGN_RE`/`_KODE_ORD_RE` fra
    `_indeholder_kode` → bash-eksemplet flagges → fejler.
    """
    tekst = (
        "## Koden\n\n"
        "```bash\n"
        "export DB_PATH=/home/bs/.jarvis-v2/state/jarvis.db\n"
        'echo "$DB_PATH"\n'
        "```\n"
    )
    assert g.fejl_i_prosa(tekst) == []


def test_pseudo_overskrift_uden_overskrift_over_sig_flagges() -> None:
    """Reglen må ikke være død i det tilfælde den findes for.

    Målt 2/11-2026 på mit eget svar: det havde tre pseudo-overskrifter og nul
    `#`-overskrifter, fordi den fede tekst VAR overskrifterne. Da regel 1–3
    blev målt inde i `_sektioner`, fandtes der ingen sektioner — og guarden
    fandt kun kodeblokken. Det er den vigtigste test i denne fil.

    MUTATION: mål blokkene med `_sektioner` i stedet for
    `_blokke_med_overskrift` → intet fund → fejler.
    """
    tekst = (
        "**Så et hul på to timer.** 17:00 til 19:16 blev der ikke committet "
        "noget — det var mens vi læste prompt-filerne igennem sammen.\n"
    )
    fejl = g.fejl_i_prosa(tekst)
    assert len(fejl) == 1
    assert "pseudo-overskrift" in fejl[0]


def test_etiket_paa_to_ord_med_kolon_flagges() -> None:
    """«**Aften: chat-kontrakten** (19:16–19:58)» er en etiket, ikke prosa.

    Dansk giver et helt emne på to ord, så et tre-ords-krav slap den igennem.

    MUTATION: fjern `and ":" not in fed` → intet fund → fejler.
    """
    tekst = (
        "**Aften: chat-kontrakten** (19:16–19:58, alle codex) og derefter "
        "blev der ikke committet mere den aften.\n"
    )
    fejl = g.fejl_i_prosa(tekst)
    assert len(fejl) == 1
    assert "pseudo-overskrift" in fejl[0]


def test_kort_pseudo_overskrift_flagges() -> None:
    """En pseudo-overskrift er kort af natur — længde-gaten må ikke dræbe den.

    MUTATION: flyt `MIN_AFSNIT_TEGN`-gaten op FØR pseudo-reglen → afsnittet på
    117 tegn filtreres væk → fejler.
    """
    tekst = (
        "**Så et hul på to timer.** 17:00 til 19:16 blev der ikke committet "
        "noget — det var mens vi læste prompt-filerne.\n"
    )
    assert len(tekst.split("\n")[0]) < g.MIN_AFSNIT_TEGN
    assert g.fejl_i_prosa(tekst) != []


def test_en_blok_giver_hoejst_et_fund() -> None:
    """Fakta-tungt afsnit må ikke flagges både som opremsning og talmur.

    MUTATION: fjern `continue` efter opremsnings-grenen → to fund for samme
    tekst → fejler.
    """
    tekst = (
        "## Dagen\n\n"
        "Doc-regenereringen står for 80 af de rørte filer og er ikke arbejde. "
        "Det egentlige ligger i 31 filer under core/services og 20 tests, og "
        "fordelingen 11/7 er tæt på de 33/16 fra september.\n"
    )
    fund = g.find_prosa_punkter(tekst)
    assert len(fund) == 1, f"forventede ét fund, fik {len(fund)}"
    assert fund[0].slags == "opremsning"

