"""Citation-proveniens og metadata-udgang — de to huller Bjørn målte 2/11-2026.

To påstande testes, og de hører sammen:

1. **memcite må ikke godkendes på en påstand.** Kontrakten sagde i sin kommentar
   at «runtime afgjorde at memory var i konteksten» — men runtime afgjorde
   intet, og `memcite` blev godkendt ubetinget. Nu skal godkendelsen komme fra
   et *probe* der spørger den prompt der faktisk blev bygget.

2. **Fundene må ikke ligge i en død liste.** `CitationKontrakt.fundet` blev
   fyldt ved hver `feed()`, men havde nul læsere. Nu skal turen samle dem op,
   så de kan afleveres til observability.

Testene er skrevet så de fejler på den adfærd der var forkert — ikke på at en
funktion mangler at eksistere.
"""

from __future__ import annotations

import pathlib

import pytest


# ── 1. memcite-proveniens ─────────────────────────────────────────────────


def test_memcite_afvises_naar_memory_ikke_var_i_konteksten():
    """Kernen: uden memory i prompten er påstanden om hukommelse falsk."""
    from core.services.citation_markorer import Kilder, parse_markorer

    kilder = Kilder(memory_probe=lambda: False)
    ren, fundet = parse_markorer("Svaret bygger på det. 【memcite】", kilder)

    assert ren.strip() == "Svaret bygger på det."
    assert len(fundet) == 1
    assert fundet[0].slags == "memcite"
    assert fundet[0].godkendt is False, (
        "memcite blev godkendt selv om memory ikke var i konteksten — "
        "det er præcis den påstand uden dækning opgaven pegede på"
    )


def test_memcite_godkendes_naar_memory_var_i_konteksten():
    from core.services.citation_markorer import Kilder, parse_markorer

    kilder = Kilder(memory_probe=lambda: True)
    ren, fundet = parse_markorer("Svaret bygger på det. 【memcite】", kilder)

    assert ren.strip() == "Svaret bygger på det."
    assert fundet[0].godkendt is True


def test_memcite_uden_probe_afvises_fail_closed():
    """Ingen probe = ingen viden = ingen godkendelse.

    Det er den samme regel som for `cite`: hellere ingen citation end en
    opdigtet. En `Kilder()` uden probe må ikke arve en tidligere sandhed.
    """
    from core.services.citation_markorer import Kilder, parse_markorer

    _, fundet = parse_markorer("Påstand. 【memcite】", Kilder())
    assert fundet[0].godkendt is False


def test_proben_spoerges_hver_gang_ikke_en_gang():
    """Proveniensen er levende: prompten bygges EFTER filteret instantieres.

    En bool der blev læst ved instansiering ville være False for evigt — det
    er den rækkefølge-fælde der gjorde kæden død i går. Probens svar skal
    derfor aflæses ved opslaget.
    """
    from core.services.citation_markorer import Kilder, parse_markorer

    svar = {"memory": False}
    kilder = Kilder(memory_probe=lambda: svar["memory"])

    _, foer = parse_markorer("A 【memcite】", kilder)
    svar["memory"] = True
    _, efter = parse_markorer("B 【memcite】", kilder)

    assert foer[0].godkendt is False
    assert efter[0].godkendt is True


def test_web_citationer_er_uaendrede_af_proveniens_arbejdet():
    """`cite` må ikke rammes af at `memcite` fik en regel."""
    from core.services.citation_markorer import Kilder, parse_markorer

    kilder = Kilder(web={"ref-a": "https://example.dk/a"}, memory_probe=lambda: False)
    ren, fundet = parse_markorer("Se her 【cite|ref-a】.", kilder)

    assert fundet[0].slags == "cite"
    assert fundet[0].godkendt is True
    assert "【" not in ren


# ── 2. metadata-udgangen ──────────────────────────────────────────────────


def test_kontrakten_opsummerer_fundene_som_metadata():
    """Fundene skal kunne afleveres som JSON-egnet metadata, ikke som objekter."""
    from core.services.citation_markorer import Kilder, parse_markorer

    kilder = Kilder(web={"ref-a": "https://example.dk/a"}, memory_probe=lambda: True)
    _, fundet = parse_markorer("Se 【cite|ref-a】 og 【memcite】.", kilder)

    oppsummeret = [f.til_metadata() for f in fundet]

    assert all(isinstance(m, dict) for m in oppsummeret)
    assert {m["slags"] for m in oppsummeret} == {"cite", "memcite"}
    assert all("raa" not in m or isinstance(m["raa"], str) for m in oppsummeret)
    # Et godkendt cite skal bære den URL det pegede på — ellers kan ingen
    # observability vise hvad der faktisk blev citeret.
    cite = next(m for m in oppsummeret if m["slags"] == "cite")
    assert cite["urls"] == ["https://example.dk/a"]


