"""Værns-noterne: hvad Bjørn ser, og hvad modellen må se.

Bjørns stående regel 3/10-2026: alt der ikke er skrevet fra hans composer skal
mærkes som fra systemet. Udløst af at han og Codex fandt værn der kostede ekstra
runder, fordi «hans tomt løfte værn kunne starte en ny runde i mit navn».

Målt samme dag: fem værns-noter appender til `_a_parts`, og `_a_parts` ER næste
rundes model-input (`compose_exchange_text`s egen docstring). Fire er i jeg-form,
tre bar ordene «Sig til» — altså en opfordring i første person, uadskillelig fra
Bjørns egne ord.

Testene her pinner de tre ting der skal holde:

1. Klasse 3 forsvinder fra model-input men BLIVER i det Bjørn ser.
2. Klasse 1 og 2 når modellen MÆRKET, og mærkningen forbyder at læse dem som
   samtykke.
3. Begge filter-lag er koblet — samme tur og på tværs af ture.
"""
from __future__ import annotations

import ast
import pathlib

from core.services import visible_run_guard_notices as gn


# ── Klasse 3: ud af model-input, bliver hos mennesket ──────────────────────

def test_de_tre_menneske_noter_genkendes():
    """Kendetegnene skal ramme de ægte noter. Gør de ikke, er filteret pynt."""
    for note in (gn.forbindelsen_glippede(),
                 gn.loekken_tvang_en_afslutning(),
                 gn.tool_call_loekke(4)):
        assert gn.er_menneske_note(note) is True, note[:60]


def test_menneske_noterne_filtreres_UD_af_model_input():
    svar = "Her er resultatet af målingen."
    dele = [svar, gn.forbindelsen_glippede(), gn.loekken_tvang_en_afslutning()]
    rene = gn.fjern_menneske_noter(dele)
    assert rene == [svar], rene


def test_listen_selv_roeres_ALDRIG():
    """`_a_parts` persisteres OG bliver model-input. Muterer filteret listen,
    mister Bjørn noten i det gemte svar — og det er den han skal kunne læse."""
    dele = ["svar", gn.loekken_tvang_en_afslutning()]
    foer = list(dele)
    gn.fjern_menneske_noter(dele)
    assert dele == foer, "filteret muterede listen"


def test_et_aegte_svar_filtreres_ikke_vaek():
    """Fail-retningen: bedre at filteret misser end at det spiser et svar."""
    for tekst in ("Jeg har kørt suiten — 17.450 passed.",
                  "Forbindelsen til CT105 virker fint nu.",
                  "Jeg stoppede processen du bad om."):
        assert gn.er_menneske_note(tekst) is False, tekst


def test_en_lang_tekst_er_aldrig_en_note():
    """Længde-vagten, som i `interruption_notice`: en note er kort. Uden den
    kunne et langt svar der tilfældigvis citerer en note blive spist."""
    assert gn.er_menneske_note(gn.forbindelsen_glippede() + "x" * 700) is False


# ── Klasse 1 og 2: når modellen, men MÆRKET ───────────────────────────────

def test_klasse1_noten_filtreres_IKKE_vaek():
    """Bjørn 3/10: «en nødvendighed … fordi deepseek har det med at stoppe uden
    og sende en besked». Den skal nå modellen — ellers dør runnet tavst."""
    note = gn.ingen_tekst_i_runder(3)
    assert gn.er_handler_note(note) is True
    assert gn.er_menneske_note(note) is False
    assert gn.fjern_menneske_noter([note]) == [note]


def test_maerkningen_forbyder_at_laese_beskeden_som_samtykke():
    """Den vigtigste linje, og den der er nemmest at udelade. «Sig til» blev
    læst som om nogen HAVDE sagt til; uden dette forbud kan en systembesked
    blive et «ja»."""
    m = gn.SYSTEM_MAERKE.lower()
    assert "ikke fra bjørn" in m
    assert "ikke en besked fra brugeren" in m
    assert "samtykke" in m


def test_tomt_loefte_advarslen_er_tredje_person_UDEN_invitation():
    """Hele fejlen var en invitation i jeg-form. Advarslen må have ingen af dem."""
    a = gn.tomt_loefte_advarsel()
    assert gn.SYSTEM_MAERKE in a
    assert "sig til" not in a.lower(), a
    assert "ikke en anmodning" in a.lower()
    # Ingen jeg-form om runtimens egen handling.
    assert "jeg lovede" not in a.lower() and "jeg kaldte" not in a.lower()


def test_systemmaerket_paa_tom_tekst_giver_tom_streng():
    assert gn.systemmaerket("") == ""
    assert gn.systemmaerket("   ") == ""


# ── Historik-laget: på tværs af ture ──────────────────────────────────────

def test_noter_fjernes_fra_den_persisterede_historik():
    """Måleresultatet bag hele familien: 45 stubs klumpet 16-8-7-4-2, og da tre
    laa i træk svarede DeepSeek på en almindelig prompt ved at skrive den SAMME
    sætning igen. Modellen efterligner sin egen historik."""
    h = [
        {"role": "user", "content": "kør suiten"},
        {"role": "assistant", "content": gn.loekken_tvang_en_afslutning()},
        {"role": "assistant", "content": "17.450 passed."},
    ]
    ud = gn.fjern_menneske_noter_fra_historik(h)
    assert [m["content"] for m in ud] == ["kør suiten", "17.450 passed."]


def test_en_BRUGER_besked_om_det_samme_bliver_staaende():
    """Skriver Bjørn selv noget om en afbrudt løkke, er det en ægte ytring."""
    h = [{"role": "user", "content": gn.loekken_tvang_en_afslutning()}]
    assert gn.fjern_menneske_noter_fra_historik(h) == h


# ── Koblingen: begge lag ──────────────────────────────────────────────────

def test_begge_filter_lag_er_KOBLET():
    """En vagt ingen kalder er død kode — husets hyppigste mønster.

    Lag 1 (samme tur): `_exchange_text` i visible_runs skal filtrere `_a_parts`
    før `compose_exchange_text`, fordi DEN er næste rundes model-input.
    Lag 2 (på tværs): transcript_sections skal strippe den gemte historik.
    """
    vr = pathlib.Path("core/services/visible_runs.py").read_text()
    for n in ast.walk(ast.parse(vr)):
        if isinstance(n, ast.FunctionDef) and n.name == "_exchange_text":
            t = ast.unparse(n)
            assert "fjern_menneske_noter" in t, "lag 1 filtrerer ikke model-input"
            assert "_vaerns_advarsler" in t, "klasse-2-advarsler naar ikke modellen"
            break
    else:
        raise AssertionError("_exchange_text findes ikke laengere")

    ts = pathlib.Path("core/services/prompt_sections/transcript_sections.py").read_text()
    assert "fjern_menneske_noter_fra_historik" in ts, "lag 2 er ikke koblet"


def test_de_fem_noter_bygges_fra_modulet_og_ikke_som_literaler():
    """Teksten skal stå ÉT sted, ellers kan skriveren og filteret drive fra
    hinanden — og det er præcis hvordan et filter bliver stille virkningsløst.
    Samme begrundelse som `interruption_notice.INTERRUPTION_NOTICE`."""
    vr = pathlib.Path("core/services/visible_runs.py").read_text()
    for forbudt in ("Forbindelsen blev ved med at glippe",
                    "stoppede her fordi løkken tvang",
                    "faldt i et tool-call loop",
                    "rounds without producing text"):
        assert forbudt not in vr, (
            f"note-teksten «{forbudt[:30]}…» står som literal i visible_runs — "
            "den hører i visible_run_guard_notices"
        )
