"""Kataloget udskilt fra cheap_provider_runtime_adapters 7/9-2026.

Testene holder to ting fast: at symbolerne stadig kan hentes fra det gamle
modul (kaldere og ældre tests importerer dem derfra), og at nye poster bygger
på MÅLINGER — ikke på hvad udbyderens /v1/models påstår.
"""
from core.services import cheap_provider_catalogue as kat
from core.services import cheap_provider_runtime_adapters as ad


def test_kataloget_kan_stadig_hentes_fra_adapters():
    assert ad.CHEAP_PROVIDER_DEFAULTS is kat.CHEAP_PROVIDER_DEFAULTS
    assert ad._OPENAI_COMPATIBLE_PROVIDERS is kat._OPENAI_COMPATIBLE_PROVIDERS


def test_breaker_symbolerne_overlevede_flytningen():
    # De blev revet med ud i første forsøg og væltede 73 test-moduler ved
    # collection. De hører til i adapters, ikke i kataloget.
    for navn in ("_ARKO_PROVIDER_ID", "_OFA_PROVIDER_ID", "_arko_circuit_open"):
        assert hasattr(ad, navn), navn


def test_llm7_har_kun_de_maalte_modeller():
    e = kat.CHEAP_PROVIDER_DEFAULTS["llm7"]
    assert e["base_url"] == "https://api.llm7.io/v1"
    assert e["auth_kind"] == "bearer"
    assert set(e["static_models"]) == {
        "codestral-latest", "minimax-m2.7", "mistral-Nemo-Instruct-2407",
    }


def test_gpt_oss_er_udeladt_med_vilje():
    """Den svarer 200 med TOM tekst. I en lane ligner det succes — værre end
    en fejl, fordi ingen opdager det."""
    assert "gpt-oss" not in kat.CHEAP_PROVIDER_DEFAULTS["llm7"]["static_models"]


def test_de_betalte_llm7_modeller_er_ikke_med():
    """31 af 36 gav 402 «Insufficient balance», selvom de står på /v1/models."""
    m = kat.CHEAP_PROVIDER_DEFAULTS["llm7"]["static_models"]
    for betalt in ("claude-opus-5", "gpt-6-astra", "deepseek-v4-flash", "glm-5.3-flash"):
        assert betalt not in m


def test_alle_udbydere_har_de_felter_puljen_bruger():
    # `runtime-key` sad ikke i min første liste — jeg gættede på lovlige
    # værdier i stedet for at læse dem. Værdierne kommer nu fra kataloget selv.
    lovlige = {"bearer", "none", "oauth", "runtime-key"}
    for navn, e in kat.CHEAP_PROVIDER_DEFAULTS.items():
        assert isinstance(e.get("priority"), int), navn
        assert e.get("auth_kind") in lovlige, f"{navn}: {e.get('auth_kind')}"


def test_runtime_key_etiketten_er_ikke_mekanismen():
    """`auth_kind: "runtime-key"` står på arko og læses af INGEN kode — arkos
    nøgle går gennem et hårdkodet særtilfælde. Mekanismen er
    RUNTIME_KEY_PROVIDERS. Testen findes så den næste ikke tror etiketten
    virker."""
    from core.services.cheap_provider_runtime_keys import RUNTIME_KEY_PROVIDERS
    etiket = {n for n, e in kat.CHEAP_PROVIDER_DEFAULTS.items()
              if e.get("auth_kind") == "runtime-key"}
    assert etiket == {"arko"}
    assert "arko" not in RUNTIME_KEY_PROVIDERS


