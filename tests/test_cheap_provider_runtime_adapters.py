"""Tests for core/services/cheap_provider_runtime_adapters.py — provider defaults."""
from __future__ import annotations

import pytest

from core.services.cheap_provider_runtime_adapters import CHEAP_PROVIDER_DEFAULTS


def test_new_verified_providers_present_and_well_formed():
    """De 4 live-verificerede providers (14. jul) skal være i CHEAP_PROVIDER_DEFAULTS
    med de felter selection/adapters kræver. En provider der IKKE er her kan ikke
    bruges af cheap lane (provider_auth_ready returnerer False)."""
    required = {"label", "priority", "base_url", "auth_kind", "protocol", "static_models"}
    expected_models = {
        "cerebras": "gpt-oss-120b",
        "cline": "deepseek/deepseek-chat",
        "aihubmix": "gpt-5.5-free",
        "requesty": "novita/tencent/hy3",
    }
    for provider, must_have_model in expected_models.items():
        assert provider in CHEAP_PROVIDER_DEFAULTS, f"{provider} mangler i defaults"
        cfg = CHEAP_PROVIDER_DEFAULTS[provider]
        assert required <= set(cfg), f"{provider} mangler felter: {required - set(cfg)}"
        assert cfg["auth_kind"] == "bearer"
        assert cfg["protocol"] == "openai-chat"
        assert cfg["base_url"].startswith("https://")
        assert must_have_model in cfg["static_models"], f"{provider} mangler {must_have_model}"


def test_cline_base_url_is_api_v1_not_clinebot():
    """Regression: Cline's endpoint er api.cline.bot/api/v1 — IKKE api.clinebot.com,
    IKKE /v1. Forkert host gav HTTP 000 i 1. test."""
    base = CHEAP_PROVIDER_DEFAULTS["cline"]["base_url"]
    assert base == "https://api.cline.bot/api/v1"
    assert "clinebot.com" not in base


def test_aihubmix_static_models_are_free_only():
    """AIHubMix 'auto' router til BETALT (403 balance). Kun *-free må stå i pool."""
    models = CHEAP_PROVIDER_DEFAULTS["aihubmix"]["static_models"]
    assert models, "aihubmix skal have free-modeller"
    assert all("free" in m for m in models), f"ikke-gratis model i aihubmix pool: {models}"
    assert "auto" not in models


def test_aionlabs_present_free_and_openai_compat():
    """AionLabs (16. jul, free-tier): OpenAI-compat bearer, cost_class=free → i cheap lane,
    routbar, og auto-tilføjet openai-compat-sættet (protocol=openai-chat). Modeller er de
    live-verificerede aion-labs/*- id'er (fuld slug, som /models returnerer)."""
    from core.services.cheap_provider_runtime_adapters import (
        _OPENAI_COMPATIBLE_PROVIDERS,
        is_routable_provider,
        provider_cost_class,
    )
    cfg = CHEAP_PROVIDER_DEFAULTS["aionlabs"]
    assert cfg["base_url"] == "https://api.aionlabs.ai/v1"
    assert cfg["auth_kind"] == "bearer" and cfg["protocol"] == "openai-chat"
    assert provider_cost_class("aionlabs") == "free"
    assert is_routable_provider("aionlabs") is True
    assert "aionlabs" in _OPENAI_COMPATIBLE_PROVIDERS
    assert "aion-labs/aion-2.0" in cfg["static_models"]
    assert all(m.startswith("aion-labs/") for m in cfg["static_models"])


def test_freetheai_is_agent_pool_reserve_not_cheap_firehose():
    """FreeTheAi (16. jul): 3 unikke frontier-modeller, MEN daglig Discord-checkin +
    concurrency=1 → KUN agent-pool-reserve. cost_class=paid (routing-gate, ikke billing —
    gratis) holder den ude af den gratis cheap-firehose men i agent-poolen via allow_paid.
    routable=True (ellers ryger den ud af BEGGE pools). Lav prioritet = bund-reserve."""
    from core.services.cheap_provider_runtime_adapters import (
        is_routable_provider, provider_cost_class,
    )
    cfg = CHEAP_PROVIDER_DEFAULTS["freetheai"]
    assert cfg["base_url"] == "https://api.freetheai.xyz/v1"
    assert cfg["protocol"] == "openai-chat" and cfg["auth_kind"] == "bearer"
    assert provider_cost_class("freetheai") == "paid"   # → ude af cheap lane, i agent-pool
    assert is_routable_provider("freetheai") is True     # → med i agent-pool-kandidater
    assert int(cfg["priority"]) >= 80                    # bund-reserve
    assert "bbl/gpt-5.5-mini" in cfg["static_models"]