def test_turen_samler_citationer_og_de_naar_observability():
    """`fundet` må ikke længere være en liste uden læsere.

    Testen fylder turen med RIGTIGE fund — en attribut der blot eksisterer
    beviser intet. Det var præcis fejlen: listen fandtes og blev fyldt, men
    ingen læste den.
    """
    from core.services.citation_markorer import Kilder, parse_markorer
    from core.services.visible_turn_accumulator import TurnAccumulator

    kilder = Kilder(web={"ref-a": "https://example.dk/a"}, memory_probe=lambda: True)
    _, fundet = parse_markorer("Se 【cite|ref-a】 og 【memcite】.", kilder)

    turn = TurnAccumulator(kilder=kilder)
    assert turn.citationer == []
    turn.registrer_citationer(fundet)

    assert len(turn.citationer) == 2, "fundene nåede ikke ind i turen"
    cite = next(c for c in turn.citationer if c["slags"] == "cite")
    assert cite["urls"] == ["https://example.dk/a"]
    assert all(isinstance(c, dict) for c in turn.citationer)


def test_turen_taaler_soeppel_i_fundlisten():
    """En fejl i sporingen må aldrig kunne vælte et svar der virkede."""
    from core.services.visible_turn_accumulator import TurnAccumulator

    turn = TurnAccumulator()
    turn.registrer_citationer([object(), None, "tekst"])
    assert turn.citationer == []


def test_visible_runs_kalder_registreringen_og_afleverer_i_tracet():
    """Kaldestedet skal findes i kilden — en beholder ingen kalder er død."""
    src = pathlib.Path("core/services/visible_runs.py").read_text(encoding="utf-8")

    assert "_turn.registrer_citationer(markup_buffer.fundet)" in src, (
        "fundene samles i kontrakten men kaldes aldrig ind i turen — "
        "så er metadata stadig i en død liste"
    )
    assert '"citationer": list(_turn.citationer)' in src, (
        "citationerne når ikke tracet — så er de usynlige for observability"
    )



def test_visible_runs_giver_filteret_en_probe_mod_sessionen():
    """Koblingen skal være i kilden, ikke i en test-dobbelt.

    Vagten læser `visible_runs.py` fordi det er der filteret instantieres; en
    test der kun kalder `Kilder(memory_probe=...)` beviser at API'et virker,
    ikke at det bliver brugt.
    """
    src = pathlib.Path("core/services/visible_runs.py").read_text(encoding="utf-8")

    assert "memory_probe" in src, (
        "visible_runs instantierer Kilder UDEN memory_probe — så afvises "
        "enhver memcite fail-closed, og proveniensen er stadig ikke koblet på"
    )


def test_prompt_contract_registrerer_memory_i_konteksten():
    """Sandheden om memory står i prompt_contract, hvor gruppen dannes.

    Vagten kræver KALDET, ikke blot navnet. Målt 2/11-2026: en tidligere
    udgave tjekkede kun at strengen `marker_memory_i_kontekst` stod i filen —
    og den overlevede en mutation der erstattede kaldet med `pass`, fordi
    navnet stadig stod i import-linjen. En vagt der grep'er efter et navn i
    en stor fil måler næsten intet.
    """
    src = pathlib.Path("core/services/prompt_contract.py").read_text(encoding="utf-8")

    assert "marker_memory_i_kontekst(session_id" in src, (
        "prompt_contract KALDER ikke registeret — så har proben intet at spørge, "
        "og memcite afvises altid fail-closed"
    )



# ── 3. registeret selv ────────────────────────────────────────────────────


def test_registeret_svarer_kun_for_den_session_der_blev_markeret():
    from core.services import context_proveniens as cp

    cp.ryd_register()
    cp.marker_memory_i_kontekst("session-a", 3)

    assert cp.memory_i_kontekst("session-a") is True
    assert cp.memory_i_kontekst("session-b") is False
    assert cp.memory_i_kontekst("") is False


def test_nul_linjer_er_en_sandhed_der_slaar_en_tidligere_tur_ud():
    """«Ingen memory i denne prompt» skal kunne overskrive et gammelt ja."""
    from core.services import context_proveniens as cp

    cp.ryd_register()
    cp.marker_memory_i_kontekst("session-a", 5)
    assert cp.memory_i_kontekst("session-a") is True

    cp.marker_memory_i_kontekst("session-a", 0)
    assert cp.memory_i_kontekst("session-a") is False


def test_en_udloebet_registrering_godkender_ikke_laengere(monkeypatch):
    """Uden TTL kunne en tur fra i går godkende en memcite i dag."""
    from core.services import context_proveniens as cp

    cp.ryd_register()
    cp.marker_memory_i_kontekst("session-a", 2)

    # Skub tidsstemplet tilbage ud over TTL'en.
    with cp._LAAS:
        tid, antal = cp._REGISTER["session-a"]
        cp._REGISTER["session-a"] = (tid - cp.TTL_SEKUNDER - 1.0, antal)

    assert cp.memory_i_kontekst("session-a") is False
