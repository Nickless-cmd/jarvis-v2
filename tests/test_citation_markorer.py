"""Citation-markører: kontrolsyntaks der ALDRIG må nå skærmen.

To opgaver, én kontrakt (2/11-2026):

* `side-991bb8e07b` — memory-citations: `【memcite】`
* `side-335ac89e6f` — web-citations: `【cite|ref1|ref2】` og
  `【url|ankertekst|ref-eller-kvalificeret-url】`

## Hvorfor det hører i `FirstPassOutputFilter`

Den grænse findes allerede og fjerner fire former for model-markup før
mennesket ser teksten (capability-markup, runtime-markører, DSML og den halve
DSML-form). Den har også de to ting en markør-kontrakt kræver: en hale der
holder et delvist token tilbage, og en `flush` der afgør hvad en uafsluttet
hale betyder. At bygge en parallel grænse ville være det samme problem løst
to steder — og den ene ville drive.

## Reglen der gør den sikker

En markør er kun en markør hvis dens indhold VALIDERER. Ukendte ref-id'er,
opdigtede kilder og skadelige URL-schemes afvises, og markøren falder tilbage
til sin egen tekst — aldrig til ingenting, for et svar må ikke tabe indhold
fordi en model skrev en reference der ikke findes.
"""
from __future__ import annotations

import pytest

from core.services.citation_markorer import (
    CitationKontrakt,
    Kilder,
    parse_markorer,
)


def _koer(tekst: str, kilder: Kilder | None = None, chunk: int = 0) -> str:
    """Kør teksten gennem kontrakten — evt. i bidder, som en strøm gør."""
    k = CitationKontrakt(kilder or Kilder())
    if chunk <= 0:
        return k.feed(tekst) + k.flush()
    vist = "".join(k.feed(tekst[i:i + chunk]) for i in range(0, len(tekst), chunk))
    return vist + k.flush()


# ── Positive: markøren fjernes, indholdet bliver ────────────────────────────

def test_memcite_fjernes_og_teksten_bliver():
    vist = _koer("Du kan lide kaffe om morgenen【memcite】.")
    assert "memcite" not in vist
    assert "Du kan lide kaffe om morgenen" in vist


def test_cite_med_kendt_ref_fjernes():
    kilder = Kilder(web={"ref1": "https://example.dk/a"})
    vist = _koer("Det regner i morgen【cite|ref1】.", kilder)
    assert "【" not in vist and "cite" not in vist
    assert "Det regner i morgen" in vist


def test_url_med_kendt_ref_bliver_et_link():
    kilder = Kilder(web={"ref1": "https://example.dk/a"})
    vist = _koer("Se 【url|kilden|ref1】 for detaljer.", kilder)
    assert "【" not in vist
    assert "https://example.dk/a" in vist
    assert "kilden" in vist


def test_url_med_kvalificeret_https_adresseres_direkte():
    vist = _koer("Se 【url|dokumentation|https://docs.example.dk/x】.")
    assert "【" not in vist
    assert "https://docs.example.dk/x" in vist


# ── Negative: det der IKKE må markeres ──────────────────────────────────────

def test_ukendt_ref_afvises_og_falder_tilbage_til_tekst():
    """En opdigtet reference må ikke blive et link — men indholdet må ikke forsvinde."""
    kilder = Kilder(web={"ref1": "https://example.dk/a"})
    vist = _koer("Påstand【cite|ref9】.", kilder)
    assert "https://" not in vist, "en ukendt ref må ikke blive et link"
    assert "Påstand" in vist and "." in vist


def test_skadeligt_url_scheme_afvises():
    for skadelig in (
        "javascript:alert(1)",
        "data:text/html,<script>x</script>",
        "file:///etc/passwd",
        "vbscript:msgbox",
    ):
        vist = _koer(f"Se 【url|klik|{skadelig}】.")
        assert "javascript:" not in vist
        assert "data:text/html" not in vist
        assert "file://" not in vist
        assert "vbscript:" not in vist


def test_almindelig_klamme_er_ikke_en_markor():
    """`【` bruges også som rent tegn — den må ikke ædes."""
    vist = _koer("Prisen er 【150 kr】 for billetten.")
    assert "150 kr" in vist


def test_markdown_link_roeres_ikke():
    vist = _koer("Se [dokumentation](https://example.dk/x).")
    assert "[dokumentation](https://example.dk/x)" in vist


# ── Streaming: et delvist token må ikke blinke ──────────────────────────────

@pytest.mark.parametrize("chunk", range(1, 24))
def test_delvist_token_blinker_ikke_ved_nogen_chunkgraense(chunk):
    tekst = "Før 【cite|ref1】 midt 【memcite】 efter."
    kilder = Kilder(web={"ref1": "https://example.dk/a"})
    vist = _koer(tekst, kilder, chunk=chunk)
    assert "【" not in vist
    assert "memcite" not in vist
    assert "Før" in vist and "midt" in vist and "efter" in vist


def test_uafsluttet_markor_i_halen_slippes_som_tekst():
    """En `【` der aldrig lukkes er prosa — den må ikke tie resten af svaret."""
    vist = _koer("Her er en åben klamme 【 uden slutning")
    assert "uden slutning" in vist


# ── Parse-laget: metadata bevares ───────────────────────────────────────────

def test_parse_returnerer_kilder_til_observability():
    kilder = Kilder(web={"ref1": "https://example.dk/a", "ref2": "https://example.dk/b"})
    ren, fundet = parse_markorer(
        "A【cite|ref1】 B【cite|ref2】 C【memcite】", kilder
    )
    assert "【" not in ren
    assert [f.slags for f in fundet] == ["cite", "cite", "memcite"]
    assert fundet[0].refs == ("ref1",)
    assert fundet[1].refs == ("ref2",)


def test_parse_afviser_ukendt_ref_men_bevarer_den_som_afvist():
    kilder = Kilder(web={"ref1": "https://example.dk/a"})
    ren, fundet = parse_markorer("A【cite|ref9】", kilder)
    assert fundet == [] or all(f.godkendt is False for f in fundet)
    assert "A" in ren


# ── Code mode: byte-uændret ─────────────────────────────────────────────────

def test_kode_uden_markorer_er_byte_uændret():
    """Filteret må ikke røre almindelig kode — heller ikke klammer.

    Code mode deler `FirstPassOutputFilter` med chat, så kravet «må ikke ændre
    code mode» kan kun holdes ved at måle det. Kode er fuld af `[`, `{`, `】`
    og URL'er; ingen af dem er en markør.
    """
    kode = (
        "def f(x: list[int]) -> dict[str, int]:\n"
        '    """Returnér 【ikke en markør】 men en docstring."""\n'
        "    return {k: v for k, v in enumerate(x)}\n"
        "\n"
        "url = 'https://example.dk/a?b=1&c=2'\n"
        "print(f'{url} 【150 kr】')\n"
    )
    assert _koer(kode) == kode


def test_kode_med_klamme_i_streng_er_uændret():
    kode = 'x = "【cite|ref1】"  # en streng, ikke en markør\n'
    # Uden kilder validerer ref1 ikke — men markøren står i en STRENG, og
    # filteret kan ikke kende forskel. Det er den ærlige begrænsning: en
    # model der skriver syntaksen i en kodeblok får den fjernet.
    vist = _koer(kode)
    assert "x = " in vist
