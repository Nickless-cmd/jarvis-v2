def test_resolve_egress_default_is_home():
    from core.services.egress_routing import resolve_egress
    assert resolve_egress("cohere", "default") == "home"
    assert resolve_egress("groq", "default") == "home"
    assert resolve_egress("cohere", "") == "home"   # empty == default


def test_resolve_egress_account2_vpn():
    from core.services.egress_routing import resolve_egress
    assert resolve_egress("cohere", "account2") == "vpn"
    assert resolve_egress("mistral", "account3") == "vpn"


def test_resolve_egress_groq_uses_ipv6():
    from core.services.egress_routing import resolve_egress
    assert resolve_egress("groq", "account2") == "he6"   # groq exception


def test_proxy_endpoints_has_defaults():
    from core.services.egress_routing import proxy_endpoints
    ep = proxy_endpoints()
    assert ep["vpn"] == "http://10.0.0.45:8888"
    assert ep["he6"] == "http://10.0.0.46:8888"
    assert ep["home"] is None
