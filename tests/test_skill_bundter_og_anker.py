"""«brug pdf skill» fandt intet — og matcheren var uskyldig.

## Målt 15/9-2026

Codex' analyse konkluderede at matcheren manglede eksplicit navne-genkendelse.
Efterprøvningen viste noget andet: matcheren kendte **63 skills, og PDF-skillet
var ikke iblandt dem**.

`_scan_skills` kiggede kun ét niveau ned — `<rod>/<navn>/SKILL.md`. Men
`composio-document-skills/` har ingen egen SKILL.md; det er en mappe med fire
skills i:

    composio-document-skills/docx
    composio-document-skills/pdf      ← name: pdf
    composio-document-skills/xlsx
    composio-document-skills/pptx

Alle fire var usynlige. Matcheren kunne ikke matche noget den aldrig havde
fået at se. Efter rettelsen: 63 → 67 skills, og «brug pdf skill» giver
`pdf (0,76)`.

## Det andet lag: ankeret

Forslag kræver et leksikalsk anker — mindst ét betydningsbærende ord delt
mellem forespørgsel og skill. Men «skill» talte med, så «brug pdf skill» også
trak `composio-skill-creator` (0,71) og `composio-template-skill` (0,71) ind.
To af tre pladser i fladen gik til støj.

Ord der handler om MEKANISMEN bærer ikke længere et anker.
"""
from __future__ import annotations

import pytest

from core.services import skill_engine as se
from core.tools import skill_engine_tools as st


# ───────────────────────────────────────────────────── bundter

@pytest.fixture
def rod(tmp_path, monkeypatch):
    monkeypatch.setattr(se, "SKILLS_ROOT", tmp_path)
    return tmp_path


def _skriv(mappe, navn: str, beskrivelse: str = "noget") -> None:
    mappe.mkdir(parents=True, exist_ok=True)
    (mappe / "SKILL.md").write_text(
        f"---\nname: {navn}\ndescription: {beskrivelse}\n---\n\n# {navn}\n",
        encoding="utf-8",
    )


def test_et_almindeligt_skill_indlaeses(rod):
    _skriv(rod / "alene", "alene")
    assert "alene" in se._scan_skills()


def test_et_BUNDT_indlaeses(rod):
    """Den ægte sag: fire dokument-skills lå usynlige i et bundt."""
    _skriv(rod / "bundt" / "pdf", "pdf")
    _skriv(rod / "bundt" / "docx", "docx")
    ud = se._scan_skills()
    assert {"pdf", "docx"} <= set(ud), sorted(ud)


def test_kun_ÉT_ekstra_niveau(rod):
    """Et bundt er en mappe med skills i, ikke et træ af vilkårlig dybde. En
    ubegrænset scanning ville gøre enhver tilfældig undermappe til et skill."""
    _skriv(rod / "bundt" / "dybere" / "for_dybt", "for_dybt")
    ud = se._scan_skills()
    # Igen: navnet er mappens. «for_dybt» ER mappenavnet her.
    assert "for_dybt" not in ud, sorted(ud)
    # Og mellemniveauet må heller ikke blive et skill.
    assert "dybere" not in ud, sorted(ud)


def test_et_bundt_med_EGEN_skill_md_er_ikke_et_bundt(rod):
    """Har mappen selv en SKILL.md, ER den skillet — så skal dens undermapper
    ikke også blive til skills (scripts/, references/ ligger dér)."""
    _skriv(rod / "eget", "eget")
    _skriv(rod / "eget" / "references", "reference_ved_en_fejl")
    ud = se._scan_skills()
    assert "eget" in ud
    # Navnet er MAPPENS. Første udgave ledte efter frontmatter-navnet og
    # bestod derfor selv når undermappen faktisk blev indlæst.
    assert "references" not in ud, sorted(ud)


def test_skillets_navn_er_MAPPENS_navn_ikke_frontmatterens(rod):
    """`name = path.parent.name`. Frontmatterens `name:` bruges ikke som nøgle.

    Det fandt jeg ved at skrive en test der antog det modsatte — den fejlede,
    og det var testen der tog fejl, ikke koden. Skrevet ned så den næste ikke
    skal finde det igen.
    """
    _skriv(rod / "mappenavn", "noget-helt-andet")
    ud = se._scan_skills()
    assert "mappenavn" in ud
    assert "noget-helt-andet" not in ud


