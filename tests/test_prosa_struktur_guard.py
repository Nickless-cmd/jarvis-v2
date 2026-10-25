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

    MUTATION: fjern fence-sporet i `_sektioner` → kommentaren bliver overskrift
    og den efterfølgende prosa måles under den → fejler.
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
