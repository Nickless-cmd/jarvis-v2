from __future__ import annotations

import pytest

from central_cli import datasource as ds


class FakeClient:
    def __init__(self, data):
        self._d = data

    def get_json(self, path, params=None):
        return self._d[path]


class RaisingClient:
    def get_json(self, path, params=None):
        raise RuntimeError("boom")


def test_agents_roster_shape():
    client = FakeClient({
        "/central/agents": {
            "roster": [{
                "model_key": "groq/x",
                "provider": "groq",
                "model": "x",
                "status": "inactive",
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
                "last_run_at": "",
                "current_activity": "",
                "tool_calls": 0,
                "role": "",
            }],
        },
    })
    rows = ds.agents(client)
    assert len(rows) == 1
    r = rows[0]
    assert r["model_key"] == "groq/x"
    assert r["provider"] == "groq"
    assert r["model"] == "x"
    assert r["status"] == "inactive"
    # raw roster row carried through for side-panel
    assert r["raw"]["model_key"] == "groq/x"


def test_agents_legacy_backward_compat():
    client = FakeClient({
        "/central/agents": {
            "agents": [{
                "agent_id": "a1",
                "role": "worker",
                "status": "active",
                "tokens_burned": 123,
            }],
        },
    })
    rows = ds.agents(client)
    assert len(rows) == 1
    r = rows[0]
    assert r["agent_id"] == "a1"
    assert r["role"] == "worker"
    assert r["status"] == "active"
    assert r["tokens_burned"] == 123
    assert r["raw"]["agent_id"] == "a1"


def test_balancer_shape():
    client = FakeClient({
        "/mc/cheap-balancer-state": {
            "header": {"total_slots": 2, "healthy": 1, "cooldown": 0},
            "slots": [{
                "slot_id": "groq::x::default",
                "provider": "groq",
                "model": "x",
                "auth_profile": "default",
                "egress": "home",
                "status": "healthy",
                "weight": 1.0,
                "daily_headroom": 0.6,
                "daily_used": 4,
                "daily_limit": 10,
                "rpm_used": 1,
                "rpm_limit": 30,
                "last_success_at": "2026-07-16T00:00:00+00:00",
                "success_rate": 0.95,
                "daily_observed": True,
                "stale": False,
            }],
        },
    })
    out = ds.balancer(client)
    assert out["header"]["total_slots"] == 2
    assert len(out["rows"]) == 1
    row = out["rows"][0]
    assert row["slot_id"] == "groq::x::default"
    assert row["provider"] == "groq"
    assert row["egress"] == "home"
    assert row["status"] == "healthy"
    assert row["weight"] == 1.0
    assert row["daily_headroom"] == 0.6
    assert row["raw"]["slot_id"] == "groq::x::default"


def test_balancer_self_safe():
    out = ds.balancer(RaisingClient())
    assert out == {"header": {}, "rows": []}
