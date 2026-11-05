"""Fakta-filer chunkes pr. PUNKT, så én fakta bliver én vektor.

Målt 5/11-2026: Bjørn spurgte «hvad har jeg af køretøjer? og hvilke motor har
de?». Faktaen står i `USER.md` under `## Personal`, men sektionen blev delt i
seks vilkårlige 800-tegns vinduer. El-cykel-faktaen landede i samme chunk som
drone-app, drone og en sætning der var klippet midt over — så vektoren blev et
gennemsnit af fem ubeslægtede emner. Søgningen gav dagens egen samtale i top-3
og faktaen uden for top-12.

Disse tests værner om ISOLATIONEN, ikke om et tal: en fakta må ikke dele vektor
med en anden fakta, og prosa-filer skal stadig chunkes i vinduer.
"""
from __future__ import annotations

from core.services.memory_search import (
    _FAKTA_FILES,
    _chunk_fakta,
    _chunk_markdown,
)


def test_hver_fakta_faar_sin_egen_chunk() -> None:
    """To beslægtede men forskellige fakta må ikke dele vektor.

    MUTATION: skift `_chunk_fakta` tilbage til 800-tegns vinduer → de to fakta
    lander i samme chunk → fejler.
    """
    tekst = (
        "## Personal\n\n"
        "- **Køretøjer:** El-cykel 2× 1000 W, tophast ~50–55 km/t.\n"
        "- **Drone:** Eachine EX3, 640 g, 2K kamera uden gimbal.\n"
    )
    chunks = _chunk_fakta(tekst, "USER.md")
    cykel = [c for c in chunks if "El-cykel" in c.text]
    drone = [c for c in chunks if "Eachine" in c.text]
    assert len(cykel) == 1, f"El-cykel skal ligge i præcis én chunk, fik {len(cykel)}"
    assert len(drone) == 1, f"Drone skal ligge i præcis én chunk, fik {len(drone)}"
    assert cykel[0].text != drone[0].text, "de to fakta deler chunk — vektoren er blandet"


def test_chunken_baerer_sin_overskrifts_sti() -> None:
    """Stien skal stå i teksten, ellers kan vektoren ikke se emnet."""
    tekst = "## Personal\n\n- **Køretøjer:** El-cykel 2× 1000 W.\n"
    chunks = _chunk_fakta(tekst, "USER.md")
    assert chunks, "ingen chunks"
    assert chunks[0].section == "Personal"
    assert chunks[0].text.startswith("Personal: "), chunks[0].text[:60]


def test_fortsættelseslinjer_hører_til_punktet_ovenfor() -> None:
    """En indrykket linje er samme fakta, ikke en ny."""
    tekst = (
        "## Personal\n\n"
        "- **Køretøjer:** El-cykel 2× 1000 W.\n"
        "  Overvejer VESC til begge.\n"
        "- **Drone:** Eachine EX3.\n"
    )
    chunks = _chunk_fakta(tekst, "USER.md")
    cykel = [c for c in chunks if "El-cykel" in c.text]
    assert len(cykel) == 1
    assert "VESC" in cykel[0].text, "fortsættelseslinjen blev skilt fra sin fakta"


def test_lang_fakta_deles_stadig() -> None:
    """Et punkt længere end loftet skal kunne søges i sin helhed."""
    lang = "- **Lang:** " + ("ord " * 400)
    chunks = _chunk_fakta(f"## Personal\n\n{lang}\n", "USER.md")
    assert len(chunks) > 1, "en 2.000-tegns fakta blev ikke delt"
    assert all(len(c.text) <= 800 for c in chunks), "en chunk overskrider loftet"


def test_prosa_filer_beholder_vinduer() -> None:
    """MEMORY.md er prosa — den må IKKE skifte til punkt-chunking."""
    assert "USER.md" in _FAKTA_FILES
    assert "MEMORY.md" not in _FAKTA_FILES, (
        "MEMORY.md er ræsonnement, ikke fakta-linjer — vinduer er det rigtige der"
    )
    tekst = "## Sektion\n\n" + ("En lang sammenhængende forklaring. " * 60)
    assert len(_chunk_markdown(tekst, "MEMORY.md")) > 1


def test_koblingen_bruges_af_indeks_bygningen(tmp_path) -> None:
    """_chunk_all_files skal FAKTISK kalde fakta-chunkeren for USER.md.

    Uden denne test er de øvrige fem grønne selv om koblingen fjernes: de kalder
    `_chunk_fakta` direkte og ser aldrig om indekset bruger den. Målt 5/11-2026 —
    mutationen «skift tilbage til vinduer» gik gennem alle fem tests.

    MUTATION: fjern `if f.name in _FAKTA_FILES`-grenen i `_chunk_all_files` →
    de to fakta deler chunk → fejler.
    """
    from core.services.memory_search import _chunk_all_files

    (tmp_path / "USER.md").write_text(
        "## Personal\n\n"
        "- **Køretøjer:** El-cykel 2× 1000 W, tophast ~50–55 km/t.\n"
        "- **Drone:** Eachine EX3, 640 g, 2K kamera uden gimbal.\n",
        encoding="utf-8",
    )
    chunks = _chunk_all_files([tmp_path / "USER.md"], tmp_path)
    cykel = [c for c in chunks if "El-cykel" in c.text]
    drone = [c for c in chunks if "Eachine" in c.text]
    assert len(cykel) == 1 and len(drone) == 1, (
        f"indeks-bygningen chunker ikke pr. punkt: cykel={len(cykel)} drone={len(drone)}"
    )
    assert cykel[0].text != drone[0].text, (
        "indeks-bygningen lagde to fakta i samme chunk — fakta-chunkeren bruges ikke"
    )
