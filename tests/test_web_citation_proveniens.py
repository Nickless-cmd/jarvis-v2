"""Web-proveniens: ref-id'er der gør `cite`-markøren brugbar.

2/11-2026. `citation_markorer` blev bygget som kontrolsyntaks, men kæden var
åben i den anden ende: `web_search` gav modellen `title`/`url`/`content` uden
noget id, så en `【cite|ref1】` ikke kunne pege på noget. Kontrakten var
fail-closed og afviste derfor ALT — korrekt, men også ubrugeligt.

To ting testes her, og de hører sammen:

1. **Leverandøren**: et web-resultat bærer et ref-id, modellen kan skrive.
2. **Genkendelsen**: den samme ref kan slås op i `Kilder`, så kontrakten
   godkender citationen — og en OPFUNDET ref afvises stadig.

Ref-id'et er udledt af URL'en (hash), ikke af rækkefølgen. Det er valget der
gør det stabilt: samme kilde hedder det samme i næste tur, i næste kald og i
en genkørt samtale. Et løbenummer ville gøre `ref1` til to forskellige kilder
alt efter hvilken søgning der kom først.
"""

from __future__ import annotations

import pytest

from core.services.citation_markorer import Kilder, parse_markorer


# ── 1. Leverandøren: web-resultatet skal bære et ref-id ──────────────────────


def test_web_resultat_barer_et_ref_id_modellen_kan_citere():
    """Kernen i hele sagen: uden et synligt id kan modellen ikke citere."""
    from core.tools.simple_tools_web import _ref_for_url

    ref = _ref_for_url("https://www.dr.dk/nyheder/indland/eksempel")
    assert ref, "en URL skal kunne give et ref-id"
    assert ref.startswith("ref"), f"ref-id'et skal være læsbart, fik {ref!r}"
    assert " " not in ref and "|" not in ref and "】" not in ref, (
        f"ref-id'et må ikke kunne bryde markør-syntaksen: {ref!r}"
    )


def test_samme_url_giver_samme_ref_hver_gang():
    """Stabilitet er hele pointen — ellers kan en citation ikke genfindes."""
    from core.tools.simple_tools_web import _ref_for_url

    a = _ref_for_url("https://example.dk/a")
    b = _ref_for_url("https://example.dk/a")
    c = _ref_for_url("https://example.dk/b")
    assert a == b, "samme URL skal give samme ref"
    assert a != c, "forskellige URL'er skal ikke dele ref"


def test_forskellige_urls_kolliderer_ikke_i_praksis():
    """Hash-kollision ville gøre en citation tavst forkert."""
    from core.tools.simple_tools_web import _ref_for_url

    urls = [f"https://example.dk/side-{i}" for i in range(500)]
    refs = {_ref_for_url(u) for u in urls}
    assert len(refs) == len(urls), (
        f"{len(urls) - len(refs)} kollisioner i 500 vilkårlige URL'er"
    )


# ── 2. Genkendelsen: ref'en skal kunne slås op ───────────────────────────────


def test_kilder_kan_fyldes_efter_den_er_oprettet():
    """Filteret laves ved run-start, FØR nogen søgning er kørt.

    Kilderne skal derfor kunne fyldes mens turen kører. Det er ikke en
    bekvemmelighed: alternativet er at kende fremtiden ved instansiering.
    """
    k = Kilder()
    assert k.url_for("ref-abc123") is None, "tomme kilder må ikke svare på noget"

    k.tilfoej("ref-abc123", "https://example.dk/a")
    assert k.url_for("ref-abc123") == "https://example.dk/a"


def test_citation_paa_en_registreret_kilde_bliver_et_link():
    """Hele kæden: en ref der ER registreret bliver et rigtigt link."""
    k = Kilder()
    k.tilfoej("ref-abc123", "https://example.dk/a")

    ren, fund = parse_markorer("Se 【url|kilden|ref-abc123】 for detaljer.", k)
    assert "【" not in ren, f"markøren lækkede: {ren!r}"
    assert "https://example.dk/a" in ren, f"linket blev ikke dannet: {ren!r}"
    assert fund and fund[0].godkendt is True