def test_navnesammenstoed_overskriver_ikke_TAVST(rod):
    """Navnet er nøglen i registret, så en dublet ville forsvinde uden spor.

    Ægte kollision = samme MAPPENAVN to steder, siden mappen er navnet.
    """
    _skriv(rod / "pdf", "pdf", "den foerste")
    _skriv(rod / "bundt" / "pdf", "pdf", "den anden")
    ud = se._scan_skills()
    # Det vigtige er INVARIANTEN: begge overlever. Præcis hvilket navn den
    # anden får er en detalje — første udgave af testen bandt sig til
    # «bundt/pdf», men mapperne scannes sorteret, så bundtet kommer FØRST og
    # tager det korte navn. Den antagelse var min, ikke kodens.
    assert len(ud) == 2, sorted(ud)
    beskrivelser = {s.description for s in ud.values()}
    assert beskrivelser == {"den foerste", "den anden"}, beskrivelser


# ───────────────────────────────────────────────────── ankeret

@pytest.mark.parametrize("ord", ["skill", "skills", "tool", "workflow", "brug", "use"])
def test_mekanik_ord_baerer_ikke_anker(ord):
    assert ord not in st._betydende_ord(f"noget {ord} her")


def test_opgavens_ord_baerer_stadig():
    """En for bred liste ville fjerne ægte signal."""
    assert "pdf" in st._betydende_ord("brug pdf skill")
    assert "excel" in st._betydende_ord("hjaelp mig med excel")
    assert "regneark" in st._betydende_ord("lav et regneark")


def test_en_forespoergsel_der_KUN_er_mekanik_giver_intet_anker():
    """«hvilke skills har du» er et spørgsmål om mekanismen, ikke en opgave."""
    assert st._betydende_ord("brug et skill") == set()


# ─────────────────────────── laengde-gulvet maa ikke spaerre den eksplicitte bøn

from core.services import skill_relevance_surface as srs


def test_en_eksplicit_bøn_slipper_gennem_gulvet():
    """«brug pdf skill» er 14 tegn — ét under tærsklen — og er samtidig den
    mest eksplicitte skill-anmodning der findes.

    Prisen er målt: af 1.527 brugerbeskeder på 30 dage var 294 under 15 tegn,
    og NUL af dem nævnte «skill». Undtagelsen koster reelt ingenting.
    """
    assert len("brug pdf skill") < srs._MIN_MESSAGE_CHARS
    assert srs._naevner_mekanismen("brug pdf skill")


@pytest.mark.parametrize("besked", ["hej", "ok tak", "ja", "godt"])
def test_smaasnak_spaerres_stadig(besked):
    """Gulvet findes for at spare et embed-kald på de ture hvor der alligevel
    aldrig er et match. Det skal det blive ved med."""
    assert not srs._naevner_mekanismen(besked)


def test_at_spoerge_og_at_bevise_er_ikke_det_samme():
    """Ordet «skill» må gerne sige at vi skal SE EFTER — men det må ikke kunne
    bevise et match. De to regler ser modsatrettede ud og er det ikke."""
    assert srs._naevner_mekanismen("brug pdf skill")       # se efter: ja
    assert "skill" not in st._betydende_ord("brug pdf skill")  # bevise: nej


def test_invokering_siger_HVOR_skillet_ligger(rod, monkeypatch):
    """Dokument-skillene henviser til `scripts/recalc.py` relativt til mappen.
    Uden mappen i svaret kan han ikke finde scriptet — 15/9 fandt han en
    tilfaeldig kopi et helt andet sted."""
    _skriv(rod / "bundt" / "xlsx", "xlsx")
    (rod / "bundt" / "xlsx" / "scripts").mkdir()
    (rod / "bundt" / "xlsx" / "scripts" / "recalc.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(se, "_skills_cache", None, raising=False)
    monkeypatch.setattr(se, "get_skill", lambda n: se._scan_skills().get(n))
    ud = se.get_skill_instructions("xlsx")
    assert ud["skill_dir"] == str(rod / "bundt" / "xlsx")
    assert "recalc.py" in ud["scripts"]
