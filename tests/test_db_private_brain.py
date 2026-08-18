"""DB-lag for private_brain: boilerplate-gate på insertet + alders-forespørgsel.

Boilerplate-gaten sidder på insert_private_brain_record — det ENE choke-point ALLE
skrive-stier passerer (Bjørn 18. aug 2026). Se INNER_LIFE_AUDIT.md #3.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.runtime.db import (
    insert_private_brain_record,
    get_private_brain_record,
    list_private_brain_records,
    list_private_brain_records_older_than,
    update_private_brain_record_status,
)
from core.runtime.db_private_brain import _is_boilerplate_carry


def _ins(rid, *, summary, detail="d", hours_old=0.0):
    ts = (datetime.now(UTC) - timedelta(hours=hours_old)).isoformat()
    return insert_private_brain_record(
        record_id=rid, record_type="thought-stream-fragment", layer="private_brain",
        session_id="s", run_id="r", focus="f", summary=summary, detail=detail,
        source_signals="", confidence="medium", created_at=ts,
    )


class TestBoilerplateGateOnInsert:
    def test_boilerplate_skrives_IKKE(self, isolated_runtime):
        r = _ins("bp1", summary="I notice a quiet inner thread around x",
                 detail="A private inner note may return as bounded reflection when grounded in visible work.")
        assert r == {}
        assert get_private_brain_record("bp1") is None

    def test_daemon_direkte_sti_dækkes_også(self, isolated_runtime):
        # Gaten sidder på selve insertet → dækker ENHVER caller (også daemons der kalder
        # direkte uden om _try_private). Her: den konstante inner-note-detail via direkte insert.
        assert _ins("bp2", summary="hvad som helst",
                    detail="A private inner note may return as bounded reflection when grounded in visible work.") == {}
        assert get_private_brain_record("bp2") is None

    def test_ægte_materiale_skrives(self, isolated_runtime):
        r = _ins("real1", summary="Er jeg blot en skygge af mig selv?", detail="refleksion")
        assert r and r.get("record_id") == "real1"
        assert get_private_brain_record("real1") is not None


class TestAgeQuery:
    def test_older_than_filtrerer_på_alder(self, isolated_runtime):
        _ins("young", summary="frisk tanke", hours_old=1)
        _ins("old", summary="gammel tanke", hours_old=30)
        cut = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
        got = list_private_brain_records_older_than(status="active", older_than_iso=cut, limit=50)
        ids = {r["record_id"] for r in got}
        assert "old" in ids and "young" not in ids

    def test_older_than_respekterer_max_salience(self, isolated_runtime):
        from core.runtime.db import update_private_brain_record_salience
        _ins("old-hi", summary="vigtig gammel", hours_old=30)
        update_private_brain_record_salience("old-hi", 0.9)
        cut = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
        got = list_private_brain_records_older_than(
            status="active", older_than_iso=cut, max_salience=0.7, limit=50)
        assert all(r["record_id"] != "old-hi" for r in got)  # høj salience filtreres fra


def test_helper_direkte():
    assert _is_boilerplate_carry("I notice things feel steadier around du", "") is True
    assert _is_boilerplate_carry("en ægte tanke", "ægte detalje") is False
    # Bevidst IKKE boilerplate (kan bære signal i focus):
    assert _is_boilerplate_carry("Idle consolidation settled bounded internal", "") is False
