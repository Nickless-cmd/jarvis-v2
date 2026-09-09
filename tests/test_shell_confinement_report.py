"""Hver shell-sti skal SIGE om den er indespaerret — Fase 3, K10.

Maalt 9/9-2026: kun ÉN af fire shell-indgange sagde noget som helst. `bash`
rapporterede paa begge sine grene; `bash_session_run`, `operator_bash` og
`operator_bash_session_run` rapporterede INTET — og alle tre kan modellen
kalde DIREKTE, altsaa uden om det ene sted der rapporterede. En taendt sandkasse
saa derfor ud som om den daekkede alle shell-veje.

Politikken er UAENDRET. Den vedvarende shell indespaerres ikke, og
operator-kanalen lukkes ikke ned — begge er Bjoerns vej udenom systemet og
staar urort efter hans staaende instruks. Det der lukkes er at de TIER.
"""
from __future__ import annotations

import pytest

from core.services import bash_sandbox as SB
from core.services import shell_confinement_report as R


@pytest.fixture
def taendt(monkeypatch):
    monkeypatch.setattr(SB, "is_enabled", lambda: True)
    monkeypatch.setattr(SB, "is_available", lambda: True)


# ── rapporten selv ───────────────────────────────────────────────────────

def test_slukket_sandkasse_giver_INGEN_rapport(monkeypatch):
    """«Ikke indespaerret» er ikke en oplysning naar ingen bad om det — det er
    standarden. Rapporten findes for naar nogen TROR den er daekket."""
    monkeypatch.setattr(SB, "is_enabled", lambda: False)
    assert R.rapport(R.VEDVARENDE) is None


def test_taendt_sandkasse_siger_at_stien_IKKE_er_daekket(taendt):
    r = R.rapport(R.VEDVARENDE)
    assert r["requested"] is True and r["actual"] is False
    assert r["honored"] is False and "kan ikke indespaerres" in r["reason"]


def test_operator_grunden_siger_HVORFOR(taendt):
    """Containerens bwrap siger intet om Bjoerns egen maskine. At rapportere
    «indespaerret» ville vaere forkert; at tie ville vaere vaerre."""
    assert "operatorens egen maskine" in R.rapport(R.OPERATOR)["reason"]


def test_en_eksisterende_rapport_overskrives_ikke(taendt):
    assert R.vedhaeft({"confinement": "min egen"}, R.OPERATOR)["confinement"] == "min egen"


@pytest.mark.parametrize("svar", [None, "tekst", 42, []])
def test_et_ikke_dict_svar_roeres_ikke(taendt, svar):
    assert R.vedhaeft(svar, R.OPERATOR) is svar


def test_den_kaster_aldrig(monkeypatch):
    """En rapport maa ikke kunne vaelte den shell den beskriver."""
    monkeypatch.setattr(SB, "is_enabled",
                        lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    assert R.vedhaeft({"status": "ok"}, R.OPERATOR) == {"status": "ok"}


# ── og at de tre stier faktisk bruger den ────────────────────────────────

def test_bash_session_run_rapporterer(taendt, monkeypatch):
    from core.tools import bash_session as BS
    monkeypatch.setattr(BS, "_client_call", lambda *a, **k: {"status": "ok"})
    svar = BS._exec_bash_session_run({"session_id": "s1", "command": "ls"})
    assert svar["confinement"]["honored"] is False
    assert "vedvarende" in svar["confinement"]["reason"]


def test_operator_bash_session_run_rapporterer(taendt, monkeypatch):
    import core.tools.operator_bash_session as OBS
    monkeypatch.setattr(OBS, "_SESSIONS", {"s1": {"cwd": "/", "last": 0,
                                                  "user_id": "u"}}, raising=False)
    import inspect
    assert "vedhaeft(res, OPERATOR)" in inspect.getsource(OBS._exec_operator_bash_session_run)


def test_operator_bash_rapporterer():
    import inspect
    from core.tools import simple_tools_operator as O
    assert "vedhaeft(" in inspect.getsource(O._exec_operator_bash)


def test_ALLE_fire_shell_indgange_naevner_indespaerring():
    """Den samlede kontrakt. Gaar denne i roedt, er en indgang faldet tilbage
    til tavshed — og en taendt sandkasse ser igen ud som om den daekker alt."""
    import inspect
    from core.tools import bash_session, operator_bash_session
    from core.tools import simple_tools_operator, simple_tools_web
    for navn, fn in (
        ("bash", simple_tools_web._exec_bash),
        ("bash_session_run", bash_session._exec_bash_session_run),
        ("operator_bash", simple_tools_operator._exec_operator_bash),
        ("operator_bash_session_run",
         operator_bash_session._exec_operator_bash_session_run),
    ):
        kilde = inspect.getsource(fn)
        assert ("confinement" in kilde or "vedhaeft(" in kilde), navn
