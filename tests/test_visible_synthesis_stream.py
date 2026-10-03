"""Den skrubbede syntese-strøm — Boy Scout-udskillelsen fra `visible_runs.py`.

Her kan skrubningen endelig testes **usmocket**: i `visible_runs` sidder den
midt i en 7.692-linjers async generator, og en test ville skulle rejse en hel
run-kontekst for at nå den. Det var grunden til at kun en kilde-vagt kunne se
den — og en kilde-vagt kan ikke se om markøren faktisk forsvinder.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.services import visible_synthesis_stream as vss


@dataclass
class _Delta:
    text: str


@dataclass
class _Facit:
    text: str


async def _stroem(*stykker):
    for s in stykker:
        yield s


async def _koer(*stykker) -> tuple[list[str], str]:
    """(viste stykker, facit)."""
    vist: list[str] = []
    facit = ""
    async for s in vss.skrubbet_syntese(_stroem(*stykker), delta_klasse=_Delta):
        if isinstance(s, vss.SyntesFacit):
            facit = s.tekst
        else:
            vist.append(s.tekst)
    return vist, facit


@pytest.mark.asyncio
async def test_ren_tekst_gaar_uaendret_igennem():
    vist, facit = await _koer(_Delta("Hej "), _Delta("Bjørn"), _Facit("Hej Bjørn"))
    assert "".join(vist) == "Hej Bjørn"
    assert facit == "Hej Bjørn"


@pytest.mark.asyncio
async def test_en_markoer_DELT_over_to_deltaer_naar_ikke_skaermen():
    """Hele grunden til at en strøm ikke kan skrubbes bagefter.

    `fjern_interne_markoerer` på den færdige tekst renser det persisterede —
    men brugeren har allerede set den halve markør. Det er det led en
    kilde-vagt ikke kan måle, og derfor denne test.
    """
    from core.services.visible_text_scrub import INTERNE_PRAEFIKSER
    # Husets EGNE praefikser, ikke et opdigtet navn. Foerste udgave af denne
    # test ledte efter `_MARKOERER`, som ikke findes — og saa blev den SKIPPET
    # i stilhed. Den vigtigste test i filen maalte ingenting, og en skip ser
    # ud som en bestaaet test i opsummeringen.
    assert INTERNE_PRAEFIKSER, "husets markoer-saet er tomt"
    for praefiks in INTERNE_PRAEFIKSER:
        note = f"{praefiks}noget-internt]"
        midt = len(note) // 2
        vist, facit = await _koer(_Delta("svar " + note[:midt]),
                                  _Delta(note[midt:] + " mere"),
                                  _Facit("svar  mere"))
        samlet = "".join(vist)
        assert praefiks not in samlet, \
            f"den delte markoer naaede skaermen: {samlet!r}"
        # Og svaret omkring den skal stadig vaere der — en skrubber der aad
        # hele stroemmen ville ogsaa bestaa assertionen ovenfor.
        assert "svar" in samlet and "mere" in samlet, \
            f"skrubberen aad svaret: {samlet!r}"


@pytest.mark.asyncio
async def test_HALEN_skylles_saa_sidste_stykke_ikke_forsvinder():
    """`StroemSkrubber` holder en hale tilbage indtil den kan afgøre om den er
    del af en markør. Uden `skyl()` ville det sidste stykke svar forsvinde —
    og det er en tavs fejl: svaret ser bare kortere ud."""
    vist, _ = await _koer(_Delta("det komplette svar"), _Facit("det komplette svar"))
    assert "".join(vist) == "det komplette svar"


@pytest.mark.asyncio
async def test_facit_kommer_PRAECIS_EN_gang_og_SIDST():
    stykker = []
    async for s in vss.skrubbet_syntese(
            _stroem(_Delta("a"), _Delta("b"), _Facit("ab")),
            delta_klasse=_Delta):
        stykker.append(s)
    facitter = [s for s in stykker if isinstance(s, vss.SyntesFacit)]
    assert len(facitter) == 1
    assert isinstance(stykker[-1], vss.SyntesFacit)


@pytest.mark.asyncio
async def test_en_AFBRUDT_stroem_skyller_stadig_halen():
    """Afbrydes strømmen (cutoff, en udbyder-fejl), ville det tilbageholdte
    stykke ellers forsvinde sammen med resten. `finally` er ikke pynt."""
    from core.services.visible_text_scrub import INTERNE_PRAEFIKSER
    # Afbrydelsen skal ske mens der ER noget tilbageholdt. Foerste udgave
    # sendte ren tekst, som slipper igennem med det samme — saa halen var tom,
    # og testen bestod uanset om `finally` var der. En mutation fra `finally`
    # til `if` blev IKKE fanget. Nu ender stroemmen paa en `[`, som
    # skrubberen MAA holde tilbage indtil den kan afgoere om det er en note.
    delvis = INTERNE_PRAEFIKSER[0][:6]

    async def _kaster():
        yield _Delta("det der naaede frem " + delvis)
        raise RuntimeError("udbyderen faldt")

    vist: list[str] = []
    with pytest.raises(RuntimeError):
        async for s in vss.skrubbet_syntese(_kaster(), delta_klasse=_Delta):
            if isinstance(s, vss.SyntesStykke):
                vist.append(s.tekst)
    samlet = "".join(vist)
    assert "det der naaede frem" in samlet, \
        "svaret forsvandt da stroemmen braekkede"
    assert delvis in samlet, \
        "den TILBAGEHOLDTE hale forsvandt — `finally` manglede"


@pytest.mark.asyncio
async def test_en_TOM_stroem_giver_et_tomt_facit_ikke_en_fejl():
    vist, facit = await _koer()
    assert vist == []
    assert facit == ""


@pytest.mark.asyncio
async def test_en_begivenhed_UDEN_text_felt_springes_over():
    """Skrald i strømmen må ikke kaste. En udbyder der sender en uventet form
    skal give et kortere svar, ikke et brækket run."""
    @dataclass
    class _Uden:
        noget_andet: str = "x"

    vist, facit = await _koer(_Delta("a"), _Uden(), _Facit("a"))
    assert "".join(vist) == "a"
    assert facit == "a"
