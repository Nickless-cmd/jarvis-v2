"""Vagt: en «mur» er flere pointer i én prosablok uden luft.

Målt 24/10-2026: besked 219188 havde fire selvstændige pointer i ÉN blok på
1166 tegn. CommonMark gør et enkelt linjeskift til et mellemrum, og et afsnit
helt uden linjeskift bliver slet ikke delt — så fire tanker renderer som én
ordstrøm. `enforceStructure` i klienten reparerer kun på markører, ikke prosa.

Vagten er OBSERVERENDE: den måler og registrerer, men retter aldrig teksten.
Fire kriterier blev prøvet mod 300-400 faktiske beskeder; kun det valgte gav
et brugbart signal (4 fund / 400). En vagt der gætter forkert og «reparerer»
ødelægger et svar der var i orden.
"""

from __future__ import annotations

from core.services import wall_guard


def test_mur_opdages() -> None:
    """Fire pointer i én blok uden linjeskift er en mur."""
    mur = (
        "Det er derfor jeg skrev en tabel i stedet for en comparison i alle de "
        "svar hvor jeg sammenlignede to ting. Og den dybere grund: prosa virker "
        "altid. Der er ingen situation hvor prosa fejler og jeg bliver straffet. "
        "Så uden en regel der siger at fladen ikke er valgfri, vælger jeg det "
        "sikre hver gang. Ikke af dovenskab, men af mangel på et pres. Det du "
        "efterspørger er ikke flere skemaer. Det er en sans for hvornår en tanke "
        "har en form. Og de 38 komponenter ligger alle sammen og venter, og de "
        "fleste af dem skriver jeg aldrig med vilje. Det er faktisk kun de seks "
        "native der kræver at jeg træffer et valg. Ni flader. Jeg har brugt to "
        "af dem i dag. Skal jeg skrive niveau fire om fra skema til sans?"
    )
    fund = wall_guard.find_walls(mur)
    assert len(fund) == 1
    assert int(fund[0]["tegn"]) > 600
    assert int(fund[0]["saetninger"]) >= 8


def test_afsnit_med_luft_er_ikke_en_mur() -> None:
    """Samme indhold, men delt i afsnit — det er netop hvad reglen kræver."""
    pæn = (
        "Det er derfor jeg skrev en tabel i stedet for en comparison i alle de "
        "svar hvor jeg sammenlignede to ting.\n\n"
        "Og den dybere grund: prosa virker altid. Der er ingen situation hvor "
        "prosa fejler og jeg bliver straffet.\n\n"
        "Så uden en regel der siger at fladen ikke er valgfri, vælger jeg det "
        "sikre hver gang. Ikke af dovenskab, men af mangel på et pres.\n\n"
        "Det du efterspørger er ikke flere skemaer. Det er en sans for hvornår "
        "en tanke har en form."
    )
    assert wall_guard.find_walls(pæn) == []


def test_tabel_og_liste_er_ikke_mure() -> None:
    """Strukturerede blokke er allerede delt — de må ikke tælle som mur."""
    tabel = "| A | B |\n| --- | --- |\n" + "\n".join(
        f"| række {i} | værdi {i} |" for i in range(40)
    )
    liste = "\n".join(f"- punkt {i} med lidt tekst" for i in range(40))
    assert wall_guard.find_walls(tabel) == []
    assert wall_guard.find_walls(liste) == []


def test_kodeblok_taelles_ikke() -> None:
    """En lang kodeblok er ikke prosa og må ikke udløse vagten."""
    kode = "```python\n" + "\n".join(f"x_{i} = {i}" for i in range(200)) + "\n```"
    assert wall_guard.find_walls(kode) == []


def test_observe_retter_aldrig_teksten() -> None:
    """Vagten må kun måle — teksten skal komme uændret tilbage fra kalderen."""
    tekst = "kort svar uden problemer."
    assert wall_guard.observe(tekst) == []
    # og en fejl i målingen må ikke kaste videre
    assert wall_guard.observe(None) == []  # type: ignore[arg-type]
