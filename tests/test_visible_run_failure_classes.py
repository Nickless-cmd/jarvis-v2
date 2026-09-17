"""Hver unormal udgang skal efterlade en durabel post — før noget lukkes.

Opgave 3. De tolv udgange i planen er ikke tolv stykker logik: de er tolv
grunde der løber gennem ét sted. Testene her holder netop det fast — at
grunden bliver skrevet ned, at dommen ikke pludselig siger «færdig», og at
den der ikke kunne skrives ned heller ikke lover en fortsættelse.
"""
from __future__ import annotations

import pytest

from core.services import in_flight_runs as ifr
from core.services.visible_run_recovery_coordinator import FailureClass
from core.services.visible_run_segment_settlement import (
    failure_class_for,
    settle_segment_exit,
)


@pytest.fixture(autouse=True)
def _isolerede_poster(monkeypatch):
    poster: dict[str, dict] = {}
    monkeypatch.setattr(ifr, "_load", lambda: {k: dict(v) for k, v in poster.items()})

    def gem(value):
        poster.clear()
        poster.update({k: dict(v) for k, v in value.items()})

    monkeypatch.setattr(ifr, "_save", gem)
    monkeypatch.setattr(ifr, "owner_still_alive", lambda owner: False)
    return poster


def _start(run_id: str = "r1") -> None:
    ifr.mark_started(run_id=run_id, session_id="s1", user_message="fix it")


#: De unormale udgange fra planens tabel — grund og forventet fejlklasse.
UDGANGE = [
    ("provider-round-timeout", FailureClass.WATCHDOG),
    ("provider-not-supported", FailureClass.PROVIDER),
    ("provider-error:HTTP 404", FailureClass.PROVIDER),
    ("breaker-open", FailureClass.PROVIDER),
    ("round-silence-timeout", FailureClass.WATCHDOG),
    ("turn-wall-clock", FailureClass.WATCHDOG),
    ("relay_source_idle_timeout", FailureClass.WATCHDOG),
    ("relay_source_closed", FailureClass.WATCHDOG),
    ("budget-opbrugt", FailureClass.RUNTIME),
    ("pending-tool-intent", FailureClass.RUNTIME),
    ("forced-finalize-unverified", FailureClass.RUNTIME),
    ("interrupted:followup-round-1-provider-error", FailureClass.RUNTIME),
    ("early-exit-no-progress", FailureClass.RUNTIME),
    ("shutdown", FailureClass.PROCESS),
]


@pytest.mark.parametrize("grund,klasse", UDGANGE)
def test_hver_unormal_udgang_bliver_durabel_foer_den_lukkes(grund, klasse):
    _start()
    ud = settle_segment_exit(run_id="r1", session_id="s1", exit_reason=grund,
                             final_text="jeg var midt i det")
    assert ud.decision.stop_reason == "recovering", grund
    assert ud.event_name == "run_recovery"
    assert ud.event_payload["continuing"] is True
    assert ud.failure_class is klasse
    post = ifr._load()["r1"]
    assert post["status"] == "recovering"
    assert post["exit_reason"] == ud.exit_reason
    assert ud.durable_write_failed is False


def test_et_faerdigt_segment_skriver_ingen_genoptagelse():
    _start()
    ud = settle_segment_exit(run_id="r1", session_id="s1", exit_reason="completed",
                             final_text="Kort sagt: det er rettet og verificeret.")
    assert ud.event_name == "" and ud.decision.stop_reason == "end_turn"
    assert ifr._load()["r1"]["status"] == "completed"


def test_brugerens_stop_er_ikke_en_genoptagelse():
    """Kun et EKSPLICIT stop må blive terminal `cancelled` — og det må aldrig
    blive til en fortsættelse der starter igen bag ryggen på ham."""
    _start()
    ud = settle_segment_exit(run_id="r1", session_id="s1", exit_reason="user-cancelled",
                             explicit_user_cancel=True, final_text="")
    assert ud.decision.should_continue is False
    assert ud.failure_class is FailureClass.CANCELLATION
    assert ifr._load()["r1"]["status"] == "cancelled"


def test_opbrugte_genoptagelser_giver_en_sidste_slutrunde_foerst():
    """Ved loftet er svaret ikke «giv op», men «afslut ordentligt én gang»."""
    _start()
    ud = settle_segment_exit(run_id="r1", session_id="s1",
                             exit_reason="provider-round-timeout",
                             recovery_attempt=3, recovery_limit=3,
                             final_text="midt i det")
    assert ud.final_synthesis_required is True
    assert ud.decision.should_continue is True
    efter = settle_segment_exit(run_id="r1", session_id="s1",
                                exit_reason="provider-round-timeout",
                                recovery_attempt=3, recovery_limit=3,
                                final_synthesis_attempted=True, final_text="midt i det")
    assert efter.decision.state.value == "failed_terminal"
    assert efter.event_payload["continuing"] is False


def test_samme_grund_to_gange_giver_kun_EN_udsendelse():
    """Idempotens: to udgange for samme segment (fx exception OG finally) må
    ikke køsætte to fortsættelser."""
    _start()
    a = settle_segment_exit(run_id="r1", session_id="s1", exit_reason="shutdown")
    b = settle_segment_exit(run_id="r1", session_id="s1", exit_reason="shutdown")
    assert a.dispatch_due is True and b.dispatch_due is False


def test_en_journal_der_ikke_kan_skrives_lover_ikke_en_fortsaettelse(monkeypatch):
    """«Jarvis fortsætter automatisk» er en påstand om noget skrevet ned. Kan
    det ikke skrives, skal beskeden sige det — ikke love noget."""
    import core.services.visible_run_segment_settlement as S
    monkeypatch.setattr(S, "settle_segment",
                        lambda _r: (_ for _ in ()).throw(OSError("disken er fuld")))
    ud = settle_segment_exit(run_id="r1", session_id="s1", exit_reason="shutdown")
    assert ud.durable_write_failed is True
    assert ud.decision.should_continue is False
    assert ud.event_payload["continuing"] is False
    assert "fortsætter ikke af sig selv" in ud.event_payload["message"]


def test_ukendt_grund_gaetter_ikke_paa_en_udbyder():
    assert failure_class_for("noget-helt-nyt") is FailureClass.RUNTIME
    assert failure_class_for("") is FailureClass.RUNTIME
