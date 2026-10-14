"""Afregningen må kun lukke en opgave ud fra ET RUN DER BÆRER DEN.

Målt i drift 14/10-2026 (journalctl + visible_runs + in_flight_runs):

    19:26:33  detached-run visible-9876eab2 fortsaetter opgave visible-a86c0813
    19:26:33  brugertur visible-9d85c1f5 starter i SAMME samtale
    19:28:33  visible-9d85c1f5 exit completed
    19:28:35  opgave visible-a86c0813 lukket — fortsaettelsen visible-9d85c1f5 sluttede
    19:28:35  lukkede soeskende-post visible-9876eab2 — deler task_id med a86c0813

Genoptagelsen KØRTE. Den blev lukket midt i sin kørsel, fordi et ANDET run i
samme samtale sluttede. `_afregn_genoptaget_run` læste tilstanden fra
`indre_run_id` — det id den første `system_event(kind=run)`-ramme bar — og i en
delt samtale kan den ramme tilhøre et fremmed run. Et fremmed «completed» er
ikke et bevis for at VORES fortsættelse er færdig.

Forskellen er målbar: et runs EGET id findes kun som nøgle i `run_event_log._ALIASER`,
mens et LOG-id (oprettet af `create`/`claim_or_create`) står i `_RUNS`. Det er
netop hvad der gør det fremmede id genkendeligt.
"""
from __future__ import annotations

import pytest

from core.services import in_flight_runs as ifr


@pytest.fixture
def poster(monkeypatch):
    records: dict[str, dict] = {}
    monkeypatch.setattr(ifr, "_load", lambda: {k: dict(v) for k, v in records.items()})

    def save(value):
        records.clear()
        records.update({k: dict(v) for k, v in value.items()})

    monkeypatch.setattr(ifr, "_save", save)
    monkeypatch.setattr(ifr, "owner_still_alive", lambda owner: True)
    return records


def _genoptagelse(poster, *, wrapper="visible-gen", opgave="opg-A", session="s1"):
    """Den kørende genoptagelses EGEN post — den der bærer opgaven."""
    poster[wrapper] = {
        "run_id": wrapper,
        "task_id": opgave,
        "session_id": session,
        "status": "running",
        "kind": "visible",
        "recovery_attempt": 1,
        "recovery_generation": 1,
        "recovery_owner": ifr.current_owner(),
        "started_at": ifr._iso(),
    }


def _fremmed_tur(poster, *, run_id="visible-bruger", session="s1"):
    """Et ANDET run i samme samtale — færdigt, og med sit eget id."""
    poster[run_id] = {
        "run_id": run_id,
        "task_id": run_id,
        "session_id": session,
        "status": "completed",
        "kind": "visible",
        "started_at": ifr._iso(),
        "settled_at": ifr._iso(),
    }


def test_fremmed_run_maa_ikke_lukke_opgaven(poster):
    """REGRESSIONEN (målt 14/10-2026)."""
    from core.services import run_event_log as rel
    from core.services.visible_runs_sections.detached_run import _afregn_genoptaget_run

    _genoptagelse(poster)
    _fremmed_tur(poster)
    # Den fremmede tur er et LOG-id — oprettet som samtale-log, ikke som et runs
    # eget id. Det er præcis hvad der gør den genkendelig som en anden samtales.
    rel.create("visible-bruger", "s1")

    _afregn_genoptaget_run(
        "opg-A", "visible-bruger", generation=1, wrapper_run_id="visible-gen",
    )

    assert poster["visible-gen"]["status"] == "running", (
        "en anden samtales afslutning maa ikke lukke en koerende genoptagelse"
    )


def test_eget_run_lukker_opgaven(poster):
    """Modstykket: den ægte vej må ikke blive blind af værnet."""
    from core.services.visible_runs_sections.detached_run import _afregn_genoptaget_run

    _genoptagelse(poster)
    # Runnets EGET id (ikke et log-id) — terminalt, altså fortsættelsen er færdig.
    poster["visible-indre"] = {
        "run_id": "visible-indre",
        "task_id": "visible-indre",
        "session_id": "s1",
        "status": "completed",
        "kind": "visible",
    }

    _afregn_genoptaget_run(
        "opg-A", "visible-indre", generation=1, wrapper_run_id="visible-gen",
    )

    assert poster["visible-gen"]["status"] == "completed", (
        "vores eget afsluttede run skal stadig lukke opgaven"
    )
