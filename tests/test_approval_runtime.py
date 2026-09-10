"""Én doer ind og ud af en godkendelse — Fase 4's sidste stykke.

MAALT foer snittet blev lagt, ikke antaget:

  beslutningen  ALLEREDE samlet — tre svarere, én `resolve_pending_approval`
  kortet        bygget i HAANDEN fire steder
  udloebet      tjekket to steder (ved svar, ved opstart), aldrig fejet

Kortet var det spredte. Hver gang Fase 4 tilfoejede et felt — ejer, tidsstempel,
digest — skulle det tilfoejes fire gange, og en glemt kopi ville have vaeret et
stille hul. Det moenster kostede en ekstra runde tre gange paa én dag.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.services import approval_runtime as AR


@pytest.fixture
def run():
    return SimpleNamespace(run_id="r1", session_id="s1", user_id="bjorn",
                           autonomous=False)


# ── ét sted der ved hvordan et gyldigt kort ser ud ───────────────────────

def test_kortet_har_ALLE_paakraevede_felter(isolated_runtime, run):
    kort = AR.build_request(tool_name="bash", arguments={"command": "ls"},
                            result={"status": "approval_needed"}, run=run)
    mangler = [f for f in AR.PAAKRAEVEDE if f not in kort]
    assert mangler == [], mangler


def test_digesten_daekker_det_FAKTISKE_kald(isolated_runtime, run):
    import core.services.visible_runs as VR
    kort = AR.build_request(tool_name="bash", arguments={"command": "ls"},
                            result={}, run=run)
    assert kort["invocation_digest"] == VR._kald_digest("bash", {"command": "ls"})


def test_ejeren_kommer_fra_koerslen(isolated_runtime, run):
    kort = AR.build_request(tool_name="bash", arguments={}, result={}, run=run)
    assert kort["owner_user_id"] == "bjorn"


def test_created_at_kan_gives_men_udfyldes_ellers(isolated_runtime, run):
    assert AR.build_request(tool_name="b", arguments={}, result={}, run=run,
                            created_at="2026-01-01T00:00:00+00:00")["created_at"] \
        == "2026-01-01T00:00:00+00:00"
    assert AR.build_request(tool_name="b", arguments={}, result={},
                            run=run)["created_at"].startswith("20")


def test_ALLE_fire_kort_steder_gaar_gennem_byggeren():
    """Den test der ville have sparet tre ekstra runder.

    Bygger et sted sit eget kort igen, mangler det naeste felt Fase 5 finder
    paa — og hullet er stille.
    """
    import inspect
    import core.services.visible_runs as VR
    kilde = inspect.getsource(VR)
    assert kilde.count("_ar.build_request(") == 4, (
        "et kort-sted bygger sit eget igen")
    # og ingen bygger den gamle form i haanden
    assert '"invocation_digest": _kald_digest(' not in kilde


def test_id_erne_er_unikke():
    assert AR.new_id() != AR.new_id()
    assert AR.new_id().startswith("approval-")


# ── beslutningen gaar samme vej som foer ─────────────────────────────────

def test_decide_delegerer_til_den_doer_der_har_vagterne(isolated_runtime,
                                                        monkeypatch):
    """Udloeb, ejerskab, digest og den atomiske overtagelse ligger dér. At
    flytte dem ville vaere at bygge den mest konsekvenstunge sti om uden en
    fejl at rette."""
    import core.services.visible_runs_approvals as A
    set_af = []
    monkeypatch.setattr(A, "resolve_pending_approval",
                        lambda aid, **kw: set_af.append((aid, kw)) or {"status": "ok"})
    AR.decide("a1", approved=True, answered_by="bjorn")
    assert set_af == [("a1", {"approved": True, "answered_by": "bjorn"})]


# ── fejningen der manglede ───────────────────────────────────────────────

def _laeg(navn: str, alder_s: float, run) -> None:
    from datetime import UTC, datetime, timedelta
    import core.services.visible_runs as VR
    kort = AR.build_request(tool_name="bash", arguments={"command": navn},
                            result={}, run=run)
    kort["created_at"] = (datetime.now(UTC)
                          - timedelta(seconds=alder_s)).isoformat()
    VR._PENDING_APPROVALS[navn] = kort


def test_fejningen_fjerner_kun_de_UDLOEBNE(isolated_runtime, run):
    import core.services.visible_runs as VR
    VR._PENDING_APPROVALS.clear()
    _laeg("frisk", 60, run)
    _laeg("gammel", 11 * 86400, run)

    ud = AR.sweep_expired()
    assert ud["fejet"] == 1 and ud["tilbage"] == 1
    assert set(VR._PENDING_APPROVALS) == {"frisk"}


def test_fejningen_paa_et_tomt_lager_er_stille(isolated_runtime):
    import core.services.visible_runs as VR
    VR._PENDING_APPROVALS.clear()
    assert AR.sweep_expired() == {"fejet": 0, "tilbage": 0}


def test_fejningen_kaster_aldrig(isolated_runtime, monkeypatch):
    import core.services.visible_runs as VR
    monkeypatch.setattr(VR, "_PENDING_APPROVALS", "ikke en dict")
    assert AR.sweep_expired()["fejet"] == 0


# ── og at man kan spoerge om et kort ─────────────────────────────────────

def test_state_finder_kortet_i_hukommelsen(isolated_runtime, run):
    import core.services.visible_runs as VR
    VR._PENDING_APPROVALS["a"] = AR.build_request(
        tool_name="bash", arguments={}, result={}, run=run)
    assert AR.state("a")["tool_name"] == "bash"


def test_state_paa_et_ukendt_kort_er_None(isolated_runtime):
    assert AR.state("findes-ikke") is None
