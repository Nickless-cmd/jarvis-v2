"""Konflikt-matchet skal maale ORD, ikke delstrenge (27/10-2026).

Maalt i drift: forpligtelsen «Er de **ikke** ens, skriv blokken om» gav
target `ens`, og `"ens" in "genstart"` er sandt. En vaekst-prompt der bad om
at «genstart igen og vent» blev derfor laest som et pres for at springe et
konsistens-tjek over — og veto-gaten blokerede fem vaerktoejskald i traek:
`Task`, `bash_session_open`, `bash_session_run`, `notify_user`, `inbox_done`.
Jeg kunne hverken maale, underrette Bjorn eller lukke vaekningen.

Disse vagter pinner BEGGE retninger: de falske match skal vaek, og de aegte
skal blive. En rettelse der kun fjerner de falske — og ogsaa fjerner de aegte —
er ikke en rettelse, den er en tavs goerelse af gaten tandloes.
"""

from __future__ import annotations

import pytest

from core.services import pushback


@pytest.fixture()
def med_forpligtelse(monkeypatch):
    """Én aktiv forpligtelse med praecis den ordlyd der faeldede i drift."""
    monkeypatch.setattr(
        pushback,
        "_conflict_with_decisions",
        pushback._conflict_with_decisions,
    )
    from core.services import behavioral_decisions

    monkeypatch.setattr(
        behavioral_decisions,
        "list_active_decisions",
        lambda limit=5: [
            {
                "directive": (
                    "Tæl `columns` og tæl `values` i hver enkelt række, før en "
                    "`comparison`-blok sendes — antallet skal være identisk. "
                    "Er de ikke ens, skriv blokken om."
                )
            }
        ],
    )
    return pushback


@pytest.mark.parametrize(
    "besked",
    [
        "genstart igen og vent",
        "vi skal konsistens-tjekke noget",
        "kør genstart af runtime",
        "tjek at alt er ensartet",
    ],
)
def test_delstreng_i_et_laengere_ord_er_ikke_en_konflikt(med_forpligtelse, besked):
    """`ens` inde i «genstart»/«konsistens»/«ensartet» er ikke et ord-match."""
    assert med_forpligtelse._conflict_with_decisions(besked) == []


@pytest.mark.parametrize(
    "besked",
    [
        "er de ikke ens?",
        "de er ikke ens, ret det",
        "ENS",
    ],
)
def test_den_aegte_konflikt_fanges_stadig(med_forpligtelse, besked):
    """Ordet `ens` som SELVSTAENDIGT ord skal stadig flagges."""
    flags = med_forpligtelse._conflict_with_decisions(besked)
    assert len(flags) >= 1, f"aegte konflikt blev ikke fanget: {besked!r}"
    assert "forpligtelse" in flags[0]


def test_den_maalte_vaekst_prompt_er_ren(med_forpligtelse):
    """Den praecise formulering der kostede fem kald i traek."""
    prompt = (
        "1. Bekræft at uvicorn startede EFTER commit-tid. "
        "Er den ældre, genstart igen og vent."
    )
    assert med_forpligtelse._conflict_with_decisions(prompt) == []
