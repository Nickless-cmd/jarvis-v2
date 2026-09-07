"""Delte ejer-nøgler i runtime.json — udskilt 7/9-2026.

Pointen med at samle dem: nøglen skal bruges TO steder (readiness OG dispatch).
Da HuggingFace blev tilføjet, blev begge skrevet i hånden. Rammer man kun det
ene, ser udbyderen klar ud og fejler så med `auth-not-ready` — eller omvendt,
og slot'et er dødt uden at nogen kan se hvorfor.
"""
import pytest

from core.services import cheap_provider_runtime_keys as k


# Navnene hentes fra RUNTIME_KEY_PROVIDERS, ikke skrevet af igen. To grunde:
# testen følger kilden hvis et navn ændrer sig, OG detect-secrets flager
# mønstret `"xkiro_api_key": "..."` på selve NØGLENAVNET uanset værdien. En
# `pragma: allowlist secret` ville have slukket for scanneren i stedet for at
# fjerne grunden til at den råbte.
def _navn(provider: str) -> str:
    return k.RUNTIME_KEY_PROVIDERS[provider][0]



@pytest.fixture
def nøgle(monkeypatch):
    def sæt(vaerdier: dict):
        import core.runtime.secrets as s
        monkeypatch.setattr(s, "read_runtime_key",
                            lambda navn, env_override=None: vaerdier.get(navn, ""))
    return sæt


def test_xkiro_laeses_fra_runtime_json(nøgle):
    nøgle({_navn("xkiro"): "ikke-en-rigtig-noegle-1"})
    assert k.runtime_owner_key("xkiro") == "ikke-en-rigtig-noegle-1"
    assert k.has_runtime_owner_key("xkiro") is True


def test_huggingface_virker_uaendret(nøgle):
    nøgle({_navn("huggingface"): "ikke-en-rigtig-noegle-2"})
    assert k.runtime_owner_key("huggingface") == "ikke-en-rigtig-noegle-2"


def test_ukendt_udbyder_giver_tom_streng(nøgle):
    nøgle({_navn("xkiro"): "x"})
    assert k.runtime_owner_key("bazaarlink") == ""
    assert k.has_runtime_owner_key("bazaarlink") is False


def test_manglende_noegle_er_ikke_en_fejl(nøgle):
    nøgle({})
    assert k.runtime_owner_key("xkiro") == ""
    assert k.has_runtime_owner_key("xkiro") is False


def test_en_kastende_secrets_modul_vaelter_ikke_lanen(monkeypatch):
    import core.runtime.secrets as s

    def sur(*a, **kw):
        raise RuntimeError("runtime.json er ulæselig")

    monkeypatch.setattr(s, "read_runtime_key", sur)
    assert k.runtime_owner_key("xkiro") == ""


def test_tomme_og_uegnede_input(nøgle):
    nøgle({_navn("xkiro"): "x"})
    for d in ("", None, "   "):
        assert k.runtime_owner_key(d) == ""


def test_bagudkompatibel_indpakning_findes_stadig(nøgle):
    from core.services.cheap_provider_runtime_adapters import _huggingface_runtime_token
    nøgle({_navn("huggingface"): "ikke-en-rigtig-noegle-3"})
    assert _huggingface_runtime_token() == "ikke-en-rigtig-noegle-3"


def test_katalog_entry_matcher_det_maalte():
    from core.services.cheap_provider_runtime_adapters import CHEAP_PROVIDER_DEFAULTS as C
    e = C["xkiro"]
    assert e["base_url"] == "https://api.xkiro.com/v1"
    assert e["protocol"] == "openai-chat"
    assert e["cost_class"] == "free"
    # Kun `:free`-mærkede i cheap lane — DeepSeek-modellerne trækker fra samme
    # pulje, men navnet lover intet, og de hører til i den synlige bane.
    assert all(m.endswith(":free") for m in e["static_models"])
