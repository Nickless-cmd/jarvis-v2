"""WS3: central_cost_surface — aggregat + fejl-tolerant saldo."""
from __future__ import annotations

import core.services.central_cost_surface as ccs
from core.costing.ledger import record_cost


def _seed(monkeypatch):
    # saldo-kald må ALDRIG ramme nettet i test
    monkeypatch.setattr(
        ccs, "_deepseek_balance_detail",
        lambda: {"total": None, "granted": None, "topped_up": None},
    )
    # Prisen afhaenger af klokken siden 3229cf788 — fastlaas til off-peak.
    import core.services.llm_pricing as lp
    monkeypatch.setattr(lp, "er_myldretid", lambda at=None: False)


def test_surface_aggregates_today(isolated_runtime, monkeypatch):
    _seed(monkeypatch)
    # 1M cache_miss + 1M output på flash, off-peak = 0,15 + 0,60
    record_cost(lane="cheap", provider="deepseek", model="deepseek-v4-flash",
                cost_usd=0.0, cache_miss_tokens=1_000_000, output_tokens=1_000_000)
    s = ccs.build_cost_surface(window="today")
    today = s["windows"]["today"]
    assert today["calls"] == 1
    assert today["output_tokens"] == 1_000_000
    assert abs(today["cost_usd"] - 0.75) < 1e-3
    assert "7d" in s["windows"] and "30d" in s["windows"]


def test_cache_hit_pct(isolated_runtime, monkeypatch):
    _seed(monkeypatch)
    record_cost(lane="cheap", provider="deepseek", model="deepseek-v4-flash",
                cost_usd=0.0, cache_hit_tokens=800, cache_miss_tokens=200, output_tokens=10)
    s = ccs.build_cost_surface(window="today")
    assert abs(s["windows"]["today"]["cache_hit_pct"] - 80.0) < 1e-6


def test_breakdown_split_by_lane(isolated_runtime, monkeypatch):
    _seed(monkeypatch)
    record_cost(lane="inner", provider="deepseek", model="deepseek-v4-flash",
                cost_usd=0.0, cache_miss_tokens=1_000_000, output_tokens=0)
    record_cost(lane="cheap-balanced", provider="deepseek", model="deepseek-v4-flash",
                cost_usd=0.0, cache_miss_tokens=1_000_000, output_tokens=0)
    s = ccs.build_cost_surface(window="today")
    lanes = {b["lane"] for b in s["breakdown"]}
    assert {"inner", "cheap-balanced"} <= lanes


def test_provider_filter(isolated_runtime, monkeypatch):
    _seed(monkeypatch)
    record_cost(lane="cheap", provider="deepseek", model="deepseek-v4-flash",
                cost_usd=0.0, cache_miss_tokens=1_000_000, output_tokens=0)
    record_cost(lane="cheap", provider="ollama", model="local",
                cost_usd=0.0, output_tokens=100)
    s = ccs.build_cost_surface(window="today", provider="deepseek")
    assert all(b["provider"] == "deepseek" for b in s["breakdown"])
    assert s["windows"]["today"]["calls"] == 1  # kun deepseek talt


def test_balance_fault_tolerant(isolated_runtime, monkeypatch):
    # simuler saldo-fejl → surface vælter IKKE, felterne bliver None
    def boom():
        raise RuntimeError("offline")
    monkeypatch.setattr(ccs, "_deepseek_balance_detail", boom)
    s = ccs.build_cost_surface(window="today")
    assert "windows" in s
    assert s["deepseek_balance_usd"] is None
    assert s["deepseek_balance_detail"] == {"total": None, "granted": None, "topped_up": None}


def test_balance_detail_surfaces_granted(isolated_runtime, monkeypatch):
    # kompensations-credits skal være SYNLIGE i surface — ikke kun i totalen
    monkeypatch.setattr(
        ccs, "_deepseek_balance_detail",
        lambda: {"total": "195.72", "granted": "20.81", "topped_up": "174.90"},
    )
    s = ccs.build_cost_surface(window="today")
    assert s["deepseek_balance_usd"] == "195.72"
    assert s["deepseek_balance_detail"]["granted"] == "20.81"
    assert s["deepseek_balance_detail"]["topped_up"] == "174.90"


def test_real_balance_never_raises(monkeypatch):
    # _deepseek_balance_detail selv: manglende config → alle None, ingen exception
    monkeypatch.setattr(ccs.os.path, "expanduser", lambda p: "/nonexistent/runtime.json")
    ccs._BAL_CACHE["ts"] = 0.0
    assert ccs._deepseek_balance_detail() == {"total": None, "granted": None, "topped_up": None}
    # wrapper'en er bagudkompatibel og giver stadig kun total
    assert ccs._deepseek_balance() is None
