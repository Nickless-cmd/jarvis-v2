"""Kontakten skal virke på begge døre.

decision_review blev slået fra som daemon 11/6-2026 pga. selv-bias. Men den
SAMME funktion kørte videre som dagligt job herfra, uden om daemon-gaten:
registret sagde DEAKTIVERET mens den skrev 30.867 domme over tre måneder.
Testen holder fast i at jobbet nu spørger daemon_manager først.
"""

from __future__ import annotations

import pytest

from core.services import governance_bootstrap as GB


def _hent_handler(monkeypatch, job_type: str):
    """Kør registreringen med en opsamlende register_handler og find én handler."""
    from core.services import jobs_engine

    opsamlet: dict = {}
    monkeypatch.setattr(
        jobs_engine, "register_handler",
        lambda kind, fn: opsamlet.__setitem__(kind, fn),
    )
    GB.ensure_default_job_handlers()
    assert job_type in opsamlet, "%s blev ikke registreret" % job_type
    return opsamlet[job_type]


def test_jobbet_respekterer_daemon_kontakten(monkeypatch):
    from core.services import daemon_manager as dm

    handler = _hent_handler(monkeypatch, "decision_review")
    monkeypatch.setattr(dm, "is_enabled", lambda navn: False)
    monkeypatch.setattr(
        "core.services.decision_review_prompter.review_pending_decisions",
        lambda **kw: pytest.fail("review må ikke køre når daemonen er slået fra"),
    )

    ud = handler({})
    assert ud["status"] == "ok"
    assert ud["result"]["status"] == "disabled"


def test_jobbet_koerer_naar_daemonen_er_taendt(monkeypatch):
    from core.services import daemon_manager as dm
    from core.services import decision_review_prompter as P

    handler = _hent_handler(monkeypatch, "decision_review")
    monkeypatch.setattr(dm, "is_enabled", lambda navn: True)
    monkeypatch.setattr(P, "review_pending_decisions", lambda **kw: {"status": "ok", "reviewed": 2})

    ud = handler({})
    assert ud["result"]["reviewed"] == 2


def test_ulaeselig_gate_stopper_ikke_jobbet(monkeypatch):
    """Fail-open som resten af runtimen: kan gaten ikke læses, kører vi videre."""
    from core.services import daemon_manager as dm
    from core.services import decision_review_prompter as P

    handler = _hent_handler(monkeypatch, "decision_review")
    monkeypatch.setattr(
        dm, "is_enabled",
        lambda navn: (_ for _ in ()).throw(RuntimeError("registret utilgængeligt")),
    )
    monkeypatch.setattr(P, "review_pending_decisions", lambda **kw: {"status": "ok", "reviewed": 1})

    ud = handler({})
    assert ud["result"]["reviewed"] == 1


def _alle_handlers(monkeypatch) -> dict:
    """Registrér alle handlers og returnér dem, uden at kalde dem."""
    from core.services import jobs_engine

    opsamlet: dict = {}
    monkeypatch.setattr(
        jobs_engine, "register_handler",
        lambda kind, fn: opsamlet.__setitem__(kind, fn),
    )
    GB.ensure_default_job_handlers()
    return opsamlet


def test_ingen_handler_importerer_et_navn_der_ikke_findes(monkeypatch):
    """12/10-2026: `dream_distillation_sweep` kaldte `tick_dream_distillation_daemon`,
    som ikke findes i modulet — den hedder `run_dream_distillation_daemon`. Fejlen
    var tavs: handleren fangede ImportError'en og returnerede `status: error`, saa
    jobbet saa ud som om det koerte. Den blev foerst synlig da sweep'en fik en
    kadence og faktisk fyrede.

    Denne test kalder HVER registreret handler og kraever at ingen af dem fejler
    med en ImportError/AttributeError — altsaa at navnene de importerer findes.
    Handlere der fejler af andre grunde (manglende data, netvaerk) er ikke i sig
    selv en fejl her; det er den DOEDE REFERENCE vi fanger.
    """
    handlers = _alle_handlers(monkeypatch)
    assert handlers, "ingen handlers blev registreret"

    doede: list[str] = []
    for job_type, fn in sorted(handlers.items()):
        try:
            ud = fn({"reason": "test"})
        except Exception as exc:  # pragma: no cover - handleren maa ikke kaste
            doede.append(f"{job_type}: kastede {type(exc).__name__}: {exc}")
            continue
        fejl = str((ud or {}).get("error") or "")
        if "cannot import name" in fejl or "has no attribute" in fejl:
            doede.append(f"{job_type}: {fejl[:160]}")

    assert not doede, "handlers med doede referencer:\n" + "\n".join(doede)


def test_dream_distillation_handler_kalder_den_rigtige_funktion(monkeypatch):
    """Navnet er `run_dream_distillation_daemon`, ikke `tick_...`."""
    from core.services import dream_distillation_daemon as D

    handler = _hent_handler(monkeypatch, "dream_distillation_sweep")
    kaldt: dict = {}

    def _falsk(*, trigger: str = "", last_visible_at: str = "") -> dict:
        kaldt["trigger"] = trigger
        return {"status": "written", "residue": "test"}

    monkeypatch.setattr(D, "run_dream_distillation_daemon", _falsk)
    ud = handler({})
    assert ud["status"] == "ok", ud
    assert ud["result"]["status"] == "written"
    assert kaldt["trigger"] == "periodic-scheduled"