def test_dahl_og_tokenharbor_er_koblet_til_noeglerne():
    """Nøglen skal kendes TRE steder (readiness, dispatch, profil-scan), og de
    to sidste læser dette kort — uden en post her kom udbyderen aldrig i puljen
    (xkiro 7/9-2026)."""
    from core.services.cheap_provider_runtime_keys import RUNTIME_KEY_PROVIDERS
    assert RUNTIME_KEY_PROVIDERS["dahl"][0] == "dahl_api_key"
    assert RUNTIME_KEY_PROVIDERS["tokenharbor"][0] == "tokenharbor_api_key"
    for p in ("dahl", "tokenharbor"):
        assert p in kat._OPENAI_COMPATIBLE_PROVIDERS


def test_dahl_har_kun_de_maalte_modeller():
    e = kat.CHEAP_PROVIDER_DEFAULTS["dahl"]
    assert e["base_url"] == "https://inference.dahl.global/v1"
    assert set(e["static_models"]) == {
        "zai-org/GLM-5.3-Flash", "MiniMaxAI/MiniMax-M2.7", "deepseek-ai/DeepSeek-V4-Flash-0731",
    }


def test_tokenharbor_kun_gratis_og_uden_mimo():
    e = kat.CHEAP_PROVIDER_DEFAULTS["tokenharbor"]
    assert e["base_url"] == "https://tokenharbor.ai/v1"
    assert all(m.endswith(":free") for m in e["static_models"])
    # mimo-v2.5:free kaldte ikke værktøjet i målingen.
    assert "mimo-v2.5:free" not in e["static_models"]
    # Langsom (7-54 s): skal ligge bag de hurtige gratis-udbydere.
    assert e["priority"] > kat.CHEAP_PROVIDER_DEFAULTS["dahl"]["priority"]


def test_de_fem_nye_udbydere_er_koblet_til_noeglerne():
    """17/9-2026: nøgle i runtime.json + post i kortet + openai-compat, ellers når
    de aldrig puljen (samme fælde som xkiro)."""
    from core.services.cheap_provider_runtime_keys import RUNTIME_KEY_PROVIDERS
    for p in ("inception", "poolside", "chatanywhere", "internlm", "agnes"):
        assert RUNTIME_KEY_PROVIDERS[p][0] == f"{p}_api_key"
        assert p in kat._OPENAI_COMPATIBLE_PROVIDERS
        assert kat.CHEAP_PROVIDER_DEFAULTS[p]["cost_class"] == "free"
    # orcarouter kom med samme dag, da GitHub-kontoen var koblet.
    assert RUNTIME_KEY_PROVIDERS["orcarouter"][0] == "orcarouter_api_key"
    orca = kat.CHEAP_PROVIDER_DEFAULTS["orcarouter"]["static_models"]
    assert all(m.endswith("-free") for m in orca)
    assert not any(m.startswith("stealth/") or "orcaverify" in m for m in orca)


def test_modeller_der_ikke_kaldte_vaerktoejet_er_udeladt():
    assert "poolside/laguna-s-2.1" not in kat.CHEAP_PROVIDER_DEFAULTS["poolside"]["static_models"]
    assert "intern-latest" not in kat.CHEAP_PROVIDER_DEFAULTS["internlm"]["static_models"]


def test_kilo_har_de_maalte_gratis_modeller_og_ikke_stealth():
    ms = kat.CHEAP_PROVIDER_DEFAULTS["kilo"]["static_models"]
    assert all(m.endswith(":free") or m == "openrouter/free" for m in ms)
    assert "nex-agi/nex-n2.5-mini:free" in ms
    assert not any(m.startswith("stealth/") for m in ms)


def test_meganova_kun_modellen_der_kaldte_vaerktoejet():
    from core.services.cheap_provider_runtime_keys import RUNTIME_KEY_PROVIDERS
    assert RUNTIME_KEY_PROVIDERS["meganova"][0] == "meganova_api_key"
    e = kat.CHEAP_PROVIDER_DEFAULTS["meganova"]
    assert e["static_models"] == ["mistralai/Mistral-Small-3.2-24B-Instruct-2506"]
    assert "meganova" in kat._OPENAI_COMPATIBLE_PROVIDERS
