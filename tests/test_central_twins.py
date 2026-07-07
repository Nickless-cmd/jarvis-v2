"""The Twins (Spec F §3) — gentagelses-detektor på tværs af tid.

Dækker: detekterer et 3+/7d incident-mønster (samme nerve+kind); ignorerer et 2× mønster; ignorerer
et spredt mønster (uden for 7-dags-vinduet); gate-gentagelse (yellow/red ≥3) og uhørt dissent (≥3);
self-safe (fejlende kilder kaster ikke); egress-fri (intet fejl-INDHOLD på eventbus — kun tællinger).
Injektion: patch de tre kilde-readere direkte (samme mock-stil som søsknene).
"""
from datetime import UTC, datetime, timedelta
from unittest import mock

from core.services import central_twins as tw


def _inc(nerve, kind, *, days_ago=0):
    ts = (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()
    return {"ts": ts, "cluster": "system", "nerve": nerve, "kind": kind,
            "severity": "error", "message": "noget gik galt"}


def _wire(*, incidents=(), gates=(), dissents=()):
    return (
        mock.patch("core.services.central_twins._incidents", return_value=list(incidents)),
        mock.patch("core.services.central_twins._gate_counts", return_value=list(gates)),
        mock.patch("core.services.central_twins._dissents", return_value=list(dissents)),
        mock.patch("core.services.central_twins._observe"),
    )


# ── detekterer 3+/7d incident-mønster ─────────────────────────────────────────

def test_detects_three_same_error_within_7d():
    incs = [_inc("streaming", "cutoff", days_ago=d) for d in (0, 1, 2)]
    p1, p2, p3, p4 = _wire(incidents=incs)
    with p1, p2, p3, p4:
        out = tw.detect_repeats()
    assert out["status"] == "ok"
    same_error = [p for p in out["patterns"]
                  if p["pattern"] == "same_error" and p["nerve"] == "streaming"]
    assert same_error and same_error[0]["count"] == 3
    assert "streaming" in same_error[0]["message"]


# ── ignorerer 2× (under tærskel) ──────────────────────────────────────────────

def test_two_occurrences_not_flagged():
    incs = [_inc("gate_x", "deny", days_ago=0), _inc("gate_x", "deny", days_ago=1)]
    p1, p2, p3, p4 = _wire(incidents=incs)
    with p1, p2, p3, p4:
        out = tw.detect_repeats()
    same_error = [p for p in out["patterns"] if p["pattern"] == "same_error"]
    assert same_error == []


# ── ignorerer spredt (uden for 7-dags-vinduet) ────────────────────────────────

def test_spread_out_beyond_window_not_flagged():
    # 3 forekomster men to ligger uden for 7 dage → kun 1 tæller → intet mønster.
    incs = [_inc("nerve_y", "err", days_ago=0),
            _inc("nerve_y", "err", days_ago=9),
            _inc("nerve_y", "err", days_ago=14)]
    p1, p2, p3, p4 = _wire(incidents=incs)
    with p1, p2, p3, p4:
        out = tw.detect_repeats()
    same_error = [p for p in out["patterns"]
                  if p["pattern"] == "same_error" and p["nerve"] == "nerve_y"]
    assert same_error == []


# ── gate-gentagelse (yellow/red ≥3 indenfor vinduet) ──────────────────────────

def test_gate_repeated_non_green_flagged():
    now = datetime.now(UTC).isoformat()
    gates = [
        {"nerve": "fact_gate", "decision": "yellow", "count": 2, "last_ts": now},
        {"nerve": "fact_gate", "decision": "red", "count": 2, "last_ts": now},
    ]
    p1, p2, p3, p4 = _wire(gates=gates)
    with p1, p2, p3, p4:
        out = tw.detect_repeats()
    gate_pats = [p for p in out["patterns"] if p["pattern"] == "repeated_non_green"]
    assert gate_pats and gate_pats[0]["nerve"] == "fact_gate"
    assert gate_pats[0]["count"] == 4


def test_gate_old_last_ts_not_flagged():
    old = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    gates = [{"nerve": "sleepy_gate", "decision": "yellow", "count": 9, "last_ts": old}]
    p1, p2, p3, p4 = _wire(gates=gates)
    with p1, p2, p3, p4:
        out = tw.detect_repeats()
    assert [p for p in out["patterns"] if p["nerve"] == "sleepy_gate"] == []


# ── uhørt dissent (≥3) ────────────────────────────────────────────────────────

def test_unheard_dissent_flagged():
    now = datetime.now(UTC).isoformat()
    dissents = [{"nerve": "memory_write_policy", "objections": 5, "last_ts": now}]
    p1, p2, p3, p4 = _wire(dissents=dissents)
    with p1, p2, p3, p4:
        out = tw.detect_repeats()
    diss = [p for p in out["patterns"] if p["pattern"] == "unheard_objection"]
    assert diss and diss[0]["count"] == 5


# ── self-safe ─────────────────────────────────────────────────────────────────

def test_failing_sources_do_not_raise():
    with mock.patch("core.runtime.db_central_incidents.list_central_incidents",
                    side_effect=RuntimeError("boom")), \
            mock.patch("core.runtime.db_gate_verdicts.read_counts", side_effect=RuntimeError("x")), \
            mock.patch("core.services.central_dissent.list_dissents", side_effect=RuntimeError("y")), \
            mock.patch("core.services.central_twins._observe"):
        out = tw.detect_repeats()
    assert out["status"] == "ok"
    assert out["count"] == 0


# ── egress-fri (§24.4) — intet fejl-INDHOLD publiceres ────────────────────────

def test_observe_publishes_no_content():
    published: list = []

    class _FakeCentral:
        def observe(self, payload):
            published.append(payload)

    incs = [_inc("secret_nerve", "secret_kind", days_ago=d) for d in (0, 1, 2)]
    with mock.patch("core.services.central_twins._incidents", return_value=incs), \
            mock.patch("core.services.central_twins._gate_counts", return_value=[]), \
            mock.patch("core.services.central_twins._dissents", return_value=[]), \
            mock.patch("core.services.central_core.central", return_value=_FakeCentral()):
        tw.detect_repeats()

    assert published, "forventede en observe"
    blob = repr(published)
    assert "secret_nerve" not in blob
    assert "secret_kind" not in blob
    assert "gik galt" not in blob
    for p in published:
        assert set(p.keys()) <= {
            "cluster", "nerve", "kind", "count",
            "incident_patterns", "gate_patterns", "dissent_patterns",
        }


# ── surface ───────────────────────────────────────────────────────────────────

def test_surface_lists_patterns():
    incs = [_inc("flappy", "timeout", days_ago=d) for d in (0, 1, 2, 3)]
    with mock.patch("core.services.central_twins._incidents", return_value=incs), \
            mock.patch("core.services.central_twins._gate_counts", return_value=[]), \
            mock.patch("core.services.central_twins._dissents", return_value=[]), \
            mock.patch("core.services.central_twins._observe"):
        surf = tw.build_twins_surface()
    assert surf["active"] is True
    assert surf["count"] >= 1
    assert any(p["nerve"] == "flappy" for p in surf["patterns"])