def test_provider_auth_ready_normalizes_empty_profile_to_default(monkeypatch):
    """Rod-årsag (16.jul): candidate-byggeren giver auth_profile='' for providere UDEN en
    provider-router-registry-entry (aionlabs/huggingface/freetheai). provider_auth_ready('')
    returnerede hårdt False → credentials_ready=False → selektoren valgte dem ALDRIG, selvom
    nøglen lå under 'default' og dispatch (_require_credentials) normaliserer ''→'default'.
    Fix: readiness normaliserer OGSÅ ''→'default' så den matcher dispatch-virkeligheden."""
    import core.services.cheap_provider_runtime_adapters as mod
    seen_profiles = []

    def _fake_get(*, profile, provider):
        seen_profiles.append(profile)
        return {"api_key": "k"} if profile == "default" else None

    monkeypatch.setattr(mod, "get_provider_credentials", _fake_get)
    monkeypatch.setattr(mod, "provider_has_real_credentials",
                        lambda *, profile, provider: profile == "default")
    # cerebras = bearer openai-chat provider i defaults
    assert mod.provider_auth_ready(provider="cerebras", auth_profile="") is True
    assert mod.provider_auth_ready(provider="cerebras", auth_profile="default") is True
    assert "default" in seen_profiles          # '' blev slået op som 'default'


def test_classify_checkin_required_from_body():
    """FreeTheAi-checkin-body → distinkt 'checkin-required' kode (uafhængig af status)."""
    from core.services.cheap_provider_runtime_adapters import (
        _classify_http_error, _default_failure_cooldown_seconds,
    )
    body = '{"error":{"message":"daily discord check-in required; run /checkin","type":"daily_checkin_required"}}'
    assert _classify_http_error(provider="freetheai", status_code=401, body=body) == "checkin-required"
    assert _classify_http_error(provider="freetheai", status_code=403, body=body) == "checkin-required"
    assert _default_failure_cooldown_seconds("checkin-required") == 1800


def test_notify_checkin_required_dedups_per_day(monkeypatch):
    """Nudge til Jarvis' awareness ved checkin-lås — men KUN én pr. UTC-dag (self-heal +
    flere kald må ikke spamme). 2. kald samme dag skal ikke pushe igen."""
    import core.services.nudge_broend as nb
    from core.services.cheap_provider_runtime_adapters import _notify_checkin_required
    pushed = []
    store = []

    def _push(**kw):
        pushed.append(kw)
        from datetime import UTC, datetime
        store.append({"source": kw.get("source"), "created_at": datetime.now(UTC).isoformat()})
        return "nudge-x"

    monkeypatch.setattr(nb, "push", _push)
    monkeypatch.setattr(nb, "list_pending", lambda limit=50: list(store))
    _notify_checkin_required("freetheai")
    _notify_checkin_required("freetheai")   # samme dag → ingen ny push
    assert len(pushed) == 1
    assert pushed[0]["source"] == "freetheai_checkin"
    assert "checkin" in pushed[0]["message"].lower()


def test_cohere_free_ongoing_low_daily_cap():
    """Cohere (16.jul, research-vinder): vedvarende gratis (1000/md) via OpenAI-compat
    endpoint. cost_class=free → cheap lane. daily_limit lavt (≤50) så månedskvoten ikke
    brændes på én dag. Kun chat-modeller i static (ingen embed/vision)."""
    from core.services.cheap_provider_runtime_adapters import provider_cost_class
    cfg = CHEAP_PROVIDER_DEFAULTS["cohere"]
    assert cfg["base_url"] == "https://api.cohere.ai/compatibility/v1"
    assert cfg["protocol"] == "openai-chat" and cfg["auth_kind"] == "bearer"
    assert provider_cost_class("cohere") == "free"
    assert int(cfg["daily_limit"]) <= 50            # beskyt 1000/md-kvoten
    assert "command-r7b-12-2024" in cfg["static_models"]
    assert all("embed" not in m and "vision" not in m for m in cfg["static_models"])


