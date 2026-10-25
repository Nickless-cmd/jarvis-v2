"""Tests for bruger-hensyn: handlingsrelevante hensyn med to levetider.

Hver adfærd er mutationsprøvet — den regel testen påstår at måle er slået fra,
og testen er set fejle. Mutationen står i kommentaren over den enkelte test.

BEVISKRAVET (fra opgaven): mekanismen prøves mod mindst to faktiske linjer fra
Bjørns USER.md — én der bør give et hensyn, og én der ikke bør.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

import core.services.user_hensyn as u

# ── Bjørns faktiske linjer (USER.md) ────────────────────────────────────────

# `## Durable Preferences` — dette ER et hensyn: en undladelse der kan efterleves.
HENSYN_LINJE = "Ikke fortæl mig hvornår jeg skal sove — jeg bestemmer selv"

# `## Kerne` — dette er en FAKTA om et navn, ikke et hensyn, selv om den har «ikke».
FAKTA_LINJE = "**Name:** Bjørn (ikke ChiefOne, Chef, Boss — ChiefOne er et maskinnavn)"

# Ren biografisk fakta uden handlingsmarkør.
FAKTA_LINJE_2 = "Bor i Svendborg, Denmark"


def _stub(regel: str, graense: str, *, svar: str | None = None):
    """En model der svarer i det format ``_formuler`` forventer."""

    def _llm(_prompt: str) -> str:
        if svar is not None:
            return svar
        return f"REGEL: {regel}\nGRAENSE: {graense}"

    return _llm


@pytest.fixture
def butik(monkeypatch):
    """In-memory state — testen må ikke røre den ægte state-fil."""
    hensyn: list[u.Hensyn] = []
    behandlet: set[str] = set()

    def _load():
        return [u.Hensyn.from_dict(h.to_dict()) for h in hensyn]

    def _save(items):
        hensyn.clear()
        hensyn.extend(u.Hensyn.from_dict(h.to_dict()) for h in items)

    def _gem(hashes):
        behandlet.clear()
        behandlet.update(hashes)

    monkeypatch.setattr(u, "_load", _load)
    monkeypatch.setattr(u, "_save", _save)
    monkeypatch.setattr(u, "_behandlede", lambda: set(behandlet))
    monkeypatch.setattr(u, "_gem_behandlede", _gem)
    return hensyn


# ── 1. Beviskravet: to faktiske tilfælde ────────────────────────────────────


def test_hensynslinje_giver_et_hensyn() -> None:
    """«Ikke fortæl mig hvornår jeg skal sove» er en undladelse → et hensyn."""
    assert u.kandidat_kategori(HENSYN_LINJE) == "tid"


def test_navnelinje_giver_intet_hensyn() -> None:
    """Navnelinjen har «ikke», men handler om hvad han hedder — ikke om et hensyn.

    Målt ved mutation 25/10-2026: denne test fældes IKKE af at fjerne
    handlingsmarkør-kravet, fordi navnelinjen heller ikke har et kategorisignal.
    Den måler derfor kategorisignal-kravet — se
    ``test_fakta_med_kategorisignal_men_uden_handling`` for det andet værn.
    """
    assert u.kandidat_kategori(FAKTA_LINJE) is None


def test_fakta_med_kategorisignal_men_uden_handling() -> None:
    """MUTATION: fjern `if not _HANDLING_RE.search(tekst): return None` → «Han
    spiser kød hver dag» bliver kandidat og modellen bliver spurgt om et hensyn
    der ikke findes.

    Linjen har et stærkt kost-signal, men den er en vaneudsagn — ikke en
    undladelse. Det er netop den falske positiv der er dyrere end en falsk
    negativ, og den er kun fanget af handlingsmarkøren.
    """
    assert u.kandidat_kategori("Han spiser kød hver dag og kan godt lide mad") is None


def test_biografisk_fakta_giver_intet_hensyn() -> None:
    """MUTATION: sænk _MIN_KANDIDAT_TEGN til 3 → «Bor i Svendborg» slipper gennem
    hvis den også har et signal; her fælder længde+signal-kravet den."""
    assert u.kandidat_kategori(FAKTA_LINJE_2) is None


def test_begge_retninger_i_samme_udledning(butik) -> None:
    """Mekanismen udleder ét hensyn og forkaster de to fakta-linjer."""
    llm = _stub("undlad at foreslå at han skal sove", "medmindre han selv spørger om træthed")
    ud = u.udled([HENSYN_LINJE, FAKTA_LINJE, FAKTA_LINJE_2], kilde="USER.md", llm=llm)
    assert len(ud) == 1
    assert ud[0].kategori == "tid"
    assert "sove" in ud[0].regel


# ── 2. Grænsen er obligatorisk ──────────────────────────────────────────────


def test_kandidat_uden_graense_forkastes(butik) -> None:
    """MUTATION: fjern `len(graense) < 8`-gaten → et absolut forbud slipper ind.

    Et forbud uden udgang er GPT-fejlen (brain-note brn_01M5J42TEHFNTF6YGG79S9XBMZ).
    """
    ud = u.udled([HENSYN_LINJE], kilde="t", llm=_stub("undlad at foreslå søvn", "altid"))
    assert ud == []


def test_svar_uden_format_forkastes(butik) -> None:
    ud = u.udled([HENSYN_LINJE], kilde="t", llm=_stub("x", "y", svar="det ved jeg ikke"))
    assert ud == []


def test_ingen_svar_forkastes(butik) -> None:
    """MUTATION: fjern «INGEN»-gaten → modellens afvisning bliver et hensyn."""
    ud = u.udled([HENSYN_LINJE], kilde="t", llm=_stub("x", "y", svar="INGEN"))
    assert ud == []


def test_modelfejl_forkaster_frem_for_at_gaette(butik) -> None:
    """En fejlende model må ikke opfinde et hensyn. Falsk negativ er billigere."""

    def _braekker(_p: str) -> str:
        raise RuntimeError("netværk nede")

    assert u.udled([HENSYN_LINJE], kilde="t", llm=_braekker) == []


# ── 3. Levetid: standard er situationel, forfremmelse kræver bevis ──────────


def test_standard_er_situationel(butik) -> None:
    """MUTATION: sæt `levetid=VARIG` som default → et dagsforms-hensyn bliver livsregel."""
    ud = u.udled([HENSYN_LINJE], kilde="t", llm=_stub("undlad at foreslå søvn", "medmindre han spørger"))
    assert ud[0].levetid == u.SITUATIONEL


def test_gentagelse_forfremmer_til_varig() -> None:
    """MUTATION: fjern `forekomster >= FORFREMNING_GENTAGELSER` → bliver aldrig varig."""
    h = u.Hensyn(
        hensyn_id="h-1", kategori="tid",
        regel="undlad at foreslå søvn", graense="medmindre han spørger",
        oprettet=datetime.now(UTC).isoformat(),
    )
    assert u.forfrem(h).levetid == u.SITUATIONEL
    h.forekomster = u.FORFREMNING_GENTAGELSER
    assert u.forfrem(h).levetid == u.VARIG


def test_eksplicit_varig_markor_forfremmer() -> None:
    """«altid» i reglen er et udsagn om varighed, ikke et gæt."""
    h = u.Hensyn(
        hensyn_id="h-2", kategori="sprog",
        regel="brug altid dansk", graense="medmindre han skriver engelsk",
        oprettet=datetime.now(UTC).isoformat(),
    )
    assert u.forfrem(h).levetid == u.VARIG


def test_varig_falmer_ikke() -> None:
    """MUTATION: lad vaegt() regne på alle → et varigt hensyn udløber efter 28 dage."""
    h = u.Hensyn(
        hensyn_id="h-3", kategori="kost", regel="foreslå ikke kød",
        graense="medmindre han spørger om mad", levetid=u.VARIG,
        oprettet=(datetime.now(UTC) - timedelta(days=365)).isoformat(),
    )
    assert u.vaegt(h) == 1.0
    assert u.opdater(h).status == u.AKTIV


# ── 4. Situationel levetid falmer af sig selv ───────────────────────────────


@pytest.mark.parametrize(
    ("dage", "forventet_status"),
    [(0, u.AKTIV), (14, u.AKTIV), (27, u.AKTIV), (28, u.UDLOEBET), (60, u.UDLOEBET)],
)
def test_situationel_falmer_ved_halveringstid(dage: int, forventet_status: str) -> None:
    """MUTATION: sæt HALVERINGSTID_DAGE=9999 → 28 dage bliver aldrig udløbet."""
    h = u.Hensyn(
        hensyn_id="h-4", kategori="tid", regel="undlad at foreslå søvn",
        graense="medmindre han spørger",
        oprettet=(datetime.now(UTC) - timedelta(days=dage)).isoformat(),
    )
    assert u.opdater(h).status == forventet_status


# ── 5. Udgangen: støj fjernes ───────────────────────────────────────────────


def test_mange_injektioner_uden_effekt_bliver_stoej() -> None:
    """MUTATION: fjern støj-grenen i opdater() → hensynet bliver i prompten for evigt.

    Uden denne udgang vokser sektionen til en væg — den «samme besked hver gang»
    Bjørn kalder tom.
    """
    h = u.Hensyn(
        hensyn_id="h-5", kategori="tid", regel="undlad at foreslå søvn",
        graense="medmindre han spørger",
        oprettet=datetime.now(UTC).isoformat(),
        injiceret=u.N_TURE_UDEN_EFFEKT,
    )
    assert u.opdater(h).status == u.STOEJ


def test_effekt_holder_hensynet_i_live() -> None:
    """Ét ramt svar er bevis for relevans — så er det ikke støj."""
    h = u.Hensyn(
        hensyn_id="h-6", kategori="tid", regel="undlad at foreslå søvn",
        graense="medmindre han spørger",
        oprettet=datetime.now(UTC).isoformat(),
        injiceret=u.N_TURE_UDEN_EFFEKT, ramte=1,
    )
    assert u.opdater(h).status == u.AKTIV


def test_marker_ramte_nulstiller_stoej_taellingen() -> None:
    h = u.Hensyn(hensyn_id="h-7", kategori="tid", regel="x" * 10, graense="y" * 10, injiceret=39)
    ud = u.marker_ramte([h], "h-7")
    assert ud[0].ramte == 1 and ud[0].injiceret == 0


def test_stoej_forlader_prompten(butik) -> None:
    """MUTATION: lad aktive() beholde STOEJ → sektionen viser et dødt hensyn."""
    butik.append(
        u.Hensyn(
            hensyn_id="h-8", kategori="tid", regel="undlad at foreslå søvn",
            graense="medmindre han spørger",
            oprettet=datetime.now(UTC).isoformat(),
            injiceret=u.N_TURE_UDEN_EFFEKT,
        )
    )
    assert u.aktive(butik) == []
    assert u.byg_hensyn_sektion(taeller_injektion=False) == ""


# ── 6. Sektionen ────────────────────────────────────────────────────────────


def test_sektion_tom_naar_intet_er_udledt(butik) -> None:
    assert u.byg_hensyn_sektion(taeller_injektion=False) == ""


def test_sektion_baerer_regel_og_graense(butik) -> None:
    """MUTATION: fjern « — {graense}» → forbuddet står uden udgang i prompten."""
    butik.append(
        u.Hensyn(
            hensyn_id="h-9", kategori="kost",
            regel="foreslå ikke kød", graense="medmindre han selv spørger om madvaner",
            levetid=u.VARIG, oprettet=datetime.now(UTC).isoformat(),
        )
    )
    tekst = u.byg_hensyn_sektion(taeller_injektion=False)
    assert "foreslå ikke kød" in tekst
    assert "medmindre han selv spørger om madvaner" in tekst


def test_varige_staar_foerst(butik) -> None:
    nu = datetime.now(UTC)
    butik.append(u.Hensyn(hensyn_id="s", kategori="tid", regel="situationel regel",
                          graense="grænse her", oprettet=nu.isoformat()))
    butik.append(u.Hensyn(hensyn_id="v", kategori="kost", regel="varig regel",
                          graense="grænse her", levetid=u.VARIG, oprettet=nu.isoformat()))
    tekst = u.byg_hensyn_sektion(taeller_injektion=False)
    assert tekst.index("varig regel") < tekst.index("situationel regel")


def test_sektion_respekterer_tegnbudgettet(butik) -> None:
    nu = datetime.now(UTC)
    for i in range(20):
        butik.append(
            u.Hensyn(
                hensyn_id=f"h-{i}", kategori="kost",
                regel=f"regel nummer {i} som er ret lang i sin form",
                graense="grænse som også er lang nok til at tælle",
                levetid=u.VARIG, oprettet=nu.isoformat(),
            )
        )
    tekst = u.byg_hensyn_sektion(max_chars=200, taeller_injektion=False)
    assert len(tekst) < 400  # overskrift + budget, ikke 20 linjer


def test_injektion_taelles(butik) -> None:
    butik.append(
        u.Hensyn(hensyn_id="h-10", kategori="kost", regel="foreslå ikke kød",
                 graense="medmindre han spørger", levetid=u.VARIG,
                 oprettet=datetime.now(UTC).isoformat())
    )
    u.byg_hensyn_sektion(taeller_injektion=True)
    u.byg_hensyn_sektion(taeller_injektion=True)
    assert butik[0].injiceret == 2


# ── 7. Baggrundskørslen: dedup og kategorisering ────────────────────────────


def test_anden_koersel_koster_nul_modelkald(butik, monkeypatch) -> None:
    """MUTATION: fjern `if noegle_linje in behandlede: continue` → 60 kald hvert
    10. minut for evigt, også for de linjer der svarede INGEN."""
    kald: list[int] = []

    def _llm(_p: str) -> str:
        kald.append(1)
        return "INGEN"

    linjer = [f"Linje nummer {i} med ikke og mad og kød" for i in range(10)]
    u.udled(linjer, kilde="t", llm=_llm)
    foerste = len(kald)
    u.udled(linjer, kilde="t", llm=_llm)
    assert foerste > 0
    assert len(kald) == foerste, "anden kørsel spurgte modellen igen"


def test_kategori_kommer_fra_reglen_ikke_kildelinjen(butik) -> None:
    """MUTATION: brug `_kilde_kategori` direkte → en kød-regel bliver «sprog»,
    fordi kildelinjen handlede om formulering (målt 25/10-2026)."""
    kilde_linje = "Brug ikke den form for formulering, og nævn ikke ordet"
    llm = _stub("foreslå ikke kød", "medmindre han selv spørger om madvaner")
    ud = u.udled([kilde_linje], kilde="t", llm=llm)
    assert ud and ud[0].kategori == "kost"


def test_gentaget_hensyn_taelles_ikke_som_nyt(butik) -> None:
    llm = _stub("foreslå ikke kød", "medmindre han selv spørger om madvaner")
    foerste = u.udled([HENSYN_LINJE], kilde="t", llm=llm)
    # Ny kildelinje, samme regel — dedup er på linje-hash, så modellen spørges igen.
    anden = u.udled(["Spiser ikke kød, så foreslå ikke kød til middag"], kilde="t", llm=llm,
                    eksisterende=foerste)
    assert len(anden) == len(foerste)
    assert anden[0].forekomster >= 2


# ── 8. Brud-detektoren ──────────────────────────────────────────────────────


def test_brud_kraever_foreslaaende_kontekst() -> None:
    """MUTATION: fjern `_FORESLAA_RE`-kravet → enhver omtale af kød er et brud.

    Et falsk brud er lige så skadeligt som et falsk hensyn: det holder et
    ubrugeligt hensyn i live ved at påstå at det blev brugt.
    """
    h = u.Hensyn(hensyn_id="b", kategori="kost", regel="foreslå ikke kød",
                 graense="medmindre han spørger")
    assert u.tjek_brud(h, "Du kunne lave en gryderet med kød i.") is True
    assert u.tjek_brud(h, "Han spiste kød i går.") is False


def test_brud_taeller_ikke_for_kategorier_uden_noegleord() -> None:
    """Kun kost er entydig nok til en deterministisk detektor."""
    h = u.Hensyn(hensyn_id="b2", kategori="foelelser", regel="nævn ikke hans sorg",
                 graense="medmindre han selv bringer det op")
    assert u.tjek_brud(h, "Du bør prøve at tale om sorg med nogen.") is False
