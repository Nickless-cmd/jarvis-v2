"""Vagt om det brugeren ser.

Grundsandheden er ikke opdigtet: `ÆGTE` er ordret den tekst der stod på Bjørns
telefon 12/9-2026 22:49, hentet fra `chat_messages` på runtime.
"""
import pytest

from core.services.visible_text_scrub import (
    MAKS_NOTE, StroemSkrubber, fjern_interne_markoerer,
)

ÆGTE = (
    "tests/services/ er tung — den ramte 115s-grænsen. Jeg kører den i "
    "baggrunden og poller.\n\n"
    "[decision-signal: interceptor (verification: [interceptor:verification] "
    "R2 blød surface — uverificerede mutationer)]\n\n"
    "[decision-signal: interceptor (verification: [interceptor:verification] "
    "R2.5 hård blok — verifikation påkrævet)]\n\n"
    "Kører — 37% efter 100 s."
)


def _stroem(tekst: str, n: int) -> str:
    s = StroemSkrubber()
    ud = "".join(s.foed(tekst[i:i + n]) for i in range(0, len(tekst), n))
    return ud + s.skyl()


def test_aegte_besked_mister_begge_noter_og_beholder_prosaen():
    ud = fjern_interne_markoerer(ÆGTE)
    assert "decision-signal" not in ud
    assert "interceptor" not in ud
    assert ud.startswith("tests/services/ er tung")
    assert ud.endswith("Kører — 37% efter 100 s.")
    # Afsnitsbruddet mellem de to stykker prosa skal overleve — ellers klistrer
    # svaret sammen der hvor noten stod.
    assert "poller.\n\nKører" in ud


def test_indre_klamme_aeder_ikke_halvdelen_af_noten():
    """Et ikke-grådigt regex stopper ved `[interceptor:verification]`s `]` og
    efterlader resten af noten. Det er DEN fejl klammetællingen findes for."""
    ud = fjern_interne_markoerer(ÆGTE)
    assert "R2 blød surface" not in ud
    assert "uverificerede mutationer" not in ud
    assert ")]" not in ud


@pytest.mark.parametrize("n", range(1, 46))
def test_ingen_markoer_slipper_ud_uanset_hvor_stroemmen_knaekker(n):
    ud = _stroem(ÆGTE, n)
    assert "decision-signal" not in ud
    assert "interceptor" not in ud
    assert "R2 blød" not in ud


@pytest.mark.parametrize("n", range(1, 46))
def test_stroemmen_taber_ikke_et_eneste_tegn_prosa(n):
    """Vagten må aldrig kunne betale for sin renhed med brugerens svar."""
    ud = _stroem(ÆGTE, n)
    for stump in ("tests/services/ er tung", "baggrunden og poller.",
                  "Kører — 37% efter 100 s."):
        assert stump in ud, f"chunk={n} tabte {stump!r}"


@pytest.mark.parametrize("tekst", [
    "Se [foo.ts](src/foo.ts) og [bar](x).",
    "En liste med [kantede] klammer:\n- et\n- to",
    "Matrix-notation a[i][j] og en [TODO] i koden.",
    "",
])
def test_almindelig_tekst_roeres_ikke(tekst):
    assert fjern_interne_markoerer(tekst) == tekst.strip()
    assert _stroem(tekst, 3) == tekst.strip()


def test_uafsluttet_note_i_halen_er_ogsaa_stoej():
    """Klippes svaret midt i en note, er en halv note lige så meget støj."""
    assert fjern_interne_markoerer("Svar.\n\n[decision-signal: klippet") == "Svar."


def test_note_alene_giver_tom_streng_ikke_tomrum():
    assert fjern_interne_markoerer("[decision-signal: a (b: c)]") == ""


def test_lang_uafsluttet_klamme_spiser_ikke_resten_af_svaret():
    """Holder vagten på ubestemt tid, kan én skæv «[» tie hele svaret ihjel.
    Derfor er tilbageholdelsen loftet — indholdet vejer tungere end formen."""
    hale = "x" * (MAKS_NOTE + 200)
    ud = fjern_interne_markoerer(f"Svar.\n\n[decision-signal: {hale}")
    assert ud.startswith("Svar.")
    s = StroemSkrubber()
    levende = s.foed(f"Svar.\n\n[decision-signal: {hale}") + s.skyl()
    assert "decision-signal" not in levende
    # Indholdet SLIPPES — kun markoer-ordet falder vaek. Foerste udgave af
    # denne test sagde det samme i en kommentar, men maalte kun at halen var
    # blevet kortere; den var groen mens koden smed alle 800 tegn vaek.
    assert hale in levende, "halen blev droppet i stedet for frigivet"


@pytest.mark.parametrize("n", range(1, 46))
def test_noten_efterlader_ikke_et_hul_i_svaret(n):
    """Den bærende invariant: tomrum sendes aldrig ud før vi ved hvad der
    følger. Uden den slipper «…poller.\\n\\n» af sted FØR noten dukker op, og
    de to blanke linjer omkring noten kan ikke længere smelte sammen — så står
    der et hul på fire linjer midt i svaret hvor gaten talte.

    Mutations-prøven fandt dette hul: `skaering = len(krop)` (altså ingen
    tilbageholdelse) lod alle 99 andre tests blive grønne.
    """
    assert "\n\n\n" not in _stroem(ÆGTE, n), f"chunk={n} efterlod et hul"


def test_vagten_er_faktisk_koblet_paa_kørslen():
    """Det hyppigste svigt i huset er en korrekt funktion ingen kalder.

    Tre steder skal bruge den, og de er ikke udskiftelige: strømmen (det
    brugeren ser LIVE), de to syntetiserede redninger (som bygges AF
    exchange-teksten og derfor bærer noterne videst), og tragten før persist
    (det der står i tråden bagefter). Falder ét af dem ud, er lækagen tilbage
    i netop den ene tilstand ingen tænker på.
    """
    import pathlib
    kilde = pathlib.Path("core/services/visible_runs.py").read_text()
    assert "from core.services import visible_text_scrub as _vts" in kilde
    # Modul-niveau, ikke inde i en gren: en import der kun er bundet HVIS
    # grenen kørte, er den fælde der brækkede .py-skrivning i syv uger.
    assert kilde.index("import visible_text_scrub") < kilde.index("_skrub = _vts.StroemSkrubber()")
    assert "_ren = _skrub.foed(_a_item.delta)" in kilde
    assert "_rest = _skrub.skyl()" in kilde, "halen ville stå tilbage over en værktøjskørsel"
    assert kilde.count("_vts.fjern_interne_markoerer(") == 3
    assert "followup_text = _vts.fjern_interne_markoerer(followup_text)" in kilde
