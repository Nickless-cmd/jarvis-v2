"""Billed-værktøjerne skal kunne NÅS — ikke bare findes.

## Målingen der udløste filen

`openrouter_image` og `openrouter_image_edit` blev bygget 13/9-2026. Målt samme
dag, før denne ændring:

    owner    chat    -> INGEN billedværktøjer
    owner    code    -> INGEN billedværktøjer
    owner    cowork  -> ['openrouter_image', 'openrouter_image_edit']
    partner  alle    -> INGEN

De var altså kun nåbare i den ene mode Bjørn sjældnest arbejder i, og slet ikke
for husstanden. Og de stod ikke i promptens faste værktøjer, så de lå i
«+ N flere værktøjer» — findbare kun ved at søge efter et navn man ikke vidste
fandtes. Et værktøj der kræver at man kender det i forvejen, er ikke
tilgængeligt.

Samme mønster som `read_attachment` i sin tid: et skærmbillede var noget han
kunne modtage og ikke se på.
"""
from __future__ import annotations

import pytest

from core.tools.tool_scoping import allowed_tool_names, is_tool_allowed

BILLEDVAERKTOEJER = {"openrouter_image", "openrouter_image_edit"}


@pytest.mark.parametrize("scope", ["chat", "code"])
def test_ejeren_har_dem_i_baade_chat_og_code(scope):
    """Desk har begge modes, og et diagram hoerer til i arbejdet — ikke i en
    anden fane."""
    ud = allowed_tool_names(role="owner", scope=scope, all_names=BILLEDVAERKTOEJER)
    assert ud == BILLEDVAERKTOEJER, f"{scope} mangler {BILLEDVAERKTOEJER - ud}"


@pytest.mark.parametrize("rolle", ["partner", "member"])
@pytest.mark.parametrize("scope", ["chat", "code"])
def test_husstanden_har_dem_ogsaa(rolle, scope):
    """Bjoern 13/9-2026: «Det er okay alle for dem.»

    BEMÆRK at det koster penge — `openrouter_image` bruger betalingsnoeglen, og
    free-tier-profilen er eksplicit forbudt i vaerktoejet. Det er et bevidst
    valg, ikke en oprydning.
    """
    ud = allowed_tool_names(role=rolle, scope=scope, all_names=BILLEDVAERKTOEJER)
    assert ud == BILLEDVAERKTOEJER, f"{rolle}/{scope} mangler {BILLEDVAERKTOEJER - ud}"


@pytest.mark.parametrize("rolle", ["owner", "partner", "member"])
def test_haandhaevelsen_siger_ogsaa_ja(rolle):
    """Modellens liste og server-haandhaevelsen er to forskellige veje. Staar
    vaerktoejet i den ene og ikke den anden, faar man et kald der afvises — og
    det ligner en fejl i modellen."""
    for navn in BILLEDVAERKTOEJER:
        assert is_tool_allowed(role=rolle, scope="chat", name=navn), \
            f"{rolle} maa ikke kalde {navn}"


def test_discord_er_daekket():
    """Discord-kanalen koerer i `chat` (og `code` for owner) — se
    `DISCORD_CHANNEL_MANIFEST.modes`. Den arver derfor mode-listerne og
    kraever ingen egen aabning."""
    from core.services.channel_inbound import DISCORD_CHANNEL_MANIFEST
    assert set(DISCORD_CHANNEL_MANIFEST.modes) <= {"chat", "code"}
    for mode in DISCORD_CHANNEL_MANIFEST.modes:
        for rolle in ("owner", "partner", "member"):
            ud = allowed_tool_names(role=rolle, scope=mode,
                                    all_names=BILLEDVAERKTOEJER)
            assert ud == BILLEDVAERKTOEJER, f"discord/{mode}/{rolle} mangler dem"


def test_de_staar_i_promptens_FASTE_vaerktoejer():
    """Et vaerktoej i «+ N flere» kan kun findes ved at soege efter et navn man
    ikke vidste fandtes."""
    from core.services.tool_catalog import build_catalog_text
    tekst = build_catalog_text()
    for navn in BILLEDVAERKTOEJER:
        assert navn in tekst, f"{navn} staar ikke i promptens katalog"


def test_read_attachment_overlevede_omdoebningen():
    """Gruppen hed «Syn» og hedder nu «Syn & billeder». En omdoebning der taber
    et vaerktoej er en regression der ligner en oprydning."""
    from core.services.tool_catalog import build_catalog_text
    assert "read_attachment" in build_catalog_text()


def test_cowork_er_uaendret():
    """Ejeren havde dem i cowork foer. Det maa en udvidelse ikke tage fra ham."""
    ud = allowed_tool_names(role="owner", scope="cowork",
                            all_names=BILLEDVAERKTOEJER)
    assert ud == BILLEDVAERKTOEJER
