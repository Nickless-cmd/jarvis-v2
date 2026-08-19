def test_resolve_egress_default_is_home():
    from core.services.egress_routing import resolve_egress
    assert resolve_egress("cohere", "default") == "home"
    assert resolve_egress("groq", "default") == "home"
    assert resolve_egress("cohere", "") == "home"   # empty == default


def test_resolve_egress_account2_vpn():
    from core.services.egress_routing import resolve_egress
    assert resolve_egress("cohere", "account2") == "vpn"
    assert resolve_egress("mistral", "account3") == "vpn"


def test_groq_har_ingen_saerrute_mere():
    """groq pegede på "he6", hvis vært blev frigivet 23. juli 2026.

    ground_truth_registry havde noteret frigivelsen; konfigurationen fulgte aldrig med.
    groq/account2 løses af native v6bind FØR proxy-stien konsulteres, og falder v6bind
    ud er `vpn` den rigtige nødplan — samme som de øvrige tolv.
    """
    from core.services.egress_routing import EGRESS_ROUTES, resolve_egress
    assert resolve_egress("groq", "account2") == "vpn"
    assert EGRESS_ROUTES == {}, "en per-provider særrute er en fremtidig drift-fælde"


def test_proxy_endpoints_has_defaults():
    """Test invarianten, ikke adressen.

    Denne test låste tidligere he6 fast på `http://10.0.0.46:8888`. Den IP forsvandt da
    llm-gateway (CT106, DHCP) flyttede til .45, og testen blev grøn på en påstand der var
    holdt op med at være sand — mens ALLE groq/account2-kald fejlede med Errno 113.
    En test der gentager en hardkodet adresse beviser kun at nogen skrev den to steder.
    """
    from core.services.egress_routing import proxy_endpoints
    ep = proxy_endpoints()
    assert ep["home"] is None, "home = ingen proxy, altid"
    for name in ("vpn", "he6"):
        assert ep[name] and ep[name].startswith("http://"), name
    # Begge proxy-ruter betjenes af den samme tinyproxy på llm-gateway; peger de på
    # forskellige værter, er den ene sandsynligvis efterladt ved en flytning.
    assert ep["vpn"] == ep["he6"], (
        "vpn og he6 peger på forskellige værter — tjek om den ene er forældet"
    )


def test_resolve_nat64_default_profile_never():
    from core.services.egress_routing import resolve_nat64
    # default profile (home IP) is never NAT64-routed, regardless of flag/allowlist
    assert resolve_nat64("cohere", "default") is False
    assert resolve_nat64("cohere", "") is False


def test_resolve_nat64_flag_off_is_false(monkeypatch):
    import core.services.egress_routing as er
    # flag OFF (default) -> account2 slot still not NAT64-routed (VPN path unchanged)
    monkeypatch.setattr(er, "get_runtime_state_value",
                        lambda *a, **k: False, raising=False)
    assert er.resolve_nat64("cohere", "account2") is False


def test_resolve_nat64_flag_on_allowlist(monkeypatch):
    import core.services.egress_routing as er
    state = {er._NAT64_FLAG_KEY: True, er._NAT64_PROVIDERS_KEY: "cohere,sambanova"}

    def fake_get(key, default=None):
        return state.get(key, default)

    # patch the db_core import target used inside resolve_nat64
    import core.runtime.db_core as dbc
    monkeypatch.setattr(dbc, "get_runtime_state_value", fake_get, raising=False)
    assert er.resolve_nat64("cohere", "account2") is True
    assert er.resolve_nat64("sambanova", "account2") is True
    assert er.resolve_nat64("nvidia-nim", "account2") is False   # not on allowlist


def test_nat64_synthesize_empty_host_none():
    from core.services.egress_routing import nat64_synthesize
    assert nat64_synthesize("") is None


def test_nat64_synthesize_cache_hit(monkeypatch):
    import core.services.egress_routing as er
    er._nat64_cache.clear()
    import time
    er._nat64_cache["api.example.com"] = ("2a00:1098:2b::1:2:3", time.monotonic() + 999)
    # cache hit returns without any DNS query
    assert er.nat64_synthesize("api.example.com") == "2a00:1098:2b::1:2:3"
