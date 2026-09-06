"""Runs er bruger-scopede. Andre skal kun se det der vedroerer dem.

`/mc/runs` returnerede ALLE brugeres runs til enhver autentificeret kalder.
Med én bruger er det usynligt; i det oejeblik der er en member eller gaest,
er det en aegte eksponering. Det er en sikkerheds-egenskab, saa den laases
her — ikke i visningen.
"""
import uuid

import pytest

from core.runtime.db import connect
from core.runtime.db_visible import _run_user_scope, recent_visible_runs


@pytest.fixture
def runs():
    """En run pr. ejer: bjoern, en anden, og én uden ejer.

    `user_id` er NOT NULL i skemaet, saa systemets egne autonome koersler
    gemmes med TOM STRENG frem for NULL. Scopingen daekker begge former.
    """
    mine = f"scope-{uuid.uuid4().hex[:8]}"
    ids = {}
    with connect() as c:
        for navn, uid in (("min", "bjorn-proeve"), ("anden", "anden-proeve"), ("ingen", "")):
            rid = f"{mine}-{navn}"
            ids[navn] = rid
            c.execute(
                "INSERT INTO visible_runs "
                "(run_id, lane, provider, model, status, started_at, "
                " finished_at, user_id) "
                "VALUES (?, 'visible', 'proeve', 'proeve', 'completed', "
                "datetime('now'), datetime('now'), ?)",
                (rid, uid),
            )
        c.commit()
    yield ids
    with connect() as c:
        c.execute("DELETE FROM visible_runs WHERE run_id LIKE ?", (f"{mine}%",))
        c.commit()


def _ids(rows):
    return {str(r.get("run_id")) for r in rows}


def test_uden_user_id_filtreres_der_ikke(runs):
    """43 interne kaldere er daemoner — de SKAL se hele billedet."""
    fundet = _ids(recent_visible_runs(limit=200))
    assert runs["min"] in fundet
    assert runs["anden"] in fundet


def test_en_fremmed_ser_KUN_sine_egne(runs):
    fundet = _ids(recent_visible_runs(limit=200, user_id="anden-proeve",
                                      include_unassigned=False))
    assert runs["anden"] in fundet
    assert runs["min"] not in fundet, "en anden brugers run maa ALDRIG med"
    assert runs["ingen"] not in fundet, "ejerloese er systemets, ikke deres"


def test_owner_ser_egne_OG_systemets_ejerloese(runs):
    """Autonome koersler har ingen user_id — de hoerer til ham."""
    fundet = _ids(recent_visible_runs(limit=200, user_id="bjorn-proeve",
                                      include_unassigned=True))
    assert runs["min"] in fundet
    assert runs["ingen"] in fundet
    assert runs["anden"] not in fundet, "heller ikke owner ser en ANDEN brugers run"


def test_scope_fragmentet_er_parametriseret():
    """Ingen streng-interpolation af bruger-id — det er en WHERE med parameter."""
    sql, params = _run_user_scope("nogen", False)
    assert "?" in sql
    assert params == ("nogen",)
    assert "nogen" not in sql


def test_tom_bruger_er_intet_filter():
    assert _run_user_scope("", True)[0] == "1=1"
    assert _run_user_scope(None, False)[0] == "1=1"
