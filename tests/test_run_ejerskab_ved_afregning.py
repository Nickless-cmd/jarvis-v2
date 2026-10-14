"""EJERSKAB: kun et run der BEVISELIGT hører til opgaven må afregne den.

ChatGPT's tredje OG fjerde indvending mod 09cac0eeb (14/10-2026), målt i kilden:

``er_fremmed_log_id`` svarede kun på «er dette et LOG-id?» (findes i ``_RUNS``).
Et fremmed runs EGET id ligger i ``_ALIASER`` og slap derfor igennem — værnet
var smallere end rapporten gav indtryk af.

Og den boolske form havde et andet hul: ``unknown → True``. Et UKENDT id er ikke
det samme som et EJET. Fail-open dér genskabte præcis den fejl værnet findes
for: et fremmed «færdig» kunne lukke vores kørende opgave.

Invarianten der pinnes her:

    Ingen del af Jarvis må kunne afslutte en opgave på baggrund af et run,
    hvis ejerskab over opgaven ikke er verificeret.

``ramme_ejerskab`` svarer derfor med TRE udfald — ``owned``/``foreign``/``unknown``
— og kun ``owned`` afregner. Retningen er asymmetrien: at lukke en LEVENDE
opgave på et fremmed signal TABER arbejde. At lade en færdig opgave ligge og
tage den igen koster ét forsøg, og forsøgs-loftet fanger den.
"""
from __future__ import annotations

import time

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


def _faerdig_post(poster, run_id, *, task_id=None, session="s1"):
    poster[run_id] = {
        "run_id": run_id,
        "task_id": task_id or run_id,
        "session_id": session,
        "status": "completed",
        "kind": "visible",
        "started_at": ifr._iso(),
        "settled_at": ifr._iso(),
    }


# ── Udfald 1: OWNED afregner ────────────────────────────────────────────────

def test_owned_alias_for_vores_log_afregner(poster):
    """Vores EGET indre run — alias for NETOP vores log — skal lukke opgaven.

    ``wrapper_run_id`` ER log-id'et: ``claim_or_create`` (eller ``create``)
    opretter loggen, og runnets eget id meldes i run-rammen og bindes til den.
    """
    from core.services import run_event_log as rel
    from core.services.visible_runs_sections.detached_run import _afregn_genoptaget_run

    _genoptagelse(poster)
    rel.create("visible-gen", "s1")
    rel.alias("visible-vores-eget", "visible-gen")
    _faerdig_post(poster, "visible-vores-eget", task_id="opg-A")

    _afregn_genoptaget_run(
        "opg-A", "visible-vores-eget", generation=1, wrapper_run_id="visible-gen",
    )

    assert poster["visible-gen"]["status"] == "completed", (
        "vores eget afsluttede run skal stadig lukke opgaven"
    )


def test_owned_naar_id_er_wrapperens_eget(poster):
    """Ingen run-ramme set → afregningen falder tilbage til vores EGET id.

    Posten er den SAMME genoptagelses-post, nu terminal — ikke en frisk. Ellers
    bærer den ingen ``recovery_generation``, og ``_check_claim`` afviser kravet
    som superseded (målt: ``StaleRecoveryClaim`` i første forsøg på denne test).
    """
    from core.services.visible_runs_sections.detached_run import _afregn_genoptaget_run

    _genoptagelse(poster)
    poster["visible-gen"]["status"] = "completed"

    _afregn_genoptaget_run("opg-A", "visible-gen", generation=1,
                           wrapper_run_id="visible-gen")

    assert poster["visible-gen"]["status"] == "completed"


# ── Udfald 2: FOREIGN afregner ALDRIG ───────────────────────────────────────

def test_foreign_alias_for_en_anden_log_afregner_ikke(poster):
    """HUL 1. Et fremmed runs EGET id ligger i ``_ALIASER`` — bundet til en
    ANDEN log. Det slap gennem den boolske form og lukkede vores opgave."""
    from core.services import run_event_log as rel
    from core.services.visible_runs_sections.detached_run import _afregn_genoptaget_run

    _genoptagelse(poster)
    rel.create("visible-fremmed-log", "s1")
    rel.alias("visible-fremmed-eget", "visible-fremmed-log")
    _faerdig_post(poster, "visible-fremmed-eget")

    _afregn_genoptaget_run(
        "opg-A", "visible-fremmed-eget", generation=1, wrapper_run_id="visible-gen",
    )

    assert poster["visible-gen"]["status"] == "running", (
        "et fremmed runs EGET id (i _ALIASER) maa ikke lukke vores opgave"
    )


def test_foreign_log_id_i_runs_afregner_ikke(poster):
    """Den brede klasse: brugerens NÆSTE tur. Dens log-id står i ``_RUNS``."""
    from core.services import run_event_log as rel
    from core.services.visible_runs_sections.detached_run import _afregn_genoptaget_run

    _genoptagelse(poster)
    rel.create("visible-brugerens-tur", "s1")
    _faerdig_post(poster, "visible-brugerens-tur")

    _afregn_genoptaget_run(
        "opg-A", "visible-brugerens-tur", generation=1, wrapper_run_id="visible-gen",
    )

    assert poster["visible-gen"]["status"] == "running"


# ── Udfald 3: UNKNOWN afregner ALDRIG (ChatGPT's fjerde indvending) ─────────

