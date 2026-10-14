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


@pytest.fixture(autouse=True)
def _ren_log():
    """_RUNS/_ALIASER er procesglobale — ryd dem så testene ikke lækker."""
    from core.services import run_event_log as rel
    for d in (rel._RUNS, rel._ALIASER, rel._ALIASER_OMVENDT):
        d.clear()
    yield
    for d in (rel._RUNS, rel._ALIASER, rel._ALIASER_OMVENDT):
        d.clear()


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
    from core.services import run_event_log as rel
    from core.services.visible_runs_sections.detached_run import _afregn_genoptaget_run

    _genoptagelse(poster)
    # OPRETTELSESPUNKTET: vores log oprettes, og runnets eget id bindes til NETOP
    # den. Uden bindingen er id'et ``unknown`` — og så afregner vi ikke, med
    # vilje. Det er relationen, ikke id'ets form, der gør det til vores.
    rel.create("visible-gen", "s1")
    rel.alias("visible-indre", "visible-gen")
    # Runnets EGET id (ikke et log-id) — terminalt, altså fortsættelsen er færdig.
    # Posten BÆRER opgaven (``task_id`` = opgavens id, ikke sit eget): det er
    # ``mark_started(task_id=…)`` der skriver den, og den er den durabelt
    # verificerbare relation mellem run og opgave.
    poster["visible-indre"] = {
        "run_id": "visible-indre",
        "task_id": "opg-A",
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


def test_den_indre_koersel_baerer_opgaven(poster):
    """REGRESSIONEN (målt 14/10-2026, kl. 20:23:36).

    Genoptagelsens INDRE koersel journalfoerer sig selv under sit EGET id.
    Foer rettelsen faldt `mark_started` tilbage til `run_id`, saa posten fik
    `task_id` = sig selv — og `_afregn_genoptaget_run`s task_id-vaern afviste
    afregningen. Opgaven laa tilbage, leasemaalet udloeb, og dispatcheren tog
    den igen som generation 2 mens generation 1 koerte.

    Maalt i drift: `afregning: run visible-7c365254 baerer opgave
    visible-7c365254 — ikke visible-55ad6c59`.
    """
    from core.services import in_flight_runs as ifr

    ifr.stempl_genoptagelse(
        run_id="visible-wrapper", session_id="s1", task_id="opgave-1",
        recovery_attempt=1, recovery_generation=1,
    )
    # Den indre koersel — gennem den AEGTE funktion, saa testen ogsaa fanger
    # hvis videresendelsen i `mark_visible_run_started` forsvinder igen.
    from core.services.visible_run_journal import mark_visible_run_started

    class _Run:
        run_id = "visible-indre"
        session_id = "s1"
        user_message = "x"
        autonomous = False
        provider = ""
        model = ""
        trust_all = False
        thinking_mode = "think"
        surface = ""
        user_id = ""
        local_tool_exec = False

    mark_visible_run_started(_Run(), recovery_task_id="opgave-1")

    indre = ifr.get_record("visible-indre")
    assert indre is not None, "den indre koersel skal have sin egen post"
    assert indre["task_id"] == "opgave-1", (
        "den indre koersel skal baere OPGAVEN, ikke sit eget id — ellers "
        "afviser afregningen dens 'faerdig' som fremmed"
    )


def test_start_visible_run_foerer_opgaven_ind_i_streamen(monkeypatch):
    """En genoptagelses opgave-id skal nå den indre stream ved rigtig opstart.

    Produktionsbruddet 14/10-2026 tilføjede ``recovery_task_id`` til den ydre
    indgang, men brugte navnet i den indre generator uden at føre det med ind.
    Resultatet var at samtlige synlige ture døde før model-loopet.
    """
    from core.services import visible_runs

    monkeypatch.setattr(visible_runs, "load_settings", lambda: type("S", (), {
        "primary_model_lane": "primary",
        "visible_model_provider": "deepseek",
        "visible_model_name": "deepseek-flash",
    })())

    modtaget: dict[str, str] = {}

    def fake_stream(
        run, *, force_user_id=None, tool_scope="", recovery_task_id: str,
    ):
        modtaget["task_id"] = recovery_task_id

        async def tom_stream():
            if False:
                yield ""

        return tom_stream()

    monkeypatch.setattr(visible_runs, "_stream_visible_run", fake_stream)

    visible_runs.start_visible_run(
        "fortsaet opgaven",
        session_id="s1",
        recovery_task_id="opgave-1",
    )

    assert modtaget == {"task_id": "opgave-1"}
