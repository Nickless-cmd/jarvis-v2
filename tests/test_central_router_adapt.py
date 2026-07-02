"""Tests for DEN MODIGE DEL — Tråd 1 routing-præference-lærer (shadow-first, §8/B4, aldrig deep-tier)."""
from __future__ import annotations

import pytest

from core.services import central_router_adapt as ra
from core.services import central_hypothesis_governance as gov


@pytest.fixture(autouse=True)
def _reset(isolated_runtime):
    gov._ANCHORED_BASELINES.clear()
    ra._kv_set(ra._LIVE_FLAG, False)
    ra._kv_set(ra._PREF_KEY, {})
    ra._kv_set(ra._SHADOW_KEY, {})
    yield


def _seed_model_meta(winner, n, *, outcome="supported"):
    """Seed n resolverede model_meta-hypoteser hvor `winner` vinder."""
    from core.runtime.db import connect
    from core.services import central_hypothesis_generator as gen
    gen.ensure_schema()
    with connect() as c:
        for i in range(n):
            fam = f"latency:{winner}>ollama/slow"
            c.execute(
                "INSERT INTO central_hypotheses (hyp_id, source, statement, prediction, "
                "null_hypothesis, success_criterion, sample_size, ttl_seconds, provenance_json, "
                "confidence, status, outcome, grounded_samples, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?, 'resolved', ?, 5, '2026-07-02T00:00:00Z')",
                (f"{winner}-{i}", "model_meta", "s", "p", "n", "sc", 5, 3600,
                 '{"mechanism":"model_meta","family":"' + fam + '"}', 0.8, outcome))
        c.commit()


def _seed_runs(model_key, n=20):
    """Gør en model 'konfigureret' (set køre) så præference-læreren tør pege på den."""
    from core.runtime.db import connect
    prov, mod = model_key.split("/", 1)
    with connect() as c:
        for i in range(n):
            c.execute("INSERT INTO visible_runs (run_id, lane, provider, model, status, started_at, "
                      "finished_at) VALUES (?,?,?,?,?,?,?)",
                      (f"{model_key}-{i}", "visible", prov, mod, "completed",
                       "2026-07-02T10:00:00+00:00", "2026-07-02T10:00:01+00:00"))
        c.commit()


def test_no_preference_without_enough_support(isolated_runtime):
    _seed_model_meta("dsk/flash", 2)          # < _MIN_SUPPORT
    _seed_runs("dsk/flash")
    assert ra.compute_preference()["enough"] is False


def test_preference_forms_from_resolved_contrasts(isolated_runtime):
    _seed_model_meta("dsk/flash", 5)
    _seed_runs("dsk/flash")
    pref = ra.compute_preference()
    assert pref["enough"] is True and pref["preferred"] == "dsk/flash" and pref["support"] == 5


def test_never_prefers_unconfigured_model(isolated_runtime):
    """Peg ALDRIG på en model der ikke er set køre (ikke konfigureret)."""
    _seed_model_meta("ghost/model", 9)        # ingen runs → ikke konfigureret
    assert ra.compute_preference()["enough"] is False


def test_never_prefers_deep_tier(isolated_runtime):
    """SPEC §3: aldrig præference-override på reasoning/deep-tier."""
    _seed_model_meta("openai/o1-reasoning", 9)
    _seed_runs("openai/o1-reasoning")
    assert ra.compute_preference()["enough"] is False   # deep-tier filtreret bort


def test_shadow_records_but_does_not_write_live(isolated_runtime):
    _seed_model_meta("dsk/flash", 6); _seed_runs("dsk/flash")
    res = ra.run_router_adapt_tick()
    assert res["mode"] == "shadow" and res["applied"] is False
    assert ra._kv_get(ra._SHADOW_KEY, {}).get("visible", {}).get("model") == "dsk/flash"
    assert ra._kv_get(ra._PREF_KEY, {}) == {}          # live URØRT
    assert ra.get_live_preference("visible") is None     # konsument ser intet i shadow


def test_live_writes_preference(isolated_runtime):
    _seed_model_meta("dsk/flash", 6); _seed_runs("dsk/flash")
    ra._kv_set(ra._LIVE_FLAG, True)
    res = ra.run_router_adapt_tick()
    assert res["mode"] == "live" and res["applied"] is True and res["gate"] != "rollback"
    p = ra.get_live_preference("visible")
    assert p and p["model"] == "dsk/flash"


def test_consumer_api_returns_none_in_shadow(isolated_runtime):
    ra._kv_set(ra._PREF_KEY, {"visible": {"model": "dsk/flash", "strength": 0.5}})
    # flag OFF → konsumenten får None (default routing bevares)
    assert ra.get_live_preference("visible") is None


def test_tick_self_safe_empty(isolated_runtime):
    out = ra.run_router_adapt_tick()
    assert out["status"] == "ok" and out["applied"] is False


# ── KONSUMENTEN (resolve_visible_model) — Tråd 1 live-wire ────────────────────────────
def test_resolver_shadow_returns_default(isolated_runtime):
    """Default/shadow (flag OFF) → uændret: base = default (ingen præference anvendt)."""
    ra._kv_set(ra._PREF_KEY, {"visible": {"model": "dsk/flash", "strength": 0.5}})  # men flag OFF
    p, m = ra.resolve_visible_model(default_provider="glm", default_model="glm-5.2:cloud")
    assert (p, m) == ("glm", "glm-5.2:cloud")


def test_resolver_live_applies_preference(isolated_runtime):
    ra._kv_set(ra._LIVE_FLAG, True)
    ra._kv_set(ra._PREF_KEY, {"visible": {"model": "deepseek/flash", "strength": 0.6}})
    p, m = ra.resolve_visible_model(default_provider="glm", default_model="glm-5.2:cloud")
    assert (p, m) == ("deepseek", "flash")       # præference anvendt


def test_resolver_explicit_override_always_wins(isolated_runtime):
    """SIKKERHED: rolle-clampet override (fx member→ollama) må ALDRIG overrules af præferencen."""
    ra._kv_set(ra._LIVE_FLAG, True)
    ra._kv_set(ra._PREF_KEY, {"visible": {"model": "deepseek/flash", "strength": 0.9}})
    p, m = ra.resolve_visible_model(provider_override="ollama", model_override="flash:cloud",
                                    default_provider="glm", default_model="glm-5.2:cloud")
    assert (p, m) == ("ollama", "flash:cloud")   # override ukrænkelig — præference rørte den IKKE


def test_resolver_never_deep_tier(isolated_runtime):
    """Selv live: en deep-tier præference ignoreres (get_live_preference-værn) → default bevares."""
    ra._kv_set(ra._LIVE_FLAG, True)
    ra._kv_set(ra._PREF_KEY, {"visible": {"model": "openai/o1-reasoning", "strength": 0.9}})
    p, m = ra.resolve_visible_model(default_provider="glm", default_model="glm-5.2:cloud")
    assert (p, m) == ("glm", "glm-5.2:cloud")
