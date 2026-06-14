"""Minimal test for voice_daemon_worker — API_BASE peger på localhost-uvicorn-porten."""
from __future__ import annotations

import re


def test_api_base_points_to_local_uvicorn() -> None:
    import core.skills.voice.voice_daemon_worker as v
    # Efter port-omlægningen lytter uvicorn på 127.0.0.1:8080 (Caddy ejer :80/:443).
    assert re.match(r"^http://(localhost|127\.0\.0\.1):8080$", v.API_BASE), v.API_BASE
