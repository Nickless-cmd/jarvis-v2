def test_routines_router_exists():
    from apps.api.jarvis_api.routes.routines import router

    assert router.prefix == "/api/routines"
