"""Tilbagevendende trim af `runtime_action_outcomes.result_json` (14/11-2026).

Maalt: 1.048 MB i `result_json`, 962 MB af det i raekker aeldre end 7 dage som kun de nyeste raekker
laeses fra (`recent_runtime_action_outcomes`, LIMIT). Rigtig sqlite via isolated_runtime — ingen mock paa
SQL'en, saa en ny WHERE-gren kan ses.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

BIG = {"status": "ok", "summary": "søgning færdig", "text": "x" * 5000, "match_count": 3,
       "nested": {"deep": "y" * 2000, "n": 1}, "items": ["a" * 900, "kort"]}


def _ts(days_ago: float) -> str:
    return (datetime.now(UTC) - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%S.000000+00:00")


@pytest.fixture
def tr(isolated_runtime):
    from core.runtime.db import connect
    from core.runtime.db_core import clear_runtime_state_cache
    from core.runtime.db_runtime_signals import _runtime_action_outcome_from_row
    from core.services import events_retention, outcome_payload_trim

    clear_runtime_state_cache()

    class H:
        mod = outcome_payload_trim
        retention = events_retention
        parse = staticmethod(_runtime_action_outcome_from_row)
        _n = 0

        def add(self, result, days_ago, *, raw=None) -> int:
            H._n += 1
            body = raw if raw is not None else json.dumps(result)
            with connect() as conn:
                cur = conn.execute(
                    "INSERT INTO runtime_action_outcomes (outcome_id, action_id, decision_mode, result_status, "
                    "result_json, recorded_at) VALUES (?, 'tool:bash', 'tool', 'ok', ?, ?)",
                    (f"o-{H._n}", body, _ts(days_ago)))
                conn.commit()
                return int(cur.lastrowid)

        def raw(self, rid) -> str:
            with connect() as conn:
                return conn.execute("SELECT result_json FROM runtime_action_outcomes WHERE id=?", (rid,)).fetchone()[0]

        def row(self, rid):
            with connect() as conn:
                return self.parse(conn.execute("SELECT * FROM runtime_action_outcomes WHERE id=?", (rid,)).fetchone())

    return H()


def test_an_old_large_row_keeps_its_structure_and_loses_only_long_text(tr):
    rid = tr.add(BIG, 30)
    out = tr.mod.trim_old_outcome_payloads()
    got = json.loads(tr.raw(rid))
    assert (out["scanned"], out["trimmed"]) == (1, 1) and 6000 < out["saved_bytes"] < len(json.dumps(BIG))
    assert got["trimmed"] is True and got["status"] == "ok" and got["summary"] == "søgning færdig"
    assert got["match_count"] == 3 and got["nested"]["n"] == 1 and got["items"][1] == "kort"
    for v in (got["text"], got["nested"]["deep"], got["items"][0]):
        assert len(v) < 400 and "trimmet fra" in v
    assert got["text"].endswith("[trimmet fra 5000 tegn]")


@pytest.mark.parametrize("days,raw", [
    pytest.param(2, json.dumps(BIG), id="ny-raekke-under-7-dage"),
    pytest.param(30, json.dumps({"status": "ok", "text": "kort"}), id="lille-raekke"),
    pytest.param(30, json.dumps({"status": "ok", "text": "k" * 500}), id="under-mindstegraensen-men-med-lang-tekst"),
    pytest.param(30, json.dumps({"items": ["s" * 100] * 12}), id="kun-korte-vaerdier-ville-blive-STOERRE"),
    pytest.param(30, "{" + "z" * 2000, id="ugyldig-json"),
    pytest.param(30, json.dumps({"trimmed": True, "text": "q" * 900}), id="allerede-trimmet"),
    pytest.param(30, json.dumps(["w" * 900]), id="ikke-et-objekt"),
])
def test_rows_that_must_not_be_touched_are_left_byte_for_byte(tr, days, raw):
    rid = tr.add(None, days, raw=raw)
    out = tr.mod.trim_old_outcome_payloads()
    assert tr.raw(rid) == raw
    assert out["trimmed"] == 0 and out["saved_bytes"] == 0


def test_a_second_run_changes_nothing(tr):
    rid = tr.add(BIG, 30)
    tr.mod.trim_old_outcome_payloads()
    first = tr.raw(rid)
    again = tr.mod.trim_old_outcome_payloads()
    assert tr.raw(rid) == first and again["trimmed"] == 0 and again["scanned"] == 0


def test_the_watermark_stops_old_rows_from_being_rescanned(tr):
    """Kontrakten: raekker under vandmaerket genbesoeges ikke (ellers laeser hvert kald hele historikken)."""
    rid = tr.add(BIG, 30)
    tr.mod.trim_old_outcome_payloads()
    from core.runtime.db import connect
    with connect() as conn:                      # saet en stor, utrimmet vaerdi UNDER vandmaerket
        conn.execute("UPDATE runtime_action_outcomes SET result_json=? WHERE id=?", (json.dumps(BIG), rid))
        conn.commit()
    out = tr.mod.trim_old_outcome_payloads()
    assert out["scanned"] == 0 and tr.raw(rid) == json.dumps(BIG)


def test_rows_added_after_a_run_are_picked_up_by_the_next(tr):
    tr.add(BIG, 30)
    tr.mod.trim_old_outcome_payloads()
    late = tr.add(BIG, 20)
    out = tr.mod.trim_old_outcome_payloads()
    assert out["trimmed"] == 1 and json.loads(tr.raw(late))["trimmed"] is True


def test_a_row_that_was_too_new_is_trimmed_once_it_has_aged(tr, monkeypatch):
    fresh = tr.add(BIG, 2)
    tr.mod.trim_old_outcome_payloads()
    assert tr.raw(fresh) == json.dumps(BIG)
    monkeypatch.setattr(tr.mod, "_full_result_days", lambda: 1)       # vinduet krympes: nu er den gammel
    assert tr.mod.trim_old_outcome_payloads()["trimmed"] == 1


def test_max_rows_caps_one_call_and_later_calls_finish_the_job(tr):
    ids = [tr.add(BIG, 30) for _ in range(10)]
    first = tr.mod.trim_old_outcome_payloads(max_rows=4, batch=2)
    assert first["scanned"] == 4 and first["trimmed"] == 4
    assert sum(json.loads(tr.raw(i)).get("trimmed") is True for i in ids) == 4
    while tr.mod.trim_old_outcome_payloads(max_rows=4, batch=2)["scanned"]:
        pass
    assert all(json.loads(tr.raw(i)).get("trimmed") is True for i in ids)


def test_a_trimmed_row_is_still_read_correctly_by_the_runtime_readers(tr):
    rid = tr.add(BIG, 30)
    tr.mod.trim_old_outcome_payloads()
    got = tr.row(rid)
    assert got["result_status"] == "ok" and got["result"]["status"] == "ok"
    assert got["result"]["summary"] == "søgning færdig" and got["result"]["trimmed"] is True


def test_the_full_result_window_comes_from_settings_with_a_floor_of_one_day(tr, monkeypatch):
    class S:
        extra = {"action_outcome_full_result_days": 0}

    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: S())
    assert tr.mod._full_result_days() == 1
    S.extra = {"action_outcome_full_result_days": 21}
    assert tr.mod._full_result_days() == 21
    S.extra = {}
    assert tr.mod._full_result_days() == tr.mod.FULL_RESULT_DAYS


def test_a_database_failure_is_reported_never_raised(tr, monkeypatch):
    def boom():
        raise RuntimeError("database is locked")

    monkeypatch.setattr("core.runtime.db.connect", boom)
    out = tr.mod.trim_old_outcome_payloads()
    assert "database is locked" in out["error"] and out["trimmed"] == 0


def test_the_recurring_retention_pass_runs_the_trim(tr):
    rid = tr.add(BIG, 30)
    out = tr.retention.prune_telemetry_tables()
    assert out["runtime_action_outcomes_payload_trim"]["trimmed"] == 1
    assert json.loads(tr.raw(rid))["trimmed"] is True
