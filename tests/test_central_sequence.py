"""Tests for core/services/central_sequence.py — Tråd 4: Centralen træner sig selv (Markov, ikke LLM)."""
from __future__ import annotations

import pytest

from core.services import central_sequence as sq
from core.services import central_hypothesis_governance as gov


@pytest.fixture(autouse=True)
def _reset(isolated_runtime):
    sq.ensure_schema()
    sq._kv_set(sq._CURSOR_KEY, 0)
    yield


def _fake_stream(monkeypatch, fams: list[str], *, start_id: int = 1):
    """Byg en syntetisk event-strøm (id,kind) og patch event_bus.recent til at returnere den."""
    rows = [{"id": start_id + i, "kind": f"{f}.x"} for i, f in enumerate(fams)]
    from core.eventbus.bus import event_bus
    monkeypatch.setattr(event_bus, "recent", lambda limit=50: list(reversed(rows)))  # bus giver DESC
    return rows


def test_learn_counts_transitions(monkeypatch):
    _fake_stream(monkeypatch, ["runtime", "tool", "runtime", "tool", "cost"])
    res = sq.learn_from_stream()
    # overgange: runtime→tool, tool→runtime, runtime→tool, tool→cost  = 4
    assert res["learned"] == 4
    assert sq.transition_prob("runtime", "tool") == pytest.approx(1.0)   # runtime går ALTID til tool
    assert sq.transition_prob("tool", "runtime") == pytest.approx(0.5)   # tool→{runtime,cost}
    assert sq.transition_prob("tool", "cost") == pytest.approx(0.5)


def test_cursor_prevents_double_count(monkeypatch):
    _fake_stream(monkeypatch, ["runtime", "tool", "cost"])
    first = sq.learn_from_stream()
    assert first["learned"] == 2
    # anden kørsel på SAMME strøm må ikke tælle igen (cursor står ved sidste id)
    second = sq.learn_from_stream()
    assert second["learned"] == 0


def test_cursor_advances_on_new_events(monkeypatch):
    _fake_stream(monkeypatch, ["runtime", "tool"], start_id=1)
    sq.learn_from_stream()
    # ny strøm der fortsætter (id 2,3) — kun overgang tool(2)→cost(3) er ny
    _fake_stream(monkeypatch, ["tool", "cost"], start_id=2)
    res = sq.learn_from_stream()
    assert res["learned"] == 1
    assert sq.transition_prob("tool", "cost") == pytest.approx(1.0)


def test_predict_next_ranks(monkeypatch):
    _fake_stream(monkeypatch, ["a", "b", "a", "b", "a", "c"])
    sq.learn_from_stream()
    preds = sq.predict_next("a")
    assert preds[0]["to"] == "b" and preds[0]["prob"] > preds[-1]["prob"]


def test_detect_surprise_on_rare_transition(monkeypatch):
    """Model har lært runtime→tool ~altid; en sjælden runtime→cost i vinduet = overraskelse."""
    from core.runtime.db import connect
    with connect() as c:
        c.execute("INSERT INTO central_sequence_transitions (from_fam,to_fam,count) VALUES ('runtime','tool',100)")
        c.execute("INSERT INTO central_sequence_transitions (from_fam,to_fam,count) VALUES ('runtime','cost',1)")
        c.commit()
    # P(cost|runtime) = 1/101 ≈ 0.0099 < 0.05, from_total=101 ≥ 20 → surprise
    _fake_stream(monkeypatch, ["runtime", "cost"])
    surprises = sq.detect_surprises()
    assert any(s["from_family"] == "runtime" and s["to_family"] == "cost" for s in surprises)


def test_no_surprise_when_from_total_too_low(monkeypatch):
    """Uden nok data om from-familien (< min_from_total) må intet flagges (usikkerhed ≠ overraskelse)."""
    from core.runtime.db import connect
    with connect() as c:
        c.execute("INSERT INTO central_sequence_transitions (from_fam,to_fam,count) VALUES ('runtime','tool',3)")
        c.commit()
    _fake_stream(monkeypatch, ["runtime", "cost"])
    assert sq.detect_surprises() == []


def test_learning_passes_through_gate(monkeypatch):
    """§8.2: aggregatet SKAL passere gate_learning_input (lærings-membranen)."""
    called = []
    orig = gov.gate_learning_input
    monkeypatch.setattr(gov, "gate_learning_input", lambda p: called.append(dict(p)) or orig(p))
    _fake_stream(monkeypatch, ["runtime", "tool", "cost"])
    sq.learn_from_stream()
    assert called and "count" in called[0]   # aggregat-skalarer krydsede membranen


def test_tick_is_self_safe(monkeypatch):
    _fake_stream(monkeypatch, ["runtime", "tool"])
    out = sq.run_sequence_tick()
    assert out["status"] == "ok"


def test_surface_reports_model_size(monkeypatch):
    _fake_stream(monkeypatch, ["runtime", "tool", "cost"])
    sq.learn_from_stream()
    surf = sq.build_central_sequence_surface()
    assert surf["active"] is True and surf["transitions_learned"] >= 1
