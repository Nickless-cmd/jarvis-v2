import sqlite3
from unittest import mock
import pytest
from core.services import central_merovingian as m


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "m.db")
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE central_hypotheses (hyp_id TEXT PRIMARY KEY, statement TEXT,
        prediction TEXT, confidence REAL, grounded_samples INT, status TEXT, source TEXT,
        provenance_json TEXT, notation_il TEXT, outcome TEXT, resolved_at TEXT)""")
    conn.commit(); conn.close()

    def _connect():
        c = sqlite3.connect(path); c.row_factory = sqlite3.Row; return c

    with mock.patch("core.services.central_merovingian.connect", side_effect=_connect), \
            mock.patch("core.services.central_merovingian._observe"):
        yield path


def _prior(path, source, statuses):
    c = sqlite3.connect(path)
    for i, st in enumerate(statuses):
        c.execute("""INSERT INTO central_hypotheses (hyp_id, statement, prediction, confidence,
            grounded_samples, status, source, provenance_json, notation_il, resolved_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (f"{source}-p{i}", "s", "p", 0.5, 3, st, source, "{}", "", "2026-01-01T00:00:00+00:00"))
    c.commit(); c.close()


# ── modhypotese-generering (symbolsk, ingen LLM) ──

def test_counter_negates_causal():
    assert m.generate_counter({"notation_il": "A -> B"})["type"] == "negated_consequent"


def test_counter_reverses_direction():
    c = m.generate_counter({"statement": "loop_persistence bør øges"})
    assert c["type"] == "reversed_direction" and "SÆNKES" in c["counter"]


def test_counter_fallback_wrong_variable():
    assert m.generate_counter({"statement": "noget neutralt"})["type"] == "wrong_variable"


# ── devil's advocate / track-record ──

def test_track_record_supports_counter_when_history_failed(db):
    _prior(db, "prediction_error", ["falsified", "falsified", "expired"])
    tr = m.variable_track_record("prediction_error:fam")
    assert tr["support"] is True and "fejlede" in tr["note"]


def test_track_record_no_history_forces_caution(db):
    tr = m.variable_track_record("brand_new:fam")
    assert tr["support"] is True and "ny variabel" in tr["note"]


def test_good_track_record_approves(db):
    _prior(db, "good_src", ["confirmed", "confirmed", "confirmed", "confirmed"])
    tr = m.variable_track_record("good_src:fam")
    assert tr["support"] is False


# ── review + cooling-off (shadow: logges, blokerer ikke) ──

def test_review_challenges_and_records(db):
    _prior(db, "prediction_error", ["falsified", "falsified", "expired"])
    r = m.review({"hyp_id": "h1", "statement": "øg X", "source": "prediction_error",
                  "provenance_json": "{}", "notation_il": "A -> B"})
    assert r["verdict"] == "challenged" and r["explanation_required"] is True
    assert m.list_challenges() and m.list_challenges()[0]["hyp_id"] == "h1"


def test_review_approves_good_track_record(db):
    _prior(db, "good_src", ["confirmed", "confirmed", "confirmed"])
    r = m.review({"hyp_id": "h9", "statement": "øg X", "source": "good_src", "provenance_json": "{}"})
    assert r["verdict"] == "approved"


def test_shadow_never_blocks(db):
    _prior(db, "prediction_error", ["falsified", "falsified", "falsified"])
    m.review({"hyp_id": "h1", "statement": "øg X", "source": "prediction_error", "provenance_json": "{}"})
    # default = shadow → is_adoption_blocked ALTID False selv med aktiv cooling-off
    assert m.is_adoption_blocked("h1") is False


def test_enforce_flag_blocks_active_cooling(db):
    _prior(db, "prediction_error", ["falsified", "falsified", "falsified"])
    m.review({"hyp_id": "h1", "statement": "øg X", "source": "prediction_error", "provenance_json": "{}"})
    with mock.patch("core.services.central_merovingian._enforced", return_value=True):
        assert m.is_adoption_blocked("h1") is True
        # forklaring løser den → ikke længere blokeret
        assert m.resolve_challenge("h1", explanation="A->B holder fordi Z")["ok"] is True
        assert m.is_adoption_blocked("h1") is False


def test_repeat_challenges_trigger_abandon_window(db):
    _prior(db, "prediction_error", ["falsified", "falsified", "falsified"])
    for i in range(3):
        m.review({"hyp_id": f"h{i}", "statement": "øg X", "source": "prediction_error",
                  "provenance_json": '{"family":"fam"}'})
    rows = m.list_challenges(active_only=False)
    assert any(r["status"] == "abandon_window" for r in rows)


def test_expire_cooling_marks_expired(db):
    _prior(db, "prediction_error", ["falsified", "falsified", "falsified"])
    m.review({"hyp_id": "h1", "statement": "øg X", "source": "prediction_error", "provenance_json": "{}"})
    # tving cooling til fortiden
    c = sqlite3.connect(db)
    c.execute("UPDATE central_merovingian SET cools_off_at='2000-01-01T00:00:00+00:00'")
    c.commit(); c.close()
    assert m.expire_cooling()["expired"] == 1