def test_alibaba_modelstudio_free_singapore():
    """Alibaba Model Studio (16.jul, Bjørns SG-workspace): OpenAI-compat, gratis token-kvote.
    cost_class=free → cheap lane workhorse. Kun verificerede non-reasoning Qwen-chat-modeller
    (glm-5.2=reasoning udeladt). Workspace-scopet Singapore-endpoint."""
    from core.services.cheap_provider_runtime_adapters import provider_cost_class, is_routable_provider
    cfg = CHEAP_PROVIDER_DEFAULTS["alibaba"]
    assert "ap-southeast-1" in cfg["base_url"] and cfg["base_url"].endswith("/compatible-mode/v1")
    assert cfg["protocol"] == "openai-chat" and cfg["auth_kind"] == "bearer"
    assert provider_cost_class("alibaba") == "free" and is_routable_provider("alibaba") is True
    assert cfg["static_models"] == ["qwen-turbo", "qwen-plus", "qwen3.7-plus"]


def test_deepseek_not_routable_but_free_providers_are():
    """Bjørn 14. jul: deepseek (betalt) skal UD af routbar cheap-pool; gratis ind."""
    from core.services.cheap_provider_runtime_adapters import is_routable_provider
    assert is_routable_provider("deepseek") is False
    assert is_routable_provider("openai-codex") is False   # død efter opsigelse
    for free in ("cerebras", "aihubmix", "requesty", "groq", "nvidia-nim"):
        assert is_routable_provider(free) is True, f"{free} skal være routbar"


def test_gemini_cloudflare_openai_compat_for_tools():
    """Research 14. jul: gemini + cloudflare bruger nu deres OpenAI-compat endpoints
    (protocol=openai-chat) → tool_calls virker → i den tool-kapable agent-pool.
    gemini-2.5 udfaset → -latest-aliaser."""
    from core.services.cheap_provider_runtime_adapters import CHEAP_PROVIDER_DEFAULTS
    g = CHEAP_PROVIDER_DEFAULTS["gemini"]
    assert g["protocol"] == "openai-chat"
    assert g["base_url"].endswith("/openai")
    assert "gemini-flash-latest" in g["static_models"]
    assert "gemini-2.5-flash-lite" not in g.get("static_models", [])
    cf = CHEAP_PROVIDER_DEFAULTS["cloudflare"]
    assert cf["protocol"] == "openai-chat"
    assert "/ai/v1" in cf["base_url"]


def test_opencode_free_models_current_not_deprecated():
    """opencode static_models skal være de AKTUELLE gratis Zen-modeller (verificeret
    via `opencode models` 14. jul), ikke de udfasede."""
    from core.services.cheap_provider_runtime_adapters import CHEAP_PROVIDER_DEFAULTS
    m = CHEAP_PROVIDER_DEFAULTS["opencode"]["static_models"]
    assert "nemotron-3-ultra-free" in m and "mimo-v2.5-free" in m
    assert "nemotron-3-super-free" not in m   # udfaset
    assert "minimax-m2.5-free" not in m       # udfaset
    assert len(m) >= 5


def test_github_models_and_ovhcloud_configured():
    """14. jul: GitHub Models (gratis GPT-5/o4-mini/DeepSeek-R1 via Copilot-token) +
    OVHcloud (anon, auth_kind=none) tilføjet til poolen."""
    from core.services.cheap_provider_runtime_adapters import (
        CHEAP_PROVIDER_DEFAULTS, is_routable_provider, provider_auth_ready)
    gh = CHEAP_PROVIDER_DEFAULTS["github-models"]
    assert gh["protocol"] == "openai-chat" and gh["base_url"].startswith("https://models.github.ai")
    assert "openai/gpt-5-mini" in gh["static_models"]
    assert gh["daily_limit"] == 50           # rate-limitet → ikke arbejdshest
    ov = CHEAP_PROVIDER_DEFAULTS["ovhcloud"]
    assert ov["auth_kind"] == "none"
    # auth_kind=none → altid ready uden nøgle
    assert provider_auth_ready(provider="ovhcloud", auth_profile="default") is True
    assert is_routable_provider("github-models") and is_routable_provider("ovhcloud")


