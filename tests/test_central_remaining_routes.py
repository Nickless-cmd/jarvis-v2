"""Tests for de 5 resterende MC-kategori-routes wired ind i Centralen:
attention / skills / integrity / experiments / execution.

Mønster (fra test_central_costs_daily_route.py): producenter importeres INDE i
funktionen, så vi patcher kilde-modulet; ``require_central_owner`` + ``absorb``
patches på route-modulet. Kald via nyt event loop.
"""
import asyncio

from unittest.mock import patch


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# ── attention ────────────────────────────────────────────────────────────────
def test_attention_shape_and_absorb():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    calls = []
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.services.attention_budget.build_attention_budget_surface",
               lambda: {"budget": 42}), \
         patch.object(m, "absorb", lambda *a, **k: calls.append((a, k))):
        out = _run(m.get_attention())
    assert out["attention"] == {"budget": 42}
    assert calls, "absorb skal kaldes"
    (cluster, nerve, _val), kw = calls[0]
    assert cluster == "attention" and nerve == "budget"
    assert kw.get("learn_key") == "attention:budget"


def test_attention_self_safe():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    calls = []

    def boom():
        raise RuntimeError("nej")

    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.services.attention_budget.build_attention_budget_surface", boom), \
         patch.object(m, "absorb", lambda *a, **k: calls.append((a, k))):
        out = _run(m.get_attention())
    assert out == {"attention": {}}
    assert calls, "absorb skal stadig kaldes ved producent-fejl"


# ── skills ───────────────────────────────────────────────────────────────────
def test_skills_shape_and_absorb():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    calls = []
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.services.skill_engine.build_skill_engine_surface",
               lambda: {"skills": ["a"]}), \
         patch("core.services.skill_contract_registry.build_skill_contract_registry_surface",
               lambda: {"contracts": ["c"]}), \
         patch.object(m, "absorb", lambda *a, **k: calls.append((a, k))):
        out = _run(m.get_skills())
    assert out["engine"] == {"skills": ["a"]}
    assert out["contracts"] == {"contracts": ["c"]}
    clusters = {(a[0], a[1]) for a, _ in calls}
    assert ("skill", "engine") in clusters
    assert ("skill", "contracts") in clusters


def test_skills_self_safe():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    calls = []

    def boom():
        raise RuntimeError("nej")

    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.services.skill_engine.build_skill_engine_surface", boom), \
         patch("core.services.skill_contract_registry.build_skill_contract_registry_surface", boom), \
         patch.object(m, "absorb", lambda *a, **k: calls.append((a, k))):
        out = _run(m.get_skills())
    assert out == {"engine": {}, "contracts": {}}
    assert len(calls) == 2, "begge absorb-kald skal ske selv ved fejl"


# ── integrity ────────────────────────────────────────────────────────────────
def test_integrity_shape_and_absorb():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    calls = []
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.services.self_deception_guard.build_self_deception_guard_surface",
               lambda: {"guard": True}), \
         patch.object(m, "absorb", lambda *a, **k: calls.append((a, k))):
        out = _run(m.get_integrity())
    assert out["integrity"] == {"guard": True}
    (cluster, nerve, _val), kw = calls[0]
    assert cluster == "integrity" and nerve == "self_deception"
    assert kw.get("learn_key") == "integrity:self_deception"


def test_integrity_self_safe():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    calls = []

    def boom():
        raise RuntimeError("nej")

    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.services.self_deception_guard.build_self_deception_guard_surface", boom), \
         patch.object(m, "absorb", lambda *a, **k: calls.append((a, k))):
        out = _run(m.get_integrity())
    assert out == {"integrity": {}}
    assert calls


# ── experiments ──────────────────────────────────────────────────────────────
def test_experiments_shape_and_absorb():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    calls = []
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.services.cognitive_core_experiments.build_cognitive_core_experiments_surface",
               lambda: {"experiments": [1, 2]}), \
         patch.object(m, "absorb", lambda *a, **k: calls.append((a, k))):
        out = _run(m.get_experiments())
    assert out["experiments"] == {"experiments": [1, 2]}
    (cluster, nerve, _val), kw = calls[0]
    assert cluster == "experiment" and nerve == "runner"
    assert kw.get("learn_key") == "experiment:runner"


def test_experiments_self_safe():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    calls = []

    def boom():
        raise RuntimeError("nej")

    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.services.cognitive_core_experiments.build_cognitive_core_experiments_surface", boom), \
         patch.object(m, "absorb", lambda *a, **k: calls.append((a, k))):
        out = _run(m.get_experiments())
    assert out == {"experiments": {}}
    assert calls


# ── execution ────────────────────────────────────────────────────────────────
class _FakeSettings:
    def __init__(self, d):
        self._d = d

    def to_dict(self):
        return dict(self._d)


def test_execution_only_whitelisted_keys():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    calls = []
    fake = _FakeSettings({
        "visible_model_provider": "github-copilot",
        "generative_autonomy_enabled": True,
        "cheap_model_lane": "cheap",
        "super_secret_api_key": "sk-should-never-leak",  # NON-whitelisted
        "another_secret_token": "t0ken",
    })
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.runtime.settings.load_settings", lambda: fake), \
         patch.object(m, "absorb", lambda *a, **k: calls.append((a, k))):
        out = _run(m.get_execution())
    cfg = out["execution"]
    # Whitelisted keys present
    assert cfg["visible_model_provider"] == "github-copilot"
    assert cfg["generative_autonomy_enabled"] is True
    assert cfg["cheap_model_lane"] == "cheap"
    # Secrets NEVER surfaced
    assert "super_secret_api_key" not in cfg
    assert "another_secret_token" not in cfg
    # absorb called with only-whitelisted config
    (cluster, nerve, val), kw = calls[0]
    assert cluster == "execution" and nerve == "config"
    assert "super_secret_api_key" not in val
    assert kw.get("learn_key") == "execution:config"


def test_execution_self_safe():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    calls = []

    def boom():
        raise RuntimeError("nej")

    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.runtime.settings.load_settings", boom), \
         patch.object(m, "absorb", lambda *a, **k: calls.append((a, k))):
        out = _run(m.get_execution())
    assert out == {"execution": {}}
    assert calls
