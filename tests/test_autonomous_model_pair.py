"""Det autonome model-par skal ogsaa tjekkes — 10/9-2026.

`model_pair_resolver.resolve_safe` blev bygget da `ollama/glm-5.2` viste sig at
give 162 tomme svar ud af 162. Men den blev kun koblet paa
`start_visible_run`. Den AUTONOME sti gik udenom — og det er praecis dér de
tomme koersler kom fra.

Fundet fordi afregnings-skyggen blev ved med at melde uenighed paa netop det
par, timer efter «fixet» var deployet. Endnu et tilfaelde af at koden er rigtig
og kun det halve af systemet kalder den.
"""
from __future__ import annotations

import inspect

import core.services.visible_runs as VR


def test_resolveren_er_KATALOG_afhaengig_og_maa_derfor_ikke_afvise_blindt():
    """Svaret afhaenger af hvilken maskine man staar paa.

    CT105 (10/9-2026):  ollama/glm-5.2 → glm-5.2:cloud, ingen indvending
    lokalt:             AFVIST — det lokale katalog har glm-5.1:cloud, ikke 5.2

    Derfor maa koblingen paa den autonome sti ALDRIG afvise: samme par ville
    blive stoppet paa én maskine og oversat paa en anden. Den egenskab testen
    her sikrer, er at et afvist par kommer UAENDRET tilbage — saa det er
    trygt at beholde det.
    """
    from core.services.model_pair_resolver import resolve_safe
    p, m, problem = resolve_safe("ollama", "glm-5.2")
    if problem:
        assert (p, m) == ("ollama", "glm-5.2"), (
            "et afvist par blev aendret — saa er «behold det» ikke trygt")
    else:
        assert p == "ollama" and m.startswith("glm-5.2")


def test_resolveren_kaster_aldrig():
    from core.services.model_pair_resolver import resolve_safe
    for par in [("", ""), ("findes-ikke", "heller-ikke"), ("ollama", "")]:
        ud = resolve_safe(*par)
        assert isinstance(ud, tuple) and len(ud) == 3


def test_den_autonome_sti_spoerger_resolveren():
    kilde = inspect.getsource(VR.start_autonomous_run)
    assert "model_pair_resolver" in kilde, (
        "den autonome sti gaar udenom par-tjekket igen")


def test_den_SYNLIGE_sti_goer_det_fortsat():
    assert "model_pair_resolver" in inspect.getsource(VR.start_visible_run)


def test_et_uafklaret_par_LUKKER_IKKE_autonomt_arbejde():
    """Forskellen fra den synlige sti: her er der ingen at vise en fejl til.
    En tvivl maa ikke stoppe alt autonomt arbejde — den skal siges hoejt."""
    kilde = inspect.getsource(VR.start_autonomous_run)
    i = kilde.index("_problem")
    vindue = kilde[i:i + 600]
    assert "beholder" in vindue, "et uafklaret par ser ud til at afvise"
    assert "logger.warning" in vindue, "tvivlen er tavs"


def test_oversaettelsen_siges_hoejt():
    """Skifter modellen under foedderne paa en koersel, skal det kunne ses i
    journalen bagefter."""
    kilde = inspect.getsource(VR.start_autonomous_run)
    assert "model-par oversat" in kilde
