from core.runtime.db import connect, init_db


def test_costs_table_has_user_id_column():
    # init_db() runs the additive schema migration (CREATE/ALTER-if-missing,
    # idempotent) against the real runtime DB, same pattern as
    # tests/test_credit_assignment.py. The additive column must be present.
    init_db()
    with connect() as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(costs)")}
    assert "user_id" in cols


import core.costing.ledger as ledger


class _FakeConn:
    def __init__(self, sink):
        self.sink = sink
    def execute(self, sql, params=None):
        if params is not None:
            self.sink["sql"] = " ".join(sql.split())
            self.sink["params"] = params
        return self
    def commit(self):
        self.sink["committed"] = True
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def test_record_cost_writes_user_id(monkeypatch):
    sink = {}
    monkeypatch.setattr(ledger, "connect", lambda: _FakeConn(sink))
    # keep the egress side-effect from firing during the test
    import core.services.central_llm_egress as egress
    monkeypatch.setattr(egress, "observe", lambda **k: None)
    ledger.record_cost(lane="agent", provider="deepseek", model="deepseek-v4-flash",
                       input_tokens=10, output_tokens=5, cost_usd=0.001, user_id="member_x")
    assert "user_id" in sink["sql"]
    assert "member_x" in sink["params"]


def test_record_cost_user_id_defaults_empty(monkeypatch):
    sink = {}
    monkeypatch.setattr(ledger, "connect", lambda: _FakeConn(sink))
    import core.services.central_llm_egress as egress
    monkeypatch.setattr(egress, "observe", lambda **k: None)
    ledger.record_cost(lane="agent", provider="deepseek", model="deepseek-v4-flash",
                       input_tokens=1, output_tokens=1, cost_usd=0.0)
    # additive default: no user_id passed -> '' written, old call sites unaffected
    assert sink["params"][-2] == ""  # user_id is second-to-last (before created_at)
