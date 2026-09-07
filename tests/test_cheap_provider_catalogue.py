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