def test_citation_paa_en_opfundet_ref_afvises_stadig():
    """Fail-closed må ikke gå tabt i arbejdet med at gøre kæden brugbar."""
    k = Kilder()
    k.tilfoej("ref-abc123", "https://example.dk/a")

    ren, fund = parse_markorer("Se 【url|kilden|ref-opdigtet】 her.", k)
    assert "【" not in ren
    assert "https://example.dk/a" not in ren, "en opdigtet ref må ikke låne en anden kildes URL"
    assert fund and fund[0].godkendt is False


def test_cite_markor_godkendes_kun_for_registrerede_refs():
    """`cite` (uden link) skal følge samme regel som `url`."""
    k = Kilder()
    k.tilfoej("ref-abc123", "https://example.dk/a")

    _, aegte = parse_markorer("Påstand 【cite|ref-abc123】", k)
    _, falsk = parse_markorer("Påstand 【cite|ref-xxxxxx】", k)
    assert aegte[0].godkendt is True
    assert falsk[0].godkendt is False


# ── 3. Turen ejer sine kilder ────────────────────────────────────────────────


def test_turen_registrerer_web_kilder_fra_sine_tool_resultater():
    """Run-løkken skal føde kilderne — ellers er de tomme når teksten kommer.

    Dette er forbindelsen der gør de to første afsnit til én kæde: et
    `web_search`-resultat i turen skal efterlade sine kilder i turens
    akkumulator, så filteret kan validere mod dem bagefter.
    """
    from core.services.visible_turn_accumulator import TurnAccumulator

    t = TurnAccumulator()
    resultat = {
        "status": "ok",
        "text": "1. **DR**\n   noget\n   https://www.dr.dk/a",
        "results": [
            {"title": "DR", "url": "https://www.dr.dk/a", "content": "noget"},
        ],
    }
    t.registrer_web_kilder("web_search", resultat)

    refs = t.kilder.web
    assert len(refs) == 1, f"forventede én kilde, fik {refs}"
    ref, url = next(iter(refs.items()))
    assert url == "https://www.dr.dk/a"

    # Og den ref kan kontrakten nu godkende.
    _, fund = parse_markorer(f"Se 【cite|{ref}】", t.kilder)
    assert fund[0].godkendt is True


def test_andre_vaerktoejer_end_web_registrerer_intet():
    """En bash-kommando er ikke en kilde. Kun web-resultater må fylde listen.

    MÅLT 2/11-2026: den første udgave af denne test sendte et resultat UDEN
    `results` — og så bestod den, selv da tool_name-tjekket blev fjernet.
    Den målte fraværet af data, ikke fraværet af tilladelse. Nu bærer
    resultatet en rigtig URL, saa det ENESTE der kan afvise den er navnet.
    """
    from core.services.visible_turn_accumulator import TurnAccumulator

    t = TurnAccumulator()
    t.registrer_web_kilder(
        "bash", {"status": "ok", "results": [{"title": "x", "url": "https://example.dk/a"}]}
    )
    t.registrer_web_kilder(
        "read_file",
        {"status": "ok", "results": [{"title": "y", "url": "https://example.dk/b"}]},
    )
    assert t.kilder.web == {}, (
        "et ikke-web-værktøj registrerede en kilde — så kan en bash-udskrift "
        "citeres som om den var slået op"
    )


def test_et_fejlet_web_kald_registrerer_intet():
    """`status: error` bærer ingen brugbare kilder."""
    from core.services.visible_turn_accumulator import TurnAccumulator

    t = TurnAccumulator()
    t.registrer_web_kilder("web_search", {"status": "error", "error": "netdown"})
    assert t.kilder.web == {}


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "data:text/html,<script>",
        "file:///etc/passwd",
        "",
        "ikke-en-url",
    ],
)
def test_uskadelige_kilder_registreres_ikke(url):
    """En kilde der ikke kan linkes til må ikke kunne citeres som om den kan."""
    from core.services.visible_turn_accumulator import TurnAccumulator

    t = TurnAccumulator()
    t.registrer_web_kilder(
        "web_search", {"status": "ok", "results": [{"title": "x", "url": url}]}
    )
    assert t.kilder.web == {}, f"{url!r} blev registreret som kilde"
