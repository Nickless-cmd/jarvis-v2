"""Den afløste kørsels EGEN række lukkes med det samme — ikke 30 minutter senere.

## Hullet (målt 6/10-2026)

`visible_run_recovery_dispatcher` afregnede kun journal-posten (JSON). En
kørsel der døde UDEN at nå sin egen afslutning blev derfor liggende `running`
med tom `finished_at`, mens dens fortsættelse kørte videre under et nyt run_id.

Målt i produktionen på CT105, én besked fra Bjørn («slet de 175 og commit
flaget»):

    visible-bd1727a4  16:36:48  running      0 costs-opslag   ← efterladt
    visible-8d73539d  16:38:42  interrupted  0 costs-opslag
    visible-3433cf05  16:49:56  completed   16 costs-opslag   ← den der svarede

Nul `costs`-opslag er beviset for at en række aldrig nåede et model-kald
(efterprøvet: 242 af 242 færdige runs de sidste to døgn HAR opslag). Først
`_ryd_visible_drift` lukkede `bd1727a4` 30 minutter senere — og indtil da
blokerede den genstarts-vagten, altså hvert deploy.

## Hvorfor det tavse stempel

`stamp_visible_run_interrupted` udsender `runtime.visible_run_interrupted`, og
`living_executive` planlægger en self-wakeup på netop det event. Kaldt fra
dispatcherens succes-sti ville den bede om en genoptagelse af det der LIGE blev
genoptaget. `stamp_visible_run_superseded` er tavs — og den sande: rækken er
afløst, ikke efterladt.

Testene kører mod RIGTIG sqlite. En fake forbindelse der svarer det samme
uanset SQL'en kan ikke se at WHERE nu dækker `running` såvel som `recovering`.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import in_flight_runs as ifr
from core.services import visible_run_recovery_dispatcher as D


@pytest.fixture(autouse=True)
def _isolerede_poster(monkeypatch, tmp_path):
    """Hold journal-posterne i hukommelsen og væk fra produktionens fil."""
    from core.runtime import state_store

    monkeypatch.setattr(state_store, "_STATE_DIR", tmp_path / "state")
    poster: dict[str, dict] = {}
    monkeypatch.setattr(ifr, "_load", lambda: {k: dict(v) for k, v in poster.items()})
    monkeypatch.setattr(
        ifr, "_save",
        lambda v: (poster.clear(), poster.update({k: dict(x) for k, x in v.items()})))
    monkeypatch.setattr(ifr, "owner_still_alive", lambda owner: False)
    monkeypatch.delenv("JARVIS_ENABLE_RUNTIME_SERVICES", raising=False)
    return poster


@pytest.fixture
def spawn(monkeypatch):
    kald: list[dict] = []

    def _start(**kw):
        kald.append(kw)
        return "visible-fortsaettelsen"

    monkeypatch.setattr(
        "core.services.visible_runs_sections.detached_run.start_user_run_detached",
        _start)
    return kald


def _skriv_raekke(run_id: str, *, status: str, finished_at: str = "",
                  age_s: int = 600) -> None:
    from core.runtime.db import connect
    from core.runtime.db_visible import ensure_visible_tables

    started = (datetime.now(UTC) - timedelta(seconds=age_s)).isoformat()
    with connect() as conn:
        ensure_visible_tables(conn)
        conn.execute(
            "INSERT OR REPLACE INTO visible_runs "
            "(run_id, lane, provider, model, status, started_at, finished_at, "
            " text_preview, error, capability_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (run_id, "primary", "ollama", "deepseek-v4-flash", status, started,
             finished_at, "slet de 175 og commit flaget", None, None),
        )


def _raekke(run_id: str) -> dict | None:
    from core.runtime.db import connect

    with connect() as conn:
        row = conn.execute(
            "SELECT status, finished_at FROM visible_runs WHERE run_id=?",
            (run_id,),
        ).fetchone()
    return {"status": row["status"], "finished_at": row["finished_at"]} if row else None


def _forladt_opgave(run_id: str, *, besked: str = "slet de 175 og commit flaget") -> None:
    ifr.mark_started(run_id=run_id, session_id="chat-1", user_message=besked)
    ifr.settle_recovering(run_id, reason="shutdown", summary="shutdown")


# ── stemplet selv, mod rigtig sqlite ────────────────────────────────────────

def test_running_uden_finished_at_lukkes_og_faar_et_tidsstempel(isolated_runtime):
    """DEN tilstand `bd1727a4` stod i. Før ændringen var stemplet en no-op."""
    from core.services.visible_runs_outcomes import stamp_visible_run_superseded

    _skriv_raekke("visible-bd1727a4", status="running", finished_at="")

    assert stamp_visible_run_superseded(
        "visible-bd1727a4", reason="afloest af visible-3433cf05") is True

    efter = _raekke("visible-bd1727a4")
    assert efter["status"] == "interrupted"
    assert efter["finished_at"], "en terminal raekke uden finished_at er dobbelt sandhed"


def test_recovering_beholder_sin_egen_finished_at(isolated_runtime):
    """Den var allerede sat da udfaldet blev persisteret — og den er sand.

    Overskrev vi den med «nu», ville rækken påstå at kørslen sluttede i det
    øjeblik oprydningen tilfældigvis kørte.
    """
    from core.services.visible_runs_outcomes import stamp_visible_run_superseded

    aegte = "2026-10-06T16:43:50.000000+00:00"
    _skriv_raekke("visible-8d73539d", status="recovering", finished_at=aegte)

    assert stamp_visible_run_superseded("visible-8d73539d", reason="afloest") is True
    assert _raekke("visible-8d73539d") == {
        "status": "interrupted", "finished_at": aegte}


def test_en_terminal_raekke_roeres_ikke(isolated_runtime):
    """Idempotens: stemplet kaldes igen ved næste genoptagelse i samme kæde."""
    from core.services.visible_runs_outcomes import stamp_visible_run_superseded

    _skriv_raekke("visible-3433cf05", status="completed",
                  finished_at="2026-10-06T16:52:00+00:00")

    assert stamp_visible_run_superseded("visible-3433cf05", reason="afloest") is False
    assert _raekke("visible-3433cf05")["status"] == "completed"


def test_stemplet_er_TAVST(isolated_runtime, monkeypatch):
    """Udsendte det `runtime.visible_run_interrupted`, ville `living_executive`
    planlægge en self-wakeup — en genoptagelse af det der lige blev genoptaget."""
    import core.services.visible_runs_outcomes as vro

    sendt: list[str] = []
    monkeypatch.setattr(vro.event_bus, "publish",
                        lambda navn, nyttelast=None, **k: sendt.append(str(navn)))
    _skriv_raekke("visible-bd1727a4", status="running")

    assert vro.stamp_visible_run_superseded("visible-bd1727a4", reason="afloest") is True
    assert sendt == [], f"stemplet skal vaere tavst, men udsendte {sendt}"


# ── dispatcheren, hele vejen igennem ────────────────────────────────────────

def test_dispatcheren_lukker_raekken_naar_fortsaettelsen_er_startet(
    isolated_runtime, spawn
):
    """Kernen. Rækken må ikke stå `running` mens dens afløser kører."""
    _skriv_raekke("visible-bd1727a4", status="running", finished_at="")
    _forladt_opgave("visible-bd1727a4")

    assert D.recover_due_once()["started"] == 1
    assert len(spawn) == 1

    efter = _raekke("visible-bd1727a4")
    assert efter["status"] == "interrupted"
    assert efter["finished_at"]


def test_raekken_lukkes_ogsaa_naar_samtalen_gik_videre(
    isolated_runtime, spawn, monkeypatch
):
    """Den sti afregnede journal-posten `cancelled` og efterlod rækken `running`
    — samme zombie, anden gren."""
    monkeypatch.setattr(D, "_samtalen_gik_videre", lambda sid, efter: True)
    _skriv_raekke("visible-bd1727a4", status="running", finished_at="")
    _forladt_opgave("visible-bd1727a4")

    svar = D.recover_due_once()
    assert svar["error"] == "samtalen-gik-videre"
    assert spawn == [], "ingen betalt fortsaettelse paa den sti"
    assert _raekke("visible-bd1727a4")["status"] == "interrupted"


def test_dispatcheren_bruger_IKKE_det_event_udsendende_stempel(isolated_runtime, spawn):
    """Kilde-vagt mod en tilbagerulning til `stamp_visible_run_interrupted`.

    Den udsender `runtime.visible_run_interrupted`, og `living_executive`
    vækker på det. Byttede nogen stemplet, ville dispatcheren bede om en
    genoptagelse af sin egen fortsættelse — og intet ville fejle.
    """
    import inspect

    kilde = inspect.getsource(D._luk_afloest_raekke)
    assert "stamp_visible_run_superseded" in kilde
    assert "stamp_visible_run_interrupted" not in kilde.split('"""')[-1], (
        "dispatcheren maa ikke kalde det event-udsendende stempel")


def test_en_udskudt_opgave_roerer_IKKE_raekken(isolated_runtime, spawn, monkeypatch):
    """`session-optaget` giver kravet tilbage — opgaven skal tages igen senere,
    så dens række må ikke stemples slut."""
    monkeypatch.setattr(
        "core.services.run_event_log.active_run_for_session",
        lambda sid: "visible-noget-der-koerer")
    _skriv_raekke("visible-bd1727a4", status="running", finished_at="")
    _forladt_opgave("visible-bd1727a4")

    svar = D.recover_due_once()
    assert svar["error"] == "session-optaget"
    assert _raekke("visible-bd1727a4")["status"] == "running"
