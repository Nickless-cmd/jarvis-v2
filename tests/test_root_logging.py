"""Modul-loggere skal have et sted at lande.

uvicorn opsætter kun sine egne loggere. Uden rod-konfiguration skriver enhver
`logging.getLogger(__name__)` ud i ingenting — ikke som en fejl, men som
tavshed. Det agentiske loop har skrevet «agentic-loop-exit reason=…» ved hver
kørsel i månedsvis uden at en eneste linje nåede journalen.
"""
from __future__ import annotations

import logging

from apps.api.jarvis_api.app import wire_root_logging


def _ryd(root: logging.Logger, gemt) -> None:
    root.handlers[:] = gemt


def test_et_modulnavn_naar_frem_naar_roden_er_koblet(caplog):
    root = logging.getLogger()
    gemt = list(root.handlers)
    uv = logging.getLogger("uvicorn")
    uv_gemt = list(uv.handlers)
    try:
        h = logging.StreamHandler()
        uv.handlers[:] = [h]
        root.handlers[:] = []
        res = wire_root_logging()
        assert res["added"] == 1
        assert h in root.handlers, "modul-loggere har intet sted at lande uden dette"
    finally:
        uv.handlers[:] = uv_gemt
        _ryd(root, gemt)


def test_kalder_man_to_gange_faar_man_ikke_dobbelte_linjer():
    """En genstart eller to lifespans må ikke give hver log-linje to gange."""
    root = logging.getLogger()
    gemt = list(root.handlers)
    uv = logging.getLogger("uvicorn")
    uv_gemt = list(uv.handlers)
    try:
        h = logging.StreamHandler()
        uv.handlers[:] = [h]
        root.handlers[:] = []
        wire_root_logging()
        anden = wire_root_logging()
        assert anden["added"] == 0
        assert root.handlers.count(h) == 1
    finally:
        uv.handlers[:] = uv_gemt
        _ryd(root, gemt)


def test_tredjepart_holdes_nede_saa_vores_egne_linjer_kan_ses():
    """Ellers bytter vi én slags tavshed for en anden: vores linjer drukner."""
    uv = logging.getLogger("uvicorn")
    uv_gemt = list(uv.handlers)
    root = logging.getLogger()
    gemt = list(root.handlers)
    try:
        uv.handlers[:] = [logging.StreamHandler()]
        wire_root_logging()
        for larmende in ("httpx", "urllib3", "asyncio"):
            assert logging.getLogger(larmende).level == logging.WARNING
    finally:
        uv.handlers[:] = uv_gemt
        _ryd(root, gemt)


def test_uden_uvicorn_handlers_goer_den_intet():
    """I en test- eller CLI-proces findes uvicorn ikke — så skal den tie stille
    frem for at kaste."""
    uv = logging.getLogger("uvicorn")
    gemt = list(uv.handlers)
    try:
        uv.handlers[:] = []
        assert wire_root_logging() == {"added": 0, "quieted": 0}
    finally:
        uv.handlers[:] = gemt