def test_pollinations_keyless_free_and_routable():
    """15. jul: Pollinations (anon, auth_kind=none, tool-capable, live-verificeret) i
    cheap lane + pool. Keyless → _require_credentials må ALDRIG rejse for den, selv
    uden nogen credential-entry i storen ( modsat de bearer-providers)."""
    from core.services.cheap_provider_runtime_adapters import (
        CHEAP_PROVIDER_DEFAULTS, is_routable_provider, provider_cost_class,
        provider_auth_ready, _OPENAI_COMPATIBLE_PROVIDERS, _require_credentials)
    p = CHEAP_PROVIDER_DEFAULTS["pollinations"]
    assert p["auth_kind"] == "none"
    assert p["protocol"] == "openai-chat"
    assert p["base_url"] == "https://text.pollinations.ai/openai"
    assert p["static_models"] == ["openai-fast"]
    assert provider_cost_class("pollinations") == "free"
    assert is_routable_provider("pollinations")
    assert "pollinations" in _OPENAI_COMPATIBLE_PROVIDERS
    # auth_kind=none → altid ready + _require_credentials returnerer {} (rejser IKKE)
    assert provider_auth_ready(provider="pollinations", auth_profile="default") is True
    assert _require_credentials(profile="default", provider="pollinations") == {}


def test_kilo_keyless_free_routes_and_tool_capable():
    """15. jul (FreeLLMAPI-extraction): Kilo Gateway — anon keyless :free-routes,
    tool-capable (live-verificeret). I cheap lane + pool. static_models kun :free."""
    from core.services.cheap_provider_runtime_adapters import (
        CHEAP_PROVIDER_DEFAULTS, is_routable_provider, provider_cost_class,
        provider_auth_ready, _OPENAI_COMPATIBLE_PROVIDERS)
    k = CHEAP_PROVIDER_DEFAULTS["kilo"]
    assert k["auth_kind"] == "none"
    assert k["protocol"] == "openai-chat"
    assert k["base_url"] == "https://api.kilo.ai/api/gateway/v1"
    # aldrig paid-routes: hver model er en :free / /free-rute
    assert all(m.endswith(":free") or m.endswith("/free") for m in k["static_models"])
    assert provider_cost_class("kilo") == "free"
    assert is_routable_provider("kilo") and "kilo" in _OPENAI_COMPATIBLE_PROVIDERS
    assert provider_auth_ready(provider="kilo", auth_profile="default") is True


def test_zai_zhipu_free_glm_flash():
    """15. jul (Bjørn-nøgle): Z.ai/Zhipu — glm-4.5-flash ÆGTE gratis (betalte GLM gav
    429 insufficient-balance). OpenAI-compat /paas/v4, bearer. static_models kun free."""
    from core.services.cheap_provider_runtime_adapters import (
        CHEAP_PROVIDER_DEFAULTS, is_routable_provider, provider_cost_class,
        _OPENAI_COMPATIBLE_PROVIDERS)
    z = CHEAP_PROVIDER_DEFAULTS["zai"]
    assert z["auth_kind"] == "bearer"
    assert z["protocol"] == "openai-chat"
    assert z["base_url"] == "https://api.z.ai/api/paas/v4"
    assert z["static_models"] == ["glm-4.5-flash"]   # kun den gratis flash-variant
    assert provider_cost_class("zai") == "free"
    assert is_routable_provider("zai") and "zai" in _OPENAI_COMPATIBLE_PROVIDERS


def test_huggingface_router_free_tool_capable():
    """15. jul: HF Router — Bjørns eksist. hf_-token. Stærke tool-capable modeller
    (Llama-3.3-70B/Qwen2.5-72B/DeepSeek-V3). Credit-meteret men konto=canPay:False →
    nul spend-risiko (402 v. tom credit). Konservativt daily_limit."""
    from core.services.cheap_provider_runtime_adapters import (
        CHEAP_PROVIDER_DEFAULTS, is_routable_provider, provider_cost_class,
        _OPENAI_COMPATIBLE_PROVIDERS)
    h = CHEAP_PROVIDER_DEFAULTS["huggingface"]
    assert h["auth_kind"] == "bearer"
    assert h["protocol"] == "openai-chat"
    assert h["base_url"] == "https://router.huggingface.co/v1"
    assert h["daily_limit"] <= 50            # credit-meteret → konservativt loft
    assert provider_cost_class("huggingface") == "free"
    assert is_routable_provider("huggingface") and "huggingface" in _OPENAI_COMPATIBLE_PROVIDERS


