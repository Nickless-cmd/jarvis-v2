import asyncio
from central_cli.engine.state import HudState
from central_cli.engine.workers import fetch_surface, SURFACE_PATHS


class _FakeClient:
    def __init__(self, mapping, fail=None):
        self._mapping = mapping
        self._fail = fail or set()
    def get_json(self, path, params=None):
        if path in self._fail:
            from central_cli.client import CentralError
            raise CentralError("server", "boom")
        return self._mapping[path]


def test_fetch_surface_writes_ok():
    state = HudState()
    client = _FakeClient({"/central/realtime": {"status": "green"}})
    asyncio.run(fetch_surface(client, state, "realtime"))
    e = state.get("realtime")
    assert e.data == {"status": "green"} and e.error is None


def test_fetch_surface_records_error_but_keeps_data():
    state = HudState()
    state.set_ok("realtime", {"status": "green"})
    client = _FakeClient({}, fail={"/central/realtime"})
    asyncio.run(fetch_surface(client, state, "realtime"))
    e = state.get("realtime")
    assert e.error is not None
    assert e.data == {"status": "green"}


def test_surface_paths_cover_phase1_surfaces():
    for s in ("realtime", "costs_daily", "diagnostics"):
        assert s in SURFACE_PATHS
