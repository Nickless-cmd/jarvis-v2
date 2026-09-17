"""Alle fejlklasser gennem HELE livscyklussen — én gang, samme påstande.

Opgave 8. De syv foregående opgaver rettede hver sin del: journalen, én
afregning, hvert ophør, én dispatcher, stop mod supersession, research og
gensynet. Matrixen her er den eneste test der kører dem SAMMEN, og den findes
fordi delene kan være rigtige hver for sig og stadig lade en tur forsvinde
mellem to af dem.

Påstandene er de samme for alle klasser:

  * det første ophør er `recovering` — aldrig «færdig» uden belæg
  * der startes PRÆCIS én fortsættelse
  * brugeren får mindst én besked om hvad der sker
  * og et eksplicit stop er kontrollen: det genoptages aldrig
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from core.services import in_flight_runs as ifr
from core.services import visible_run_recovery_dispatcher as D
from core.services.visible_run_recovery_coordinator import FailureClass
from core.services.visible_run_segment_settlement import (
    settle_segment_exit,
    settle_user_stop,
)


@dataclass
class Udfald:
    """Hvad der skete med opgaven, fra ophør til fortsættelse."""

    initial_terminal_state: str = ""
    continuations: int = 0
    final_state: str = ""
    visible_notice_count: int = 0
    failure_class: str = ""
    beskeder: list[str] = field(default_factory=list)


class Proeveopstilling:
    """Ét run, én journal, én dispatcher — uden netværk og uden tråde."""

    def __init__(self, poster: dict, spawns: list[dict]) -> None:
        self.poster = poster
        self.spawns = spawns

    def inject(self, fejl: str) -> Udfald:
        ifr.mark_started(run_id="task-1", session_id="chat-1",
                         user_message="ret cheap lane-værnet")
        ud = Udfald()

        if fejl == "explicit_cancel":
            stop = settle_user_stop(run_id="task-1", session_id="chat-1")
            ud.initial_terminal_state = stop.decision.state.value
            ud.failure_class = stop.failure_class.value
        else:
            grund, klasse = _FEJL[fejl]
            segment = settle_segment_exit(
                run_id="task-1", session_id="chat-1", exit_reason=grund,
                final_text="jeg var midt i det", failure_class=klasse,
                summary="ret cheap lane-værnet",
            )
            ud.initial_terminal_state = segment.decision.stop_reason
            ud.failure_class = segment.failure_class.value
            if segment.event_name:
                ud.visible_notice_count += 1
                ud.beskeder.append(str(segment.event_payload.get("message") or ""))

        # Dispatcheren kører til den ikke finder mere — ÉN fortsættelse pr. opgave.
        for _ in range(3):
            svar = D.recover_due_once()
            ud.continuations += int(svar.get("started") or 0)
            if not svar.get("started"):
                break

        # Fortsættelsen gør sit arbejde færdigt.
        if ud.continuations:
            ifr.settle_terminal("task-1", status="completed", reason="completed")
        ud.final_state = str((self.poster.get("task-1") or {}).get("status")
                             or ("completed" if ud.continuations else ""))
        if not ud.final_state and "task-1" not in self.poster:
            ud.final_state = "completed"      # posten ryddes når turen lykkedes
        return ud


#: Fejl → (exit-grund, klasse). De fem klasser der kan genoptages.
_FEJL = {
    "process_owner_dead": ("shutdown", FailureClass.PROCESS),
    "provider_failure": ("provider-not-supported", FailureClass.PROVIDER),
    "watchdog_timeout": ("provider-round-timeout", FailureClass.WATCHDOG),
    "research_timeout": ("research-wall-time-exceeded", FailureClass.RESEARCH),
    "runtime_exception": ("runtime-ValueError", FailureClass.RUNTIME),
}


@pytest.fixture
def harness(monkeypatch):
    poster: dict[str, dict] = {}
    monkeypatch.setattr(ifr, "_load", lambda: {k: dict(v) for k, v in poster.items()})
    monkeypatch.setattr(ifr, "_save", lambda v: (poster.clear(),
                                                 poster.update({k: dict(x) for k, x in v.items()})))
    monkeypatch.setattr(ifr, "owner_still_alive", lambda owner: False)
    monkeypatch.delenv("JARVIS_ENABLE_RUNTIME_SERVICES", raising=False)
    spawns: list[dict] = []
    monkeypatch.setattr(
        "core.services.visible_runs_sections.detached_run.start_user_run_detached",
        lambda **kw: spawns.append(kw) or f"visible-{len(spawns)}")
    return Proeveopstilling(poster, spawns)


@pytest.mark.parametrize("fejl", sorted(_FEJL))
def test_en_genoptagelig_fejl_bliver_aldrig_tavst_faerdig(fejl, harness):
    ud = harness.inject(fejl)
    assert ud.initial_terminal_state == "recovering", fejl
    assert ud.continuations == 1, "præcis én fortsættelse"
    assert ud.final_state in {"completed", "failed_terminal"}, fejl
    assert ud.visible_notice_count >= 1, "brugeren skal have fået det at vide"
    assert len(harness.spawns) == 1


@pytest.mark.parametrize("fejl", sorted(_FEJL))
def test_fortsaettelsen_baerer_opgaven_med_sig(fejl, harness):
    """En fortsættelse uden den oprindelige anmodning ville starte forfra på
    noget andet."""
    harness.inject(fejl)
    spawn = harness.spawns[0]
    assert spawn["session_id"] == "chat-1"
    assert "ret cheap lane-værnet" in spawn["message"]
    assert spawn["recovery_task_id"] == "task-1"
    assert spawn["recovery_generation"] == 1


def test_brugerens_stop_er_kontrollen(harness):
    """Den ene fejl der IKKE må genoptages — ellers ville et stop starte igen."""
    ud = harness.inject("explicit_cancel")
    assert ud.final_state == "cancelled"
    assert ud.continuations == 0
    assert ud.failure_class == "cancellation"
    assert harness.spawns == []


def test_to_ophoer_for_samme_opgave_giver_EN_fortsaettelse(harness):
    """Et segment kan ende både i sin undtagelse og i sin finally. Den samme
    opgave må ikke startes to gange af den grund."""
    ifr.mark_started(run_id="task-1", session_id="chat-1", user_message="opgaven")
    for _ in range(2):
        settle_segment_exit(run_id="task-1", session_id="chat-1",
                            exit_reason="shutdown", final_text="")
    startede = sum(int(D.recover_due_once().get("started") or 0) for _ in range(3))
    assert startede == 1
    assert len(harness.spawns) == 1