def test_reka_edge_conservative_cap():
    """15. jul: Reka — reka-edge-2603 tool-capable. Usage-based ($0.10/1M) på gratis
    trial-credits, Bjørn bekræftede ingen kort → konservativt daily_limit."""
    from core.services.cheap_provider_runtime_adapters import (
        CHEAP_PROVIDER_DEFAULTS, is_routable_provider, provider_cost_class,
        _OPENAI_COMPATIBLE_PROVIDERS)
    r = CHEAP_PROVIDER_DEFAULTS["reka"]
    assert r["auth_kind"] == "bearer"
    assert r["base_url"] == "https://api.reka.ai/v1"
    assert r["static_models"] == ["reka-edge-2603"]   # den rene tool-capable (ikke flash-3-reasoner)
    assert r["daily_limit"] <= 50                      # trial-credit → konservativt
    assert provider_cost_class("reka") == "free"
    assert is_routable_provider("reka") and "reka" in _OPENAI_COMPATIBLE_PROVIDERS


def test_bazaarlink_auto_free_sustained():
    """15. jul: BazaarLink auto:free — perpetual gratis (6/6 kald cost=0, bestod den
    SiliconFlow-hærdede vedvarende-test). Chat-stærk, tool-svag → cheap lane. cost=free."""
    from core.services.cheap_provider_runtime_adapters import (
        CHEAP_PROVIDER_DEFAULTS, is_routable_provider, provider_cost_class,
        _OPENAI_COMPATIBLE_PROVIDERS)
    b = CHEAP_PROVIDER_DEFAULTS["bazaarlink"]
    assert b["auth_kind"] == "bearer"
    assert b["base_url"] == "https://bazaarlink.ai/api/v1"
    assert b["static_models"] == ["auto:free"]        # kun den gratis auto-route
    assert provider_cost_class("bazaarlink") == "free"
    assert is_routable_provider("bazaarlink") and "bazaarlink" in _OPENAI_COMPATIBLE_PROVIDERS


def test_require_credentials_empty_profile_keyless_no_crash():
    """15. jul regression: cheap-lane-selection kan give TOM auth_profile for en keyless
    provider (kilo/pollinations blev cheap-lane-pick på containeren). _profile_dir('')
    rejste 'Profile name must be a simple non-empty identifier' → crash i inderlivet.
    Fix: normalisér tom→'default' + try/except → aldrig crash, kør anonymt."""
    from core.services.cheap_provider_runtime_adapters import _require_credentials
    for p in ("pollinations", "kilo", "ovhcloud"):
        # tom + whitespace profil → returnerer dict (evt. tom), rejser ALDRIG
        assert isinstance(_require_credentials(profile="", provider=p), dict)
        assert isinstance(_require_credentials(profile="   ", provider=p), dict)


def test_require_credentials_still_raises_for_bearer_without_key(monkeypatch):
    """Guarden må kun gælde auth_kind=none. En bearer-provider uden nøgle skal stadig
    rejse auth-not-ready (ellers ville vi kalde en betalt/nøgle-provider uden auth)."""
    import core.services.cheap_provider_runtime_adapters as mod
    monkeypatch.setattr(mod, "get_provider_credentials", lambda **kw: None)
    with pytest.raises(mod.CheapProviderError):
        mod._require_credentials(profile="default", provider="cerebras")


def test_copilot_cost_classes():
    from core.services.cheap_provider_runtime_adapters import provider_cost_class, CHEAP_PROVIDER_DEFAULTS
    assert provider_cost_class("copilot-premium") == "paid"
    assert provider_cost_class("copilot-free") == "free"
    assert provider_cost_class("cerebras") == "free"   # default
    assert "claude-sonnet-5" in CHEAP_PROVIDER_DEFAULTS["copilot-premium"]["static_models"]
    assert "gpt-4o" in CHEAP_PROVIDER_DEFAULTS["copilot-free"]["static_models"]


