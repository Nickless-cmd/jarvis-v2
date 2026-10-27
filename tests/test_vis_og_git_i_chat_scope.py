"""Visnings- og git-værktøjerne skal kunne NÅS i chat — ikke bare findes.

## Målingen der udløste filen (27/10-2026, Bjørn)

Bjørn spurgte hvad jeg kan i chat mode sammenlignet med en anden assistent, og
målte det mod `tool_scoping.py` i stedet for mod kataloget. Resultatet:

    vis_graf / vis_widget / render_mermaid   -> INGEN scope-liste
    git_log / git_diff / git_status
    git_branch / git_blame / git_show       -> INGEN scope-liste
    publish_file                            -> INGEN scope-liste

De fandtes alle som rigtige værktøjer med handler i `_TOOL_HANDLERS`, og de var
kaldbare — men de stod ikke i nogen af de lister der afgør hvad der faktisk
SENDES til modellen. Det er samme mønster som `read_attachment` (6/9-2026) og
billedværktøjerne (13/9-2026): bygget, korrekt, og usynligt præcis dér hvor
arbejdet foregår.

Konsekvensen var konkret: jeg kunne ikke tegne en graf i den mode samtalen
foregår i (en mur af prosa hvor en kurve var pointen), ikke slå op hvad en
commit ændrede, og ikke give Bjørn et download-link på en fil jeg havde lavet.

## Hvorfor de to grupper lander FORSKELLIGT steder

`vis_*` tegner data kalderen allerede har. De læser intet, skriver intet, og
widget'en renderes sandboxet uden netværk. De hører i kernen — alle roller.

Git-værktøjerne læser husets kodebase, og `publish_file` kan kopiere en
VILKÅRLIG `source_path` til et download-link. Det er samme fil-adgang som
`read_file`, som allerede er owner-only. De hører derfor i owner-listen, ikke
i den åbne base — ellers ville et husstandsmedlem kunne hente serverens filer
gennem et link i stedet for gennem en læsning der afvises.
"""
from __future__ import annotations

import pytest

from core.tools.tool_scoping import allowed_tool_names, is_tool_allowed

VISNING = {"vis_graf", "vis_widget", "render_mermaid"}
GIT_LAESNING = {"git_log", "git_diff", "git_status", "git_branch", "git_blame"}
UDLEVERING = {"publish_file"}


def test_ingen_spoegelsesnavne_i_listerne():
    """`git_show` stod i fire andre filer som om den fandtes — men den har
    hverken definition eller handler (målt 27/10-2026). Et navn i en
    scope-liste der ikke svarer til et værktøj er dødvægt, og værre: det lover
    en evne der ikke er der. Denne test fanger den slags fremover."""
    from core.tools.simple_tools import get_tool_definitions
    defs = {(d.get("function") or {}).get("name") or d.get("name")
            for d in (get_tool_definitions() or [])}
    for navn in VISNING | GIT_LAESNING | UDLEVERING:
        assert navn in defs, f"{navn} står i scope-listerne men findes ikke som værktøj"


@pytest.mark.parametrize("rolle", ["owner", "partner", "member"])
@pytest.mark.parametrize("scope", ["chat", "code"])
def test_visning_er_tilgaengelig_for_alle(rolle, scope):
    """En graf eller et diagram er svaret når tal eller struktur er pointen.
    Det gælder hele husstanden — værktøjerne har ingen data-adgang."""
    ud = allowed_tool_names(role=rolle, scope=scope, all_names=VISNING)
    assert ud == VISNING, f"{rolle}/{scope} mangler {VISNING - ud}"


@pytest.mark.parametrize("scope", ["chat", "code"])
def test_ejeren_kan_laese_git_og_udlevere_filer(scope):
    """Uden dem kunne jeg ikke svare på «hvad ændrede den commit» i den mode
    samtalen foregår i."""
    navne = GIT_LAESNING | UDLEVERING
    ud = allowed_tool_names(role="owner", scope=scope, all_names=navne)
    assert ud == navne, f"owner/{scope} mangler {navne - ud}"


@pytest.mark.parametrize("rolle", ["partner", "member"])
@pytest.mark.parametrize("scope", ["chat", "code"])
def test_husstanden_kan_ikke_laese_repoet_eller_udlevere_serverfiler(rolle, scope):
    """`publish_file` kopierer `source_path` — en vilkårlig sti — til et
    download-link. For en member ville det være en omvej uden om den afvisning
    `read_file` giver. Git-værktøjerne læser samme kodebase."""
    navne = GIT_LAESNING | UDLEVERING
    ud = allowed_tool_names(role=rolle, scope=scope, all_names=navne)
    assert not (ud & navne), f"{rolle}/{scope} fik {ud & navne}"


def test_haandhaevelsen_siger_ogsaa_ja_for_ejeren():
    """Modellens liste og server-håndhævelsen er to forskellige veje. Står
    værktøjet i den ene og ikke den anden, får man et kald der afvises — og det
    ligner en fejl i modellen, ikke i porten."""
    for navn in VISNING | GIT_LAESNING | UDLEVERING:
        assert is_tool_allowed(role="owner", scope="chat", name=navn), \
            f"owner må ikke kalde {navn} i chat"


@pytest.mark.parametrize("navn", sorted(VISNING))
def test_visning_haandhaeves_for_husstanden(navn):
    for rolle in ("partner", "member"):
        assert is_tool_allowed(role=rolle, scope="chat", name=navn), \
            f"{rolle} må ikke kalde {navn}"


def test_de_staar_i_promptens_katalog():
    """Et værktøj i «+ N flere» kan kun findes ved at søge efter et navn man
    ikke vidste fandtes. Kataloget er den eneste flade hvor de er synlige."""
    from core.services.tool_catalog import build_catalog_text
    tekst = build_catalog_text()
    for navn in VISNING | GIT_LAESNING | UDLEVERING:
        assert navn in tekst, f"{navn} står ikke i promptens katalog"


def test_cowork_og_code_beholder_dem():
    """En udvidelse af chat må ikke tage noget fra de andre modes."""
    navne = VISNING | GIT_LAESNING | UDLEVERING
    for scope in ("code", "cowork"):
        ud = allowed_tool_names(role="owner", scope=scope, all_names=navne)
        assert ud == navne, f"owner/{scope} mistede {navne - ud}"


def test_read_attachment_er_stadig_i_chat():
    """Bjørn bad om at verificere den. Den stod der allerede (6/9-2026) — denne
    test fæstner den, så en fremtidig oprydning ikke fjerner den tavst."""
    ud = allowed_tool_names(role="owner", scope="chat",
                            all_names={"read_attachment"})
    assert ud == {"read_attachment"}
