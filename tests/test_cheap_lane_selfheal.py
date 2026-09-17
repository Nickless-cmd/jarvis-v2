"""cheap-lane self-heal: re-probe fastlaaste providere saa en fikset provider kommer tilbage."""
import pytest

from core.services import cheap_lane_selfheal as sh


@pytest.fixture(autouse=True)
def _tomt_register(monkeypatch):
    # Hermetisk: ingen test læser maskinens rigtige provider_router.json.
    monkeypatch.setattr(sh, "_slukket", lambda: (set(), set()))


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
    # zero-row-loopet skal ikke bidrage her → tomt katalog
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters.CHEAP_PROVIDER_DEFAULTS", {})
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
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters.CHEAP_PROVIDER_DEFAULTS", {})
    assert sh._stale_targets(10) == []   # aktiv cooldown haandterer den


def test_stale_targets_probes_zero_row_configured_providers(monkeypatch):
    """Zero-row-fælde (16.jul, HF): en konfigureret+routbar+gratis provider UDEN nogen
    state-row er usynlig for selektoren OG for state-row-loopet → sidder fast på 0 rows
    for evigt (aldrig valgt → aldrig probet → aldrig en row). Self-heal skal probe dens
    static_models ind, ellers 'stale' den for altid."""
    monkeypatch.setattr("core.runtime.db_cheap_provider.list_cheap_provider_runtime_states",
                        lambda lane="cheap": [])                      # INGEN rows
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.CHEAP_PROVIDER_DEFAULTS",
                        {"huggingface": {"static_models": ["m1", "m2"]}})
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.provider_cost_class",
                        lambda p: "free")
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.is_routable_provider",
                        lambda p: True)
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.provider_runtime_defaults",
                        lambda p: {"static_models": ["m1", "m2"]})
    targets = sh._stale_targets(10)
    assert ("huggingface", "m1") in targets and ("huggingface", "m2") in targets


def test_stale_targets_skips_zero_row_paid_and_nonroutable(monkeypatch):
    """Zero-row-probing gælder KUN cheap-kandidater (gratis+routbar). En betalt
    (copilot-premium) eller ude-af-pool (deepseek) provider uden row skal IKKE seedes
    ind i cheap-lane af self-heal."""
    monkeypatch.setattr("core.runtime.db_cheap_provider.list_cheap_provider_runtime_states",
                        lambda lane="cheap": [])
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.CHEAP_PROVIDER_DEFAULTS",
                        {"copilot-premium": {"static_models": ["x"]},
                         "deepseek": {"static_models": ["y"]}})
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.provider_cost_class",
                        lambda p: "paid" if p == "copilot-premium" else "free")
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.is_routable_provider",
                        lambda p: p != "deepseek")
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.provider_runtime_defaults",
                        lambda p: {"static_models": ["x"] if p == "copilot-premium" else ["y"]})
    assert sh._stale_targets(10) == []


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


def test_stale_targets_springer_slukkede_over(monkeypatch):
    """17/9-2026: self-heal prøvede cerebras/cline igen efter de var slukket i registret."""
    monkeypatch.setattr(sh, "_slukket", lambda: ({"cerebras"}, {("kilo", "doed")}))
    monkeypatch.setattr("core.runtime.db_cheap_provider.list_cheap_provider_runtime_states",
                        lambda lane="cheap": [
                            {"provider": "cerebras", "model": "g", "status": "model-not-found", "cooldown_until": None},
                            {"provider": "kilo", "model": "doed", "status": "empty-response", "cooldown_until": None},
                            {"provider": "kilo", "model": "levende", "status": "provider-error", "cooldown_until": None},
                        ])
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.CHEAP_PROVIDER_DEFAULTS",
                        {"cerebras": {"static_models": ["g", "ny"]}, "kilo": {"static_models": ["doed", "levende"]}})
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.provider_cost_class", lambda p: "free")
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.is_routable_provider", lambda p: True)
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.provider_runtime_defaults",
                        lambda p: {"static_models": ["g", "ny"] if p == "cerebras" else ["doed", "levende"]})
    assert sh._stale_targets(10) == [("kilo", "levende")]


def _reprobe_fejl(monkeypatch, **fejl):
    from datetime import UTC, datetime
    from core.services.cheap_provider_runtime_adapters import CheapProviderError
    saved = {}
    monkeypatch.setattr("core.runtime.db_cheap_provider.upsert_cheap_provider_runtime_state",
                        lambda **kw: saved.update(kw))
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.provider_runtime_defaults",
                        lambda p: {"base_url": "http://x"})

    def _boom(**kw):
        raise CheapProviderError(provider="p", **fejl)
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters._execute_provider_chat", _boom)
    sh.reprobe("p", "m")
    return (datetime.fromisoformat(saved["cooldown_until"]) - datetime.now(UTC)).total_seconds()


def test_reprobe_giver_pensioneret_model_24_timer(monkeypatch):
    sek = _reprobe_fejl(monkeypatch, code="model-not-found",
                        message="Model gemma-4-31b is archived and unavailable")
    assert sek > 23 * 3600


def test_reprobe_retry_after_vinder(monkeypatch):
    sek = _reprobe_fejl(monkeypatch, code="model-not-found", message="gone", retry_after_seconds=90)
    assert sek < 200


def test_reprobe_forbigaaende_fejl_beholder_kort_cooldown(monkeypatch):
    assert _reprobe_fejl(monkeypatch, code="provider-error", message="down") < 3 * 3600


def test_reprobe_respekterer_udbyderens_mindste_pause(monkeypatch):
    monkeypatch.setattr("core.services.cheap_provider_runtime_adapters.provider_min_failure_cooldown_seconds",
                        lambda p: 7200)
    assert _reprobe_fejl(monkeypatch, code="request-failed", message="timed out") > 7000
