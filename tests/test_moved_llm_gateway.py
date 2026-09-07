"""Værten flyttede fra 10.0.0.45 til 10.0.0.26 (7/9-2026).

To ting pegede stadig på den gamle adresse, og begge var tavse:

  * `ollama-a2` — 1.063 kald på syv døgn, ALLE «[Errno 113] No route to host»,
    0,0 % success. En død pool-plads der blev valgt igen og igen.
  * VPN-egress-proxyen — kostede intet i dag, fordi v6bind tager forrang for de
    allowlistede account2-udbydere. Men slukkes v6bind, ville al account2-trafik
    ryge mod en død vært, og lækage-guarden ville se et gyldigt endpoint.

Testene er billige og fanger præcis den slags: en adresse der er blevet
efterladt i en konstant.
"""
from core.services.cheap_provider_catalogue import CHEAP_PROVIDER_DEFAULTS
from core.services.egress_routing import _DEFAULT_PROXY_ENDPOINTS

GAMMEL = "10.0.0.45"


def test_ollama_a2_peger_paa_den_levende_gateway():
    assert CHEAP_PROVIDER_DEFAULTS["ollama-a2"]["base_url"] == "http://10.0.0.26:11434"


def test_egress_proxyerne_peger_paa_den_levende_vaert():
    for navn in ("vpn", "he6"):
        assert _DEFAULT_PROXY_ENDPOINTS[navn] == "http://10.0.0.26:8888", navn


def test_ingen_konstant_naevner_den_gamle_adresse():
    """Kommentarer må gerne fortælle historien; VÆRDIER må ikke."""
    for navn, e in CHEAP_PROVIDER_DEFAULTS.items():
        assert GAMMEL not in str(e.get("base_url") or ""), navn
    for navn, v in _DEFAULT_PROXY_ENDPOINTS.items():
        assert GAMMEL not in str(v or ""), navn


def test_home_ruten_har_stadig_ingen_proxy():
    """`home` = direkte ud ad hjemme-IP'en. Får den et endpoint, lækker
    default-profilen gennem VPN'en uden at nogen har bedt om det."""
    assert _DEFAULT_PROXY_ENDPOINTS["home"] is None


def test_kun_den_model_free_tier_faktisk_kan():
    """Gatewayen LISTER syv modeller, men account2's free-tier kan én.
    minimax-m3, glm-5.2, kimi-k2.7-code og deepseek-v4-* svarer alle «this
    model requires a subscription». At stå på /api/tags er ikke det samme som
    at kunne kaldes — samme lærestreg som LLM7's 46 modeller hvoraf 3 svarer."""
    assert CHEAP_PROVIDER_DEFAULTS["ollama-a2"]["static_models"] == ["gemma4:31b-cloud"]
