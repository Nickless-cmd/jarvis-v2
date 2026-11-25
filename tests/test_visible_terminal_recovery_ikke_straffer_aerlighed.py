import pytest

from core.services.visible_run_terminal_recovery import has_incompletion_evidence


@pytest.mark.parametrize(
    "final_text",
    [
        "ikke noget jeg påstår er færdigt",
        "ikke fordi jeg var færdig",
        "ikke løst",
        "aldrig afsluttet",
        "ikke** verificeret",
        "Ikke verificeret",
        "ikke git — de er verificeret",
        "ikke har løst",
    ],
)
def test_aerlig_begraensning_er_ikke_uafsluttethed(final_text):
    assert has_incompletion_evidence(final_text) is False


def test_aerlig_begraensning_i_markdown_overskrift_er_ikke_uafsluttethed():
    assert has_incompletion_evidence("## Det jeg ikke har løst") is False


@pytest.mark.parametrize(
    "final_text",
    [
        "Jeg samler nu de sidste tal",
        "jeg fortsætter nu med fixet",
        "Jeg er ikke færdig med at undersøge det",
        "Vi er ikke færdige her.",
    ],
)
def test_aegte_foerstepersons_uafsluttethed_fanges(final_text):
    assert has_incompletion_evidence(final_text) is True
