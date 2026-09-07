"""Operator-filskrivning skal have samme port som den lokale.

Fundet 7/9-2026 under gate-kortlægningen: `operator_write_file` og
`operator_edit_file` havde en read-before-write-vagt, men hverken
spærret-sti-tjek eller godkendelseskort. Broen skrev direkte:

    writeFileSync(path, content, 'utf8')

Broens egen `approvalRace` er død kode — godkendelserne blev flyttet til
chat-kort for SEKS værktøjer 28/5, og de to filværktøjer fulgte ikke med.

Broen kører på operatørens egen maskine, så det var ikke en vej ind til
Bjørn. Men Mikkel, der bruger desk-appen med operator-sættet, havde ubetinget
filskrivning på sin — uden at nogen havde besluttet det.
"""

from __future__ import annotations

import pytest

from core.tools import simple_tools_operator as O

BLOKERET = "/home/bs/.ssh/id_rsa"
UDENFOR = "/home/mikkel/noter.md"
WORKSPACE = "/media/projects/jarvis-v2/noget.txt"


@pytest.mark.parametrize("kind", ["write", "edit"])
def test_spaerret_sti_afvises(kind):
    """Den lokale write_file afviser ~/.ssh/id_rsa. Operator-varianten gjorde ikke.

    Gaten er mønster-baseret, så den virker også på en fjern sti — filen
    behøver ikke ligge på denne maskine for at blive dømt.
    """
    r = O._sti_gate_operator(BLOKERET, {}, kind=kind, tool="operator_write_file")
    assert r is not None and r["status"] == "blocked"


@pytest.mark.parametrize("kind", ["write", "edit"])
def test_uden_for_workspacet_kraever_godkendelse(kind):
    r = O._sti_gate_operator(UDENFOR, {}, kind=kind, tool="operator_write_file")
    assert r is not None and r["status"] == "approval_needed"
    # Kortet skal baere stien, ellers godkender man noget man ikke kan se.
    assert UDENFOR in r["message"]


def test_workspace_stier_giver_INGEN_kort():
    """Ellers ville hver eneste skrivning i kodetilstand kræve et klik.

    Samme dom som den lokale write_file giver: workspace er `auto`.
    """
    assert O._sti_gate_operator(WORKSPACE, {}, kind="write", tool="operator_write_file") is None


def test_godkendt_kald_slipper_igennem():
    """`_runtime_trust_all` sættes af force-handleren efter Bjørn har klikket.

    Uden det ramte kaldet sin egen gate igen og svarede approval_needed på ny —
    den løkke vi allerede har haft to udgaver af i dag.
    """
    r = O._sti_gate_operator(UDENFOR, {"_runtime_trust_all": True},
                             kind="write", tool="operator_write_file")
    assert r is None


def test_en_spaerret_sti_aabnes_IKKE_af_trust():
    """Trust springer godkendelsen over — aldrig sikkerheden."""
    r = O._sti_gate_operator(BLOKERET, {"_runtime_trust_all": True},
                             kind="write", tool="operator_write_file")
    assert r is not None and r["status"] == "blocked"


def test_begge_har_en_force_handler():
    """Ellers løber godkendelsen i ring — invarianten i
    test_approval_har_force_handler.py dækker det generelt, men de to er nye
    og værd at nævne ved navn."""
    from core.tools.simple_tools import _FORCE_HANDLERS

    assert "operator_write_file" in _FORCE_HANDLERS
    assert "operator_edit_file" in _FORCE_HANDLERS


def test_gaten_ligger_FOER_read_before_write_vagten():
    """En spærret sti skal afvises uanset om filen er læst i sessionen.

    Lå gaten efter vagten, kunne man læse ~/.ssh/id_rsa og derefter skrive til
    den — vagten ville være tilfreds, og sti-gaten ville aldrig blive spurgt.
    """
    import inspect

    kilde = inspect.getsource(O._exec_operator_write_file)
    assert kilde.index("_sti_gate_operator") < kilde.index("read-before-write")
