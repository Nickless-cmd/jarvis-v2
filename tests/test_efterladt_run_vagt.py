"""Vagter for den periodiske sweep af efterladte ``running``-rækker.

Baggrund (14/11-2026): ``stamp_visible_run_interrupted`` blev kun kaldt ved
opstart og ved nedlukning, så et run der døde midt i en tur blev stående
``running`` indtil næste genstart — og blokerede sin session imens.

Testene her bevogter det der gør sweepen sikker at lade køre i drift: den må
stemple det døde, og den må **ikke** røre det levende.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture
def state_i_tmp(tmp_path, monkeypatch):
    """Flyt ``state_store``s mappe til tmp, så ``in_flight_runs`` ikke rører produktionen.

    Samme grund som i ``test_session_boot_reconciler``: ``_STATE_DIR`` bindes ved
    import, så uden dette læser og SKRIVER testen den rigtige
    ``~/.jarvis-v2/state/in_flight_runs.json``.
    """
    from core.runtime import state_store

    monkeypatch.setattr(state_store, "_STATE_DIR", tmp_path / "state")
    return tmp_path


def _seed_raekke(run_id: str, *, status: str = "running", alder_s: float = 1000.0,
                 finished: str | None = None) -> None:
    from core.runtime.db import connect

    started = (datetime.now(UTC) - timedelta(seconds=alder_s)).isoformat()
    with connect() as c:
        c.execute(
            "INSERT INTO visible_runs (run_id, lane, provider, model, status, "
            "started_at, finished_at) VALUES (?,?,?,?,?,?,?)",
            (run_id, "visible", "deepseek", "deepseek-v4-flash", status, started,
             # `finished_at` er NOT NULL i skemaet: en kørende række bærer tom
             # streng, ikke NULL. `run_er_terminal` læser `bool(...)`, så '' er
             # netop «ikke slut».
             finished or ""),
        )
        c.commit()


def _seed_inflight(run_id: str, *, owner: str, alder_s: float = 5.0) -> None:
    from core.services import in_flight_runs as runs

    nu = (datetime.now(UTC) - timedelta(seconds=alder_s)).isoformat()
    poster = runs._load()
    poster[run_id] = {
        "run_id": run_id, "session_id": "s1", "status": "running",
        "kind": "visible", "provider": "", "model": "",
        "excerpt": "arbejde", "started_at": nu, "last_progress_at": nu,
        "last_tool": "", "owner_proc": owner,
    }
    runs._save(poster)


def _status(run_id: str) -> tuple[str, str | None]:
    from core.runtime.db import connect

    with connect() as c:
        row = c.execute(
            "SELECT status, finished_at FROM visible_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
    return (str(row[0]), row[1])


def test_efterladt_raekke_stemples_afbrudt(isolated_runtime, state_i_tmp):
    """En ``running``-række uden post i den delte sandhed er død. Den skal lukkes."""
    from core.services.efterladt_run_vagt import sweep_efterladte_runs

    _seed_raekke("run-efterladt")

    ud = sweep_efterladte_runs()

    assert ud["stemplet"] == ["run-efterladt"]
    status, finished = _status("run-efterladt")
    assert status == "interrupted"
    assert finished, "finished_at skal sættes — ellers ser rækken stadig ud som en kørsel"


def test_levende_run_roeres_ikke(isolated_runtime, state_i_tmp):
    """Er runnet i den delte sandhed med frisk fremgang, er det LEVENDE.

    Dette er det vigtigste værn: en sweep der stempler et kørende run dræber
    Bjørns tur. Tærsklen alene må aldrig afgøre sagen.
    """
    from core.services.efterladt_run_vagt import sweep_efterladte_runs
    from core.services.in_flight_runs import current_owner

    _seed_raekke("run-levende")
    _seed_inflight("run-levende", owner=current_owner(), alder_s=5.0)

    ud = sweep_efterladte_runs()

    assert ud["stemplet"] == []
    assert "run-levende" in ud["sprunget_over"]
    assert _status("run-levende")[0] == "running"


def test_stilstand_over_taersklen_stemples_selv_med_levende_ejer(isolated_runtime, state_i_tmp):
    """En post hvis ejer lever, men som ikke har rørt sig i > tærsklen, er død.

    Ejeren kan være en proces der aldrig afmeldte posten. Uden dette ville en
    sådan post holde sessionen låst for evigt.
    """
    from core.services.efterladt_run_vagt import sweep_efterladte_runs
    from core.services.in_flight_runs import current_owner

    _seed_raekke("run-stille")
    _seed_inflight("run-stille", owner=current_owner(), alder_s=10_000.0)

    ud = sweep_efterladte_runs()

    assert ud["stemplet"] == ["run-stille"]
    assert _status("run-stille")[0] == "interrupted"


def test_doed_ejer_stemples(isolated_runtime, state_i_tmp):
    """En post hvis ejer-proces er væk er en ægte zombie — uanset alder."""
    from core.services.efterladt_run_vagt import sweep_efterladte_runs

    _seed_raekke("run-zombie")
    _seed_inflight("run-zombie", owner="999999:1", alder_s=5.0)

    ud = sweep_efterladte_runs()

    assert ud["stemplet"] == ["run-zombie"]
    assert _status("run-zombie")[0] == "interrupted"


def test_terminal_raekke_roeres_ikke(isolated_runtime, state_i_tmp):
    """Et rigtigt udfald må aldrig overskrives af en sweep der kommer bagefter."""
    from core.services.efterladt_run_vagt import sweep_efterladte_runs

    _seed_raekke("run-faerdig", status="completed",
                 finished=datetime.now(UTC).isoformat())

    ud = sweep_efterladte_runs()

    assert ud["stemplet"] == []
    assert _status("run-faerdig")[0] == "completed"


def test_frisk_raekke_undersoeges_slet_ikke(isolated_runtime, state_i_tmp):
    """En række yngre end tærsklen er ikke engang kandidat.

    Uden dette forfilter ville sweepen stempler runs der lige er startet, før
    de har haft en chance for at skrive deres første fremgang.
    """
    from core.services.efterladt_run_vagt import sweep_efterladte_runs

    _seed_raekke("run-frisk", alder_s=5.0)

    ud = sweep_efterladte_runs()

    assert ud["stemplet"] == []
    assert ud["sprunget_over"] == []
    assert _status("run-frisk")[0] == "running"


def test_taersklen_ligger_over_husets_egen_tavshedsgraense():
    """Tærsklen skal være højere end den grænse hvor runnet selv giver op.

    Ellers kan sweepen stemple en tur der stadig kører — et langt værktøjskald
    har også en gammel ``last_progress_at``. Husets egen runde-watchdog giver op
    efter ``round_silence_timeout_s`` (180 s som standard), så vi skal ligge
    over det, ikke på det.
    """
    from core.services.efterladt_run_vagt import STILSTAND_S

    assert STILSTAND_S > 180.0
