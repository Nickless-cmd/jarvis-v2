"""DSML-lækagen i den SYNLIGE første-pas-vej.

MÅLT 30/10-2026 (Bjørn): «nu leaker du osse». Besked 236732 i chat_messages
sluttede med rå DeepSeek-tokens:

    </parameter>
    <parameter name="title">…</parameter>
    </invoke>
    </｜｜DSML｜｜ parameter>
    </｜｜DSML｜｜ invoke>
    </｜｜DSML｜｜ calls>

Stripperen FINDES (`cheap_provider_runtime_adapters._strip_dsml_leak`) og er
koblet på TRE veje: `cheap_provider_runtime_streaming`, `visible_followup_adapters`
og `cheap_provider_runtime`. Men den vej Bjørns EGEN tur kører —
`visible_runs.py` — har nul kald. Den har `FirstPassOutputFilter`, som dækker
capability-markup og runtime-markører, men ikke DSML.

Reproduceret mod den levende funktion før fixet: 5 DSML-tokens gik uhindret
igennem. Det er ikke en model-fejl alene — modellen spilder sin DSL, og
runtime har allerede et værn der fanger det. Værnet var blot ikke koblet på
den vej der vises for mennesket.
"""
from __future__ import annotations

from core.services.visible_first_pass_output import FirstPassOutputFilter

# Den faktiske form fra besked 236732 — inkl. den halve åbner der opstod
# fordi modellen skrev `</parameter>` som rå tekst.
_LAEKAGE = (
    "Jeg gemmer i hukommelsen og skriver overdragelsen.\n"
    '<｜｜DSML｜｜ invoke name="remember_this">\n'
    '<｜｜DSML｜｜ parameter name="content">tekst</｜｜DSML｜｜ parameter>\n'
    "</｜｜DSML｜｜ invoke>\n"
    "</｜｜DSML｜｜ calls>"
)


def _koer(tekst: str) -> str:
    f = FirstPassOutputFilter()
    return f.feed(tekst) + f.flush()


def test_dsml_blok_naar_ikke_frem_til_mennesket() -> None:
    """Hele DSML-blokken skal væk — ikke bare gøres pænere."""
    ud = _koer(_LAEKAGE)
    assert "DSML" not in ud, ud
    assert "｜｜" not in ud, ud


def test_den_rigtige_prosa_overlever() -> None:
    """Teksten FØR blokken er svaret og må ikke forsvinde med den."""
    ud = _koer(_LAEKAGE)
    assert "Jeg gemmer i hukommelsen og skriver overdragelsen." in ud, ud


def test_dsml_midt_i_teksten_fjernes_og_resten_bliver() -> None:
    """Blokken kan stå mellem to sætninger — halen efter må ikke ædes."""
    tekst = (
        "Første del af svaret.\n"
        '<｜｜DSML｜｜ calls>\n<｜｜DSML｜｜ invoke name="bash">x</｜｜DSML｜｜ invoke>\n'
        "</｜｜DSML｜｜ calls>\n"
        "Anden del af svaret."
    )
    ud = _koer(tekst)
    assert "DSML" not in ud, ud
    assert "Første del af svaret." in ud, ud
    assert "Anden del af svaret." in ud, ud


def test_uafsluttet_blok_holder_hale_tilbage_og_skylles_tom() -> None:
    """Streaming: åbneren kan komme før closeren. Halen må ikke lække ved flush."""
    f = FirstPassOutputFilter()
    ud1 = f.feed("Svaret er her.\n<｜｜DSML｜｜ calls>\n<｜｜DSML｜｜ invoke name=\"bash\">")
    ud2 = f.flush()
    samlet = ud1 + ud2
    assert "DSML" not in samlet, samlet
    assert "Svaret er her." in samlet, samlet


def test_almindelig_tekst_med_pipe_roeres_ikke() -> None:
    """Værnet må ikke blive en bred regex der æder normal tekst."""
    tekst = "Kør `ls | grep x` og se på a || b — det er skævt."
    assert _koer(tekst) == tekst


def test_den_halve_form_beholder_indholdet_og_draeber_tagene() -> None:
    """Den halve DSL-form: navnet og tag'ene væk — argumentet skal blive.

    Målt 30/10-2026 på besked 236732: formen omsluttede et helt gyldigt argument
    (en 4.500-tegns hukommelsespost). At fjerne HELE blokken ville kaste indholdet
    væk; det er markup'en der er lækagen, ikke teksten. Testen kræver begge dele:
    intet `</invoke>` tilbage, og argumentet stadig til stede.
    """
    tekst = (
        "Nu gemmer jeg.\n"
        '[remember_this">\n'
        '<parameter name="content">Bjørn: «dine 2 ture er kollideret».</parameter>\n'
        '<parameter name="title">Kollision</parameter>\n'
        "</invoke>"
    )
    ud = _koer(tekst)
    assert "</invoke>" not in ud, ud
    assert "<parameter" not in ud, ud
    assert "Nu gemmer jeg." in ud, ud
    # Indholdet — det der faktisk betyder noget — må ikke forsvinde med tag'ene.
    assert "Bjørn: «dine 2 ture er kollideret»" in ud, ud
    assert "Kollision" in ud, ud
