"""Genoptagelsen der er OPGIVET — den maa ikke staa som «i gang».

Maalt 3/10-2026: 13 poster i én samtale stod som `recovering` med
`recovery_attempt=3` / `recovery_limit=3` og `exit_reason="shutdown"`.
Budgettet var brugt op — de kunne ALDRIG genoptages. Men `recovery_snapshot`
laeste raa status fra disken og tilboed dem for EVIGT, med loeftet
«checkpointet er bevaret til genoptagelse».

Banneret stod over composeren ved HVER afsluttet tur: klienten spoerger igen
hver gang en tur slutter, og `_kvitter_varsel` ramte kun `failed_terminal` —
saa en `recovering`-post blev aldrig brugt op.

Policy-laget (`visible_terminal_policy.decide_terminal`) og dispatcheren
(`claim_due_recovery`) vidste det hele tiden: forsoeg >= loft betyder
FAILED_TERMINAL. De skrev bare aldrig status-feltet om.
"""
from __future__ import annotations

import pytest

from core.services import in_flight_runs as ifr


@pytest.fixture(autouse=True)
def _isolerede_poster(monkeypatch):
    poster: dict[str, dict] = {}
    monkeypatch.setattr(ifr, "_load", lambda: {k: dict(v) for k, v in poster.items()})
    monkeypatch.setattr(
        ifr, "_save",
        lambda v: (poster.clear(), poster.update({k: dict(x) for k, x in v.items()})),
    )
    monkeypatch.setattr(ifr, "owner_still_alive", lambda owner: False)
    return poster


def _braend_budgettet(run_id: str) -> None:
    """Saet forsoegs-taelleren op paa loftet — praecis som dispatcheren goer."""
    poster = ifr._load()
    noegle = ifr._record_key(poster, run_id)
    assert noegle is not None, f"ukendt post: {run_id}"
    poster[noegle]["recovery_attempt"] = int(poster[noegle]["recovery_limit"])
    ifr._save(poster)


def test_en_opbrugt_genoptagelse_er_opgivet_ikke_i_gang():
    ifr.mark_started(run_id="r1", session_id="s1", user_message="ret cheap lane")
    ifr.settle_recovering("r1", reason="shutdown", summary="ret cheap lane")
    _braend_budgettet("r1")

    snap = ifr.recovery_snapshot("s1")
    assert snap is not None, "en opgivet opgave maa ikke forsvinde tavst"
    assert snap["state"] == "failed_terminal"
    assert snap["notice"]["continuing"] is False
    # Loefte maa ikke staa paa noget der er opgivet — han skal have det raad
    # der virker i stedet: skriv den igen.
    assert "Skriv den igen" in snap["notice"]["message"]
    assert "bevaret" not in snap["notice"]["message"]


def test_en_opbrugt_genoptagelse_siges_praecis_en_gang():
    """Ellers staar banneret der ved hver afsluttet tur — for evigt."""
    ifr.mark_started(run_id="r1", session_id="s1", user_message="x")
    ifr.settle_recovering("r1", reason="shutdown")
    _braend_budgettet("r1")

    assert ifr.recovery_snapshot("s1") is not None
    assert ifr.recovery_snapshot("s1") is None


def test_en_genoptagelse_med_budget_tilbage_er_stadig_i_gang():
    """Vaernet mod at slukke varslet for alt det der FAKTISK fortsaetter."""
    ifr.mark_started(run_id="r1", session_id="s1", user_message="x")
    ifr.settle_recovering("r1", reason="shutdown")

    snap = ifr.recovery_snapshot("s1")
    assert snap is not None
    assert snap["state"] == "recovering"
    assert snap["notice"]["continuing"] is True


def test_alle_opbrugte_i_samtalen_lukkes_men_kun_den_nyeste_varsles():
    """Tretten draebte forsoeg er ÉN begivenhed — ikke tretten bannere."""
    for i in range(3):
        ifr.mark_started(run_id=f"r{i}", session_id="s1", user_message="x")
        ifr.settle_recovering(f"r{i}", reason="shutdown")
        _braend_budgettet(f"r{i}")

    assert ifr.recovery_snapshot("s1") is not None

    # Ingen af dem staar tilbage som «i gang»: de kan ikke genoptages.
    tilbage = [
        v for v in ifr._load().values() if v.get("status") == "recovering"
    ]
    assert tilbage == [], f"opbrugte poster stod stadig som i gang: {tilbage}"
    # ... og der kommer ikke et banner mere.
    assert ifr.recovery_snapshot("s1") is None


def test_et_helt_almindeligt_run_roeres_ikke():
    ifr.mark_started(run_id="r1", session_id="s1", user_message="x")
    assert ifr.recovery_snapshot("s1") is None
    assert ifr.get_record("r1")["status"] == "running"