def test_openai_compatible_set_derived_from_protocol():
    """15. jul: _OPENAI_COMPATIBLE_PROVIDERS udledes fra protocol → auto-inkluderer alle
    openai-chat (nye + gemini/cloudflare). Fikser balancer 'unsupported-provider' +
    agent-step deepseek-fallback."""
    from core.services.cheap_provider_runtime_adapters import _OPENAI_COMPATIBLE_PROVIDERS
    for p in ("cerebras", "aihubmix", "requesty", "cline", "gemini", "cloudflare",
              "github-models", "ovhcloud", "copilot-free", "copilot-premium",
              "groq", "nvidia-nim", "openrouter", "mistral", "opencode"):
        assert p in _OPENAI_COMPATIBLE_PROVIDERS, f"{p} mangler"
    assert "arko" not in _OPENAI_COMPATIBLE_PROVIDERS          # arko-protokol
    assert "ollamafreeapi" not in _OPENAI_COMPATIBLE_PROVIDERS


def test_ollama_a2_present_free_lan_cloud_account():
    """account2's separate ollama-cloud free-tier (10.0.0.45) skal være en distinkt
    cheap-lane-provider — IKKE den lokale `ollama` (ejerens konto, excluded).
    LAN-kald: auth_kind=none, protocol=ollama, gratis. static_models = KUN de
    cloud-modeller free-tier faktisk kan (de subscription-gatede er udeladt)."""
    cfg = CHEAP_PROVIDER_DEFAULTS["ollama-a2"]
    assert cfg["base_url"] == "http://10.0.0.45:11434"
    assert cfg["auth_kind"] == "none"          # LAN — ingen nøgle fra vores side
    assert cfg["protocol"] == "ollama"          # native /api/chat, ikke openai-compat
    assert cfg.get("cost_class") == "free"
    assert set(cfg["static_models"]) == {"gemma4:31b-cloud", "minimax-m3:cloud"}
    # Må ALDRIG folde subscription-gatede modeller ind (ville blive døde slots).
    for gated in ("glm-5.2:cloud", "deepseek-v4-flash:cloud", "kimi-k2.7-code:cloud"):
        assert gated not in cfg["static_models"]


def _ollama_urlopen_shim(monkeypatch, payload_bytes):
    """Scoped patch af adapters-modulets urllib — ALDRIG det globale urllib.request
    (det lækker ind i andre in-process urlopen-kaldere, jf. streaming-fixet 24. jul)."""
    import types
    import core.services.cheap_provider_runtime_adapters as mod

    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return payload_bytes

    real = mod.urllib_request
    shim = types.SimpleNamespace(Request=real.Request, urlopen=lambda *a, **k: _Resp())
    monkeypatch.setattr(mod, "urllib_request", shim)


def test_ollama_a2_dispatch_labels_provider(monkeypatch):
    """Success-svar skal labelles med den kaldende provider (ollama-a2), ikke den
    hardcodede 'ollama' — ellers fejl-attribueres account2's kald til lokal ollama."""
    import json as _json
    import core.services.cheap_provider_runtime_adapters as mod
    _ollama_urlopen_shim(monkeypatch, _json.dumps(
        {"message": {"content": "OK"}}).encode("utf-8"))
    r = mod._execute_local_ollama_chat(
        model="gemma4:31b-cloud", base_url="http://10.0.0.45:11434",
        message="hi", provider="ollama-a2")
    assert r["provider"] == "ollama-a2"
    assert r["status"] == "completed"
    assert r["text"] == "OK"


def test_ollama_a2_error_body_raises_not_silent_completion(monkeypatch):
    """Ollama melder subscription/kvote som {"error": ...} med HTTP 200. Det skal
    blive en ægte CheapProviderError (så balanceren cooldown'er), IKKE en tavs
    status=completed med tom tekst."""
    import json as _json
    import core.services.cheap_provider_runtime_adapters as mod
    _ollama_urlopen_shim(monkeypatch, _json.dumps(
        {"error": "this model requires a subscription, upgrade for access"}
    ).encode("utf-8"))
    with pytest.raises(mod.CheapProviderError) as ei:
        mod._execute_local_ollama_chat(
            model="glm-5.2:cloud", base_url="http://10.0.0.45:11434",
            message="hi", provider="ollama-a2")
    assert ei.value.code == "model-not-found"
    assert ei.value.provider == "ollama-a2"
