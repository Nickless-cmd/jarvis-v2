def test_local_when_runtime_enabled(monkeypatch):
    import core.services.central_runtime_proxy as p
    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES","1")
    assert p.proxy_or_local("x", lambda: {"ok":1}) == {"ok":1}

def test_proxy_when_api_only(monkeypatch):
    import core.services.central_runtime_proxy as p
    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES","0")
    monkeypatch.setattr(p, "_http_get", lambda name: {"ok":2})
    assert p.proxy_or_local("x", lambda: {"ok":1}) == {"ok":2}

def test_self_safe_on_error(monkeypatch):
    import core.services.central_runtime_proxy as p
    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES","0")
    def boom(name): raise RuntimeError("nej")
    monkeypatch.setattr(p, "_http_get", boom)
    assert p.proxy_or_local("x", lambda: {"ok":1}) == {}
