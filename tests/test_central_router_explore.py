"""Tests for Tråd 1 EKSPLORATIONS-ARM — sample alt-model på autonome runs (shadow-first, sikkert)."""
from __future__ import annotations

import pytest

from core.services import central_router_explore as ex
from core.services import central_router_adapt as ra


@pytest.fixture(autouse=True)
def _reset(isolated_runtime):
    ex._kv_set(ex._EXPLORE_FLAG, False)
    ex._kv_set(ex._COUNTER_KEY, 0)
    yield


def _seed_models():
    """To modeller set køre (konfigureret): default deepseek/flash (mange) + glm (få)."""
    from core.runtime.db import connect
    with connect() as c:
        for i in range(30):
            c.execute("INSERT INTO visible_runs (run_id, lane, provider, model, status, started_at, "
                      "finished_at) VALUES (?,?,?,?,?,?,?)",
                      (f"d{i}", "visible", "deepseek", "deepseek-v4-flash", "completed",
                       "2026-07-02T10:00:00+00:00", "2026-07-02T10:00:01+00:00"))
        for i in range(4):
            c.execute("INSERT INTO visible_runs (run_id, lane, provider, model, status, started_at, "
                      "finished_at) VALUES (?,?,?,?,?,?,?)",
                      (f"g{i}", "visible", "ollama", "glm-5.2:cloud", "completed",
                       "2026-07-02T10:00:00+00:00", "2026-07-02T10:00:03+00:00"))
        c.commit()


def test_shadow_default_never_explores(isolated_runtime):
    _seed_models()
    assert ex.is_explore_live() is False
    assert ex.pick_exploration_model("deepseek", "deepseek-v4-flash") is None


def test_candidates_exclude_default_and_prefer_least_sampled(isolated_runtime):
    _seed_models()
    cands = ex._candidates("deepseek/deepseek-v4-flash")
    keys = [k for k, _ in cands]
    assert "deepseek/deepseek-v4-flash" not in keys        # default ekskluderet
    assert keys and keys[0] == "ollama/glm-5.2:cloud"      # mindst-samplede først


def test_rate_bounded_every_kth_run(isolated_runtime):
    _seed_models()
    ex._kv_set(ex._EXPLORE_FLAG, True)
    picks = [ex.pick_exploration_model("deepseek", "deepseek-v4-flash") for _ in range(ex._SAMPLE_EVERY)]
    # kun den K'te (sidste i denne blok) sampler; resten None
    assert picks[:-1] == [None] * (ex._SAMPLE_EVERY - 1)
    assert picks[-1] == ("ollama", "glm-5.2:cloud")


def test_never_explores_deep_tier(isolated_runtime):
    from core.runtime.db import connect
    with connect() as c:
        for i in range(20):
            c.execute("INSERT INTO visible_runs (run_id, lane, provider, model, status, started_at, "
                      "finished_at) VALUES (?,?,?,?,?,?,?)",
                      (f"o{i}", "visible", "openai", "o1-reasoning", "completed",
                       "2026-07-02T10:00:00+00:00", "2026-07-02T10:00:05+00:00"))
        c.commit()
    ex._kv_set(ex._EXPLORE_FLAG, True)
    cands = [k for k, _ in ex._candidates("deepseek/deepseek-v4-flash")]
    assert "openai/o1-reasoning" not in cands              # deep-tier aldrig kandidat


# ── integration med resolveren: KUN autonome runs, aldrig interaktive ────────────────
def test_exploration_only_on_autonomous(isolated_runtime):
    _seed_models()
    ex._kv_set(ex._EXPLORE_FLAG, True)
    ra._kv_set(ra._LIVE_FLAG, False)
    # kør K gange PÅ INTERAKTIVE runs (autonomous=False) → må ALDRIG eksplorere
    for _ in range(ex._SAMPLE_EVERY * 2):
        p, m = ra.resolve_visible_model(default_provider="deepseek", default_model="deepseek-v4-flash",
                                        autonomous=False)
        assert (p, m) == ("deepseek", "deepseek-v4-flash")   # interaktiv: aldrig rørt


def test_exploration_fires_on_autonomous(isolated_runtime):
    _seed_models()
    ex._kv_set(ex._EXPLORE_FLAG, True)
    seen = set()
    for _ in range(ex._SAMPLE_EVERY):
        seen.add(ra.resolve_visible_model(default_provider="deepseek", default_model="deepseek-v4-flash",
                                          autonomous=True))
    assert ("ollama", "glm-5.2:cloud") in seen             # den K'te autonome run samplede alternativet


def test_explicit_override_still_wins_over_exploration(isolated_runtime):
    _seed_models()
    ex._kv_set(ex._EXPLORE_FLAG, True)
    for _ in range(ex._SAMPLE_EVERY):
        p, m = ra.resolve_visible_model(provider_override="ollama", model_override="flash:cloud",
                                        default_provider="deepseek", default_model="deepseek-v4-flash",
                                        autonomous=True)
        assert (p, m) == ("ollama", "flash:cloud")         # rolle-clamp ukrænkelig, selv under eksploration
