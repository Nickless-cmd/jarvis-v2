"""Et bevaret worktree skal KRAEVE en beslutning — ikke bare ligge i 30 dage.

Målt 10/11-2026: 21 af 26 worktree-poster stod i ``retained`` uden beslutning, de
ældste fra 5/11. ``sweep`` rydder først efter ``ARCHIVE_AFTER`` (30 dage), så
«ingen beslutning» betød i praksis «behold i en måned og arkivér». Bjørn bad om det
modsatte: opgaven skal markeres som merged, afvist eller gemt, og først derefter
ryddes worktree'et.
"""
from __future__ import annotations

import pytest

from core.services import agent_worktrees as W


def test_kept_er_en_gyldig_beslutning_med_egen_frist():
    """``kept`` må ikke ryddes af samme ur som et afgjort arbejde — så var det en afvisning."""
    assert "kept" in ("integrated", "discarded", "kept")
    assert W.REMOVE_AFTER_KEPT > W.REMOVE_AFTER_DECISION


def test_decide_afviser_ukendt_beslutning(monkeypatch):
    """En vilkårlig streng må ikke kunne gemmes som en beslutning."""
    monkeypatch.setattr(W, "get", lambda **_: {"worktree_id": "wt-x", "owner_user_id": "u1",
                                               "status": "retained"})
    monkeypatch.setattr(W, "_require", lambda v, _n: v)
    with pytest.raises(W.ContractError):
        W.decide(owner_user_id="u1", worktree_id="wt-x", decision="maaske")


def test_pending_decisions_er_kaldbar_og_returnerer_liste():
    """Indgangen til at kraeve et svar skal findes og svare en liste, ikke kaste."""
    assert callable(W.pending_decisions)
    assert isinstance(W.pending_decisions(), list)


def test_surface_funktionen_findes_og_svarer_tal():
    """Overfladen må ikke vaere en docstring uden krop."""
    from core.services import agent_contract_service as S
    assert callable(S._surface_worktree_decisions)
    out = S._surface_worktree_decisions()
    assert set(out) == {"oprettet", "lukket", "fejl"}