def test_unknown_id_afregner_ikke(poster):
    """Et id vi ALDRIG har set er ikke det samme som et ejet.

    Fail-open her genskabte fejlen: et fremmed «completed» kunne lukke vores
    kørende opgave. Tvivlen skal BEVARE opgaven — den tages igen, og loftet
    fanger den hvis den aldrig bliver afregnet.
    """
    from core.services import run_event_log as rel
    from core.services.visible_runs_sections.detached_run import _afregn_genoptaget_run

    _genoptagelse(poster)
    _faerdig_post(poster, "visible-aldrig-set")

    assert rel.ramme_ejerskab("visible-aldrig-set", "visible-gen") == rel.EJERSKAB_UNKNOWN

    _afregn_genoptaget_run(
        "opg-A", "visible-aldrig-set", generation=1, wrapper_run_id="visible-gen",
    )

    assert poster["visible-gen"]["status"] == "running", (
        "et UKENDT id maa ikke afregne — tvivlen skal bevare opgaven"
    )


def test_uden_eget_log_id_er_alt_ukendt(poster):
    """Uden et eget log-id findes der intet at holde kandidaten op imod."""
    from core.services import run_event_log as rel

    assert rel.ramme_ejerskab("visible-x", "") == rel.EJERSKAB_UNKNOWN
    assert rel.ramme_ejerskab("", "visible-gen") == rel.EJERSKAB_UNKNOWN


def test_alias_for_os_selv_er_owned():
    """Grænsen mellem OWNED og FOREIGN ligger i HVILKEN log aliaset peger på."""
    from core.services import run_event_log as rel

    rel.create("visible-gen", "s1")
    rel.alias("visible-vores-eget", "visible-gen")
    rel.create("visible-fremmed-log", "s1")
    rel.alias("visible-fremmed-eget", "visible-fremmed-log")

    assert rel.ramme_ejerskab("visible-vores-eget", "visible-gen") == rel.EJERSKAB_OWNED
    assert rel.ramme_ejerskab("visible-fremmed-eget", "visible-gen") == rel.EJERSKAB_FOREIGN
    assert rel.ramme_ejerskab("visible-gen", "visible-gen") == rel.EJERSKAB_OWNED


# ── Den VIRKELIGE vej: _consume() må ikke lade en fremmed ramme kapre aliaset ──

def _tom_iter():
    async def _gen():
        if False:  # pragma: no cover - bevidst tom generator
            yield ""
    return _gen()


def _frames_iter(frames):
    async def _gen():
        for f in frames:
            yield f
    return _gen()


def _ramme(run_id: str) -> str:
    return (
        "event: system_event\n"
        'data: {"type": "system_event", "kind": "run", '
        f'"payload": {{"run_id": "{run_id}"}}}}\n\n'
    )


def _start(monkeypatch, frames, *, run_id="visible-gen", task_id="opg-A"):
    """Kør den ÆGTE ``start_user_run_detached`` → ``_consume()``-vej."""
    import core.services.run_event_log as rel
    import core.services.visible_runs as vr
    import core.services.visible_runs_sse_v2 as v2

    done: list[str] = []
    monkeypatch.setattr(vr, "start_visible_run", lambda **kw: _tom_iter())
    monkeypatch.setattr(v2, "translate_to_v2", lambda it, **kw: _frames_iter(frames))
    monkeypatch.setattr(rel, "append", lambda rid, f: None)
    monkeypatch.setattr(rel, "mark_done", lambda rid: done.append(rid))
    monkeypatch.setattr(rel, "prune", lambda: None)

    from core.services.visible_runs_sections.detached_run import start_user_run_detached
    start_user_run_detached(
        message="hej", session_id="s1", eff_model="m", eff_provider="p", lane="l",
        run_id=run_id, recovery_task_id=task_id, recovery_generation=1,
    )
    for _ in range(80):
        if done:
            return
        time.sleep(0.05)
    raise AssertionError("_consume() blev aldrig færdig")


def test_fremmed_ramme_maa_ikke_kapre_vores_alias(monkeypatch):
    """HUL 2, gennem den VIRKELIGE ``_consume()``-vej (ChatGPT's krav).

    ``detached_run`` aliaserede den FØRSTE ``system_event(kind=run)``-ramme
    ukritisk. Kom den fra et andet run, pegede aliaset et fremmed id mod vores
    log — og så var ejerskabs-tjekket ved afregningen CIRKULÆRT: det bekræftede
    et alias som rammen selv havde sat.
    """
    from core.services import run_event_log as rel

    rel.create("visible-fremmed-log", "s1")
    rel.alias("visible-fremmed-eget", "visible-fremmed-log")
    rel.create("visible-gen", "s1")

    _start(monkeypatch, [_ramme("visible-fremmed-eget")])

    assert rel._ALIASER.get("visible-fremmed-eget") == "visible-fremmed-log", (
        "en fremmed ramme maa ikke kapre vores streams alias-binding"
    )


def test_vores_egen_ramme_binder_aliaset(monkeypatch):
    """Modstykket: den ægte vej må ikke blive blind af ejerskabs-kravet."""
    from core.services import run_event_log as rel

    rel.create("visible-gen", "s1")

    _start(monkeypatch, [_ramme("visible-vores-eget")])

    assert rel._ALIASER.get("visible-vores-eget") == "visible-gen", (
        "vores eget runs id skal bindes til vores log"
    )
