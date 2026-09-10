"""Raadet taeller nu sine ture — og sikkerhedsnettene virker der. Fase 6.

«depth, child-count, provider, cost, token, time, tool, secret, and workspace
limits are enforced across failover.»

MAALT 10/9-2026 paa produktionen:

    explore-boern     1,0 runs hver (97 boern) — one-shot som designet
    raadsmedlemmer    8,4 runs i snit, op til TI (91 boern)
    turns_completed   hoejst 1 for ALLE 190

Raadet skaber sine runs DIREKTE med `create_agent_run` og gaar uden om
`execute_agent_task` — hvor `turns_completed_delta=1` er det ENESTE sted i
huset turen taelles. Derfor kunne hverken `max_turns` eller budget-tjekket
nogensinde udloese for netop de agenter der koerer flest gange.

Sikkerhedsnettet fandtes altsaa ikke dér hvor det var noedvendigt. Og det er
det net Bjoern valgte at hvile paa i juli, da budgettet blev sat til
ubegraenset for ikke at kvaele agenter midt i opgaven.
"""
from __future__ import annotations

import inspect

from core.services import agent_runtime_council as C


def test_raadet_taeller_turen():
    kilde = inspect.getsource(C)
    assert "turns_completed_delta=1" in kilde, (
        "raadet taeller stadig ikke sine ture — max_turns kan ikke udloese")


def test_raadet_koerer_BEGGE_graense_tjek():
    kilde = inspect.getsource(C)
    assert "_check_max_turns_and_expire" in kilde
    assert "_check_budget_and_expire" in kilde


def test_tjekkene_ligger_EFTER_at_turen_er_taalt():
    """Ellers ville loftet blive maalt mod et tal der endnu ikke var opdateret,
    og altid vaere én tur bagud."""
    kilde = inspect.getsource(C)
    i_tael = kilde.index("turns_completed_delta=1")
    i_tjek = kilde.index("_check_max_turns_and_expire")
    assert i_tael < i_tjek


def test_et_kollapset_tjek_stopper_ikke_raadet():
    """En debat maa ikke doe fordi et graense-tjek fejlede.

    (Foerste udgave af testen brugte `.index()`, som fandt IMPORT-linjen og
    ikke kaldet — vinduet naaede derfor aldrig frem til vagten. Nu ledes der
    efter selve advarslen, som kun findes ét sted.)
    """
    kilde = inspect.getsource(C)
    assert "raad: kunne ikke koere graense-tjek" in kilde
    i_kald = kilde.rindex("_check_max_turns_and_expire(agent_id)")
    hale = kilde[i_kald:i_kald + 400]
    assert "except Exception" in hale, "graense-tjekket er uden vagt"


def test_budget_tjekket_er_et_NO_OP_for_raadet(isolated_runtime, monkeypatch):
    """Alle 93 raadsmedlemmer har budget 0 = ubegraenset, saa tjekket kan ikke
    kvaele en debat. Det var praecis den fejl der kostede en dag i juli:
    et lille budget gav «completed men tomt».
    """
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    from core.services.agent_runtime_spawn import _check_budget_and_expire

    create_agent_registry_entry(agent_id="raad-1", role="filosof",
                                budget_tokens=0, council_id="c1")
    assert _check_budget_and_expire("raad-1", tokens_used=999_999) is False


def test_tur_loftet_ER_et_aegte_net(isolated_runtime):
    """Det bider ikke i dag — hoejeste maalte er ti runder mod et loft paa 20 —
    men det skal kunne bide."""
    from core.runtime.db_agent_runtime import (
        create_agent_registry_entry, update_agent_registry_entry,
    )
    from core.services.agent_runtime_spawn import _check_max_turns_and_expire

    create_agent_registry_entry(agent_id="raad-2", role="filosof",
                                max_turns=3, council_id="c1")
    update_agent_registry_entry("raad-2", turns_completed_delta=3)
    assert _check_max_turns_and_expire("raad-2") is True
