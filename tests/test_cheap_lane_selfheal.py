"""cheap-lane self-heal: re-probe fastlaaste providere saa en fikset provider kommer tilbage."""
from core.services import cheap_lane_selfheal as sh


def test_stale_targets_picks_any_unhealthy_without_cooldown(monkeypatch):
    states = [
        {"provider": "copilot-premium", "model": "claude-sonnet-5",
         "status": "unsupported-provider", "cooldown_until": None},   # fast → med
        {"provider": "groq", "model": "llama",
         "status": "rate-limited", "cooldown_until": None},           # udloebet cooldown, fast → MED nu
        {"provider": "nvidia-nim", "model": "meta/llama",
         "status": "ready", "cooldown_until": None},                  # sund → IKKE med
        {"provider": "legacy", "model": "m",
         "status": "ok", "cooldown_until": None},                     # sund (ok) → IKKE med
        {"provider": "retired", "model": "x",
         "status": "provider-error", "cooldown_until": None},         # ikke konfigureret → skip
    ]
    monkeypatch.setattr("core.runtime.db_cheap_provider.list_cheap_provider_runtime_states",
                        lambda lane="cheap": states)
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters.provider_runtime_defaults",
        lambda p: {} if p == "retired" else {"static_models": []})
    targets = sh._stale_targets(10)
    assert ("copilot-premium", "claude-sonnet-5") in targets
    assert ("groq", "llama") in targets          # rate-limited u. cooldown fanges nu
    assert not any(p in ("nvidia-nim", "legacy", "retired") for p, _ in targets)


def test_stale_targets_skips_active_cooldown(monkeypatch):
    from datetime import datetime, UTC, timedelta
    future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    monkeypatch.setattr("core.runtime.db_cheap_provider.list_cheap_provider_runtime_states",
                        lambda lane="cheap": [{"provider": "p", "model": "m",
                                               "status": "provider-error", "cooldown_until": future}])
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.provider_runtime_defaults",
                        lambda p: {"static_models": ["m"]})
    assert sh._stale_targets(10) == []   # aktiv cooldown haandterer den


def test_reprobe_heals_on_success(monkeypatch):
    saved = {}
    monkeypatch.setattr("core.runtime.db_cheap_provider.upsert_cheap_provider_runtime_state",
                        lambda **kw: saved.update(kw))
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.provider_runtime_defaults",
                        lambda p: {"base_url": "http://x"})
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters._execute_provider_chat",
                        lambda **kw: {"text": "pong"})
    ok = sh.reprobe("copilot-premium", "claude-sonnet-5")
    assert ok is True
    assert saved["status"] == "ready" and saved["cooldown_until"] is None


def test_reprobe_sets_cooldown_on_failure(monkeypatch):
    from core.services.cheap_provider_runtime_adapters import CheapProviderError
    saved = {}
    monkeypatch.setattr("core.runtime.db_cheap_provider.upsert_cheap_provider_runtime_state",
                        lambda **kw: saved.update(kw))
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.provider_runtime_defaults",
                        lambda p: {"base_url": "http://x"})

    def _boom(**kw):
        raise CheapProviderError(provider="p", code="provider-error", message="down")
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters._execute_provider_chat", _boom)
    ok = sh.reprobe("p", "m")
    assert ok is False
    assert saved["status"] == "provider-error" and saved["cooldown_until"]  # cooldown sat


def test_run_selfheal_summarizes(monkeypatch):
    monkeypatch.setattr(sh, "_stale_targets", lambda n: [("a", "m1"), ("b", "m2")])
    monkeypatch.setattr(sh, "reprobe", lambda p, m: p == "a")   # a healer, b fejler
    out = sh.run_selfheal(max_probes=6)
    assert out["healed"] == ["a/m1"] and out["still_down"] == ["b/m2"] and out["probed"] == 2
