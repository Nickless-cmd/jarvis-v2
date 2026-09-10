"""Et barn maa ikke laane foraeldrens autoritet — Fase 5.

«child authority/profile/tool scope is frozen before publication, cannot
import ambient parent authority.»

MAALT 10/9-2026: `spawn_agent_task` kalder `execute_agent_task` INLINE — ingen
traad, ingen `contextvars.copy_context()` — saa barnet koerer i foraeldrens
kontekst og ser alle ambiente ContextVars.

Ikke udnytteligt i dag: `owner_approval` saettes kun under ét godkendt
vaerktoejskald og nulstilles i `finally`, og ingen af de nitten
godkendelses-kraevende vaerktoejer spawner agenter. Vinduet findes ikke.

Men invarianten skal holde naar det naeste vaerktoej tilfoejes. En arv der er
utilsigtet men harmloes bliver farlig i det oejeblik nogen kobler de to ting
sammen — og saa vil ingen huske at kigge her.
"""
from __future__ import annotations

import pytest

from core.services import run_autonomy_context as RA
from core.services.child_authority import uden_foraeldrens_godkendelse
from core.tools import owner_approval as OA


# ── den ene autoritet der IKKE arves ─────────────────────────────────────

def test_barnet_arver_IKKE_ejer_godkendelsen():
    """«Et menneske sagde ja til DEN HER handling» gaelder kaldet, ikke alt
    hvad kaldet maatte finde paa at starte."""
    t = OA._ejer_godkendt.set(True)
    try:
        with uden_foraeldrens_godkendelse():
            assert OA.er_ejer_godkendt() is False
    finally:
        OA._ejer_godkendt.reset(t)


def test_foraeldrens_egen_godkendelse_overlever_barnet():
    """Kaldet er ikke faerdigt fordi et barn var forbi."""
    t = OA._ejer_godkendt.set(True)
    try:
        with uden_foraeldrens_godkendelse():
            pass
        assert OA.er_ejer_godkendt() is True
    finally:
        OA._ejer_godkendt.reset(t)


def test_den_nulstiller_ogsaa_naar_barnet_KASTER():
    t = OA._ejer_godkendt.set(True)
    try:
        with pytest.raises(ValueError):
            with uden_foraeldrens_godkendelse():
                raise ValueError("barnet fejlede")
        assert OA.er_ejer_godkendt() is True
    finally:
        OA._ejer_godkendt.reset(t)


def test_uden_godkendelse_i_forvejen_er_den_et_no_op():
    assert OA.er_ejer_godkendt() is False
    with uden_foraeldrens_godkendelse():
        assert OA.er_ejer_godkendt() is False
    assert OA.er_ejer_godkendt() is False


# ── og de tre der MED VILJE bevares ──────────────────────────────────────

def test_autonomien_BEVARES():
    """Et barn af en uovervaaget koersel ER uovervaaget. At rydde det ville
    give barnet en frihed foraeldren ikke havde — stik modsat af hensigten."""
    t = RA.set_autonomous(True)
    try:
        with uden_foraeldrens_godkendelse():
            assert RA.is_autonomous() is True
    finally:
        RA.reset_autonomous(t)


def test_vaerktoejs_scope_BEVARES():
    """Explore mod en workstation hviler paa det; ryddede vi det, holdt den op
    med at virke."""
    from core.tools import tool_scoping as TS
    t = TS._scope_var.set("code")
    try:
        with uden_foraeldrens_godkendelse():
            assert TS.current_tool_scope() == "code"
    finally:
        TS._scope_var.reset(t)


# ── koblingen ────────────────────────────────────────────────────────────

def test_barnets_udfoerelse_gaar_gennem_graensen():
    """Uden koblingen er graensen bare en fil."""
    import inspect
    from core.services import agent_runtime_spawn as S
    kilde = inspect.getsource(S.execute_agent_task)
    assert "uden_foraeldrens_godkendelse()" in kilde
    assert "_execute_agent_task_impl" in kilde


def test_et_AEGTE_barn_ser_ingen_ejer_godkendelse(isolated_runtime, monkeypatch):
    """Hele vejen igennem, ikke bare context-manageren."""
    from core.services import agent_runtime_spawn as S
    set_af = {}
    monkeypatch.setattr(S, "_execute_agent_task_impl",
                        lambda **kw: set_af.update(
                            ejer=OA.er_ejer_godkendt()) or {"status": "ok"})
    t = OA._ejer_godkendt.set(True)
    try:
        S.execute_agent_task(agent_id="a1")
    finally:
        OA._ejer_godkendt.reset(t)
    assert set_af == {"ejer": False}
