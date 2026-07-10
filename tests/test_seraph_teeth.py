from __future__ import annotations
import core.services.central_seraph as seraph


def test_seraph_shadow_permits_all(monkeypatch):
    monkeypatch.setattr(seraph, "_seraph_enforced", lambda: False)
    # I shadow: alt passerer uden at røre DB
    assert seraph.may_surface_dream_hypothesis("any-id") is True


def test_seraph_enforced_gates_on_confidence(monkeypatch):
    monkeypatch.setattr(seraph, "_seraph_enforced", lambda: True)
    class _Row(dict):
        def __getitem__(self, k): return dict.__getitem__(self, k)
    class _Conn:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, q, args):
            hid = args[0]
            class _C:
                def fetchone(_self):
                    return {"confidence": 0.8} if hid == "mature" else {"confidence": 0.2}
            return _C()
    monkeypatch.setattr("core.runtime.db.connect", lambda: _Conn())
    assert seraph.may_surface_dream_hypothesis("mature") is True    # 0.8 ≥ 0.5
    assert seraph.may_surface_dream_hypothesis("immature") is False  # 0.2 < 0.5


def test_seraph_fail_open_on_unknown(monkeypatch):
    monkeypatch.setattr(seraph, "_seraph_enforced", lambda: True)
    class _Conn:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, q, args):
            class _C:
                def fetchone(_self): return None  # ukendt id
            return _C()
    monkeypatch.setattr("core.runtime.db.connect", lambda: _Conn())
    assert seraph.may_surface_dream_hypothesis("ghost") is True  # fail-open


def test_seraph_default_shadow():
    assert seraph._seraph_enforced() is False
